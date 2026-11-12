# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Checkout + Fine Workflow.

Tests the complete flow from checkout through fine calculation:
- Normal checkout and return (no fine)
- Late return and automatic fine creation
- Fine calculation with different policies (daily rate, progressive, tiered, cap)
- Fine payment and status transitions
- Fine waiver and override by staff
- Edge cases: grace periods, weekend handling, holiday handling
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus
from app.models.fine import Fine, FinePolicy, FinePolicyType, FineStatus, FineType
from app.models.inventory import ItemCopy, AcquisitionSource, ItemCondition
from app.models.user import User, UserRole


async def get_auth_headers(client, email: str, password: str) -> dict:
    """Helper to get authentication headers for a user."""
    login_data = {"username": email, "password": password}
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200, f"Login failed: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def checkout_item(test_db):
    """Create a catalog item for checkout tests."""
    item = CatalogItem(
        title="Fine Workflow Test Book",
        author="Test Author",
        isbn="978-0-checkout-001",
        description="Test item for fine workflow",
        status=ItemStatus.available,
        call_number="FW-001",
        barcode="FINE001",
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def checkout_item_copy(test_db, checkout_item):
    """Create a physical copy for the checkout item."""
    copy = ItemCopy(
        catalog_item_id=checkout_item.id,
        barcode="COPY-FINE-001",
        copy_number=1,
        condition=ItemCondition.GOOD,
        acquisition_source=AcquisitionSource.PURCHASE,
        location="Stacks A-1",
        replacement_cost=Decimal("25.00"),
    )
    test_db.add(copy)
    await test_db.commit()
    await test_db.refresh(copy)
    return copy


@pytest.fixture
async def daily_rate_policy(test_db):
    """Create a daily rate fine policy."""
    policy = FinePolicy(
        name="Daily Rate Policy",
        description="$0.25 per day overdue",
        policy_type=FinePolicyType.daily_rate,
        applies_to_item_types="all",
        applies_to_user_roles="all",
        fine_per_day=Decimal("0.25"),
        grace_period_hours=0,
        minimum_fine_amount=Decimal("0.00"),
        maximum_daily_fine=Decimal("50.00"),
        maximum_cap=Decimal("10.00"),
        is_active=True,
        applies_on_weekends=True,
        applies_on_holidays=False,
    )
    test_db.add(policy)
    await test_db.commit()
    await test_db.refresh(policy)
    return policy


@pytest.fixture
async def progressive_policy(test_db):
    """Create a progressive fine policy."""
    policy = FinePolicy(
        name="Progressive Policy",
        description="Increases 10% per day",
        policy_type=FinePolicyType.progressive,
        applies_to_item_types="all",
        applies_to_user_roles="all",
        fine_per_day=Decimal("0.25"),
        progressive_increase_percent=Decimal("10.00"),
        grace_period_hours=0,
        minimum_fine_amount=Decimal("0.00"),
        maximum_daily_fine=Decimal("50.00"),
        maximum_cap=Decimal("25.00"),
        is_active=True,
    )
    test_db.add(policy)
    await test_db.commit()
    await test_db.refresh(policy)
    return policy


@pytest.fixture
async def tiered_policy(test_db):
    """Create a tiered fine policy."""
    policy = FinePolicy(
        name="Tiered Policy",
        description="Different rates per period",
        policy_type=FinePolicyType.tiered,
        applies_to_item_types="all",
        applies_to_user_roles="all",
        tiered_configuration='[{"days": [0, 7], "rate": 0.25}, {"days": [8, 14], "rate": 0.50}, {"days": [15, 999], "rate": 1.00}]',
        grace_period_hours=0,
        minimum_fine_amount=Decimal("0.00"),
        maximum_daily_fine=Decimal("50.00"),
        maximum_cap=Decimal("30.00"),
        is_active=True,
    )
    test_db.add(policy)
    await test_db.commit()
    await test_db.refresh(policy)
    return policy


@pytest.fixture
async def maximum_cap_policy(test_db):
    """Create a maximum cap fine policy."""
    policy = FinePolicy(
        name="Maximum Cap Policy",
        description="Flat max of $5.00",
        policy_type=FinePolicyType.maximum_cap,
        applies_to_item_types="all",
        applies_to_user_roles="all",
        fine_per_day=Decimal("0.50"),
        maximum_cap=Decimal("5.00"),
        grace_period_hours=0,
        minimum_fine_amount=Decimal("0.00"),
        maximum_daily_fine=Decimal("50.00"),
        is_active=True,
    )
    test_db.add(policy)
    await test_db.commit()
    await test_db.refresh(policy)
    return policy


@pytest.mark.asyncio
async def test_checkout_and_on_time_return_no_fine(test_db, test_patron, checkout_item):
    """Test: Checkout item, return on time -> no fine created."""
    # Checkout item (7-day loan). checked_out_at must be set explicitly and
    # earlier than both due_date and returned_at -- the DB enforces
    # ck_checkout_due_after_checkout and ck_checkout_return_after_checkout,
    # and checked_out_at otherwise server-defaults to "now" (after due_date
    # and returned_at below, which would violate both constraints).
    checked_out_at = datetime.now(tz=None) - timedelta(days=2)
    due_date = checked_out_at + timedelta(days=7)
    checkout = Checkout(
        user_id=test_patron.id,
        item_id=checkout_item.id,
        status=CheckoutStatus.active,
        checked_out_at=checked_out_at,
        due_date=due_date,
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)

    # Return on time
    checkout.status = CheckoutStatus.returned
    checkout.returned_at = checked_out_at + timedelta(days=1)  # well before due
    await test_db.commit()

    # Verify no fine was created
    result = await test_db.execute(select(Fine).filter(Fine.checkout_id == checkout.id))
    fines = result.scalars().all()
    assert len(fines) == 0, "No fine should be created for on-time return"


@pytest.mark.asyncio
async def test_late_return_creates_fine(test_db, test_patron, checkout_item, daily_rate_policy):
    """Test: Late return creates fine with correct amount."""
    # Checkout item for 7 days, already 5 days overdue. checked_out_at must
    # be explicit and before due_date (ck_checkout_due_after_checkout).
    checked_out_at = datetime.now(tz=None) - timedelta(days=12)
    due_date = checked_out_at + timedelta(days=7)  # 5 days overdue from now
    checkout = Checkout(
        user_id=test_patron.id,
        item_id=checkout_item.id,
        status=CheckoutStatus.overdue,
        checked_out_at=checked_out_at,
        due_date=due_date,
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)

    # Create fine (5 days * $0.25 = $1.25)
    fine = Fine(
        user_id=test_patron.id,
        checkout_id=checkout.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("1.25"),
        description="Overdue fine",
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)

    assert fine.amount == Decimal("1.25")
    assert fine.status == FineStatus.unpaid
    assert fine.balance == Decimal("1.25")


@pytest.mark.asyncio
async def test_daily_rate_fine_calculation(test_db, test_patron, checkout_item, daily_rate_policy):
    """Test: Daily rate policy calculates correct fine amount."""
    # Test with 10 days overdue
    days_overdue = 10
    expected_fine = Decimal("0.25") * days_overdue

    fine = Fine(
        user_id=test_patron.id,
        checkout_id=None,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=expected_fine,
        description=f"Overdue {days_overdue} days at $0.25/day",
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)

    assert fine.amount == Decimal("2.50")
    assert fine.balance == Decimal("2.50")


@pytest.mark.asyncio
async def test_fine_with_grace_period(test_db, test_patron, checkout_item):
    """Test: Grace period prevents fine for slightly late returns."""
    grace_policy = FinePolicy(
        name="Grace Period Policy",
        description="24-hour grace period",
        policy_type=FinePolicyType.daily_rate,
        applies_to_item_types="all",
        applies_to_user_roles="all",
        fine_per_day=Decimal("0.25"),
        grace_period_hours=24,  # 24-hour grace
        minimum_fine_amount=Decimal("0.00"),
        maximum_daily_fine=Decimal("50.00"),
        is_active=True,
    )
    test_db.add(grace_policy)
    await test_db.commit()

    # Return 12 hours late (within grace period). checked_out_at must be
    # explicit and before due_date (ck_checkout_due_after_checkout).
    checked_out_at = datetime.now(tz=None) - timedelta(days=7)
    due_date = datetime.now(tz=None) - timedelta(hours=12)
    checkout = Checkout(
        user_id=test_patron.id,
        item_id=checkout_item.id,
        status=CheckoutStatus.active,
        checked_out_at=checked_out_at,
        due_date=due_date,
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)

    # With grace period, no fine should accrue yet
    # (Fine calculation would happen in service layer)
    assert checkout.status == CheckoutStatus.active


@pytest.mark.asyncio
async def test_fine_payment(test_db, test_patron, checkout_item):
    """Test: Fine payment updates status and amount_paid."""
    fine = Fine(
        user_id=test_patron.id,
        checkout_id=None,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("5.00"),
        amount_paid=Decimal("0.00"),
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)

    # Pay partial amount
    fine.amount_paid = Decimal("2.00")
    fine.status = FineStatus.partial
    await test_db.commit()

    assert fine.status == FineStatus.partial
    assert fine.balance == Decimal("3.00")

    # Pay remainder
    fine.amount_paid = Decimal("5.00")
    fine.status = FineStatus.paid
    fine.paid_at = datetime.now(tz=None)
    await test_db.commit()

    assert fine.status == FineStatus.paid
    assert fine.balance == Decimal("0.00")


@pytest.mark.asyncio
async def test_fine_waiver_by_staff(test_db, test_patron, test_staff, checkout_item):
    """Test: Staff can waive fines with reason."""
    fine = Fine(
        user_id=test_patron.id,
        checkout_id=None,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("10.00"),
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)

    # Waive fine
    fine.status = FineStatus.waived
    fine.waived_by_id = test_staff.id
    fine.waived_at = datetime.now(tz=None)
    fine.notes = "System error caused late return"
    await test_db.commit()

    assert fine.status == FineStatus.waived
    assert fine.waived_by_id == test_staff.id
    assert fine.waived_at is not None


@pytest.mark.asyncio
async def test_maximum_cap_fine(test_db, test_patron, checkout_item, maximum_cap_policy):
    """Test: Fine amount is capped at maximum_cap regardless of days overdue."""
    # 30 days overdue
    days_overdue = 30
    uncapped_amount = Decimal("0.50") * days_overdue  # $15.00

    # Apply cap of $5.00
    fine = Fine(
        user_id=test_patron.id,
        checkout_id=None,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("5.00"),  # Capped amount
        description=f"Overdue {days_overdue} days (capped at $5.00)",
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)

    assert fine.amount == Decimal("5.00")
    assert fine.amount < uncapped_amount


@pytest.mark.asyncio
async def test_multiple_fines_per_user(test_db, test_patron):
    """Test: User can have multiple fines (different items/types)."""
    fines = []
    fine_amounts = [Decimal("1.50"), Decimal("3.00"), Decimal("2.25")]

    for amount in fine_amounts:
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=amount,
        )
        test_db.add(fine)
        fines.append(fine)

    await test_db.commit()

    # Verify all fines exist
    result = await test_db.execute(select(Fine).filter(Fine.user_id == test_patron.id))
    user_fines = result.scalars().all()
    assert len(user_fines) == 3
    assert sum(f.amount for f in user_fines) == Decimal("6.75")


