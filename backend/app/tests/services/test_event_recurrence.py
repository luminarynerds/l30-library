# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the event recurrence expander.

Focus: weekday correctness. A weekly series with BYDAY must land every
generated instance on the intended weekday, and a non-BYDAY weekly rule must
repeat on the dtstart's own weekday. These lock in the behavior that the
patron /events page depends on (no "Tech Help Tuesday" showing on a Saturday).
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.event_recurrence import expand_event_instances


def _event(start, *, rule, duration_minutes=90, title="Sample Event"):
    return SimpleNamespace(
        id=1,
        start_time=start,
        end_time=start + timedelta(minutes=duration_minutes),
        recurrence_rule=rule,
        title=title,
        description=None,
        location=None,
        is_virtual=False,
        virtual_link=None,
        category=None,
        audience=None,
    )


def test_no_rule_returns_nothing():
    ev = _event(datetime(2026, 6, 9, 14, 0, tzinfo=timezone.utc), rule=None)
    assert expand_event_instances(ev, datetime(2026, 12, 1, tzinfo=timezone.utc)) == []


def test_weekly_byday_keeps_intended_weekday():
    # dtstart is a Tuesday; BYDAY=TU should keep every instance on Tuesday.
    start = datetime(2026, 6, 9, 14, 0, tzinfo=timezone.utc)  # Tuesday
    assert start.weekday() == 1
    ev = _event(start, rule="FREQ=WEEKLY;BYDAY=TU;COUNT=5")
    instances = expand_event_instances(ev, datetime(2026, 8, 1, tzinfo=timezone.utc))

    assert len(instances) == 5
    assert all(i["start_time"].weekday() == 1 for i in instances)  # all Tuesdays
    # Consecutive Tuesdays, clock time preserved, duration preserved.
    for idx, inst in enumerate(instances):
        assert inst["start_time"] == start + timedelta(weeks=idx)
        assert inst["end_time"] - inst["start_time"] == timedelta(minutes=90)


def test_byday_overrides_a_mismatched_dtstart_weekday():
    # dtstart is a Saturday but the rule targets Tuesdays. The expander must
    # honor BYDAY and emit Tuesdays only, never the Saturday anchor.
    start = datetime(2026, 6, 13, 14, 0, tzinfo=timezone.utc)  # Saturday
    assert start.weekday() == 5
    ev = _event(start, rule="FREQ=WEEKLY;BYDAY=TU;COUNT=3", title="Tech Help Tuesday")
    instances = expand_event_instances(ev, datetime(2026, 8, 1, tzinfo=timezone.utc))

    assert len(instances) == 3
    assert all(i["start_time"].weekday() == 1 for i in instances)
    assert all(i["start_time"].date() > start.date() for i in instances)


def test_weekly_without_byday_repeats_on_dtstart_weekday():
    start = datetime(2026, 6, 11, 18, 0, tzinfo=timezone.utc)  # Thursday
    assert start.weekday() == 3
    ev = _event(start, rule="FREQ=WEEKLY;COUNT=4")
    instances = expand_event_instances(ev, datetime(2026, 9, 1, tzinfo=timezone.utc))

    assert len(instances) == 4
    assert all(i["start_time"].weekday() == 3 for i in instances)  # all Thursdays


def test_window_end_bounds_instances():
    start = datetime(2026, 6, 9, 14, 0, tzinfo=timezone.utc)  # Tuesday
    ev = _event(start, rule="FREQ=WEEKLY;BYDAY=TU")
    window_end = start + timedelta(weeks=2, days=1)
    instances = expand_event_instances(ev, window_end)

    # Tuesdays at weeks 0, 1, 2 fall within the window; week 3 does not.
    assert len(instances) == 3
    assert all(i["start_time"] <= window_end for i in instances)


def test_microsecond_dtstart_still_yields_first_occurrence():
    # DB-stored datetimes can carry microseconds; the 1-second lookback in the
    # expander must still capture the dtstart occurrence.
    start = datetime(2026, 6, 9, 14, 0, 0, 151466, tzinfo=timezone.utc)  # Tuesday
    ev = _event(start, rule="FREQ=WEEKLY;BYDAY=TU;COUNT=2")
    instances = expand_event_instances(ev, datetime(2026, 7, 1, tzinfo=timezone.utc))

    assert len(instances) == 2
    assert instances[0]["start_time"].weekday() == 1
