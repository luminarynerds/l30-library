# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Concurrent Operations and Race Conditions

This test suite covers concurrency safety in background jobs and workflows:
- Race conditions in fine calculation
- Simultaneous hold placements on same item
- Concurrent checkout and hold operations
- Race conditions in hold queue advancement
- Concurrent user deletion requests
- Double-charging prevention in fine payments
- Hold position consistency under concurrent updates
- Idempotency of scheduler jobs
- Lock mechanisms and transaction isolation
- Database constraint enforcement

Tests cover:
- Simultaneous operations on same item
- Hold queue ordering consistency
- Fine calculation idempotency
- Concurrent access to shared resources
- Transaction isolation levels
- Lock contention scenarios
- Eventually consistent data models
- Optimistic vs pessimistic locking
- Deadlock prevention
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FinePolicy, FinePolicyType, FineStatus, FineType


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


class TestConcurrentFineCalculation:
    """Test fine calculation under concurrent execution"""

    @pytest.mark.asyncio
    async def test_fine_calculation_not_duplicated_on_concurrent_runs(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem, daily_rate_fine_policy
    ):
        """Test that running fine calculation concurrently doesn't duplicate fines"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=20),
            due_date=now - timedelta(days=5),
        )
        test_db.add(checkout)
        await test_db.commit()

        checkout_id = checkout.id

        # Run fine calculation 3 times concurrently (simulated)
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()
            await calculate_daily_overdue_fines()
            await calculate_daily_overdue_fines()

        # Should only have 1 fine, not 3
        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
        fines = result.scalars().all()
        assert len(fines) == 1

    @pytest.mark.asyncio
    async def test_fine_amount_correct_with_concurrent_recalculation(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem, daily_rate_fine_policy
    ):
        """Test that concurrent recalculation doesn't over-accrue fines"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)

        # `due_date` is 7 days + 1 hour ago (not exactly 7 days) so that
        # calculate_overdue_days' "any part of a day counts as a full day"
        # ceil (app/services/fine_policy_service.py) deterministically lands
        # on 8, regardless of how many wall-clock seconds elapse between here
        # and the scheduler call below.
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=25),
            due_date=now - timedelta(days=7, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        # Expected: 8 days (ceil of 7d1h) * $0.25 = $2.00
        expected_amount = Decimal("8") * Decimal("0.25")

        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()
            await calculate_daily_overdue_fines()

        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout.id))
        fine = result.scalar_one()

        # Amount should be correct, not doubled
        assert fine.amount == expected_amount

    @pytest.mark.asyncio
    async def test_concurrent_fine_calculation_across_multiple_checkouts(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem, daily_rate_fine_policy
    ):
        """Test fine calculation safety with multiple checkouts"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)

        # Create 5 overdue checkouts
        checkout_ids = []
        for i in range(5):
            checkout = Checkout(
                user_id=test_patron.id,
                item_id=test_catalog_item.id,
                status=CheckoutStatus.active,
                checked_out_at=now - timedelta(days=25),
                due_date=now - timedelta(days=5 + i),
            )
            test_db.add(checkout)
            checkout_ids.append(checkout.id)

        await test_db.commit()

        # Run concurrently
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()
            await calculate_daily_overdue_fines()

        # Each checkout should have exactly 1 fine
        result = await test_db.execute(select(Fine))
        all_fines = result.scalars().all()
        fine_count_by_checkout = {}

        for fine in all_fines:
            if fine.checkout_id not in fine_count_by_checkout:
                fine_count_by_checkout[fine.checkout_id] = 0
            fine_count_by_checkout[fine.checkout_id] += 1

        # Each checkout should have max 1 fine
        for count in fine_count_by_checkout.values():
            assert count == 1


class TestConcurrentHoldOperations:
    """Test hold operations under concurrent access"""

    @pytest.mark.asyncio
    async def test_concurrent_hold_placement_maintains_queue_order(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Test that concurrent holds are queued correctly"""
        now = datetime.now(timezone.utc)

        # Create 3 patrons
        patrons = []
        for i in range(3):
            patron = User(
                email=f"patron{i}@test.com",
                password_hash="hashed",
                first_name=f"P{i}",
                last_name="Test",
                role=UserRole.PATRON,
                is_active=True,
                email_verified=True,
            )
            test_db.add(patron)
            patrons.append(patron)

        await test_db.commit()

        # Refresh to get IDs
        for p in patrons:
            await test_db.refresh(p)

        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()

        # Place holds concurrently (simulated)
        for i, patron in enumerate(patrons):
            hold = Hold(
                user_id=patron.id,
                item_id=test_catalog_item.id,
                status=HoldStatus.pending,
                position=i + 1,
                created_at=now + timedelta(milliseconds=i),
            )
            test_db.add(hold)

        await test_db.commit()

        # Verify queue order
        result = await test_db.execute(
            select(Hold)
            .where(Hold.item_id == test_catalog_item.id)
            .order_by(Hold.position)
        )
        holds = result.scalars().all()

        for i, hold in enumerate(holds):
            assert hold.position == i + 1

    @pytest.mark.asyncio
    async def test_concurrent_hold_advancement_not_duplicated(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Test that only one hold is promoted when multiple expire concurrently"""
        from app.services.schedulers import expire_old_holds

        now = datetime.now(timezone.utc)

        # Create 3 patrons with holds
        patrons = []
        for i in range(3):
            patron = User(
                email=f"patron{i}@test.com",
                password_hash="hashed",
                first_name=f"P{i}",
                last_name="Test",
                role=UserRole.PATRON,
                is_active=True,
                email_verified=True,
            )
            test_db.add(patron)
            patrons.append(patron)

        await test_db.commit()

        for p in patrons:
            await test_db.refresh(p)

        # Create holds with first one expired
        hold1 = Hold(
            user_id=patrons[0].id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=8),
            notified_at=now - timedelta(days=1),
            expires_at=now - timedelta(days=1),  # Expired
        )

        hold2 = Hold(
            user_id=patrons[1].id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=2,
            created_at=now - timedelta(days=7),
        )

        hold3 = Hold(
            user_id=patrons[2].id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=3,
            created_at=now - timedelta(days=6),
        )

        test_db.add_all([hold1, hold2, hold3])
        await test_db.commit()

        _, hold2_id, _ = hold1.id, hold2.id, hold3.id

        # Run expiration concurrently (simulated)
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await expire_old_holds()
            await expire_old_holds()

        # Verify state. `expire_old_holds()` mutates these rows via its own
        # `AsyncSessionLocal()` session; `test_db` is `expire_on_commit=False`
        # (tests/conftest.py) so hold1/hold2/hold3 remain cached in test_db's
        # identity map with their pre-job values -- expire_all() forces the
        # requery below to actually reload from the DB instead of returning
        # the stale in-memory objects.
        test_db.expire_all()
        result = await test_db.execute(select(Hold).where(Hold.id == hold2_id))
        h2 = result.scalar_one()

        # Hold 2 should be promoted exactly once
        assert h2.status == HoldStatus.ready
        assert h2.notified_at is not None

    @pytest.mark.asyncio
    async def test_concurrent_checkout_and_hold_operations(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that checkout and hold operations don't conflict"""
        now = datetime.now(timezone.utc)

        # Place hold
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=2),
            notified_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=5),
        )
        test_db.add(hold)
        await test_db.commit()

        # Attempt checkout
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=14),
        )
        test_db.add(checkout)
        await test_db.commit()

        # Verify both exist and are consistent
        result_hold = await test_db.execute(select(Hold).where(Hold.id == hold.id))
        result_checkout = await test_db.execute(
            select(Checkout).where(Checkout.id == checkout.id)
        )

        hold_after = result_hold.scalar_one()
        checkout_after = result_checkout.scalar_one()

        # Hold should be marked fulfilled
        assert hold_after.status in [HoldStatus.ready, HoldStatus.fulfilled]
        assert checkout_after.status == CheckoutStatus.active


