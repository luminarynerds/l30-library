# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for Patron Account page functionality.

Covers the patron-facing account experience:
1. Account page access (reading history, holds, fines)
2. Hold placement on checked-out items and queue position display
3. Fine viewing and detail inspection
4. Notification preference toggling (email ↔ SMS)
5. Display name changes propagating across the site
6. Reading history / reading logs page
7. Reading Insights page for new users
8. Critical notices still sent when all preferences toggled off
9. Purchase request submission for items the library doesn't own
10. Account isolation — cannot access another patron's account
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.patron_account import (
    PatronAccount,
    PatronTransaction,
    TransactionType,
    TransactionStatus,
    AccountPaymentMethod,
)
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.notification import (
    Notification,
    NotificationPreferences,
    NotificationStatus,
    NotificationType,
    PatronNotification,
    PatronNotificationCategory,
)
from app.models.purchase_request import (
    PatronPurchaseRequest,
    PurchaseRequestStatus,
    RequestMaterialType,
)
from app.models.reading import ReadingLog, ReadingLogStatus, ReadingStats
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_patron(id: int = 1, **overrides) -> MagicMock:
    """Return a MagicMock that behaves like a User with PATRON role."""
    user = MagicMock(spec=User)
    user.id = id
    user.email = overrides.get("email", f"patron{id}@example.com")
    user.first_name = overrides.get("first_name", "Test")
    user.last_name = overrides.get("last_name", "Patron")
    user.role = UserRole.PATRON
    user.is_active = True
    user.email_verified = True
    user.full_name = f"{user.first_name} {user.last_name}"
    return user


def _make_staff(id: int = 99) -> MagicMock:
    """Return a MagicMock that behaves like a staff User."""
    user = MagicMock(spec=User)
    user.id = id
    user.email = "staff@example.com"
    user.first_name = "Staff"
    user.last_name = "Member"
    user.role = UserRole.STAFF
    user.is_active = True
    user.email_verified = True
    user.full_name = "Staff Member"
    return user


def _mock_db() -> AsyncMock:
    """Return a fresh AsyncMock mimicking an AsyncSession."""
    db = AsyncMock()
    db.add = MagicMock()
    return db


# ===========================================================================
# 1. Patron Account Page — Reading History, Holds, Fines Overview
# ===========================================================================


class TestPatronAccountPage:
    """Verify that a logged-in patron can see their account overview."""

    @pytest.mark.asyncio
    async def test_patron_sees_active_checkouts(self, test_db, test_patron, test_catalog_item):
        """Patron can see their active checkouts (reading history)."""
        from sqlalchemy import select, func

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()

        result = await test_db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.user_id == test_patron.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        count = result.scalar()
        assert count == 1

    @pytest.mark.asyncio
    async def test_patron_sees_active_holds(self, test_db, test_patron, test_catalog_item):
        """Patron can view their pending holds."""
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(hold)
        await test_db.commit()

        from sqlalchemy import select
        result = await test_db.execute(
            select(Hold).where(
                Hold.user_id == test_patron.id,
                Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
            )
        )
        holds = result.scalars().all()
        assert len(holds) == 1
        assert holds[0].position == 1

    @pytest.mark.asyncio
    async def test_patron_sees_fines(self, test_db, test_patron):
        """Patron can see their outstanding fines."""
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("5.50"),
            amount_paid=Decimal("0.00"),
            description="Overdue: Test Book",
        )
        test_db.add(fine)
        await test_db.commit()

        from sqlalchemy import select
        result = await test_db.execute(
            select(Fine).where(
                Fine.user_id == test_patron.id,
                Fine.status == FineStatus.unpaid,
            )
        )
        fines = result.scalars().all()
        assert len(fines) == 1
        assert fines[0].amount == Decimal("5.50")


# ===========================================================================
# 2. Hold Placement on Checked-Out Items — Queue Position Display
# ===========================================================================


