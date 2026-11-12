# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import case, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.staff_presence import PresenceStatus, StaffPresence
from ..models.staff_time_entry import StaffTimeEntry, TimeEntryType
from ..models.staff_schedule_fairness import StaffShift, ShiftStatus

logger = get_logger(__name__)

try:
    from zoneinfo import ZoneInfo
    LIBRARY_TZ = ZoneInfo("America/New_York")
except ImportError:
    import pytz
    LIBRARY_TZ = pytz.timezone("America/New_York")


async def _entries_for_day(
    db: AsyncSession, staff_id: int, shift_date: date
) -> list[StaffTimeEntry]:
    result = await db.execute(
        select(StaffTimeEntry)
        .where(
            and_(
                StaffTimeEntry.staff_id == staff_id,
                StaffTimeEntry.shift_date == shift_date,
            )
        )
        .order_by(StaffTimeEntry.recorded_at, StaffTimeEntry.id)
    )
    return list(result.scalars().all())


def _open_clock_in(entries: list[StaffTimeEntry]) -> StaffTimeEntry | None:
    """Earliest CLOCK_IN of the still-open segment, or None when every segment
    is closed. Duplicate CLOCK_INs inside one open segment are ignored."""
    open_ci = None
    for e in entries:
        if e.entry_type == TimeEntryType.CLOCK_IN:
            if open_ci is None:
                open_ci = e
        elif e.entry_type == TimeEntryType.CLOCK_OUT:
            open_ci = None
    return open_ci


def _segment_tail(
    entries: list[StaffTimeEntry], segment_ci: StaffTimeEntry
) -> list[StaffTimeEntry]:
    return entries[entries.index(segment_ci) + 1:]


def _open_break_start(
    entries: list[StaffTimeEntry], segment_ci: StaffTimeEntry
) -> StaffTimeEntry | None:
    """Earliest BREAK_START in the segment with no later BREAK_END."""
    open_bs = None
    for e in _segment_tail(entries, segment_ci):
        if e.entry_type == TimeEntryType.BREAK_START:
            if open_bs is None:
                open_bs = e
        elif e.entry_type == TimeEntryType.BREAK_END:
            open_bs = None
    return open_bs


def _paired_break_minutes(
    entries: list[StaffTimeEntry], segment_ci: StaffTimeEntry
) -> float:
    """Closed break minutes inside a segment. Derives from timestamps when a
    backfilled BREAK_END carries no stored duration."""
    total = 0.0
    open_start = None
    for e in _segment_tail(entries, segment_ci):
        if e.entry_type == TimeEntryType.BREAK_START:
            if open_start is None:
                open_start = e
        elif e.entry_type == TimeEntryType.BREAK_END:
            if e.duration_minutes is not None:
                total += e.duration_minutes
            elif open_start is not None:
                total += (e.recorded_at - open_start.recorded_at).total_seconds() / 60.0
            open_start = None
    return total


async def _locate_open_segment(
    db: AsyncSession, staff_id: int, today: date
) -> tuple[date, list[StaffTimeEntry], StaffTimeEntry | None]:
    """Find the open segment a punch belongs to: today's, or -- only while the
    new local day has no punches yet -- the prior day's (a shift running past
    local midnight). Returns (shift_date, that day's entries, open clock-in)."""
    entries = await _entries_for_day(db, staff_id, today)
    open_ci = _open_clock_in(entries)
    if open_ci is None and not entries:
        prev_day = today - timedelta(days=1)
        prev_entries = await _entries_for_day(db, staff_id, prev_day)
        prev_ci = _open_clock_in(prev_entries)
        if prev_ci is not None:
            return prev_day, prev_entries, prev_ci
    return today, entries, open_ci


async def _shift_id_for(db: AsyncSession, staff_id: int, shift_date: date) -> int | None:
    result = await db.execute(
        select(StaffShift).where(
            and_(
                StaffShift.staff_id == staff_id,
                StaffShift.shift_date == shift_date,
            )
        )
    )
    shift = result.scalars().first()
    return shift.id if shift else None


