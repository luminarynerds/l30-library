# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Indie reading list endpoints."""
from app.core.logging import get_logger
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.indie_reading_list import IndieReadingList, IndieReadingListItem
from ...models.user import User
from ..v1.auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/indie/reading-lists", tags=["indie-reading-lists"])


# -- Schemas --

class ListSummary(BaseModel):
    id: int
    name: str
    description: str | None
    is_public: bool
    share_token: str | None
    item_count: int
    created_at: str
    updated_at: str


class ListItemResponse(BaseModel):
    ebook_id: int
    note: str | None
    added_at: str


class ListDetailResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_public: bool
    share_token: str | None
    creator_name: str
    items: list[ListItemResponse]
    created_at: str
    updated_at: str


class CreateListRequest(BaseModel):
    name: str = Field(max_length=200)
    description: str | None = None


class UpdateListRequest(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    is_public: bool | None = None


class AddItemRequest(BaseModel):
    ebook_id: int
    note: str | None = None


# -- Helpers --

def _generate_token() -> str:
    return secrets.token_urlsafe(24)[:32]


def _creator_name(user: User) -> str:
    if hasattr(user, "display_name") and user.display_name:
        return user.display_name
    if hasattr(user, "username") and user.username:
        return user.username
    return "Anonymous"


# -- Endpoints --

@router.get("", response_model=list[ListSummary])
async def get_my_lists(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's reading lists."""
    stmt = (
        select(IndieReadingList, func.count(IndieReadingListItem.id).label("item_count"))
        .outerjoin(IndieReadingListItem)
        .where(IndieReadingList.user_id == user.id)
        .group_by(IndieReadingList.id)
        .order_by(IndieReadingList.updated_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        ListSummary(
            id=lst.id, name=lst.name, description=lst.description,
            is_public=lst.is_public, share_token=lst.share_token,
            item_count=count, created_at=lst.created_at.isoformat(),
            updated_at=lst.updated_at.isoformat(),
        )
        for lst, count in rows
    ]


@router.post("", response_model=ListSummary, status_code=201)
async def create_list(
    body: CreateListRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new reading list (starts private)."""
    new_list = IndieReadingList(
        user_id=user.id,
        name=body.name,
        description=body.description,
        is_public=False,
    )
    db.add(new_list)
    await db.commit()
    await db.refresh(new_list)
    return ListSummary(
        id=new_list.id, name=new_list.name, description=new_list.description,
        is_public=False, share_token=None, item_count=0,
        created_at=new_list.created_at.isoformat(),
        updated_at=new_list.updated_at.isoformat(),
    )


@router.get("/public", response_model=list[ListSummary])
async def browse_public_lists(
    sort: str = Query("newest", pattern="^(newest|most_items)$"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Browse public reading lists."""
    stmt = (
        select(IndieReadingList, func.count(IndieReadingListItem.id).label("item_count"))
        .outerjoin(IndieReadingListItem)
        .where(IndieReadingList.is_public == True)
        .group_by(IndieReadingList.id)
    )
    if sort == "most_items":
        stmt = stmt.order_by(func.count(IndieReadingListItem.id).desc())
    else:
        stmt = stmt.order_by(IndieReadingList.created_at.desc())
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    rows = result.all()
    return [
        ListSummary(
            id=lst.id, name=lst.name, description=lst.description,
            is_public=True, share_token=lst.share_token,
            item_count=count, created_at=lst.created_at.isoformat(),
            updated_at=lst.updated_at.isoformat(),
        )
        for lst, count in rows
    ]


@router.get("/shared/{share_token}", response_model=ListDetailResponse)
async def get_shared_list(
    share_token: str,
    db: AsyncSession = Depends(get_db),
):
    """View a shared reading list (no auth required)."""
    stmt = (
        select(IndieReadingList)
        .options(selectinload(IndieReadingList.items), selectinload(IndieReadingList.user))
        .where(IndieReadingList.share_token == share_token, IndieReadingList.is_public == True)
    )
    result = await db.execute(stmt)
    lst = result.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    return ListDetailResponse(
        id=lst.id, name=lst.name, description=lst.description,
        is_public=True, share_token=lst.share_token,
        creator_name=_creator_name(lst.user),
        items=[ListItemResponse(ebook_id=i.ebook_id, note=i.note, added_at=i.added_at.isoformat()) for i in lst.items],
        created_at=lst.created_at.isoformat(), updated_at=lst.updated_at.isoformat(),
    )


@router.get("/{list_id}", response_model=ListDetailResponse)
async def get_list(
    list_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a reading list with all items. Owner only for private lists."""
    stmt = (
        select(IndieReadingList)
        .options(selectinload(IndieReadingList.items), selectinload(IndieReadingList.user))
        .where(IndieReadingList.id == list_id)
    )
    result = await db.execute(stmt)
    lst = result.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    if not lst.is_public and lst.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return ListDetailResponse(
        id=lst.id, name=lst.name, description=lst.description,
        is_public=lst.is_public, share_token=lst.share_token,
        creator_name=_creator_name(lst.user),
        items=[ListItemResponse(ebook_id=i.ebook_id, note=i.note, added_at=i.added_at.isoformat()) for i in lst.items],
        created_at=lst.created_at.isoformat(), updated_at=lst.updated_at.isoformat(),
    )


@router.put("/{list_id}", response_model=ListSummary)
async def update_list(
    list_id: int,
    body: UpdateListRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a reading list. Generates share_token on first public toggle."""
    stmt = select(IndieReadingList).where(IndieReadingList.id == list_id)
    result = await db.execute(stmt)
    lst = result.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    if lst.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

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

    count_stmt = select(func.count(IndieReadingListItem.id)).where(IndieReadingListItem.list_id == list_id)
    count_result = await db.execute(count_stmt)
    item_count = count_result.scalar() or 0

    return ListSummary(
        id=lst.id, name=lst.name, description=lst.description,
        is_public=lst.is_public, share_token=lst.share_token,
        item_count=item_count, created_at=lst.created_at.isoformat(),
        updated_at=lst.updated_at.isoformat(),
    )


@router.delete("/{list_id}", status_code=204)
async def delete_list(
    list_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a reading list and all its items."""
    stmt = select(IndieReadingList).where(IndieReadingList.id == list_id)
    result = await db.execute(stmt)
    lst = result.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    if lst.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.delete(lst)
    await db.commit()


@router.post("/{list_id}/items", status_code=201)
async def add_item(
    list_id: int,
    body: AddItemRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add an ebook to a reading list."""
    stmt = select(IndieReadingList).where(IndieReadingList.id == list_id)
    result = await db.execute(stmt)
    lst = result.scalar_one_or_none()
    if not lst or lst.user_id != user.id:
        raise HTTPException(status_code=404, detail="List not found")

    dup_stmt = select(IndieReadingListItem).where(
        IndieReadingListItem.list_id == list_id,
        IndieReadingListItem.ebook_id == body.ebook_id,
    )
    dup_result = await db.execute(dup_stmt)
    if dup_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Book already in list")

    item = IndieReadingListItem(list_id=list_id, ebook_id=body.ebook_id, note=body.note)
    db.add(item)
    await db.commit()
    return {"ebook_id": body.ebook_id, "added": True}


@router.delete("/{list_id}/items/{ebook_id}", status_code=204)
async def remove_item(
    list_id: int,
    ebook_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an ebook from a reading list."""
    list_stmt = select(IndieReadingList).where(IndieReadingList.id == list_id)
    list_result = await db.execute(list_stmt)
    lst = list_result.scalar_one_or_none()
    if not lst or lst.user_id != user.id:
        raise HTTPException(status_code=404, detail="List not found")

    del_stmt = delete(IndieReadingListItem).where(
        IndieReadingListItem.list_id == list_id,
        IndieReadingListItem.ebook_id == ebook_id,
    )
    await db.execute(del_stmt)
    await db.commit()

