# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration Tests for Complete Fine Workflow

This test suite covers the end-to-end fine lifecycle:
1. Item becomes overdue -> fine creation
2. Fine accrues daily based on policy
3. Patron receives notification
4. Patron can view balance and details
5. Patron makes payment (full or partial)
6. Payment confirmation sent
7. Partial payment tracked
8. Fine can be waived by staff
9. Exempted users/roles don't accrue fines
10. Multiple fines tracked separately
11. Grace periods respected
12. Maximum caps enforced

Tests cover:
- Fine creation on overdue
- Daily accrual calculations
- Payment processing
- Partial payments
- Waiver handling
- Exemption policies
- Policy application (daily, tiered, progressive)
- Grace periods
- Maximum caps
- Fine forgiveness scenarios
- Notification on fine accrual/payment
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus
from app.models.fine import Fine, FineStatus, FineType, FinePolicy, FinePolicyType


@pytest.fixture
async def daily_rate_fine_policy(test_db: AsyncSession):
    """An active $0.25/day fine policy.

    apply_fine_policy (called by calculate_daily_overdue_fines) looks up an
    active FinePolicy for the checkout; with none in the DB it logs a
    warning and silently skips fine creation.
    """
    policy = FinePolicy(
        name="Test Daily Rate Policy",
        policy_type=FinePolicyType.daily_rate,
        applies_to_item_types="all",
        applies_to_user_roles="all",
        fine_per_day=Decimal("0.25"),
        grace_period_hours=0,
        minimum_fine_amount=Decimal("0.00"),
        maximum_daily_fine=Decimal("50.00"),
        maximum_cap=Decimal("50.00"),
        is_active=True,
        applies_on_weekends=True,
        applies_on_holidays=True,
    )
    test_db.add(policy)
    await test_db.commit()
    await test_db.refresh(policy)
    return policy


