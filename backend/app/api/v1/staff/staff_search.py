# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Advanced unified staff search API."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ..dependencies import get_current_user, require_staff
from ....models.user import User
from ....services.staff_search_service import (
    get_staff_search_service,
    get_recent_searches,
)
from .patrons_schemas import CardStatusFilter

router = APIRouter(prefix="/staff/search", tags=["staff-search"])


class StaffSearchItemResponse(BaseModel):
    id: str
    entity_type: str
    title: str
    subtitle: str | None = None
    snippet: str | None = None
    url: str | None = None
    score: float
    source: str
    metadata: dict = {}


class StaffSearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[StaffSearchItemResponse]
    page: int
    per_page: int
    has_more: bool
    suggestions: list[str] = []


class RecentSearchesResponse(BaseModel):
    searches: list[str]


@router.get("/unified", response_model=StaffSearchResponse)
async def unified_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    types: Optional[str] = Query(None, description="Comma-separated entity types to filter by"),
    card_status: CardStatusFilter = Query(
        CardStatusFilter.any,
        alias="cardStatus",
        description=(
            "Restrict patron results to a library-card expiration band. "
            "Same semantics as /staff/patrons?cardStatus. No effect on non-patron entity types."
        ),
    ),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Search across patrons, items, checkouts, and events.

    Query string can search by:
    - Patron: name, email, phone, patron ID (library card)
    - Item: title, author, ISBN
    - Checkout: patron name or item title
    - Event: title, description, location
    """
    entity_types = []
    if types:
        entity_types = [t.strip() for t in types.split(",")]

    service = get_staff_search_service(db)
    result = await service.search(
        query=q,
        user_id=staff_user.id,
        page=page,
        per_page=per_page,
        entity_types=entity_types,
        card_status=card_status,
    )
    return result.to_dict()


@router.get("/recent", response_model=RecentSearchesResponse)
async def get_recent_search_list(
    limit: int = Query(10, ge=1, le=50, description="Number of recent searches to return"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get recent searches for the current user."""
    searches = await get_recent_searches(db, staff_user.id, limit)
    return RecentSearchesResponse(searches=searches)
