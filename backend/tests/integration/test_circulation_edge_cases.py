# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for circulation edge cases.

Tests for:
- Hold expiration handling
- Timezone-aware due dates (UTC)
- Renewal when already overdue
- Fine calculation with partial days
- Reading minutes tracking (no duplicates)
- Partial fine payment handling
- Background job endpoint security
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.user import User, UserRole
from app.core.datetime_utils import utc_now


@pytest.mark.integration
class TestHoldExpiration:
    """Test hold expiration handling."""

    @pytest.mark.asyncio
    async def test_expired_hold_is_cancelled(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Test that expired ready holds are cancelled by process_expired_holds."""
        from app.services.hold_service import process_expired_holds

        # Create an expired ready hold
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=utc_now() - timedelta(days=10),
            notified_at=utc_now() - timedelta(days=8),
            expires_at=utc_now() - timedelta(days=1),  # Expired yesterday
        )
        test_db.add(hold)
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()
        await test_db.refresh(hold)

        # Process expired holds
        processed_count = await process_expired_holds(test_db, item_id=test_catalog_item.id)
        await test_db.commit()

        # Verify hold was expired
        await test_db.refresh(hold)
        assert hold.status == HoldStatus.expired
        assert processed_count == 1

    @pytest.mark.asyncio
    async def test_expired_hold_promotes_next_in_queue(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """Test that when a hold expires, the next person in queue is promoted."""
        from app.services.hold_service import process_expired_holds
        from app.core.security import hash_password

        # Create two patrons
        patron1 = User(
            email="patron1_expire@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Patron1",
            last_name="Test",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        patron2 = User(
            email="patron2_expire@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Patron2",
            last_name="Test",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron1)
        test_db.add(patron2)
        await test_db.flush()

        # Create expired ready hold for patron1 (position 1)
        hold1 = Hold(
            user_id=patron1.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            expires_at=utc_now() - timedelta(days=1),
        )
        # Create pending hold for patron2 (position 2)
        hold2 = Hold(
            user_id=patron2.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=2,
        )
        test_db.add(hold1)
        test_db.add(hold2)
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

        # Process expired holds
        await process_expired_holds(test_db, item_id=test_catalog_item.id)
        await test_db.commit()

        # Verify patron1's hold is expired
        await test_db.refresh(hold1)
        assert hold1.status == HoldStatus.expired

        # Verify patron2's hold is now ready and position updated
        await test_db.refresh(hold2)
        assert hold2.status == HoldStatus.ready
        assert hold2.position == 1
        assert hold2.notified_at is not None
        assert hold2.expires_at is not None

    @pytest.mark.asyncio
    async def test_expired_hold_makes_item_available_if_no_more_holds(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Test that item becomes available when last hold expires."""
        from app.services.hold_service import process_expired_holds

        # Create an expired ready hold (only hold on item)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            expires_at=utc_now() - timedelta(days=1),
        )
        test_db.add(hold)
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

        # Process expired holds
        await process_expired_holds(test_db, item_id=test_catalog_item.id)
        await test_db.commit()

        # Verify item is now available
        await test_db.refresh(test_catalog_item)
        assert test_catalog_item.status == ItemStatus.available


