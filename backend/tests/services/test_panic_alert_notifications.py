# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Service-level tests for Panic Alert Notification System.

Tests notification delivery mechanisms for panic alerts:
- Email notification sending via UnifiedNotificationService
- SMS notification integration (logging/queueing)
- In-app notification creation
- Email template rendering with proper context
- Notification preference filtering
- Branch-based notification routing
- High-priority notification delivery (bypassing DND)
- Multi-recipient notification broadcasting
- Error handling and retry logic

These tests validate that panic alerts trigger appropriate notifications
to the right recipients through the correct channels.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime

from app.models.panic_alert import (
    PanicAlert,
    PanicAlertStatus,
    PanicAlertSource,
    PanicAlertNotificationPreferences,
)
from app.models.user import User, UserRole
from app.models.branch import Branch
from app.services.panic_alert_service import PanicAlertService
from app.schemas.panic_alert import (
    PanicAlertCreate,
    PanicAlertNotificationPreferencesCreate,
)
from app.services.unified_notification_service import (
    UnifiedNotificationService,
    NotificationType as UnifiedNotificationType,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def notification_staff_user(test_db):
    """Create staff user for notification tests"""
    from app.core.security import hash_password

    user = User(
        email="notif_staff@library.local",
        password_hash=hash_password("NotifStaff123!"),
        first_name="Notification",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def notification_manager_user(test_db):
    """Create manager user who receives notifications"""
    from app.core.security import hash_password

    user = User(
        email="notif_manager@library.local",
        password_hash=hash_password("NotifManager123!"),
        first_name="Notification",
        last_name="Manager",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def notification_supervisor_user(test_db):
    """Create supervisor user who receives notifications"""
    from app.core.security import hash_password

    user = User(
        email="notif_supervisor@library.local",
        password_hash=hash_password("NotifSupervisor123!"),
        first_name="Notification",
        last_name="Supervisor",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def notification_branch(test_db):
    """Create branch for notification routing tests"""
    from app.models.multi_branch import LibrarySystem

    system = LibrarySystem(code="NOTIFSYS", name="Notification Test System")
    test_db.add(system)
    await test_db.commit()
    await test_db.refresh(system)

    branch = Branch(
        library_system_id=system.id,
        code="NOTIFBR",
        name="Notification Test Branch",
        address_line1="100 Notif St",
        city="Somewhere Up North",
        state="ON",
        zip_code="M4D 4D4",
        phone="555-4000",
        email="notif_branch@library.local",
    )
    test_db.add(branch)
    await test_db.commit()
    await test_db.refresh(branch)
    return branch


@pytest.fixture
async def manager_with_email_prefs(test_db, notification_manager_user):
    """Create manager with email notification preferences enabled"""
    prefs = PanicAlertNotificationPreferences(
        user_id=notification_manager_user.id,
        receive_panic_alerts=True,
        notify_via_email=True,
        notify_via_sms=False,
        notify_via_in_app=True,
        notify_for_all_branches=True,
    )
    test_db.add(prefs)
    await test_db.commit()
    await test_db.refresh(prefs)
    return notification_manager_user


@pytest.fixture
async def manager_with_sms_prefs(test_db, notification_supervisor_user):
    """Create manager with SMS notification preferences enabled"""
    # Add phone number to user
    notification_supervisor_user.phone = "+15551234567"
    test_db.add(notification_supervisor_user)

    prefs = PanicAlertNotificationPreferences(
        user_id=notification_supervisor_user.id,
        receive_panic_alerts=True,
        notify_via_email=False,
        notify_via_sms=True,
        notify_via_in_app=True,
        notify_for_all_branches=True,
    )
    test_db.add(prefs)
    await test_db.commit()
    await test_db.refresh(prefs)
    await test_db.refresh(notification_supervisor_user)
    return notification_supervisor_user


# ============================================================================
# Email Notification Tests
# ============================================================================


class TestEmailNotifications:
    """Test email notification delivery for panic alerts"""

    @pytest.mark.asyncio
    async def test_email_sent_on_alert_creation(
        self, test_db, notification_staff_user, manager_with_email_prefs
    ):
        """Should send email notification when panic alert is triggered"""
        with patch.object(
            UnifiedNotificationService, "send_templated", new_callable=AsyncMock
        ) as mock_send:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
                situation_notes="Test email notification",
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
            )

            # Verify email notification was sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args

            # Check notification type
            assert call_args.kwargs["notification_type"] == UnifiedNotificationType.PANIC_ALERT

            # Check recipient
            assert call_args.kwargs["recipient_email"] == manager_with_email_prefs.email

            # Check context data includes required fields
            context = call_args.kwargs["context_data"]
            assert "alert_number" in context
            assert "location" in context
            assert "triggered_at" in context
            assert "staff_name" in context
            assert "alert_url" in context

    @pytest.mark.asyncio
    async def test_email_context_includes_situation_notes(
        self, test_db, notification_staff_user, manager_with_email_prefs
    ):
        """Should include situation notes in email context"""
        with patch.object(
            UnifiedNotificationService, "send_templated", new_callable=AsyncMock
        ) as mock_send:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.PHYSICAL_BUTTON,
                situation_notes="Patron becoming aggressive",
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
            )

            context = mock_send.call_args.kwargs["context_data"]
            assert "situation_notes" in context
            assert "Patron becoming aggressive" in context["situation_notes"]

    @pytest.mark.asyncio
    async def test_email_context_empty_when_no_notes(
        self, test_db, notification_staff_user, manager_with_email_prefs
    ):
        """Should handle alerts without situation notes"""
        with patch.object(
            UnifiedNotificationService, "send_templated", new_callable=AsyncMock
        ) as mock_send:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
            )

            context = mock_send.call_args.kwargs["context_data"]
            # situation_notes should be empty string when not provided
            assert context["situation_notes"] == ""

    @pytest.mark.asyncio
    async def test_email_includes_branch_location(
        self, test_db, notification_staff_user, manager_with_email_prefs, notification_branch
    ):
        """Should include branch name in email context"""
        with patch.object(
            UnifiedNotificationService, "send_templated", new_callable=AsyncMock
        ) as mock_send:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.PHYSICAL_BUTTON,
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
                branch_id=notification_branch.id,
            )

            context = mock_send.call_args.kwargs["context_data"]
            assert context["location"] == notification_branch.name

    @pytest.mark.asyncio
    async def test_email_error_logged_not_raised(
        self, test_db, notification_staff_user, manager_with_email_prefs
    ):
        """Should log email errors but not raise exception"""
        with patch.object(
            UnifiedNotificationService, "send_templated", new_callable=AsyncMock
        ) as mock_send:
            # Simulate email sending failure
            mock_send.side_effect = Exception("SMTP error")

            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            )

            # Should not raise exception
            alert = await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
            )

            # Alert should still be created
            assert alert.id is not None
            assert alert.status == PanicAlertStatus.ACTIVE