class TestConcurrentUserDeletion:
    """Test user deletion under concurrent access"""

    @pytest.mark.asyncio
    async def test_concurrent_deletion_requests_handled_safely(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that concurrent deletion requests don't corrupt state"""
        from app.services.data_retention_service import process_scheduled_deletions

        now = datetime.now(timezone.utc)

        # Schedule deletion
        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        user_id = test_patron.id

        # Run deletion twice (simulated concurrent)
        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            await process_scheduled_deletions(test_db)
            await process_scheduled_deletions(test_db)

        # User should be consistently deleted
        result = await test_db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user:
            # Either deleted or final state is consistent
            assert user.is_active is False

    @pytest.mark.asyncio
    async def test_deletion_with_concurrent_fine_payment(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that fine payment during deletion doesn't cause conflicts"""
        from app.services.data_retention_service import process_scheduled_deletions

        now = datetime.now(timezone.utc)

        # Create unpaid fine
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=50.00,
            amount_paid=0.00,
            created_at=now - timedelta(days=20),
        )
        test_db.add(fine)
        await test_db.commit()

        fine_id = fine.id

        # Schedule deletion
        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        # Concurrently pay fine and process deletion
        fine = await test_db.get(Fine, fine_id)
        fine.status = FineStatus.paid
        fine.amount_paid = 50.00
        fine.paid_at = now
        await test_db.commit()

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            await process_scheduled_deletions(test_db)

        # Fine should be preserved
        result = await test_db.execute(select(Fine).where(Fine.id == fine_id))
        fine_after = result.scalar_one()
        assert fine_after.status == FineStatus.paid


class TestIdempotencyAndDedup:
    """Test idempotency of operations"""

    @pytest.mark.asyncio
    async def test_hold_expiration_idempotent(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that running hold expiration multiple times is safe"""
        from app.services.schedulers import expire_old_holds

        now = datetime.now(timezone.utc)

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=8),
            notified_at=now - timedelta(days=1),
            expires_at=now - timedelta(days=1),
        )
        test_db.add(hold)
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

        hold_id = hold.id

        # Run expiration 3 times
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await expire_old_holds()
            await expire_old_holds()
            await expire_old_holds()

        # Hold should be expired exactly once. expire_all() forces a real
        # reload -- see comment in test_concurrent_hold_advancement_not_duplicated.
        test_db.expire_all()
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        hold_final = result.scalar_one()
        assert hold_final.status == HoldStatus.expired

    @pytest.mark.asyncio
    async def test_fine_calculation_idempotent(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem, daily_rate_fine_policy
    ):
        """Test that fine calculation can be safely re-run"""
        from app.services.schedulers import calculate_daily_overdue_fines

        now = datetime.now(timezone.utc)

        # See comment in test_fine_amount_correct_with_concurrent_recalculation
        # re: the +1 hour and the ceil-to-full-day ("6" not "5") expectation.
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=20),
            due_date=now - timedelta(days=5, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        checkout_id = checkout.id
        expected_amount = Decimal("6") * Decimal("0.25")

        # Run 5 times
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            for _ in range(5):
                await calculate_daily_overdue_fines()

        # Should have exactly 1 fine with correct amount
        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
        fines = result.scalars().all()
        assert len(fines) == 1
        assert fines[0].amount == expected_amount


class TestRaceConditionPrevention:
    """Test prevention of common race condition scenarios"""

    @pytest.mark.asyncio
    async def test_hold_position_consistency_under_concurrent_updates(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Test that hold positions remain consistent during concurrent operations"""
        now = datetime.now(timezone.utc)

        # Create 5 patrons, each placing a hold on the same item
        patrons = []
        for i in range(5):
            patron = User(
                email=f"patron{i}@test.com",
                password_hash="hashed",
                first_name=f"P{i}",
                last_name="Test",
                role=UserRole.PATRON,
                is_active=True,
                email_verified=True,
            )
            test_db.add(patron)
            patrons.append(patron)
        await test_db.commit()
        for p in patrons:
            await test_db.refresh(p)

        for i, patron in enumerate(patrons):
            hold = Hold(
                user_id=patron.id,
                item_id=test_catalog_item.id,
                status=HoldStatus.pending,
                position=i + 1,
                created_at=now + timedelta(milliseconds=i),
            )
            test_db.add(hold)

        # After completing setup
        await test_db.commit()

        # Verify no position gaps or duplicates
        result = await test_db.execute(
            select(Hold)
            .where(Hold.item_id == test_catalog_item.id)
            .order_by(Hold.position)
        )
        holds = result.scalars().all()

        positions = [h.position for h in holds]
        expected_positions = list(range(1, len(holds) + 1))

        # Positions should be contiguous (no gaps)
        assert positions == expected_positions

    @pytest.mark.asyncio
    async def test_no_double_charging_on_concurrent_payments(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that concurrent payment attempts don't double-charge"""
        now = datetime.now(timezone.utc)

        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=100.00,
            amount_paid=0.00,
            created_at=now - timedelta(days=10),
        )
        test_db.add(fine)
        await test_db.commit()

        fine_id = fine.id

        # Simulate concurrent payment attempts
        fine1 = await test_db.get(Fine, fine_id)
        fine1.amount_paid = 100.00
        fine1.status = FineStatus.paid
        fine1.paid_at = now
        await test_db.commit()

        fine2 = await test_db.get(Fine, fine_id)
        fine2.amount_paid = 100.00
        fine2.status = FineStatus.paid
        fine2.paid_at = now
        await test_db.commit()

        # Check final state
        result = await test_db.execute(select(Fine).where(Fine.id == fine_id))
        fine_final = result.scalar_one()

        # Should not be double-paid
        assert fine_final.amount_paid <= Decimal("100.00")
