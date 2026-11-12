# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from dateutil.rrule import rrulestr

if TYPE_CHECKING:  # pragma: no cover
    from ..models.event import Event


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def expand_event_instances(
    event: "Event", window_end: datetime
) -> list[dict[str, Any]]:
    if not event.recurrence_rule:
        return []

    dtstart = _ensure_aware(event.start_time)
    window_end_aware = _ensure_aware(window_end)

    rule = rrulestr(event.recurrence_rule, dtstart=dtstart)

    # rrule.between(after, before, inc=True) returns instances within [after, before].
    # dateutil's rrule generator truncates microseconds, so when dtstart has
    # microsecond precision (as DB-stored datetimes typically do) the first
    # generated occurrence is < dtstart and would be dropped by `between`.
    # Use a 1-second lookback as the actual "tiny lookback" promised by the
    # original comment so dtstart's occurrence is reliably captured.
    occurrences = rule.between(
        dtstart - timedelta(seconds=1), window_end_aware, inc=True
    )

    # Compute end_time offset once if both present.
    duration = None
    if event.end_time is not None:
        duration = _ensure_aware(event.end_time) - dtstart

    out: list[dict[str, Any]] = []
    for occ in occurrences:
        if occ > window_end_aware:
            break  # belt-and-suspenders; rrule.between should already exclude
        end_time = occ + duration if duration is not None else None
        out.append(
            {
                "id": None,
                "parent_event_id": event.id,
                "start_time": occ,
                "end_time": end_time,
                "title": event.title,
                "description": event.description,
                "location": event.location,
                "is_virtual": event.is_virtual,
                "virtual_link": event.virtual_link,
                "category": event.category,
                "audience": event.audience,
            }
        )
    return out
