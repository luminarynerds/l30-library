# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the circulation_policy resolver.

Verifies the (collection x role x item_type x binding) precedence walk and
per-field fallback against system_settings.
"""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.catalog import CatalogItem, ItemType
from app.models.circulation_policy import BookBinding, CirculationPolicy
from app.models.user import User, UserRole
from app.services.circulation_policy import (
    _precedence_rank,
    get_loan_period_days,
    get_overdue_fine_per_day,
    resolve,
)


# --- helpers ---------------------------------------------------------------


def make_policy(
    *,
    role=None,
    item_type=None,
    binding=None,
    collection_id=None,
    loan_period_days=None,
    max_renewals=None,
    overdue_fine_per_day=None,
    max_fine=None,
    grace_period_days=None,
    hold_pickup_days=None,
    fine_free=None,
    library_system_id=1,
):
    p = CirculationPolicy()
    p.library_system_id = library_system_id
    p.role = role
    p.item_type = item_type
    p.binding = binding
    p.collection_id = collection_id
    p.loan_period_days = loan_period_days
    p.max_renewals = max_renewals
    p.overdue_fine_per_day = overdue_fine_per_day
    p.max_fine = max_fine
    p.grace_period_days = grace_period_days
    p.hold_pickup_days = hold_pickup_days
    p.fine_free = fine_free
    p.active = True
    return p


def make_user(role=UserRole.PATRON, library_system_id=1):
    u = User()
    u.id = 99
    u.role = role
    u.library_system_id = library_system_id
    return u


def make_item(item_type=ItemType.book, binding=None):
    i = CatalogItem()
    i.id = 7
    i.item_type = item_type
    i.binding = binding
    return i


def make_settings(
    *,
    default_loan_period_days=21,
    default_renewal_limit=2,
    default_overdue_fine_per_day=Decimal("0.25"),
    default_max_fine=Decimal("25.00"),
    grace_period_days=0,
    hold_pickup_days=7,
    fine_free_juvenile=False,
    library_system_id=1,
):
    s = MagicMock()
    s.library_system_id = library_system_id
    s.default_loan_period_days = default_loan_period_days
    s.default_renewal_limit = default_renewal_limit
    s.default_overdue_fine_per_day = default_overdue_fine_per_day
    s.default_max_fine = default_max_fine
    s.grace_period_days = grace_period_days
    s.hold_pickup_days = hold_pickup_days
    s.fine_free_juvenile = fine_free_juvenile
    return s


def _matches_input(policy, *, role, item_type, binding, collection_id, library_system_id):
    """Mirror the WHERE clause in _load_candidates so the mock returns the same
    rows a real Postgres query would.
    """
    if policy.library_system_id != library_system_id:
        return False
    if policy.role is not None and policy.role != role:
        return False
    if policy.item_type is not None and policy.item_type != item_type:
        return False
    if binding is None:
        if policy.binding is not None:
            return False
    else:
        if policy.binding is not None and policy.binding != binding:
            return False
    if collection_id is None:
        if policy.collection_id is not None:
            return False
    else:
        if policy.collection_id is not None and policy.collection_id != collection_id:
            return False
    return True


def stub_db(policies, settings, *, user, item, collection_id=None, library_system_id=None):
    """Build an AsyncMock db that mirrors real Postgres filtering behavior.

    Derives library_system_id the same way resolve() does so tests can exercise
    the home_library_system_id fallback path.
    """
    sys_id = (
        library_system_id
        or getattr(user, "library_system_id", None)
        or getattr(user, "home_library_system_id", None)
    )
    if sys_id is None and settings is not None:
        sys_id = settings.library_system_id
    filtered = [
        p for p in policies
        if _matches_input(
            p,
            role=user.role,
            item_type=item.item_type,
            binding=getattr(item, "binding", None),
            collection_id=collection_id,
            library_system_id=sys_id,
        )
    ]
    candidate_result = MagicMock()
    candidate_result.scalars.return_value.all.return_value = filtered
    settings_result = MagicMock()
    settings_result.scalar_one_or_none.return_value = settings

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[candidate_result, settings_result])
    return db


# --- precedence rank -------------------------------------------------------


def test_precedence_rank_orders_most_specific_first():
    """Row with (collection, item_type, role, binding) all set must rank lowest."""
    p_global = make_policy()
    p_format = make_policy(item_type=ItemType.book)
    p_role_format = make_policy(item_type=ItemType.book, role=UserRole.CHILD)
    p_full = make_policy(
        item_type=ItemType.book,
        role=UserRole.CHILD,
        binding=BookBinding.hardback,
        collection_id=12,
    )

    ranks = sorted([p_global, p_format, p_role_format, p_full], key=_precedence_rank)
    assert ranks == [p_full, p_role_format, p_format, p_global]


# --- precedence walk -------------------------------------------------------


@pytest.mark.asyncio
async def test_most_specific_row_wins():
    """A (role, item_type) row beats a (NULL, item_type) row."""
    policies = [
        make_policy(item_type=ItemType.book, loan_period_days=21),
        make_policy(role=UserRole.CHILD, item_type=ItemType.book, loan_period_days=14),
    ]
    user = make_user(role=UserRole.CHILD)
    item = make_item(item_type=ItemType.book)
    db = stub_db(policies, make_settings(), user=user, item=item)

    resolved = await resolve(user=user, item=item, db=db)
    assert resolved.loan_period_days == 14


@pytest.mark.asyncio
async def test_per_field_fallback_combines_rows():
    """Most-specific row provides loan_period; less-specific row provides max_fine."""
    policies = [
        # less-specific row supplies max_fine only
        make_policy(item_type=ItemType.dvd, max_fine=Decimal("10.00")),
        # most-specific row supplies loan_period only
        make_policy(
            role=UserRole.PATRON,
            item_type=ItemType.dvd,
            loan_period_days=7,
        ),
    ]
    user = make_user(role=UserRole.PATRON)
    item = make_item(item_type=ItemType.dvd)
    db = stub_db(policies, make_settings(default_max_fine=Decimal("99.00")), user=user, item=item)

    resolved = await resolve(user=user, item=item, db=db)
    assert resolved.loan_period_days == 7
    # Falls through to less-specific row, NOT to system_settings.
    assert resolved.max_fine == Decimal("10.00")


@pytest.mark.asyncio
async def test_falls_back_to_system_settings_when_no_rows():
    policies = []
    user = make_user()
    item = make_item()
    db = stub_db(
        policies,
        make_settings(default_loan_period_days=28, default_max_fine=Decimal("5.00")),
        user=user,
        item=item,
    )

    resolved = await resolve(user=user, item=item, db=db)
    assert resolved.loan_period_days == 28
    assert resolved.max_fine == Decimal("5.00")


@pytest.mark.asyncio
async def test_hardback_vs_paperback_distinct_loan_periods():
    """Binding axis: same item_type, different binding -> different period."""
    policies = [
        make_policy(item_type=ItemType.book, loan_period_days=21),
        make_policy(
            item_type=ItemType.book,
            binding=BookBinding.hardback,
            loan_period_days=14,
        ),
    ]
    user = make_user()
    hardback = make_item(item_type=ItemType.book, binding=BookBinding.hardback)
    db = stub_db(policies, make_settings(), user=user, item=hardback)

    resolved = await resolve(user=user, item=hardback, db=db)
    assert resolved.loan_period_days == 14


@pytest.mark.asyncio
async def test_paperback_uses_format_default_when_no_binding_row():
    """Item with binding=paperback falls through to (item_type=book, binding=NULL)."""
    policies = [
        make_policy(item_type=ItemType.book, loan_period_days=21),
        make_policy(
            item_type=ItemType.book,
            binding=BookBinding.hardback,
            loan_period_days=14,
        ),
    ]
    user = make_user()
    paperback = make_item(item_type=ItemType.book, binding=BookBinding.paperback)
    db = stub_db(policies, make_settings(), user=user, item=paperback)

    resolved = await resolve(user=user, item=paperback, db=db)
    assert resolved.loan_period_days == 21


@pytest.mark.asyncio
async def test_juvenile_fine_free_backfill_preserves_waiver():
    """role='child' + fine_free=True row -> get_overdue_fine_per_day returns 0."""
    policies = [
        make_policy(item_type=ItemType.book, overdue_fine_per_day=Decimal("0.25")),
        make_policy(role=UserRole.CHILD, fine_free=True),
    ]
    user = make_user(role=UserRole.CHILD)
    item = make_item(item_type=ItemType.book)
    db = stub_db(policies, make_settings(default_overdue_fine_per_day=Decimal("0.25")), user=user, item=item)

    fine = await get_overdue_fine_per_day(user, item, db)
    assert fine == Decimal("0.00")


@pytest.mark.asyncio
async def test_get_loan_period_days_convenience_wrapper():
    policies = [make_policy(item_type=ItemType.kit, loan_period_days=42)]
    user = make_user()
    item = make_item(item_type=ItemType.kit)
    db = stub_db(policies, make_settings(), user=user, item=item)

    period = await get_loan_period_days(user, item, db)
    assert period == 42


@pytest.mark.asyncio
async def test_collection_scope_overrides_format_default():
    """A (collection_id=N, item_type) row beats a (NULL, item_type) row."""
    policies = [
        make_policy(item_type=ItemType.book, loan_period_days=21),
        make_policy(item_type=ItemType.book, collection_id=5, loan_period_days=3),
    ]
    user = make_user()
    item = make_item(item_type=ItemType.book)
    db = stub_db(policies, make_settings(), user=user, item=item, collection_id=5)

    resolved = await resolve(user=user, item=item, db=db, collection_id=5)
    assert resolved.loan_period_days == 3



@pytest.mark.asyncio
async def test_falls_back_to_home_library_system_id():
    """When user.library_system_id is None but home_library_system_id is set,
    resolver uses the home value. This is the typical staff/admin shape."""
    policies = [
        make_policy(library_system_id=7, item_type=ItemType.book, loan_period_days=42),
    ]
    user = User()
    user.id = 99
    user.role = UserRole.PATRON
    user.library_system_id = None
    user.home_library_system_id = 7
    item = make_item(item_type=ItemType.book)
    db = stub_db(policies, make_settings(library_system_id=7), user=user, item=item)

    resolved = await resolve(user=user, item=item, db=db)
    assert resolved.loan_period_days == 42


@pytest.mark.asyncio
async def test_library_system_id_param_beats_user_home_value():
    """Explicit library_system_id param wins over user's home_library_system_id."""
    policies = [
        make_policy(library_system_id=3, item_type=ItemType.book, loan_period_days=21),
        make_policy(library_system_id=7, item_type=ItemType.book, loan_period_days=42),
    ]
    user = User()
    user.id = 99
    user.role = UserRole.PATRON
    user.library_system_id = None
    user.home_library_system_id = 7
    item = make_item(item_type=ItemType.book)
    db = stub_db(
        policies,
        make_settings(library_system_id=3),
        user=user,
        item=item,
        library_system_id=3,
    )

    resolved = await resolve(user=user, item=item, db=db, library_system_id=3)
    assert resolved.loan_period_days == 21
