# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Property-based tests for hold expiration predicates.

Targets (pure, app/services/hold_service.py):
  :82 get_effective_expiration  (explicit expires_at, else notified_at fallback)
  :99 is_hold_expired           (status gate + strict-past comparison)

Deliberately NOT covered here: queue position math. Position assignment is a
SELECT max(position) under pg_advisory_xact_lock (hold_service.py:311) and
cancel/expire compaction is a SQL UPDATE position = position - 1
(hold_service.py:135,:214). There is no pure queue function to property-test;
that behavior belongs in DB-backed integration tests.
"""
from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, strategies as st

from app.core.circulation_config import HOLD_EXPIRY_DAYS
from app.models.circulation import Hold, HoldStatus
from app.services.hold_service import get_effective_expiration, is_hold_expired

pytestmark = pytest.mark.property

aware_dts = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2035, 12, 31),
    timezones=st.just(timezone.utc),
)
naive_dts = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2035, 12, 31),
)
non_ready_statuses = st.sampled_from(
    [s for s in HoldStatus if s != HoldStatus.ready]
)


def make_hold(status, expires_at=None, notified_at=None) -> Hold:
    return Hold(status=status, expires_at=expires_at, notified_at=notified_at)


@given(
    status=non_ready_statuses,
    expires_at=st.one_of(st.none(), aware_dts),
    notified_at=st.one_of(st.none(), aware_dts),
    now=aware_dts,
)
def test_non_ready_hold_never_expired(status, expires_at, notified_at, now):
    """Only ready holds can expire off the shelf; pending/fulfilled/cancelled/
    expired holds must not flip, no matter what their timestamps say."""
    hold = make_hold(status, expires_at, notified_at)
    assert is_hold_expired(hold, now=now) is False


@given(expires_at=aware_dts, notified_at=st.one_of(st.none(), aware_dts))
def test_explicit_expiration_wins(expires_at, notified_at):
    """An explicit expires_at always takes precedence over the notified_at
    fallback."""
    hold = make_hold(HoldStatus.ready, expires_at, notified_at)
    assert get_effective_expiration(hold) == expires_at


@given(notified_at=aware_dts)
def test_notified_fallback_adds_expiry_window(notified_at):
    """Ready hold with NULL expires_at falls back to notified_at +
    HOLD_EXPIRY_DAYS (legacy rows from before expires_at was stamped)."""
    hold = make_hold(HoldStatus.ready, None, notified_at)
    assert get_effective_expiration(hold) == notified_at + timedelta(
        days=HOLD_EXPIRY_DAYS
    )


@given(now=aware_dts)
def test_no_timestamps_means_never_expired(now):
    hold = make_hold(HoldStatus.ready)
    assert get_effective_expiration(hold) is None
    assert is_hold_expired(hold, now=now) is False


@given(expires_at=aware_dts, now=aware_dts)
def test_expired_iff_strictly_past(expires_at, now):
    """A ready hold is expired exactly when its expiration is strictly before
    now -- at the boundary instant the patron can still pick up."""
    hold = make_hold(HoldStatus.ready, expires_at)
    assert is_hold_expired(hold, now=now) is (expires_at < now)


@given(
    expires_at=aware_dts,
    now=aware_dts,
    later_by=st.timedeltas(min_value=timedelta(0), max_value=timedelta(days=3650)),
)
def test_expiry_monotonic_in_time(expires_at, now, later_by):
    """Once expired, a hold stays expired as the clock advances."""
    hold = make_hold(HoldStatus.ready, expires_at)
    if is_hold_expired(hold, now=now):
        assert is_hold_expired(hold, now=now + later_by)


@given(expires_at=naive_dts, now=aware_dts)
def test_naive_expiration_treated_as_utc(expires_at, now):
    """Legacy naive datetimes must behave exactly like the same instant
    tagged UTC (hold_service.py:93 _ensure_utc)."""
    naive_hold = make_hold(HoldStatus.ready, expires_at)
    aware_hold = make_hold(
        HoldStatus.ready, expires_at.replace(tzinfo=timezone.utc)
    )
    assert is_hold_expired(naive_hold, now=now) == is_hold_expired(
        aware_hold, now=now
    )
