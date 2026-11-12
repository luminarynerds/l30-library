# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Desk schedule -- who is on duty, on break, or missing from today's schedule."""
from app.core.logging import get_logger
from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....models.user import User
from ....models.staff_presence import StaffPresence, PresenceStatus
from ....models.staff_time_entry import StaffTimeEntry, TimeEntryType
from ....models.staff_schedule_fairness import StaffShift
from ..dependencies import require_staff

try:
    from zoneinfo import ZoneInfo
    LIBRARY_TZ = ZoneInfo("America/New_York")
except ImportError:
    import pytz
    LIBRARY_TZ = pytz.timezone("America/New_York")

router = APIRouter(prefix="/staff/desk-schedule", tags=["staff-desk-schedule"])
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DeskScheduleStaff(BaseModel):
    staff_id: int
    staff_name: str
    scheduled_start: str | None = None
    scheduled_end: str | None = None
    scheduled_hours: float | None = None
    shift_type: str | None = None
    presence_status: str
    clock_in_time: str | None = None


class DeskScheduleResponse(BaseModel):
    date: str
    on_duty: list[DeskScheduleStaff]
    on_break: list[DeskScheduleStaff]
    needs_help: list[DeskScheduleStaff] = []
    scheduled_not_present: list[DeskScheduleStaff]
    present_unscheduled: list[DeskScheduleStaff]
    coverage_note: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today():
    return datetime.now(timezone.utc).astimezone(LIBRARY_TZ).date()


def _staff_name(user: User | None) -> str:
    if user is None:
        return "Unknown"
    return user.first_name


def _presence_value(status) -> str:
    if isinstance(status, PresenceStatus):
        return status.value
    return str(status)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/today", response_model=DeskScheduleResponse)
async def get_desk_schedule_today(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return today's desk coverage: who is on duty, on break, missing, or unscheduled."""
    today = _today()

    try:
        # 1. Scheduled shifts for today
        shift_result = await db.execute(
            select(StaffShift)
            .options(selectinload(StaffShift.staff))
            .where(StaffShift.shift_date == today)
        )
        shifts = shift_result.scalars().all()
        shifts_by_staff = {s.staff_id: s for s in shifts}
        scheduled_ids = set(shifts_by_staff.keys())

        # 2. Current presence (non-off-duty, touched today -- rows persist
        # across days, and yesterday's missed clock-out is not coverage)
        day_start = datetime.combine(today, time.min, tzinfo=LIBRARY_TZ).astimezone(timezone.utc)
        presence_result = await db.execute(
            select(StaffPresence)
            .options(selectinload(StaffPresence.staff))
            .where(
                StaffPresence.status != PresenceStatus.OFF_DUTY,
                StaffPresence.status_changed_at >= day_start,
            )
        )
        presences = presence_result.scalars().all()
        presence_by_staff = {p.staff_id: p for p in presences}
        present_ids = set(presence_by_staff.keys())

        # 3. Clock-in times for today
        clockin_result = await db.execute(
            select(StaffTimeEntry).where(and_(
                StaffTimeEntry.shift_date == today,
                StaffTimeEntry.entry_type == TimeEntryType.CLOCK_IN,
            ))
        )
        clockins = clockin_result.scalars().all()
        clockin_by_staff = {}
        for ci in clockins:
            if ci.staff_id not in clockin_by_staff:
                clockin_by_staff[ci.staff_id] = ci.recorded_at

        # 4. Categorize
        on_duty: list[DeskScheduleStaff] = []
        on_break: list[DeskScheduleStaff] = []
        needs_help: list[DeskScheduleStaff] = []
        scheduled_not_present: list[DeskScheduleStaff] = []
        present_unscheduled: list[DeskScheduleStaff] = []

        all_ids = scheduled_ids | present_ids

        for sid in all_ids:
            shift = shifts_by_staff.get(sid)
            presence = presence_by_staff.get(sid)
            clock_in_time = clockin_by_staff.get(sid)

            # Determine user name from whichever source is available
            user = None
            if shift and shift.staff:
                user = shift.staff
            elif presence and presence.staff:
                user = presence.staff

            pstatus = _presence_value(presence.status) if presence else "off_duty"

            entry = DeskScheduleStaff(
                staff_id=sid,
                staff_name=_staff_name(user),
                scheduled_start=shift.scheduled_start.isoformat() if shift and shift.scheduled_start else None,
                scheduled_end=shift.scheduled_end.isoformat() if shift and shift.scheduled_end else None,
                scheduled_hours=shift.scheduled_hours if shift else None,
                shift_type=shift.shift_type.value if shift and hasattr(shift.shift_type, "value") else (shift.shift_type if shift else None),
                presence_status=pstatus,
                clock_in_time=clock_in_time.isoformat() if clock_in_time else None,
            )

            is_scheduled = sid in scheduled_ids
            is_present = sid in present_ids

            if is_present and pstatus == "needs_help":
                # A colleague flagged as stuck must not read as plain coverage.
                needs_help.append(entry)
            elif is_present and pstatus == "on_break":
                on_break.append(entry)
            elif is_scheduled and is_present:
                on_duty.append(entry)
            elif is_scheduled and not is_present:
                scheduled_not_present.append(entry)
            elif not is_scheduled and is_present:
                present_unscheduled.append(entry)

        # 5. Coverage note
        total_scheduled = len(scheduled_ids)
        present_scheduled = len(scheduled_ids & present_ids)
        if total_scheduled == 0:
            coverage_note = "No staff scheduled today"
        elif present_scheduled == total_scheduled:
            coverage_note = f"All {total_scheduled} scheduled staff present"
        else:
            coverage_note = f"{present_scheduled} of {total_scheduled} scheduled staff present"

        return DeskScheduleResponse(
            date=today.isoformat(),
            on_duty=on_duty,
            on_break=on_break,
            needs_help=needs_help,
            scheduled_not_present=scheduled_not_present,
            present_unscheduled=present_unscheduled,
            coverage_note=coverage_note,
        )
    except Exception:
        # An all-empty 200 here renders as "no staff today"; a database fault
        # must surface as a real 500 instead.
        logger.exception("Failed to build desk schedule")
        raise