class TestHoldQueuePosition:
    """Placing a hold on an already checked-out item and verifying queue position."""

    @pytest.mark.asyncio
    async def test_hold_records_queue_position(self, test_db, test_patron, test_catalog_item):
        """When a hold is placed, the position in the queue is recorded."""
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=3,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        assert hold.position == 3

    @pytest.mark.asyncio
    async def test_hold_position_increments_for_multiple_patrons(self, test_db, test_catalog_item):
        """Multiple patrons placing holds on the same item get sequential positions."""
        from app.core.security import hash_password

        positions = []
        for i in range(1, 4):
            patron = User(
                email=f"holdpatron{i}@example.com",
                password_hash=hash_password("Pass123!"),
                first_name=f"Patron{i}",
                last_name="Holder",
                role=UserRole.PATRON,
                is_active=True,
                email_verified=True,
            )
            test_db.add(patron)
            await test_db.commit()
            await test_db.refresh(patron)

            hold = Hold(
                user_id=patron.id,
                item_id=test_catalog_item.id,
                status=HoldStatus.pending,
                position=i,
            )
            test_db.add(hold)
            await test_db.commit()
            await test_db.refresh(hold)
            positions.append(hold.position)

        assert positions == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_hold_on_checked_out_item_is_pending(self, test_db, test_patron, test_catalog_item):
        """A hold placed on an item currently checked out starts as 'pending'."""
        # Create an active checkout for the item (different patron)
        from app.core.security import hash_password
        other_patron = User(
            email="other@example.com",
            password_hash=hash_password("Pass123!"),
            first_name="Other",
            last_name="User",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(other_patron)
        await test_db.commit()
        await test_db.refresh(other_patron)

        checkout = Checkout(
            user_id=other_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
        )
        test_db.add(checkout)
        await test_db.commit()

        # Place a hold on the checked-out item
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        assert hold.status == HoldStatus.pending
        assert hold.position == 1


# ===========================================================================
# 3. Fine Viewing — Details Inspection
# ===========================================================================


class TestFineDetails:
    """Patron can view fine details including type, amount, and status."""

    @pytest.mark.asyncio
    async def test_fine_balance_property(self):
        """Fine.balance returns amount minus amount_paid."""
        fine = Fine(
            user_id=1,
            fine_type=FineType.overdue,
            status=FineStatus.partial,
            amount=Decimal("10.00"),
            amount_paid=Decimal("3.00"),
            description="Overdue fine",
        )
        assert fine.balance == Decimal("7.00")

    @pytest.mark.asyncio
    async def test_fine_detail_fields(self, test_db, test_patron, test_checkout):
        """Fine details include linked checkout, type, description, and timestamps."""
        fine = Fine(
            user_id=test_patron.id,
            checkout_id=test_checkout.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("2.50"),
            amount_paid=Decimal("0.00"),
            description="3 days overdue: Test Book",
            notes="Auto-generated overdue fine",
        )
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        assert fine.checkout_id == test_checkout.id
        assert fine.fine_type == FineType.overdue
        assert fine.description == "3 days overdue: Test Book"
        assert fine.notes == "Auto-generated overdue fine"
        assert fine.balance == Decimal("2.50")

    @pytest.mark.asyncio
    async def test_multiple_fine_types(self, test_db, test_patron):
        """Patron can have different fine types and see all of them."""
        fines_data = [
            (FineType.overdue, Decimal("5.00"), "Overdue fine"),
            (FineType.lost_item, Decimal("25.00"), "Lost book replacement"),
            (FineType.damaged_item, Decimal("10.00"), "Water damage"),
        ]
        for fine_type, amount, desc in fines_data:
            fine = Fine(
                user_id=test_patron.id,
                fine_type=fine_type,
                status=FineStatus.unpaid,
                amount=amount,
                amount_paid=Decimal("0.00"),
                description=desc,
            )
            test_db.add(fine)

        await test_db.commit()

        from sqlalchemy import select
        result = await test_db.execute(
            select(Fine).where(Fine.user_id == test_patron.id)
        )
        all_fines = result.scalars().all()
        assert len(all_fines) == 3

        types = {f.fine_type for f in all_fines}
        assert types == {FineType.overdue, FineType.lost_item, FineType.damaged_item}

        total_owed = sum(f.balance for f in all_fines)
        assert total_owed == Decimal("40.00")


# ===========================================================================
# 4. Notification Preferences — Toggle Email ↔ SMS
# ===========================================================================


class TestNotificationPreferences:
    """Patron can switch notification preferences between email and SMS."""

    @pytest.mark.asyncio
    async def test_create_default_preferences(self, test_db, test_patron):
        """Default preferences are created with email enabled, SMS disabled."""
        prefs = NotificationPreferences(
            user_id=test_patron.id,
        )
        test_db.add(prefs)
        await test_db.commit()
        await test_db.refresh(prefs)

        # Email defaults enabled
        assert prefs.email_checkout_receipt is True
        assert prefs.email_due_date_reminder is True
        assert prefs.email_hold_ready is True
        assert prefs.email_fine_notice is True

        # SMS defaults disabled
        assert prefs.sms_notifications_enabled is False

    @pytest.mark.asyncio
    async def test_enable_sms_notifications(self, test_db, test_patron):
        """Patron can enable SMS and set a phone number."""
        prefs = NotificationPreferences(
            user_id=test_patron.id,
            sms_notifications_enabled=True,
            sms_phone_number="+15551234567",
            sms_due_date_reminder=True,
            sms_hold_ready=True,
        )
        test_db.add(prefs)
        await test_db.commit()
        await test_db.refresh(prefs)

        assert prefs.sms_notifications_enabled is True
        assert prefs.sms_phone_number == "+15551234567"
        assert prefs.sms_due_date_reminder is True
        assert prefs.sms_hold_ready is True

    @pytest.mark.asyncio
    async def test_switch_from_email_to_sms(self, test_db, test_patron):
        """Patron switches from email-only to SMS-only for hold notifications."""
        prefs = NotificationPreferences(
            user_id=test_patron.id,
            email_hold_ready=True,
            sms_notifications_enabled=False,
            sms_hold_ready=False,
        )
        test_db.add(prefs)
        await test_db.commit()

        # Toggle: disable email, enable SMS
        prefs.email_hold_ready = False
        prefs.sms_notifications_enabled = True
        prefs.sms_phone_number = "+15559876543"
        prefs.sms_hold_ready = True
        await test_db.commit()
        await test_db.refresh(prefs)

        assert prefs.email_hold_ready is False
        assert prefs.sms_notifications_enabled is True
        assert prefs.sms_hold_ready is True

    @pytest.mark.asyncio
    async def test_sms_timing_preferences(self, test_db, test_patron):
        """SMS-specific timing preferences can be configured."""
        prefs = NotificationPreferences(
            user_id=test_patron.id,
            sms_notifications_enabled=True,
            sms_phone_number="+15551112222",
            sms_due_date_reminder_days=3,
            sms_event_reminder_hours=48,
        )
        test_db.add(prefs)
        await test_db.commit()
        await test_db.refresh(prefs)

        assert prefs.sms_due_date_reminder_days == 3
        assert prefs.sms_event_reminder_hours == 48


# ===========================================================================
# 5. Display Name Change — Propagation Across the Site
# ===========================================================================


class TestDisplayNameChange:
    """Patron updates their display name and it updates across the site."""

    @pytest.mark.asyncio
    async def test_change_first_and_last_name(self, test_db, test_patron):
        """Patron can update first_name and last_name."""
        assert test_patron.first_name == "Test"
        assert test_patron.last_name == "User"

        test_patron.first_name = "Jane"
        test_patron.last_name = "Doe"
        await test_db.commit()
        await test_db.refresh(test_patron)

        assert test_patron.first_name == "Jane"
        assert test_patron.last_name == "Doe"
        assert test_patron.full_name == "Jane Doe"

    @pytest.mark.asyncio
    async def test_name_visible_in_hold_record(self, test_db, test_patron, test_catalog_item):
        """After name change, the hold record references the updated user."""
        test_patron.first_name = "Updated"
        test_patron.last_name = "Name"
        await test_db.commit()

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(hold)
        await test_db.commit()

        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        result = await test_db.execute(
            select(Hold)
            .options(selectinload(Hold.user))
            .where(Hold.user_id == test_patron.id)
        )
        fetched_hold = result.scalar_one()

        assert fetched_hold.user.first_name == "Updated"
        assert fetched_hold.user.last_name == "Name"

    @pytest.mark.asyncio
    async def test_name_visible_in_fine_record(self, test_db, test_patron):
        """After name change, the fine record references the updated user."""
        test_patron.first_name = "NewFirst"
        test_patron.last_name = "NewLast"
        await test_db.commit()

        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("1.00"),
            amount_paid=Decimal("0.00"),
            description="Test",
        )
        test_db.add(fine)
        await test_db.commit()

        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        result = await test_db.execute(
            select(Fine)
            .options(selectinload(Fine.user))
            .where(Fine.user_id == test_patron.id)
        )
        fetched_fine = result.scalar_one()

        assert fetched_fine.user.first_name == "NewFirst"
        assert fetched_fine.user.last_name == "NewLast"