async def record_transition(
    db: AsyncSession,
    staff_id: int,
    old_status: str | None,
    new_status: str,
    now: datetime,
) -> StaffTimeEntry | None:
    today = now.astimezone(LIBRARY_TZ).date()

    if new_status == "on_break":
        seg_date, entries, open_ci = await _locate_open_segment(db, staff_id, today)
        if open_ci is None:
            raise HTTPException(status_code=409, detail="Clock in before starting a break.")
        if _open_break_start(entries, open_ci) is not None:
            logger.info("Break already open for staff %d on %s", staff_id, seg_date)
            return None
        entry = StaffTimeEntry(
            staff_id=staff_id,
            entry_type=TimeEntryType.BREAK_START,
            recorded_at=now,
            shift_date=seg_date,
            staff_shift_id=await _shift_id_for(db, staff_id, seg_date),
        )
        db.add(entry)
        await db.flush()
        return entry

    if new_status == "available":
        # Going "available" is either ending a break or clocking in. Decide from
        # the punch entries, never from the presence status -- presence persists
        # across days, so a stale "available"/"on_break" carried over from a prior
        # shift that never clocked out would otherwise mislabel (or silently drop)
        # today's punch and leave the user stuck on "Clock-in didn't record".
        seg_date, entries, open_ci = await _locate_open_segment(db, staff_id, today)
        if open_ci is not None:
            open_bs = _open_break_start(entries, open_ci)
            if open_bs is not None:
                # Break end -- close the open break in its own segment (which may
                # be yesterday's, for a break running past local midnight).
                entry = StaffTimeEntry(
                    staff_id=staff_id,
                    entry_type=TimeEntryType.BREAK_END,
                    recorded_at=now,
                    duration_minutes=(now - open_bs.recorded_at).total_seconds() / 60.0,
                    shift_date=seg_date,
                    staff_shift_id=await _shift_id_for(db, staff_id, seg_date),
                )
                db.add(entry)
                await db.flush()
                return entry
            if seg_date == today:
                # Already clocked in today with no open break -- idempotent no-op.
                logger.info("Open clock-in already exists for staff %d on %s", staff_id, today)
                return None
            # Only a prior day's segment is open (forgotten clock-out): fall
            # through so the new day still gets a fresh clock-in.

        # Clock in -- opens a new segment. A closed earlier segment today
        # (split shift, accidental clock-out) does not block it.
        entry = StaffTimeEntry(
            staff_id=staff_id,
            entry_type=TimeEntryType.CLOCK_IN,
            recorded_at=now,
            shift_date=today,
            staff_shift_id=await _shift_id_for(db, staff_id, today),
        )
        db.add(entry)
        await db.flush()
        return entry

    if new_status == "off_duty":
        # Clock out -- only valid against an open segment. A duplicate clock-out
        # (stale tab) or one with no clock-in must not write a row: the last
        # clock-out defines paid hours downstream.
        seg_date, entries, open_ci = await _locate_open_segment(db, staff_id, today)
        if open_ci is None:
            if any(e.entry_type == TimeEntryType.CLOCK_OUT for e in entries):
                detail = "You're already clocked out. Clock in again to start a new shift segment."
            else:
                detail = "You're not clocked in, so there's nothing to clock out."
            raise HTTPException(status_code=409, detail=detail)

        shift_id = await _shift_id_for(db, staff_id, seg_date)
        total_break_minutes = _paired_break_minutes(entries, open_ci)

        # Close a dangling break: clocking out while still on_break.
        open_bs = _open_break_start(entries, open_ci)
        if open_bs is not None:
            open_minutes = (now - open_bs.recorded_at).total_seconds() / 60.0
            total_break_minutes += open_minutes
            db.add(StaffTimeEntry(
                staff_id=staff_id,
                entry_type=TimeEntryType.BREAK_END,
                recorded_at=now,
                duration_minutes=open_minutes,
                shift_date=seg_date,
                staff_shift_id=shift_id,
            ))

        worked_minutes = (
            (now - open_ci.recorded_at).total_seconds() / 60.0 - total_break_minutes
        )

        entry = StaffTimeEntry(
            staff_id=staff_id,
            entry_type=TimeEntryType.CLOCK_OUT,
            recorded_at=now,
            duration_minutes=worked_minutes,
            shift_date=seg_date,
            staff_shift_id=shift_id,
        )
        db.add(entry)
        await db.flush()
        await sync_shift_actuals(db, staff_id, seg_date)
        return entry

    return None


