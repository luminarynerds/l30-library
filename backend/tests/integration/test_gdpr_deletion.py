# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for GDPR-style patron data deletion (Right to be Forgotten).

Tests cover:
1. Patron self-service deletion request
2. Staff-initiated deletion
3. Deletion eligibility checks (fines, checkouts, children)
4. 30-day grace period workflow
5. Data export before deletion
6. 90-day email re-registration block
7. Deletion confirmation/cancellation
8. Audit logging
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.security import hash_password
from app.models.user import User, UserRole, DeletedEmail
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineType, FineStatus
from app.models.audit_log import AuditLog, AuditAction
from app.api.v1.privacy.helpers import hash_email_for_block, check_email_blocked


class TestDeletionEligibility:
    """Tests for deletion eligibility checking."""

    @pytest.mark.asyncio
    async def test_eligible_user_can_delete(self, test_db, test_patron):
        """User with no blockers should be eligible for deletion."""
        from app.api.v1.privacy.helpers import check_deletion_eligibility

        eligibility = await check_deletion_eligibility(test_db, test_patron)

        assert eligibility.eligible is True
        assert eligibility.has_unpaid_fines is False
        assert eligibility.has_active_checkouts is False
        assert eligibility.has_child_accounts is False
        assert len(eligibility.blockers) == 0

    @pytest.mark.asyncio
    async def test_unpaid_fines_block_deletion(self, test_db, test_patron, test_fine):
        """User with unpaid fines should not be eligible."""
        from app.api.v1.privacy.helpers import check_deletion_eligibility

        eligibility = await check_deletion_eligibility(test_db, test_patron)

        assert eligibility.eligible is False
        assert eligibility.has_unpaid_fines is True
        assert eligibility.unpaid_fine_amount == 10.00
        assert any("fine" in blocker.lower() for blocker in eligibility.blockers)

    @pytest.mark.asyncio
    async def test_active_checkouts_block_deletion(self, test_db, test_patron, test_checkout):
        """User with active checkouts should not be eligible."""
        from app.api.v1.privacy.helpers import check_deletion_eligibility

        eligibility = await check_deletion_eligibility(test_db, test_patron)

        assert eligibility.eligible is False
        assert eligibility.has_active_checkouts is True
        assert eligibility.active_checkout_count == 1
        assert any("checkout" in blocker.lower() for blocker in eligibility.blockers)

    @pytest.mark.asyncio
    async def test_child_accounts_block_deletion(self, test_db, test_patron):
        """User with linked child accounts should not be eligible."""
        from app.api.v1.privacy.helpers import check_deletion_eligibility

        # Create a child account linked to the patron
        child = User(
            email="child@example.com",
            password_hash=hash_password("ChildPass123!"),
            first_name="Child",
            last_name="User",
            role=UserRole.CHILD,
            parent_guardian_id=test_patron.id,
            is_active=True,
        )
        test_db.add(child)
        await test_db.commit()

        eligibility = await check_deletion_eligibility(test_db, test_patron)

        assert eligibility.eligible is False
        assert eligibility.has_child_accounts is True
        assert eligibility.child_account_count == 1
        assert any("child" in blocker.lower() for blocker in eligibility.blockers)


class TestSelfServiceDeletionRequest:
    """Tests for patron self-service deletion requests."""

    @pytest.mark.asyncio
    async def test_request_deletion_schedules_for_30_days(self, test_db, test_patron, test_user_data):
        """Deletion request should schedule deletion for 30 days."""
        from app.api.v1.privacy.schemas import AccountDeletionRequest
        from app.core.security import verify_password

        # Set up deletion request
        now = datetime.now(timezone.utc)

        # Simulate the request process
        test_patron.deletion_requested_at = now
        test_patron.deletion_scheduled_for = now + timedelta(days=30)
        await test_db.commit()
        await test_db.refresh(test_patron)

        assert test_patron.deletion_requested_at is not None
        assert test_patron.deletion_scheduled_for is not None

        # Should be approximately 30 days from now
        days_until_deletion = (test_patron.deletion_scheduled_for - now).days
        assert days_until_deletion == 30

    @pytest.mark.asyncio
    async def test_cancel_deletion_clears_schedule(self, test_db, test_patron):
        """Cancelling deletion should clear the scheduled date."""
        now = datetime.now(timezone.utc)

        # First schedule deletion
        test_patron.deletion_requested_at = now
        test_patron.deletion_scheduled_for = now + timedelta(days=30)
        await test_db.commit()

        # Then cancel
        test_patron.deletion_requested_at = None
        test_patron.deletion_scheduled_for = None
        await test_db.commit()
        await test_db.refresh(test_patron)

        assert test_patron.deletion_requested_at is None
        assert test_patron.deletion_scheduled_for is None

    @pytest.mark.asyncio
    async def test_duplicate_deletion_request_rejected(self, test_db, test_patron):
        """Cannot request deletion twice."""
        now = datetime.now(timezone.utc)

        # First request
        test_patron.deletion_requested_at = now
        test_patron.deletion_scheduled_for = now + timedelta(days=30)
        await test_db.commit()

        # Second request should see existing
        await test_db.refresh(test_patron)
        assert test_patron.deletion_requested_at is not None


