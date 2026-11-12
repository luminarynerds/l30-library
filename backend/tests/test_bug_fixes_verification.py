# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Verification tests for Critical Business Logic Bug Fixes

This test suite verifies that the following bugs have been fixed:
1. Hold expiration system - Holds auto-expire after 7 days
2. Concurrent checkout prevention - Unique constraint prevents duplicate checkouts
3. Fund rollover validation - Prevents rollover with pending purchase orders
4. Hold queue advancement - Next hold advances when previous expires
"""
import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.user import User, UserRole
from app.models.acquisition import Fund, FundStatus, PurchaseOrder, PurchaseOrderStatus, Vendor
from app.services.hold_service import process_expired_holds


@pytest.mark.integration
class TestBugFixVerification:
    """Verify that critical bugs have been fixed."""

    # =========================================================================
    # BUG FIX #1: Hold Expiration System
    # =========================================================================

    @pytest.mark.asyncio
    async def test_hold_expiration_fixed_ready_hold_transitions_to_expired(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Verify FIX: Ready holds now transition to expired status after expiry date."""
        # Create a hold that's ready and has passed expiry
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
        hold_id = hold.id

        # FIX: Call process_expired_holds to expire the hold
        count = await process_expired_holds(test_db)
        await test_db.commit()

        # Verify the hold is now expired
        assert count == 1, "Should have processed 1 expired hold"
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        expired_hold = result.scalar_one()
        assert expired_hold.status == HoldStatus.expired, "Hold should transition to expired"

    @pytest.mark.asyncio
    async def test_hold_expiration_fixed_item_released(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Verify FIX: Item is released when hold expires and no more holds exist."""
        # Set item as on_hold
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

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
        item_id = test_catalog_item.id

        # FIX: Call process_expired_holds to expire the hold and release the item
        _ = await process_expired_holds(test_db)
        await test_db.commit()

        # Verify the item is now available
        result = await test_db.execute(
            select(CatalogItem).where(CatalogItem.id == item_id)
        )
        item = result.scalar_one()
        assert item.status == ItemStatus.available, "Item should be released when hold expires"

    # =========================================================================
    # BUG FIX #2: Concurrent Checkout Prevention
    # =========================================================================

    @pytest.mark.asyncio
    async def test_concurrent_checkout_fixed_unique_constraint_prevents_duplicate(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Verify FIX: Unique constraint prevents two active checkouts of the same COPY.

        Uniqueness is enforced per physical copy (ix_active_item_copy_checkout on
        item_copy_id), not per title (see app/models/circulation.py Checkout
        model and alembic/versions/drop_title_active_idx_001.py, #1427). A
        multi-copy title must allow one active checkout per copy concurrently,
        so this test exercises two checkouts of the *same* copy, not just the
        same title.
        """
        from app.models.inventory import ItemCopy

        # Create two different patrons
        patron1 = User(
            email="fix_patron1@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Fix",
            last_name="Patron1",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        patron2 = User(
            email="fix_patron2@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Fix",
            last_name="Patron2",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add_all([patron1, patron2])
        await test_db.commit()
        await test_db.refresh(patron1)
        await test_db.refresh(patron2)

        # Ensure item is available
        test_catalog_item.status = ItemStatus.available
        copy = ItemCopy(
            catalog_item_id=test_catalog_item.id,
            barcode="FIX-COPY-001",
            condition="excellent",
        )
        test_db.add(copy)
        await test_db.commit()
        await test_db.refresh(copy)

        # Create first checkout of the copy
        checkout1 = Checkout(
            user_id=patron1.id,
            item_id=test_catalog_item.id,
            item_copy_id=copy.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
            status=CheckoutStatus.active,
        )
        test_db.add(checkout1)
        await test_db.commit()

        # FIX: Try to check out the SAME copy again - should fail due to the
        # per-copy unique constraint.
        checkout2 = Checkout(
            user_id=patron2.id,
            item_id=test_catalog_item.id,
            item_copy_id=copy.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
            status=CheckoutStatus.active,
        )
        test_db.add(checkout2)

        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            await test_db.commit()

    # =========================================================================
    # BUG FIX #3: Hold Queue Advancement
    # =========================================================================

    @pytest.mark.asyncio
    async def test_hold_queue_advancement_fixed_next_hold_advances_on_expiration(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Verify FIX: Next hold advances to ready when previous ready hold expires."""
        # Create two patrons
        patron1 = User(
            email="queue_patron1@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Queue",
            last_name="Patron1",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        patron2 = User(
            email="queue_patron2@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Queue",
            last_name="Patron2",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add_all([patron1, patron2])
        await test_db.commit()
        await test_db.refresh(patron1)
        await test_db.refresh(patron2)

        # Create expired ready hold for patron1
        expired_time = datetime.now(timezone.utc) - timedelta(days=10)
        hold1 = Hold(
            user_id=patron1.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=expired_time,
            notified_at=expired_time,
            expires_at=expired_time + timedelta(days=7),
        )

        # Create pending hold for patron2
        hold2 = Hold(
            user_id=patron2.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=2,
            created_at=datetime.now(timezone.utc) - timedelta(days=5),
        )

        test_db.add_all([hold1, hold2])
        await test_db.commit()
        await test_db.refresh(hold1)
        await test_db.refresh(hold2)

        hold2_id = hold2.id

        # FIX: Call process_expired_holds
        count = await process_expired_holds(test_db)
        await test_db.commit()

        # Verify that hold1 is now expired
        assert count == 1, "Should have processed 1 expired hold"

        # Verify that hold2 is now ready
        result = await test_db.execute(select(Hold).where(Hold.id == hold2_id))
        advanced_hold = result.scalar_one()
        assert advanced_hold.status == HoldStatus.ready, "Next hold should advance to ready"
        assert advanced_hold.expires_at is not None, "Next hold should have expiry date set"

    # =========================================================================
    # BUG FIX #4: Fund Rollover Validation
    # =========================================================================


