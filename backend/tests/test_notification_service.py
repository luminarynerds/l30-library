# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the notification_service facade (app.services.notification_service).

REWRITTEN 2026-07 -- the module was consolidated by PR #611 ("Consolidate 7
notification services into unified template-driven system"). `NotificationService`
is now an alias for `UnifiedNotificationService`
(app/services/notifications/__init__.py), a facade over per-domain services.
There is no queue_checkout_receipt / queue_due_date_reminders /
queue_overdue_notices / queue_hold_ready_notification /
queue_hold_expiring_warnings / process_notification_queue on it any more --
those don't exist as service methods today. Real circulation notifications
are sent immediately (not queued) by the scheduler jobs in
app/services/schedulers/circulation_jobs.py and notification_jobs.py, which
render via CirculationNotificationService and gate delivery via
app/services/notifications/preference_gate.should_send_email.

This file now covers what the facade itself actually exposes:
- Template rendering delegation (render_*_email)
- Legacy preferences delegation (get_or_create_preferences/update_preferences)
- SMS delegation (send_hold_ready_sms)

The queue_notification/send_queued_notifications generic infra (still real,
used by non-circulation notification types) and notification history are
covered in tests/test_notification_verification.py -- not duplicated here.
The current preference-gate mechanism (UserNotificationPreference,
channel_preferences JSON) is covered here since nothing else exercises it.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.catalog import CatalogItem
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.notification import NotificationPreferences
from app.models.notification_preference import UserNotificationPreference


class TestNotificationRenderingDelegation:
    """The facade's render_*_email methods delegate to CirculationNotificationService."""

    @pytest.mark.asyncio
    async def test_render_checkout_receipt_email(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
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
            user=test_patron, item=test_catalog_item, checkout=checkout
        )

        assert test_catalog_item.title in subject
        assert test_patron.first_name in html

    @pytest.mark.asyncio
    async def test_render_due_date_reminder_email(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
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
            user=test_patron, item=test_catalog_item, checkout=checkout, days_until_due=2
        )

        assert "remind" in subject.lower()
        assert test_catalog_item.title in html

    @pytest.mark.asyncio
    async def test_render_overdue_notice_email(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
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
            user=test_patron, item=test_catalog_item, checkout=checkout, days_overdue=1
        )

        assert "overdue" in subject.lower()
        assert test_catalog_item.title in html

    @pytest.mark.asyncio
    async def test_render_hold_ready_email(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
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
            user=test_patron, item=test_catalog_item, hold=hold
        )

        assert "ready" in subject.lower()
        assert test_catalog_item.title in html

    @pytest.mark.asyncio
    async def test_render_hold_expiring_email(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
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
            user=test_patron, item=test_catalog_item, hold=hold, days_until_expiry=2
        )

        assert "expir" in subject.lower()
        assert test_catalog_item.title in html


class TestLegacyPreferencesDelegation:
    """get_or_create_preferences/update_preferences delegate to PreferencesManager
    (app/services/notifications/preferences.py), which still targets the
    legacy NotificationPreferences model (per-toggle booleans), not the newer
    UserNotificationPreference (channel_preferences JSON) used by
    preference_gate.should_send_email below. Both are live in production."""

    @pytest.mark.asyncio
    async def test_get_or_create_preferences_creates_defaults(
        self, test_db: AsyncSession, test_patron: User
    ):
        from app.services.notification_service import NotificationService

        prefs = await NotificationService.get_or_create_preferences(test_patron.id, test_db)

        assert prefs is not None
        assert prefs.user_id == test_patron.id
        assert prefs.email_checkout_receipt is True  # model default

    @pytest.mark.asyncio
    async def test_get_or_create_preferences_returns_existing(
        self, test_db: AsyncSession, test_patron: User
    ):
        from app.services.notification_service import NotificationService

        existing = NotificationPreferences(
            user_id=test_patron.id, email_overdue_notice=False
        )
        test_db.add(existing)
        await test_db.commit()

        prefs = await NotificationService.get_or_create_preferences(test_patron.id, test_db)

        assert prefs.id == existing.id
        assert prefs.email_overdue_notice is False

    @pytest.mark.asyncio
    async def test_update_preferences(self, test_db: AsyncSession, test_patron: User):
        from app.services.notification_service import NotificationService

        updated = await NotificationService.update_preferences(
            test_patron.id,
            {"email_hold_ready": False, "email_checkout_receipt": False},
            test_db,
        )

        assert updated.email_hold_ready is False
        assert updated.email_checkout_receipt is False