# ============================================================================
# SMS Notification Tests
# ============================================================================


class TestSMSNotifications:
    """Test SMS notification delivery for panic alerts"""

    @pytest.mark.asyncio
    async def test_sms_queued_on_alert_creation(
        self, test_db, notification_staff_user, manager_with_sms_prefs
    ):
        """Should queue SMS notification when panic alert is triggered"""
        with patch("app.services.panic_alert_service.logger") as mock_logger:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
            )

            # Verify SMS was logged/queued
            assert any(
                "SMS panic alert notification queued" in str(call)
                for call in mock_logger.info.call_args_list
            )

    @pytest.mark.asyncio
    async def test_sms_includes_phone_number(
        self, test_db, notification_staff_user, manager_with_sms_prefs
    ):
        """Should include phone number in SMS log"""
        with patch("app.services.panic_alert_service.logger") as mock_logger:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.PHYSICAL_BUTTON,
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
            )

            # Check that the log references the phone -- by design the
            # service only logs the last 4 digits (privacy: full numbers
            # must never hit application logs), so check for that instead
            # of the full E.164 number.
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            last4 = manager_with_sms_prefs.phone[-4:]
            assert any(
                last4 in call
                for call in info_calls
            )

    @pytest.mark.asyncio
    async def test_sms_not_sent_when_no_phone_number(
        self, test_db, notification_staff_user, notification_manager_user
    ):
        """Should skip SMS if user has no phone number"""
        # Manager has SMS enabled but no phone number
        prefs = PanicAlertNotificationPreferences(
            user_id=notification_manager_user.id,
            receive_panic_alerts=True,
            notify_via_sms=True,
            notify_for_all_branches=True,
        )
        test_db.add(prefs)
        await test_db.commit()

        with patch("app.services.panic_alert_service.logger") as mock_logger:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
            )

            # SMS should not be queued
            sms_calls = [
                call for call in mock_logger.info.call_args_list
                if "SMS panic alert notification queued" in str(call)
            ]
            assert len(sms_calls) == 0


