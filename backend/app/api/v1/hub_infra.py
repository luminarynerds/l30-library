# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hub favorites, hub stats, and hub visit logging endpoints.

All three feature surfaces share a single router so the API surface lives
in one file: /api/v1/hub-favorites, /api/v1/hub-stats/{hub_slug},
/api/v1/hub-visits. They are independent feature areas grouped only by
their shared user-hub vocabulary; tests cover each separately.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models import User, UserHubFavorite, UserHubVisit
from ...schemas.user_hub import (
    HubFavoriteCreate,
    HubFavoriteDelete,
    HubFavoriteResponse,
    HubStatsResponse,
    HubVisitCreate,
)
from ...services.hub_stats_service import get_hub_stats
from .auth.helpers import get_current_user

router = APIRouter(tags=["hub-infra"])


# ============================================================================
# Hub favorites
# ============================================================================


@router.get("/hub-favorites", response_model=List[HubFavoriteResponse])
async def list_hub_favorites(
    hub_slug: Optional[str] = Query(None, max_length=64),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's favorites; optionally filtered by hub_slug."""
    stmt = select(UserHubFavorite).where(UserHubFavorite.user_id == current_user.id)
    if hub_slug:
        stmt = stmt.where(UserHubFavorite.hub_slug == hub_slug)
    stmt = stmt.order_by(UserHubFavorite.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/hub-favorites", response_model=HubFavoriteResponse)
async def add_hub_favorite(
    data: HubFavoriteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Idempotently add a favorite. Re-adding an existing favorite is a no-op (200)."""
    existing_stmt = select(UserHubFavorite).where(
        UserHubFavorite.user_id == current_user.id,
        UserHubFavorite.hub_slug == data.hub_slug,
        UserHubFavorite.item_path == data.item_path,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        return existing

    favorite = UserHubFavorite(
        user_id=current_user.id,
        hub_slug=data.hub_slug,
        item_path=data.item_path,
    )
    db.add(favorite)
    try:
        await db.commit()
    except IntegrityError:
        # Race with another concurrent add -- treat as idempotent success.
        await db.rollback()
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            return existing
        raise
    await db.refresh(favorite)
    return favorite


@router.delete("/hub-favorites", status_code=status.HTTP_204_NO_CONTENT)
async def remove_hub_favorite(
    data: HubFavoriteDelete,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Idempotently remove a favorite. Removing a non-existent favorite is a no-op (204)."""
    stmt = select(UserHubFavorite).where(
        UserHubFavorite.user_id == current_user.id,
        UserHubFavorite.hub_slug == data.hub_slug,
        UserHubFavorite.item_path == data.item_path,
    )
    favorite = (await db.execute(stmt)).scalar_one_or_none()
    if favorite is not None:
        await db.delete(favorite)
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Hub stats
# ============================================================================


@router.get("/hub-stats/{hub_slug}", response_model=HubStatsResponse)
async def hub_stats(
    hub_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return named counters for a hub header. Unknown slugs return empty list (NOT 404)."""
    stats = await get_hub_stats(db, hub_slug)
    return HubStatsResponse(hub_slug=hub_slug, stats=stats)


# ============================================================================
# Hub visit logging
# ============================================================================


@router.post("/hub-visits", status_code=status.HTTP_204_NO_CONTENT)
async def log_hub_visit(
    data: HubVisitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fire-and-forget visit log. No dedup, no GET (Wave 3 will add aggregation)."""
    visit = UserHubVisit(
        user_id=current_user.id,
        hub_slug=data.hub_slug,
        item_path=data.item_path,
    )
    db.add(visit)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Hub usage shortcuts (read-side of visit logging)
# ============================================================================


from datetime import datetime, timedelta, timezone  # noqa: E402
from sqlalchemy import desc, func  # noqa: E402

from ...schemas.user_hub import HubShortcutsResponse, ShortcutEntry  # noqa: E402

_SHORTCUTS_WINDOW_DAYS = 14
_SHORTCUTS_DEFAULT_LIMIT = 5
_SHORTCUTS_MAX_LIMIT = 10


@router.get("/hub-shortcuts/{hub_slug}", response_model=HubShortcutsResponse)
async def hub_shortcuts(
    hub_slug: str,
    limit: int = Query(_SHORTCUTS_DEFAULT_LIMIT, ge=1, le=_SHORTCUTS_MAX_LIMIT),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Top-N item_paths in this hub for the current user, last 14 days, by visit count.

    Tie-breaker is most-recent visit. Returns an empty list (not 404) for users
    with no visits in the window so callers can render unconditionally.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=_SHORTCUTS_WINDOW_DAYS)
    stmt = (
        select(
            UserHubVisit.item_path.label("item_path"),
            func.count().label("visit_count"),
            func.max(UserHubVisit.visited_at).label("last_visited_at"),
        )
        .where(
            UserHubVisit.user_id == current_user.id,
            UserHubVisit.hub_slug == hub_slug,
            UserHubVisit.visited_at > cutoff,
        )
        .group_by(UserHubVisit.item_path)
        .order_by(desc("visit_count"), desc("last_visited_at"))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    shortcuts = [
        ShortcutEntry(
            item_path=row.item_path,
            visit_count=row.visit_count,
            last_visited_at=row.last_visited_at,
        )
        for row in rows
    ]
    return HubShortcutsResponse(hub_slug=hub_slug, shortcuts=shortcuts)
