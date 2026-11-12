# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for business logic edge cases in LSC Library Management System.

Tests for critical edge cases:
1. Hold expiration handling (what happens after 7 days?)
2. Concurrent operations (two people checking out same item)
3. Reading minutes overflow/caps
4. Fiscal year rollover in acquisitions
"""

import asyncio
from datetime import datetime, timedelta, date, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.security import hash_password
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.user import User, UserRole
from app.models.acquisition import Fund, FundStatus, PurchaseOrder, PurchaseOrderStatus, Vendor


# =============================================================================
# SECTION 1: HOLD EXPIRATION EDGE CASES
# =============================================================================

@pytest.mark.integration
class TestHoldExpirationEdgeCases:
    """
    Test edge cases around hold expiration handling.

    Key scenarios:
    - Hold expires exactly at 7 days
    - Hold status transitions when expired
    - Queue progression when ready hold expires
    - Item availability when hold expires
    """

    @pytest.mark.asyncio
    async def test_hold_expires_after_7_days(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Test that a ready hold is considered expired after 7 days."""
        # Create a hold that was set to ready 8 days ago (should be expired)
        expired_time = datetime.now(timezone.utc) - timedelta(days=8)
        expires_at = expired_time + timedelta(days=7)  # Expired 1 day ago

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=expired_time - timedelta(days=1),
            notified_at=expired_time,
            expires_at=expires_at,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        # Verify the hold's expires_at is in the past
        assert hold.expires_at < datetime.now(timezone.utc), "Hold should be past expiration"

        # BUG DETECTED: The system has no mechanism to transition this to expired status
        # This hold remains "ready" indefinitely even though expires_at has passed
        assert hold.status == HoldStatus.ready, "System doesn't auto-expire holds"

    @pytest.mark.asyncio
    async def test_expired_hold_still_blocks_item(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Test that an expired hold still blocks the item (BUG)."""
        # Set item as on_hold
        test_catalog_item.status = ItemStatus.on_hold

        # Create an expired hold
        expired_time = datetime.now(timezone.utc) - timedelta(days=10)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=expired_time,
            notified_at=expired_time,
            expires_at=expired_time + timedelta(days=7),  # Expired 3 days ago
        )
        test_db.add(hold)
        await test_db.commit()

        # BUG: Item remains on_hold even though the hold has expired
        await test_db.refresh(test_catalog_item)
        assert test_catalog_item.status == ItemStatus.on_hold, \
            "Expired holds still block items - no cleanup mechanism exists"

    @pytest.mark.asyncio
    async def test_hold_queue_not_advanced_on_expiration(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """Test that the hold queue doesn't advance when a ready hold expires."""
        # Create two patrons
        patron1 = User(
            email="patron1_queue@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Patron1",
            last_name="Queue",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        patron2 = User(
            email="patron2_queue@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Patron2",
            last_name="Queue",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add_all([patron1, patron2])
        await test_db.commit()

        # Create expired ready hold for patron1 (position 1)
        expired_time = datetime.now(timezone.utc) - timedelta(days=10)
        hold1 = Hold(
            user_id=patron1.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=expired_time,
            notified_at=expired_time,
            expires_at=expired_time + timedelta(days=7),  # Expired 3 days ago
        )

        # Create pending hold for patron2 (position 2)
        hold2 = Hold(
            user_id=patron2.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=2,
            created_at=datetime.now(timezone.utc) - timedelta(days=5),
        )

        test_db.add_all([hold1, hold2])
        await test_db.commit()

        # BUG: Second patron's hold never advances to "ready" status
        # because no expiration cleanup process exists
        await test_db.refresh(hold2)
        assert hold2.status == HoldStatus.pending, \
            "Queue doesn't advance when ready hold expires"
        assert hold2.position == 2, "Position unchanged despite expired first hold"

    @pytest.mark.asyncio
    async def test_hold_expiration_boundary_exactly_7_days(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Test hold at exactly the 7-day expiration boundary."""
        # Create hold that expires exactly now
        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=8),
            notified_at=now - timedelta(days=7),
            expires_at=now,  # Expires exactly now
        )
        test_db.add(hold)
        await test_db.commit()

        # Hold at exact boundary - should this be expired or not?
        # Without an expiration check, it's neither handled
        assert hold.expires_at <= datetime.now(timezone.utc)
        assert hold.status == HoldStatus.ready  # Still ready, never transitions

    @pytest.mark.asyncio
    async def test_expired_status_enum_exists_but_unused(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Verify that HoldStatus.expired exists but is never set by the system."""
        # The enum value exists
        assert HoldStatus.expired == "expired"

        # But no holds ever have this status in normal operation
        # This is a test to document the gap
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=datetime.now(timezone.utc) - timedelta(days=10),
            notified_at=datetime.now(timezone.utc) - timedelta(days=10),
            expires_at=datetime.now(timezone.utc) - timedelta(days=3),
        )
        test_db.add(hold)
        await test_db.commit()

        # Count holds with expired status - should be 0
        result = await test_db.execute(
            select(func.count(Hold.id)).where(Hold.status == HoldStatus.expired)
        )
        expired_count = result.scalar() or 0

        assert expired_count == 0, "No holds ever transition to expired status automatically"


# =============================================================================
# SECTION 2: CONCURRENT CHECKOUT EDGE CASES
# =============================================================================

@pytest.mark.integration
class TestConcurrentCheckoutEdgeCases:
    """
    Test edge cases around concurrent checkout operations.

    Key scenarios:
    - Two users attempting to checkout same item simultaneously
    - Race condition in checkout limit enforcement
    - TOCTOU (time-of-check to time-of-use) vulnerabilities
    """

    @pytest.mark.asyncio
    async def test_two_users_checkout_same_item_race_condition(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """
        Test race condition when two users try to checkout the same item.

        This demonstrates the vulnerability: without row-level locking,
        both checkouts can succeed, causing data integrity issues.
        """
        # Create two different patrons
        patron1 = User(
            email="race_patron1@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Race",
            last_name="Patron1",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        patron2 = User(
            email="race_patron2@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Race",
            last_name="Patron2",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add_all([patron1, patron2])
        await test_db.commit()

        # Ensure item is available
        test_catalog_item.status = ItemStatus.available
        await test_db.commit()

        # Simulate race condition: both users "see" item as available
        # In real scenario, this would be two concurrent API requests

        # User 1 reads item status (available)
        result1 = await test_db.execute(
            select(CatalogItem).where(CatalogItem.id == test_catalog_item.id)
        )
        item_for_user1 = result1.scalar_one()
        assert item_for_user1.status == ItemStatus.available

        # User 2 also reads item status (still available, no lock)
        result2 = await test_db.execute(
            select(CatalogItem).where(CatalogItem.id == test_catalog_item.id)
        )
        item_for_user2 = result2.scalar_one()
        assert item_for_user2.status == ItemStatus.available

        # Both users proceed to create checkouts
        # This demonstrates the vulnerability - there's no constraint preventing this
        checkout1 = Checkout(
            user_id=patron1.id,
            item_id=test_catalog_item.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
            status=CheckoutStatus.active,
        )
        checkout2 = Checkout(
            user_id=patron2.id,
            item_id=test_catalog_item.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
            status=CheckoutStatus.active,
        )

        test_db.add(checkout1)
        await test_db.flush()

        test_db.add(checkout2)

        # BUG: Both checkouts succeed because there's no unique constraint
        # on (item_id) where status = 'active'
        try:
            await test_db.commit()

            # If we get here, we have a data integrity issue
            result = await test_db.execute(
                select(func.count(Checkout.id)).where(
                    Checkout.item_id == test_catalog_item.id,
                    Checkout.status == CheckoutStatus.active,
                )
            )
            active_count = result.scalar() or 0

            # This assertion documents the bug - 2 active checkouts for same item
            assert active_count == 2, \
                "Race condition: Same item checked out to two users simultaneously"

        except Exception as e:
            # If there WAS a constraint, this would be caught here
            pytest.fail(f"Expected race condition to succeed but got: {e}")

    @pytest.mark.asyncio
    async def test_checkout_limit_race_condition(
        self, test_db: AsyncSession, test_patron
    ):
        """
        Test race condition in checkout limit enforcement.

        If checkout limit is 3 and user has 2 checkouts, two concurrent
        requests could both see count=2 and both proceed, exceeding limit.
        """
        # Create items for testing
        items = []
        for i in range(5):
            item = CatalogItem(
                title=f"Limit Test Book {i}",
                author="Test Author",
                isbn=f"978-0-333333-3{i}-9",
                description="Test book for limit testing",
                status=ItemStatus.available,
                call_number=f"LIMIT-{i:03d}",
                publication_year=2024,
            )
            test_db.add(item)
            items.append(item)
        await test_db.commit()

        # Create 2 existing checkouts (assuming limit of 3)
        for item in items[:2]:
            checkout = Checkout(
                user_id=test_patron.id,
                item_id=item.id,
                due_date=datetime.now(timezone.utc) + timedelta(days=21),
                status=CheckoutStatus.active,
            )
            test_db.add(checkout)
        await test_db.commit()

        # Simulate race: two concurrent requests both check limit
        # Both see count=2, both proceed

        # Request 1 checks count
        result1 = await test_db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.user_id == test_patron.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        count1 = result1.scalar() or 0
        assert count1 == 2

        # Request 2 also checks count (no lock)
        result2 = await test_db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.user_id == test_patron.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        count2 = result2.scalar() or 0
        assert count2 == 2

        # Both requests see count=2, both believe they can add 1 more
        # Both proceed to create checkout
        checkout3 = Checkout(
            user_id=test_patron.id,
            item_id=items[2].id,
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
            status=CheckoutStatus.active,
        )
        checkout4 = Checkout(
            user_id=test_patron.id,
            item_id=items[3].id,
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
            status=CheckoutStatus.active,
        )

        test_db.add(checkout3)
        test_db.add(checkout4)
        await test_db.commit()

        # Count checkouts - if limit is 3, we now have 4
        result = await test_db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.user_id == test_patron.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        total = result.scalar() or 0

        # This documents the bug - limit was exceeded due to race condition
        assert total == 4, "Race condition allowed exceeding checkout limit"

    @pytest.mark.asyncio
    async def test_hold_fulfillment_race_condition(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """
        Test race condition when fulfilling a hold.

        If a ready hold exists and two requests try to fulfill it,
        both might succeed without proper locking.
        """
        patron = User(
            email="hold_fulfill_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="HoldFulfill",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        # Create a ready hold
        hold = Hold(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=datetime.now(timezone.utc),
            notified_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        # Simulate two concurrent fulfillment attempts
        # Both read the hold as "ready"

        # First request reads hold
        result1 = await test_db.execute(
            select(Hold).where(Hold.id == hold.id)
        )
        hold_for_req1 = result1.scalar_one()
        assert hold_for_req1.status == HoldStatus.ready

        # Second request also reads hold (still ready)
        result2 = await test_db.execute(
            select(Hold).where(Hold.id == hold.id)
        )
        hold_for_req2 = result2.scalar_one()
        assert hold_for_req2.status == HoldStatus.ready

        # Both proceed to fulfill - but only one should succeed
        # First fulfillment
        hold_for_req1.status = HoldStatus.fulfilled
        checkout1 = Checkout(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
            status=CheckoutStatus.active,
        )
        test_db.add(checkout1)
        await test_db.flush()

        # In a real race, the second request would create another checkout
        # This test documents that no protection exists
        checkout2 = Checkout(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
            status=CheckoutStatus.active,
        )
        test_db.add(checkout2)

        # Both checkouts are created - duplicate checkout bug
        await test_db.commit()

        result = await test_db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.user_id == patron.id,
                Checkout.item_id == test_catalog_item.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        checkout_count = result.scalar() or 0

        # Documents the bug - same user has 2 active checkouts for same item
        assert checkout_count == 2, \
            "Hold fulfillment race allows duplicate checkouts"


# =============================================================================
# SECTION 3: READING MINUTES OVERFLOW/CAP EDGE CASES
# =============================================================================

@pytest.mark.integration
class TestReadingMinutesEdgeCases:
    """
    Test edge cases around reading minutes tracking.

    Key scenarios:
    - Cap enforcement on reading_minutes_owed
    - Unbounded accumulation of reading_minutes_logged
    - Balance calculation edge cases
    - Integer overflow concerns
    """

    @pytest.mark.asyncio
    async def test_reading_minutes_owed_cap_enforcement(
        self, test_db: AsyncSession
    ):
        """Test that reading_minutes_owed is capped at the configured maximum."""
        # Create a CHILD user (reading minutes apply to children)
        child = User(
            email="child_cap_test@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Child",
            last_name="CapTest",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            reading_minutes_owed=0,
            reading_minutes_logged=0,
        )
        test_db.add(child)
        await test_db.commit()

        # Simulate adding overdue minutes that would exceed cap (default 60)
        # In real system, this is done via check_and_create_overdue_fine
        _ = 60  # Default cap for CHILD role

        # Try to set minutes beyond cap
        child.reading_minutes_owed = 100  # Exceeds cap
        await test_db.commit()
        await test_db.refresh(child)

        # BUG: Direct assignment bypasses cap - only overdue calculation enforces it
        assert child.reading_minutes_owed == 100, \
            "Cap not enforced on direct assignment (only on overdue calculation)"

    @pytest.mark.asyncio
    async def test_reading_minutes_logged_unbounded(
        self, test_db: AsyncSession
    ):
        """Test that reading_minutes_logged has no upper bound."""
        child = User(
            email="child_unbounded@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Child",
            last_name="Unbounded",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            reading_minutes_owed=60,
            reading_minutes_logged=0,
        )
        test_db.add(child)
        await test_db.commit()

        # Log way more minutes than owed
        child.reading_minutes_logged = 1000000  # 1 million minutes logged
        await test_db.commit()
        await test_db.refresh(child)

        # No cap enforcement - this succeeds
        assert child.reading_minutes_logged == 1000000, \
            "reading_minutes_logged has no upper bound"

        # Balance property handles this gracefully
        assert child.reading_minutes_balance == 0, \
            "Balance capped at 0 when logged > owed"

    @pytest.mark.asyncio
    async def test_reading_minutes_balance_when_logged_exceeds_owed(
        self, test_db: AsyncSession
    ):
        """Test balance calculation when logged minutes exceed owed minutes."""
        child = User(
            email="child_balance@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Child",
            last_name="Balance",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            reading_minutes_owed=30,
            reading_minutes_logged=50,  # More logged than owed
        )
        test_db.add(child)
        await test_db.commit()

        # Balance should be 0, not negative
        assert child.reading_minutes_balance == 0

        # But underlying values can be mismatched
        assert child.reading_minutes_logged > child.reading_minutes_owed

    @pytest.mark.asyncio
    async def test_reading_minutes_at_integer_boundary(
        self, test_db: AsyncSession
    ):
        """Test behavior near integer boundaries."""
        child = User(
            email="child_boundary@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Child",
            last_name="Boundary",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            reading_minutes_owed=0,
            reading_minutes_logged=0,
        )
        test_db.add(child)
        await test_db.commit()

        # Set to large value (not quite max int but large)
        large_value = 2_000_000_000  # 2 billion
        child.reading_minutes_logged = large_value
        await test_db.commit()
        await test_db.refresh(child)

        assert child.reading_minutes_logged == large_value

        # Adding more should work until we hit int32 max
        child.reading_minutes_logged += 100_000_000  # Add 100 million
        await test_db.commit()
        await test_db.refresh(child)

        assert child.reading_minutes_logged == 2_100_000_000

    @pytest.mark.asyncio
    async def test_reading_minutes_concurrent_approval(
        self, test_db: AsyncSession
    ):
        """
        Test race condition when two approvals happen simultaneously.

        Two staff members approving reading logs for same child at the same
        time could cause incorrect totals due to read-modify-write pattern.
        """
        child = User(
            email="child_concurrent@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Child",
            last_name="Concurrent",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            reading_minutes_owed=60,
            reading_minutes_logged=0,
        )
        test_db.add(child)
        await test_db.commit()
        await test_db.refresh(child)

        # Simulate two concurrent approvals
        # Both read current logged = 0
        # Both add 15 minutes
        # Expected: 30, but if race condition: 15

        # First approval reads
        result1 = await test_db.execute(
            select(User).where(User.id == child.id)
        )
        child_for_approval1 = result1.scalar_one()
        current1 = child_for_approval1.reading_minutes_logged  # 0

        # Second approval also reads (same value)
        result2 = await test_db.execute(
            select(User).where(User.id == child.id)
        )
        child_for_approval2 = result2.scalar_one()
        current2 = child_for_approval2.reading_minutes_logged  # 0

        # Both perform read-modify-write
        # First approval: 0 + 15 = 15
        child_for_approval1.reading_minutes_logged = current1 + 15
        await test_db.flush()

        # Second approval: 0 + 15 = 15 (lost update!)
        # In same session this won't show the bug, but documents the pattern
        child_for_approval2.reading_minutes_logged = current2 + 15
        await test_db.commit()

        await test_db.refresh(child)

        # In a single session, SQLAlchemy tracks this as one object
        # In separate sessions (real concurrent requests), one update would be lost
        # This test documents the vulnerable pattern
        assert child.reading_minutes_logged == 15, \
            "Read-modify-write pattern is vulnerable to lost updates"

    @pytest.mark.asyncio
    async def test_negative_reading_minutes_handling(
        self, test_db: AsyncSession
    ):
        """A negative reading_minutes_owed is now rejected outright.

        app/models/user.py added ck_user_reading_minutes_owed_non_negative
        (CheckConstraint("reading_minutes_owed >= 0")) after this test was
        written -- the DB no longer lets the "shouldn't happen" state exist
        at all, so the old assertion (insert succeeds, balance clamps via
        max(0, ...)) is obsolete. This now verifies the stronger guarantee:
        the constraint rejects the insert.
        """
        from sqlalchemy.exc import IntegrityError

        child = User(
            email="child_negative@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Child",
            last_name="Negative",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            reading_minutes_owed=-10,  # Negative owed (shouldn't happen)
            reading_minutes_logged=0,
        )
        test_db.add(child)
        with pytest.raises(IntegrityError):
            await test_db.commit()
        await test_db.rollback()


# =============================================================================
# SECTION 4: FISCAL YEAR ROLLOVER EDGE CASES
# =============================================================================

@pytest.mark.integration
class TestFiscalYearRolloverEdgeCases:
    """
    Test edge cases around fiscal year rollover in acquisitions.

    Key scenarios:
    - Rollover with pending purchase orders
    - Duplicate rollover prevention (or lack thereof)
    - Budget calculation during rollover
    - PO references after fund closure
    """

    @pytest.mark.asyncio
    async def test_rollover_fund_with_pending_po(
        self, test_db: AsyncSession
    ):
        """Test fiscal year rollover when fund has pending purchase orders."""
        # Create a vendor
        vendor = Vendor(
            name="Test Vendor",
            email="vendor@test.com",
            is_active=True,
        )
        test_db.add(vendor)
        await test_db.flush()

        # Create a staff user for PO creation
        staff = User(
            email="acquisitions_staff@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Acq",
            last_name="Staff",
            role=UserRole.STAFF,
            is_active=True,
            email_verified=True,
        )
        test_db.add(staff)
        await test_db.flush()

        # Create fund for FY2025
        fund = Fund(
            code="GENERAL-FY2025",
            name="General Fund 2025",
            fiscal_year=2025,
            allocated_amount=Decimal("10000.00"),
            encumbered_amount=Decimal("2000.00"),  # Has encumbered funds
            spent_amount=Decimal("3000.00"),
            status=FundStatus.ACTIVE,
        )
        test_db.add(fund)
        await test_db.flush()

        # Create a pending PO against this fund
        po = PurchaseOrder(
            po_number="PO-2025-001",
            vendor_id=vendor.id,
            fund_id=fund.id,
            status=PurchaseOrderStatus.PENDING_APPROVAL,  # Not yet processed
            total_amount=Decimal("2000.00"),
            created_by_id=staff.id,
        )
        test_db.add(po)
        await test_db.commit()

        # BUG: Rollover can proceed without checking for pending POs
        # This would close the fund while PO is still pending

        # Simulate rollover: close old fund, create new one
        fund.status = FundStatus.CLOSED

        new_fund = Fund(
            code="GENERAL-FY2026",
            name="General Fund 2026",
            fiscal_year=2026,
            allocated_amount=Decimal("10000.00"),
            encumbered_amount=Decimal("0.00"),
            spent_amount=Decimal("0.00"),
            status=FundStatus.ACTIVE,
        )
        test_db.add(new_fund)
        await test_db.commit()

        # PO now references a CLOSED fund
        await test_db.refresh(po)
        await test_db.refresh(fund)

        assert fund.status == FundStatus.CLOSED
        assert po.fund_id == fund.id
        assert po.status == PurchaseOrderStatus.PENDING_APPROVAL

        # This is a data integrity issue - PO can't be processed against closed fund

    @pytest.mark.asyncio
    async def test_duplicate_rollover_prevented(
        self, test_db: AsyncSession
    ):
        """Test that rolling over the same year twice is prevented.

        Closed funds cannot be reopened, so a second rollover is impossible.
        """
        # Create fund for FY2025
        fund = Fund(
            code="DUP-TEST-FY2025",
            name="Duplicate Test Fund 2025",
            fiscal_year=2025,
            allocated_amount=Decimal("5000.00"),
            encumbered_amount=Decimal("0.00"),
            spent_amount=Decimal("1000.00"),
            status=FundStatus.ACTIVE,
        )
        test_db.add(fund)
        await test_db.commit()

        # First rollover
        fund.status = FundStatus.CLOSED
        fund1_2026 = Fund(
            code="DUP-TEST-FY2026-1",
            name="Duplicate Test Fund 2026 (First)",
            fiscal_year=2026,
            allocated_amount=Decimal("5000.00"),
            status=FundStatus.ACTIVE,
        )
        test_db.add(fund1_2026)
        await test_db.commit()

        # FIX: Reopening a closed fund is now prevented at model level
        with pytest.raises(ValueError, match="Cannot reopen closed fund"):
            fund.status = FundStatus.ACTIVE

        # Fund remains closed - duplicate rollover impossible
        assert fund.status == FundStatus.CLOSED

        # Only one FY2026 fund exists
        result = await test_db.execute(
            select(func.count(Fund.id)).where(
                Fund.fiscal_year == 2026,
                Fund.name.contains("Duplicate Test"),
            )
        )
        count = result.scalar() or 0
        assert count == 1, "Only one rollover fund should exist"


    @pytest.mark.asyncio
    async def test_receive_items_against_closed_fund_prevented(
        self, test_db: AsyncSession
    ):
        """Test that financial modifications on closed funds are prevented.

        The Fund model now validates that spent_amount and encumbered_amount
        cannot be modified when the fund status is CLOSED.
        """
        vendor = Vendor(
            name="Closed Fund Vendor",
            email="closed@test.com",
            is_active=True,
        )
        test_db.add(vendor)

        staff = User(
            email="closed_fund_staff@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Closed",
            last_name="Staff",
            role=UserRole.STAFF,
            is_active=True,
            email_verified=True,
        )
        test_db.add(staff)
        await test_db.flush()

        # Create and close fund
        fund = Fund(
            code="CLOSED-FY2025",
            name="Closed Fund 2025",
            fiscal_year=2025,
            allocated_amount=Decimal("5000.00"),
            encumbered_amount=Decimal("1000.00"),
            spent_amount=Decimal("0.00"),
            status=FundStatus.CLOSED,  # Already closed
        )
        test_db.add(fund)
        await test_db.flush()

        # Create PO against closed fund
        po = PurchaseOrder(
            po_number="PO-CLOSED-001",
            vendor_id=vendor.id,
            fund_id=fund.id,
            status=PurchaseOrderStatus.SUBMITTED,
            total_amount=Decimal("1000.00"),
            created_by_id=staff.id,
        )
        test_db.add(po)
        await test_db.commit()

        # FIX: Model-level validation prevents modifying financial fields on closed funds
        with pytest.raises(ValueError, match="Cannot modify spent amount on closed fund"):
            fund.spent_amount = fund.spent_amount + Decimal("500.00")

        with pytest.raises(ValueError, match="Cannot modify encumbered amount on closed fund"):
            fund.encumbered_amount = fund.encumbered_amount - Decimal("500.00")

        # Fund financial fields remain unchanged
        assert fund.spent_amount == Decimal("0.00")
        assert fund.encumbered_amount == Decimal("1000.00")


# =============================================================================
# ADDITIONAL: Combined Edge Cases
# =============================================================================

@pytest.mark.integration
class TestCombinedEdgeCases:
    """Test scenarios combining multiple edge cases."""

    @pytest.mark.asyncio
    async def test_hold_expires_during_checkout_attempt(
        self, test_db: AsyncSession, test_catalog_item
    ):
        """
        Test what happens when a hold expires while user is trying to checkout.

        User has ready hold that expires between clicking checkout and
        the transaction completing.
        """
        patron = User(
            email="expiring_hold_patron@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Expiring",
            last_name="Hold",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()

        # Create hold that's about to expire (1 second from now)
        hold = Hold(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=datetime.now(timezone.utc) - timedelta(days=7),
            notified_at=datetime.now(timezone.utc) - timedelta(days=7),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=1),  # About to expire
        )
        test_db.add(hold)
        await test_db.commit()

        # Simulate delay (hold expires)
        await asyncio.sleep(2)

        # User tries to checkout - hold is expired but status is still "ready"
        await test_db.refresh(hold)

        assert hold.expires_at < datetime.now(timezone.utc), "Hold should be expired"
        assert hold.status == HoldStatus.ready, \
            "Hold status not updated even though expired"

        # Checkout would still succeed because no expiration check exists
        checkout = Checkout(
            user_id=patron.id,
            item_id=test_catalog_item.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
            status=CheckoutStatus.active,
        )
        test_db.add(checkout)
        hold.status = HoldStatus.fulfilled
        await test_db.commit()

        # The system allows checkout of expired hold
        assert checkout.status == CheckoutStatus.active


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
