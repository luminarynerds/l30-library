# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading goals API endpoints."""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.reading_goal import ReadingGoalProgress, ReadingGoalResponse, ReadingGoalSet
from ...services.reading_goal_service import ReadingGoalService
from .auth import get_current_user

router = APIRouter(tags=["reading-goals"])


@router.get("/reading-goals", response_model=List[ReadingGoalResponse])
async def get_reading_goals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all reading goals for the current user."""
    return await ReadingGoalService.get_goals(db, current_user.id)


@router.get("/reading-goals/{year}/progress", response_model=ReadingGoalProgress)
async def get_goal_progress(
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get reading goal progress for a specific year."""
    progress = await ReadingGoalService.get_progress(db, current_user.id, year)
    if not progress:
        raise HTTPException(status_code=404, detail="No goal set for this year")
    return ReadingGoalProgress(**progress)


@router.put("/reading-goals/{year}", response_model=ReadingGoalResponse)
async def set_reading_goal(
    year: int,
    data: ReadingGoalSet,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set or update a reading goal for a specific year."""
    current_year = datetime.now(timezone.utc).year
    if year < current_year - 1 or year > current_year + 1:
        raise HTTPException(
            status_code=400, detail="Year must be within one year of current year"
        )
    return await ReadingGoalService.set_goal(
        db, current_user.id, year, data.target_books
    )


@router.delete("/reading-goals/{year}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_reading_goal(
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a reading goal."""
    removed = await ReadingGoalService.remove_goal(db, current_user.id, year)
    if not removed:
        raise HTTPException(status_code=404, detail="No goal set for this year")
