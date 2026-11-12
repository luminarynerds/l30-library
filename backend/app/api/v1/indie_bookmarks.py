# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Indie ebook bookmarks -- save for later / reading list."""
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.indie_bookmark import IndieBookmark
from ...models.user import User
from ..v1.auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/indie/bookmarks", tags=["indie-bookmarks"])


class BookmarkResponse(BaseModel):
    ebook_id: int
    created_at: str


class BookmarkStatusResponse(BaseModel):
    bookmarked: bool


class BookmarkListResponse(BaseModel):
    items: list[BookmarkResponse]
    total: int


@router.get("", response_model=BookmarkListResponse)
async def list_bookmarks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all bookmarked ebook IDs for current patron."""
    stmt = (
        select(IndieBookmark)
        .where(IndieBookmark.user_id == current_user.id)
        .order_by(IndieBookmark.created_at.desc())
    )
    result = await db.execute(stmt)
    bookmarks = result.scalars().all()
    return BookmarkListResponse(
        items=[
            BookmarkResponse(
                ebook_id=b.ebook_id,
                created_at=b.created_at.isoformat(),
            )
            for b in bookmarks
        ],
        total=len(bookmarks),
    )


@router.get("/{ebook_id}/status", response_model=BookmarkStatusResponse)
async def get_bookmark_status(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if a specific ebook is bookmarked."""
    stmt = select(func.count()).where(
        IndieBookmark.user_id == current_user.id,
        IndieBookmark.ebook_id == ebook_id,
    )
    result = await db.execute(stmt)
    count = result.scalar_one()
    return BookmarkStatusResponse(bookmarked=count > 0)


@router.post("/{ebook_id}", status_code=status.HTTP_201_CREATED)
async def add_bookmark(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save an ebook to reading list."""
    stmt = pg_insert(IndieBookmark).values(
        user_id=current_user.id,
        ebook_id=ebook_id,
    ).on_conflict_do_nothing(constraint="uq_indie_bookmark")
    await db.execute(stmt)
    await db.commit()
    return {"bookmarked": True, "ebook_id": ebook_id}


@router.delete("/{ebook_id}", status_code=status.HTTP_200_OK)
async def remove_bookmark(
    ebook_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an ebook from reading list."""
    stmt = delete(IndieBookmark).where(
        IndieBookmark.user_id == current_user.id,
        IndieBookmark.ebook_id == ebook_id,
    )
    await db.execute(stmt)
    await db.commit()
    return {"bookmarked": False, "ebook_id": ebook_id}
