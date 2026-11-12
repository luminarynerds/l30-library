# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for app.services.event_recurrence.expand_event_instances."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo


from app.services.event_recurrence import expand_event_instances


def _fake_event(**overrides):
    """Minimal duck-typed Event for the utility — no DB needed."""
    base = dict(
        id=42,
        title="Storytime",
        description="Weekly storytime",
        location="Children's Room",
        is_virtual=False,
        virtual_link=None,
        category="Story Time",
        audience="Children",
        start_time=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 6, 2, 11, 0, tzinfo=timezone.utc),
        recurrence_rule=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_expand_event_instances_weekly_within_window():
    """Weekly Tuesday rule expands to 4 instances in a 4-week window."""
    event = _fake_event(recurrence_rule="FREQ=WEEKLY;BYDAY=TU")
    window_end = datetime(2026, 6, 30, 23, 59, tzinfo=timezone.utc)

    instances = expand_event_instances(event, window_end)

    # Tuesdays in June 2026 between Jun 2 (incl) and Jun 30 (incl): 2, 9, 16, 23, 30
    assert len(instances) == 5
    starts = [i["start_time"] for i in instances]
    assert starts[0] == datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    # Each instance carries computed end_time preserving the 1-hour duration.
    assert instances[0]["end_time"] == datetime(2026, 6, 2, 11, 0, tzinfo=timezone.utc)
    # Virtual instances carry parent linkage.
    assert all(i["id"] is None for i in instances)
    assert all(i["parent_event_id"] == 42 for i in instances)


def test_expand_event_instances_respects_until():
    """UNTIL clause caps expansion even when window_end is later."""
    event = _fake_event(
        recurrence_rule="FREQ=WEEKLY;BYDAY=TU;UNTIL=20260616T120000Z"
    )
    # Window is much wider than UNTIL.
    window_end = datetime(2026, 12, 31, tzinfo=timezone.utc)

    instances = expand_event_instances(event, window_end)

    # UNTIL is 2026-06-16T12:00 — Tuesdays Jun 2, 9, 16 all qualify.
    assert len(instances) == 3
    assert instances[-1]["start_time"] == datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc)


def test_expand_event_instances_caps_at_window_end():
    """Window_end caps expansion even for an unbounded rule."""
    event = _fake_event(recurrence_rule="FREQ=WEEKLY;BYDAY=TU")
    window_end = datetime(2026, 6, 9, 23, 59, tzinfo=timezone.utc)

    instances = expand_event_instances(event, window_end)

    # Only Jun 2 and Jun 9 should expand.
    assert len(instances) == 2
    assert instances[-1]["start_time"] == datetime(2026, 6, 9, 10, 0, tzinfo=timezone.utc)


def test_expand_event_instances_handles_dst_transition():
    """Wall-clock weekly recurrence across America/Los_Angeles spring-forward.

    Spring forward 2026: Sun Mar 8 at 02:00 PT. A weekly Sunday 10:00 PT
    series starting Mar 1 (PST, UTC-8) should produce Mar 8 at 10:00 PDT
    (UTC-7) — i.e. the wall-clock time stays 10:00 even though the UTC
    offset shifts by an hour.
    """
    pt = ZoneInfo("America/Los_Angeles")
    start = datetime(2026, 3, 1, 10, 0, tzinfo=pt)
    event = _fake_event(
        start_time=start,
        end_time=start + timedelta(hours=1),
        recurrence_rule="FREQ=WEEKLY;BYDAY=SU",
    )
    window_end = datetime(2026, 3, 23, tzinfo=pt)

    instances = expand_event_instances(event, window_end)

    # Mar 1 (PST), Mar 8 (PDT — DST starts), Mar 15 (PDT), Mar 22 (PDT)
    assert len(instances) == 4
    # All wall-clock 10:00 in America/Los_Angeles despite DST shift.
    for inst in instances:
        local = inst["start_time"].astimezone(pt)
        assert local.hour == 10, f"DST broke wall-clock for {inst['start_time']}"


def test_expand_event_instances_no_rule_returns_empty():
    """Events with no recurrence_rule expand to an empty list."""
    event = _fake_event(recurrence_rule=None)
    window_end = datetime(2027, 1, 1, tzinfo=timezone.utc)

    assert expand_event_instances(event, window_end) == []

    event2 = _fake_event(recurrence_rule="")
    assert expand_event_instances(event2, window_end) == []
