# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration Tests for Patron Live Notifications

Tests the full patron notification lifecycle:
  - Notification creation from domain events
  - Fetching notifications via API
  - Marking as read / read-all
  - Dismissing notifications
  - Unread count badge
  - Pagination and filtering
  - Idempotency (no duplicate notifications from replayed events)
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.notification import (
    PatronNotification,
    PatronNotificationCategory,
)
from app.services.patron_notification_service import PatronNotificationService


class TestPatronNotificationCreation:
    """Test creating notifications from domain events."""

    @pytest.mark.asyncio
    async def test_create_hold_available_notification(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test creating a hold available notification."""
        _ = PatronNotificationService()

        notification = PatronNotification(
            patron_id=test_patron.id,
            category=PatronNotificationCategory.HOLD_AVAILABLE,
            title="Your hold is ready for pickup!",
            message="Your held item is now available at the Main Branch.",
            source_event_type="HoldReady",
            source_event_id="evt-test-hold-001",
            related_hold_id="hold-123",
            action_url="/my-account/holds",
            action_label="View My Holds",
        )
        test_db.add(notification)
        await test_db.commit()
        await test_db.refresh(notification)

        assert notification.id is not None
        assert notification.patron_id == test_patron.id
        assert notification.category == PatronNotificationCategory.HOLD_AVAILABLE
        assert notification.is_read is False
        assert notification.is_dismissed is False
        assert notification.created_at is not None

    @pytest.mark.asyncio
    async def test_create_overdue_notification(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test creating an overdue notice notification."""
        notification = PatronNotification(
            patron_id=test_patron.id,
            category=PatronNotificationCategory.OVERDUE_NOTICE,
            title="You have an overdue item",
            message="An item due on March 01, 2025 is 3 day(s) overdue.",
            source_event_type="LoanBecameOverdue",
            source_event_id="evt-test-overdue-001",
            related_loan_id="loan-100",
            action_url="/my-account/checkouts",
            action_label="View My Checkouts",
        )
        test_db.add(notification)
        await test_db.commit()
        await test_db.refresh(notification)

        assert notification.category == PatronNotificationCategory.OVERDUE_NOTICE
        assert notification.related_loan_id == "loan-100"

    @pytest.mark.asyncio
    async def test_create_fine_notification(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test creating a fine assessed notification."""
        notification = PatronNotification(
            patron_id=test_patron.id,
            category=PatronNotificationCategory.FINE_ASSESSED,
            title="Fine of $2.50 added to your account",
            message="An overdue fine of $2.50 has been assessed on your account.",
            source_event_type="FineAssessed",
            source_event_id="evt-test-fine-001",
            related_fine_id="fine-500",
            action_url="/my-account/fines",
            action_label="View My Fines",
        )
        test_db.add(notification)
        await test_db.commit()

        assert notification.related_fine_id == "fine-500"

    @pytest.mark.asyncio
    async def test_idempotency_prevents_duplicate_notifications(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that the same event_id cannot create duplicate notifications."""
        event_id = "evt-idempotent-001"

        # First notification
        n1 = PatronNotification(
            patron_id=test_patron.id,
            category=PatronNotificationCategory.HOLD_AVAILABLE,
            title="First notification",
            message="First",
            source_event_type="HoldReady",
            source_event_id=event_id,
        )
        test_db.add(n1)
        await test_db.commit()

        # Second notification with same event_id should fail (unique constraint)
        n2 = PatronNotification(
            patron_id=test_patron.id,
            category=PatronNotificationCategory.HOLD_AVAILABLE,
            title="Duplicate",
            message="Duplicate",
            source_event_type="HoldReady",
            source_event_id=event_id,
        )
        test_db.add(n2)

        with pytest.raises(Exception):
            await test_db.commit()

        await test_db.rollback()


class TestPatronNotificationRetrieval:
    """Test fetching notifications for a patron."""

    async def _create_test_notifications(
        self, test_db: AsyncSession, patron_id: int, count: int = 5
    ):
        """Helper: create a set of test notifications."""
        categories = [
            PatronNotificationCategory.HOLD_AVAILABLE,
            PatronNotificationCategory.OVERDUE_NOTICE,
            PatronNotificationCategory.FINE_ASSESSED,
            PatronNotificationCategory.CHECKOUT_RECEIPT,
            PatronNotificationCategory.DUE_DATE_REMINDER,
        ]
        notifications = []
        for i in range(count):
            n = PatronNotification(
                patron_id=patron_id,
                category=categories[i % len(categories)],
                title=f"Test Notification {i}",
                message=f"Test message {i}",
                source_event_type="TestEvent",
                source_event_id=f"evt-retrieval-{i}",
            )
            notifications.append(n)
        test_db.add_all(notifications)
        await test_db.commit()
        return notifications

    @pytest.mark.asyncio
    async def test_get_all_notifications(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test fetching all notifications for a patron."""
        service = PatronNotificationService()
        await self._create_test_notifications(test_db, test_patron.id, count=5)

        results, total = await service.get_notifications(
            patron_id=test_patron.id, db=test_db
        )

        assert total == 5
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_get_unread_only(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test filtering for unread notifications only."""
        service = PatronNotificationService()
        await self._create_test_notifications(test_db, test_patron.id, count=5)

        # Mark 2 as read
        result = await test_db.execute(
            select(PatronNotification)
            .where(PatronNotification.patron_id == test_patron.id)
            .limit(2)
        )
        for n in result.scalars().all():
            n.is_read = True
            n.read_at = datetime.now(timezone.utc)
        await test_db.commit()

        results, total = await service.get_notifications(
            patron_id=test_patron.id, db=test_db, unread_only=True
        )

        assert total == 3

    @pytest.mark.asyncio
    async def test_filter_by_category(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test filtering notifications by category."""
        service = PatronNotificationService()
        await self._create_test_notifications(test_db, test_patron.id, count=5)

        results, total = await service.get_notifications(
            patron_id=test_patron.id,
            db=test_db,
            category="hold_available",
        )

        assert total >= 1
        for n in results:
            assert n.category == PatronNotificationCategory.HOLD_AVAILABLE

    @pytest.mark.asyncio
    async def test_pagination(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test pagination of notifications."""
        service = PatronNotificationService()
        await self._create_test_notifications(test_db, test_patron.id, count=10)

        # Page 1
        page1, total = await service.get_notifications(
            patron_id=test_patron.id, db=test_db, limit=3, offset=0
        )
        assert total == 10
        assert len(page1) == 3

        # Page 2
        page2, _ = await service.get_notifications(
            patron_id=test_patron.id, db=test_db, limit=3, offset=3
        )
        assert len(page2) == 3

        # IDs shouldn't overlap
        page1_ids = {n.id for n in page1}
        page2_ids = {n.id for n in page2}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_dismissed_notifications_excluded(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that dismissed notifications are not returned."""
        service = PatronNotificationService()
        await self._create_test_notifications(test_db, test_patron.id, count=5)

        # Dismiss 2
        result = await test_db.execute(
            select(PatronNotification)
            .where(PatronNotification.patron_id == test_patron.id)
            .limit(2)
        )
        for n in result.scalars().all():
            n.is_dismissed = True
            n.dismissed_at = datetime.now(timezone.utc)
        await test_db.commit()

        results, total = await service.get_notifications(
            patron_id=test_patron.id, db=test_db
        )

        assert total == 3

    @pytest.mark.asyncio
    async def test_notifications_ordered_by_created_at_desc(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that notifications are returned newest first."""
        service = PatronNotificationService()
        await self._create_test_notifications(test_db, test_patron.id, count=5)

        results, _ = await service.get_notifications(
            patron_id=test_patron.id, db=test_db
        )

        for i in range(len(results) - 1):
            assert results[i].created_at >= results[i + 1].created_at


class TestUnreadCount:
    """Test unread notification count for UI badge."""

    @pytest.mark.asyncio
    async def test_unread_count(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test counting unread notifications."""
        service = PatronNotificationService()

        # Create 3 notifications
        for i in range(3):
            n = PatronNotification(
                patron_id=test_patron.id,
                category=PatronNotificationCategory.HOLD_AVAILABLE,
                title=f"Test {i}",
                message=f"Test {i}",
                source_event_type="TestEvent",
                source_event_id=f"evt-unread-{i}",
            )
            test_db.add(n)
        await test_db.commit()

        count = await service.get_unread_count(test_patron.id, test_db)
        assert count == 3

    @pytest.mark.asyncio
    async def test_unread_count_excludes_read(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that read notifications are excluded from count."""
        service = PatronNotificationService()

        for i in range(3):
            n = PatronNotification(
                patron_id=test_patron.id,
                category=PatronNotificationCategory.OVERDUE_NOTICE,
                title=f"Test {i}",
                message=f"Test {i}",
                source_event_type="TestEvent",
                source_event_id=f"evt-unread-read-{i}",
                is_read=(i == 0),  # First one is read
            )
            test_db.add(n)
        await test_db.commit()

        count = await service.get_unread_count(test_patron.id, test_db)
        assert count == 2

    @pytest.mark.asyncio
    async def test_unread_count_excludes_dismissed(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that dismissed notifications are excluded from count."""
        service = PatronNotificationService()

        for i in range(3):
            n = PatronNotification(
                patron_id=test_patron.id,
                category=PatronNotificationCategory.FINE_ASSESSED,
                title=f"Test {i}",
                message=f"Test {i}",
                source_event_type="TestEvent",
                source_event_id=f"evt-unread-dismiss-{i}",
                is_dismissed=(i == 0),
            )
            test_db.add(n)
        await test_db.commit()

        count = await service.get_unread_count(test_patron.id, test_db)
        assert count == 2

    @pytest.mark.asyncio
    async def test_zero_unread_when_none_exist(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test unread count returns 0 when patron has no notifications."""
        service = PatronNotificationService()
        count = await service.get_unread_count(test_patron.id, test_db)
        assert count == 0


class TestMarkAsRead:
    """Test marking notifications as read."""

    @pytest.mark.asyncio
    async def test_mark_single_notification_as_read(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test marking a single notification as read."""
        service = PatronNotificationService()

        n = PatronNotification(
            patron_id=test_patron.id,
            category=PatronNotificationCategory.HOLD_AVAILABLE,
            title="Test",
            message="Test",
            source_event_type="HoldReady",
            source_event_id="evt-read-001",
        )
        test_db.add(n)
        await test_db.commit()
        await test_db.refresh(n)

        result = await service.mark_as_read(n.id, test_patron.id, test_db)

        assert result is not None
        assert result.is_read is True
        assert result.read_at is not None

    @pytest.mark.asyncio
    async def test_mark_as_read_returns_none_for_wrong_patron(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that marking someone else's notification returns None."""
        service = PatronNotificationService()

        n = PatronNotification(
            patron_id=test_patron.id,
            category=PatronNotificationCategory.HOLD_AVAILABLE,
            title="Test",
            message="Test",
            source_event_type="HoldReady",
            source_event_id="evt-read-wrong-patron",
        )
        test_db.add(n)
        await test_db.commit()
        await test_db.refresh(n)

        # Try to mark as read with a different patron ID
        result = await service.mark_as_read(n.id, 99999, test_db)
        assert result is None

    @pytest.mark.asyncio
    async def test_mark_all_as_read(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test marking all notifications as read."""
        service = PatronNotificationService()

        for i in range(5):
            n = PatronNotification(
                patron_id=test_patron.id,
                category=PatronNotificationCategory.OVERDUE_NOTICE,
                title=f"Test {i}",
                message=f"Test {i}",
                source_event_type="TestEvent",
                source_event_id=f"evt-readall-{i}",
            )
            test_db.add(n)
        await test_db.commit()

        count = await service.mark_all_as_read(test_patron.id, test_db)
        assert count == 5

        # Verify all are read
        unread = await service.get_unread_count(test_patron.id, test_db)
        assert unread == 0

    @pytest.mark.asyncio
    async def test_mark_all_as_read_only_affects_own_notifications(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that mark_all_as_read only affects the specified patron."""
        service = PatronNotificationService()
        from app.core.security import hash_password
        from app.models.user import User, UserRole

        # Create another patron
        other_patron = User(
            email="other@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Other",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(other_patron)
        await test_db.commit()
        await test_db.refresh(other_patron)

        # Create notifications for both patrons
        for patron in [test_patron, other_patron]:
            n = PatronNotification(
                patron_id=patron.id,
                category=PatronNotificationCategory.HOLD_AVAILABLE,
                title="Test",
                message="Test",
                source_event_type="TestEvent",
                source_event_id=f"evt-readall-patron-{patron.id}",
            )
            test_db.add(n)
        await test_db.commit()

        # Mark test_patron's as read
        await service.mark_all_as_read(test_patron.id, test_db)

        # Other patron's should still be unread
        other_unread = await service.get_unread_count(other_patron.id, test_db)
        assert other_unread == 1


class TestDismissNotification:
    """Test dismissing (soft-deleting) notifications."""

    @pytest.mark.asyncio
    async def test_dismiss_notification(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test dismissing a notification."""
        service = PatronNotificationService()

        n = PatronNotification(
            patron_id=test_patron.id,
            category=PatronNotificationCategory.CHECKOUT_RECEIPT,
            title="Test",
            message="Test",
            source_event_type="ItemCheckedOut",
            source_event_id="evt-dismiss-001",
        )
        test_db.add(n)
        await test_db.commit()
        await test_db.refresh(n)

        result = await service.dismiss_notification(n.id, test_patron.id, test_db)

        assert result is not None
        assert result.is_dismissed is True
        assert result.dismissed_at is not None

    @pytest.mark.asyncio
    async def test_dismiss_returns_none_for_wrong_patron(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that dismissing someone else's notification returns None."""
        service = PatronNotificationService()

        n = PatronNotification(
            patron_id=test_patron.id,
            category=PatronNotificationCategory.CHECKOUT_RECEIPT,
            title="Test",
            message="Test",
            source_event_type="ItemCheckedOut",
            source_event_id="evt-dismiss-wrong",
        )
        test_db.add(n)
        await test_db.commit()
        await test_db.refresh(n)

        result = await service.dismiss_notification(n.id, 99999, test_db)
        assert result is None


class TestNotificationCategories:
    """Test that all notification categories work correctly."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "category",
        [
            PatronNotificationCategory.HOLD_AVAILABLE,
            PatronNotificationCategory.HOLD_EXPIRING,
            PatronNotificationCategory.DUE_DATE_REMINDER,
            PatronNotificationCategory.OVERDUE_NOTICE,
            PatronNotificationCategory.FINE_ASSESSED,
            PatronNotificationCategory.FINE_PAID,
            PatronNotificationCategory.ACCOUNT_BLOCKED,
            PatronNotificationCategory.ACCOUNT_UNBLOCKED,
            PatronNotificationCategory.CHECKOUT_RECEIPT,
        ],
    )
    async def test_all_categories_can_be_persisted(
        self, test_db: AsyncSession, test_patron: User, category
    ):
        """Test that each notification category can be stored and retrieved."""
        n = PatronNotification(
            patron_id=test_patron.id,
            category=category,
            title=f"Test {category.value}",
            message=f"Test message for {category.value}",
            source_event_type="TestEvent",
            source_event_id=f"evt-cat-{category.value}",
        )
        test_db.add(n)
        await test_db.commit()
        await test_db.refresh(n)

        assert n.category == category
        assert n.id is not None
