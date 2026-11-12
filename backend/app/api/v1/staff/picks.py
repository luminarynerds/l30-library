# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff Picks API Endpoints

Staff-curated lists of recommended items from the catalog.
Supports creating lists, adding/removing items, and marking items as featured.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.staff_picks import StaffPicksList, StaffPicksItem
from app.models.catalog import CatalogItem
from app.models.user import User
from ..dependencies import require_staff

router = APIRouter(prefix="/staff/picks", tags=["staff-picks"])


def _status_value(raw: object) -> Optional[str]:
    if raw is None:
        return None
    value = getattr(raw, "value", raw)
    return str(value)


# ============================================================================
# Schemas
# ============================================================================


class CatalogItemResponse(BaseModel):
    id: int
    title: str
    author: Optional[str] = None
    cover_url: Optional[str] = None
    item_type: str
    # Surfaced so Discover's sidebar/staff-pick cards can render a consistent
    # status badge (PR-E). Optional because the legacy create/update path
    # below doesn't populate it; the list-detail paths do.
    status: Optional[str] = None

    class Config:
        from_attributes = True


class StaffPicksItemResponse(BaseModel):
    id: int
    catalog_item_id: int
    catalog_item: CatalogItemResponse
    staff_notes: Optional[str] = None
    display_order: int
    added_at: datetime
    added_by_id: Optional[int] = None

    class Config:
        from_attributes = True


class StaffPicksListResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    is_active: bool
    display_order: int
    created_by_id: Optional[int] = None
    items_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StaffPicksListDetailResponse(StaffPicksListResponse):
    items: List[StaffPicksItemResponse] = []


class StaffPicksListCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=5000)
    is_active: bool = False
    display_order: int = 0


class StaffPicksListUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=5000)
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class StaffPicksItemCreate(BaseModel):
    catalog_item_id: int
    staff_notes: Optional[str] = Field(default=None, max_length=5000)
    display_order: int = 0


# ============================================================================
# List Endpoints
# ============================================================================