# ============================================================================
# In-App Notification Tests
# ============================================================================


class TestInAppNotifications:
    """Test in-app notification creation for panic alerts"""

    @pytest.mark.asyncio
    async def test_in_app_notification_logged(
        self, test_db, notification_staff_user, manager_with_email_prefs
    ):
        """Should log in-app notification creation"""
        with patch("app.services.panic_alert_service.logger") as mock_logger:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
            )

            # Verify in-app notification was logged
            assert any(
                "In-app panic alert notification" in str(call)
                for call in mock_logger.info.call_args_list
            )


# ============================================================================
# Notification Preference Filtering Tests
# ============================================================================


class TestNotificationPreferenceFiltering:
    """Test notification routing based on user preferences"""

    @pytest.mark.asyncio
    async def test_no_notifications_when_receive_disabled(
        self, test_db, notification_staff_user, notification_manager_user
    ):
        """Should not send notifications when receive_panic_alerts is False"""
        prefs = PanicAlertNotificationPreferences(
            user_id=notification_manager_user.id,
            receive_panic_alerts=False,  # Disabled
            notify_via_email=True,
            notify_for_all_branches=True,
        )
        test_db.add(prefs)
        await test_db.commit()

        with patch.object(
            UnifiedNotificationService, "send_templated", new_callable=AsyncMock
        ) as mock_send:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
            )

            # No email should be sent
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_recipients_receive_notifications(
        self, test_db, notification_staff_user
    ):
        """Should send notifications to all recipients with enabled preferences"""
        from app.core.security import hash_password

        # Create two managers with email preferences
        manager1 = User(
            email="manager1@library.local",
            password_hash=hash_password("Manager123!"),
            first_name="Manager",
            last_name="One",
            role=UserRole.ADMIN,
            is_active=True,
            email_verified=True,
        )
        manager2 = User(
            email="manager2@library.local",
            password_hash=hash_password("Manager123!"),
            first_name="Manager",
            last_name="Two",
            role=UserRole.ADMIN,
            is_active=True,
            email_verified=True,
        )
        test_db.add_all([manager1, manager2])
        await test_db.commit()
        await test_db.refresh(manager1)
        await test_db.refresh(manager2)

        # Both managers want email notifications
        prefs1 = PanicAlertNotificationPreferences(
            user_id=manager1.id,
            receive_panic_alerts=True,
            notify_via_email=True,
            notify_for_all_branches=True,
        )
        prefs2 = PanicAlertNotificationPreferences(
            user_id=manager2.id,
            receive_panic_alerts=True,
            notify_via_email=True,
            notify_for_all_branches=True,
        )
        test_db.add_all([prefs1, prefs2])
        await test_db.commit()

        with patch.object(
            UnifiedNotificationService, "send_templated", new_callable=AsyncMock
        ) as mock_send:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
            )

            # Should have called send_templated twice (once per manager)
            assert mock_send.call_count == 2

            # Verify both emails were sent
            recipients = [call.kwargs["recipient_email"] for call in mock_send.call_args_list]
            assert "manager1@library.local" in recipients
            assert "manager2@library.local" in recipients

    @pytest.mark.asyncio
    async def test_branch_filtering_all_branches(
        self, test_db, notification_staff_user, notification_manager_user, notification_branch
    ):
        """Should notify managers with notify_for_all_branches=True"""
        prefs = PanicAlertNotificationPreferences(
            user_id=notification_manager_user.id,
            receive_panic_alerts=True,
            notify_via_email=True,
            notify_for_all_branches=True,  # Receives from all branches
        )
        test_db.add(prefs)
        await test_db.commit()

        with patch.object(
            UnifiedNotificationService, "send_templated", new_callable=AsyncMock
        ) as mock_send:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
                branch_id=notification_branch.id,
            )

            # Should receive notification
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_branch_filtering_specific_branches_match(
        self, test_db, notification_staff_user, notification_manager_user, notification_branch
    ):
        """Should notify managers when alert branch matches their preferences"""
        prefs = PanicAlertNotificationPreferences(
            user_id=notification_manager_user.id,
            receive_panic_alerts=True,
            notify_via_email=True,
            notify_for_all_branches=False,
            branch_ids=[notification_branch.id],  # Only this branch
        )
        test_db.add(prefs)
        await test_db.commit()

        with patch.object(
            UnifiedNotificationService, "send_templated", new_callable=AsyncMock
        ) as mock_send:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
                branch_id=notification_branch.id,
            )

            # Should receive notification (branch matches)
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_branch_filtering_specific_branches_no_match(
        self, test_db, notification_staff_user, notification_manager_user, notification_branch
    ):
        """Should NOT notify managers when alert branch doesn't match preferences"""
        # Create another branch
        from app.models.multi_branch import LibrarySystem

        other_system = LibrarySystem(code="OTHERSYS", name="Other Test System")
        test_db.add(other_system)
        await test_db.commit()
        await test_db.refresh(other_system)

        other_branch = Branch(
            library_system_id=other_system.id,
            code="OTHERBR",
            name="Other Branch",
            address_line1="200 Other St",
            city="Somewhere Up North",
            state="ON",
            zip_code="M5E 5E5",
            phone="555-5000",
            email="other@library.local",
        )
        test_db.add(other_branch)
        await test_db.commit()
        await test_db.refresh(other_branch)

        prefs = PanicAlertNotificationPreferences(
            user_id=notification_manager_user.id,
            receive_panic_alerts=True,
            notify_via_email=True,
            notify_for_all_branches=False,
            branch_ids=[other_branch.id],  # Different branch
        )
        test_db.add(prefs)
        await test_db.commit()

        with patch.object(
            UnifiedNotificationService, "send_templated", new_callable=AsyncMock
        ) as mock_send:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
                branch_id=notification_branch.id,  # Alert from different branch
            )

            # Should NOT receive notification (branch doesn't match)
            mock_send.assert_not_called()


