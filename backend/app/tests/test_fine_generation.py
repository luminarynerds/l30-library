# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comprehensive tests for overdue fine generation system.

Tests cover:
- Fine policy creation and configuration
- Fine calculation for different policy types
- Overdue checkout detection
- Edge cases: grace periods, partial days, maximum caps
- Children's reading minutes tracking
- Fine-exempt users
- Fine payment processing
- Fine waiver management
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.circulation import Checkout, CheckoutStatus
from app.models.fine import Fine, FineStatus, FineType, FinePolicy, FinePolicyType
from app.models.user import User, UserRole
from app.models.catalog import CatalogItem
from app.models.permission import RoleSettings
from app.services.fine_service import (
    check_and_create_overdue_fine,
    get_user_fines_summary,
    record_fine_payment,
    waive_fine,
)
from app.services.fine_policy_service import (
    apply_fine_policy,
    calculate_fine_amount,
    calculate_overdue_days,
    find_applicable_policy,
    create_or_update_fine_policy,
)


# NOTE: no local `db` fixture here. This file used to spin up its own
# in-memory SQLite engine, but CatalogItem.search_tsv is a Postgres
# TSVECTOR column that SQLite's compiler can't render (sqlalchemy.exc.
# CompileError on Base.metadata.create_all). Falls through to the shared
# Postgres-backed `db` fixture in app/tests/conftest.py instead.


