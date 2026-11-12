# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""record_transition: clock-in must not be silent; clock-out closes dangling breaks."""

import pytest
from datetime import date, datetime, time, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import select
from app.models.staff_schedule_fairness import FairnessShiftType, ShiftStatus, StaffShift
from app.models.staff_time_entry import StaffTimeEntry, TimeEntryType
from app.services.time_entry_service import record_transition, sync_shift_actuals


def _utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


# 2026-06-09 09:00 EDT. Fixed timestamps keep cross-midnight tests deterministic:
# record_transition derives everything from the `now` argument, not the wall clock.
T0 = _utc(2026, 6, 9, 13, 0)


async def _entries(db, staff_id, entry_type=None):
    q = select(StaffTimeEntry).where(StaffTimeEntry.staff_id == staff_id)
    if entry_type is not None:
        q = q.where(StaffTimeEntry.entry_type == entry_type)
    result = await db.execute(q)
    return result.scalars().all()


async def _make_shift(db, staff_id, shift_date):
    shift = StaffShift(
        branch_id=1,
        staff_id=staff_id,
        shift_date=shift_date,
        shift_type=FairnessShiftType.FULL_DAY,
        status=ShiftStatus.ASSIGNED,
        scheduled_start=time(9, 0),
        scheduled_end=time(17, 0),
        scheduled_hours=8.0,
    )
    db.add(shift)
    await db.flush()
    return shift


@pytest.mark.asyncio
async def test_clock_in_records_entry(test_db, test_staff):
    now = datetime.now(timezone.utc)
    entry = await record_transition(test_db, test_staff.id, "off_duty", "available", now)
    assert entry is not None
    assert entry.entry_type == TimeEntryType.CLOCK_IN


@pytest.mark.asyncio
async def test_record_transition_raises_on_db_error(test_db, test_staff, monkeypatch):
    now = datetime.now(timezone.utc)

    async def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(test_db, "execute", boom)
    with pytest.raises(RuntimeError):
        await record_transition(test_db, test_staff.id, "off_duty", "available", now)


@pytest.mark.asyncio
async def test_clock_out_closes_dangling_break(test_db, test_staff):
    t0 = T0
    await record_transition(test_db, test_staff.id, "off_duty", "available", t0)  # clock in
    await record_transition(
        test_db, test_staff.id, "available", "on_break", t0 + timedelta(minutes=60)
    )  # break start, no end
    out = await record_transition(
        test_db, test_staff.id, "on_break", "off_duty", t0 + timedelta(minutes=90)
    )  # clock out while on break
    # 90 min elapsed, 30 min of open break => 60 min worked, not 90.
    assert out.entry_type == TimeEntryType.CLOCK_OUT
    assert out.duration_minutes == pytest.approx(60.0, abs=0.5)


@pytest.mark.asyncio
async def test_clock_in_when_presence_stale_available(test_db, test_staff):
    """A stale 'available' presence (a prior shift that never clocked out) must not
    block today's clock-in. The decision keys on today's entries, not presence."""
    now = datetime.now(timezone.utc)
    entry = await record_transition(test_db, test_staff.id, "available", "available", now)
    assert entry is not None
    assert entry.entry_type == TimeEntryType.CLOCK_IN


@pytest.mark.asyncio
async def test_clock_in_idempotent_when_already_clocked_in(test_db, test_staff):
    """Going 'available' again after a clock-in today must not create a duplicate."""
    now = T0
    first = await record_transition(test_db, test_staff.id, "off_duty", "available", now)
    assert first is not None and first.entry_type == TimeEntryType.CLOCK_IN
    second = await record_transition(
        test_db, test_staff.id, "available", "available", now + timedelta(minutes=5)
    )
    assert second is None


@pytest.mark.asyncio
async def test_break_end_closes_open_break(test_db, test_staff):
    """available after on_break, with an open break today, records a BREAK_END."""
    t0 = T0
    await record_transition(test_db, test_staff.id, "off_duty", "available", t0)  # clock in
    await record_transition(
        test_db, test_staff.id, "available", "on_break", t0 + timedelta(minutes=30)
    )  # break start
    be = await record_transition(
        test_db, test_staff.id, "on_break", "available", t0 + timedelta(minutes=45)
    )  # break end
    assert be is not None
    assert be.entry_type == TimeEntryType.BREAK_END
    assert be.duration_minutes == pytest.approx(15.0, abs=0.5)


@pytest.mark.asyncio
async def test_stale_on_break_clocks_in_not_break_end(test_db, test_staff):
    """A stale 'on_break' carried from a prior day (no open break today) must clock
    in, not record a stray BREAK_END -- the old presence status is ignored."""
    now = datetime.now(timezone.utc)
    entry = await record_transition(test_db, test_staff.id, "on_break", "available", now)
    assert entry is not None
    assert entry.entry_type == TimeEntryType.CLOCK_IN


