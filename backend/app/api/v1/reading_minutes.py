# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Reading Minutes API for children.
Instead of monetary fines, children earn reading minutes they need to "pay off"
by logging their reading time (honor system).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.permission import RoleSettings
from ...models.reading import ReadingLog, ReadingLogStatus
from ...models.user import User, UserRole
from .auth import get_current_user

router = APIRouter(prefix="/reading-minutes", tags=["reading-minutes"])

# Maximum total reading minutes that can be logged (prevents unbounded accumulation)
# 10,000 minutes = ~167 hours - a reasonable lifetime cap for a child
MAX_TOTAL_READING_MINUTES = 10000


class ReadingMinutesStatus(BaseModel):
    minutes_owed: int
    minutes_logged: int
    minutes_remaining: int
    is_clear: bool
    message: str


class LogReadingRequest(BaseModel):
    minutes: int = Field(..., ge=5, le=120, description="Minutes read (5-120)")
    note: str | None = Field(None, max_length=200, description="Optional note")


class LogReadingResponse(BaseModel):
    minutes_logged: int
    minutes_remaining: int
    is_clear: bool
    message: str


class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    minutes_logged: int
    is_you: bool


@router.get("/status", response_model=ReadingMinutesStatus)
async def get_reading_minutes_status(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get current reading minutes status."""
    settings_result = await db.execute(
        select(RoleSettings).where(RoleSettings.role == current_user.role)
    )
    settings = settings_result.scalar_one_or_none()

    if not settings or not settings.use_reading_minutes:
        return ReadingMinutesStatus(
            minutes_owed=0,
            minutes_logged=0,
            minutes_remaining=0,
            is_clear=True,
            message="Your account does not use reading minutes.",
        )

    remaining = max(
        0, current_user.reading_minutes_owed - current_user.reading_minutes_logged
    )
    is_clear = remaining == 0

    if is_clear:
        msg = "You're all caught up! No reading minutes owed."
    else:
        msg = f"You have {remaining} minutes of reading to log."

    return ReadingMinutesStatus(
        minutes_owed=current_user.reading_minutes_owed,
        minutes_logged=current_user.reading_minutes_logged,
        minutes_remaining=remaining,
        is_clear=is_clear,
        message=msg,
    )


@router.post("/log", response_model=LogReadingResponse, status_code=status.HTTP_201_CREATED)
async def log_reading_time(
    request: LogReadingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Log reading time to pay off reading minutes (honor system)."""
    settings_result = await db.execute(
        select(RoleSettings).where(RoleSettings.role == current_user.role)
    )
    settings = settings_result.scalar_one_or_none()

    if not settings or not settings.use_reading_minutes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account does not use reading minutes.",
        )

    # Check if user has minutes owed
    remaining = current_user.reading_minutes_owed - current_user.reading_minutes_logged
    if remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You don't have any reading minutes to pay off. You're all caught up!",
        )

    # Cap the logged minutes to what's actually owed
    minutes_to_log = min(request.minutes, remaining)

    # Check if user would exceed the total cap (PR #69 validation)
    if current_user.reading_minutes_logged + minutes_to_log > MAX_TOTAL_READING_MINUTES:
        # Calculate how many minutes they can still log
        available = MAX_TOTAL_READING_MINUTES - current_user.reading_minutes_logged
        if available <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You've reached the maximum of {MAX_TOTAL_READING_MINUTES:,} logged minutes.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot log {minutes_to_log} minutes. You can only log up to {available} more minutes.",
        )

    # Use atomic increment to prevent race conditions (lost updates from PR #69)
    # This ensures concurrent operations don't overwrite each other
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(reading_minutes_logged=User.reading_minutes_logged + minutes_to_log)
    )

    # Create audit trail entry (auto-approved for honor system, from main)
    reading_log = ReadingLog(
        user_id=current_user.id,
        minutes=minutes_to_log,
        notes=request.note,
        reading_date=datetime.now(timezone.utc),
        status=ReadingLogStatus.approved,
        reviewed_at=datetime.now(timezone.utc),  # Auto-approved timestamp
    )
    db.add(reading_log)

    await db.commit()
    await db.refresh(current_user)

    remaining = max(
        0, current_user.reading_minutes_owed - current_user.reading_minutes_logged
    )
    is_clear = remaining == 0

    if is_clear:
        msg = f"Amazing! You logged {minutes_to_log} minutes and you're all caught up!"
    else:
        msg = f"Great job! You logged {minutes_to_log} minutes. {remaining} minutes remaining."

    return LogReadingResponse(
        minutes_logged=minutes_to_log,
        minutes_remaining=remaining,
        is_clear=is_clear,
        message=msg,
    )


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_reading_leaderboard(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get top readers leaderboard."""
    result = await db.execute(
        select(User)
        .where(User.role == UserRole.CHILD)
        .where(User.reading_minutes_logged > 0)
        .order_by(User.reading_minutes_logged.desc())
        .limit(10)
    )
    users = result.scalars().all()

    return [
        {
            "rank": i + 1,
            "name": f"Reader #{i + 1}" if u.role == UserRole.CHILD else f"{u.first_name} {u.last_name[0]}.",
            "minutes_logged": u.reading_minutes_logged,
            "is_you": u.id == current_user.id,
        }
        for i, u in enumerate(users)
    ]