@router.get("", response_model=List[StaffPicksListResponse])
async def get_staff_picks_lists(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
    _: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> List[StaffPicksListResponse]:
    """Get all staff picks lists (staff only)."""
    items_count_subq = (
        select(func.count(StaffPicksItem.id))
        .where(StaffPicksItem.list_id == StaffPicksList.id)
        .correlate(StaffPicksList)
        .scalar_subquery()
    )
    query = select(StaffPicksList, items_count_subq.label("items_count"))
    if active_only:
        query = query.where(StaffPicksList.is_active == True)
    query = query.order_by(StaffPicksList.display_order).offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()
    return [StaffPicksListResponse(id=l.id, title=l.title, description=l.description,
                                    is_active=l.is_active, display_order=l.display_order,
                                    created_by_id=l.created_by_id, items_count=items_count)
            for l, items_count in rows]


@router.get("/{list_id}", response_model=StaffPicksListDetailResponse)
async def get_staff_picks_list(
    list_id: int,
    _: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> StaffPicksListDetailResponse:
    """Get a specific staff picks list with all items."""
    query = (
        select(StaffPicksList)
        .options(
            selectinload(StaffPicksList.items).selectinload(StaffPicksItem.catalog_item)
        )
        .where(StaffPicksList.id == list_id)
    )
    result = await db.execute(query)
    picks_list = result.scalar_one_or_none()
    if not picks_list:
        raise HTTPException(status_code=404, detail="Staff picks list not found")

    items = [
        StaffPicksItemResponse(
            id=item.id,
            catalog_item_id=item.catalog_item_id,
            catalog_item=CatalogItemResponse(
                id=item.catalog_item.id,
                title=item.catalog_item.title,
                author=item.catalog_item.author,
                cover_url=item.catalog_item.cover_url,
                item_type=item.catalog_item.item_type,
                status=_status_value(item.catalog_item.status),
            ),
            staff_notes=item.staff_notes,
            display_order=item.display_order,
            added_at=item.added_at,
            added_by_id=item.added_by_id,
        )
        for item in (picks_list.items or [])
    ]

    return StaffPicksListDetailResponse(
        id=picks_list.id,
        title=picks_list.title,
        description=picks_list.description,
        is_active=picks_list.is_active,
        display_order=picks_list.display_order,
        created_by_id=picks_list.created_by_id,
        items_count=len(items),
        items=items,
    )


@router.post("", response_model=StaffPicksListResponse, status_code=status.HTTP_201_CREATED)
async def create_staff_picks_list(
    list_in: StaffPicksListCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> StaffPicksListResponse:
    """Create a new staff picks list."""
    picks_list = StaffPicksList(
        title=list_in.title,
        description=list_in.description,
        is_active=list_in.is_active,
        display_order=list_in.display_order,
        created_by_id=staff_user.id,
    )
    db.add(picks_list)
    await db.commit()
    await db.refresh(picks_list)
    return StaffPicksListResponse(
        id=picks_list.id,
        title=picks_list.title,
        description=picks_list.description,
        is_active=picks_list.is_active,
        display_order=picks_list.display_order,
        created_by_id=picks_list.created_by_id,
        items_count=0,
    )


@router.put("/{list_id}", response_model=StaffPicksListResponse)
async def update_staff_picks_list(
    list_id: int,
    list_in: StaffPicksListUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> StaffPicksListResponse:
    """Update a staff picks list (author or admin only)."""
    query = select(StaffPicksList).where(StaffPicksList.id == list_id)
    result = await db.execute(query)
    picks_list = result.scalar_one_or_none()
    if not picks_list:
        raise HTTPException(status_code=404, detail="Staff picks list not found")

    is_admin = staff_user.role in ("ADMIN", "SUPER_ADMIN")
    if picks_list.created_by_id != staff_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="You can only edit your own lists")

    update_data = list_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(picks_list, field, value)

    await db.commit()
    await db.refresh(picks_list)
    return StaffPicksListResponse(
        id=picks_list.id,
        title=picks_list.title,
        description=picks_list.description,
        is_active=picks_list.is_active,
        display_order=picks_list.display_order,
        created_by_id=picks_list.created_by_id,
        items_count=0,
    )


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_staff_picks_list(
    list_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete a staff picks list (author or admin only)."""
    query = select(StaffPicksList).where(StaffPicksList.id == list_id)
    result = await db.execute(query)
    picks_list = result.scalar_one_or_none()
    if not picks_list:
        raise HTTPException(status_code=404, detail="Staff picks list not found")

    is_admin = staff_user.role in ("ADMIN", "SUPER_ADMIN")
    if picks_list.created_by_id != staff_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="You can only delete your own lists")

    await db.delete(picks_list)
    await db.commit()


# ============================================================================
# Item Endpoints
# ============================================================================


@router.post("/{list_id}/items", response_model=StaffPicksItemResponse, status_code=status.HTTP_201_CREATED)
async def add_item_to_picks_list(
    list_id: int,
    item_in: StaffPicksItemCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> StaffPicksItemResponse:
    """Add an item to a staff picks list."""
    # Verify list exists and user has permission
    query = select(StaffPicksList).where(StaffPicksList.id == list_id)
    result = await db.execute(query)
    picks_list = result.scalar_one_or_none()
    if not picks_list:
        raise HTTPException(status_code=404, detail="Staff picks list not found")

    is_admin = staff_user.role in ("ADMIN", "SUPER_ADMIN")
    if picks_list.created_by_id != staff_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="You can only edit your own lists")

    # Verify catalog item exists
    catalog_query = select(CatalogItem).where(CatalogItem.id == item_in.catalog_item_id)
    catalog_result = await db.execute(catalog_query)
    catalog_item = catalog_result.scalar_one_or_none()
    if not catalog_item:
        raise HTTPException(status_code=404, detail="Catalog item not found")

    picks_item = StaffPicksItem(
        list_id=list_id,
        catalog_item_id=item_in.catalog_item_id,
        staff_notes=item_in.staff_notes,
        display_order=item_in.display_order,
        added_by_id=staff_user.id,
    )
    db.add(picks_item)
    await db.commit()
    await db.refresh(picks_item, attribute_names=["catalog_item"])

    return StaffPicksItemResponse(
        id=picks_item.id,
        catalog_item_id=picks_item.catalog_item_id,
        catalog_item=CatalogItemResponse(
            id=catalog_item.id,
            title=catalog_item.title,
            cover_url=catalog_item.cover_url,
            item_type=catalog_item.item_type,
        ),
        staff_notes=picks_item.staff_notes,
        display_order=picks_item.display_order,
        added_at=picks_item.added_at,
        added_by_id=picks_item.added_by_id,
    )


@router.delete("/{list_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_from_picks_list(
    list_id: int,
    item_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Remove an item from a staff picks list."""
    # Verify list exists and user has permission
    query = select(StaffPicksList).where(StaffPicksList.id == list_id)
    result = await db.execute(query)
    picks_list = result.scalar_one_or_none()
    if not picks_list:
        raise HTTPException(status_code=404, detail="Staff picks list not found")

    is_admin = staff_user.role in ("ADMIN", "SUPER_ADMIN")
    if picks_list.created_by_id != staff_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="You can only edit your own lists")

    # Get and delete the item
    item_query = select(StaffPicksItem).where(
        StaffPicksItem.id == item_id, StaffPicksItem.list_id == list_id
    )
    item_result = await db.execute(item_query)
    picks_item = item_result.scalar_one_or_none()
    if not picks_item:
        raise HTTPException(status_code=404, detail="Item not found in this list")

    await db.delete(picks_item)
    await db.commit()


# ============================================================================
# Public Endpoints
# ============================================================================


@router.get("/public/lists", response_model=List[StaffPicksListResponse])
async def get_public_staff_picks_lists(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[StaffPicksListResponse]:
    """Get all active staff picks lists (public)."""
    items_count_subq = (
        select(func.count(StaffPicksItem.id))
        .where(StaffPicksItem.list_id == StaffPicksList.id)
        .correlate(StaffPicksList)
        .scalar_subquery()
    )
    query = (
        select(StaffPicksList, items_count_subq.label("items_count"))
        .where(StaffPicksList.is_active == True)
        .order_by(StaffPicksList.display_order)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()
    return [
        StaffPicksListResponse(
            id=l.id,
            title=l.title,
            description=l.description,
            is_active=l.is_active,
            display_order=l.display_order,
            created_by_id=l.created_by_id,
            items_count=items_count,
        )
        for l, items_count in rows
    ]


@router.get("/public/{list_id}", response_model=StaffPicksListDetailResponse)
async def get_public_staff_picks_list(
    list_id: int,
    db: AsyncSession = Depends(get_db),
) -> StaffPicksListDetailResponse:
    """Get a specific active staff picks list with all items (public)."""
    query = (
        select(StaffPicksList)
        .options(
            selectinload(StaffPicksList.items).selectinload(StaffPicksItem.catalog_item)
        )
        .where(StaffPicksList.id == list_id, StaffPicksList.is_active == True)
    )
    result = await db.execute(query)
    picks_list = result.scalar_one_or_none()
    if not picks_list:
        raise HTTPException(status_code=404, detail="Staff picks list not found")

    items = [
        StaffPicksItemResponse(
            id=item.id,
            catalog_item_id=item.catalog_item_id,
            catalog_item=CatalogItemResponse(
                id=item.catalog_item.id,
                title=item.catalog_item.title,
                author=item.catalog_item.author,
                cover_url=item.catalog_item.cover_url,
                item_type=item.catalog_item.item_type,
                status=_status_value(item.catalog_item.status),
            ),
            staff_notes=item.staff_notes,
            display_order=item.display_order,
            added_at=item.added_at,
            added_by_id=item.added_by_id,
        )
        for item in (picks_list.items or [])
    ]

    return StaffPicksListDetailResponse(
        id=picks_list.id,
        title=picks_list.title,
        description=picks_list.description,
        is_active=picks_list.is_active,
        display_order=picks_list.display_order,
        created_by_id=picks_list.created_by_id,
        items_count=len(items),
        items=items,
    )