async def sync_shift_actuals(
    db: AsyncSession,
    staff_id: int,
    shift_date: date,
) -> None:
    try:
        result = await db.execute(
            select(StaffShift).where(
                and_(
                    StaffShift.staff_id == staff_id,
                    StaffShift.shift_date == shift_date,
                )
            )
        )
        shift = result.scalars().first()
        if shift is None:
            return

        entries = await _entries_for_day(db, staff_id, shift_date)

        # Pair punches into ordered segments; each closed segment contributes
        # its own span minus its paired break minutes. A day can hold several
        # segments (split shift, re-clock-in after an accidental clock-out).
        first_clock_in = None
        last_clock_out = None
        open_ci = None
        open_break = None
        seg_break_minutes = 0.0
        worked_minutes = 0.0
        has_closed_segment = False

        for e in entries:
            if e.entry_type == TimeEntryType.CLOCK_IN:
                if first_clock_in is None:
                    first_clock_in = e
                if open_ci is None:
                    open_ci = e
                    open_break = None
                    seg_break_minutes = 0.0
            elif e.entry_type == TimeEntryType.CLOCK_OUT:
                last_clock_out = e
                if open_ci is not None:
                    span = (e.recorded_at - open_ci.recorded_at).total_seconds() / 60.0
                    worked_minutes += span - seg_break_minutes
                    has_closed_segment = True
                    open_ci = None
            elif e.entry_type == TimeEntryType.BREAK_START:
                if open_ci is not None and open_break is None:
                    open_break = e
            elif e.entry_type == TimeEntryType.BREAK_END:
                if open_ci is not None:
                    if e.duration_minutes is not None:
                        seg_break_minutes += e.duration_minutes
                    elif open_break is not None:
                        seg_break_minutes += (e.recorded_at - open_break.recorded_at).total_seconds() / 60.0
                    open_break = None

        shift.actual_start = (
            first_clock_in.recorded_at.astimezone(LIBRARY_TZ).time() if first_clock_in else None
        )
        shift.actual_end = (
            last_clock_out.recorded_at.astimezone(LIBRARY_TZ).time() if last_clock_out else None
        )
        shift.actual_hours = round(worked_minutes / 60.0, 2) if has_closed_segment else None

        if has_closed_segment and open_ci is None:
            shift.status = ShiftStatus.COMPLETED
        elif shift.status == ShiftStatus.COMPLETED:
            # The punches no longer show a finished day (clock-out deleted, or a
            # segment reopened) -- staying COMPLETED would let payroll pay the
            # stale hours. ASSIGNED keeps it out of payroll until re-confirmed.
            shift.status = ShiftStatus.ASSIGNED
        await db.flush()

    except Exception:
        logger.exception("Failed to sync shift actuals for staff %d on %s", staff_id, shift_date)


