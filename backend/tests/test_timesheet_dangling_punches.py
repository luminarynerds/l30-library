# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Dangling punches: past open days read 'incomplete' instead of growing
without bound, the nightly sweeper closes them for manager review, stale
presence rows stop haunting the desk schedule, and read endpoints fail
loudly instead of fabricating empty 200s."""
import pytest
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.models.staff_presence import PresenceStatus, StaffPresence
from app.models.staff_schedule_fairness import FairnessShiftType, ShiftStatus, StaffShift
from app.models.staff_time_entry import StaffTimeEntry, TimeEntryType

LOCAL_TZ = ZoneInfo("America/New_York")

TODAY_URL = "/api/v1/staff/timesheet/today"
SUMMARY_URL = "/api/v1/staff/timesheet/summary"
ENTRIES_URL = "/api/v1/staff/timesheet/entries"
OPEN_SHIFTS_URL = "/api/v1/staff/timesheet/open-shifts/me"
ADMIN_ENTRIES_URL = "/api/v1/staff/timesheet/staff/999999/entries"
ON_DUTY_URL = "/api/v1/staff/presence/on-duty"
PRESENCE_ME_URL = "/api/v1/staff/presence/me"
DESK_URL = "/api/v1/staff/desk-schedule/today"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _local_today() -> date:
    return _now().astimezone(LOCAL_TZ).date()


def _local_dt(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=LOCAL_TZ).astimezone(timezone.utc)


def _entry(staff_id, entry_type, recorded_at, shift_date, **kw):
    return StaffTimeEntry(
        staff_id=staff_id,
        entry_type=entry_type,
        recorded_at=recorded_at,
        shift_date=shift_date,
        **kw,
    )


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


async def _add_presence(db, staff_id, status=PresenceStatus.AVAILABLE, changed_at=None):
    changed_at = changed_at or _now()
    presence = StaffPresence(
        staff_id=staff_id,
        status=status,
        status_changed_at=changed_at,
        shift_started_at=changed_at,
    )
    db.add(presence)
    await db.flush()
    return presence


# ---------------------------------------------------------------------------
# 1. Day display: live elapsed only applies to today
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_past_open_punch_reads_incomplete_not_growing(staff_client, test_db, test_staff):
    """A clock-in left open three days ago must not render as a 70-hour day."""
    day = _local_today() - timedelta(days=3)
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, _local_dt(day, 9), day))
    await test_db.flush()

    r = await staff_client.get(SUMMARY_URL, params={
        "start_date": (day - timedelta(days=1)).isoformat(),
        "end_date": _local_today().isoformat(),
    })
    assert r.status_code == 200, r.text
    body = r.json()
    day_row = next(d for d in body["days"] if d["shift_date"] == day.isoformat())
    assert day_row["status"] == "incomplete"
    assert day_row["total_worked_hours"] is None
    assert body["total_worked_hours"] == 0


@pytest.mark.asyncio
async def test_past_split_shift_counts_only_closed_segments(staff_client, test_db, test_staff):
    """Closed segments still count on an incomplete day; the open one adds 0."""
    day = _local_today() - timedelta(days=2)
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, _local_dt(day, 9), day))
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_OUT, _local_dt(day, 13), day))
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, _local_dt(day, 14), day))
    await test_db.flush()

    r = await staff_client.get(SUMMARY_URL, params={
        "start_date": day.isoformat(),
        "end_date": day.isoformat(),
    })
    assert r.status_code == 200, r.text
    day_row = r.json()["days"][0]
    assert day_row["status"] == "incomplete"
    assert day_row["total_worked_hours"] == pytest.approx(4.0, abs=0.01)


@pytest.mark.asyncio
async def test_today_open_punch_still_counts_live(staff_client, test_db, test_staff):
    """Today's open shift keeps the live now-minus-clock-in display."""
    test_db.add(_entry(
        test_staff.id, TimeEntryType.CLOCK_IN, _now() - timedelta(hours=2), _local_today()))
    await test_db.flush()

    r = await staff_client.get(TODAY_URL)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "in_progress"
    assert 1.9 <= body["total_worked_hours"] <= 2.1


@pytest.mark.asyncio
async def test_today_re_clock_in_reads_in_progress(staff_client, test_db, test_staff):
    """A second session today (split shift) renders in_progress, and the
    midday gap is not counted as worked."""
    today = _local_today()
    now = _now()
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, now - timedelta(hours=4), today))
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_OUT, now - timedelta(hours=3), today))
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, now - timedelta(hours=1), today))
    await test_db.flush()

    r = await staff_client.get(TODAY_URL)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "in_progress"
    assert body["total_worked_hours"] == pytest.approx(2.0, abs=0.05)


