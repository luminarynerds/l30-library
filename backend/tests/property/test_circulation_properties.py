# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Property-based tests for circulation policy resolution helpers.

Targets (pure, app/services/circulation_policy.py):
  :306 _precedence_rank   (which policy wins when several match)
  :340 _system_defaults   (SystemSettings -> effective defaults mapping)

There is no pure due-date function to test: due dates are inline
`utc_now() + timedelta(days=loan_period)` inside async DB methods
(checkout_service.py:253,:511; unified_circulation_service.py:486,:812).
Policy resolution itself (resolve at :54) is DB-bound; these two helpers are
its pure core.

Both helpers only read attributes, so SimpleNamespace stand-ins are used
instead of ORM instances; no mapper behavior is involved.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest
from hypothesis import given, strategies as st

from app.services.circulation_policy import (
    LOAN_PERIOD_DAYS,
    OVERDUE_FINE_PER_DAY,
    _precedence_rank,
    _system_defaults,
)

pytestmark = pytest.mark.property

_DIMS = ("collection_id", "item_type", "role", "binding")

dim_subsets = st.frozensets(st.sampled_from(_DIMS))


def policy_with(dims: frozenset[str]) -> SimpleNamespace:
    return SimpleNamespace(**{d: (object() if d in dims else None) for d in _DIMS})


@given(base=dim_subsets, extra=dim_subsets)
def test_more_specific_policy_always_ranks_first(base, extra):
    """Adding any scoping dimension to a policy must strictly improve its
    precedence (lower rank sorts first)."""
    if not (extra - base):
        return
    assert _precedence_rank(policy_with(base | extra)) < _precedence_rank(
        policy_with(base)
    )


@given(unscoped_dims=dim_subsets)
def test_collection_scope_dominates_all_other_dims(unscoped_dims):
    """A collection-scoped policy outranks ANY policy without a collection
    scope, even one scoped on every other dimension."""
    collection_policy = policy_with(frozenset({"collection_id"}))
    other = policy_with(unscoped_dims - {"collection_id"})
    assert _precedence_rank(collection_policy) < _precedence_rank(other)


@given(a=dim_subsets, b=dim_subsets)
def test_rank_ties_only_between_identical_scopes(a, b):
    """Distinct scope combinations never tie -- a tie would make the winning
    policy depend on query order."""
    if a != b:
        assert _precedence_rank(policy_with(a)) != _precedence_rank(policy_with(b))
    else:
        assert _precedence_rank(policy_with(a)) == _precedence_rank(policy_with(b))


_DEFAULT_KEYS = {
    "loan_period_days",
    "max_renewals",
    "overdue_fine_per_day",
    "max_fine",
    "grace_period_days",
    "hold_pickup_days",
    "fine_free",
}


def test_no_settings_row_yields_complete_defaults():
    defaults = _system_defaults(None)
    assert set(defaults) == _DEFAULT_KEYS
    assert defaults["loan_period_days"] == LOAN_PERIOD_DAYS
    assert defaults["overdue_fine_per_day"] == OVERDUE_FINE_PER_DAY
    assert defaults["max_fine"] == Decimal("25.00")
    assert defaults["fine_free"] is False


@given(
    loan=st.integers(min_value=1, max_value=365),
    renewals=st.integers(min_value=1, max_value=20),
    fine_per_day=st.decimals(
        min_value="0.01", max_value="99.99", places=2, allow_nan=False
    ),
    max_fine=st.decimals(
        min_value="0.01", max_value="999.99", places=2, allow_nan=False
    ),
    grace=st.integers(min_value=0, max_value=30),
    pickup=st.integers(min_value=1, max_value=30),
    fine_free_juvenile=st.booleans(),
)
def test_configured_settings_are_respected(
    loan, renewals, fine_per_day, max_fine, grace, pickup, fine_free_juvenile
):
    settings = SimpleNamespace(
        default_loan_period_days=loan,
        default_renewal_limit=renewals,
        default_overdue_fine_per_day=fine_per_day,
        default_max_fine=max_fine,
        grace_period_days=grace,
        hold_pickup_days=pickup,
        fine_free_juvenile=fine_free_juvenile,
    )
    defaults = _system_defaults(settings)
    assert defaults["loan_period_days"] == loan
    assert defaults["max_renewals"] == renewals
    assert defaults["overdue_fine_per_day"] == fine_per_day
    assert defaults["max_fine"] == max_fine
    assert defaults["grace_period_days"] == grace
    assert defaults["hold_pickup_days"] == pickup
    assert defaults["fine_free"] is fine_free_juvenile


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG (out of scope for this PR): circulation_policy.py:353 "
        "`settings.default_renewal_limit or 2` treats a stored 0 "
        "(no renewals allowed -- storable, multi_branch.py:200) as unset and "
        "silently grants 2 renewals. Same falsy family as the maximum_cap "
        "bug fixed in this PR. Needs `if ... is not None` semantics."
    ),
)
def test_zero_renewal_limit_means_no_renewals():
    settings = SimpleNamespace(
        default_loan_period_days=21,
        default_renewal_limit=0,
        default_overdue_fine_per_day=Decimal("0.25"),
        default_max_fine=Decimal("25.00"),
        grace_period_days=0,
        hold_pickup_days=7,
        fine_free_juvenile=False,
    )
    assert _system_defaults(settings)["max_renewals"] == 0