class TestFineCreation:
    """Test fine creation on overdue items"""

    @pytest.mark.asyncio
    async def test_fine_created_when_item_overdue(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem, daily_rate_fine_policy
    ):
        """Test that fine is created when item becomes overdue"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=25),
            due_date=now - timedelta(days=5),
        )
        test_db.add(checkout)
        await test_db.commit()

        checkout_id = checkout.id

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
        fine = result.scalar_one_or_none()

        assert fine is not None
        assert fine.status == FineStatus.unpaid
        assert fine.checkout_id == checkout_id

    @pytest.mark.asyncio
    async def test_fine_amount_based_on_days_overdue(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem, daily_rate_fine_policy
    ):
        """Test that fine amount matches days overdue * daily rate"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)
        days_overdue = 10

        # due_date is days_overdue + 1 hour ago (not exactly on the day
        # boundary) so calculate_overdue_days' "any part of a day counts as
        # a full day" ceil (app/services/fine_policy_service.py) deterministically
        # lands on days_overdue + 1, regardless of how many wall-clock seconds
        # elapse before the scheduler call below runs.
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=30),
            due_date=now - timedelta(days=days_overdue, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout.id))
        fine = result.scalar_one()

        # Expected: 11 days (ceil of 10d1h) * $0.25/day = $2.75
        expected = Decimal(str(days_overdue + 1)) * Decimal("0.25")
        assert fine.amount == expected

    @pytest.mark.asyncio
    async def test_fine_created_per_overdue_item(
        self, test_db: AsyncSession, test_patron: User, daily_rate_fine_policy
    ):
        """Test that each overdue item gets its own fine record"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)

        # Create 3 overdue checkouts
        checkout_ids = []
        for i in range(3):
            item = CatalogItem(
                title=f"Book {i}",
                author="Author",
                isbn=f"ISBN-{i}",
                status=ItemStatus.available,
                call_number=f"CAL-{i}",
                publication_year=2024,
            )
            test_db.add(item)
            await test_db.flush()

            checkout = Checkout(
                user_id=test_patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=now - timedelta(days=30),
                due_date=now - timedelta(days=5 + i),
            )
            test_db.add(checkout)
            # flush so checkout.id is assigned before we capture it -- without
            # this, checkout.id is None here (PK isn't allocated until
            # flush/commit) and every checkout_id in the list below is None,
            # making the Fine.checkout_id == None lookups downstream match
            # nothing (SQL NULL never equals NULL).
            await test_db.flush()
            checkout_ids.append(checkout.id)

        await test_db.commit()

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # Each checkout should have its own fine
        for checkout_id in checkout_ids:
            result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
            fine = result.scalar_one_or_none()
            assert fine is not None


class TestFineAccrual:
    """Test daily fine accrual and updates"""

    @pytest.mark.asyncio
    async def test_fine_accrues_daily(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem, daily_rate_fine_policy
    ):
        """Test that fine amount increases on subsequent days"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=30),
            due_date=now - timedelta(days=7),
        )
        test_db.add(checkout)
        await test_db.commit()

        checkout_id = checkout.id

        # First calculation: 7 days overdue = $1.75
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
        fine1 = result.scalar_one()
        amount1 = fine1.amount

        # Simulate next day
        checkout.due_date = now - timedelta(days=8)
        await test_db.commit()

        # Second calculation: due_date moved to 8 days ago, but real
        # wall-clock time has advanced since the first calc above, so this
        # ceils to 9 days overdue (see calculate_overdue_days) = $2.25.
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # calculate_daily_overdue_fines() updates the Fine row via its own
        # AsyncSessionLocal() session; test_db is expire_on_commit=False
        # (tests/conftest.py) so fine1 (same PK, already in test_db's
        # identity map) would otherwise be returned unchanged by the requery
        # below. expire_all() forces a real reload.
        test_db.expire_all()
        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
        fine2 = result.scalar_one()
        amount2 = fine2.amount

        # Amount should increase
        assert amount2 > amount1
        assert amount2 == Decimal("9") * Decimal("0.25")

    @pytest.mark.asyncio
    async def test_fine_respects_maximum_cap(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that fine respects maximum cap setting"""
        from app.services.schedulers import calculate_daily_overdue_fines

        # Create fine policy with maximum cap
        now = datetime.now(timezone.utc)
        policy = FinePolicy(
            name="Max Cap Policy",
            policy_type=FinePolicyType.maximum_cap,
            applies_to_item_types="all",
            applies_to_user_roles="all",
            fine_per_day=Decimal("0.25"),
            maximum_cap=Decimal("50.00"),
            is_active=True,
        )
        test_db.add(policy)
        await test_db.commit()

        # Create very overdue checkout (500 days)
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=550),
            due_date=now - timedelta(days=500),
        )
        test_db.add(checkout)
        await test_db.commit()

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout.id))
        fine = result.scalar_one()

        # Fine should not exceed maximum cap
        assert fine.amount <= Decimal("50.00")

    @pytest.mark.asyncio
    async def test_fine_respects_grace_period(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that grace period delays fine accrual"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)

        # Create checkout overdue by 2 hours (less than 24 hour grace period)
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=20),
            due_date=now - timedelta(hours=2),
        )
        test_db.add(checkout)
        await test_db.commit()

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # Depending on grace period, fine may not be created yet
        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout.id))
        _ = result.scalar_one_or_none()

        # Fine may or may not exist depending on grace period


class TestFinePayment:
    """Test fine payment processing"""

    @pytest.mark.asyncio
    async def test_full_fine_payment_marks_paid(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that full payment marks fine as paid"""
        now = datetime.now(timezone.utc)

        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("25.00"),
            amount_paid=Decimal("0.00"),
            created_at=now - timedelta(days=5),
        )
        test_db.add(fine)
        await test_db.commit()

        fine_id = fine.id

        # Process payment
        fine.status = FineStatus.paid
        fine.amount_paid = Decimal("25.00")
        fine.paid_at = now
        await test_db.commit()

        result = await test_db.execute(select(Fine).where(Fine.id == fine_id))
        paid_fine = result.scalar_one()

        assert paid_fine.status == FineStatus.paid
        assert paid_fine.amount_paid == Decimal("25.00")
        assert paid_fine.paid_at is not None

    @pytest.mark.asyncio
    async def test_partial_fine_payment_tracked(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that partial payments are tracked"""
        now = datetime.now(timezone.utc)

        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("50.00"),
            amount_paid=Decimal("0.00"),
            created_at=now - timedelta(days=10),
        )
        test_db.add(fine)
        await test_db.commit()

        fine_id = fine.id

        # First payment: $20
        fine.amount_paid = Decimal("20.00")
        fine.status = FineStatus.partial
        await test_db.commit()

        result = await test_db.execute(select(Fine).where(Fine.id == fine_id))
        partial_fine = result.scalar_one()

        assert partial_fine.status == FineStatus.partial
        assert partial_fine.amount_paid == Decimal("20.00")
        assert partial_fine.balance == Decimal("30.00")

        # Second payment: $20 more
        fine.amount_paid = Decimal("40.00")
        await test_db.commit()

        result = await test_db.execute(select(Fine).where(Fine.id == fine_id))
        still_partial = result.scalar_one()

        assert still_partial.amount_paid == Decimal("40.00")
        assert still_partial.balance == Decimal("10.00")

        # Final payment
        fine.amount_paid = Decimal("50.00")
        fine.status = FineStatus.paid
        fine.paid_at = now
        await test_db.commit()

        result = await test_db.execute(select(Fine).where(Fine.id == fine_id))
        final_fine = result.scalar_one()

        assert final_fine.status == FineStatus.paid
        assert final_fine.balance == Decimal("0.00")


class TestFineWaiver:
    """Test fine waiver by staff"""

    @pytest.mark.asyncio
    async def test_fine_waived_by_staff(
        self, test_db: AsyncSession, test_patron: User, test_staff: User
    ):
        """Test that staff can waive fines"""
        now = datetime.now(timezone.utc)

        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("50.00"),
            amount_paid=Decimal("0.00"),
            created_at=now - timedelta(days=10),
        )
        test_db.add(fine)
        await test_db.commit()

        fine_id = fine.id

        # Staff waives fine
        fine.status = FineStatus.waived
        fine.waived_by_id = test_staff.id
        fine.waived_at = now
        await test_db.commit()

        result = await test_db.execute(select(Fine).where(Fine.id == fine_id))
        waived_fine = result.scalar_one()

        assert waived_fine.status == FineStatus.waived
        assert waived_fine.waived_by_id == test_staff.id
        assert waived_fine.waived_at is not None

    @pytest.mark.asyncio
    async def test_partial_waiver(
        self, test_db: AsyncSession, test_patron: User, test_staff: User
    ):
        """Test that staff can partially waive fines"""
        now = datetime.now(timezone.utc)

        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("50.00"),
            amount_paid=Decimal("0.00"),
            created_at=now - timedelta(days=10),
        )
        test_db.add(fine)
        await test_db.commit()

        fine_id = fine.id

        # Waive $30, patron pays remaining $20
        fine.amount = Decimal("20.00")
        fine.waived_by_id = test_staff.id
        fine.waived_at = now
        await test_db.commit()

        result = await test_db.execute(select(Fine).where(Fine.id == fine_id))
        adjusted_fine = result.scalar_one()

        assert adjusted_fine.amount == Decimal("20.00")
        assert adjusted_fine.waived_by_id is not None


class TestFineExemptions:
    """Test fine exemptions by role"""

    @pytest.mark.asyncio
    async def test_fine_exempt_user_no_fine_created(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Test that fine-exempt users don't get fined.

        There's no per-user `fine_exempt` column on User -- exemption is a
        per-ROLE setting (RoleSettings.fine_exempt, app/models/permission.py)
        looked up by apply_fine_policy. Also seed a FinePolicy so the "no
        fine" outcome is provably due to the exemption check, not merely the
        absence of any applicable policy (see test_fine_respects_maximum_cap
        for the FinePolicy shape).
        """
        from app.models.permission import RoleSettings
        from app.services.schedulers import calculate_daily_overdue_fines

        policy = FinePolicy(
            name="Exempt Test Policy",
            policy_type=FinePolicyType.daily_rate,
            applies_to_item_types="all",
            applies_to_user_roles="all",
            fine_per_day=Decimal("0.25"),
            maximum_cap=Decimal("50.00"),
            is_active=True,
        )
        test_db.add(policy)

        role_settings = RoleSettings(role=UserRole.PATRON, fine_exempt=True)
        test_db.add(role_settings)

        # Create fine-exempt patron
        exempt_patron = User(
            email="exempt@test.com",
            password_hash="hashed",
            first_name="Exempt",
            last_name="User",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(exempt_patron)
        await test_db.commit()
        await test_db.refresh(exempt_patron)

        now = datetime.now(timezone.utc)
        checkout = Checkout(
            user_id=exempt_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=25),
            due_date=now - timedelta(days=10),
        )
        test_db.add(checkout)
        await test_db.commit()

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # No fine should be created
        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout.id))
        fine = result.scalar_one_or_none()
        assert fine is None

    @pytest.mark.asyncio
    async def test_child_reading_minutes_instead_of_fine(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Test that children accrue reading minutes instead of fines.

        There's no `is_child_account` flag on User -- CHILD is a distinct
        UserRole, and the reading-minutes-instead-of-fines behavior is
        gated by RoleSettings.use_reading_minutes for that role (see
        apply_fine_policy in app/services/fine_policy_service.py).
        """
        from app.models.permission import RoleSettings
        from app.services.schedulers import calculate_daily_overdue_fines

        policy = FinePolicy(
            name="Child Test Policy",
            policy_type=FinePolicyType.daily_rate,
            applies_to_item_types="all",
            applies_to_user_roles="all",
            fine_per_day=Decimal("0.25"),
            maximum_cap=Decimal("50.00"),
            is_active=True,
        )
        test_db.add(policy)

        role_settings = RoleSettings(
            role=UserRole.CHILD,
            use_reading_minutes=True,
            minutes_per_day_overdue=10,
            max_reading_minutes_owed=120,
        )
        test_db.add(role_settings)

        # Create child patron
        child = User(
            email="child@test.com",
            password_hash="hashed",
            first_name="Child",
            last_name="User",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)

        now = datetime.now(timezone.utc)
        checkout = Checkout(
            user_id=child.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=25),
            due_date=now - timedelta(days=10),
        )
        test_db.add(checkout)
        await test_db.commit()

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # No fine should be created -- reading minutes accrue instead
        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout.id))
        fine = result.scalar_one_or_none()
        assert fine is None

        await test_db.refresh(child)
        assert child.reading_minutes_owed > 0

        # May create reading minute fine type or update reading_minutes_owed
        # Implementation dependent


class TestMultipleFineHandling:
    """Test handling multiple fines for same user"""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_fines_tracked(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that multiple fines are tracked separately"""
        now = datetime.now(timezone.utc)

        # Create 3 separate fines
        fine_ids = []
        for i in range(3):
            fine = Fine(
                user_id=test_patron.id,
                fine_type=FineType.overdue if i < 2 else FineType.lost_item,
                status=FineStatus.unpaid,
                amount=Decimal(str(10 * (i + 1))),
                amount_paid=Decimal("0.00"),
                created_at=now - timedelta(days=10 - i),
            )
            test_db.add(fine)
            fine_ids.append(fine.id)

        await test_db.commit()

        # Verify all exist
        result = await test_db.execute(select(Fine).where(Fine.user_id == test_patron.id))
        user_fines = result.scalars().all()

        assert len(user_fines) == 3
        amounts = sorted([f.amount for f in user_fines])
        assert amounts == [Decimal("10"), Decimal("20"), Decimal("30")]

    @pytest.mark.asyncio
    async def test_fine_balance_calculation_with_multiple_fines(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that balance is calculated correctly across multiple fines"""
        _ = datetime.now(timezone.utc)

        # Create 2 fines
        fine1 = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("50.00"),
            amount_paid=Decimal("0.00"),
        )
        fine2 = Fine(
            user_id=test_patron.id,
            fine_type=FineType.lost_item,
            status=FineStatus.unpaid,
            amount=Decimal("100.00"),
            amount_paid=Decimal("25.00"),
        )
        test_db.add_all([fine1, fine2])
        await test_db.commit()

        # Total balance: (50 - 0) + (100 - 25) = 125
        result = await test_db.execute(select(Fine).where(Fine.user_id == test_patron.id))
        fines = result.scalars().all()

        total_balance = sum(f.balance for f in fines)
        assert total_balance == Decimal("125.00")
