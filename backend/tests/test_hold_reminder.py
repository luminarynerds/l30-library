# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Hold Expiration Reminder Background Job

This test suite covers the scheduler job that:
- Finds ready holds expiring within 2 days
- Sends reminder email notifications to patrons
- Uses reminder_sent_at field to prevent duplicate reminders
- Skips pending holds (only ready holds get reminders)

Tests cover:
- Reminder sent 2 days before expiry
- No duplicate reminders (reminder_sent_at tracking)
- No reminder for pending holds
- No reminder for already expired holds
- No reminder for holds expiring more than 2 days out
- Error handling for missing user/item
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Hold, HoldStatus


class TestHoldExpirationReminderBasics:
    """Test basic reminder functionality"""

    @pytest.mark.asyncio
    async def test_reminder_sent_for_hold_expiring_in_2_days(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that reminder is sent for hold expiring within 2 days"""
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        # Create ready hold expiring in 1.5 days
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            notified_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=1, hours=12),
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        hold_id = hold.id

        # Run reminder job
        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()

        # Verify reminder was sent
        mock_email.assert_called_once()
        call_args = mock_email.call_args
        assert test_patron.email in call_args[0]
        # Actual i18n subject (see email.hold_expiring.subject in
        # app/translations/en.json) is "Hold Expiring Soon: {item_title}".
        assert "Hold Expiring Soon" in call_args[0][1]

        # Verify reminder_sent_at was set. send_hold_expiration_reminders()
        # mutates this row via its own AsyncSessionLocal() session; test_db
        # is expire_on_commit=False (tests/conftest.py) so `hold` is still
        # cached with its pre-job value -- expire_all() forces a real reload.
        test_db.expire_all()
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        updated_hold = result.scalar_one()
        assert updated_hold.reminder_sent_at is not None

    @pytest.mark.asyncio
    async def test_reminder_sent_for_hold_expiring_tomorrow(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that reminder is sent for hold expiring tomorrow"""
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        # Create ready hold expiring tomorrow
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            notified_at=now - timedelta(days=6),
            expires_at=now + timedelta(hours=20),
        )
        test_db.add(hold)
        await test_db.commit()

        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()

        # Verify reminder was sent
        mock_email.assert_called_once()


class TestNoDuplicateReminders:
    """Test that duplicate reminders are prevented"""

    @pytest.mark.asyncio
    async def test_no_duplicate_reminder_when_already_sent(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that holds with reminder_sent_at don't receive another reminder"""
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        # Create ready hold with reminder already sent
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            notified_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=1),
            reminder_sent_at=now - timedelta(hours=12),  # Already reminded
        )
        test_db.add(hold)
        await test_db.commit()

        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()

        # No email should be sent
        mock_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_running_job_twice_no_duplicate_reminder(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that running job twice doesn't send duplicate reminders"""
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            notified_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=1, hours=12),
        )
        test_db.add(hold)
        await test_db.commit()

        # Run job first time
        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()
            first_call_count = mock_email.call_count

        # Run job again
        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()
            second_call_count = mock_email.call_count

        # First run should send 1 email, second run should send 0
        assert first_call_count == 1
        assert second_call_count == 0


class TestPendingHoldsNoReminder:
    """Test that pending holds don't receive expiration reminders"""

    @pytest.mark.asyncio
    async def test_no_reminder_for_pending_holds(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that pending status holds don't receive expiration reminders"""
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        # Create pending hold (not ready for pickup yet)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,  # Not ready yet
            created_at=now - timedelta(days=10),
            expires_at=now + timedelta(days=1),  # Would expire soon if it were ready
        )
        test_db.add(hold)
        await test_db.commit()

        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()

        # No reminder should be sent for pending holds
        mock_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_reminder_for_expired_holds(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that already expired holds don't receive reminders"""
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        # Create hold with expired status
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.expired,
            notified_at=now - timedelta(days=10),
            expires_at=now - timedelta(days=3),  # Already expired
        )
        test_db.add(hold)
        await test_db.commit()

        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()

        mock_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_reminder_for_fulfilled_holds(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that fulfilled holds don't receive reminders"""
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.fulfilled,
            notified_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=1),
        )
        test_db.add(hold)
        await test_db.commit()

        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()

        mock_email.assert_not_called()


class TestReminderTiming:
    """Test reminder timing constraints"""

    @pytest.mark.asyncio
    async def test_no_reminder_for_hold_expiring_more_than_2_days(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that holds expiring more than 2 days out don't get reminders"""
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        # Create hold expiring in 5 days
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            notified_at=now - timedelta(days=2),
            expires_at=now + timedelta(days=5),  # Too far out
        )
        test_db.add(hold)
        await test_db.commit()

        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()

        mock_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_reminder_for_already_past_expiry(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that holds past their expiry date don't receive reminders"""
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        # Create ready hold that's already past expiry (but status not updated yet)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            notified_at=now - timedelta(days=10),
            expires_at=now - timedelta(hours=2),  # Already expired
        )
        test_db.add(hold)
        await test_db.commit()

        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()

        mock_email.assert_not_called()