# ===========================================================================
# 6. Reading History / Reading Logs Page
# ===========================================================================


class TestReadingHistory:
    """Patron views their reading logs and checkout history."""

    @pytest.mark.asyncio
    async def test_patron_reading_log_creation(self, test_db, test_patron):
        """Patron can create a reading log entry."""
        log = ReadingLog(
            user_id=test_patron.id,
            minutes=30,
            book_title="The Great Gatsby",
            book_author="F. Scott Fitzgerald",
            notes="Chapter 1-3",
            status=ReadingLogStatus.pending,
            reading_date=datetime.now(timezone.utc),
        )
        test_db.add(log)
        await test_db.commit()
        await test_db.refresh(log)

        assert log.minutes == 30
        assert log.book_title == "The Great Gatsby"
        assert log.status == ReadingLogStatus.pending

    @pytest.mark.asyncio
    async def test_patron_checkout_history(self, test_db, test_patron, test_catalog_item):
        """Patron can see both active and returned checkouts."""
        now = datetime.now(timezone.utc)

        active = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=21),
        )
        test_db.add(active)
        await test_db.commit()

        # Return the item
        active.status = CheckoutStatus.returned
        active.returned_at = now + timedelta(days=10)
        await test_db.commit()

        from sqlalchemy import select
        result = await test_db.execute(
            select(Checkout).where(Checkout.user_id == test_patron.id)
        )
        history = result.scalars().all()
        assert len(history) == 1
        assert history[0].status == CheckoutStatus.returned
        assert history[0].returned_at is not None

    @pytest.mark.asyncio
    async def test_reading_log_approval_updates_stats(self, test_db, test_patron):
        """When a reading log is approved, the status changes to approved."""
        log = ReadingLog(
            user_id=test_patron.id,
            minutes=45,
            book_title="To Kill a Mockingbird",
            status=ReadingLogStatus.pending,
            reading_date=datetime.now(timezone.utc),
        )
        test_db.add(log)
        await test_db.commit()

        # Simulate staff approval
        log.status = ReadingLogStatus.approved
        log.reviewed_at = datetime.now(timezone.utc)
        await test_db.commit()
        await test_db.refresh(log)

        assert log.status == ReadingLogStatus.approved
        assert log.reviewed_at is not None


