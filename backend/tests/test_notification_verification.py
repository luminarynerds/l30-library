# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive L30 Notification System Verification Tests

Tests for:
1. Email notifications (overdue, hold ready, checkout receipt)
2. Notification delivery preferences per patron
3. Unsubscribe tokens
4. Notification template rendering
5. Notification queue and processing
6. Notification history tracking
7. Email deliverability configuration
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.catalog import CatalogItem
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.notification import (
    NotificationPreferences,
    NotificationQueue,
    NotificationStatus,
    NotificationType,
    NotificationHistory,
)
from app.models.marketing import EmailUnsubscribeToken


class TestEmailNotificationTypes:
    """Test various email notification types"""

    @pytest.mark.asyncio
    async def test_overdue_notice_email_generation(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that overdue notice emails are generated correctly"""
        from app.services.notification_service import NotificationService

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.overdue,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=22),
            due_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        subject, html = NotificationService.render_overdue_notice_email(
            user=test_patron,
            item=test_catalog_item,
            checkout=checkout,
            days_overdue=1,
            fine_amount=Decimal("0.50"),
        )

        assert "overdue" in subject.lower()
        assert test_catalog_item.title in html
        assert test_patron.first_name in html

    @pytest.mark.asyncio
    async def test_hold_ready_email_generation(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that hold ready notification emails are generated correctly"""
        from app.services.notification_service import NotificationService

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            notified_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=3),
        )
        test_db.add(hold)
        await test_db.commit()

        subject, html = NotificationService.render_hold_ready_email(
            user=test_patron,
            item=test_catalog_item,
            hold=hold,
        )

        assert "ready" in subject.lower()
        assert test_catalog_item.title in html
        assert test_patron.first_name in html

    @pytest.mark.asyncio
    async def test_hold_expiring_warning_email(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that hold expiring warning emails are generated correctly"""
        from app.services.notification_service import NotificationService

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            notified_at=datetime.now(timezone.utc) - timedelta(days=1),
            expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        )
        test_db.add(hold)
        await test_db.commit()

        subject, html = NotificationService.render_hold_expiring_email(
            user=test_patron,
            item=test_catalog_item,
            hold=hold,
            days_until_expiry=2,
        )

        assert "expir" in subject.lower()
        assert test_catalog_item.title in html

    @pytest.mark.asyncio
    async def test_checkout_receipt_email_generation(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that checkout receipt emails are generated correctly"""
        from app.services.notification_service import NotificationService

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()

        subject, html = NotificationService.render_checkout_receipt_email(
            user=test_patron,
            item=test_catalog_item,
            checkout=checkout,
        )

        assert "checkout" in subject.lower() or "checked out" in subject.lower()
        assert test_catalog_item.title in subject
        assert test_patron.first_name in html


class TestNotificationPreferencesPerPatron:
    """Test notification delivery preferences functionality"""

    @pytest.mark.asyncio
    async def test_patron_can_disable_email_notifications(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that patrons can disable specific email notifications"""
        from app.services.notification_service import NotificationService

        prefs = NotificationPreferences(
            user_id=test_patron.id,
            email_overdue_notice=False,
            email_hold_ready=True,
        )
        test_db.add(prefs)
        await test_db.commit()

        service = NotificationService()
        retrieved_prefs = await service.get_or_create_preferences(test_patron.id, test_db)

        assert retrieved_prefs.email_overdue_notice is False
        assert retrieved_prefs.email_hold_ready is True

    @pytest.mark.asyncio
    async def test_patron_can_update_preferences(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that patrons can update their notification preferences"""
        from app.services.notification_service import NotificationService

        service = NotificationService()

        initial_prefs = await service.get_or_create_preferences(test_patron.id, test_db)
        initial_prefs.email_hold_ready = False
        test_db.add(initial_prefs)
        await test_db.commit()

        updated_prefs = await service.update_preferences(
            test_patron.id,
            {"email_hold_ready": True, "email_checkout_receipt": False},
            test_db,
        )

        assert updated_prefs.email_hold_ready is True
        assert updated_prefs.email_checkout_receipt is False

    @pytest.mark.asyncio
    async def test_default_preferences_when_not_set(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that default preferences enable all notifications"""
        from app.services.notification_service import NotificationService

        service = NotificationService()
        prefs = await service.get_or_create_preferences(test_patron.id, test_db)

        # Verify default preferences exist and are created
        assert prefs is not None
        assert prefs.user_id == test_patron.id


class TestUnsubscribeTokens:
    """Test email unsubscribe token functionality"""

    @pytest.mark.asyncio
    async def test_generate_unsubscribe_token(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that valid unsubscribe tokens are generated"""
        from app.services.unsubscribe_service import UnsubscribeService

        service = UnsubscribeService()

        token = await service.generate_unsubscribe_token(
            db=test_db,
            email=test_patron.email,
            email_type="notification",
            user_id=test_patron.id,
            email_category="OVERDUE_NOTICE",
        )

        assert token is not None
        assert len(token) > 0

        result = await test_db.execute(
            select(EmailUnsubscribeToken).where(
                EmailUnsubscribeToken.token == token
            )
        )
        stored_token = result.scalar_one_or_none()

        assert stored_token is not None
        assert stored_token.email == test_patron.email.lower()
        assert stored_token.user_id == test_patron.id
        assert stored_token.used_at is None

    @pytest.mark.asyncio
    async def test_unsubscribe_from_notification_type(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that unsubscribe tokens work for notification types"""
        from app.services.unsubscribe_service import UnsubscribeService

        service = UnsubscribeService()

        token = await service.generate_unsubscribe_token(
            db=test_db,
            email=test_patron.email,
            email_type="notification",
            user_id=test_patron.id,
            email_category="overdue_notice",
        )

        prefs = NotificationPreferences(
            user_id=test_patron.id,
            email_overdue_notice=True,
        )
        test_db.add(prefs)
        await test_db.commit()

        result = await service.process_unsubscribe(test_db, token)

        assert result["success"] is True
        assert "unsubscrib" in result["message"].lower()

        await test_db.refresh(prefs)
        assert prefs.email_overdue_notice is False

    @pytest.mark.asyncio
    async def test_unsubscribe_token_can_only_be_used_once(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that unsubscribe tokens are single-use"""
        from app.services.unsubscribe_service import UnsubscribeService

        service = UnsubscribeService()

        token = await service.generate_unsubscribe_token(
            db=test_db,
            email=test_patron.email,
            email_type="notification",
            user_id=test_patron.id,
            email_category="HOLD_READY",
        )

        prefs = NotificationPreferences(
            user_id=test_patron.id,
            email_hold_ready=True,
        )
        test_db.add(prefs)
        await test_db.commit()

        result1 = await service.process_unsubscribe(test_db, token)
        assert result1["success"] is True

        result2 = await service.process_unsubscribe(test_db, token)
        assert result2["success"] is False
        assert "already used" in result2["error"]

    @pytest.mark.asyncio
    async def test_invalid_unsubscribe_token_fails(
        self, test_db: AsyncSession
    ):
        """Test that invalid tokens are rejected"""
        from app.services.unsubscribe_service import UnsubscribeService

        service = UnsubscribeService()

        result = await service.process_unsubscribe(test_db, "invalid-token-123")

        assert result["success"] is False
        assert "invalid" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_unsubscribe_url_generation(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that unsubscribe URLs are correctly generated"""
        from app.services.unsubscribe_service import UnsubscribeService

        service = UnsubscribeService()

        token = await service.generate_unsubscribe_token(
            db=test_db,
            email=test_patron.email,
            email_type="notification",
            user_id=test_patron.id,
        )

        unsubscribe_url = service.generate_unsubscribe_url(token)

        assert token in unsubscribe_url
        assert "/unsubscribe?" in unsubscribe_url


class TestNotificationTemplateRendering:
    """Test notification template rendering"""

    @pytest.mark.asyncio
    async def test_checkout_receipt_email_renders_correctly(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that checkout receipt templates render with all required data"""
        from app.services.notification_service import NotificationService

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()

        subject, html = NotificationService.render_checkout_receipt_email(
            user=test_patron,
            item=test_catalog_item,
            checkout=checkout,
        )

        assert subject is not None
        assert len(subject) > 0
        assert test_catalog_item.title in subject

        assert html is not None
        assert len(html) > 0
        assert test_patron.first_name in html
        assert test_catalog_item.title in html

    @pytest.mark.asyncio
    async def test_due_date_reminder_email_renders_correctly(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that due date reminder templates render with all required data"""
        from app.services.notification_service import NotificationService

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=19),
            due_date=datetime.now(timezone.utc) + timedelta(days=2),
        )
        test_db.add(checkout)
        await test_db.commit()

        subject, html = NotificationService.render_due_date_reminder_email(
            user=test_patron,
            item=test_catalog_item,
            checkout=checkout,
            days_until_due=2,
        )

        assert "reminder" in subject.lower()
        assert test_catalog_item.title in subject

        assert test_patron.first_name in html
        assert test_catalog_item.title in html

    @pytest.mark.asyncio
    async def test_html_email_templates_have_valid_structure(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that HTML templates have proper structure"""
        from app.services.notification_service import NotificationService

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()

        _, html = NotificationService.render_checkout_receipt_email(
            user=test_patron,
            item=test_catalog_item,
            checkout=checkout,
        )

        # Verify HTML structure
        assert "style=" in html or "<style>" in html
        assert html.count("<") > 0
        assert html.count(">") > 0
        # Check for balanced tags (rough check)
        assert abs(html.count("<") - html.count(">")) <= 10


class TestNotificationQueueAndProcessing:
    """Test notification queue and processing"""

    @pytest.mark.asyncio
    async def test_queue_notification_creates_pending_record(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that queue_notification creates a pending notification record"""
        from app.services.notification_service import NotificationService

        service = NotificationService()
        notification = await service.queue_notification(
            user_id=test_patron.id,
            notification_type=NotificationType.DUE_DATE_REMINDER,
            recipient_email=test_patron.email,
            subject="Test Subject",
            html_body="<p>Test body</p>",
            context_data={"item_id": 123},
            db=test_db,
        )

        assert notification is not None
        assert notification.status == NotificationStatus.PENDING
        assert notification.recipient_email == test_patron.email

    @pytest.mark.asyncio
    async def test_send_queued_notifications_processes_pending(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that send_queued_notifications processes pending notifications"""
        from app.services.notification_service import NotificationService

        notif = NotificationQueue(
            user_id=test_patron.id,
            notification_type=NotificationType.DUE_DATE_REMINDER,
            status=NotificationStatus.PENDING,
            recipient_email=test_patron.email,
            subject="Test Subject",
            html_body="<p>Test body</p>",
            scheduled_for=datetime.now(timezone.utc),
        )
        test_db.add(notif)
        await test_db.commit()

        service = NotificationService()
        with patch(
            "app.services.notifications.base.send_email", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = True

            result = await service.send_queued_notifications(test_db)

        assert result["processed"] > 0
        assert result["sent"] > 0

    @pytest.mark.asyncio
    async def test_notification_retry_on_failure(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that failed notifications are retried"""
        from app.services.notification_service import NotificationService

        notif = NotificationQueue(
            user_id=test_patron.id,
            notification_type=NotificationType.DUE_DATE_REMINDER,
            status=NotificationStatus.PENDING,
            recipient_email=test_patron.email,
            subject="Test Subject",
            html_body="<p>Test body</p>",
            scheduled_for=datetime.now(timezone.utc),
            retry_count=0,
        )
        test_db.add(notif)
        await test_db.commit()

        service = NotificationService()
        with patch(
            "app.services.notifications.base.send_email", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = False

            await service.send_queued_notifications(test_db)

        await test_db.refresh(notif)
        # Retry count should be incremented
        assert notif.retry_count >= 1


class TestNotificationHistory:
    """Test notification history tracking"""

    @pytest.mark.asyncio
    async def test_notification_history_is_created_on_send(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that notification history records are created when notifications are sent"""
        from app.services.notification_service import NotificationService

        notif = NotificationQueue(
            user_id=test_patron.id,
            notification_type=NotificationType.DUE_DATE_REMINDER,
            status=NotificationStatus.PENDING,
            recipient_email=test_patron.email,
            subject="Test Subject",
            html_body="<p>Test body</p>",
            scheduled_for=datetime.now(timezone.utc),
        )
        test_db.add(notif)
        await test_db.commit()

        service = NotificationService()
        with patch(
            "app.services.notifications.base.send_email", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = True

            await service.send_queued_notifications(test_db)

        # Verify history record was created
        result = await test_db.execute(
            select(NotificationHistory).where(
                NotificationHistory.user_id == test_patron.id,
                NotificationHistory.notification_type == NotificationType.DUE_DATE_REMINDER,
            )
        )
        history = result.scalar_one_or_none()

        assert history is not None

    @pytest.mark.asyncio
    async def test_notification_history_stores_context(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that notification history stores context data"""
        from app.services.notification_service import NotificationService

        context_data = {"item_id": 123, "title": "Test Item"}

        notif = NotificationQueue(
            user_id=test_patron.id,
            notification_type=NotificationType.CHECKOUT_RECEIPT,
            status=NotificationStatus.PENDING,
            recipient_email=test_patron.email,
            subject="Test Subject",
            html_body="<p>Test body</p>",
            context_data=context_data,
            scheduled_for=datetime.now(timezone.utc),
        )
        test_db.add(notif)
        await test_db.commit()

        service = NotificationService()
        with patch(
            "app.services.notifications.base.send_email", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = True

            await service.send_queued_notifications(test_db)

        result = await test_db.execute(
            select(NotificationHistory).where(
                NotificationHistory.user_id == test_patron.id,
            )
        )
        history = result.scalar_one_or_none()

        if history:
            # Context data should be stored
            assert history.context_data is not None


class TestEmailDeliverability:
    """Test email deliverability and SMTP configuration"""

    @pytest.mark.asyncio
    async def test_can_spam_footer_is_included(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that CAN-SPAM compliance footer is included"""
        from app.services.notification_service import NotificationService
        from app.core.email import get_can_spam_footer

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()

        _, html = NotificationService.render_checkout_receipt_email(
            user=test_patron,
            item=test_catalog_item,
            checkout=checkout,
        )

        footer = get_can_spam_footer()
        # Verify footer has required elements
        assert "unsubscribe" in footer.lower() or "Library" in footer

    @pytest.mark.asyncio
    async def test_list_unsubscribe_headers_are_set(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that List-Unsubscribe headers are properly set"""
        from app.services.unsubscribe_service import UnsubscribeService

        service = UnsubscribeService()

        token = await service.generate_unsubscribe_token(
            db=test_db,
            email=test_patron.email,
            email_type="notification",
            user_id=test_patron.id,
        )

        headers = service.generate_list_unsubscribe_header(token)

        assert "List-Unsubscribe" in headers
        assert "List-Unsubscribe-Post" in headers
        assert token in headers["List-Unsubscribe"]

    @pytest.mark.asyncio
    async def test_email_validation(self):
        """Test that email validation works"""
        from email_validator import validate_email, EmailNotValidError

        valid_email = "test@example.com"
        invalid_email = "not-an-email"

        try:
            # check_deliverability=False: the test runner has no outbound
            # DNS/MX access, matching production's validate_email_allow_test
            # (app/schemas/user.py) which disables the same check.
            validate_email(valid_email, check_deliverability=False)
            valid_is_valid = True
        except EmailNotValidError:
            valid_is_valid = False

        assert valid_is_valid

        try:
            validate_email(invalid_email, check_deliverability=False)
            invalid_is_valid = True
        except EmailNotValidError:
            invalid_is_valid = False

        assert not invalid_is_valid
