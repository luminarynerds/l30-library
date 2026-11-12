# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Indie ebook reading progress endpoints."""
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.indie_reading_progress import IndieReadingProgress
from ...models.indie_ebook_borrow import IndieEbookBorrow, BorrowStatus
from ...models.user import User
from ..v1.auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/indie/reading-progress", tags=["indie-reading-progress"])


class ProgressResponse(BaseModel):
    ebook_id: int
    percent: int
    current_position: str | None
    updated_at: str


class ProgressUpdate(BaseModel):
    percent: int = Field(ge=0, le=100)
    current_position: str | None = None


class ActiveProgressItem(BaseModel):
    ebook_id: int
    percent: int
    current_position: str | None
    updated_at: str


@router.get("/active", response_model=list[ActiveProgressItem])
async def get_active_progress(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all reading progress for user active borrows."""
    stmt = (
        select(IndieReadingProgress)
        .join(IndieEbookBorrow, (
            (IndieEbookBorrow.ebook_id == IndieReadingProgress.ebook_id) &
            (IndieEbookBorrow.user_id == IndieReadingProgress.user_id) &
            (IndieEbookBorrow.status == BorrowStatus.active)
        ))
        .where(IndieReadingProgress.user_id == user.id)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        ActiveProgressItem(
            ebook_id=p.ebook_id,
            percent=p.percent,
            current_position=p.current_position,
            updated_at=p.updated_at.isoformat(),
        )
        for p in items
    ]


@router.get("/{ebook_id}", response_model=ProgressResponse)
async def get_progress(
    ebook_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get reading progress for a specific ebook."""
    stmt = select(IndieReadingProgress).where(
        IndieReadingProgress.user_id == user.id,
        IndieReadingProgress.ebook_id == ebook_id,
    )
    result = await db.execute(stmt)
    progress = result.scalar_one_or_none()
    if not progress:
        raise HTTPException(status_code=404, detail="No progress found")
    return ProgressResponse(
        ebook_id=progress.ebook_id,
        percent=progress.percent,
        current_position=progress.current_position,
        updated_at=progress.updated_at.isoformat(),
    )


@router.put("/{ebook_id}", response_model=ProgressResponse)
async def update_progress(
    ebook_id: int,
    body: ProgressUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upsert reading progress for an ebook."""
    stmt = pg_insert(IndieReadingProgress).values(
        user_id=user.id,
        ebook_id=ebook_id,
        percent=body.percent,
        current_position=body.current_position,
    ).on_conflict_do_update(
        constraint="uq_indie_reading_progress_user_ebook",
        set_=dict(percent=body.percent, current_position=body.current_position),
    ).returning(IndieReadingProgress)
    result = await db.execute(stmt)
    await db.commit()
    progress = result.scalar_one()
    return ProgressResponse(
        ebook_id=progress.ebook_id,
        percent=progress.percent,
        current_position=progress.current_position,
        updated_at=progress.updated_at.isoformat(),
    )
