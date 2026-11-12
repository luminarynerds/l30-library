# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron-facing CRUD + ``run`` endpoints for saved catalog searches.

Routes live under ``/api/v1/patrons/me/saved-searches``. All endpoints
require an authenticated user and only ever return / mutate rows owned
by that user (``WHERE user_id = current_user.id``). Cross-patron access
is rejected with 404 (not 403) to avoid leaking the existence of
another user's row.
"""
from __future__ import annotations

from app.core.logging import get_logger
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.catalog import ItemStatus, ItemType
from ...models.saved_search import SavedSearch
from ...models.user import User
from ...schemas.catalog import CatalogItemResponse
from ...schemas.saved_search import (
    SavedSearchCreate,
    SavedSearchListResponse,
    SavedSearchResponse,
    SavedSearchRunResponse,
    SavedSearchUpdate,
)
from ...services.catalog_search_service import catalog_search_service
from .auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(
    prefix="/patrons/me/saved-searches",
    tags=["patron-saved-searches"],
)

# Per-patron cap. The plan recommended 25 with a clear error; tune from
# telemetry once we have any.
MAX_PER_USER = 25


async def _get_owned_or_404(
    db: AsyncSession, search_id: uuid.UUID, user_id: int
) -> SavedSearch:
    result = await db.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == user_id,
        )
    )
    saved = result.scalar_one_or_none()
    if saved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found.",
        )
    return saved


@router.get("", response_model=SavedSearchListResponse)
async def list_saved_searches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavedSearchListResponse:
    """List the current patron's saved searches, newest first."""
    result = await db.execute(
        select(SavedSearch)
        .where(SavedSearch.user_id == current_user.id)
        .order_by(SavedSearch.created_at.desc())
    )
    rows = result.scalars().all()
    return SavedSearchListResponse(
        items=[SavedSearchResponse.model_validate(r) for r in rows],
        total=len(rows),
    )


@router.post(
    "",
    response_model=SavedSearchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_saved_search(
    payload: SavedSearchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavedSearchResponse:
    """Create a new saved search for the current patron."""
    # Enforce per-user cap so a runaway client can't fill the table.
    count_result = await db.execute(
        select(func.count())
        .select_from(SavedSearch)
        .where(SavedSearch.user_id == current_user.id)
    )
    count = count_result.scalar_one()
    if count >= MAX_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"You have reached the maximum of {MAX_PER_USER} saved "
                "searches. Delete one to add another."
            ),
        )

    # Email opt-in requires a deliverable address. We don't 400 if the
    # email is missing — we just downgrade to in-app so the UI's tooltip
    # explanation remains the source of truth without surfacing a server
    # error on a benign UX state.
    notify_email = payload.notify_email
    if notify_email and not (current_user.email and current_user.email.strip()):
        notify_email = False

    saved = SavedSearch(
        user_id=current_user.id,
        library_system_id=getattr(current_user, "home_library_system_id", None),
        name=payload.name,
        query=payload.query,
        filters_json=payload.filters_json,
        sort_by=payload.sort_by,
        view_mode=payload.view_mode,
        notify_on_new=payload.notify_on_new,
        notify_in_app=payload.notify_in_app,
        notify_email=notify_email,
    )
    db.add(saved)
    await db.commit()
    await db.refresh(saved)
    return SavedSearchResponse.model_validate(saved)


@router.get("/{search_id}", response_model=SavedSearchResponse)
async def get_saved_search(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavedSearchResponse:
    """Return a single saved search owned by the current patron."""
    saved = await _get_owned_or_404(db, search_id, current_user.id)
    return SavedSearchResponse.model_validate(saved)


@router.patch("/{search_id}", response_model=SavedSearchResponse)
async def update_saved_search(
    search_id: uuid.UUID,
    payload: SavedSearchUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavedSearchResponse:
    """Patch a saved search (rename, retune filters, toggle notifications)."""
    saved = await _get_owned_or_404(db, search_id, current_user.id)

    data = payload.model_dump(exclude_unset=True)

    # Same email-deliverability check as create: don't enable email alerts
    # for a patron with no email on file.
    if data.get("notify_email") and not (
        current_user.email and current_user.email.strip()
    ):
        data["notify_email"] = False

    for key, value in data.items():
        setattr(saved, key, value)

    await db.commit()
    await db.refresh(saved)
    return SavedSearchResponse.model_validate(saved)


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete one of the current patron's saved searches."""
    saved = await _get_owned_or_404(db, search_id, current_user.id)
    await db.delete(saved)
    await db.commit()


@router.post("/{search_id}/run", response_model=SavedSearchRunResponse)
async def run_saved_search(
    search_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavedSearchRunResponse:
    """Execute a saved search and return paginated results.

    The response payload mirrors ``POST /api/v1/catalog/search/advanced``
    (results / total / page / per_page / pages) plus the ``saved_search_id``
    so the frontend can render shared markup.
    """
    saved = await _get_owned_or_404(db, search_id, current_user.id)
    filters = saved.filters_json or {}

    # Translate filter strings to enums the same way the simple advanced
    # search endpoint does. Bad values are silently dropped on run rather
    # than 400ing — a stale saved search that references an enum value
    # the org has since removed should still return SOME results.
    item_type: Optional[ItemType] = None
    item_status: Optional[ItemStatus] = None
    raw_type = filters.get("item_type")
    raw_status = filters.get("status")
    if raw_type:
        try:
            item_type = ItemType(raw_type)
        except ValueError:
            logger.info(
                "saved_search.run: dropping unknown item_type=%r for search %s",
                raw_type,
                saved.id,
            )
    if raw_status:
        try:
            item_status = ItemStatus(raw_status)
        except ValueError:
            logger.info(
                "saved_search.run: dropping unknown status=%r for search %s",
                raw_status,
                saved.id,
            )

    items, total = await catalog_search_service.advanced_search_with_count(
        db=db,
        title=saved.query or filters.get("title"),
        author=filters.get("author"),
        subject=filters.get("subject"),
        isbn=filters.get("isbn"),
        publisher=filters.get("publisher"),
        operator=filters.get("operator", "AND"),
        exclude_subject=filters.get("exclude_subject"),
        item_type=item_type,
        status=item_status,
        year_min=filters.get("year_min"),
        year_max=filters.get("year_max"),
        location=filters.get("location"),
        min_lexile=filters.get("min_lexile"),
        max_lexile=filters.get("max_lexile"),
        page=page,
        per_page=per_page,
    )

    saved.last_run_at = func.now()
    await db.commit()

    return SavedSearchRunResponse(
        saved_search_id=saved.id,
        results=[
            CatalogItemResponse.model_validate(i).model_dump() for i in items
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )
