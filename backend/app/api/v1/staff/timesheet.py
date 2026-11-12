# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff timesheet -- view clock-in/out history, breaks, and daily summaries."""
from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....models.staff_time_entry import StaffTimeEntry, TimeEntryType
from ....models.staff_schedule_fairness import StaffShift
from ..dependencies import require_staff, require_admin

try:
    from zoneinfo import ZoneInfo
    LIBRARY_TZ = ZoneInfo("America/New_York")
except ImportError:
    import pytz
    LIBRARY_TZ = pytz.timezone("America/New_York")

router = APIRouter(prefix="/staff/timesheet", tags=["staff-timesheet"])
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BreakEntry(BaseModel):
    start: str | None = None
    end: str | None = None
    duration_minutes: float | None = None


class TimesheetDayResponse(BaseModel):
    shift_date: str
    clock_in: str | None = None
    clock_out: str | None = None
    breaks: list[BreakEntry] = []
    total_worked_hours: float | None = None
    total_break_minutes: float = 0
    scheduled_hours: float | None = None
    status: str  # "in_progress" | "completed" | "not_started" | "incomplete"


class TimesheetSummaryResponse(BaseModel):
    start_date: str
    end_date: str
    days: list[TimesheetDayResponse]
    total_worked_hours: float
    total_scheduled_hours: float
    total_break_minutes: float


class TimeEntryResponse(BaseModel):
    id: int
    entry_type: str
    recorded_at: str
    duration_minutes: float | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today() -> date:
    return datetime.now(timezone.utc).astimezone(LIBRARY_TZ).date()


