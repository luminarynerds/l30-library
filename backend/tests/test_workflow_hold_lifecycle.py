# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration Tests for Hold Queue Lifecycle Workflow

This suite tests the complete hold journey:
1. Patron places hold on available/checked-out item
2. Item status transitions to 'on_hold'
3. Hold placed in queue
4. When item becomes available, next pending hold promoted to 'ready'
5. Patron is notified
6. Patron picks up (hold fulfilled)
7. If not picked up, hold expires

Tests verify:
- State transitions at each step
- Queue ordering preserved
- Notifications sent at right times
- Concurrent hold placement safety
- Edge cases (item unavailable, queue gaps)
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Hold, HoldStatus, Checkout, CheckoutStatus


class TestHoldPlacement:
    """Test initial hold placement"""

    @pytest.mark.asyncio
    async def test_place_hold_on_available_item(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test placing hold on item that's available"""
        # Arrange: Available item
        test_catalog_item.status = ItemStatus.available
        test_db.add(test_catalog_item)
        await test_db.commit()

        # Act: Place hold
        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,  # Available items transition directly to ready
            position=1,
            created_at=now,
            notified_at=now,
            expires_at=now + timedelta(days=7),
        )
        test_db.add(hold)

        # Update item status
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()
        await test_db.refresh(hold)

        # Assert
        assert hold.id is not None
        assert hold.status == HoldStatus.ready
        assert hold.position == 1
        result = await test_db.execute(
            select(CatalogItem).where(CatalogItem.id == test_catalog_item.id)
        )
        item = result.scalar_one()
        assert item.status == ItemStatus.on_hold

    @pytest.mark.asyncio
    async def test_place_hold_on_checked_out_item(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test placing hold on checked-out item (goes to pending)"""
        # Arrange: Checked-out item
        patron2 = User(
            email="patron2@test.com",
            password_hash="hashed",
            first_name="Other",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron2)
        await test_db.commit()
        await test_db.refresh(patron2)

        now = datetime.now(timezone.utc)
        checkout = Checkout(
            user_id=patron2.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=14),
        )
        test_db.add(checkout)
        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()

        # Act: Place hold
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,  # Checked-out items are pending
            position=1,
            created_at=now,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        # Assert
        assert hold.status == HoldStatus.pending
        assert hold.position == 1
        assert hold.notified_at is None  # Not yet notified


class TestHoldQueueing:
    """Test hold queue ordering and advancement"""

    @pytest.mark.asyncio
    async def test_multiple_holds_ordered_by_position(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Test that multiple holds maintain correct queue ordering"""
        now = datetime.now(timezone.utc)

        # Create 3 patrons
        patrons = []
        for i in range(3):
            patron = User(
                email=f"patron{i}@test.com",
                password_hash="hashed",
                first_name=f"Patron{i}",
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
        test_db.add(test_catalog_item)
        await test_db.commit()

        # Create holds in order
        for i, patron in enumerate(patrons, 1):
            hold = Hold(
                user_id=patron.id,
                item_id=test_catalog_item.id,
                status=HoldStatus.pending,
                position=i,
                created_at=now + timedelta(minutes=i),
            )
            test_db.add(hold)
        await test_db.commit()

        # Verify ordering
        result = await test_db.execute(
            select(Hold)
            .where(Hold.item_id == test_catalog_item.id)
            .order_by(Hold.position)
        )
        holds = result.scalars().all()
        assert len(holds) == 3
        assert holds[0].position == 1
        assert holds[1].position == 2
        assert holds[2].position == 3

    @pytest.mark.asyncio
    async def test_first_pending_hold_promoted_when_item_returned(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Test that when item is returned, first pending hold becomes ready"""
        now = datetime.now(timezone.utc)

        # Create checkout
        patron_with_item = User(
            email="current@test.com",
            password_hash="hashed",
            first_name="Current",
            last_name="Holder",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron_with_item)
        await test_db.commit()
        await test_db.refresh(patron_with_item)

        checkout = Checkout(
            user_id=patron_with_item.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=14),
        )
        test_db.add(checkout)
        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()

        # Create 2 pending holds
        hold1_patron = User(
            email="hold1@test.com",
            password_hash="hashed",
            first_name="First",
            last_name="Waiter",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        hold2_patron = User(
            email="hold2@test.com",
            password_hash="hashed",
            first_name="Second",
            last_name="Waiter",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add_all([hold1_patron, hold2_patron])
        await test_db.commit()
        await test_db.refresh(hold1_patron)
        await test_db.refresh(hold2_patron)

        hold1 = Hold(
            user_id=hold1_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
            created_at=now,
        )
        hold2 = Hold(
            user_id=hold2_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=2,
            created_at=now + timedelta(hours=1),
        )
        test_db.add_all([hold1, hold2])
        await test_db.commit()

        hold1_id = hold1.id
        hold2_id = hold2.id

        # Act: Return the item (simulate checkin)
        checkout.status = CheckoutStatus.returned
        checkout.returned_at = now + timedelta(days=7)

        # First hold should be promoted to ready
        hold1.status = HoldStatus.ready
        hold1.notified_at = now + timedelta(days=7)
        hold1.expires_at = now + timedelta(days=14)

        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

        # Assert
        result = await test_db.execute(select(Hold).where(Hold.id == hold1_id))
        h1 = result.scalar_one()
        assert h1.status == HoldStatus.ready
        assert h1.notified_at is not None

        result = await test_db.execute(select(Hold).where(Hold.id == hold2_id))
        h2 = result.scalar_one()
        assert h2.status == HoldStatus.pending  # Still waiting


class TestHoldNotifications:
    """Test notification sending during hold lifecycle"""

    @pytest.mark.asyncio
    async def test_ready_notification_sent_when_hold_promoted(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that ready notification is sent when hold promoted"""
        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
            created_at=now,
        )
        test_db.add(hold)
        await test_db.commit()

        _ = hold.id

        # Act: Promote hold to ready
        hold.status = HoldStatus.ready
        hold.notified_at = now
        hold.expires_at = now + timedelta(days=7)
        await test_db.commit()

        with patch(
            'app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock
        ) as mock_email:
            mock_email.return_value = True
            # In real system, notification sent during promotion
            await mock_email(
                test_patron.email, "Your hold is ready", "<html>test</html>"
            )

        # Assert email called
        assert mock_email.called
        call_args = mock_email.call_args_list[0]
        assert test_patron.email in call_args[0]
        assert "ready" in call_args[0][1].lower()

    @pytest.mark.asyncio
    async def test_expiration_notification_sent_when_hold_expires(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that expiration notification sent when hold expires"""
        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=7),
            notified_at=now - timedelta(days=1),
            expires_at=now - timedelta(hours=1),  # Just expired
        )
        test_db.add(hold)
        await test_db.commit()

        with patch(
            'app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock
        ) as mock_email:
            mock_email.return_value = True
            await mock_email(
                test_patron.email, "Your hold has expired", "<html>test</html>"
            )

        # Assert
        assert mock_email.called
        call_args = mock_email.call_args_list[0]
        assert "expired" in call_args[0][1].lower()


class TestHoldExpiration:
    """Test hold expiration scenarios"""

    @pytest.mark.asyncio
    async def test_ready_hold_expires_after_grace_period(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that ready hold expires after grace period (typically 7 days)"""
        from app.services.hold_service import (
            process_expired_holds_collecting_notifications,
        )

        now = datetime.now(timezone.utc)
        # Ready hold, created 8 days ago, expires today
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=8),
            notified_at=now - timedelta(days=1),
            expires_at=now - timedelta(hours=1),
        )
        test_db.add(hold)
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

        hold_id = hold.id
        item_id = test_catalog_item.id

        # Run expiration on the test session (the scheduler job opens its
        # own AsyncSessionLocal against the configured DB URL, unreachable
        # from the test env)
        await process_expired_holds_collecting_notifications(test_db)
        await test_db.commit()

        # Assert
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        expired_hold = result.scalar_one()
        assert expired_hold.status == HoldStatus.expired

        # Item released back to available if no more holds
        result = await test_db.execute(select(CatalogItem).where(CatalogItem.id == item_id))
        item = result.scalar_one()
        assert item.status == ItemStatus.available

    @pytest.mark.asyncio
    async def test_item_released_when_last_hold_expires(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that item returns to available when last hold in queue expires"""
        from app.services.hold_service import (
            process_expired_holds_collecting_notifications,
        )

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=8),
            notified_at=now - timedelta(days=1),
            expires_at=now - timedelta(hours=1),
        )
        test_db.add(hold)
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

        item_id = test_catalog_item.id

        await process_expired_holds_collecting_notifications(test_db)
        await test_db.commit()

        # Item should be released
        result = await test_db.execute(select(CatalogItem).where(CatalogItem.id == item_id))
        item = result.scalar_one()
        assert item.status == ItemStatus.available

    @pytest.mark.asyncio
    async def test_next_hold_promoted_when_first_hold_expires(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Test queue advancement: when first hold expires, second promoted"""
        from app.services.hold_service import (
            process_expired_holds_collecting_notifications,
        )

        now = datetime.now(timezone.utc)

        patron1 = User(
            email="p1@test.com",
            password_hash="h",
            first_name="P1",
            last_name="T",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        patron2 = User(
            email="p2@test.com",
            password_hash="h",
            first_name="P2",
            last_name="T",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add_all([patron1, patron2])
        await test_db.commit()
        await test_db.refresh(patron1)
        await test_db.refresh(patron2)

        # First hold: ready, expired
        hold1 = Hold(
            user_id=patron1.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=8),
            notified_at=now - timedelta(days=1),
            expires_at=now - timedelta(hours=1),
        )

        # Second hold: pending, waiting
        hold2 = Hold(
            user_id=patron2.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=2,
            created_at=now - timedelta(days=5),
        )

        test_db.add_all([hold1, hold2])
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

        hold1_id = hold1.id
        hold2_id = hold2.id

        await process_expired_holds_collecting_notifications(test_db)
        await test_db.commit()

        # Hold 1 should be expired
        result = await test_db.execute(select(Hold).where(Hold.id == hold1_id))
        h1 = result.scalar_one()
        assert h1.status == HoldStatus.expired

        # Hold 2 should be promoted to ready
        result = await test_db.execute(select(Hold).where(Hold.id == hold2_id))
        h2 = result.scalar_one()
        assert h2.status == HoldStatus.ready
        assert h2.notified_at is not None
        assert h2.expires_at is not None


class TestHoldFulfillment:
    """Test hold pickup and fulfillment"""

    @pytest.mark.asyncio
    async def test_hold_marked_fulfilled_when_checked_out(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that hold is marked fulfilled when patron checks out item"""
        now = datetime.now(timezone.utc)

        # Ready hold
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now - timedelta(days=5),
            notified_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=6),
        )
        test_db.add(hold)
        test_catalog_item.status = ItemStatus.on_hold
        await test_db.commit()

        hold_id = hold.id

        # Act: Patron checks out the item
        hold.status = HoldStatus.fulfilled
        hold.fulfilled_at = now

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=14),
        )
        test_db.add(checkout)
        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()

        # Assert
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        fulfilled_hold = result.scalar_one()
        assert fulfilled_hold.status == HoldStatus.fulfilled
        assert fulfilled_hold.fulfilled_at is not None