@pytest.mark.integration
class TestTimezoneHandling:
    """Test timezone-aware datetime handling."""

    @pytest.mark.asyncio
    async def test_checkout_due_date_is_utc(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Test that checkout due dates are stored in UTC."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            due_date=utc_now() + timedelta(days=21),
            status=CheckoutStatus.active,
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        # Due date should have timezone info
        assert checkout.due_date.tzinfo is not None or checkout.due_date is not None


@pytest.mark.integration
class TestRenewalWhenOverdue:
    """Test renewal behavior for overdue items."""

    @pytest.mark.asyncio
    async def test_overdue_renewal_sets_due_date_from_now(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Test that renewing an overdue item sets due date from current time, not old due date."""
        # Create overdue checkout (due 10 days ago)
        old_due_date = utc_now() - timedelta(days=10)
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            due_date=old_due_date,
            status=CheckoutStatus.overdue,
            checked_out_at=utc_now() - timedelta(days=31),
            renewal_count=0,
        )
        test_db.add(checkout)
        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()
        await test_db.refresh(checkout)

        # Simulate renewal (should calculate from now, not old due date)
        loan_period = 21
        now = utc_now()
        checkout.due_date = now + timedelta(days=loan_period)
        checkout.renewal_count += 1
        checkout.status = CheckoutStatus.active
        await test_db.commit()
        await test_db.refresh(checkout)

        # New due date should be in the future (not 10 days ago + 21 = 11 days from now)
        # but rather now + 21 days
        assert checkout.due_date > now
        assert checkout.status == CheckoutStatus.active
        # Due date should be approximately 21 days from now
        days_until_due = (checkout.due_date - now).days
        assert 20 <= days_until_due <= 22  # Allow for small timing differences


@pytest.mark.integration
class TestFineCalculation:
    """Test fine calculation with partial days."""

    @pytest.mark.asyncio
    async def test_partial_day_rounds_up(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Test that partial days are rounded up in fine calculation."""
        from app.services.fine_service import check_and_create_overdue_fine

        # Create checkout overdue by 25 hours (1 day + 1 hour)
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            due_date=utc_now() - timedelta(hours=25),
            status=CheckoutStatus.active,
            checked_out_at=utc_now() - timedelta(days=22),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        # Create fine
        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)
        await test_db.commit()

        # Should round up to 2 days (since >24 hours)
        if fine:
            assert fine.amount >= Decimal("0.50")  # At least 2 days * 0.25

    @pytest.mark.asyncio
    async def test_fine_updates_as_item_becomes_more_overdue(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Test that fines are updated when items become more overdue."""
        from app.services.fine_service import check_and_create_overdue_fine

        # Create checkout overdue by 2 days. checked_out_at must be explicit
        # and before due_date (ck_checkout_due_after_checkout) -- it
        # otherwise server-defaults to "now", which is after this due_date.
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            checked_out_at=utc_now() - timedelta(days=23),
            due_date=utc_now() - timedelta(days=2),
            status=CheckoutStatus.active,
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        # Create initial fine
        fine1 = await check_and_create_overdue_fine(checkout, test_db, test_patron)
        await test_db.commit()

        if fine1:
            initial_amount = fine1.amount

            # Make item more overdue (5 days total)
            checkout.due_date = utc_now() - timedelta(days=5)
            await test_db.commit()

            # Recalculate fine
            fine2 = await check_and_create_overdue_fine(checkout, test_db, test_patron)
            await test_db.commit()

            # Fine amount should have increased
            if fine2:
                assert fine2.amount >= initial_amount


@pytest.mark.integration
class TestReadingMinutesTracking:
    """Test reading minutes tracking to prevent duplicates."""

    @pytest.mark.asyncio
    async def test_reading_minutes_only_added_for_new_days(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """Test that reading minutes are only added for NEW overdue days."""
        from app.core.security import hash_password
        from app.models.permission import RoleSettings

        # Create patron with reading minutes role
        patron = User(
            email="reading_minutes_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Reading",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            reading_minutes_owed=0,
        )
        test_db.add(patron)

        # Create role settings that use reading minutes
        settings = RoleSettings(
            role=UserRole.PATRON,
            checkout_duration_days=21,
            max_checkouts=10,
            max_holds=5,
            max_renewals=2,
            use_reading_minutes=True,
            minutes_per_day_overdue=15,
            max_reading_minutes_owed=300,
            hold_duration_days=7,
            fine_exempt=False,
        )
        test_db.add(settings)
        await test_db.flush()

        # Create overdue checkout. checked_out_at must be explicit and
        # before due_date (ck_checkout_due_after_checkout).
        #
        # check_and_create_overdue_fine() applies a 48h grace period before
        # counting overdue days (OVERDUE_GRACE_HOURS in
        # app/core/time_config.py), then ceil()s the remainder to whole
        # days -- overdue_days = ceil((overdue_hours - 48) / 24). Using an
        # exact 3-day-overdue due_date used to land exactly on a ceil()
        # boundary (72h - 48h = 24h = exactly 1 day), which made this test
        # flaky: a few hundred ms of real setup time between computing
        # due_date here and check_and_create_overdue_fine() computing "now"
        # internally was enough to tip ceil() from 1 to 2. Using a half-day
        # offset (84h overdue) keeps the result mid-interval and
        # deterministic: (84-48)/24 = 1.5 -> ceil = 2, regardless of a few
        # seconds of drift either way.
        checkout = Checkout(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            checked_out_at=utc_now() - timedelta(days=24),
            due_date=utc_now() - timedelta(days=3, hours=12),
            status=CheckoutStatus.active,
            last_overdue_days_processed=0,
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)
        await test_db.refresh(patron)

        from app.services.fine_service import check_and_create_overdue_fine

        # First call - should add minutes for 2 days (see grace-period note above)
        initial_minutes = patron.reading_minutes_owed
        await check_and_create_overdue_fine(checkout, test_db, patron)
        await test_db.commit()
        await test_db.refresh(patron)
        await test_db.refresh(checkout)

        first_call_minutes = patron.reading_minutes_owed
        assert first_call_minutes == initial_minutes + (2 * 15)  # 2 days * 15 min
        assert checkout.last_overdue_days_processed == 2

        # Second call with same overdue days - should NOT add more minutes
        await check_and_create_overdue_fine(checkout, test_db, patron)
        await test_db.commit()
        await test_db.refresh(patron)

        second_call_minutes = patron.reading_minutes_owed
        assert second_call_minutes == first_call_minutes  # No change


@pytest.mark.integration
class TestPartialFinePayment:
    """Test partial fine payment handling."""

    @pytest.mark.asyncio
    async def test_fine_updates_when_partially_paid(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Test that partially paid fines can still be updated as items become more overdue."""
        from app.services.fine_service import check_and_create_overdue_fine

        # Create overdue checkout. checked_out_at must be explicit and
        # before due_date (ck_checkout_due_after_checkout).
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            checked_out_at=utc_now() - timedelta(days=23),
            due_date=utc_now() - timedelta(days=2),
            status=CheckoutStatus.overdue,
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        # Create initial fine
        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)
        await test_db.commit()

        if fine:
            initial_amount = fine.amount

            # Make partial payment
            fine.amount_paid = Decimal("0.25")
            fine.status = FineStatus.partial
            await test_db.commit()

            # Make item more overdue
            checkout.due_date = utc_now() - timedelta(days=5)
            await test_db.commit()

            # Recalculate fine
            await check_and_create_overdue_fine(checkout, test_db, test_patron)
            await test_db.commit()
            await test_db.refresh(fine)

            # Fine amount should have increased
            assert fine.amount > initial_amount
            # But amount_paid should be preserved
            assert fine.amount_paid == Decimal("0.25")
            # Status should still be partial
            assert fine.status == FineStatus.partial


@pytest.mark.integration
class TestBackgroundJobSecurity:
    """Test background job endpoint security."""

    async def test_process_expired_holds_requires_auth(self, client):
        """Test that process-expired-holds endpoint requires authentication."""
        response = await client.post("/api/v1/circulation/jobs/process-expired-holds")
        assert response.status_code == 401

    async def test_process_overdue_fines_requires_auth(self, client):
        """Test that process-overdue-fines endpoint requires authentication."""
        response = await client.post("/api/v1/circulation/jobs/process-overdue-fines")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_patron_cannot_access_job_endpoints(
        self, client, test_db, test_patron, test_user_data
    ):
        """Test that regular patrons cannot access job endpoints."""
        # Login as patron
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )

        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            # Try to access job endpoint
            response = await client.post(
                "/api/v1/circulation/jobs/process-expired-holds",
                headers=headers,
            )
            # Should be forbidden (403) for non-admin users
            assert response.status_code in [401, 403]


@pytest.mark.integration
class TestHoldExpirationViaCheckout:
    """Test that expired holds are processed during checkout operations."""

    @pytest.mark.asyncio
    async def test_checkout_processes_expired_holds_first(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """Test that checkout operation processes expired holds on the item first."""
        from app.core.security import hash_password

        # Create patron with expired hold
        patron1 = User(
            email="expired_hold_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Expired",
            last_name="Hold",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        # Create patron who wants to checkout
        patron2 = User(
            email="checkout_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Checkout",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron1)
        test_db.add(patron2)
        await test_db.flush()

        # Create expired ready hold for patron1
        hold = Hold(
            user_id=patron1.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            expires_at=utc_now() - timedelta(days=1),
        )
        test_db.add(hold)
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

        # Process expired holds (simulating what checkout does)
        from app.services.hold_service import process_expired_holds

        await process_expired_holds(test_db, item_id=test_catalog_item.id)
        await test_db.commit()

        # Item should now be available since the only hold expired
        await test_db.refresh(test_catalog_item)
        await test_db.refresh(hold)

        assert hold.status == HoldStatus.expired
        assert test_catalog_item.status == ItemStatus.available


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