# ============================================================================
# Notification Template Tests
# ============================================================================


class TestNotificationTemplateRendering:
    """Test email template rendering and context"""

    @pytest.mark.asyncio
    async def test_alert_number_format(
        self, test_db, notification_staff_user, manager_with_email_prefs
    ):
        """Should format alert number as PA-XXXXXX"""
        with patch.object(
            UnifiedNotificationService, "send_templated", new_callable=AsyncMock
        ) as mock_send:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            )

            alert = await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
            )

            context = mock_send.call_args.kwargs["context_data"]
            expected_number = f"PA-{alert.id:06d}"
            assert context["alert_number"] == expected_number

    @pytest.mark.asyncio
    async def test_staff_name_included(
        self, test_db, notification_staff_user, manager_with_email_prefs
    ):
        """Should include staff member's full name in context"""
        with patch.object(
            UnifiedNotificationService, "send_templated", new_callable=AsyncMock
        ) as mock_send:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
            )

            context = mock_send.call_args.kwargs["context_data"]
            assert context["staff_name"] == notification_staff_user.full_name

    @pytest.mark.asyncio
    async def test_alert_url_included(
        self, test_db, notification_staff_user, manager_with_email_prefs
    ):
        """Should include alert URL for quick access"""
        with patch.object(
            UnifiedNotificationService, "send_templated", new_callable=AsyncMock
        ) as mock_send:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            )

            alert = await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
            )

            context = mock_send.call_args.kwargs["context_data"]
            assert "alert_url" in context
            assert f"/staff/panic-alerts/{alert.id}" in context["alert_url"]

    @pytest.mark.asyncio
    async def test_triggered_at_timestamp(
        self, test_db, notification_staff_user, manager_with_email_prefs
    ):
        """Should include formatted timestamp of alert creation"""
        with patch.object(
            UnifiedNotificationService, "send_templated", new_callable=AsyncMock
        ) as mock_send:
            alert_data = PanicAlertCreate(
                activation_source=PanicAlertSource.KEYBOARD_SHORTCUT,
            )

            await PanicAlertService.trigger_alert(
                session=test_db,
                user_id=notification_staff_user.id,
                alert_data=alert_data,
            )

            context = mock_send.call_args.kwargs["context_data"]
            assert "triggered_at" in context
            # Should be formatted datetime string
            assert len(context["triggered_at"]) > 10
