"""Regression tests for the is-open 'next opening' computation.

Bug: when closed, the homepage 'Today at the library' showed today's open time
even after it had already passed (e.g. Sunday 8pm showed Sunday's 1pm open
instead of Monday's morning open). _next_open_time must roll forward.
"""
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.api.v1.library_hours import _next_open_time

TZ = ZoneInfo("America/New_York")


class _H:
    """Minimal stand-in for a LibraryHours row."""
    def __init__(self, open_time, is_closed=False):
        self.open_time = open_time
        self.is_closed = is_closed


# day_of_week: 0=Sun..6=Sat — a typical schedule (Sun 1-5, Mon-Thu 9-8, Fri 9-6, Sat 10-4)
WEEKLY = {
    0: _H(time(13, 0)),   # Sunday 1pm
    1: _H(time(9, 0)),    # Monday 9am
    2: _H(time(9, 0)),
    3: _H(time(9, 0)),
    4: _H(time(9, 0)),
    5: _H(time(9, 0)),    # Friday
    6: _H(time(10, 0)),   # Saturday 10am
}

# 2026-06-07 is a Sunday; 2026-06-08 is a Monday.
SUNDAY_EVENING = datetime(2026, 6, 7, 20, 5, tzinfo=TZ)
MONDAY_EARLY = datetime(2026, 6, 8, 7, 0, tzinfo=TZ)


def test_evening_after_close_rolls_to_next_day():
    # The bug: returned Sunday's 13:00; correct is Monday's 09:00.
    assert _next_open_time(SUNDAY_EVENING, WEEKLY) == time(9, 0)


def test_before_todays_opening_returns_today():
    # Monday 7am, opens 9am -> today's open is still ahead.
    assert _next_open_time(MONDAY_EARLY, WEEKLY) == time(9, 0)


def test_skips_a_closed_day():
    weekly = dict(WEEKLY)
    weekly[1] = _H(None, is_closed=True)   # Monday closed
    # Sunday evening -> skip Sunday (passed) and Monday (closed) -> Tuesday 09:00
    assert _next_open_time(SUNDAY_EVENING, weekly) == time(9, 0)


def test_saturday_evening_rolls_to_sunday():
    sat_evening = datetime(2026, 6, 6, 19, 0, tzinfo=TZ)   # 2026-06-06 is Saturday
    assert _next_open_time(sat_evening, WEEKLY) == time(13, 0)   # Sunday 1pm


def test_skip_today_flag_forces_tomorrow():
    # Monday 7am but today is overridden closed -> Tuesday 09:00, not today's 09:00.
    assert _next_open_time(MONDAY_EARLY, WEEKLY, skip_today=True) == time(9, 0)
