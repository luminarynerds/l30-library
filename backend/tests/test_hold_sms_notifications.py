# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for SMS notifications for hold ready and hold expired notifications.

This test suite covers:
- SMS notifications sent when holds become ready
- SMS notifications sent when holds expire
- User SMS preference checking
- SMS queuing behavior
- Graceful handling of SMS failures (not affecting email)
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus
from app.models.notification import NotificationPreferences
from app.models.sms import SMSNotificationType


def create_mock_user(user_id=1):
    """Create a mock user for testing"""
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = f"test{user_id}@example.com"
    user.first_name = "Test"
    user.last_name = "User"
    return user


def create_mock_item(item_id=1):
    """Create a mock catalog item for testing"""
    item = MagicMock(spec=CatalogItem)
    item.id = item_id
    item.title = "Test Book"
    item.author = "Test Author"
    return item


def create_mock_prefs(
    sms_enabled=True,
    hold_ready=True,
    hold_expired=True,
    phone="+15551234567",
    verified=True
):
    """Create mock notification preferences"""
    prefs = MagicMock(spec=NotificationPreferences)
    prefs.sms_notifications_enabled = sms_enabled
    prefs.sms_hold_ready = hold_ready
    prefs.sms_hold_expired = hold_expired
    prefs.sms_phone_number = phone
    prefs.sms_phone_verified = verified
    return prefs


def create_mock_template():
    """Create a mock SMS template"""
    template = MagicMock()
    template.template_body = "{library_name}: Your hold '{title}' is ready!"
    return template


