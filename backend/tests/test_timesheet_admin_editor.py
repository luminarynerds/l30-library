# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Admin timesheet editor: every edit re-syncs payroll actuals, future or
incoherent punches are rejected, and resolving a dangling punch resets presence."""
import pytest
from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy import select
from app.models.staff_presence import PresenceStatus, StaffPresence
from app.models.staff_schedule_fairness import FairnessShiftType, ShiftStatus, StaffShift
from app.models.staff_time_entry import StaffTimeEntry, TimeEntryType
from app.services.time_entry_service import record_transition

ENTRIES_URL = "/api/v1/staff/timesheet/entries"

# A fixed past day keeps assertions deterministic; presence tests that depend on
# "today" use the wall clock explicitly.
D0 = date(2026, 6, 9)
T0 = datetime(2026, 6, 9, 13, 0, tzinfo=timezone.utc)  # 09:00 EDT
OLD_DAY = date(2026, 6, 1)
OLD_T = datetime(2026, 6, 1, 13, 0, tzinfo=timezone.utc)


@pytest.fixture
async def admin_client(test_db, test_admin):
    """Async HTTP client authenticated as an admin user."""
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return test_admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


async def _make_shift(db, staff_id, shift_date=D0):
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


async def _completed_day(db, staff_id):
    """Clock in at T0 and out at T0+8h through the real punch flow."""
    await record_transition(db, staff_id, "off_duty", "available", T0)
    await record_transition(db, staff_id, "available", "off_duty", T0 + timedelta(hours=8))


async def _entry_id(db, staff_id, entry_type):
    result = await db.execute(
        select(StaffTimeEntry).where(
            StaffTimeEntry.staff_id == staff_id,
            StaffTimeEntry.entry_type == entry_type,
        )
    )
    return result.scalars().first().id


async def _entry_count(db, staff_id, entry_type=None):
    q = select(StaffTimeEntry).where(StaffTimeEntry.staff_id == staff_id)
    if entry_type is not None:
        q = q.where(StaffTimeEntry.entry_type == entry_type)
    result = await db.execute(q)
    return len(result.scalars().all())


async def _add_presence(db, staff_id, status=PresenceStatus.AVAILABLE):
    presence = StaffPresence(
        staff_id=staff_id,
        status=status,
        status_changed_at=OLD_T,
        shift_started_at=OLD_T,
    )
    db.add(presence)
    await db.flush()
    return presence


def _create_payload(staff_id, entry_type, recorded_at, shift_date=D0):
    return {
        "staff_id": staff_id,
        "entry_type": entry_type,
        "recorded_at": recorded_at.isoformat(),
        "shift_date": shift_date.isoformat(),
    }


# ---------------------------------------------------------------------------
# 1. Re-sync on every entry type
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manual_break_backfill_drops_actual_hours(admin_client, test_db, test_staff):
    """The documented manager workflow (backfill a missed lunch) must reduce
    payroll actual_hours, not just the displayed day."""
    shift = await _make_shift(test_db, test_staff.id)
    await _completed_day(test_db, test_staff.id)
    await test_db.refresh(shift)
    assert shift.actual_hours == pytest.approx(8.0, abs=0.01)

    r1 = await admin_client.post(ENTRIES_URL, json=_create_payload(
        test_staff.id, "break_start", T0 + timedelta(hours=2)))
    assert r1.status_code == 201, r1.text
    r2 = await admin_client.post(ENTRIES_URL, json=_create_payload(
        test_staff.id, "break_end", T0 + timedelta(hours=2, minutes=30)))
    assert r2.status_code == 201, r2.text

    await test_db.refresh(shift)
    assert shift.actual_hours == pytest.approx(7.5, abs=0.01)


@pytest.mark.asyncio
async def test_edit_clock_in_resyncs_actuals(admin_client, test_db, test_staff):
    """Correcting a clock-in time (the most common fix) must reach payroll."""
    shift = await _make_shift(test_db, test_staff.id)
    await _completed_day(test_db, test_staff.id)
    ci_id = await _entry_id(test_db, test_staff.id, TimeEntryType.CLOCK_IN)

    r = await admin_client.patch(f"{ENTRIES_URL}/{ci_id}", json={
        "recorded_at": (T0 + timedelta(hours=1)).isoformat(),
    })
    assert r.status_code == 200, r.text

    await test_db.refresh(shift)
    assert shift.actual_hours == pytest.approx(7.0, abs=0.01)
    assert shift.actual_start == time(10, 0)


@pytest.mark.asyncio
async def test_delete_clock_in_clears_actuals_and_reverts_completed(admin_client, test_db, test_staff):
    """Deleting a clock-in leaves no closed segment: actuals must clear and the
    shift must drop out of the payroll-eligible COMPLETED state."""
    shift = await _make_shift(test_db, test_staff.id)
    await _completed_day(test_db, test_staff.id)
    ci_id = await _entry_id(test_db, test_staff.id, TimeEntryType.CLOCK_IN)

    r = await admin_client.delete(f"{ENTRIES_URL}/{ci_id}")
    assert r.status_code == 204, r.text

    await test_db.refresh(shift)
    assert shift.actual_hours is None
    assert shift.status != ShiftStatus.COMPLETED


# ---------------------------------------------------------------------------
# 2. Validation: future timestamps and incoherent segments -> 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_rejects_future_timestamp(admin_client, test_db, test_staff):
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    r = await admin_client.post(ENTRIES_URL, json=_create_payload(
        test_staff.id, "clock_in", future))
    assert r.status_code == 422, r.text
    body = r.json()
    detail = body.get("detail") or body.get("error", {}).get("message", "")
    assert "future" in detail.lower()
    assert await _entry_count(test_db, test_staff.id) == 0


@pytest.mark.asyncio
async def test_create_rejects_clock_out_before_clock_in(admin_client, test_db, test_staff):
    await record_transition(test_db, test_staff.id, "off_duty", "available", T0)
    r = await admin_client.post(ENTRIES_URL, json=_create_payload(
        test_staff.id, "clock_out", T0 - timedelta(hours=1)))
    assert r.status_code == 422, r.text
    assert await _entry_count(test_db, test_staff.id, TimeEntryType.CLOCK_OUT) == 0


@pytest.mark.asyncio
async def test_edit_rejects_clock_out_before_clock_in(admin_client, test_db, test_staff):
    await _completed_day(test_db, test_staff.id)
    co_id = await _entry_id(test_db, test_staff.id, TimeEntryType.CLOCK_OUT)

    r = await admin_client.patch(f"{ENTRIES_URL}/{co_id}", json={
        "recorded_at": (T0 - timedelta(hours=1)).isoformat(),
    })
    assert r.status_code == 422, r.text

    result = await test_db.execute(
        select(StaffTimeEntry).where(StaffTimeEntry.id == co_id)
    )
    assert result.scalar_one().recorded_at == T0 + timedelta(hours=8)


@pytest.mark.asyncio
async def test_repair_of_already_orphaned_day_is_allowed(admin_client, test_db, test_staff):
    """A day that already has an orphan clock-out (legacy data) must accept the
    repair: adding the missing clock-in before it."""
    test_db.add(StaffTimeEntry(
        staff_id=test_staff.id,
        entry_type=TimeEntryType.CLOCK_OUT,
        recorded_at=T0 + timedelta(hours=8),
        shift_date=D0,
    ))
    await test_db.flush()

    r = await admin_client.post(ENTRIES_URL, json=_create_payload(
        test_staff.id, "clock_in", T0))
    assert r.status_code == 201, r.text


# ---------------------------------------------------------------------------
# 3. Presence reset when a dangling punch is resolved
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_closing_dangling_punch_resets_presence(admin_client, test_db, test_staff):
    """Manager backfills the missing clock-out for an old dangling punch: the
    stale 'available' presence row must reset to off_duty."""
    test_db.add(StaffTimeEntry(
        staff_id=test_staff.id,
        entry_type=TimeEntryType.CLOCK_IN,
        recorded_at=OLD_T,
        shift_date=OLD_DAY,
    ))
    presence = await _add_presence(test_db, test_staff.id)

    r = await admin_client.post(ENTRIES_URL, json=_create_payload(
        test_staff.id, "clock_out", OLD_T + timedelta(hours=8), OLD_DAY))
    assert r.status_code == 201, r.text

    await test_db.refresh(presence)
    assert presence.status == PresenceStatus.OFF_DUTY


@pytest.mark.asyncio
async def test_presence_kept_when_open_segment_remains_today(admin_client, test_db, test_staff):
    """Cleaning up an old dangling punch must not clock out someone who is
    legitimately on shift right now."""
    test_db.add(StaffTimeEntry(
        staff_id=test_staff.id,
        entry_type=TimeEntryType.CLOCK_IN,
        recorded_at=OLD_T,
        shift_date=OLD_DAY,
    ))
    await test_db.flush()
    await record_transition(
        test_db, test_staff.id, "off_duty", "available", datetime.now(timezone.utc))
    presence = await _add_presence(test_db, test_staff.id)

    r = await admin_client.post(ENTRIES_URL, json=_create_payload(
        test_staff.id, "clock_out", OLD_T + timedelta(hours=8), OLD_DAY))
    assert r.status_code == 201, r.text

    await test_db.refresh(presence)
    assert presence.status == PresenceStatus.AVAILABLE


@pytest.mark.asyncio
async def test_deleting_accidental_clock_in_resets_presence(admin_client, test_db, test_staff):
    """Deleting today's accidental clock-in leaves no open segment, so the
    phantom 'available' must clear."""
    entry = await record_transition(
        test_db, test_staff.id, "off_duty", "available", datetime.now(timezone.utc))
    presence = await _add_presence(test_db, test_staff.id)

    r = await admin_client.delete(f"{ENTRIES_URL}/{entry.id}")
    assert r.status_code == 204, r.text

    await test_db.refresh(presence)
    assert presence.status == PresenceStatus.OFF_DUTY