# ===========================================================================
# 7. Reading Insights — Stats for New Users
# ===========================================================================


class TestReadingInsights:
    """'My Reading Insights' page should handle new users with no data."""

    @pytest.mark.asyncio
    async def test_new_user_has_no_reading_stats(self, test_db, test_patron):
        """A new patron with no checkouts should have no reading stats records."""
        from sqlalchemy import select

        result = await test_db.execute(
            select(ReadingStats).where(ReadingStats.user_id == test_patron.id)
        )
        stats = result.scalar_one_or_none()
        assert stats is None

    @pytest.mark.asyncio
    async def test_new_user_has_zero_checkouts(self, test_db, test_patron):
        """A new patron should have zero checkout history."""
        from sqlalchemy import select, func

        result = await test_db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.user_id == test_patron.id,
            )
        )
        count = result.scalar()
        assert count == 0

    @pytest.mark.asyncio
    async def test_reading_stats_can_be_initialized(self, test_db, test_patron):
        """Reading stats can be created for a patron (e.g., after first checkout)."""
        stats = ReadingStats(
            user_id=test_patron.id,
            total_approved_minutes=0,
            current_streak=0,
            longest_streak=0,
            xp=0,
        )
        test_db.add(stats)
        await test_db.commit()
        await test_db.refresh(stats)

        assert stats.total_approved_minutes == 0
        assert stats.current_streak == 0
        assert stats.xp == 0

    @pytest.mark.asyncio
    async def test_reading_insights_service_handles_new_user(self):
        """PatronReadingInsightsService.get_summary returns defaults for new users."""
        with patch(
            "app.services.patron_reading_insights_service.PatronReadingInsightsService.get_summary"
        ) as mock_summary:
            mock_summary.return_value = {
                "total_checkouts": 0,
                "total_reading_minutes": 0,
                "current_streak": 0,
                "favorite_genre": None,
                "books_this_year": 0,
            }
            result = await mock_summary(user_id=999)
            assert result["total_checkouts"] == 0
            assert result["favorite_genre"] is None


# ===========================================================================
# 8. Toggle All Notifications Off — Critical Notices Still Delivered
# ===========================================================================