async def _get_day_summary(
    db: AsyncSession,
    staff_id: int,
    day: date,
    scheduled_hours: float | None = None,
) -> TimesheetDayResponse:
    result = await db.execute(
        select(StaffTimeEntry)
        .where(and_(
            StaffTimeEntry.staff_id == staff_id,
            StaffTimeEntry.shift_date == day,
        ))
        .order_by(StaffTimeEntry.recorded_at)
    )
    entries = result.scalars().all()

    clock_in: datetime | None = None
    clock_out: datetime | None = None
    breaks: list[BreakEntry] = []
    current_break_start: datetime | None = None
    total_break_minutes: float = 0

    # Pair punches into segments (mirroring sync_shift_actuals): each closed
    # segment contributes its span minus its own breaks, so a split shift
    # never counts the midday gap as worked.
    open_since: datetime | None = None
    seg_break_minutes: float = 0.0
    closed_minutes: float = 0.0
    has_closed_segment = False

    for entry in entries:
        etype = entry.entry_type
        if isinstance(etype, TimeEntryType):
            etype = etype.value
        if etype == "clock_in":
            if clock_in is None:
                clock_in = entry.recorded_at
            if open_since is None:
                open_since = entry.recorded_at
                seg_break_minutes = 0.0
        elif etype == "clock_out":
            clock_out = entry.recorded_at
            if open_since is not None:
                span = (entry.recorded_at - open_since).total_seconds() / 60
                closed_minutes += span - seg_break_minutes
                has_closed_segment = True
                open_since = None
        elif etype == "break_start":
            current_break_start = entry.recorded_at
        elif etype == "break_end":
            brk = BreakEntry(
                start=current_break_start.isoformat() if current_break_start else None,
                end=entry.recorded_at.isoformat(),
                duration_minutes=entry.duration_minutes,
            )
            if brk.duration_minutes is None and current_break_start:
                brk.duration_minutes = round(
                    (entry.recorded_at - current_break_start).total_seconds() / 60, 1
                )
            if brk.duration_minutes:
                total_break_minutes += brk.duration_minutes
                if open_since is not None:
                    seg_break_minutes += brk.duration_minutes
            breaks.append(brk)
            current_break_start = None

    # Handle in-progress break
    if current_break_start is not None:
        breaks.append(BreakEntry(start=current_break_start.isoformat()))

    # Calculate status and worked hours. Live elapsed time applies only to
    # today: on a past day an unclosed punch is a missed clock-out, not a
    # multi-hundred-hour shift, so the day reads 'incomplete' and only its
    # closed segments count.
    if clock_in is None:
        status = "not_started"
        total_worked_hours = None
    elif open_since is None:
        status = "completed"
        total_worked_hours = round(max(closed_minutes / 60, 0), 2)
    elif day == _today():
        status = "in_progress"
        live = (datetime.now(timezone.utc) - open_since).total_seconds() / 60 - seg_break_minutes
        total_worked_hours = round(max((closed_minutes + max(live, 0)) / 60, 0), 2)
    else:
        status = "incomplete"
        total_worked_hours = round(max(closed_minutes / 60, 0), 2) if has_closed_segment else None

    return TimesheetDayResponse(
        shift_date=day.isoformat(),
        clock_in=clock_in.isoformat() if clock_in else None,
        clock_out=clock_out.isoformat() if clock_out else None,
        breaks=breaks,
        total_worked_hours=total_worked_hours,
        total_break_minutes=round(total_break_minutes, 1),
        scheduled_hours=scheduled_hours,
        status=status,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/today", response_model=TimesheetDayResponse)
async def get_today_timesheet(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's timesheet for today."""
    today = _today()
    try:
        shift_result = await db.execute(
            select(StaffShift).where(and_(
                StaffShift.staff_id == staff_user.id,
                StaffShift.shift_date == today,
            ))
        )
        shift = shift_result.scalar_one_or_none()
        scheduled_hours = shift.scheduled_hours if shift else None

        return await _get_day_summary(db, staff_user.id, today, scheduled_hours)
    except Exception:
        # A fabricated empty 200 here reads as "not clocked in" and makes the
        # button's reconcile branch lie; let it surface as a real 500.
        logger.exception("Failed to fetch today timesheet for user %s", staff_user.id)
        raise


@router.get("/summary", response_model=TimesheetSummaryResponse)
async def get_timesheet_summary(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return a timesheet summary for a date range (max 31 days)."""
    try:
        sd = date.fromisoformat(start_date)
        ed = date.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format, use YYYY-MM-DD") from None

    if ed < sd:
        raise HTTPException(status_code=422, detail="end_date must be >= start_date")
    if (ed - sd).days > 30:
        raise HTTPException(status_code=422, detail="Date range cannot exceed 31 days")

    try:
        shift_result = await db.execute(
            select(StaffShift).where(and_(
                StaffShift.staff_id == staff_user.id,
                StaffShift.shift_date >= sd,
                StaffShift.shift_date <= ed,
            ))
        )
        shifts_by_date = {s.shift_date: s for s in shift_result.scalars().all()}

        days: list[TimesheetDayResponse] = []
        current = sd
        while current <= ed:
            shift = shifts_by_date.get(current)
            scheduled_hours = shift.scheduled_hours if shift else None
            day_summary = await _get_day_summary(db, staff_user.id, current, scheduled_hours)
            days.append(day_summary)
            current += timedelta(days=1)

        total_worked = sum(d.total_worked_hours or 0 for d in days)
        total_scheduled = sum(d.scheduled_hours or 0 for d in days)
        total_breaks = sum(d.total_break_minutes for d in days)

        return TimesheetSummaryResponse(
            start_date=start_date,
            end_date=end_date,
            days=days,
            total_worked_hours=round(total_worked, 2),
            total_scheduled_hours=round(total_scheduled, 2),
            total_break_minutes=round(total_breaks, 1),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch timesheet summary for user %s", staff_user.id)
        raise


@router.get("/entries", response_model=list[TimeEntryResponse])
async def get_timesheet_entries(
    entry_date: str = Query(default=None, alias="date", description="Date YYYY-MM-DD, defaults to today"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return raw time entries for a single day."""
    if entry_date is None:
        target = _today()
    else:
        try:
            target = date.fromisoformat(entry_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date format, use YYYY-MM-DD") from None

    try:
        result = await db.execute(
            select(StaffTimeEntry)
            .where(and_(
                StaffTimeEntry.staff_id == staff_user.id,
                StaffTimeEntry.shift_date == target,
            ))
            .order_by(StaffTimeEntry.recorded_at)
        )
        entries = result.scalars().all()

        return [
            TimeEntryResponse(
                id=e.id,
                entry_type=e.entry_type.value if isinstance(e.entry_type, TimeEntryType) else e.entry_type,
                recorded_at=e.recorded_at.isoformat(),
                duration_minutes=e.duration_minutes,
                notes=e.notes,
            )
            for e in entries
        ]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch time entries for user %s", staff_user.id)
        raise


# ---------------------------------------------------------------------------
# Open shifts (missing clock-out detection)
# ---------------------------------------------------------------------------

class OpenShiftEntry(BaseModel):
    shift_date: str
    clock_in: str
    days_ago: int
    auto_closed: bool = False


@router.get("/open-shifts/me", response_model=list[OpenShiftEntry])
async def get_my_open_shifts(
    days: int = Query(7, ge=1, le=30),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Days in the last `days` where the current user clocked in but never clocked out."""
    from ....services.time_entry_service import is_unreviewed_auto_close

    today = _today()
    cutoff = today - timedelta(days=days)
    try:
        result = await db.execute(
            select(StaffTimeEntry)
            .where(and_(
                StaffTimeEntry.staff_id == staff_user.id,
                StaffTimeEntry.shift_date >= cutoff,
                StaffTimeEntry.shift_date < today,
            ))
            .order_by(StaffTimeEntry.shift_date, StaffTimeEntry.recorded_at)
        )
        entries = result.scalars().all()
        by_day: dict[date, dict] = {}
        for e in entries:
            day = e.shift_date
            slot = by_day.setdefault(day, {"clock_in": None, "clock_out": False, "auto_closed": False})
            if e.entry_type == TimeEntryType.CLOCK_IN and slot["clock_in"] is None:
                slot["clock_in"] = e.recorded_at
            elif e.entry_type == TimeEntryType.CLOCK_OUT:
                # The sweeper's guessed clock-out keeps the day surfaced for
                # review until a manager confirms or corrects it.
                if is_unreviewed_auto_close(e.notes):
                    slot["auto_closed"] = True
                else:
                    slot["clock_out"] = True
        out: list[OpenShiftEntry] = []
        for day, slot in sorted(by_day.items()):
            if slot["clock_in"] is not None and not slot["clock_out"]:
                out.append(OpenShiftEntry(
                    shift_date=day.isoformat(),
                    clock_in=slot["clock_in"].isoformat(),
                    days_ago=(today - day).days,
                    auto_closed=slot["auto_closed"],
                ))
        return out
    except Exception:
        logger.exception("Failed to fetch open shifts for user %s", staff_user.id)
        raise


# ---------------------------------------------------------------------------
# Manager-only time entry editing
# ---------------------------------------------------------------------------

class TimeEntryUpdateRequest(BaseModel):
    recorded_at: str | None = None  # ISO 8601 UTC
    notes: str | None = None


class TimeEntryCreateRequest(BaseModel):
    staff_id: int
    entry_type: str  # clock_in | clock_out | break_start | break_end
    recorded_at: str  # ISO 8601 UTC
    shift_date: str  # YYYY-MM-DD; library-local date for the shift
    notes: str | None = None


def _parse_iso_utc(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get("/staff/{staff_id}/entries", response_model=list[TimeEntryResponse])
async def admin_list_entries(
    staff_id: int,
    target_date: date | None = Query(None, alias="date"),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Manager view of a staff member's time entries for a given day (default today)."""
    target = target_date or _today()
    try:
        result = await db.execute(
            select(StaffTimeEntry)
            .where(and_(
                StaffTimeEntry.staff_id == staff_id,
                StaffTimeEntry.shift_date == target,
            ))
            .order_by(StaffTimeEntry.recorded_at)
        )
        entries = result.scalars().all()
        return [
            TimeEntryResponse(
                id=e.id,
                entry_type=e.entry_type.value if isinstance(e.entry_type, TimeEntryType) else e.entry_type,
                recorded_at=e.recorded_at.isoformat(),
                duration_minutes=e.duration_minutes,
                notes=e.notes,
            )
            for e in entries
        ]
    except Exception:
        logger.exception("admin_list_entries failed for staff %s on %s", staff_id, target)
        raise


@router.post("/entries", response_model=TimeEntryResponse, status_code=201)
async def admin_create_entry(
    payload: TimeEntryCreateRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Manager-only: insert a missing time entry (e.g. a backdated clock-out)."""
    try:
        etype = TimeEntryType(payload.entry_type)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid entry_type: {payload.entry_type}") from None

    try:
        recorded = _parse_iso_utc(payload.recorded_at)
    except ValueError:
        raise HTTPException(status_code=422, detail="recorded_at must be ISO 8601") from None

    try:
        shift_d = date.fromisoformat(payload.shift_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="shift_date must be YYYY-MM-DD") from None

    from ....services.time_entry_service import (
        manual_change_creates_orphan_clock_out,
        reset_presence_if_no_open_segment,
        sync_shift_actuals,
    )

    now = datetime.now(timezone.utc)
    if recorded > now:
        raise HTTPException(
            status_code=422,
            detail="That time is in the future. Punches can only be recorded for times that have already happened.",
        )
    if await manual_change_creates_orphan_clock_out(
        db, payload.staff_id, shift_d, add=(recorded, etype)
    ):
        raise HTTPException(
            status_code=422,
            detail="That entry would leave a clock-out with no clock-in before it. Add or fix the clock-in first.",
        )

    note = (payload.notes or "").strip()
    audit = f"manual entry by {admin_user.first_name} (admin id={admin_user.id})"
    full_note = f"{note} -- {audit}" if note else audit

    entry = StaffTimeEntry(
        staff_id=payload.staff_id,
        entry_type=etype,
        recorded_at=recorded,
        shift_date=shift_d,
        notes=full_note[:255],
    )
    db.add(entry)
    await db.flush()

    # Re-sync shift actuals for every entry type -- a backfilled break or a
    # corrected clock-in changes payroll hours just like a clock-out does.
    try:
        await sync_shift_actuals(db, payload.staff_id, shift_d)
    except Exception:  # noqa: BLE001  # best-effort sync_shift_actuals — entry already saved
        logger.warning("sync_shift_actuals failed after manual entry %s", entry.id, exc_info=True)

    await reset_presence_if_no_open_segment(db, payload.staff_id, now)

    return TimeEntryResponse(
        id=entry.id,
        entry_type=entry.entry_type.value if isinstance(entry.entry_type, TimeEntryType) else entry.entry_type,
        recorded_at=entry.recorded_at.isoformat(),
        duration_minutes=entry.duration_minutes,
        notes=entry.notes,
    )


@router.patch("/entries/{entry_id}", response_model=TimeEntryResponse)
async def admin_update_entry(
    entry_id: int,
    payload: TimeEntryUpdateRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Manager-only: adjust recorded_at and/or notes on an existing entry."""
    result = await db.execute(
        select(StaffTimeEntry).where(StaffTimeEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Time entry not found")

    from ....services.time_entry_service import (
        manual_change_creates_orphan_clock_out,
        reset_presence_if_no_open_segment,
        sync_shift_actuals,
    )

    now = datetime.now(timezone.utc)
    if payload.recorded_at is not None:
        try:
            new_recorded = _parse_iso_utc(payload.recorded_at)
        except ValueError:
            raise HTTPException(status_code=422, detail="recorded_at must be ISO 8601") from None
        # Validate before mutating: a rejected edit must leave the entry untouched.
        if new_recorded > now:
            raise HTTPException(
                status_code=422,
                detail="That time is in the future. Punches can only be recorded for times that have already happened.",
            )
        if await manual_change_creates_orphan_clock_out(
            db, entry.staff_id, entry.shift_date, move=(entry.id, new_recorded)
        ):
            raise HTTPException(
                status_code=422,
                detail="That change would leave a clock-out with no clock-in before it. Adjust the times so each clock-out follows its clock-in.",
            )
        entry.recorded_at = new_recorded

    audit = f"edited by {admin_user.first_name} (admin id={admin_user.id})"
    if payload.notes is not None:
        existing = (entry.notes or "").strip()
        merged = (payload.notes.strip() + " -- " + audit) if payload.notes.strip() else audit
        entry.notes = (merged if not existing else f"{existing}; {merged}")[:255]
    else:
        existing = (entry.notes or "").strip()
        entry.notes = (f"{existing}; {audit}" if existing else audit)[:255]

    await db.flush()

    try:
        await sync_shift_actuals(db, entry.staff_id, entry.shift_date)
    except Exception:  # noqa: BLE001  # best-effort sync_shift_actuals — entry already saved
        logger.warning("sync_shift_actuals failed after edit of entry %s", entry.id, exc_info=True)

    await reset_presence_if_no_open_segment(db, entry.staff_id, now)

    return TimeEntryResponse(
        id=entry.id,
        entry_type=entry.entry_type.value if isinstance(entry.entry_type, TimeEntryType) else entry.entry_type,
        recorded_at=entry.recorded_at.isoformat(),
        duration_minutes=entry.duration_minutes,
        notes=entry.notes,
    )


@router.delete("/entries/{entry_id}", status_code=204)
async def admin_delete_entry(
    entry_id: int,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Manager-only: delete a stray time entry (e.g. an accidental clock-in)."""
    result = await db.execute(
        select(StaffTimeEntry).where(StaffTimeEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Time entry not found")

    staff_id = entry.staff_id
    shift_d = entry.shift_date

    await db.delete(entry)
    await db.flush()

    from ....services.time_entry_service import (
        reset_presence_if_no_open_segment,
        sync_shift_actuals,
    )

    try:
        await sync_shift_actuals(db, staff_id, shift_d)
    except Exception:  # noqa: BLE001  # best-effort sync_shift_actuals — entry already deleted
        logger.warning("sync_shift_actuals failed after delete on shift %s/%s", staff_id, shift_d, exc_info=True)

    await reset_presence_if_no_open_segment(db, staff_id, datetime.now(timezone.utc))

    return None
