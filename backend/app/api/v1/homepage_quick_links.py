# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Homepage quick links API — public read, staff write."""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.homepage_content import HomepageQuickLink
from ...models.user import User
from ...schemas.homepage_content import (
    QuickLinkCreate,
    QuickLinkResponse,
    QuickLinkUpdate,
    ReorderRequest,
)
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/homepage/quick-links", tags=["homepage-quick-links"])


@router.get("/", response_model=list[QuickLinkResponse])
async def get_active_quick_links(db: AsyncSession = Depends(get_db)):
    """Public — returns active links sorted by sort_order."""
    result = await db.execute(
        select(HomepageQuickLink)
        .where(HomepageQuickLink.is_active == True)
        .order_by(HomepageQuickLink.sort_order.asc())
    )
    return result.scalars().all()


@router.get("/all", response_model=list[QuickLinkResponse])
async def get_all_quick_links(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff — returns all links including inactive."""
    result = await db.execute(
        select(HomepageQuickLink).order_by(HomepageQuickLink.sort_order.asc())
    )
    return result.scalars().all()


@router.post("/", response_model=QuickLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_quick_link(
    body: QuickLinkCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff — create a new quick link."""
    link = HomepageQuickLink(
        **body.model_dump(),
        created_by_id=current_user.id,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


@router.put("/reorder")
async def reorder_quick_links(
    body: ReorderRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff — bulk reorder quick links."""
    for item in body.items:
        await db.execute(
            update(HomepageQuickLink)
            .where(HomepageQuickLink.id == item.id)
            .values(sort_order=item.sort_order)
        )
    await db.commit()
    return {"status": "reordered", "count": len(body.items)}


@router.put("/{link_id}", response_model=QuickLinkResponse)
async def update_quick_link(
    link_id: int,
    body: QuickLinkUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff — update a quick link."""
    result = await db.execute(
        select(HomepageQuickLink).where(HomepageQuickLink.id == link_id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Quick link not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(link, key, value)

    await db.commit()
    await db.refresh(link)
    return link


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quick_link(
    link_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff — delete a quick link."""
    result = await db.execute(
        select(HomepageQuickLink).where(HomepageQuickLink.id == link_id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Quick link not found")

    await db.delete(link)
    await db.commit()
    return None