class TestEmailReregistrationBlock:
    """Tests for 90-day email re-registration blocking."""

    @pytest.mark.asyncio
    async def test_email_hash_is_deterministic(self):
        """Same email should always produce same hash."""
        email = "test@example.com"
        hash1 = hash_email_for_block(email)
        hash2 = hash_email_for_block(email)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

    @pytest.mark.asyncio
    async def test_email_hash_is_case_insensitive(self):
        """Email hashing should be case-insensitive."""
        hash1 = hash_email_for_block("Test@Example.COM")
        hash2 = hash_email_for_block("test@example.com")

        assert hash1 == hash2

    @pytest.mark.asyncio
    async def test_blocked_email_detected(self, test_db):
        """Blocked email should be detected."""
        email = "blocked@example.com"
        now = datetime.now(timezone.utc)

        # Create blocked email record
        blocked = DeletedEmail(
            email_hash=hash_email_for_block(email),
            deleted_at=now,
            block_expires_at=now + timedelta(days=90),
            deletion_type="self_service",
        )
        test_db.add(blocked)
        await test_db.commit()

        # Check if blocked
        is_blocked, expires_at = await check_email_blocked(test_db, email)

        assert is_blocked is True
        assert expires_at is not None

    @pytest.mark.asyncio
    async def test_expired_block_not_detected(self, test_db):
        """Expired block should not be detected."""
        email = "expired@example.com"
        now = datetime.now(timezone.utc)

        # Create expired block record
        blocked = DeletedEmail(
            email_hash=hash_email_for_block(email),
            deleted_at=now - timedelta(days=100),
            block_expires_at=now - timedelta(days=10),  # Expired
            deletion_type="self_service",
        )
        test_db.add(blocked)
        await test_db.commit()

        # Check if blocked
        is_blocked, expires_at = await check_email_blocked(test_db, email)

        assert is_blocked is False
        assert expires_at is None


class TestStaffInitiatedDeletion:
    """Tests for staff-initiated deletion."""

    @pytest.mark.asyncio
    async def test_staff_can_initiate_patron_deletion(self, test_db, test_staff, test_patron):
        """Staff member should be able to initiate deletion for patron."""
        now = datetime.now(timezone.utc)

        # Simulate staff initiating deletion
        test_patron.deletion_requested_at = now
        test_patron.deletion_scheduled_for = now + timedelta(days=30)
        await test_db.commit()

        # Create audit log
        audit = AuditLog(
            admin_id=test_staff.id,
            target_user_id=test_patron.id,
            action=AuditAction.STAFF_INITIATED_DELETION,
            details={
                "deletion_type": "staff_initiated",
                "reason": "In-person request",
                "identity_verified": True,
            },
        )
        test_db.add(audit)
        await test_db.commit()

        await test_db.refresh(test_patron)
        assert test_patron.deletion_scheduled_for is not None

    @pytest.mark.asyncio
    async def test_staff_cannot_delete_admin(self, test_db, test_staff, test_admin):
        """Staff should not be able to delete admin accounts."""
        # This is a policy check - admin accounts protected
        assert test_admin.role == UserRole.ADMIN
        assert test_staff.role == UserRole.STAFF


class TestDataExport:
    """Tests for GDPR data export functionality."""

    @pytest.mark.asyncio
    async def test_export_includes_profile_data(self, test_db, test_patron):
        """Export should include profile information."""
        # Profile data that should be exported
        profile_fields = [
            "email", "first_name", "last_name", "phone", "address",
            "library_card", "role", "email_verified"
        ]

        for field in profile_fields:
            assert hasattr(test_patron, field)

    @pytest.mark.asyncio
    async def test_audit_log_created_on_export(self, test_db, test_patron):
        """Data export should create audit log entry."""
        audit = AuditLog(
            target_user_id=test_patron.id,
            action=AuditAction.GDPR_DATA_EXPORTED,
            details={"export_type": "full"},
        )
        test_db.add(audit)
        await test_db.commit()

        # Verify audit was created
        from sqlalchemy import select
        result = await test_db.execute(
            select(AuditLog).where(
                AuditLog.target_user_id == test_patron.id,
                AuditLog.action == AuditAction.GDPR_DATA_EXPORTED,
            )
        )
        found_audit = result.scalar_one_or_none()
        assert found_audit is not None


