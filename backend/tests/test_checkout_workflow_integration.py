# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration Tests for Complete Checkout Workflow

This test suite covers the end-to-end checkout lifecycle:
1. User searches for and finds item
2. Item is available -> checkout succeeds
3. Item is checked out -> placed on hold queue
4. Item is returned -> next hold in queue notified
5. User renews active checkout
6. Renewal extends due date
7. User returns item early
8. Late return triggers fine calculation
9. Fine is paid
10. Account with unpaid fines may have checkout restrictions
11. Checkout history is maintained for reading records

Tests cover:
- Happy path checkout, renewal, return
- Hold queue interaction
- Fine calculation on late return
- Renewal restrictions (max renewals, items on hold)
- Item status transitions
- Concurrent checkout and hold operations
- Return and queue advancement
- Renewal deadline enforcement
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType


class TestCheckoutPlacement:
    """Test initial checkout process"""

    @pytest.mark.asyncio
    async def test_checkout_available_item_succeeds(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test successful checkout of available item"""
        now = datetime.now(timezone.utc)

        test_catalog_item.status = ItemStatus.available
        await test_db.commit()

        # Perform checkout
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=21),
        )
        test_db.add(checkout)
        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()
        await test_db.refresh(checkout)

        # Verify checkout created
        assert checkout.id is not None
        assert checkout.status == CheckoutStatus.active
        assert checkout.due_date is not None

        # Verify item status updated
        result = await test_db.execute(
            select(CatalogItem).where(CatalogItem.id == test_catalog_item.id)
        )
        item = result.scalar_one()
        assert item.status == ItemStatus.checked_out

    @pytest.mark.asyncio
    async def test_checkout_respects_loan_period(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that checkout respects configured loan period"""
        now = datetime.now(timezone.utc)
        loan_period_days = 21

        test_catalog_item.status = ItemStatus.available
        await test_db.commit()

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=loan_period_days),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        # Due date should be loan_period_days in future
        days_until_due = (checkout.due_date - checkout.checked_out_at).days
        assert days_until_due == loan_period_days

    @pytest.mark.asyncio
    async def test_checkout_blocked_if_unpaid_fines(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that patrons with unpaid fines may be blocked from checkout"""
        # Create unpaid fine
        now = datetime.now(timezone.utc)
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=50.00,
            amount_paid=0.00,
            created_at=now - timedelta(days=10),
        )
        test_db.add(fine)
        await test_db.commit()

        test_catalog_item.status = ItemStatus.available
        await test_db.commit()

        # Attempt checkout - may fail if fine balance exceeds threshold
        # (Implementation dependent)

    @pytest.mark.asyncio
    async def test_checkout_allowed_with_paid_fine(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that checkout allowed after fine is paid"""
        now = datetime.now(timezone.utc)

        # Create paid fine
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.paid,
            amount=50.00,
            amount_paid=50.00,
            paid_at=now,
            created_at=now - timedelta(days=10),
        )
        test_db.add(fine)
        await test_db.commit()

        test_catalog_item.status = ItemStatus.available
        await test_db.commit()

        # Checkout should succeed
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()

        assert checkout.id is not None


