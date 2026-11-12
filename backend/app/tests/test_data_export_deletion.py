# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comprehensive tests for data export and deletion privacy features.

Tests cover:
- Consent record creation and retrieval
- Consent withdrawal
- Data sharing log recording and retrieval
- Data correction requests (self-service and staff-reviewed)
- Staff correction approval/rejection
- Deletion verification transparency
- Enhanced complete data export
- Privacy ledger anonymization on user deletion
- Data retention service integration with privacy ledger
"""

import pytest
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.audit_log import AuditLog, AuditAction
from app.models.privacy_ledger import (
    ConsentRecord,
    ConsentMethod,
    ConsentStatus,
    ConsentType,
    CorrectionStatus,
    DataCorrectionLog,
    DataSharingLog,
    DataSharingPurpose,
)

# NOTE: no local `db` fixture here. This file used to spin up its own
# in-memory SQLite engine with a hand-rolled patch that swapped Postgres
# JSONB/ARRAY/BYTEA columns for SQLite-compatible types across the whole
# (globally shared) Base.metadata -- a moving target, since new
# Postgres-only types/defaults elsewhere in the schema (TSVECTOR, plain
# sqlalchemy.ARRAY vs. dialects.postgresql.ARRAY, `::jsonb`-cast server
# defaults) kept resurfacing as new SQLite compile errors, and mutating
# the shared metadata in place risked leaking into other test files that
# run in the same pytest process. Falls through to the shared
# Postgres-backed `db` fixture in app/tests/conftest.py instead, which
# sidesteps the whole class of problem since Postgres supports its own
# types natively.


@pytest.fixture
async def patron(db: AsyncSession) -> User:
    """Create a sample patron user."""
    user = User(
        email="patron@example.com",
        password_hash="hashed_password",
        first_name="Jane",
        last_name="Reader",
        role=UserRole.PATRON,
        phone="555-0100",
        address="123 Main St",
        track_reading_history=True,
        allow_staff_access_to_history=True,
        notification_frequency="instant",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def staff_user(db: AsyncSession) -> User:
    """Create a sample staff user."""
    user = User(
        email="staff@example.com",
        password_hash="hashed_password",
        first_name="Staff",
        last_name="Member",
        role=UserRole.STAFF,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# =============================================================================
# Consent Record Tests
# =============================================================================


class TestConsentRecords:
    """Tests for consent record creation and retrieval."""

    async def test_create_consent_record_on_account_creation(self, db: AsyncSession, patron: User):
        """Consent record is created when account is created."""
        record = ConsentRecord(
            user_id=patron.id,
            consent_type=ConsentType.ACCOUNT_CREATION,
            status=ConsentStatus.GRANTED,
            method=ConsentMethod.WEB_FORM,
            policy_version="1.0",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            details={"terms_accepted": True, "privacy_policy_version": "2024-01"},
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        assert record.id is not None
        assert record.user_id == patron.id
        assert record.consent_type == ConsentType.ACCOUNT_CREATION
        assert record.status == ConsentStatus.GRANTED
        assert record.method == ConsentMethod.WEB_FORM
        assert record.policy_version == "1.0"

    async def test_multiple_consent_types(self, db: AsyncSession, patron: User):
        """A patron can have consent records for multiple types."""
        types = [
            ConsentType.ACCOUNT_CREATION,
            ConsentType.EMAIL_NOTIFICATIONS,
            ConsentType.READING_HISTORY_TRACKING,
        ]
        for ct in types:
            record = ConsentRecord(
                user_id=patron.id,
                consent_type=ct,
                status=ConsentStatus.GRANTED,
                method=ConsentMethod.WEB_FORM,
            )
            db.add(record)
        await db.commit()

        result = await db.execute(
            select(ConsentRecord).where(ConsentRecord.user_id == patron.id)
        )
        records = result.scalars().all()
        assert len(records) == 3

    async def test_consent_withdrawal_creates_new_record(self, db: AsyncSession, patron: User):
        """Withdrawing consent creates a new record, preserving history."""
        # Grant consent
        grant = ConsentRecord(
            user_id=patron.id,
            consent_type=ConsentType.READING_HISTORY_TRACKING,
            status=ConsentStatus.GRANTED,
            method=ConsentMethod.WEB_FORM,
        )
        db.add(grant)
        await db.commit()

        # Withdraw consent
        withdraw = ConsentRecord(
            user_id=patron.id,
            consent_type=ConsentType.READING_HISTORY_TRACKING,
            status=ConsentStatus.WITHDRAWN,
            method=ConsentMethod.WEB_FORM,
            details={"action": "patron_initiated_withdrawal"},
        )
        db.add(withdraw)
        await db.commit()

        result = await db.execute(
            select(ConsentRecord)
            .where(
                ConsentRecord.user_id == patron.id,
                ConsentRecord.consent_type == ConsentType.READING_HISTORY_TRACKING,
            )
            .order_by(ConsentRecord.id.desc())
        )
        records = result.scalars().all()
        assert len(records) == 2
        # Most recent (highest ID) is the withdrawal
        assert records[0].status == ConsentStatus.WITHDRAWN

    async def test_in_person_consent_with_staff(self, db: AsyncSession, patron: User, staff_user: User):
        """Consent given in person is recorded with staff member who witnessed it."""
        record = ConsentRecord(
            user_id=patron.id,
            consent_type=ConsentType.PHOTO_RELEASE,
            status=ConsentStatus.GRANTED,
            method=ConsentMethod.IN_PERSON,
            recorded_by_staff_id=staff_user.id,
            details={"form_number": "PR-2024-001"},
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        assert record.recorded_by_staff_id == staff_user.id
        assert record.method == ConsentMethod.IN_PERSON

    async def test_consent_expiration(self, db: AsyncSession, patron: User):
        """Consent records can have expiration dates."""
        expires = datetime.now(timezone.utc) + timedelta(days=365)
        record = ConsentRecord(
            user_id=patron.id,
            consent_type=ConsentType.MARKETING_COMMUNICATIONS,
            status=ConsentStatus.GRANTED,
            method=ConsentMethod.EMAIL_CONFIRMATION,
            expires_at=expires,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        assert record.expires_at is not None


# =============================================================================
# Data Sharing Log Tests
# =============================================================================


class TestDataSharingLog:
    """Tests for data sharing log recording and retrieval."""

    async def test_record_law_enforcement_sharing(self, db: AsyncSession, patron: User, staff_user: User):
        """Record data shared with law enforcement."""
        log = DataSharingLog(
            user_id=patron.id,
            recipient_name="Springfield Police Department",
            recipient_type="law_enforcement",
            purpose=DataSharingPurpose.LAW_ENFORCEMENT_REQUEST,
            data_categories=["name", "address", "checkout_history"],
            legal_basis="court_order",
            reference_id="LE-2024-001",
            reference_type="law_enforcement_request",
            patron_notified=True,
            patron_notified_at=datetime.now(timezone.utc),
            shared_by_staff_id=staff_user.id,
            notes="Court order #12345",
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)

        assert log.id is not None
        assert log.recipient_name == "Springfield Police Department"
        assert log.purpose == DataSharingPurpose.LAW_ENFORCEMENT_REQUEST
        assert "checkout_history" in log.data_categories
        assert log.legal_basis == "court_order"
        assert log.patron_notified is True

    async def test_record_interlibrary_loan_sharing(self, db: AsyncSession, patron: User, staff_user: User):
        """Record data shared for interlibrary loan."""
        log = DataSharingLog(
            user_id=patron.id,
            recipient_name="Metro Library Consortium",
            recipient_type="consortium",
            purpose=DataSharingPurpose.INTERLIBRARY_LOAN,
            data_categories=["name", "library_card", "email"],
            legal_basis="patron_consent",
            patron_notified=False,
            shared_by_staff_id=staff_user.id,
        )
        db.add(log)
        await db.commit()

        assert log.id is not None
        assert log.patron_notified is False

    async def test_multiple_sharing_events(self, db: AsyncSession, patron: User, staff_user: User):
        """Multiple sharing events are tracked independently."""
        for recipient in ["Vendor A", "Vendor B", "Collection Agency"]:
            log = DataSharingLog(
                user_id=patron.id,
                recipient_name=recipient,
                purpose=DataSharingPurpose.PAYMENT_PROCESSING if "Vendor" in recipient else DataSharingPurpose.COLLECTION_AGENCY,
                data_categories=["name", "email"],
                shared_by_staff_id=staff_user.id,
            )
            db.add(log)
        await db.commit()

        result = await db.execute(
            select(DataSharingLog).where(DataSharingLog.user_id == patron.id)
        )
        records = result.scalars().all()
        assert len(records) == 3

    async def test_sharing_log_preserves_categories(self, db: AsyncSession, patron: User, staff_user: User):
        """Data categories list is correctly stored and retrieved."""
        categories = ["name", "email", "phone", "address", "checkout_history", "fine_records"]
        log = DataSharingLog(
            user_id=patron.id,
            recipient_name="Insurance Company",
            purpose=DataSharingPurpose.INSURANCE_CLAIM,
            data_categories=categories,
            shared_by_staff_id=staff_user.id,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)

        assert log.data_categories == categories


# =============================================================================
# Data Correction Tests
# =============================================================================


class TestDataCorrections:
    """Tests for data correction requests and edit trail."""

    async def test_self_correctable_field_applied_immediately(self, db: AsyncSession, patron: User):
        """Low-risk fields are corrected immediately."""
        correction = DataCorrectionLog(
            user_id=patron.id,
            field_name="phone",
            old_value="555-0100",
            new_value="555-0200",
            reason="Updated phone number",
            status=CorrectionStatus.APPLIED,
            requested_by_user_id=patron.id,
            processed_at=datetime.now(timezone.utc),
        )
        db.add(correction)
        await db.commit()
        await db.refresh(correction)

        assert correction.status == CorrectionStatus.APPLIED
        assert correction.old_value == "555-0100"
        assert correction.new_value == "555-0200"

    async def test_sensitive_field_requires_staff_review(self, db: AsyncSession, patron: User):
        """Sensitive fields like email require staff review."""
        correction = DataCorrectionLog(
            user_id=patron.id,
            field_name="email",
            old_value="patron@example.com",
            new_value="new.email@example.com",
            reason="Typo in email",
            status=CorrectionStatus.PENDING,
            requested_by_user_id=patron.id,
        )
        db.add(correction)
        await db.commit()
        await db.refresh(correction)

        assert correction.status == CorrectionStatus.PENDING
        assert correction.processed_at is None

    async def test_staff_approve_correction(self, db: AsyncSession, patron: User, staff_user: User):
        """Staff can approve a pending correction."""
        correction = DataCorrectionLog(
            user_id=patron.id,
            field_name="first_name",
            old_value="Jane",
            new_value="Janet",
            reason="Legal name change",
            status=CorrectionStatus.PENDING,
            requested_by_user_id=patron.id,
        )
        db.add(correction)
        await db.commit()

        # Staff approves
        correction.status = CorrectionStatus.APPLIED
        correction.processed_by_staff_id = staff_user.id
        correction.processed_at = datetime.now(timezone.utc)
        correction.staff_notes = "Verified with ID"
        await db.commit()
        await db.refresh(correction)

        assert correction.status == CorrectionStatus.APPLIED
        assert correction.processed_by_staff_id == staff_user.id
        assert correction.staff_notes == "Verified with ID"

    async def test_staff_reject_correction(self, db: AsyncSession, patron: User, staff_user: User):
        """Staff can reject a correction with a reason."""
        correction = DataCorrectionLog(
            user_id=patron.id,
            field_name="date_of_birth",
            old_value="1990-01-01",
            new_value="1985-06-15",
            reason="Wrong DOB on file",
            status=CorrectionStatus.PENDING,
            requested_by_user_id=patron.id,
        )
        db.add(correction)
        await db.commit()

        # Staff rejects
        correction.status = CorrectionStatus.REJECTED
        correction.processed_by_staff_id = staff_user.id
        correction.processed_at = datetime.now(timezone.utc)
        correction.staff_notes = "Unable to verify new DOB - no supporting documentation"
        await db.commit()
        await db.refresh(correction)

        assert correction.status == CorrectionStatus.REJECTED

    async def test_edit_trail_preserved(self, db: AsyncSession, patron: User):
        """Multiple corrections to the same field preserve full edit trail."""
        for i, new_phone in enumerate(["555-0200", "555-0300", "555-0400"]):
            correction = DataCorrectionLog(
                user_id=patron.id,
                field_name="phone",
                old_value=f"555-0{i}00" if i > 0 else "555-0100",
                new_value=new_phone,
                reason=f"Correction #{i + 1}",
                status=CorrectionStatus.APPLIED,
                requested_by_user_id=patron.id,
                processed_at=datetime.now(timezone.utc),
            )
            db.add(correction)

        await db.commit()

        result = await db.execute(
            select(DataCorrectionLog)
            .where(
                DataCorrectionLog.user_id == patron.id,
                DataCorrectionLog.field_name == "phone",
            )
            .order_by(DataCorrectionLog.created_at)
        )
        records = result.scalars().all()
        assert len(records) == 3


# =============================================================================
# Deletion & Anonymization Tests
# =============================================================================


class TestDeletionAnonymization:
    """Tests that privacy ledger records are properly anonymized on deletion."""

    async def test_consent_records_anonymized_on_deletion(self, db: AsyncSession, patron: User):
        """Consent records have user_id set to NULL on deletion (not deleted)."""
        record = ConsentRecord(
            user_id=patron.id,
            consent_type=ConsentType.ACCOUNT_CREATION,
            status=ConsentStatus.GRANTED,
            method=ConsentMethod.WEB_FORM,
        )
        db.add(record)
        await db.commit()
        record_id = record.id

        # Simulate anonymization (what _perform_user_deletion does)
        from sqlalchemy import update
        await db.execute(
            update(ConsentRecord)
            .where(ConsentRecord.user_id == patron.id)
            .values(user_id=None)
        )
        await db.commit()

        # Record still exists but user_id is NULL
        result = await db.execute(
            select(ConsentRecord).where(ConsentRecord.id == record_id)
        )
        anonymized = result.scalar_one()
        assert anonymized.user_id is None
        assert anonymized.consent_type == ConsentType.ACCOUNT_CREATION

    async def test_data_sharing_log_anonymized_on_deletion(self, db: AsyncSession, patron: User, staff_user: User):
        """Data sharing logs have user_id set to NULL on deletion."""
        log = DataSharingLog(
            user_id=patron.id,
            recipient_name="Test Vendor",
            purpose=DataSharingPurpose.PAYMENT_PROCESSING,
            data_categories=["name"],
            shared_by_staff_id=staff_user.id,
        )
        db.add(log)
        await db.commit()
        log_id = log.id

        from sqlalchemy import update
        await db.execute(
            update(DataSharingLog)
            .where(DataSharingLog.user_id == patron.id)
            .values(user_id=None)
        )
        await db.commit()

        result = await db.execute(
            select(DataSharingLog).where(DataSharingLog.id == log_id)
        )
        anonymized = result.scalar_one()
        assert anonymized.user_id is None
        assert anonymized.recipient_name == "Test Vendor"

    async def test_correction_log_anonymized_on_deletion(self, db: AsyncSession, patron: User):
        """Data correction logs have user_id set to NULL on deletion."""
        correction = DataCorrectionLog(
            user_id=patron.id,
            field_name="phone",
            old_value="555-0100",
            new_value="555-0200",
            reason="Updated",
            status=CorrectionStatus.APPLIED,
            requested_by_user_id=patron.id,
        )
        db.add(correction)
        await db.commit()
        correction_id = correction.id

        from sqlalchemy import update
        await db.execute(
            update(DataCorrectionLog)
            .where(DataCorrectionLog.user_id == patron.id)
            .values(user_id=None)
        )
        await db.commit()

        result = await db.execute(
            select(DataCorrectionLog).where(DataCorrectionLog.id == correction_id)
        )
        anonymized = result.scalar_one()
        assert anonymized.user_id is None


# =============================================================================
# Integration Tests
# =============================================================================


class TestPrivacyIntegration:
    """Integration tests for the complete privacy workflow."""

    async def test_full_lifecycle_consent_to_deletion(self, db: AsyncSession, patron: User, staff_user: User):
        """Test complete lifecycle: consent -> sharing -> correction -> export -> deletion."""
        # 1. Record initial consent
        consent = ConsentRecord(
            user_id=patron.id,
            consent_type=ConsentType.ACCOUNT_CREATION,
            status=ConsentStatus.GRANTED,
            method=ConsentMethod.WEB_FORM,
            policy_version="1.0",
        )
        db.add(consent)

        # 2. Record a data sharing event
        sharing = DataSharingLog(
            user_id=patron.id,
            recipient_name="State ILL Network",
            purpose=DataSharingPurpose.INTERLIBRARY_LOAN,
            data_categories=["name", "library_card"],
            legal_basis="patron_consent",
            patron_notified=True,
            patron_notified_at=datetime.now(timezone.utc),
            shared_by_staff_id=staff_user.id,
        )
        db.add(sharing)

        # 3. Request a data correction
        correction = DataCorrectionLog(
            user_id=patron.id,
            field_name="phone",
            old_value="555-0100",
            new_value="555-9999",
            reason="Moved, new number",
            status=CorrectionStatus.APPLIED,
            requested_by_user_id=patron.id,
            processed_at=datetime.now(timezone.utc),
        )
        db.add(correction)
        await db.commit()

        # 4. Verify all records exist
        consent_result = await db.execute(
            select(ConsentRecord).where(ConsentRecord.user_id == patron.id)
        )
        assert len(consent_result.scalars().all()) == 1

        sharing_result = await db.execute(
            select(DataSharingLog).where(DataSharingLog.user_id == patron.id)
        )
        assert len(sharing_result.scalars().all()) == 1

        correction_result = await db.execute(
            select(DataCorrectionLog).where(DataCorrectionLog.user_id == patron.id)
        )
        assert len(correction_result.scalars().all()) == 1

        # 5. Simulate deletion (anonymize)
        from sqlalchemy import update
        for model in [ConsentRecord, DataSharingLog, DataCorrectionLog]:
            await db.execute(
                update(model)
                .where(model.user_id == patron.id)
                .values(user_id=None)
            )
        await db.commit()

        # 6. Verify records still exist but are anonymized
        consent_result = await db.execute(
            select(ConsentRecord).where(ConsentRecord.user_id == patron.id)
        )
        assert len(consent_result.scalars().all()) == 0  # No records linked to user

        all_consents = await db.execute(select(ConsentRecord))
        consents = all_consents.scalars().all()
        assert len(consents) == 1  # Record exists but user_id is NULL
        assert consents[0].user_id is None

    async def test_consent_proves_authorization(self, db: AsyncSession, patron: User):
        """Consent records can prove when authorization was given."""
        now = datetime.now(timezone.utc)

        # Create a consent record with detailed proof
        consent = ConsentRecord(
            user_id=patron.id,
            consent_type=ConsentType.READING_HISTORY_TRACKING,
            status=ConsentStatus.GRANTED,
            method=ConsentMethod.WEB_FORM,
            policy_version="2.1",
            ip_address="10.0.0.1",
            user_agent="LibraryApp/2.0",
            details={
                "checkbox_label": "I agree to have my reading history tracked for personalized recommendations",
                "page_url": "/settings/privacy",
                "timestamp_utc": now.isoformat(),
            },
        )
        db.add(consent)
        await db.commit()
        await db.refresh(consent)

        # Verify we can produce proof of consent
        assert consent.consent_type == ConsentType.READING_HISTORY_TRACKING
        assert consent.status == ConsentStatus.GRANTED
        assert consent.ip_address is not None
        assert consent.policy_version == "2.1"
        assert consent.details["checkbox_label"] is not None

    async def test_audit_log_created_for_export(self, db: AsyncSession, patron: User):
        """An audit log entry is created when data is exported."""
        audit = AuditLog(
            admin_id=None,
            target_user_id=patron.id,
            action=AuditAction.GDPR_DATA_EXPORTED,
            details={
                "export_type": "complete",
                "record_counts": {
                    "consent_records": 3,
                    "data_sharing_log": 1,
                    "data_corrections": 2,
                },
            },
        )
        db.add(audit)
        await db.commit()

        result = await db.execute(
            select(AuditLog).where(
                AuditLog.target_user_id == patron.id,
                AuditLog.action == AuditAction.GDPR_DATA_EXPORTED,
            )
        )
        log = result.scalar_one()
        assert log.details["export_type"] == "complete"
        assert log.details["record_counts"]["consent_records"] == 3

    async def test_law_enforcement_export_creates_sharing_log(self, db: AsyncSession, patron: User, staff_user: User):
        """Law enforcement data export automatically creates a DataSharingLog entry."""
        # Simulate what LawEnforcementService.export_patron_data now does:
        # After exporting patron data, it auto-creates a DataSharingLog record
        sharing_log = DataSharingLog(
            user_id=patron.id,
            recipient_name="Springfield PD",
            recipient_type="law_enforcement",
            purpose=DataSharingPurpose.LAW_ENFORCEMENT_REQUEST,
            data_categories=["profile", "checkouts", "fines"],
            legal_basis="court_order",
            reference_id="42",
            reference_type="law_enforcement_request",
            patron_notified=False,
            shared_by_staff_id=staff_user.id,
            notes="Data exported for law enforcement request LE-2026-ABC123",
        )
        db.add(sharing_log)
        await db.commit()
        await db.refresh(sharing_log)

        # Verify auto-log was created with correct fields
        result = await db.execute(
            select(DataSharingLog).where(
                DataSharingLog.user_id == patron.id,
                DataSharingLog.purpose == DataSharingPurpose.LAW_ENFORCEMENT_REQUEST,
            )
        )
        log = result.scalar_one()
        assert log.recipient_type == "law_enforcement"
        assert log.reference_type == "law_enforcement_request"
        assert "profile" in log.data_categories
        assert "checkouts" in log.data_categories
        assert log.shared_by_staff_id == staff_user.id


# =============================================================================
# Router Registration Tests
# =============================================================================


class TestRouterRegistration:
    """Tests that privacy router is properly registered in the app.

    `app/api/v1/privacy.py` doesn't exist any more -- the 2026-07-01 god-file
    split (see docs/.../project_l30_god_file_audit_wave_2026_07_01) broke it
    into the app/api/v1/privacy/ package (children, data_export,
    account_deletion, staff_deletion, consent, data_correction,
    patron_data_controls submodules combined under one APIRouter in
    privacy/__init__.py), and registry.py registers everything for a
    router group inline in one register_all_routers() function rather than
    per-domain register_*_routers() helpers. These tests used to assert on
    that literal old source text; they now assert on the actual live
    routes instead, which is robust to how the registration is implemented.
    """

    def test_privacy_router_registered_in_registry(self):
        """The privacy package's router is mounted on the live app."""
        from app.main import app

        privacy_paths = [
            route.path for route in app.routes if getattr(route, "path", "").startswith("/api/v1/privacy")
        ]
        assert privacy_paths, "no /api/v1/privacy routes registered on the app"

    def test_privacy_router_has_endpoints(self):
        """Privacy router package exposes the expected endpoint paths."""
        from app.api.v1.privacy import router

        paths = {route.path for route in router.routes}

        # Core GDPR endpoints
        assert "/privacy/export" in paths
        # New privacy ledger endpoints
        assert "/privacy/consent-records" in paths
        assert "/privacy/data-sharing" in paths
        assert "/privacy/correct" in paths
        assert "/privacy/deletion-verification" in paths
        assert "/privacy/export/complete" in paths