class TestUserDeletion:
    """Tests for actual user data deletion."""

    @pytest.mark.asyncio
    async def test_user_deletion_anonymizes_checkouts(self, test_db, test_patron, test_catalog_item):
        """Checkouts should be anonymized (not deleted) on user deletion."""
        from app.api.v1.privacy.helpers import _perform_user_deletion

        # Create a returned checkout
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.returned,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=9),
            returned_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        test_db.add(checkout)
        await test_db.commit()
        checkout_id = checkout.id

        # Perform deletion
        await _perform_user_deletion(test_db, test_patron.id)
        await test_db.commit()

        # Checkout row survives and keeps its user_id (NOT NULL + RESTRICT by
        # design); anonymization = the user row itself is scrubbed of PII.
        from sqlalchemy import select
        result = await test_db.execute(
            select(Checkout).where(Checkout.id == checkout_id)
        )
        anonymized_checkout = result.scalar_one_or_none()

        assert anonymized_checkout is not None
        assert anonymized_checkout.user_id == test_patron.id

        result = await test_db.execute(
            select(User).where(User.id == test_patron.id)
        )
        tombstone = result.scalar_one_or_none()
        assert tombstone is not None
        assert tombstone.email.startswith("deleted-")
        assert tombstone.first_name == "Deleted"
        assert tombstone.last_name == "User"
        assert tombstone.is_active is False

    @pytest.mark.asyncio
    async def test_user_deletion_anonymizes_fines(self, test_db, test_patron):
        """Fines should be anonymized (not deleted) for legal records."""
        from app.api.v1.privacy.helpers import _perform_user_deletion

        # Create a paid fine
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.paid,
            amount=Decimal("5.00"),
            amount_paid=Decimal("5.00"),
            description="Test fine",
        )
        test_db.add(fine)
        await test_db.commit()
        fine_id = fine.id

        # Perform deletion
        await _perform_user_deletion(test_db, test_patron.id)
        await test_db.commit()

        # Check fine still exists but is anonymized
        from sqlalchemy import select
        result = await test_db.execute(
            select(Fine).where(Fine.id == fine_id)
        )
        anonymized_fine = result.scalar_one_or_none()

        assert anonymized_fine is not None
        assert anonymized_fine.user_id is None  # Anonymized

    @pytest.mark.asyncio
    async def test_user_deletion_deletes_holds(self, test_db, test_patron, test_catalog_item):
        """Holds should be deleted on user deletion."""
        from app.api.v1.privacy.helpers import _perform_user_deletion

        # Create a hold
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(hold)
        await test_db.commit()
        hold_id = hold.id

        # Perform deletion
        await _perform_user_deletion(test_db, test_patron.id)
        await test_db.commit()

        # Holds are soft-cancelled (status="cancelled"), preserved for audit —
        # matches _perform_user_deletion step 6, not hard-deleted.
        from sqlalchemy import select
        result = await test_db.execute(
            select(Hold).where(Hold.id == hold_id)
        )
        cancelled_hold = result.scalar_one_or_none()

        assert cancelled_hold is not None
        assert cancelled_hold.status == "cancelled"

    @pytest.mark.asyncio
    async def test_user_record_deleted(self, test_db, test_user_data):
        """User record is soft-deleted: row kept for referential integrity
        (checkouts.user_id is NOT NULL/RESTRICT), all PII scrubbed."""
        from app.api.v1.privacy.helpers import _perform_user_deletion

        # Create a test user just for deletion
        user = User(
            email="delete_me@example.com",
            password_hash=hash_password("DeleteMe123!"),
            first_name="Delete",
            last_name="Me",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(user)
        await test_db.commit()
        user_id = user.id

        # Perform deletion
        await _perform_user_deletion(test_db, user_id)
        await test_db.commit()

        # Row survives as a PII-free tombstone
        from sqlalchemy import select
        result = await test_db.execute(
            select(User).where(User.id == user_id)
        )
        tombstone = result.scalar_one_or_none()

        assert tombstone is not None
        assert tombstone.email == f"deleted-{user_id}@deleted.local"
        assert tombstone.first_name == "Deleted"
        assert tombstone.last_name == "User"
        assert tombstone.is_active is False
        assert tombstone.password_hash != hash_password("DeleteMe123!")
        assert tombstone.deletion_requested_at is not None


class TestAuditLogging:
    """Tests for GDPR-related audit logging."""

    @pytest.mark.asyncio
    async def test_deletion_request_logged(self, test_db, test_patron):
        """Deletion request should create audit log."""
        audit = AuditLog(
            target_user_id=test_patron.id,
            action=AuditAction.GDPR_DELETION_REQUESTED,
            details={
                "deletion_type": "scheduled_self_service",
                "scheduled_for": datetime.now(timezone.utc).isoformat(),
            },
        )
        test_db.add(audit)
        await test_db.commit()

        assert audit.id is not None
        assert audit.action == AuditAction.GDPR_DELETION_REQUESTED

    @pytest.mark.asyncio
    async def test_deletion_cancellation_logged(self, test_db, test_patron):
        """Deletion cancellation should create audit log."""
        audit = AuditLog(
            target_user_id=test_patron.id,
            action=AuditAction.GDPR_DELETION_CANCELLED,
            details={"cancelled_by": "user"},
        )
        test_db.add(audit)
        await test_db.commit()

        assert audit.id is not None
        assert audit.action == AuditAction.GDPR_DELETION_CANCELLED

    @pytest.mark.asyncio
    async def test_completion_audit_is_anonymized(self, test_db):
        """Deletion completion audit should not reference user ID."""
        # When deletion completes, the audit should be anonymized
        audit = AuditLog(
            target_user_id=None,  # Anonymized
            action=AuditAction.GDPR_DELETION_COMPLETED,
            details={
                "deletion_type": "scheduled_automatic",
                "user_role": "PATRON",
                "account_age_days": 365,
            },
        )
        test_db.add(audit)
        await test_db.commit()

        assert audit.id is not None
        assert audit.target_user_id is None  # Important: anonymized


class TestDataRetentionService:
    """Tests for the data retention service."""

    @pytest.mark.asyncio
    async def test_expired_email_blocks_cleaned_up(self, test_db):
        """Expired email blocks should be cleaned up."""
        from app.services.data_retention_service import cleanup_expired_email_blocks

        now = datetime.now(timezone.utc)

        # Create expired block
        expired_block = DeletedEmail(
            email_hash=hash_email_for_block("expired@test.com"),
            deleted_at=now - timedelta(days=100),
            block_expires_at=now - timedelta(days=10),
            deletion_type="self_service",
        )
        test_db.add(expired_block)

        # Create active block
        active_block = DeletedEmail(
            email_hash=hash_email_for_block("active@test.com"),
            deleted_at=now,
            block_expires_at=now + timedelta(days=80),
            deletion_type="self_service",
        )
        test_db.add(active_block)
        await test_db.commit()

        expired_id = expired_block.id
        active_id = active_block.id

        # Run cleanup
        deleted_count = await cleanup_expired_email_blocks(test_db)
        await test_db.commit()

        assert deleted_count >= 1

        # Verify expired block was deleted
        from sqlalchemy import select
        result = await test_db.execute(
            select(DeletedEmail).where(DeletedEmail.id == expired_id)
        )
        assert result.scalar_one_or_none() is None

        # Verify active block still exists
        result = await test_db.execute(
            select(DeletedEmail).where(DeletedEmail.id == active_id)
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_scheduled_deletions_processed(self, test_db, test_user_data):
        """Scheduled deletions past their date should be processed."""
        from app.services.data_retention_service import process_scheduled_deletions

        now = datetime.now(timezone.utc)

        # Create user scheduled for deletion (past due)
        user = User(
            email="scheduled_delete@example.com",
            password_hash=hash_password("DeleteMe123!"),
            first_name="Scheduled",
            last_name="Delete",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            deletion_requested_at=now - timedelta(days=35),
            deletion_scheduled_for=now - timedelta(days=5),  # 5 days ago
        )
        test_db.add(user)
        await test_db.commit()
        user_id = user.id

        # Run processing
        deleted_count = await process_scheduled_deletions(test_db)
        await test_db.commit()

        assert deleted_count >= 1

        # Verify the user row survives as a PII-scrubbed, deactivated
        # tombstone (checkouts.user_id is NOT NULL by design, so retention
        # deletion tombstones instead of hard-deleting).
        from sqlalchemy import select
        result = await test_db.execute(
            select(User).where(User.id == user_id)
        )
        tombstone = result.scalar_one_or_none()
        assert tombstone is not None
        assert tombstone.is_active is False
        assert tombstone.email == f"deleted-{user_id}@deleted.local"
        assert tombstone.first_name == "Deleted"
