# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Admin endpoints for managing all reading lists.

Staff can view, edit, toggle visibility, and delete any reading list.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.reading_list import ReadingList, ListItem
from ...models.user import User
from .dependencies import require_staff

router = APIRouter(prefix="/admin/reading-lists", tags=["admin-reading-lists"])


class AdminReadingListItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_public: bool
    item_count: int = 0
    owner_name: str = ""
    owner_email: str = ""
    owner_id: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class AdminReadingListUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


@router.get("", response_model=List[AdminReadingListItem])
async def list_all_reading_lists(
    public_only: bool = Query(False),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List all reading lists with owner info and item counts."""
    query = (
        select(
            ReadingList,
            func.count(ListItem.id).label("item_count"),
            User.email.label("owner_email"),
            # Names encrypted; select columns (auto-decrypted) and concat app-side.
            User.first_name.label("owner_first_name"),
            User.last_name.label("owner_last_name"),
        )
        .join(User, ReadingList.user_id == User.id)
        .outerjoin(ListItem, ListItem.list_id == ReadingList.id)
        .group_by(ReadingList.id, User.email, User.first_name, User.last_name)
    )

    if public_only:
        query = query.where(ReadingList.is_public == True)

    if search:
        query = query.where(ReadingList.name.ilike(f"%{search}%"))

    query = query.order_by(ReadingList.name)
    result = await db.execute(query)
    rows = result.all()

    return [
        AdminReadingListItem(
            id=row[0].id,
            name=row[0].name,
            description=row[0].description,
            is_public=row[0].is_public,
            item_count=row[1],
            owner_email=row[2] or "",
            owner_name=f"{row[3] or ''} {row[4] or ''}".strip(),
            owner_id=row[0].user_id,
            created_at=row[0].created_at.isoformat() if row[0].created_at else None,
            updated_at=row[0].updated_at.isoformat() if row[0].updated_at else None,
        )
        for row in rows
    ]


@router.patch("/{list_id}", response_model=AdminReadingListItem)
async def update_reading_list(
    list_id: int,
    data: AdminReadingListUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update any reading list (name, description, visibility)."""
    result = await db.execute(select(ReadingList).where(ReadingList.id == list_id))
    reading_list = result.scalar_one_or_none()
    if not reading_list:
        raise HTTPException(status_code=404, detail="Reading list not found")

    if data.name is not None:
        reading_list.name = data.name
    if data.description is not None:
        reading_list.description = data.description
    if data.is_public is not None:
        reading_list.is_public = data.is_public

    await db.commit()
    await db.refresh(reading_list)

    # Re-query with owner info
    full = await db.execute(
        select(
            ReadingList,
            func.count(ListItem.id).label("item_count"),
            User.email,
            User.first_name,
            User.last_name,
        )
        .join(User, ReadingList.user_id == User.id)
        .outerjoin(ListItem, ListItem.list_id == ReadingList.id)
        .where(ReadingList.id == list_id)
        .group_by(ReadingList.id, User.email, User.first_name, User.last_name)
    )
    row = full.one()
    return AdminReadingListItem(
        id=row[0].id,
        name=row[0].name,
        description=row[0].description,
        is_public=row[0].is_public,
        item_count=row[1],
        owner_email=row[2] or "",
        owner_name=f"{row[3] or ''} {row[4] or ''}".strip(),
        owner_id=row[0].user_id,
        created_at=row[0].created_at.isoformat() if row[0].created_at else None,
        updated_at=row[0].updated_at.isoformat() if row[0].updated_at else None,
    )


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reading_list(
    list_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Delete any reading list."""
    result = await db.execute(select(ReadingList).where(ReadingList.id == list_id))
    reading_list = result.scalar_one_or_none()
    if not reading_list:
        raise HTTPException(status_code=404, detail="Reading list not found")

    await db.delete(reading_list)
    await db.commit()