class TestHoldReadySMSNotification:
    """Test SMS notifications for hold ready events"""

    @pytest.mark.asyncio
    async def test_send_sms_when_hold_ready_and_user_has_sms_enabled(self):
        """Test that SMS is queued when hold becomes ready and user has SMS enabled"""
        from app.services.schedulers.circulation_jobs import _send_hold_ready_notification

        user = create_mock_user()
        item = create_mock_item()
        prefs = create_mock_prefs()
        mock_db = MagicMock(spec=AsyncSession)

        with patch('app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True

            with patch('app.services.sms_service.SMSService.get_sms_preferences', new_callable=AsyncMock) as mock_get_prefs:
                mock_get_prefs.return_value = prefs

                with patch('app.services.sms_service.SMSService.get_or_create_template', new_callable=AsyncMock) as mock_template:
                    mock_template.return_value = create_mock_template()

                    with patch('app.services.sms_service.SMSService.queue_sms', new_callable=AsyncMock) as mock_queue_sms:
                        mock_queue_sms.return_value = MagicMock(id=1)

                        result = await _send_hold_ready_notification(user, item, mock_db)

                        assert result is True
                        assert mock_email.called
                        assert mock_queue_sms.called
                        call_kwargs = mock_queue_sms.call_args.kwargs
                        assert call_kwargs['user_id'] == user.id
                        assert call_kwargs['phone_number'] == "+15551234567"
                        assert call_kwargs['notification_type'] == SMSNotificationType.HOLD_READY

    @pytest.mark.asyncio
    async def test_no_sms_when_user_has_sms_disabled(self):
        """Test that no SMS is queued when user has SMS notifications disabled"""
        from app.services.schedulers.circulation_jobs import _send_hold_ready_notification

        user = create_mock_user()
        item = create_mock_item()
        prefs = create_mock_prefs(sms_enabled=False)
        mock_db = MagicMock(spec=AsyncSession)

        with patch('app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True

            with patch('app.services.sms_service.SMSService.get_sms_preferences', new_callable=AsyncMock) as mock_get_prefs:
                mock_get_prefs.return_value = prefs

                with patch('app.services.sms_service.SMSService.queue_sms', new_callable=AsyncMock) as mock_queue_sms:
                    result = await _send_hold_ready_notification(user, item, mock_db)

                    assert result is True
                    assert mock_email.called
                    assert not mock_queue_sms.called

    @pytest.mark.asyncio
    async def test_no_sms_when_hold_ready_preference_disabled(self):
        """Test that no SMS is queued when user has sms_hold_ready disabled"""
        from app.services.schedulers.circulation_jobs import _send_hold_ready_notification

        user = create_mock_user()
        item = create_mock_item()
        prefs = create_mock_prefs(hold_ready=False)
        mock_db = MagicMock(spec=AsyncSession)

        with patch('app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True

            with patch('app.services.sms_service.SMSService.get_sms_preferences', new_callable=AsyncMock) as mock_get_prefs:
                mock_get_prefs.return_value = prefs

                with patch('app.services.sms_service.SMSService.queue_sms', new_callable=AsyncMock) as mock_queue_sms:
                    result = await _send_hold_ready_notification(user, item, mock_db)

                    assert result is True
                    assert not mock_queue_sms.called

    @pytest.mark.asyncio
    async def test_no_sms_when_phone_not_verified(self):
        """Test that no SMS is queued when phone number is not verified"""
        from app.services.schedulers.circulation_jobs import _send_hold_ready_notification

        user = create_mock_user()
        item = create_mock_item()
        prefs = create_mock_prefs(verified=False)
        mock_db = MagicMock(spec=AsyncSession)

        with patch('app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True

            with patch('app.services.sms_service.SMSService.get_sms_preferences', new_callable=AsyncMock) as mock_get_prefs:
                mock_get_prefs.return_value = prefs

                with patch('app.services.sms_service.SMSService.queue_sms', new_callable=AsyncMock) as mock_queue_sms:
                    result = await _send_hold_ready_notification(user, item, mock_db)

                    assert result is True
                    assert not mock_queue_sms.called

    @pytest.mark.asyncio
    async def test_no_sms_when_no_phone_number(self):
        """Test that no SMS is queued when user has no phone number"""
        from app.services.schedulers.circulation_jobs import _send_hold_ready_notification

        user = create_mock_user()
        item = create_mock_item()
        prefs = create_mock_prefs(phone=None)
        mock_db = MagicMock(spec=AsyncSession)

        with patch('app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True

            with patch('app.services.sms_service.SMSService.get_sms_preferences', new_callable=AsyncMock) as mock_get_prefs:
                mock_get_prefs.return_value = prefs

                with patch('app.services.sms_service.SMSService.queue_sms', new_callable=AsyncMock) as mock_queue_sms:
                    result = await _send_hold_ready_notification(user, item, mock_db)

                    assert result is True
                    assert not mock_queue_sms.called

    @pytest.mark.asyncio
    async def test_no_sms_when_no_preferences(self):
        """Test that no SMS is queued when user has no notification preferences"""
        from app.services.schedulers.circulation_jobs import _send_hold_ready_notification

        user = create_mock_user()
        item = create_mock_item()
        mock_db = MagicMock(spec=AsyncSession)

        with patch('app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True

            with patch('app.services.sms_service.SMSService.get_sms_preferences', new_callable=AsyncMock) as mock_get_prefs:
                mock_get_prefs.return_value = None  # No preferences

                with patch('app.services.sms_service.SMSService.queue_sms', new_callable=AsyncMock) as mock_queue_sms:
                    result = await _send_hold_ready_notification(user, item, mock_db)

                    assert result is True
                    assert not mock_queue_sms.called

    @pytest.mark.asyncio
    async def test_sms_failure_does_not_affect_email_success(self):
        """Test that SMS failure does not affect email notification success"""
        from app.services.schedulers.circulation_jobs import _send_hold_ready_notification

        user = create_mock_user()
        item = create_mock_item()
        prefs = create_mock_prefs()
        mock_db = MagicMock(spec=AsyncSession)

        with patch('app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True

            with patch('app.services.sms_service.SMSService.get_sms_preferences', new_callable=AsyncMock) as mock_get_prefs:
                mock_get_prefs.return_value = prefs

                with patch('app.services.sms_service.SMSService.get_or_create_template', new_callable=AsyncMock) as mock_template:
                    mock_template.return_value = create_mock_template()

                    with patch('app.services.sms_service.SMSService.queue_sms', new_callable=AsyncMock) as mock_queue_sms:
                        mock_queue_sms.side_effect = Exception("SMS service unavailable")

                        result = await _send_hold_ready_notification(user, item, mock_db)

                        # Email should still succeed
                        assert result is True
                        assert mock_email.called

    @pytest.mark.asyncio
    async def test_no_sms_when_no_db_session(self):
        """Test that no SMS is attempted when db session is not provided"""
        from app.services.schedulers.circulation_jobs import _send_hold_ready_notification

        user = create_mock_user()
        item = create_mock_item()

        with patch('app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True

            with patch('app.services.sms_service.SMSService.queue_sms', new_callable=AsyncMock) as mock_queue_sms:
                result = await _send_hold_ready_notification(user, item, db=None)

                assert result is True
                assert mock_email.called
                assert not mock_queue_sms.called


class TestHoldExpiredSMSNotification:
    """Test SMS notifications for hold expired events"""

    @pytest.mark.asyncio
    async def test_send_sms_when_hold_expires_and_user_has_sms_enabled(self):
        """Test that SMS is queued when hold expires and user has SMS enabled"""
        from app.services.schedulers.circulation_jobs import _send_hold_expired_notification

        user = create_mock_user()
        item = create_mock_item()
        prefs = create_mock_prefs()
        mock_db = MagicMock(spec=AsyncSession)

        with patch('app.services.schedulers.circulation_jobs.should_send_email', new_callable=AsyncMock) as mock_gate:
            mock_gate.return_value = True

            with patch('app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock) as mock_email:
                mock_email.return_value = True

                with patch('app.services.sms_service.SMSService.get_sms_preferences', new_callable=AsyncMock) as mock_get_prefs:
                    mock_get_prefs.return_value = prefs

                    with patch('app.services.sms_service.SMSService.get_or_create_template', new_callable=AsyncMock) as mock_template:
                        template = MagicMock()
                        template.template_body = "{library_name}: Your hold for '{title}' has expired."
                        mock_template.return_value = template

                        with patch('app.services.sms_service.SMSService.queue_sms', new_callable=AsyncMock) as mock_queue_sms:
                            mock_queue_sms.return_value = MagicMock(id=1)

                            result = await _send_hold_expired_notification(user, item, mock_db)

                            assert result is True
                            assert mock_email.called
                            assert mock_queue_sms.called
                            call_kwargs = mock_queue_sms.call_args.kwargs
                            assert call_kwargs['user_id'] == user.id
                            assert call_kwargs['phone_number'] == "+15551234567"
                            assert call_kwargs['notification_type'] == SMSNotificationType.HOLD_EXPIRED

    @pytest.mark.asyncio
    async def test_no_sms_when_hold_expired_preference_disabled(self):
        """Test that no SMS is queued when user has sms_hold_expired disabled"""
        from app.services.schedulers.circulation_jobs import _send_hold_expired_notification

        user = create_mock_user()
        item = create_mock_item()
        prefs = create_mock_prefs(hold_expired=False)
        mock_db = MagicMock(spec=AsyncSession)

        # This test is about SMS gating (sms_hold_expired), not email
        # preference gating -- mock the email-side gate directly so a
        # MagicMock(spec=AsyncSession) with no configured query result
        # doesn't make should_send_email's real DB round-trip blow up.
        # Mirrors test_expired_sms_failure_does_not_affect_email_success
        # below, which does the same for the same reason.
        with patch('app.services.schedulers.circulation_jobs.should_send_email', new_callable=AsyncMock) as mock_gate:
            mock_gate.return_value = True

            with patch('app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock) as mock_email:
                mock_email.return_value = True

                with patch('app.services.sms_service.SMSService.get_sms_preferences', new_callable=AsyncMock) as mock_get_prefs:
                    mock_get_prefs.return_value = prefs

                    with patch('app.services.sms_service.SMSService.queue_sms', new_callable=AsyncMock) as mock_queue_sms:
                        result = await _send_hold_expired_notification(user, item, mock_db)

                        assert result is True
                        assert not mock_queue_sms.called

    @pytest.mark.asyncio
    async def test_expired_sms_failure_does_not_affect_email_success(self):
        """Test that SMS failure does not affect email notification success for expired holds"""
        from app.services.schedulers.circulation_jobs import _send_hold_expired_notification

        user = create_mock_user()
        item = create_mock_item()
        prefs = create_mock_prefs()
        mock_db = MagicMock(spec=AsyncSession)

        with patch('app.services.schedulers.circulation_jobs.should_send_email', new_callable=AsyncMock) as mock_gate:
            mock_gate.return_value = True

            with patch('app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock) as mock_email:
                mock_email.return_value = True

                with patch('app.services.sms_service.SMSService.get_sms_preferences', new_callable=AsyncMock) as mock_get_prefs:
                    mock_get_prefs.return_value = prefs

                    with patch('app.services.sms_service.SMSService.get_or_create_template', new_callable=AsyncMock) as mock_template:
                        mock_template.return_value = create_mock_template()

                        with patch('app.services.sms_service.SMSService.queue_sms', new_callable=AsyncMock) as mock_queue_sms:
                            mock_queue_sms.side_effect = Exception("SMS service unavailable")

                            result = await _send_hold_expired_notification(user, item, mock_db)

                            assert result is True
                            assert mock_email.called

    @pytest.mark.asyncio
    async def test_email_failure_does_not_prevent_sms(self):
        """Test that email failure does not prevent SMS from being queued"""
        from app.services.schedulers.circulation_jobs import _send_hold_expired_notification

        user = create_mock_user()
        item = create_mock_item()
        prefs = create_mock_prefs()
        mock_db = MagicMock(spec=AsyncSession)

        with patch('app.services.schedulers.circulation_jobs.should_send_email', new_callable=AsyncMock) as mock_gate:
            mock_gate.return_value = True

            with patch('app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock) as mock_email:
                mock_email.side_effect = Exception("Email service unavailable")

                with patch('app.services.sms_service.SMSService.get_sms_preferences', new_callable=AsyncMock) as mock_get_prefs:
                    mock_get_prefs.return_value = prefs

                    with patch('app.services.sms_service.SMSService.get_or_create_template', new_callable=AsyncMock) as mock_template:
                        template = MagicMock()
                        template.template_body = "{library_name}: Your hold for '{title}' has expired."
                        mock_template.return_value = template

                        with patch('app.services.sms_service.SMSService.queue_sms', new_callable=AsyncMock) as mock_queue_sms:
                            mock_queue_sms.return_value = MagicMock(id=1)

                            result = await _send_hold_expired_notification(user, item, mock_db)

                            # Email failed
                            assert result is False
                            # But SMS should still be queued
                            assert mock_queue_sms.called

    @pytest.mark.asyncio
    async def test_no_sms_when_no_db_session_for_expired(self):
        """Test that no SMS is attempted when db session is not provided for expired holds"""
        from app.services.schedulers.circulation_jobs import _send_hold_expired_notification

        user = create_mock_user()
        item = create_mock_item()

        with patch('app.services.schedulers.circulation_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True

            with patch('app.services.sms_service.SMSService.queue_sms', new_callable=AsyncMock) as mock_queue_sms:
                result = await _send_hold_expired_notification(user, item, db=None)

                assert result is True
                assert mock_email.called
                assert not mock_queue_sms.called


class TestSMSNotificationTypeEnum:
    """Test that HOLD_EXPIRED is properly defined in SMSNotificationType"""

    def test_hold_expired_in_enum(self):
        """Test that HOLD_EXPIRED is a valid SMSNotificationType"""
        assert hasattr(SMSNotificationType, 'HOLD_EXPIRED')
        assert SMSNotificationType.HOLD_EXPIRED.value == "hold_expired"

    def test_hold_ready_in_enum(self):
        """Test that HOLD_READY is a valid SMSNotificationType"""
        assert hasattr(SMSNotificationType, 'HOLD_READY')
        assert SMSNotificationType.HOLD_READY.value == "hold_ready"


class TestSMSTemplates:
    """Test SMS templates for hold notifications"""

    def test_hold_expired_template_exists(self):
        """Test that HOLD_EXPIRED template is defined in DEFAULT_TEMPLATES"""
        from app.services.sms_service import DEFAULT_TEMPLATES

        assert SMSNotificationType.HOLD_EXPIRED in DEFAULT_TEMPLATES
        template = DEFAULT_TEMPLATES[SMSNotificationType.HOLD_EXPIRED]
        assert "{title}" in template
        assert "expired" in template.lower()

    def test_hold_ready_template_exists(self):
        """Test that HOLD_READY template is defined in DEFAULT_TEMPLATES"""
        from app.services.sms_service import DEFAULT_TEMPLATES

        assert SMSNotificationType.HOLD_READY in DEFAULT_TEMPLATES
        template = DEFAULT_TEMPLATES[SMSNotificationType.HOLD_READY]
        assert "{title}" in template
        assert "ready" in template.lower()
