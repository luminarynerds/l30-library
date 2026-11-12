# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Kids & Teen Services dashboard endpoint."""

from app.core.logging import get_logger
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ..dependencies import require_staff

router = APIRouter(prefix="/staff/kids", tags=["staff-kids-dashboard"])
logger = get_logger(__name__)

KIDS_AUDIENCES = ("children", "teen", "family", "all_ages")
ACTIVE_STATUSES = ("planned", "scheduled")


class KidsProgramSummary(BaseModel):
    id: int
    title: str
    program_date: date
    start_time: str
    end_time: Optional[str] = None
    location_name: Optional[str] = None
    audience: str
    registration_count: int
    capacity: Optional[int] = None
    notes: Optional[str] = None


class KidsReadingStats(BaseModel):
    active_program_count: int
    total_enrollments: int


class KidsDashboardResponse(BaseModel):
    next_program: Optional[KidsProgramSummary] = None
    reading_stats: KidsReadingStats
    upcoming_programs: List[KidsProgramSummary]
    school_visits: List[dict]


@router.get("/dashboard", response_model=KidsDashboardResponse)
async def get_kids_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> KidsDashboardResponse:
    """Aggregate dashboard data for kids & teen services."""

    upcoming_programs: List[KidsProgramSummary] = []
    next_program: Optional[KidsProgramSummary] = None
    try:
        result = await db.execute(
            text("""
                SELECT
                    p.id,
                    p.title,
                    p.program_date,
                    p.start_time,
                    p.end_time,
                    p.location_name,
                    p.audience,
                    p.max_capacity,
                    p.notes,
                    (SELECT COUNT(*) FROM program_registrations pr
                     WHERE pr.program_id = p.id
                     AND pr.status IN ('registered', 'waitlisted'))
                        AS registration_count
                FROM programs p
                WHERE p.audience::text = ANY(:audiences)
                  AND p.status::text = ANY(:statuses)
                  AND p.program_date >= :today
                ORDER BY p.program_date ASC, p.start_time ASC
                LIMIT 6
            """),
            {
                "audiences": list(KIDS_AUDIENCES),
                "statuses": list(ACTIVE_STATUSES),
                "today": date.today(),
            },
        )
        rows = result.fetchall()
        for row in rows:
            summary = KidsProgramSummary(
                id=row[0],
                title=row[1],
                program_date=row[2],
                start_time=str(row[3]) if row[3] else "",
                end_time=str(row[4]) if row[4] else None,
                location_name=row[5],
                audience=row[6],
                registration_count=row[9] or 0,
                capacity=row[7],
                notes=row[8],
            )
            upcoming_programs.append(summary)

        if upcoming_programs:
            next_program = upcoming_programs[0]
            upcoming_programs = upcoming_programs[1:6]
    except SQLAlchemyError:
        logger.exception("Failed to load kids upcoming programs")

    active_program_count = 0
    total_enrollments = 0
    try:
        rp_result = await db.execute(
            text("""
                SELECT
                    (SELECT COUNT(*) FROM reading_programs
                     WHERE is_active = true
                       AND start_date <= :today
                       AND end_date >= :today) AS active_count,
                    (SELECT COUNT(*) FROM reading_registrations rr
                     JOIN reading_programs rp ON rr.program_id = rp.id
                     WHERE rp.is_active = true
                       AND rp.start_date <= :today
                       AND rp.end_date >= :today) AS total_enrollments
            """),
            {"today": date.today()},
        )
        rp_row = rp_result.fetchone()
        if rp_row:
            active_program_count = rp_row[0] or 0
            total_enrollments = rp_row[1] or 0
    except SQLAlchemyError:
        logger.warning("Reading program tables not available, defaulting to zero")

    return KidsDashboardResponse(
        next_program=next_program,
        reading_stats=KidsReadingStats(
            active_program_count=active_program_count,
            total_enrollments=total_enrollments,
        ),
        upcoming_programs=upcoming_programs,
        school_visits=[],
    )


class WalkinResponse(BaseModel):
    registration_count: int


@router.post("/programs/{program_id}/walkin", response_model=WalkinResponse)
async def record_program_walkin(
    program_id: int,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
) -> WalkinResponse:
    """Record a walk-in attendee for a kids program.

    Inserts a new program_registrations row (status='registered',
    attended=true, participant_name='Walk-in', checked_in_by=staff)
    and returns the updated active registration count. The count matches
    the GET /dashboard computation (rows with status IN registered, waitlisted).

    Race-condition note: two simultaneous walk-ins can both insert before
    either reads the new count. Each insert is atomic, so totals remain
    correct; the response value may briefly lag by one between concurrent
    clients but converges on the next read.
    """
    from fastapi import HTTPException
    from datetime import datetime, timezone

    program_row = await db.execute(
        text("SELECT id, status FROM programs WHERE id = :pid"),
        {"pid": program_id},
    )
    program = program_row.fetchone()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    if program[1] in ("cancelled", "completed"):
        raise HTTPException(
            status_code=409, detail=f"Cannot record walk-in for {program[1]} program"
        )

    try:
        now = datetime.now(timezone.utc)
        await db.execute(
            text("""
                INSERT INTO program_registrations
                    (program_id, patron_id, participant_name, status,
                     registered_at, attended, attended_at, checked_in_by_id,
                     created_at, updated_at)
                VALUES
                    (:program_id, NULL, 'Walk-in', 'registered',
                     :now, true, :now, :staff_id,
                     :now, :now)
            """),
            {"program_id": program_id, "now": now, "staff_id": staff_user.id},
        )
        await db.execute(
            text(
                "UPDATE programs SET actual_attendance = COALESCE(actual_attendance, 0) + 1 WHERE id = :pid"
            ),
            {"pid": program_id},
        )
        count_result = await db.execute(
            text("""
                SELECT COUNT(*) FROM program_registrations
                WHERE program_id = :pid
                  AND status IN ('registered', 'waitlisted')
            """),
            {"pid": program_id},
        )
        new_count = count_result.scalar() or 0
        await db.commit()
        return WalkinResponse(registration_count=new_count)
    except SQLAlchemyError:
        await db.rollback()
        logger.exception("Failed to record walk-in for program %s", program_id)
        raise HTTPException(status_code=500, detail="Failed to record walk-in") from None