class TestEdgeCasesAndErrors:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_handle_missing_user_gracefully(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Test that job doesn't crash if user was deleted"""
        from sqlalchemy import text
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        # Create hold with non-existent user. holds.user_id is NOT NULL with
        # ON DELETE RESTRICT (app/models/circulation.py), so a real orphan
        # row can't be produced through a normal insert -- FK checks are
        # disabled for this one INSERT to simulate legacy/corrupted data.
        hold = Hold(
            user_id=99999,  # User doesn't exist
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            notified_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=1),
        )
        test_db.add(hold)
        await test_db.execute(text("SET session_replication_role = replica"))
        await test_db.commit()
        await test_db.execute(text("SET session_replication_role = DEFAULT"))
        await test_db.commit()

        # Should not raise exception
        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()

        # No email should be sent for non-existent user
        mock_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_missing_item_gracefully(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that job doesn't crash if item was deleted"""
        from sqlalchemy import text
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        # holds.item_id is NOT NULL with ON DELETE RESTRICT -- FK check
        # disabled for this one INSERT (see comment in
        # test_handle_missing_user_gracefully above).
        hold = Hold(
            user_id=test_patron.id,
            item_id=99999,  # Item doesn't exist
            status=HoldStatus.ready,
            notified_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=1),
        )
        test_db.add(hold)
        await test_db.execute(text("SET session_replication_role = replica"))
        await test_db.commit()
        await test_db.execute(text("SET session_replication_role = DEFAULT"))
        await test_db.commit()

        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()

        mock_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_email_failure_gracefully(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that email failure doesn't crash job or set reminder_sent_at"""
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            notified_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=1),
        )
        test_db.add(hold)
        await test_db.commit()
        hold_id = hold.id

        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = False  # Email failed
            await send_hold_expiration_reminders()

        # reminder_sent_at should NOT be set when email fails
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        updated_hold = result.scalar_one()
        assert updated_hold.reminder_sent_at is None

    @pytest.mark.asyncio
    async def test_multiple_holds_different_users(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem
    ):
        """Test that job handles multiple holds for different users"""
        from app.services.schedulers import send_hold_expiration_reminders
        from app.core.security import hash_password

        now = datetime.now(timezone.utc)

        # Create two users
        user1 = User(
            email="user1@test.com",
            password_hash=hash_password("TestPass123!"),
            first_name="User",
            last_name="One",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        user2 = User(
            email="user2@test.com",
            password_hash=hash_password("TestPass123!"),
            first_name="User",
            last_name="Two",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add_all([user1, user2])
        await test_db.commit()
        await test_db.refresh(user1)
        await test_db.refresh(user2)

        # Create holds for both users
        hold1 = Hold(
            user_id=user1.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            notified_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=1),
        )
        hold2 = Hold(
            user_id=user2.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            notified_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=1, hours=12),
        )
        test_db.add_all([hold1, hold2])
        await test_db.commit()

        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()

        # Both users should receive reminders
        assert mock_email.call_count == 2


class TestEmailContent:
    """Test email content and formatting"""

    @pytest.mark.asyncio
    async def test_email_contains_item_details(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that reminder email contains item title and author"""
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            notified_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=1),
        )
        test_db.add(hold)
        await test_db.commit()

        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()

        # Check email content
        call_args = mock_email.call_args
        html_content = call_args[0][2]
        assert test_catalog_item.title in html_content
        assert test_catalog_item.author in html_content

    @pytest.mark.asyncio
    async def test_email_contains_expiration_date(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that reminder email contains the expiration date"""
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=1)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            notified_at=now - timedelta(days=5),
            expires_at=expires_at,
        )
        test_db.add(hold)
        await test_db.commit()

        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()

        # Check email contains expiration date
        call_args = mock_email.call_args
        html_content = call_args[0][2]
        expected_date = expires_at.strftime("%B %d, %Y")
        assert expected_date in html_content

    @pytest.mark.asyncio
    async def test_email_contains_account_link(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that reminder email contains link to account holds page"""
        from app.services.schedulers import send_hold_expiration_reminders

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            notified_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=1),
        )
        test_db.add(hold)
        await test_db.commit()

        with patch('app.services.schedulers.notification_jobs.send_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            await send_hold_expiration_reminders()

        # Check email contains link to holds page. render_hold_expiring_email
        # (app/services/notifications/templates.py) links routes.account_holds
        # ("/my-account/holds"), not the legacy routes.account_holds_alt
        # ("/account/holds") used by the separate hold-expired notification.
        call_args = mock_email.call_args
        html_content = call_args[0][2]
        assert "/my-account/holds" in html_content