class TestHoldReadySMSDelegation:
    """CirculationNotificationService.send_hold_ready_sms, reached via the facade."""

    @pytest.mark.asyncio
    async def test_no_sms_when_sms_disabled_globally(
        self, test_db: AsyncSession, test_patron: User
    ):
        from app.services.notification_service import NotificationService
        from app.services.notifications import circulation as circulation_module

        service = NotificationService()
        assert circulation_module.settings.sms_enabled is False  # default

        sent = await service.send_hold_ready_sms(
            test_patron.id, "Test Book", "July 10", test_db
        )

        assert sent is False

    @pytest.mark.asyncio
    async def test_sms_queued_when_enabled_and_opted_in(
        self, test_db: AsyncSession, test_patron: User, monkeypatch
    ):
        from app.services.notification_service import NotificationService
        from app.services.notifications import circulation as circulation_module

        monkeypatch.setattr(circulation_module.settings, "sms_enabled", True)

        prefs = NotificationPreferences(
            user_id=test_patron.id,
            sms_notifications_enabled=True,
            sms_phone_number="+15555550123",
            sms_phone_verified=True,
            sms_hold_ready=True,
        )
        test_db.add(prefs)
        await test_db.commit()

        service = NotificationService()
        with patch(
            "app.services.sms_service.sms_service.queue_sms", new_callable=AsyncMock
        ) as mock_queue:
            sent = await service.send_hold_ready_sms(
                test_patron.id, "Test Book", "July 10", test_db
            )

        assert sent is True
        assert mock_queue.call_count == 1

    @pytest.mark.asyncio
    async def test_no_sms_when_not_opted_in(
        self, test_db: AsyncSession, test_patron: User, monkeypatch
    ):
        from app.services.notification_service import NotificationService
        from app.services.notifications import circulation as circulation_module

        monkeypatch.setattr(circulation_module.settings, "sms_enabled", True)

        # No NotificationPreferences row at all -- defaults to opted out (sms
        # disabled by default, per app/models/notification.py).
        service = NotificationService()
        with patch(
            "app.services.sms_service.sms_service.queue_sms", new_callable=AsyncMock
        ) as mock_queue:
            sent = await service.send_hold_ready_sms(
                test_patron.id, "Test Book", "July 10", test_db
            )

        assert sent is False
        assert mock_queue.call_count == 0


class TestPreferenceGate:
    """app.services.notifications.preference_gate.should_send_email -- the
    real gate the circulation scheduler jobs call before sending patron
    email (see app/services/schedulers/circulation_jobs.py:439)."""

    @pytest.mark.asyncio
    async def test_required_type_always_sends_even_when_disabled(
        self, test_db: AsyncSession, test_patron: User
    ):
        from app.services.notifications.preference_gate import should_send_email

        prefs = UserNotificationPreference(
            user_id=test_patron.id,
            channel_preferences={"hold_ready": {"email": False}},
        )
        test_db.add(prefs)
        await test_db.commit()

        # hold_ready is in REQUIRED_NOTIFICATION_TYPES -- always sends
        assert await should_send_email(test_patron.id, "hold_ready", test_db) is True

    @pytest.mark.asyncio
    async def test_no_preferences_row_defaults_to_send(
        self, test_db: AsyncSession, test_patron: User
    ):
        from app.services.notifications.preference_gate import should_send_email

        assert (
            await should_send_email(test_patron.id, "event_reminder", test_db) is True
        )

    @pytest.mark.asyncio
    async def test_channel_toggle_off_blocks_email(
        self, test_db: AsyncSession, test_patron: User
    ):
        from app.services.notifications.preference_gate import should_send_email

        prefs = UserNotificationPreference(
            user_id=test_patron.id,
            channel_preferences={"event_reminder": {"email": False}},
        )
        test_db.add(prefs)
        await test_db.commit()

        assert (
            await should_send_email(test_patron.id, "event_reminder", test_db) is False
        )

    @pytest.mark.asyncio
    async def test_digest_mode_suppresses_and_enqueues(
        self, test_db: AsyncSession, test_patron: User
    ):
        from sqlalchemy import select
        from app.models.notification import NotificationDigestQueue
        from app.services.notifications.preference_gate import should_send_email

        prefs = UserNotificationPreference(
            user_id=test_patron.id, digest_enabled=True
        )
        test_db.add(prefs)
        await test_db.commit()

        result = await should_send_email(
            test_patron.id,
            "event_reminder",
            test_db,
            summary="Your event is tomorrow",
            dedup_key="event:123",
        )

        assert result is False

        digest_result = await test_db.execute(
            select(NotificationDigestQueue).where(
                NotificationDigestQueue.user_id == test_patron.id
            )
        )
        digest_item = digest_result.scalar_one_or_none()
        assert digest_item is not None
        assert digest_item.summary == "Your event is tomorrow"

    @pytest.mark.asyncio
    async def test_quiet_hours_blocks_email(
        self, test_db: AsyncSession, test_patron: User
    ):
        from app.services.notifications.preference_gate import should_send_email

        prefs = UserNotificationPreference(
            user_id=test_patron.id,
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="23:59",
            quiet_hours_days=[0, 1, 2, 3, 4, 5, 6],
        )
        test_db.add(prefs)
        await test_db.commit()

        now = datetime.now(timezone.utc)
        assert (
            await should_send_email(
                test_patron.id, "event_reminder", test_db, now=now
            )
            is False
        )