async def manual_change_creates_orphan_clock_out(
    db: AsyncSession,
    staff_id: int,
    shift_date: date,
    add: tuple[datetime, TimeEntryType] | None = None,
    move: tuple[int, datetime] | None = None,
) -> bool:
    """Simulate a manual-editor add/move against the day's punches with the same
    segment rule the sync uses: does any clock-out stop closing an open segment?
    A day that is already incoherent (legacy orphan rows) only fails when the
    change adds a NEW orphan, so repairs and unrelated edits stay possible."""
    entries = await _entries_for_day(db, staff_id, shift_date)

    def orphan_count(rows: list[tuple[datetime, int, TimeEntryType]]) -> int:
        orphans = 0
        open_segment = False
        for _, _, etype in sorted(rows, key=lambda r: (r[0], r[1])):
            if etype == TimeEntryType.CLOCK_IN:
                open_segment = True
            elif etype == TimeEntryType.CLOCK_OUT:
                if open_segment:
                    open_segment = False
                else:
                    orphans += 1
        return orphans

    baseline = [(e.recorded_at, e.id, e.entry_type) for e in entries]
    simulated = list(baseline)
    if move is not None:
        simulated = [
            ((move[1], rid, etype) if rid == move[0] else (ts, rid, etype))
            for ts, rid, etype in simulated
        ]
    if add is not None:
        # A new row gets the highest id, so it sorts after same-timestamp rows.
        next_id = max((e.id for e in entries), default=0) + 1
        simulated.append((add[0], next_id, add[1]))
    return orphan_count(simulated) > orphan_count(baseline)


async def reset_presence_if_no_open_segment(
    db: AsyncSession,
    staff_id: int,
    now: datetime,
) -> bool:
    """After a manual punch correction, clear a stale presence row: someone whose
    timesheet shows no open segment cannot still be on duty. Keeps the desk
    schedule and on-duty list honest once a manager resolves a dangling punch."""
    result = await db.execute(
        select(StaffPresence).where(StaffPresence.staff_id == staff_id)
    )
    presence = result.scalar_one_or_none()
    if presence is None or presence.status == PresenceStatus.OFF_DUTY:
        return False

    today = now.astimezone(LIBRARY_TZ).date()
    _, _, open_ci = await _locate_open_segment(db, staff_id, today)
    if open_ci is not None:
        return False

    presence.status = PresenceStatus.OFF_DUTY
    presence.status_changed_at = now
    presence.shift_ended_at = now
    presence.break_started_at = None
    await db.flush()
    return True


AUTO_CLOSE_NOTE = "auto-closed -- no clock-out was recorded, needs manager review"


def is_unreviewed_auto_close(notes: str | None) -> bool:
    """A sweeper-written clock-out stays flagged for review until a manager
    edits it (manual edits append an 'edited by' audit suffix)."""
    return bool(notes) and notes.startswith("auto-closed") and "edited by" not in notes


async def auto_close_open_day(
    db: AsyncSession,
    staff_id: int,
    shift_date: date,
    now: datetime,
) -> StaffTimeEntry | None:
    """Close a past day's dangling punch: at the scheduled shift end when a
    shift row exists (and ends after the day's last punch), else local
    midnight. Closes any open break the same way, re-syncs payroll actuals,
    and clears the stale presence row."""
    entries = await _entries_for_day(db, staff_id, shift_date)
    open_ci = _open_clock_in(entries)
    if open_ci is None:
        return None

    result = await db.execute(
        select(StaffShift).where(
            and_(
                StaffShift.staff_id == staff_id,
                StaffShift.shift_date == shift_date,
            )
        )
    )
    shift = result.scalars().first()

    last_recorded = entries[-1].recorded_at
    day_end = datetime.combine(
        shift_date + timedelta(days=1), time.min, tzinfo=LIBRARY_TZ
    ).astimezone(timezone.utc)
    close_at = max(day_end, last_recorded)
    if shift is not None and shift.scheduled_end is not None:
        scheduled_end = datetime.combine(
            shift_date, shift.scheduled_end, tzinfo=LIBRARY_TZ
        ).astimezone(timezone.utc)
        if scheduled_end > last_recorded:
            close_at = scheduled_end

    total_break_minutes = _paired_break_minutes(entries, open_ci)
    open_bs = _open_break_start(entries, open_ci)
    if open_bs is not None:
        open_minutes = (close_at - open_bs.recorded_at).total_seconds() / 60.0
        total_break_minutes += open_minutes
        db.add(StaffTimeEntry(
            staff_id=staff_id,
            entry_type=TimeEntryType.BREAK_END,
            recorded_at=close_at,
            duration_minutes=open_minutes,
            shift_date=shift_date,
            staff_shift_id=shift.id if shift else None,
            notes=AUTO_CLOSE_NOTE,
        ))

    worked_minutes = (
        (close_at - open_ci.recorded_at).total_seconds() / 60.0 - total_break_minutes
    )
    entry = StaffTimeEntry(
        staff_id=staff_id,
        entry_type=TimeEntryType.CLOCK_OUT,
        recorded_at=close_at,
        duration_minutes=worked_minutes,
        shift_date=shift_date,
        staff_shift_id=shift.id if shift else None,
        notes=AUTO_CLOSE_NOTE,
    )
    db.add(entry)
    await db.flush()
    await sync_shift_actuals(db, staff_id, shift_date)
    await reset_presence_if_no_open_segment(db, staff_id, now)
    return entry


