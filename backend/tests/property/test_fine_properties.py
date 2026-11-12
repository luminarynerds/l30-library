# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Property-based tests for fine calculation.

Targets (all pure):
  app/services/fine_policy_service.py:239 calculate_overdue_days
      (grace + day-rounding; async-declared but awaits nothing and touches
      no DB -- driven via asyncio.run on a synthetic checkout/now pair)
  app/services/fine_policy_service.py:170 calculate_fine_amount
      (rate/cap math; pure function of an in-memory FinePolicy + days)
  app/services/fine_service.py:33,:37 cents_to_dollars / dollars_to_cents

Unit adaptation in compute_fine: the test contract is int cents; l/30 is
Decimal dollars (Numeric(10,2)). cents/100 -> Decimal in, int(amount*100)
out, exact. Grace contract is whole days; l/30 stores grace_period_hours,
so days * 24. minimum_fine_amount is pinned to 0.00 and maximum_daily_fine
to None so the four contract inputs are the only live policy knobs.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from hypothesis import assume, given, strategies as st

from app.models.fine import FinePolicy, FinePolicyType
from app.services.fine_policy_service import (
    calculate_fine_amount,
    calculate_overdue_days,
)
from app.services.fine_service import cents_to_dollars, dollars_to_cents

pytestmark = pytest.mark.property

_DUE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def compute_fine(
    days_overdue: int,
    daily_rate_cents: int,
    grace_period_days: int,
    max_fine_cents: int | None,
    policy_type: FinePolicyType = FinePolicyType.daily_rate,
) -> int:
    """Total fine in cents for a checkout exactly days_overdue days late."""
    policy = FinePolicy(
        policy_type=policy_type,
        fine_per_day=Decimal(daily_rate_cents) / 100,
        grace_period_hours=grace_period_days * 24,
        maximum_cap=None if max_fine_cents is None else Decimal(max_fine_cents) / 100,
        minimum_fine_amount=Decimal("0.00"),
        maximum_daily_fine=None,
    )
    checkout = SimpleNamespace(due_date=_DUE)
    effective_days = asyncio.run(
        calculate_overdue_days(
            checkout, policy, now=_DUE + timedelta(days=days_overdue)
        )
    )
    return int(calculate_fine_amount(policy, effective_days) * 100)


@given(
    days_overdue=st.integers(min_value=0, max_value=3650),
    daily_rate=st.integers(min_value=0, max_value=10_000),
    grace=st.integers(min_value=0, max_value=60),
    max_fine=st.one_of(st.none(), st.integers(min_value=0, max_value=100_000)),
)
def test_fine_never_negative(days_overdue, daily_rate, grace, max_fine):
    fine = compute_fine(days_overdue, daily_rate, grace, max_fine)
    assert fine >= 0, "Fine went negative"


@given(
    days_overdue=st.integers(min_value=0, max_value=60),
    daily_rate=st.integers(min_value=1, max_value=1000),
    grace=st.integers(min_value=0, max_value=60),
)
def test_fine_zero_within_grace(days_overdue, daily_rate, grace):
    """No fine accrues inside the grace period. This is the off-by-one that
    charges patrons a day early."""
    assume(days_overdue <= grace)
    fine = compute_fine(days_overdue, daily_rate, grace, None)
    assert fine == 0, (
        f"Charged {fine} cents at {days_overdue} days inside {grace}-day grace"
    )


@given(
    days_overdue=st.integers(min_value=0, max_value=3650),
    daily_rate=st.integers(min_value=0, max_value=10_000),
    grace=st.integers(min_value=0, max_value=60),
    max_fine=st.integers(min_value=0, max_value=100_000),
)
def test_fine_respects_cap(days_overdue, daily_rate, grace, max_fine):
    """Includes max_fine=0: a $0 cap means no fines, not no cap. Regression
    for the falsy-Decimal bug at fine_policy_service.py:233 (shrunk
    counterexample before the fix: days=1, rate=1, grace=0, cap=0 -> 1)."""
    fine = compute_fine(days_overdue, daily_rate, grace, max_fine)
    assert fine <= max_fine, f"Fine {fine} exceeded cap {max_fine}"


@given(
    days_overdue=st.integers(min_value=0, max_value=3650),
    daily_rate=st.integers(min_value=0, max_value=10_000),
    grace=st.integers(min_value=0, max_value=60),
    max_fine=st.integers(min_value=0, max_value=100_000),
)
def test_flat_cap_policy_respects_cap(days_overdue, daily_rate, grace, max_fine):
    """Same invariant through the FinePolicyType.maximum_cap branch
    (fine_policy_service.py:219, the second falsy-cap site)."""
    fine = compute_fine(
        days_overdue, daily_rate, grace, max_fine,
        policy_type=FinePolicyType.maximum_cap,
    )
    assert fine <= max_fine, f"Flat-cap fine {fine} exceeded cap {max_fine}"


@given(
    d1=st.integers(min_value=0, max_value=3650),
    d2=st.integers(min_value=0, max_value=3650),
    daily_rate=st.integers(min_value=0, max_value=10_000),
    grace=st.integers(min_value=0, max_value=60),
)
def test_fine_monotonic_in_days(d1, d2, daily_rate, grace):
    """More overdue days never produces a smaller fine (with no cap)."""
    lo, hi = sorted((d1, d2))
    assert compute_fine(lo, daily_rate, grace, None) <= compute_fine(
        hi, daily_rate, grace, None
    ), "Fine decreased as overdue days increased"


@given(cents=st.integers(min_value=-(10**8), max_value=10**8))
def test_cents_dollars_round_trip(cents):
    """dollars_to_cents inverts cents_to_dollars exactly; payment recording
    (fine_service.py:379) depends on this conversion never losing a cent."""
    assert dollars_to_cents(cents_to_dollars(cents)) == cents


@given(cents=st.integers(min_value=0, max_value=10**8))
def test_cents_to_dollars_is_exact_two_decimal(cents):
    dollars = cents_to_dollars(cents)
    assert dollars == Decimal(cents).scaleb(-2), "Lossy cents->dollars conversion"