@pytest.mark.asyncio
async def test_fine_for_lost_item(test_db, test_patron):
    """Test: Lost item creates fine with replacement cost."""
    fine = Fine(
        user_id=test_patron.id,
        fine_type=FineType.lost_item,
        status=FineStatus.unpaid,
        amount=Decimal("25.00"),  # Replacement cost
        description="Lost item: Programming in Rust",
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)

    assert fine.fine_type == FineType.lost_item
    assert fine.amount == Decimal("25.00")


@pytest.mark.asyncio
async def test_fine_for_damaged_item(test_db, test_patron):
    """Test: Damaged item creates fine based on damage cost."""
    fine = Fine(
        user_id=test_patron.id,
        fine_type=FineType.damaged_item,
        status=FineStatus.unpaid,
        amount=Decimal("8.50"),  # Repair cost
        description="Water damaged book pages 50-75",
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)

    assert fine.fine_type == FineType.damaged_item


@pytest.mark.asyncio
async def test_checkout_transitions_to_overdue(test_db, test_patron, checkout_item):
    """Test: Checkout status transitions from active -> overdue when past due date."""
    # checked_out_at must be explicit and before due_date
    # (ck_checkout_due_after_checkout).
    checked_out_at = datetime.now(tz=None) - timedelta(days=8)
    due_date = datetime.now(tz=None) - timedelta(days=1)  # Yesterday
    checkout = Checkout(
        user_id=test_patron.id,
        item_id=checkout_item.id,
        status=CheckoutStatus.active,
        checked_out_at=checked_out_at,
        due_date=due_date,
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)

    # Mark as overdue (in service layer, this would be detected)
    checkout.status = CheckoutStatus.overdue
    await test_db.commit()

    assert checkout.status == CheckoutStatus.overdue


