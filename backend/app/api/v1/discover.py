# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Discover endpoints.

Public endpoints that power the /discover page and patron-facing RA-shelf
browsing. Currently exposes staff-curated readers'-advisory shelves; the
neighbors/trending rail will land in a separate PR.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.content_i18n import translated
from app.core.database import get_db
from app.models.catalog import CatalogItem
from app.models.staff_shelves import ShelfAudience, StaffShelf


router = APIRouter(prefix="/discover", tags=["discover"])


class ShelfSummary(BaseModel):
    id: int
    slug: str
    title: str
    description: Optional[str] = None
    audience: Optional[str] = None
    display_order: int
    item_count: int

    class Config:
        from_attributes = True


class ShelfItem(BaseModel):
    id: int
    title: str
    author: Optional[str] = None
    cover_url: Optional[str] = None
    item_type: str
    status: str

    class Config:
        from_attributes = True


class ShelfDetail(ShelfSummary):
    items: List[ShelfItem] = []


def _summary(shelf: StaffShelf, lang: Optional[str] = None) -> ShelfSummary:
    item_ids = shelf.item_ids or []
    return ShelfSummary(
        id=shelf.id,
        slug=shelf.slug,
        title=translated(shelf, "title", lang),
        description=translated(shelf, "description", lang),
        audience=shelf.audience.value if shelf.audience else None,
        display_order=shelf.display_order,
        item_count=len(item_ids),
    )


@router.get("/shelves", response_model=List[ShelfSummary])
async def list_shelves(
    audience: Optional[ShelfAudience] = Query(default=None),
    lang: Optional[str] = Query(None, max_length=10),
    db: AsyncSession = Depends(get_db),
):
    """Return active shelves ordered by display_order. Optionally filter by
    audience -- "all" shelves are returned for every audience filter."""
    stmt = select(StaffShelf).where(StaffShelf.is_active.is_(True))
    if audience is not None:
        stmt = stmt.where(
            StaffShelf.audience.in_([audience, ShelfAudience.all])
        )
    stmt = stmt.order_by(StaffShelf.display_order.asc(), StaffShelf.id.asc())
    result = await db.execute(stmt)
    shelves = result.scalars().all()
    return [_summary(s, lang) for s in shelves]


@router.get("/shelves/{slug}", response_model=ShelfDetail)
async def get_shelf(
    slug: str,
    lang: Optional[str] = Query(None, max_length=10),
    db: AsyncSession = Depends(get_db),
):
    """Return a single shelf plus its catalog items in display order."""
    result = await db.execute(
        select(StaffShelf).where(StaffShelf.slug == slug)
    )
    shelf = result.scalar_one_or_none()
    if shelf is None or not shelf.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")

    item_ids = list(shelf.item_ids or [])
    items: List[ShelfItem] = []
    if item_ids:
        rows = await db.execute(
            select(CatalogItem).where(CatalogItem.id.in_(item_ids))
        )
        by_id = {ci.id: ci for ci in rows.scalars().all()}
        for cid in item_ids:
            ci = by_id.get(cid)
            if ci is None:
                continue
            items.append(
                ShelfItem(
                    id=ci.id,
                    title=ci.title,
                    author=ci.author,
                    cover_url=ci.cover_url,
                    item_type=ci.item_type.value if hasattr(ci.item_type, "value") else str(ci.item_type),
                    status=ci.status.value if hasattr(ci.status, "value") else str(ci.status),
                )
            )

    base = _summary(shelf, lang)
    return ShelfDetail(**base.model_dump(), items=items)