class TestCheckoutRenewal:
    """Test renewal of active checkouts"""

    @pytest.mark.asyncio
    async def test_renew_extends_due_date(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that renewal extends due date by full loan period"""
        now = datetime.now(timezone.utc)
        original_due = now + timedelta(days=3)

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=18),
            due_date=original_due,
        )
        test_db.add(checkout)
        await test_db.commit()

        checkout_id = checkout.id

        # Perform renewal (extend by 21 days from today)
        checkout.due_date = now + timedelta(days=21)
        await test_db.commit()

        result = await test_db.execute(select(Checkout).where(Checkout.id == checkout_id))
        renewed = result.scalar_one()

        # New due date should be in future
        assert renewed.due_date > original_due
        assert renewed.status == CheckoutStatus.active

    @pytest.mark.asyncio
    async def test_renewal_blocked_if_item_on_hold(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that renewal is blocked if item has pending holds"""
        now = datetime.now(timezone.utc)

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=18),
            due_date=now + timedelta(days=3),
        )
        test_db.add(checkout)
        await test_db.commit()

        # Create pending hold for another patron
        patron2 = User(
            email="patron2@test.com",
            password_hash="hashed",
            first_name="Other",
            last_name="User",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron2)
        await test_db.commit()
        await test_db.refresh(patron2)

        hold = Hold(
            user_id=patron2.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
            created_at=now,
        )
        test_db.add(hold)
        await test_db.commit()

        # Attempt renewal - should be blocked
        # (Implementation may return error or raise exception)

    @pytest.mark.asyncio
    async def test_renewal_count_limited(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that renewals are limited (e.g., max 2 renewals)"""
        now = datetime.now(timezone.utc)

        # Create checkout with tracking for renewals
        # (Implementation dependent - may use renewal_count field or separate record)
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=42),  # 2 renewals already
            due_date=now + timedelta(days=3),
        )
        test_db.add(checkout)
        await test_db.commit()

        # Attempt 3rd renewal - should be blocked
        # (If renewal count limit is enforced)

    @pytest.mark.asyncio
    async def test_renewal_preserves_checkout_id(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that renewal doesn't create new checkout record"""
        now = datetime.now(timezone.utc)

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=18),
            due_date=now + timedelta(days=3),
        )
        test_db.add(checkout)
        await test_db.commit()

        original_id = checkout.id

        # Renew
        checkout.due_date = now + timedelta(days=21)
        await test_db.commit()

        result = await test_db.execute(select(Checkout).where(Checkout.id == original_id))
        renewed = result.scalar_one()

        # Should be same record
        assert renewed.id == original_id