@pytest.mark.asyncio
async def test_reclock_in_after_clock_out_starts_second_segment(test_db, test_staff):
    """An accidental clock-out or a split shift must not lock out the rest of the
    day: 'available' after a clock-out opens a second segment."""
    await record_transition(test_db, test_staff.id, "off_duty", "available", T0)
    await record_transition(
        test_db, test_staff.id, "available", "off_duty", T0 + timedelta(hours=3)
    )
    again = await record_transition(
        test_db, test_staff.id, "off_duty", "available", T0 + timedelta(hours=5)
    )
    assert again is not None
    assert again.entry_type == TimeEntryType.CLOCK_IN


@pytest.mark.asyncio
async def test_duplicate_clock_out_conflicts_and_writes_no_row(test_db, test_staff):
    """A stale tab's second clock-out must not extend paid hours: no row, 409."""
    await record_transition(test_db, test_staff.id, "off_duty", "available", T0)
    await record_transition(
        test_db, test_staff.id, "available", "off_duty", T0 + timedelta(hours=4)
    )
    with pytest.raises(HTTPException) as exc:
        await record_transition(
            test_db, test_staff.id, "available", "off_duty", T0 + timedelta(hours=6)
        )
    assert exc.value.status_code == 409
    assert len(await _entries(test_db, test_staff.id, TimeEntryType.CLOCK_OUT)) == 1


@pytest.mark.asyncio
async def test_clock_out_without_clock_in_conflicts_and_writes_no_row(test_db, test_staff):
    """Clock-out with no clock-in must not write an orphan CLOCK_OUT row."""
    with pytest.raises(HTTPException) as exc:
        await record_transition(test_db, test_staff.id, "available", "off_duty", T0)
    assert exc.value.status_code == 409
    assert len(await _entries(test_db, test_staff.id)) == 0


@pytest.mark.asyncio
async def test_break_start_without_clock_in_conflicts_and_writes_no_row(test_db, test_staff):
    """on_break while not clocked in must not fabricate a BREAK_START row."""
    with pytest.raises(HTTPException) as exc:
        await record_transition(test_db, test_staff.id, "off_duty", "on_break", T0)
    assert exc.value.status_code == 409
    assert len(await _entries(test_db, test_staff.id)) == 0


@pytest.mark.asyncio
async def test_duplicate_break_start_is_noop(test_db, test_staff):
    """A second on_break while a break is already open writes no extra row."""
    await record_transition(test_db, test_staff.id, "off_duty", "available", T0)
    await record_transition(
        test_db, test_staff.id, "available", "on_break", T0 + timedelta(hours=2)
    )
    second = await record_transition(
        test_db, test_staff.id, "on_break", "on_break", T0 + timedelta(hours=2, minutes=1)
    )
    assert second is None
    assert len(await _entries(test_db, test_staff.id, TimeEntryType.BREAK_START)) == 1


@pytest.mark.asyncio
async def test_orphan_break_start_does_not_hijack_clock_in(test_db, test_staff):
    """A stray BREAK_START with no clock-in (legacy/manual row) must not turn the
    next 'available' into a BREAK_END -- it should clock in directly."""
    test_db.add(
        StaffTimeEntry(
            staff_id=test_staff.id,
            entry_type=TimeEntryType.BREAK_START,
            recorded_at=T0,
            shift_date=date(2026, 6, 9),
        )
    )
    await test_db.flush()
    entry = await record_transition(
        test_db, test_staff.id, "off_duty", "available", T0 + timedelta(hours=1)
    )
    assert entry is not None
    assert entry.entry_type == TimeEntryType.CLOCK_IN


@pytest.mark.asyncio
async def test_cross_midnight_clock_out_closes_prior_day_segment(test_db, test_staff):
    """A clock-out after local midnight pairs with the prior local day's open
    segment instead of writing an orphan on the new date."""
    t_in = _utc(2026, 6, 10, 1, 0)  # 2026-06-09 21:00 EDT
    t_out = _utc(2026, 6, 10, 6, 0)  # 2026-06-10 02:00 EDT
    await record_transition(test_db, test_staff.id, "off_duty", "available", t_in)
    out = await record_transition(test_db, test_staff.id, "available", "off_duty", t_out)
    assert out.entry_type == TimeEntryType.CLOCK_OUT
    assert out.shift_date == date(2026, 6, 9)
    assert out.duration_minutes == pytest.approx(300.0, abs=0.5)


@pytest.mark.asyncio
async def test_cross_midnight_break_end_buckets_to_prior_day(test_db, test_staff):
    """A break ended after local midnight closes the prior day's open break, not
    a phantom next-day clock-in."""
    t_in = _utc(2026, 6, 10, 1, 0)  # 2026-06-09 21:00 EDT
    t_bs = _utc(2026, 6, 10, 3, 50)  # 2026-06-09 23:50 EDT
    t_be = _utc(2026, 6, 10, 4, 10)  # 2026-06-10 00:10 EDT
    await record_transition(test_db, test_staff.id, "off_duty", "available", t_in)
    await record_transition(test_db, test_staff.id, "available", "on_break", t_bs)
    be = await record_transition(test_db, test_staff.id, "on_break", "available", t_be)
    assert be is not None
    assert be.entry_type == TimeEntryType.BREAK_END
    assert be.shift_date == date(2026, 6, 9)
    assert be.duration_minutes == pytest.approx(20.0, abs=0.5)


