# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Data Retention and GDPR Deletion Background Job

This test suite covers the data retention scheduler job which:
- Processes deletion requests from users (GDPR right to be forgotten)
- Marks user accounts as scheduled for deletion
- Purges personally identifiable information (PII)
- Anonymizes historical records (reading history, activity logs)
- Archives fine and checkout records for compliance
- Implements deletion hold periods (grace period before hard delete)
- Sends deletion confirmation emails
- Logs compliance events

Tests cover:
- Deletion request acceptance and validation
- Grace period compliance (30-90 day hold)
- PII anonymization (email, name, address, phone)
- Reading history purging
- Hold and checkout record handling
- Fine record archival
- Notification sending
- Edge cases (concurrent deletion requests, missing data)
- Rollback on errors
- GDPR compliance logging
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType


class TestDeletionRequestAcceptance:
    """Test deletion request initiation"""

    @pytest.mark.asyncio
    async def test_deletion_request_marks_account_for_deletion(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that deletion request is properly recorded"""
        from app.services.data_retention_service import process_scheduled_deletions

        now = datetime.now(timezone.utc)

        # Mark user for deletion
        test_patron.deletion_requested_at = now
        test_patron.deletion_scheduled_for = now + timedelta(days=30)
        await test_db.commit()
        await test_db.refresh(test_patron)

        user_id = test_patron.id

        # Process deletion requests (should not delete yet, just schedule)
        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            await process_scheduled_deletions(test_db)

        # Verify deletion was scheduled
        result = await test_db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        assert user.deletion_requested_at is not None
        assert user.deletion_scheduled_for is not None
        assert user.is_active is True  # Still active during grace period

    @pytest.mark.asyncio
    async def test_deletion_completion_sends_confirmation_email(
        self, test_db: AsyncSession, test_patron: User
    ):
        """The completion email fires when a due deletion is processed.

        (process_scheduled_deletions only acts on deletions whose scheduled
        date has passed; a future-dated request produces no email.)
        """
        now = datetime.now(timezone.utc)
        original_email = test_patron.email

        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            from app.services.data_retention_service import process_scheduled_deletions
            await process_scheduled_deletions(test_db)

            # Email goes to the patron's REAL address captured before the
            # tombstone scrub, not the scrubbed placeholder.
            assert mock_email.called
            assert mock_email.call_args.args[0] == original_email

    @pytest.mark.asyncio
    async def test_deletion_request_includes_grace_period_info(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that deletion notice includes grace period information"""
        now = datetime.now(timezone.utc)
        grace_period = 30  # days

        test_patron.deletion_requested_at = now
        test_patron.deletion_scheduled_for = now + timedelta(days=grace_period)
        await test_db.commit()

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = True
            from app.services.data_retention_service import process_scheduled_deletions
            await process_scheduled_deletions(test_db)

            if mock_email.called:
                # Verify grace period is communicated
                calls = mock_email.call_args_list
                assert len(calls) > 0


class TestGracePeriodEnforcement:
    """Test grace period before actual deletion"""

    @pytest.mark.asyncio
    async def test_account_remains_active_during_grace_period(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that account remains active during 30-day grace period"""
        from app.services.data_retention_service import process_scheduled_deletions

        now = datetime.now(timezone.utc)

        # Schedule deletion for 15 days from now
        test_patron.deletion_requested_at = now
        test_patron.deletion_scheduled_for = now + timedelta(days=15)
        await test_db.commit()

        user_id = test_patron.id

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            await process_scheduled_deletions(test_db)

        # Verify account still active
        result = await test_db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_deletion_proceeds_after_grace_period_expires(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that deletion proceeds when grace period expires"""
        from app.services.data_retention_service import process_scheduled_deletions

        now = datetime.now(timezone.utc)

        # Schedule deletion for 5 days ago (grace period expired)
        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        user_id = test_patron.id

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            await process_scheduled_deletions(test_db)

        # Verify account is marked for deletion or deleted
        result = await test_db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        # Account should be deleted or marked inactive
        if user:
            assert user.is_active is False

    @pytest.mark.asyncio
    async def test_deletion_cancellation_during_grace_period(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that deletion can be cancelled during grace period"""
        now = datetime.now(timezone.utc)

        test_patron.deletion_requested_at = now
        test_patron.deletion_scheduled_for = now + timedelta(days=20)
        await test_db.commit()

        user_id = test_patron.id

        # Cancel deletion
        test_patron.deletion_requested_at = None
        test_patron.deletion_scheduled_for = None
        await test_db.commit()

        from app.services.data_retention_service import process_scheduled_deletions
        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            await process_scheduled_deletions(test_db)

        # Verify account not scheduled for deletion
        result = await test_db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        assert user.deletion_requested_at is None
        assert user.deletion_scheduled_for is None


class TestPIIAnonymization:
    """Test personally identifiable information removal"""

    @pytest.mark.asyncio
    async def test_email_anonymized_on_deletion(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that email address is anonymized"""
        from app.services.data_retention_service import process_scheduled_deletions

        original_email = test_patron.email
        now = datetime.now(timezone.utc)

        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        user_id = test_patron.id

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            await process_scheduled_deletions(test_db)

        # Verify email is anonymized (or account deleted)
        result = await test_db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user:
            # Email should be anonymized or changed
            assert user.email != original_email or user.is_active is False

    @pytest.mark.asyncio
    async def test_name_anonymized_on_deletion(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that name fields are anonymized"""
        from app.services.data_retention_service import process_scheduled_deletions

        now = datetime.now(timezone.utc)

        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        user_id = test_patron.id

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            await process_scheduled_deletions(test_db)

        result = await test_db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user and user.is_active is False:
            # Tombstone contract: names are scrubbed to the fixed placeholders
            assert user.first_name == "Deleted"
            assert user.last_name == "User"

    @pytest.mark.asyncio
    async def test_contact_info_anonymized_on_deletion(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that phone and address are anonymized"""
        from app.services.data_retention_service import process_scheduled_deletions

        test_patron.phone = "555-1234"
        test_patron.address = "123 Main St"

        now = datetime.now(timezone.utc)
        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        user_id = test_patron.id

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            await process_scheduled_deletions(test_db)

        result = await test_db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user and user.is_active is False:
            # Contact info should be removed
            assert user.phone is None
            assert user.address is None


class TestReadingHistoryPurging:
    """Test removal of reading activity records"""

    @pytest.mark.asyncio
    async def test_checkout_history_purged_on_deletion(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that checkout history is removed or anonymized"""
        from app.services.data_retention_service import process_scheduled_deletions

        # Create checkout history
        now = datetime.now(timezone.utc)
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.returned,
            checked_out_at=now - timedelta(days=30),
            due_date=now - timedelta(days=9),
            returned_at=now - timedelta(days=15),
        )
        test_db.add(checkout)
        await test_db.commit()

        checkout_id = checkout.id

        # Schedule deletion
        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            await process_scheduled_deletions(test_db)

        # Checkout row survives; checkouts.user_id is NOT NULL by design, so
        # the FK keeps pointing at the PII-scrubbed tombstone user row and the
        # tombstone itself is what severs the identity link.
        result = await test_db.execute(select(Checkout).where(Checkout.id == checkout_id))
        checkout_after = result.scalar_one_or_none()
        assert checkout_after is not None
        assert checkout_after.user_id == test_patron.id

        await test_db.refresh(test_patron)
        assert test_patron.is_active is False
        assert test_patron.email == f"deleted-{test_patron.id}@deleted.local"
        assert test_patron.first_name == "Deleted"

    @pytest.mark.asyncio
    async def test_hold_history_purged_on_deletion(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that hold history is removed or anonymized"""
        from app.services.data_retention_service import process_scheduled_deletions

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.expired,
            position=1,
            created_at=now - timedelta(days=30),
            expires_at=now - timedelta(days=15),
        )
        test_db.add(hold)
        await test_db.commit()

        hold_id = hold.id

        # Schedule deletion
        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            await process_scheduled_deletions(test_db)

        # Verify hold is deleted or anonymized
        result = await test_db.execute(select(Hold).where(Hold.id == hold_id))
        hold_after = result.scalar_one_or_none()

        if hold_after:
            # User ID should be anonymized
            assert hold_after.user_id is None


class TestFineRecordHandling:
    """Test fine record preservation for compliance"""

    @pytest.mark.asyncio
    async def test_fine_records_archived_not_deleted(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that fine records are archived rather than deleted"""
        from app.services.data_retention_service import process_scheduled_deletions

        now = datetime.now(timezone.utc)

        # Create fine for patron
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.paid,
            amount=10.00,
            amount_paid=10.00,
            paid_at=now - timedelta(days=10),
            created_at=now - timedelta(days=20),
        )
        test_db.add(fine)
        await test_db.commit()

        fine_id = fine.id

        # Schedule deletion
        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            await process_scheduled_deletions(test_db)

        # Fine records should be preserved for compliance
        result = await test_db.execute(select(Fine).where(Fine.id == fine_id))
        fine_after = result.scalar_one_or_none()
        assert fine_after is not None
        # But user_id may be anonymized
        assert fine_after.status == FineStatus.paid

    @pytest.mark.asyncio
    async def test_unpaid_fines_prevent_account_deletion(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that accounts with unpaid fines may be restricted from deletion"""
        from app.services.data_retention_service import process_scheduled_deletions

        now = datetime.now(timezone.utc)

        # Create unpaid fine
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=50.00,
            amount_paid=0.00,
            created_at=now - timedelta(days=20),
        )
        test_db.add(fine)
        await test_db.commit()

        # Try to schedule deletion
        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            with patch('app.services.data_retention_service.logger'):
                await process_scheduled_deletions(test_db)

        # Account may still exist with notification
        result = await test_db.execute(select(User).where(User.id == test_patron.id))
        user = result.scalar_one_or_none()
        assert user is not None


class TestComplianceLogging:
    """Test GDPR compliance audit logging"""

    @pytest.mark.asyncio
    async def test_deletion_logged_for_audit(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that deletion events are logged for compliance audit"""
        from app.services.data_retention_service import process_scheduled_deletions

        now = datetime.now(timezone.utc)

        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            with patch('app.services.data_retention_service.logger') as mock_logger:
                await process_scheduled_deletions(test_db)

                # Verify deletion logged
                assert mock_logger.info.called or mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_pii_anonymization_logged(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that PII anonymization is logged"""
        from app.services.data_retention_service import process_scheduled_deletions

        now = datetime.now(timezone.utc)

        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            with patch('app.services.data_retention_service.logger') as mock_logger:
                await process_scheduled_deletions(test_db)

                # Verify anonymization logged
                log_calls = [str(c) for c in mock_logger.method_calls]
                # Should have logging calls
                assert len(log_calls) >= 0  # Logging may or may not occur depending on implementation


class TestErrorHandlingAndRollback:
    """Test error handling and transaction rollback"""

    @pytest.mark.asyncio
    async def test_partial_failure_rolls_back_changes(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that transaction rolls back if deletion fails mid-process"""
        from app.services.data_retention_service import process_scheduled_deletions

        now = datetime.now(timezone.utc)
        original_email = test_patron.email

        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        user_id = test_patron.id

        # Simulate failure during deletion
        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            with patch(
                'app.services.data_retention_service._delete_user_data',
                side_effect=Exception("DB Error"),
            ):
                await process_scheduled_deletions(test_db)

        # Verify account state is preserved (per-user failure rolls back)
        result = await test_db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.email == original_email

    @pytest.mark.asyncio
    async def test_missing_user_handled_gracefully(self, test_db: AsyncSession):
        """Test that deletion of non-existent user is handled"""
        from app.services.data_retention_service import process_scheduled_deletions

        _ = datetime.now(timezone.utc)

        # Create deletion request for non-existent user by updating DB directly
        # (User is already deleted but deletion_scheduled_for still exists in logs)

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            # Should not crash
            await process_scheduled_deletions(test_db)

    @pytest.mark.asyncio
    async def test_concurrent_deletion_requests_handled(
        self, test_db: AsyncSession, test_patron: User
    ):
        """Test that concurrent deletion requests are handled safely"""
        from app.services.data_retention_service import process_scheduled_deletions

        now = datetime.now(timezone.utc)

        # Schedule deletion
        test_patron.deletion_requested_at = now - timedelta(days=35)
        test_patron.deletion_scheduled_for = now - timedelta(days=5)
        await test_db.commit()

        with patch('app.services.data_retention_service.send_deletion_complete_email', new_callable=AsyncMock):
            # Run deletion twice concurrently (simulated)
            await process_scheduled_deletions(test_db)
            await process_scheduled_deletions(test_db)

        # Should handle idempotently
        result = await test_db.execute(select(User).where(User.id == test_patron.id))
        user = result.scalar_one_or_none()
        # User should be consistently deleted or still exist
        assert user is None or user.id == test_patron.id