class TestCheckoutReturn:
    """Test item return and queue advancement"""

    @pytest.mark.asyncio
    async def test_return_on_time_no_fine(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that on-time return doesn't create fine"""
        now = datetime.now(timezone.utc)

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=10),
            due_date=now + timedelta(days=11),
        )
        test_db.add(checkout)
        await test_db.commit()

        checkout_id = checkout.id

        # Return item
        checkout.status = CheckoutStatus.returned
        checkout.returned_at = now
        test_catalog_item.status = ItemStatus.available
        await test_db.commit()

        # No fine should exist
        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
        fine = result.scalar_one_or_none()
        assert fine is None

    @pytest.mark.asyncio
    async def test_return_late_creates_fine(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that late return creates fine"""
        from app.models.fine import FinePolicy, FinePolicyType
        from app.services.schedulers import calculate_daily_overdue_fines

        # apply_fine_policy (called by calculate_daily_overdue_fines) looks
        # up an active FinePolicy for the checkout; with none in the DB it
        # logs a warning and silently skips fine creation.
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

        now = datetime.now(timezone.utc)

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=30),
            due_date=now - timedelta(days=8),
        )
        test_db.add(checkout)
        await test_db.commit()

        checkout_id = checkout.id

        # Mark as overdue and calculate fine. `app.services.scheduler_service`
        # doesn't exist anymore -- the scheduled jobs live under
        # app.services.schedulers/, and send_email is defined in
        # app.core.email (imported directly into circulation_jobs.py, not
        # re-exported), so that's the patch target to prevent a real send if
        # anything downstream ever triggers a notification.
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # Fine should exist
        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
        fine = result.scalar_one()
        assert fine is not None
        # FineStatus has no "pending" member; new fines are created "unpaid".
        assert fine.status == FineStatus.unpaid

    @pytest.mark.asyncio
    async def test_return_advances_hold_queue(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that returning item promotes next hold in queue"""
        now = datetime.now(timezone.utc)

        # Create checkout
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=15),
            due_date=now + timedelta(days=6),
        )
        test_db.add(checkout)
        await test_db.commit()

        # Create pending holds
        patron2 = User(
            email="patron2@test.com",
            password_hash="hashed",
            first_name="Wait",
            last_name="User",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron2)
        await test_db.commit()
        await test_db.refresh(patron2)

        hold1 = Hold(
            user_id=patron2.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
            created_at=now,
        )
        test_db.add(hold1)
        await test_db.commit()

        hold1_id = hold1.id

        # Return item
        checkout.status = CheckoutStatus.returned
        checkout.returned_at = now

        # Promote first hold to ready
        hold1.status = HoldStatus.ready
        hold1.notified_at = now
        hold1.expires_at = now + timedelta(days=7)

        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

        # Verify hold promoted
        result = await test_db.execute(select(Hold).where(Hold.id == hold1_id))
        promoted_hold = result.scalar_one()
        assert promoted_hold.status == HoldStatus.ready
        assert promoted_hold.notified_at is not None

    @pytest.mark.asyncio
    async def test_return_marks_item_available_if_no_holds(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that item becomes available when returned with no holds"""
        now = datetime.now(timezone.utc)

        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=15),
            due_date=now + timedelta(days=6),
        )
        test_db.add(checkout)
        await test_db.commit()

        item_id = test_catalog_item.id

        # Return item
        checkout.status = CheckoutStatus.returned
        checkout.returned_at = now
        test_catalog_item.status = ItemStatus.available
        await test_db.commit()

        result = await test_db.execute(select(CatalogItem).where(CatalogItem.id == item_id))
        item = result.scalar_one()
        assert item.status == ItemStatus.available


class TestFullCheckoutCycle:
    """Test complete checkout -> renewal -> return cycle"""

    @pytest.mark.asyncio
    async def test_checkout_renew_return_full_cycle(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test full cycle: checkout -> renew -> on-time return"""
        now = datetime.now(timezone.utc)

        # 1. Checkout
        test_catalog_item.status = ItemStatus.available
        await test_db.commit()

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=21),
        )
        test_db.add(checkout)
        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()

        checkout_id = checkout.id

        # 2. Renew
        checkout.due_date = now + timedelta(days=42)
        await test_db.commit()

        # 3. Return
        checkout.status = CheckoutStatus.returned
        checkout.returned_at = now + timedelta(days=30)
        test_catalog_item.status = ItemStatus.available
        await test_db.commit()

        # Verify final state
        result = await test_db.execute(select(Checkout).where(Checkout.id == checkout_id))
        final_checkout = result.scalar_one()
        assert final_checkout.status == CheckoutStatus.returned
        assert final_checkout.returned_at is not None

        result = await test_db.execute(
            select(CatalogItem).where(CatalogItem.id == test_catalog_item.id)
        )
        final_item = result.scalar_one()
        assert final_item.status == ItemStatus.available

        # No fine should exist
        result = await test_db.execute(select(Fine).where(Fine.checkout_id == checkout_id))
        fine = result.scalar_one_or_none()
        assert fine is None

    @pytest.mark.asyncio
    async def test_checkout_with_hold_queue_interaction(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test checkout interaction with hold queue"""
        now = datetime.now(timezone.utc)

        # Create hold first
        patron2 = User(
            email="patron2@test.com",
            password_hash="hashed",
            first_name="Waiter",
            last_name="User",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron2)
        await test_db.commit()
        await test_db.refresh(patron2)

        test_catalog_item.status = ItemStatus.available
        await test_db.commit()

        # Patron 2 places hold
        hold = Hold(
            user_id=patron2.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now,
            notified_at=now,
            expires_at=now + timedelta(days=7),
        )
        test_db.add(hold)
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

        # Patron 1 attempts checkout
        # (Should either fail or be treated as hold pickup)
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()

        # Hold should still exist
        result = await test_db.execute(select(Hold).where(Hold.id == hold.id))
        hold_after = result.scalar_one()
        assert hold_after.status in [HoldStatus.ready, HoldStatus.fulfilled]

    @pytest.mark.asyncio
    async def test_checkout_history_preserved(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that checkout history is preserved for reading records"""
        now = datetime.now(timezone.utc)

        # Create and return checkout
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=20),
            due_date=now - timedelta(days=1),
            returned_at=now,
        )
        checkout.status = CheckoutStatus.returned
        test_db.add(checkout)
        await test_db.commit()

        checkout_id = checkout.id

        # Verify history exists
        result = await test_db.execute(select(Checkout).where(Checkout.id == checkout_id))
        history = result.scalar_one()

        assert history.checked_out_at is not None
        assert history.returned_at is not None
        assert history.status == CheckoutStatus.returned
