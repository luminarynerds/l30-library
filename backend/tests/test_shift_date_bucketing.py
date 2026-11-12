# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""An evening shift completed after 8pm ET must bucket to the local day, not UTC."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.api.v1.end_of_shift import _local_shift_date


def test_evening_shift_buckets_to_local_day():
    # 8:30pm EDT on 2026-06-07 == 00:30 UTC on 2026-06-08.
    utc_dt = datetime(2026, 6, 8, 0, 30, tzinfo=timezone.utc)
    assert _local_shift_date(utc_dt) == datetime(2026, 6, 7, tzinfo=ZoneInfo("America/New_York")).date()
