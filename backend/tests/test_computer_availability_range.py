# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hourly slot builder for computer availability (the all-computers grid core)."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.api.v1.computers import _build_hourly_slots

ET = ZoneInfo("America/New_York")


def _res(start_local: datetime, end_local: datetime) -> SimpleNamespace:
    """A reservation stub with UTC-stored start/end, like the real rows."""
    return SimpleNamespace(
        reserved_start_time=start_local.astimezone(timezone.utc),
        reserved_end_time=end_local.astimezone(timezone.utc),
    )


def test_all_free_when_no_reservations():
    open_dt = datetime(2026, 6, 9, 9, 0, tzinfo=ET)
    close_dt = datetime(2026, 6, 9, 13, 0, tzinfo=ET)
    slots = _build_hourly_slots(open_dt, close_dt, [])
    assert len(slots) == 4
    assert all(s.is_available for s in slots)
    # Slots are tz-aware UTC, exactly one hour each.
    assert slots[0].start_time.tzinfo is not None
    assert slots[0].end_time - slots[0].start_time == timedelta(hours=1)


def test_overlapping_reservation_marks_that_slot_busy():
    open_dt = datetime(2026, 6, 9, 9, 0, tzinfo=ET)
    close_dt = datetime(2026, 6, 9, 12, 0, tzinfo=ET)  # 9, 10, 11 -> 3 slots
    reservations = [_res(datetime(2026, 6, 9, 10, 0, tzinfo=ET), datetime(2026, 6, 9, 11, 0, tzinfo=ET))]
    slots = _build_hourly_slots(open_dt, close_dt, reservations)
    assert [s.is_available for s in slots] == [True, False, True]


def test_no_full_hour_window_yields_no_slots():
    open_dt = datetime(2026, 6, 9, 9, 0, tzinfo=ET)
    close_dt = datetime(2026, 6, 9, 9, 30, tzinfo=ET)
    assert _build_hourly_slots(open_dt, close_dt, []) == []