async def close_dangling_punches(db: AsyncSession, now: datetime) -> int:
    """Auto-close every punch still open past its local end-of-day; returns the
    number of days closed. Today's open punches are live shifts, never touched."""
    today = now.astimezone(LIBRARY_TZ).date()
    result = await db.execute(
        select(StaffTimeEntry.staff_id, StaffTimeEntry.shift_date)
        .where(StaffTimeEntry.shift_date < today)
        .group_by(StaffTimeEntry.staff_id, StaffTimeEntry.shift_date)
        .having(
            func.sum(case((StaffTimeEntry.entry_type == TimeEntryType.CLOCK_IN, 1), else_=0))
            > func.sum(case((StaffTimeEntry.entry_type == TimeEntryType.CLOCK_OUT, 1), else_=0))
        )
    )
    closed = 0
    for staff_id, shift_date in result.all():
        if await auto_close_open_day(db, staff_id, shift_date, now) is not None:
            closed += 1
    return closed


async def get_day_summary(
    db: AsyncSession,
    staff_id: int,
    target_date: date,
) -> dict:
    result = await db.execute(
        select(StaffTimeEntry)
        .where(
            and_(
                StaffTimeEntry.staff_id == staff_id,
                StaffTimeEntry.shift_date == target_date,
            )
        )
        .order_by(StaffTimeEntry.recorded_at)
    )
    entries = result.scalars().all()

    clock_in = None
    clock_out = None
    break_starts = []
    break_ends = []

    for e in entries:
        if e.entry_type == TimeEntryType.CLOCK_IN and clock_in is None:
            clock_in = e
        elif e.entry_type == TimeEntryType.CLOCK_OUT:
            clock_out = e
        elif e.entry_type == TimeEntryType.BREAK_START:
            break_starts.append(e)
        elif e.entry_type == TimeEntryType.BREAK_END:
            break_ends.append(e)

    break_pairs = list(zip(break_starts, break_ends))
    total_break_minutes = sum((be.duration_minutes or 0) for be in break_ends)
    total_worked_hours = (clock_out.duration_minutes / 60.0) if clock_out and clock_out.duration_minutes is not None else None

    if clock_out:
        status = "completed"
    elif clock_in:
        status = "in_progress"
    else:
        status = "not_started"

    return {
        "shift_date": target_date.isoformat(),
        "clock_in": clock_in.recorded_at.isoformat() if clock_in else None,
        "clock_out": clock_out.recorded_at.isoformat() if clock_out else None,
        "breaks": [
            {
                "start": bs.recorded_at.isoformat(),
                "end": be.recorded_at.isoformat(),
                "duration_minutes": be.duration_minutes,
            }
            for bs, be in break_pairs
        ],
        "total_worked_hours": round(total_worked_hours, 2) if total_worked_hours is not None else None,
        "total_break_minutes": round(total_break_minutes, 1),
        "status": status,
    }
