# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron-facing reading list endpoints."""
from app.core.logging import get_logger
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.catalog import CatalogItem
from ...models.reading_list import ListItem, ReadingList
from ...models.user import User
from ...schemas.favorites import (
    ListItemCreate,
    ListItemResponse,
    ReadingListCreate,
    ReadingListResponse,
    ReadingListUpdate,
    ReadingListWithItems,
)
from ..v1.auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/reading-lists/me", tags=["patron-reading-lists"])

DEFAULT_LIST_NAME = "To Read"


def _generate_token() -> str:
    return secrets.token_urlsafe(24)[:32]


async def _ensure_default_list(user_id: int, db: AsyncSession) -> None:
    count_stmt = select(func.count(ReadingList.id)).where(ReadingList.user_id == user_id)
    result = await db.execute(count_stmt)
    if result.scalar() == 0:
        default = ReadingList(
            user_id=user_id,
            name=DEFAULT_LIST_NAME,
            description="Your default reading list",
            is_public=False,
        )
        db.add(default)
        await db.commit()


async def _get_own_list(list_id: int, user_id: int, db: AsyncSession) -> ReadingList:
    stmt = select(ReadingList).where(ReadingList.id == list_id)
    result = await db.execute(stmt)
    lst = result.scalar_one_or_none()
    if not lst or lst.user_id != user_id:
        raise HTTPException(status_code=404, detail="List not found")
    return lst


@router.get("", response_model=list[ReadingListResponse])
async def get_my_lists(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's reading lists with item counts."""
    await _ensure_default_list(user.id, db)
    stmt = (
        select(ReadingList, func.count(ListItem.id).label("item_count"))
        .outerjoin(ListItem)
        .where(ReadingList.user_id == user.id)
        .group_by(ReadingList.id)
        .order_by(ReadingList.updated_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        ReadingListResponse(
            id=lst.id,
            name=lst.name,
            description=lst.description,
            is_public=lst.is_public,
            created_at=lst.created_at,
            item_count=count,
        )
        for lst, count in rows
    ]


@router.post("", response_model=ReadingListResponse, status_code=201)
async def create_list(
    body: ReadingListCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new reading list."""
    new_list = ReadingList(
        user_id=user.id,
        name=body.name,
        description=body.description,
        is_public=body.is_public,
    )
    if body.is_public:
        new_list.share_token = _generate_token()
    db.add(new_list)
    await db.commit()
    await db.refresh(new_list)
    return ReadingListResponse(
        id=new_list.id,
        name=new_list.name,
        description=new_list.description,
        is_public=new_list.is_public,
        created_at=new_list.created_at,
        item_count=0,
    )


@router.get("/containing/{catalog_item_id}", response_model=list[int])
async def lists_containing_item(
    catalog_item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return list IDs that contain a given catalog item (for frontend checkmarks)."""
    stmt = (
        select(ListItem.list_id)
        .join(ReadingList)
        .where(
            ReadingList.user_id == user.id,
            ListItem.catalog_item_id == catalog_item_id,
        )
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


@router.get("/{list_id}", response_model=ReadingListWithItems)
async def get_list(
    list_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a reading list with all items and catalog details."""
    stmt = (
        select(ReadingList)
        .options(
            selectinload(ReadingList.items).selectinload(ListItem.catalog_item)
        )
        .where(ReadingList.id == list_id)
    )
    result = await db.execute(stmt)
    lst = result.scalar_one_or_none()
    if not lst or lst.user_id != user.id:
        raise HTTPException(status_code=404, detail="List not found")
    return lst


@router.put("/{list_id}", response_model=ReadingListResponse)
async def update_list(
    list_id: int,
    body: ReadingListUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update list name, description, or public visibility."""
    lst = await _get_own_list(list_id, user.id, db)

    if body.name is not None:
        lst.name = body.name
    if body.description is not None:
        lst.description = body.description
    if body.is_public is not None:
        lst.is_public = body.is_public
        if body.is_public and not lst.share_token:
            lst.share_token = _generate_token()

    await db.commit()
    await db.refresh(lst)

    count_stmt = select(func.count(ListItem.id)).where(ListItem.list_id == list_id)
    count_result = await db.execute(count_stmt)
    item_count = count_result.scalar() or 0

    return ReadingListResponse(
        id=lst.id,
        name=lst.name,
        description=lst.description,
        is_public=lst.is_public,
        created_at=lst.created_at,
        item_count=item_count,
    )


@router.delete("/{list_id}", status_code=204)
async def delete_list(
    list_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a reading list. Cannot delete the default 'To Read' list."""
    lst = await _get_own_list(list_id, user.id, db)
    if lst.name == DEFAULT_LIST_NAME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the default 'To Read' list",
        )
    await db.delete(lst)
    await db.commit()


@router.post("/{list_id}/items", status_code=201)
async def add_item(
    list_id: int,
    body: ListItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a catalog item to a reading list."""
    lst = await _get_own_list(list_id, user.id, db)

    # Verify catalog item exists
    cat_stmt = select(CatalogItem.id).where(CatalogItem.id == body.catalog_item_id)
    cat_result = await db.execute(cat_stmt)
    if not cat_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Catalog item not found")

    # Check for duplicate
    dup_stmt = select(ListItem).where(
        ListItem.list_id == list_id,
        ListItem.catalog_item_id == body.catalog_item_id,
    )
    dup_result = await db.execute(dup_stmt)
    if dup_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Item already in list")

    item = ListItem(list_id=list_id, catalog_item_id=body.catalog_item_id)
    db.add(item)
    await db.commit()
    return {"catalog_item_id": body.catalog_item_id, "added": True}


@router.delete("/{list_id}/items/{catalog_item_id}", status_code=204)
async def remove_item(
    list_id: int,
    catalog_item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a catalog item from a reading list."""
    await _get_own_list(list_id, user.id, db)
    del_stmt = delete(ListItem).where(
        ListItem.list_id == list_id,
        ListItem.catalog_item_id == catalog_item_id,
    )
    await db.execute(del_stmt)
    await db.commit()