@pytest.fixture
async def sample_user(db: AsyncSession) -> User:
    """Create a sample patron user."""
    user = User(
        email="patron@test.com",
        password_hash="hashed_password",
        first_name="John",
        last_name="Patron",
        role=UserRole.PATRON,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def sample_child_user(db: AsyncSession) -> User:
    """Create a sample child user."""
    user = User(
        email="child@test.com",
        password_hash="hashed_password",
        first_name="Jane",
        last_name="Child",
        role=UserRole.CHILD,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def sample_item(db: AsyncSession) -> CatalogItem:
    """Create a sample catalog item."""
    item = CatalogItem(
        title="Test Book",
        author="Test Author",
        isbn="1234567890",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@pytest.fixture
async def role_settings_patron(db: AsyncSession) -> RoleSettings:
    """Create role settings for patron."""
    settings = RoleSettings(
        role=UserRole.PATRON,
        max_checkouts=10,
        checkout_duration_days=21,
        fine_exempt=False,
        use_reading_minutes=False,
    )
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return settings


@pytest.fixture
async def role_settings_child(db: AsyncSession) -> RoleSettings:
    """Create role settings for child (uses reading minutes)."""
    settings = RoleSettings(
        role=UserRole.CHILD,
        max_checkouts=5,
        checkout_duration_days=14,
        fine_exempt=False,
        use_reading_minutes=True,
        minutes_per_day_overdue=10,
        max_reading_minutes_owed=60,
    )
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return settings


@pytest.fixture
async def default_fine_policy(db: AsyncSession) -> FinePolicy:
    """Create a default daily rate fine policy."""
    policy = await create_or_update_fine_policy(
        db,
        name="Standard Daily Rate",
        policy_type=FinePolicyType.daily_rate,
        fine_per_day=Decimal("0.25"),
        applies_to_item_types="all",
        applies_to_user_roles="all",
        grace_period_hours=0,
    )
    await db.commit()
    return policy


# Test Fine Policy Creation and Configuration


@pytest.mark.asyncio
async def test_create_fine_policy(db: AsyncSession):
    """Test creating a new fine policy."""
    policy = await create_or_update_fine_policy(
        db,
        name="Test Policy",
        policy_type=FinePolicyType.daily_rate,
        fine_per_day=Decimal("0.50"),
        applies_to_item_types="book,dvd",
        applies_to_user_roles="PATRON",
    )

    assert policy.name == "Test Policy"
    assert policy.fine_per_day == Decimal("0.50")
    assert policy.applies_to_item_types == "book,dvd"
    assert policy.applies_to_user_roles == "PATRON"


@pytest.mark.asyncio
async def test_update_fine_policy(db: AsyncSession):
    """Test updating an existing fine policy."""
    # Create initial policy
    policy1 = await create_or_update_fine_policy(
        db,
        name="Test Policy",
        policy_type=FinePolicyType.daily_rate,
        fine_per_day=Decimal("0.25"),
    )
    await db.commit()

    # Update the policy
    policy2 = await create_or_update_fine_policy(
        db,
        name="Test Policy",
        policy_type=FinePolicyType.daily_rate,
        fine_per_day=Decimal("0.50"),
    )
    await db.commit()

    # Should be the same policy with updated values
    assert policy2.id == policy1.id
    assert policy2.fine_per_day == Decimal("0.50")


# Test Fine Calculation


@pytest.mark.asyncio
async def test_calculate_fine_amount_daily_rate(default_fine_policy: FinePolicy):
    """Test fine calculation with daily rate policy."""
    amount = calculate_fine_amount(default_fine_policy, 5)
    assert amount == Decimal("1.25")  # 5 days * $0.25


@pytest.mark.asyncio
async def test_calculate_fine_amount_with_minimum(db: AsyncSession):
    """Test fine calculation respects minimum amount."""
    policy = await create_or_update_fine_policy(
        db,
        name="Minimum Policy",
        policy_type=FinePolicyType.daily_rate,
        fine_per_day=Decimal("0.01"),
        minimum_fine_amount=Decimal("1.00"),
    )
    await db.commit()

    # Even 1 day should give minimum amount
    amount = calculate_fine_amount(policy, 1)
    assert amount == Decimal("1.00")


@pytest.mark.asyncio
async def test_calculate_fine_amount_with_maximum_cap(db: AsyncSession):
    """Test fine calculation respects maximum cap."""
    policy = await create_or_update_fine_policy(
        db,
        name="Cap Policy",
        policy_type=FinePolicyType.maximum_cap,
        fine_per_day=Decimal("0.50"),
        maximum_cap=Decimal("5.00"),
    )
    await db.commit()

    # 100 days would be $50, but capped at $5
    amount = calculate_fine_amount(policy, 100)
    assert amount == Decimal("5.00")


@pytest.mark.asyncio
async def test_calculate_fine_amount_progressive(db: AsyncSession):
    """Test progressive fine calculation (increases each day)."""
    policy = await create_or_update_fine_policy(
        db,
        name="Progressive Policy",
        policy_type=FinePolicyType.progressive,
        fine_per_day=Decimal("0.25"),
        progressive_increase_percent=Decimal("10"),  # 10% increase per day
    )
    await db.commit()

    # Day 1: $0.25
    # Day 2: $0.25 * 1.10 = $0.275
    # Day 3: $0.25 * 1.1^2 = $0.3025
    # Total: $0.8275
    amount = calculate_fine_amount(policy, 3)
    expected = (
        Decimal("0.25")
        + (Decimal("0.25") * Decimal("1.1"))
        + (Decimal("0.25") * Decimal("1.1") ** 2)
    )
    # pytest.approx(float) compared against a Decimal raises TypeError
    # ("unsupported operand type(s) for -: 'float' and 'decimal.Decimal'")
    # -- approx's __eq__ subtracts its expected value from actual, and
    # Python won't auto-coerce float/Decimal in subtraction. Compare like
    # types instead; the calculation itself is untouched.
    assert float(amount) == pytest.approx(float(expected), abs=0.01)


@pytest.mark.asyncio
async def test_calculate_fine_amount_tiered(db: AsyncSession):
    """Test tiered fine calculation."""
    tiered_config = '[{"min_days": 0, "max_days": 7, "rate": 0.25}, {"min_days": 8, "max_days": 14, "rate": 0.50}]'

    policy = await create_or_update_fine_policy(
        db,
        name="Tiered Policy",
        policy_type=FinePolicyType.tiered,
        tiered_configuration=tiered_config,
    )
    await db.commit()

    # Tiers are cumulative (tax-bracket style), per the documented
    # calculate_fine_amount semantics: each tier's rate applies only to the
    # days that fall inside that tier, not the whole period.

    # 5 days, all in tier 1: 5 x $0.25 = $1.25
    amount = calculate_fine_amount(policy, 5)
    assert amount == Decimal("1.25")

    # 10 days: 7 x $0.25 (tier 1) + 2 x $0.50 (days 9-10, tier 2) = $2.75
    amount = calculate_fine_amount(policy, 10)
    assert amount == Decimal("2.75")


# Test Overdue Day Calculation


@pytest.mark.asyncio
async def test_calculate_overdue_days_not_overdue(sample_user: User, sample_item: CatalogItem):
    """Test that not-yet-due items have 0 days overdue."""
    now = datetime.now(timezone.utc)
    future_date = now + timedelta(days=5)

    checkout = Checkout(
        user_id=sample_user.id,
        item_id=sample_item.id,
        due_date=future_date,
        status=CheckoutStatus.active,
    )

    days = await calculate_overdue_days(checkout, now=now)
    assert days == 0


@pytest.mark.asyncio
async def test_calculate_overdue_days_one_day(sample_user: User, sample_item: CatalogItem):
    """Test calculating 1 day overdue."""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)

    checkout = Checkout(
        user_id=sample_user.id,
        item_id=sample_item.id,
        due_date=yesterday,
        status=CheckoutStatus.active,
    )

    days = await calculate_overdue_days(checkout, now=now)
    assert days == 1


@pytest.mark.asyncio
async def test_calculate_overdue_days_partial_day_rounds_up(
    sample_user: User, sample_item: CatalogItem
):
    """Test that partial days round up."""
    now = datetime.now(timezone.utc)
    # 0.5 hours overdue
    slightly_past = now - timedelta(hours=0.5)

    checkout = Checkout(
        user_id=sample_user.id,
        item_id=sample_item.id,
        due_date=slightly_past,
        status=CheckoutStatus.active,
    )

    days = await calculate_overdue_days(checkout, now=now)
    assert days == 1  # Rounds up


@pytest.mark.asyncio
async def test_calculate_overdue_days_with_grace_period(
    db: AsyncSession, sample_user: User, sample_item: CatalogItem
):
    """Test grace period is applied before counting days."""
    policy = await create_or_update_fine_policy(
        db,
        name="Grace Policy",
        policy_type=FinePolicyType.daily_rate,
        grace_period_hours=24,  # 1 day grace period
    )
    await db.commit()

    now = datetime.now(timezone.utc)
    # 1.5 days past due, but with 1 day grace = 0.5 days = rounds up to 1
    past_due = now - timedelta(hours=36)

    checkout = Checkout(
        user_id=sample_user.id,
        item_id=sample_item.id,
        due_date=past_due,
        status=CheckoutStatus.active,
    )

    days = await calculate_overdue_days(checkout, policy, now=now)
    assert days == 1


# Test Fine Policy Selection


@pytest.mark.asyncio
async def test_find_applicable_policy_all_match(
    db: AsyncSession, sample_user: User, sample_item: CatalogItem
):
    """Test finding policy that matches all items and all roles."""
    policy = await create_or_update_fine_policy(
        db,
        name="Universal Policy",
        policy_type=FinePolicyType.daily_rate,
        applies_to_item_types="all",
        applies_to_user_roles="all",
    )
    await db.commit()

    found = await find_applicable_policy(db, None, sample_user, sample_item)
    assert found is not None
    assert found.id == policy.id


@pytest.mark.asyncio
async def test_find_applicable_policy_specific_role(
    db: AsyncSession, sample_user: User, sample_item: CatalogItem
):
    """Test finding policy specific to a user role."""
    _ = await create_or_update_fine_policy(
        db,
        name="Patron Policy",
        policy_type=FinePolicyType.daily_rate,
        applies_to_item_types="all",
        # find_applicable_policy compares this against user.role.value,
        # which is the lowercase UserRole wire value ("patron"), not the
        # enum member name. "PATRON" (uppercase) never matched, so this
        # policy was silently skipped and the generic fallback always won.
        applies_to_user_roles="patron",
        fine_per_day=Decimal("0.50"),
    )

    _ = await create_or_update_fine_policy(
        db,
        name="General Policy",
        policy_type=FinePolicyType.daily_rate,
        applies_to_item_types="all",
        applies_to_user_roles="all",
        fine_per_day=Decimal("0.25"),
    )
    await db.commit()

    # Should prefer the more specific policy
    found = await find_applicable_policy(db, None, sample_user, sample_item)
    assert found.name == "Patron Policy"


# Test Fine Creation and Updates


@pytest.mark.asyncio
async def test_apply_fine_policy_creates_new_fine(
    db: AsyncSession,
    sample_user: User,
    sample_item: CatalogItem,
    role_settings_patron: RoleSettings,
    default_fine_policy: FinePolicy,
):
    """Test that apply_fine_policy creates a new fine for overdue checkout."""
    now = datetime.now(timezone.utc)
    past_due = now - timedelta(days=3) + timedelta(minutes=5)

    checkout = Checkout(
        user_id=sample_user.id,
        item_id=sample_item.id,
        # ck_checkout_due_after_checkout requires due_date >= checked_out_at;
        # checked_out_at otherwise server-defaults to "now" at insert time,
        # which is after a backdated due_date.
        checked_out_at=past_due - timedelta(days=21),
        due_date=past_due,
        status=CheckoutStatus.active,
    )
    db.add(checkout)
    await db.commit()
    await db.refresh(checkout)

    fine, was_modified = await apply_fine_policy(checkout, sample_user, sample_item, db)

    assert fine is not None
    assert fine.amount == Decimal("0.75")  # 3 days * $0.25
    assert fine.status == FineStatus.unpaid
    assert checkout.status == CheckoutStatus.overdue


@pytest.mark.asyncio
async def test_apply_fine_policy_updates_existing_fine(
    db: AsyncSession,
    sample_user: User,
    sample_item: CatalogItem,
    role_settings_patron: RoleSettings,
    default_fine_policy: FinePolicy,
):
    """Test that apply_fine_policy updates an existing fine."""
    now = datetime.now(timezone.utc)
    past_due = now - timedelta(days=3) + timedelta(minutes=5)

    checkout = Checkout(
        user_id=sample_user.id,
        item_id=sample_item.id,
        # ck_checkout_due_after_checkout requires due_date >= checked_out_at;
        # set it far enough back to cover the due_date reassignment below too.
        checked_out_at=now - timedelta(days=30),
        due_date=past_due,
        status=CheckoutStatus.active,
    )
    db.add(checkout)
    await db.commit()
    await db.refresh(checkout)

    # Create initial fine
    fine1, _ = await apply_fine_policy(checkout, sample_user, sample_item, db)
    initial_id = fine1.id
    await db.commit()

    # Simulate another day passing
    checkout.due_date = now - timedelta(days=4) + timedelta(minutes=5)

    # Apply policy again - should update existing fine
    fine2, was_modified = await apply_fine_policy(checkout, sample_user, sample_item, db)

    assert fine2.id == initial_id  # Same fine record
    assert fine2.amount == Decimal("1.00")  # 4 days * $0.25
    assert was_modified is True


@pytest.mark.asyncio
async def test_apply_fine_policy_reading_minutes(
    db: AsyncSession,
    sample_child_user: User,
    sample_item: CatalogItem,
    role_settings_child: RoleSettings,
):
    """Test that child users accumulate reading minutes instead of fines."""
    # Create a policy for children
    _ = await create_or_update_fine_policy(
        db,
        name="Child Policy",
        policy_type=FinePolicyType.daily_rate,
        # find_applicable_policy compares this against user.role.value, the
        # lowercase UserRole wire value ("child"). "CHILD" (uppercase) never
        # matched, so this policy was silently skipped, no policy matched at
        # all (no "all"-role fallback exists in this test), and
        # apply_fine_policy short-circuited with (None, False) -- logged as
        # "No fine policy found" -- before ever reaching the reading-minutes
        # branch this test exists to cover.
        applies_to_user_roles="child",
    )
    await db.commit()

    now = datetime.now(timezone.utc)
    past_due = now - timedelta(days=3) + timedelta(minutes=5)

    checkout = Checkout(
        user_id=sample_child_user.id,
        item_id=sample_item.id,
        checked_out_at=past_due - timedelta(days=21),
        due_date=past_due,
        status=CheckoutStatus.active,
    )
    db.add(checkout)
    await db.commit()
    await db.refresh(checkout)

    # Apply policy
    fine, was_modified = await apply_fine_policy(checkout, sample_child_user, sample_item, db)

    # Should not create a monetary fine
    assert fine is None

    # Should add reading minutes instead
    await db.refresh(sample_child_user)
    assert sample_child_user.reading_minutes_owed == 30  # 3 days * 10 minutes/day


@pytest.mark.asyncio
async def test_apply_fine_policy_respects_max_reading_minutes(
    db: AsyncSession,
    sample_child_user: User,
    sample_item: CatalogItem,
    role_settings_child: RoleSettings,
):
    """Test that reading minutes are capped at maximum."""
    _ = await create_or_update_fine_policy(
        db,
        name="Child Policy",
        policy_type=FinePolicyType.daily_rate,
        # See test_apply_fine_policy_reading_minutes above: must match the
        # lowercase UserRole wire value ("child"), not the enum member name.
        applies_to_user_roles="child",
    )
    await db.commit()

    now = datetime.now(timezone.utc)
    # 100 days overdue = 1000 minutes, but max is 60
    past_due = now - timedelta(days=100) + timedelta(minutes=5)

    checkout = Checkout(
        user_id=sample_child_user.id,
        item_id=sample_item.id,
        checked_out_at=past_due - timedelta(days=21),
        due_date=past_due,
        status=CheckoutStatus.active,
    )
    db.add(checkout)
    await db.commit()
    await db.refresh(checkout)

    fine, _ = await apply_fine_policy(checkout, sample_child_user, sample_item, db)

    await db.refresh(sample_child_user)
    assert sample_child_user.reading_minutes_owed == 60  # Capped at max


# Test Fine Payment and Waiver


@pytest.mark.asyncio
async def test_record_fine_payment_full(
    db: AsyncSession,
    sample_user: User,
    sample_item: CatalogItem,
    role_settings_patron: RoleSettings,
    default_fine_policy: FinePolicy,
):
    """Test recording a full fine payment."""
    now = datetime.now(timezone.utc)
    past_due = now - timedelta(days=2) + timedelta(minutes=5)

    checkout = Checkout(
        user_id=sample_user.id,
        item_id=sample_item.id,
        checked_out_at=past_due - timedelta(days=21),
        due_date=past_due,
        status=CheckoutStatus.active,
    )
    db.add(checkout)
    await db.commit()
    await db.refresh(checkout)

    fine, _ = await apply_fine_policy(checkout, sample_user, sample_item, db)
    await db.commit()
    await db.refresh(fine)

    # Pay the full fine
    paid_fine = await record_fine_payment(fine.id, fine.amount, db, payment_method="online")
    await db.commit()

    assert paid_fine.status == FineStatus.paid
    assert paid_fine.amount_paid == fine.amount
    assert paid_fine.balance == Decimal("0.00")


@pytest.mark.asyncio
async def test_record_fine_payment_partial(
    db: AsyncSession,
    sample_user: User,
    sample_item: CatalogItem,
    role_settings_patron: RoleSettings,
    default_fine_policy: FinePolicy,
):
    """Test recording a partial fine payment."""
    now = datetime.now(timezone.utc)
    past_due = now - timedelta(days=4) + timedelta(minutes=5)

    checkout = Checkout(
        user_id=sample_user.id,
        item_id=sample_item.id,
        checked_out_at=past_due - timedelta(days=21),
        due_date=past_due,
        status=CheckoutStatus.active,
    )
    db.add(checkout)
    await db.commit()
    await db.refresh(checkout)

    fine, _ = await apply_fine_policy(checkout, sample_user, sample_item, db)
    await db.commit()
    await db.refresh(fine)

    # Pay half the fine
    payment = fine.amount / 2
    paid_fine = await record_fine_payment(fine.id, payment, db)
    await db.commit()

    assert paid_fine.status == FineStatus.partial
    assert paid_fine.amount_paid == payment
    assert paid_fine.balance == payment


@pytest.mark.asyncio
async def test_waive_fine(
    db: AsyncSession,
    sample_user: User,
    sample_item: CatalogItem,
    role_settings_patron: RoleSettings,
    default_fine_policy: FinePolicy,
):
    """Test waiving a fine."""
    now = datetime.now(timezone.utc)
    past_due = now - timedelta(days=5) + timedelta(minutes=5)

    checkout = Checkout(
        user_id=sample_user.id,
        item_id=sample_item.id,
        checked_out_at=past_due - timedelta(days=21),
        due_date=past_due,
        status=CheckoutStatus.active,
    )
    db.add(checkout)
    await db.commit()
    await db.refresh(checkout)

    fine, _ = await apply_fine_policy(checkout, sample_user, sample_item, db)
    await db.commit()
    await db.refresh(fine)

    # Waive the fine
    waived_fine = await waive_fine(fine.id, db, waived_by_id=sample_user.id, reason="Testing")
    await db.commit()

    assert waived_fine.status == FineStatus.waived
    assert waived_fine.waived_by_id == sample_user.id


# Test Fine Summaries


@pytest.mark.asyncio
async def test_get_user_fines_summary(
    db: AsyncSession,
    sample_user: User,
    sample_item: CatalogItem,
    role_settings_patron: RoleSettings,
    default_fine_policy: FinePolicy,
):
    """Test getting user's fine summary."""
    now = datetime.now(timezone.utc)

    # Create two overdue checkouts
    for days_overdue in [2, 3]:
        due_date = now - timedelta(days=days_overdue) + timedelta(minutes=5)
        checkout = Checkout(
            user_id=sample_user.id,
            item_id=sample_item.id,
            checked_out_at=due_date - timedelta(days=21),
            due_date=due_date,
            status=CheckoutStatus.active,
        )
        db.add(checkout)

    await db.commit()

    # Apply fines
    checkouts_result = await db.execute(select(Checkout).where(Checkout.user_id == sample_user.id))
    for checkout in checkouts_result.scalars().all():
        await apply_fine_policy(checkout, sample_user, sample_item, db)

    await db.commit()

    # Get summary
    summary = await get_user_fines_summary(sample_user.id, db)

    # 2 days * $0.25 + 3 days * $0.25 = $1.25
    assert summary["total_outstanding"] == Decimal("1.25")
    assert summary["outstanding_count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