@pytest.mark.asyncio
async def test_next_morning_clock_in_is_fresh_despite_dangling_punch(test_db, test_staff):
    """Yesterday's forgotten clock-out must not block or absorb a next-morning
    clock-in once the new local day has begun."""
    await record_transition(
        test_db, test_staff.id, "off_duty", "available", T0
    )  # 06-09, never clocked out
    morning = _utc(2026, 6, 10, 13, 0)  # 2026-06-10 09:00 EDT
    entry = await record_transition(test_db, test_staff.id, "available", "available", morning)
    assert entry is not None
    assert entry.entry_type == TimeEntryType.CLOCK_IN
    assert entry.shift_date == date(2026, 6, 10)


@pytest.mark.asyncio
async def test_sync_sums_split_shift_segments(test_db, test_staff):
    """actual_hours covers each segment's own span, never the off-clock gap."""
    shift = await _make_shift(test_db, test_staff.id, date(2026, 6, 9))
    await record_transition(test_db, test_staff.id, "off_duty", "available", T0)  # 09:00
    await record_transition(
        test_db, test_staff.id, "available", "off_duty", T0 + timedelta(hours=3)
    )  # 12:00
    await record_transition(
        test_db, test_staff.id, "off_duty", "available", T0 + timedelta(hours=8)
    )  # 17:00
    out2 = await record_transition(
        test_db, test_staff.id, "available", "off_duty", T0 + timedelta(hours=10)
    )  # 19:00
    assert out2.duration_minutes == pytest.approx(
        120.0, abs=0.5
    )  # second segment only, not the 10h span
    await test_db.refresh(shift)
    assert shift.actual_hours == pytest.approx(5.0, abs=0.01)
    assert shift.status == ShiftStatus.COMPLETED
    assert shift.actual_start == time(9, 0)
    assert shift.actual_end == time(19, 0)


@pytest.mark.asyncio
async def test_sync_clears_actuals_when_only_clock_out_deleted(test_db, test_staff):
    """Deleting the only clock-out must clear actual_end/actual_hours and revert
    COMPLETED so payroll cannot pay the stale hours."""
    shift = await _make_shift(test_db, test_staff.id, date(2026, 6, 9))
    await record_transition(test_db, test_staff.id, "off_duty", "available", T0)
    out = await record_transition(
        test_db, test_staff.id, "available", "off_duty", T0 + timedelta(hours=4)
    )
    await test_db.refresh(shift)
    assert shift.status == ShiftStatus.COMPLETED
    assert shift.actual_hours == pytest.approx(4.0, abs=0.01)

    await test_db.delete(out)
    await test_db.flush()
    await sync_shift_actuals(test_db, test_staff.id, date(2026, 6, 9))
    await test_db.refresh(shift)
    assert shift.actual_end is None
    assert shift.actual_hours is None
    assert shift.status != ShiftStatus.COMPLETED


@pytest.mark.asyncio
async def test_sync_zero_punches_does_not_mark_completed(test_db, test_staff):
    """sync with no punches (e.g. end-of-shift checklist with zero punches) must
    not mark the shift COMPLETED."""
    shift = await _make_shift(test_db, test_staff.id, date(2026, 6, 9))
    await sync_shift_actuals(test_db, test_staff.id, date(2026, 6, 9))
    await test_db.refresh(shift)
    assert shift.status == ShiftStatus.ASSIGNED
    assert shift.actual_hours is None


@pytest.mark.asyncio
async def test_null_duration_break_end_deducted_by_pairing(test_db, test_staff):
    """A backfilled BREAK_END with no stored duration still deducts its paired
    span from worked time and actual_hours."""
    shift = await _make_shift(test_db, test_staff.id, date(2026, 6, 9))
    await record_transition(test_db, test_staff.id, "off_duty", "available", T0)
    test_db.add(
        StaffTimeEntry(
            staff_id=test_staff.id,
            entry_type=TimeEntryType.BREAK_START,
            recorded_at=T0 + timedelta(hours=2),
            shift_date=date(2026, 6, 9),
        )
    )
    test_db.add(
        StaffTimeEntry(
            staff_id=test_staff.id,
            entry_type=TimeEntryType.BREAK_END,
            recorded_at=T0 + timedelta(hours=2, minutes=30),
            shift_date=date(2026, 6, 9),
            duration_minutes=None,
        )
    )
    await test_db.flush()
    out = await record_transition(
        test_db, test_staff.id, "available", "off_duty", T0 + timedelta(hours=8)
    )
    assert out.duration_minutes == pytest.approx(
        450.0, abs=0.5
    )  # 8h minus the 30-min backfilled break
    await test_db.refresh(shift)
    assert shift.actual_hours == pytest.approx(7.5, abs=0.01)