# ---------------------------------------------------------------------------
# 2. Nightly sweeper: auto-close punches open past local end-of-day
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sweeper_closes_at_scheduled_shift_end(test_db, test_staff):
    from app.services.time_entry_service import close_dangling_punches
    day = _local_today() - timedelta(days=2)
    shift = await _make_shift(test_db, test_staff.id, day)
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, _local_dt(day, 9), day))
    await test_db.flush()

    closed = await close_dangling_punches(test_db, _now())
    assert closed == 1

    result = await test_db.execute(select(StaffTimeEntry).where(
        StaffTimeEntry.staff_id == test_staff.id,
        StaffTimeEntry.entry_type == TimeEntryType.CLOCK_OUT,
    ))
    co = result.scalars().one()
    assert co.recorded_at == _local_dt(day, 17)
    assert (co.notes or "").startswith("auto-closed")
    assert co.duration_minutes == pytest.approx(480, abs=0.5)

    await test_db.refresh(shift)
    assert shift.actual_hours == pytest.approx(8.0, abs=0.01)


@pytest.mark.asyncio
async def test_sweeper_falls_back_to_local_midnight(test_db, test_staff):
    from app.services.time_entry_service import close_dangling_punches
    day = _local_today() - timedelta(days=1)
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, _local_dt(day, 22), day))
    await test_db.flush()

    closed = await close_dangling_punches(test_db, _now())
    assert closed == 1

    result = await test_db.execute(select(StaffTimeEntry).where(
        StaffTimeEntry.staff_id == test_staff.id,
        StaffTimeEntry.entry_type == TimeEntryType.CLOCK_OUT,
    ))
    co = result.scalars().one()
    assert co.recorded_at == _local_dt(day + timedelta(days=1), 0)
    assert co.duration_minutes == pytest.approx(120, abs=0.5)


@pytest.mark.asyncio
async def test_sweeper_closes_open_break_with_the_day(test_db, test_staff):
    from app.services.time_entry_service import close_dangling_punches
    day = _local_today() - timedelta(days=2)
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, _local_dt(day, 9), day))
    test_db.add(_entry(test_staff.id, TimeEntryType.BREAK_START, _local_dt(day, 12), day))
    await test_db.flush()

    closed = await close_dangling_punches(test_db, _now())
    assert closed == 1

    result = await test_db.execute(select(StaffTimeEntry).where(
        StaffTimeEntry.staff_id == test_staff.id,
        StaffTimeEntry.entry_type == TimeEntryType.BREAK_END,
    ))
    be = result.scalars().one()
    assert be.duration_minutes == pytest.approx(720, abs=0.5)

    result = await test_db.execute(select(StaffTimeEntry).where(
        StaffTimeEntry.staff_id == test_staff.id,
        StaffTimeEntry.entry_type == TimeEntryType.CLOCK_OUT,
    ))
    co = result.scalars().one()
    assert co.duration_minutes == pytest.approx(180, abs=0.5)


@pytest.mark.asyncio
async def test_sweeper_resets_stale_presence(test_db, test_staff):
    from app.services.time_entry_service import close_dangling_punches
    day = _local_today() - timedelta(days=1)
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, _local_dt(day, 9), day))
    presence = await _add_presence(test_db, test_staff.id, changed_at=_local_dt(day, 9))

    closed = await close_dangling_punches(test_db, _now())
    assert closed == 1

    await test_db.refresh(presence)
    assert presence.status == PresenceStatus.OFF_DUTY


@pytest.mark.asyncio
async def test_sweeper_leaves_today_alone(test_db, test_staff):
    from app.services.time_entry_service import close_dangling_punches
    test_db.add(_entry(
        test_staff.id, TimeEntryType.CLOCK_IN, _now() - timedelta(hours=1), _local_today()))
    presence = await _add_presence(test_db, test_staff.id)

    closed = await close_dangling_punches(test_db, _now())
    assert closed == 0

    result = await test_db.execute(select(StaffTimeEntry).where(
        StaffTimeEntry.staff_id == test_staff.id,
        StaffTimeEntry.entry_type == TimeEntryType.CLOCK_OUT,
    ))
    assert result.scalars().all() == []
    await test_db.refresh(presence)
    assert presence.status == PresenceStatus.AVAILABLE