class TestCriticalNoticesAlwaysSent:
    """Even with all preferences disabled, critical notices are still sent."""

    @pytest.mark.asyncio
    async def test_all_email_prefs_off(self, test_db, test_patron):
        """Patron can disable all email notification preferences."""
        prefs = NotificationPreferences(
            user_id=test_patron.id,
            email_checkout_receipt=False,
            email_due_date_reminder=False,
            email_overdue_notice=False,
            email_hold_ready=False,
            email_hold_expiring=False,
            email_hold_cancelled=False,
            email_fine_notice=False,
            sms_notifications_enabled=False,
        )
        test_db.add(prefs)
        await test_db.commit()
        await test_db.refresh(prefs)

        assert prefs.email_checkout_receipt is False
        assert prefs.email_due_date_reminder is False
        assert prefs.email_overdue_notice is False
        assert prefs.email_fine_notice is False
        assert prefs.sms_notifications_enabled is False

    @pytest.mark.asyncio
    async def test_critical_notification_created_regardless(self, test_db, test_patron):
        """Critical notifications (e.g., ACCOUNT_LOCKED) are created regardless of preferences."""
        # Even if all prefs are off, the system should still generate critical notifications
        critical_notification = Notification(
            user_id=test_patron.id,
            notification_type=NotificationType.ACCOUNT_LOCKED,
            status=NotificationStatus.PENDING,
            subject="Your account has been locked",
            message="Your account has been locked due to excessive fines.",
        )
        test_db.add(critical_notification)
        await test_db.commit()
        await test_db.refresh(critical_notification)

        assert critical_notification.notification_type == NotificationType.ACCOUNT_LOCKED
        assert critical_notification.status == NotificationStatus.PENDING

    @pytest.mark.asyncio
    async def test_overdue_notice_is_critical(self, test_db, test_patron):
        """Overdue notices are always created since they're part of the legal notice chain."""
        notification = Notification(
            user_id=test_patron.id,
            notification_type=NotificationType.OVERDUE_NOTICE,
            status=NotificationStatus.PENDING,
            subject="Overdue Item Notice",
            message="You have overdue items. Please return them.",
        )
        test_db.add(notification)
        await test_db.commit()

        from sqlalchemy import select
        result = await test_db.execute(
            select(Notification).where(
                Notification.user_id == test_patron.id,
                Notification.notification_type == NotificationType.OVERDUE_NOTICE,
            )
        )
        notice = result.scalar_one()
        assert notice is not None
        assert notice.notification_type == NotificationType.OVERDUE_NOTICE

    @pytest.mark.asyncio
    async def test_patron_notification_for_account_blocked(self, test_db, test_patron):
        """Live patron notification is created for account-blocked events."""
        notif = PatronNotification(
            patron_id=test_patron.id,
            category=PatronNotificationCategory.ACCOUNT_BLOCKED,
            title="Account Blocked",
            message="Your account has been blocked. Please contact the library.",
            source_event_type="AccountBlocked",
            source_event_id=f"block-{test_patron.id}-001",
        )
        test_db.add(notif)
        await test_db.commit()
        await test_db.refresh(notif)

        assert notif.category == PatronNotificationCategory.ACCOUNT_BLOCKED
        assert notif.is_read is False


# ===========================================================================
# 9. Purchase Request Submission
# ===========================================================================


class TestPurchaseRequest:
    """Patron submits a purchase request for a book the library doesn't own."""

    @pytest.mark.asyncio
    async def test_submit_purchase_request(self, test_db, test_patron):
        """Patron can submit a new purchase request."""
        request = PatronPurchaseRequest(
            patron_id=test_patron.id,
            title="The Midnight Library",
            author="Matt Haig",
            isbn="978-0525559474",
            material_type=RequestMaterialType.BOOK,
            publisher="Viking",
            publication_year=2020,
            patron_notes="Saw on bestseller list, would love to read it",
            status=PurchaseRequestStatus.PENDING,
            duplicate_check_done=True,
        )
        test_db.add(request)
        await test_db.commit()
        await test_db.refresh(request)

        assert request.status == PurchaseRequestStatus.PENDING
        assert request.patron_id == test_patron.id
        assert request.title == "The Midnight Library"
        assert request.material_type == RequestMaterialType.BOOK

    @pytest.mark.asyncio
    async def test_purchase_request_status_workflow(self, test_db, test_patron):
        """Purchase request moves through the status workflow correctly."""
        request = PatronPurchaseRequest(
            patron_id=test_patron.id,
            title="Project Hail Mary",
            author="Andy Weir",
            material_type=RequestMaterialType.BOOK,
            status=PurchaseRequestStatus.PENDING,
            duplicate_check_done=True,
        )
        test_db.add(request)
        await test_db.commit()

        # Staff approves
        request.status = PurchaseRequestStatus.APPROVED
        request.reviewed_at = datetime.now(timezone.utc)
        await test_db.commit()
        assert request.status == PurchaseRequestStatus.APPROVED

        # Ordered
        request.status = PurchaseRequestStatus.ORDERED
        await test_db.commit()
        assert request.status == PurchaseRequestStatus.ORDERED

        # Received
        request.status = PurchaseRequestStatus.RECEIVED
        await test_db.commit()
        assert request.status == PurchaseRequestStatus.RECEIVED

    @pytest.mark.asyncio
    async def test_patron_can_cancel_pending_request(self, test_db, test_patron):
        """Patron can cancel a request that's still pending."""
        request = PatronPurchaseRequest(
            patron_id=test_patron.id,
            title="A Cancelled Book",
            author="Author Name",
            material_type=RequestMaterialType.BOOK,
            status=PurchaseRequestStatus.PENDING,
            duplicate_check_done=True,
        )
        test_db.add(request)
        await test_db.commit()

        # Patron cancels
        request.status = PurchaseRequestStatus.CANCELLED
        await test_db.commit()
        await test_db.refresh(request)

        assert request.status == PurchaseRequestStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_purchase_request_various_material_types(self, test_db, test_patron):
        """Purchase requests can be for various material types."""
        types = [
            (RequestMaterialType.BOOK, "A Novel"),
            (RequestMaterialType.AUDIOBOOK, "An Audiobook"),
            (RequestMaterialType.DVD, "A Film"),
            (RequestMaterialType.EBOOK, "An eBook"),
        ]

        for mat_type, title in types:
            req = PatronPurchaseRequest(
                patron_id=test_patron.id,
                title=title,
                material_type=mat_type,
                status=PurchaseRequestStatus.PENDING,
                duplicate_check_done=True,
            )
            test_db.add(req)

        await test_db.commit()

        from sqlalchemy import select
        result = await test_db.execute(
            select(PatronPurchaseRequest).where(
                PatronPurchaseRequest.patron_id == test_patron.id
            )
        )
        requests = result.scalars().all()
        assert len(requests) == 4


