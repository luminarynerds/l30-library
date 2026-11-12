# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public youth page API endpoints."""
from app.core.logging import get_logger
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from .auth import get_current_user
from ...models.user import User

router = APIRouter(prefix="/youth", tags=["youth"])
logger = get_logger(__name__)


class ActiveReadingProgram(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    program_type: str
    age_group: Optional[str] = None
    start_date: date
    end_date: date
    enrollment_count: int
    reading_goal_type: Optional[str] = None
    reading_goal_value: Optional[int] = None


@router.get("/active-reading-programs", response_model=List[ActiveReadingProgram])
async def get_active_reading_programs(db: AsyncSession = Depends(get_db)):
    """Return currently active reading programs for the youth page banner."""
    try:
        result = await db.execute(
            text("""
                SELECT
                    rp.id, rp.name, rp.description,
                    rp.program_type, rp.age_group,
                    rp.start_date, rp.end_date,
                    rp.reading_goal_type, rp.reading_goal_value,
                    (SELECT COUNT(*) FROM reading_registrations rr
                     WHERE rr.program_id = rp.id) AS enrollment_count
                FROM reading_programs rp
                WHERE rp.is_active = true
                  AND rp.start_date <= :today
                  AND rp.end_date >= :today
                ORDER BY rp.end_date ASC
            """),
            {"today": date.today()},
        )
        rows = result.fetchall()
        return [
            ActiveReadingProgram(
                id=row[0], name=row[1], description=row[2],
                program_type=row[3], age_group=row[4],
                start_date=row[5], end_date=row[6],
                reading_goal_type=row[7], reading_goal_value=row[8],
                enrollment_count=row[9] or 0,
            )
            for row in rows
        ]
    except Exception:
        logger.exception("Failed to load active reading programs")
        return []


class UpcomingYouthEvent(BaseModel):
    id: int
    title: str
    program_date: date
    start_time: str
    end_time: Optional[str] = None
    location_name: Optional[str] = None
    audience: str
    registration_count: int
    capacity: Optional[int] = None


@router.get("/upcoming-events", response_model=List[UpcomingYouthEvent])
async def get_upcoming_youth_events(
    limit: int = Query(default=4, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
):
    """Return upcoming youth-relevant events for the youth page."""
    try:
        result = await db.execute(
            text("""
                SELECT p.id, p.title, p.program_date, p.start_time, p.end_time,
                       p.location_name, p.audience, p.max_capacity,
                       (SELECT COUNT(*) FROM program_registrations pr
                        WHERE pr.program_id = p.id
                          AND pr.status IN ('registered', 'waitlisted'))
                FROM programs p
                WHERE p.audience IN ('children', 'teen', 'family', 'all_ages')
                  AND p.status IN ('planned', 'scheduled')
                  AND p.program_date >= :today
                ORDER BY p.program_date ASC, p.start_time ASC
                LIMIT :lim
            """),
            {"today": date.today(), "lim": limit},
        )
        rows = result.fetchall()
        return [
            UpcomingYouthEvent(
                id=row[0], title=row[1], program_date=row[2],
                start_time=str(row[3])[:5] if row[3] else "",
                end_time=str(row[4])[:5] if row[4] else None,
                location_name=row[5], audience=row[6],
                registration_count=row[8] or 0,
                capacity=row[7],
            )
            for row in rows
        ]
    except Exception:
        logger.exception("Failed to load upcoming youth events")
        return []


class MyReadingProgress(BaseModel):
    enrolled_programs: List[dict]
    books_read_count: int
    total_reading_minutes: int


@router.get("/my-reading-progress", response_model=MyReadingProgress)
async def get_my_reading_progress(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return reading progress for the authenticated youth patron."""
    enrolled = []
    books_read = 0
    total_minutes = 0
    try:
        result = await db.execute(
            text("""
                SELECT rp.name, rp.reading_goal_type, rp.reading_goal_value,
                       rp.start_date, rp.end_date,
                       COALESCE(
                           (SELECT SUM(rl.minutes_read) FROM reading_logs rl
                            WHERE rl.user_id = :uid AND rl.created_at >= rp.start_date
                            AND rl.created_at <= rp.end_date), 0
                       ) AS progress_minutes,
                       COALESCE(
                           (SELECT COUNT(*) FROM reading_logs rl
                            WHERE rl.user_id = :uid AND rl.created_at >= rp.start_date
                            AND rl.created_at <= rp.end_date), 0
                       ) AS log_count
                FROM reading_programs rp
                JOIN reading_registrations rr ON rr.program_id = rp.id
                WHERE rr.user_id = :uid
                  AND rp.is_active = true
                  AND rp.end_date >= :today
                ORDER BY rp.end_date ASC
            """),
            {"uid": user.id, "today": date.today()},
        )
        for row in result.fetchall():
            enrolled.append({
                "program_name": row[0],
                "goal_type": row[1],
                "goal_target": row[2],
                "start_date": str(row[3]),
                "end_date": str(row[4]),
                "progress_minutes": row[5],
                "log_count": row[6],
            })
            total_minutes += row[5] or 0
            books_read += row[6] or 0
    except Exception:
        logger.exception("Failed to load reading progress")

    return MyReadingProgress(
        enrolled_programs=enrolled,
        books_read_count=books_read,
        total_reading_minutes=total_minutes,
    )