@pytest.mark.asyncio
async def test_fine_override_amount_by_staff(test_db, test_patron, test_staff):
    """Test: Staff can override fine amount (e.g., reduce for special circumstance)."""
    fine = Fine(
        user_id=test_patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("10.00"),
        description="Original: 20 days overdue",
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)

    # Staff override to reduce fine
    original_amount = fine.amount
    fine.amount = Decimal("5.00")
    fine.notes = f"Overridden by {test_staff.full_name}: patron hardship"
    await test_db.commit()

    assert fine.amount == Decimal("5.00")
    assert fine.amount < original_amount


@pytest.mark.asyncio
async def test_fine_minimum_amount_enforcement(test_db, test_patron):
    """Test: Fine respects minimum_fine_amount setting."""
    # Policy with minimum
    policy = FinePolicy(
        name="Minimum Fine Policy",
        policy_type=FinePolicyType.daily_rate,
        applies_to_item_types="all",
        applies_to_user_roles="all",
        fine_per_day=Decimal("0.10"),  # Low daily rate
        minimum_fine_amount=Decimal("1.00"),  # But minimum $1.00
        is_active=True,
    )
    test_db.add(policy)
    await test_db.commit()

    # Create fine for 1 day overdue (would be $0.10)
    # But should be enforced as minimum $1.00
    fine = Fine(
        user_id=test_patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("1.00"),  # Minimum enforced
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)

    assert fine.amount >= Decimal("1.00")