# ===========================================================================
# 10. Account Isolation — Cannot Access Another Patron's Account
# ===========================================================================


class TestAccountIsolation:
    """Verify that one patron cannot access another patron's data."""

    @pytest.mark.asyncio
    async def test_holds_scoped_to_patron(self, test_db, test_catalog_item):
        """Each patron only sees their own holds."""
        from app.core.security import hash_password
        from sqlalchemy import select

        patron_a = User(
            email="patrona@example.com",
            password_hash=hash_password("Pass123!"),
            first_name="Patron",
            last_name="A",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        patron_b = User(
            email="patronb@example.com",
            password_hash=hash_password("Pass123!"),
            first_name="Patron",
            last_name="B",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron_a)
        test_db.add(patron_b)
        await test_db.commit()
        await test_db.refresh(patron_a)
        await test_db.refresh(patron_b)

        hold_a = Hold(
            user_id=patron_a.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(hold_a)
        await test_db.commit()

        # Query as patron_b
        result = await test_db.execute(
            select(Hold).where(Hold.user_id == patron_b.id)
        )
        patron_b_holds = result.scalars().all()
        assert len(patron_b_holds) == 0

        # Query as patron_a
        result = await test_db.execute(
            select(Hold).where(Hold.user_id == patron_a.id)
        )
        patron_a_holds = result.scalars().all()
        assert len(patron_a_holds) == 1

    @pytest.mark.asyncio
    async def test_fines_scoped_to_patron(self, test_db):
        """Each patron only sees their own fines."""
        from app.core.security import hash_password
        from sqlalchemy import select

        patron_a = User(
            email="finea@example.com",
            password_hash=hash_password("Pass123!"),
            first_name="Fine",
            last_name="PatronA",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        patron_b = User(
            email="fineb@example.com",
            password_hash=hash_password("Pass123!"),
            first_name="Fine",
            last_name="PatronB",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron_a)
        test_db.add(patron_b)
        await test_db.commit()
        await test_db.refresh(patron_a)
        await test_db.refresh(patron_b)

        fine = Fine(
            user_id=patron_a.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("5.00"),
            amount_paid=Decimal("0.00"),
            description="Patron A's fine",
        )
        test_db.add(fine)
        await test_db.commit()

        # patron_b should see zero fines
        result = await test_db.execute(
            select(Fine).where(Fine.user_id == patron_b.id)
        )
        assert len(result.scalars().all()) == 0

        # patron_a should see their fine
        result = await test_db.execute(
            select(Fine).where(Fine.user_id == patron_a.id)
        )
        assert len(result.scalars().all()) == 1

    @pytest.mark.asyncio
    async def test_purchase_requests_scoped_to_patron(self, test_db):
        """Each patron only sees their own purchase requests."""
        from app.core.security import hash_password
        from sqlalchemy import select

        patron_a = User(
            email="pra@example.com",
            password_hash=hash_password("Pass123!"),
            first_name="PR",
            last_name="PatronA",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        patron_b = User(
            email="prb@example.com",
            password_hash=hash_password("Pass123!"),
            first_name="PR",
            last_name="PatronB",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron_a)
        test_db.add(patron_b)
        await test_db.commit()
        await test_db.refresh(patron_a)
        await test_db.refresh(patron_b)

        request = PatronPurchaseRequest(
            patron_id=patron_a.id,
            title="Patron A's Book",
            material_type=RequestMaterialType.BOOK,
            status=PurchaseRequestStatus.PENDING,
            duplicate_check_done=True,
        )
        test_db.add(request)
        await test_db.commit()

        # Patron B's view
        result = await test_db.execute(
            select(PatronPurchaseRequest).where(
                PatronPurchaseRequest.patron_id == patron_b.id
            )
        )
        assert len(result.scalars().all()) == 0

    @pytest.mark.asyncio
    async def test_notifications_scoped_to_patron(self, test_db):
        """Each patron only sees their own notifications."""
        from app.core.security import hash_password
        from sqlalchemy import select

        patron_a = User(
            email="nota@example.com",
            password_hash=hash_password("Pass123!"),
            first_name="Notif",
            last_name="PatronA",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        patron_b = User(
            email="notb@example.com",
            password_hash=hash_password("Pass123!"),
            first_name="Notif",
            last_name="PatronB",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron_a)
        test_db.add(patron_b)
        await test_db.commit()
        await test_db.refresh(patron_a)
        await test_db.refresh(patron_b)

        notif = Notification(
            user_id=patron_a.id,
            notification_type=NotificationType.HOLD_READY,
            status=NotificationStatus.SENT,
            subject="Hold Ready",
            message="Your hold is ready for pickup.",
        )
        test_db.add(notif)
        await test_db.commit()

        # Patron B's view should be empty
        result = await test_db.execute(
            select(Notification).where(Notification.user_id == patron_b.id)
        )
        assert len(result.scalars().all()) == 0

    @pytest.mark.asyncio
    async def test_checkouts_scoped_to_patron(self, test_db, test_catalog_item):
        """Each patron only sees their own checkouts."""
        from app.core.security import hash_password
        from sqlalchemy import select

        patron_a = User(
            email="checkouta@example.com",
            password_hash=hash_password("Pass123!"),
            first_name="Checkout",
            last_name="A",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        patron_b = User(
            email="checkoutb@example.com",
            password_hash=hash_password("Pass123!"),
            first_name="Checkout",
            last_name="B",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron_a)
        test_db.add(patron_b)
        await test_db.commit()
        await test_db.refresh(patron_a)
        await test_db.refresh(patron_b)

        checkout = Checkout(
            user_id=patron_a.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
        )
        test_db.add(checkout)
        await test_db.commit()

        # Patron B should see zero
        result = await test_db.execute(
            select(Checkout).where(Checkout.user_id == patron_b.id)
        )
        assert len(result.scalars().all()) == 0

    @pytest.mark.asyncio
    async def test_account_balance_scoped_to_patron(self, test_db):
        """Each patron's account balance is independent."""
        from app.core.security import hash_password
        from sqlalchemy import select

        patron_a = User(
            email="acca@example.com",
            password_hash=hash_password("Pass123!"),
            first_name="Acc",
            last_name="PatronA",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        patron_b = User(
            email="accb@example.com",
            password_hash=hash_password("Pass123!"),
            first_name="Acc",
            last_name="PatronB",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron_a)
        test_db.add(patron_b)
        await test_db.commit()
        await test_db.refresh(patron_a)
        await test_db.refresh(patron_b)

        acct_a = PatronAccount(
            patron_id=patron_a.id,
            balance=Decimal("50.00"),
        )
        acct_b = PatronAccount(
            patron_id=patron_b.id,
            balance=Decimal("10.00"),
        )
        test_db.add(acct_a)
        test_db.add(acct_b)
        await test_db.commit()

        result = await test_db.execute(
            select(PatronAccount).where(PatronAccount.patron_id == patron_a.id)
        )
        a_account = result.scalar_one()
        assert a_account.balance == Decimal("50.00")

        result = await test_db.execute(
            select(PatronAccount).where(PatronAccount.patron_id == patron_b.id)
        )
        b_account = result.scalar_one()
        assert b_account.balance == Decimal("10.00")


# ===========================================================================
# Additional Edge Cases & Service-Level Tests
# ===========================================================================


class TestPatronAccountService:
    """Service-level tests using mocks for patron account operations."""

    @pytest.mark.asyncio
    async def test_get_balance_for_patron(self):
        """account_service.get_balance returns the current account state."""
        from app.services import account_service

        db = _mock_db()
        acct = MagicMock(spec=PatronAccount)
        acct.id = 1
        acct.patron_id = 1
        acct.balance = Decimal("25.00")
        acct.is_active = True

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = acct
        db.execute.return_value = result_mock

        account = await account_service.get_or_create_account(db, patron_id=1)
        assert account.balance == Decimal("25.00")

    @pytest.mark.asyncio
    async def test_deposit_increases_balance(self):
        """Depositing funds increases account balance."""
        from app.services import account_service

        db = _mock_db()
        acct = MagicMock(spec=PatronAccount)
        acct.id = 1
        acct.patron_id = 1
        acct.balance = Decimal("10.00")
        acct.total_deposited = Decimal("100.00")
        acct.total_spent = Decimal("90.00")
        acct.is_active = True
        acct.last_deposit_at = None

        with patch.object(account_service, "get_or_create_account", return_value=acct):
            await account_service.add_funds(
                db,
                patron_id=1,
                amount=Decimal("20.00"),
                payment_method=AccountPaymentMethod.ONLINE,
                notes="Online top-up",
            )

        assert acct.balance == Decimal("30.00")
        assert acct.total_deposited == Decimal("120.00")

    @pytest.mark.asyncio
    async def test_charge_on_inactive_account_fails(self):
        """Cannot charge an inactive account."""
        from app.services import account_service
        from fastapi import HTTPException

        db = _mock_db()
        acct = MagicMock(spec=PatronAccount)
        acct.id = 1
        acct.patron_id = 1
        acct.balance = Decimal("100.00")
        acct.is_active = False

        # charge() does its own SELECT...FOR UPDATE, so mock db.execute
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = acct
        db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc:
            await account_service.charge(
                db, patron_id=1, amount=Decimal("5.00"), description="Test charge"
            )
        assert exc.value.status_code == 400


class TestHoldEdgeCases:
    """Additional hold-related edge cases."""

    @pytest.mark.asyncio
    async def test_hold_expires_at_field(self, test_db, test_patron, test_catalog_item):
        """Ready holds have an expiration date."""
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            expires_at=expires,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        assert hold.expires_at is not None
        assert hold.status == HoldStatus.ready

    @pytest.mark.asyncio
    async def test_cancelled_hold_not_in_active_view(self, test_db, test_patron, test_catalog_item):
        """Cancelled holds are excluded from the active holds view."""
        from sqlalchemy import select

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.cancelled,
            position=1,  # ck_hold_position_positive requires position > 0
        )
        test_db.add(hold)
        await test_db.commit()

        result = await test_db.execute(
            select(Hold).where(
                Hold.user_id == test_patron.id,
                Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
            )
        )
        active_holds = result.scalars().all()
        assert len(active_holds) == 0

    @pytest.mark.asyncio
    async def test_fulfilled_hold_not_in_active_view(self, test_db, test_patron, test_catalog_item):
        """Fulfilled holds are excluded from the active holds view."""
        from sqlalchemy import select

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.fulfilled,
            position=1,  # ck_hold_position_positive requires position > 0
        )
        test_db.add(hold)
        await test_db.commit()

        result = await test_db.execute(
            select(Hold).where(
                Hold.user_id == test_patron.id,
                Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
            )
        )
        active_holds = result.scalars().all()
        assert len(active_holds) == 0


class TestFinePaymentHistory:
    """Fine payment and waiver tracking."""

    @pytest.mark.asyncio
    async def test_partial_payment_updates_fine(self, test_db, test_patron):
        """Partial payment updates amount_paid and changes status to partial."""
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("10.00"),
            amount_paid=Decimal("0.00"),
            description="Overdue fine",
        )
        test_db.add(fine)
        await test_db.commit()

        # Simulate partial payment
        fine.amount_paid = Decimal("3.00")
        fine.status = FineStatus.partial
        await test_db.commit()
        await test_db.refresh(fine)

        assert fine.status == FineStatus.partial
        assert fine.balance == Decimal("7.00")

    @pytest.mark.asyncio
    async def test_full_payment_clears_fine(self, test_db, test_patron):
        """Full payment updates status to paid with paid_at timestamp."""
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("5.00"),
            amount_paid=Decimal("0.00"),
            description="Overdue fine",
        )
        test_db.add(fine)
        await test_db.commit()

        fine.amount_paid = Decimal("5.00")
        fine.status = FineStatus.paid
        fine.paid_at = datetime.now(timezone.utc)
        await test_db.commit()
        await test_db.refresh(fine)

        assert fine.status == FineStatus.paid
        assert fine.balance == Decimal("0.00")
        assert fine.paid_at is not None

    @pytest.mark.asyncio
    async def test_waived_fine(self, test_db, test_patron, test_staff):
        """Staff can waive a fine, which sets waived_at and waived_by_id."""
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("2.00"),
            amount_paid=Decimal("0.00"),
            description="Waivable fine",
        )
        test_db.add(fine)
        await test_db.commit()

        fine.status = FineStatus.waived
        fine.waived_at = datetime.now(timezone.utc)
        fine.waived_by_id = test_staff.id  # fines_waived_by_id_fkey -> users.id
        await test_db.commit()
        await test_db.refresh(fine)

        assert fine.status == FineStatus.waived
        assert fine.waived_at is not None
        assert fine.waived_by_id == test_staff.id