# ---------------------------------------------------------------------------
# 3. Auto-closed days stay reviewable in /open-shifts/me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auto_closed_day_still_surfaces_for_review(staff_client, test_db, test_staff):
    from app.services.time_entry_service import close_dangling_punches
    swept_day = _local_today() - timedelta(days=1)
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, _local_dt(swept_day, 9), swept_day))
    await test_db.flush()
    assert await close_dangling_punches(test_db, _now()) == 1

    open_day = _local_today() - timedelta(days=2)
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, _local_dt(open_day, 9), open_day))
    await test_db.flush()

    r = await staff_client.get(OPEN_SHIFTS_URL, params={"days": 7})
    assert r.status_code == 200, r.text
    rows = {row["shift_date"]: row for row in r.json()}
    assert rows[swept_day.isoformat()]["auto_closed"] is True
    assert rows[open_day.isoformat()]["auto_closed"] is False


@pytest.mark.asyncio
async def test_reviewed_auto_close_stops_surfacing(staff_client, test_db, test_staff):
    """Once a manager edits the auto-closed punch (edits append an 'edited by'
    audit note), the day counts as closed."""
    day = _local_today() - timedelta(days=1)
    test_db.add(_entry(test_staff.id, TimeEntryType.CLOCK_IN, _local_dt(day, 9), day))
    test_db.add(_entry(
        test_staff.id, TimeEntryType.CLOCK_OUT, _local_dt(day, 17), day,
        notes="auto-closed -- no clock-out was recorded, needs manager review; edited by Sam (admin id=1)",
    ))
    await test_db.flush()

    r = await staff_client.get(OPEN_SHIFTS_URL, params={"days": 7})
    assert r.status_code == 200, r.text
    assert all(row["shift_date"] != day.isoformat() for row in r.json())


# ---------------------------------------------------------------------------
# 4. Cross-day presence: yesterday's rows are not coverage today
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_on_duty_hides_yesterday_presence(staff_client, test_db, test_staff):
    await _add_presence(test_db, test_staff.id, changed_at=_now() - timedelta(days=1))

    r = await staff_client.get(ON_DUTY_URL)
    assert r.status_code == 200, r.text
    assert all(row["staff_id"] != test_staff.id for row in r.json())


@pytest.mark.asyncio
async def test_on_duty_lists_today_presence(staff_client, test_db, test_staff):
    await _add_presence(test_db, test_staff.id)

    r = await staff_client.get(ON_DUTY_URL)
    assert r.status_code == 200, r.text
    assert any(row["staff_id"] == test_staff.id for row in r.json())


@pytest.mark.asyncio
async def test_desk_schedule_hides_yesterday_presence(staff_client, test_db, test_staff):
    await _add_presence(test_db, test_staff.id, changed_at=_now() - timedelta(days=1))

    r = await staff_client.get(DESK_URL)
    assert r.status_code == 200, r.text
    body = r.json()
    listed = [
        s["staff_id"]
        for bucket in ("on_duty", "on_break", "present_unscheduled")
        for s in body[bucket]
    ]
    assert test_staff.id not in listed


@pytest.mark.asyncio
async def test_desk_schedule_buckets_needs_help(staff_client, test_db, test_staff):
    await _add_presence(test_db, test_staff.id, status=PresenceStatus.NEEDS_HELP)

    r = await staff_client.get(DESK_URL)
    assert r.status_code == 200, r.text
    body = r.json()
    assert any(s["staff_id"] == test_staff.id for s in body["needs_help"])
    assert all(s["staff_id"] != test_staff.id for s in body["on_duty"])
    assert all(s["staff_id"] != test_staff.id for s in body["present_unscheduled"])


# ---------------------------------------------------------------------------
# 5. Read endpoints fail loudly: forced repository error -> 5xx, not empty 200
# ---------------------------------------------------------------------------

class _BrokenSession:
    async def execute(self, *args, **kwargs):
        raise RuntimeError("forced database failure")


@pytest.fixture
async def broken_db_client(test_admin):
    """Authed client whose request-scoped db session fails on first use."""
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    async def override_get_db():
        yield _BrokenSession()

    async def override_get_current_user():
        return test_admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("url,params", [
    (TODAY_URL, None),
    (SUMMARY_URL, {"start_date": "2026-06-01", "end_date": "2026-06-07"}),
    (ENTRIES_URL, None),
    (OPEN_SHIFTS_URL, None),
    (ADMIN_ENTRIES_URL, None),
    (ON_DUTY_URL, None),
    (PRESENCE_ME_URL, None),
    (DESK_URL, None),
])
async def test_db_failure_yields_5xx_not_empty_200(broken_db_client, url, params):
    r = await broken_db_client.get(url, params=params)
    assert r.status_code >= 500, f"{url} -> {r.status_code}: {r.text[:200]}"


@pytest.mark.asyncio
async def test_presence_me_without_row_is_still_off_duty_200(staff_client):
    """The deliberate empty state survives: no presence row is a clean off_duty,
    not an error."""
    r = await staff_client.get(PRESENCE_ME_URL)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "off_duty"
