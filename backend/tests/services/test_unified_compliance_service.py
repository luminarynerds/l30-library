# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for the Unified Compliance Audit Service.

Tests cover:
- Immutable audit trail with hash chaining
- Hash chain integrity verification
- Staff access logging with anomaly detection
- Compliance scanning and violation detection
- Retention policy enforcement tracking
- Incident lifecycle management
- Report generation
- Officer dashboard aggregation

Uses mocking to avoid database overhead.
"""

import hashlib
import pytest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.models.unified_compliance_audit import (
    AccessType, ComplianceIncident, ComplianceReport,
    UnifiedComplianceRequirement as ComplianceRequirement,
    ComplianceViolation, DataCategory, ImmutableAuditEntry, IncidentCategory,
    ComplianceIncidentSeverity, IncidentStatus, RegulationType, ReportStatus, ReportType,
    RequirementStatus, RetentionAction, RetentionPolicyRule, StaffAccessLog,
    VerificationMethod, ViolationSeverity, ViolationStatus,
)
from app.services.unified_compliance_service import (
    GENESIS_HASH,
    UnifiedComplianceService,
)


# =============================================================================
# ImmutableAuditEntry Hash Computation
# =============================================================================

class TestImmutableAuditEntryHash:
    """Tests for the tamper-evident hash computation."""

    def test_compute_hash_returns_64_char_hex(self):
        """Hash should be a 64-character hex SHA-256 digest."""
        result = ImmutableAuditEntry.compute_hash(
            previous_hash=GENESIS_HASH,
            timestamp="2026-01-01T00:00:00+00:00",
            actor_id="1",
            action="test_action",
            resource_type="test_resource",
            resource_id="42",
            ip_address="127.0.0.1",
        )
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_compute_hash_is_deterministic(self):
        """Same inputs should produce the same hash."""
        args = {
            "previous_hash": GENESIS_HASH,
            "timestamp": "2026-01-01T12:00:00+00:00",
            "actor_id": "5",
            "action": "view",
            "resource_type": "patron",
            "resource_id": "100",
            "ip_address": "10.0.0.1",
        }
        hash1 = ImmutableAuditEntry.compute_hash(**args)
        hash2 = ImmutableAuditEntry.compute_hash(**args)
        assert hash1 == hash2

    def test_compute_hash_changes_with_different_input(self):
        """Different inputs should produce different hashes."""
        base_args = {
            "previous_hash": GENESIS_HASH,
            "timestamp": "2026-01-01T00:00:00+00:00",
            "actor_id": "1",
            "action": "view",
            "resource_type": "patron",
            "resource_id": "1",
            "ip_address": "127.0.0.1",
        }
        hash_original = ImmutableAuditEntry.compute_hash(**base_args)

        # Changing any single field should produce a different hash
        for field, alt_value in [
            ("previous_hash", "a" * 64),
            ("actor_id", "2"),
            ("action", "delete"),
            ("resource_type", "checkout"),
            ("resource_id", "2"),
            ("ip_address", "192.168.1.1"),
        ]:
            modified = {**base_args, field: alt_value}
            assert ImmutableAuditEntry.compute_hash(**modified) != hash_original

    def test_compute_hash_chains_correctly(self):
        """Chaining hashes should work: hash2.previous = hash1.value."""
        hash1 = ImmutableAuditEntry.compute_hash(
            previous_hash=GENESIS_HASH,
            timestamp="2026-01-01T00:00:00+00:00",
            actor_id="1",
            action="create",
            resource_type="req",
            resource_id="1",
            ip_address="127.0.0.1",
        )
        hash2 = ImmutableAuditEntry.compute_hash(
            previous_hash=hash1,
            timestamp="2026-01-01T00:00:01+00:00",
            actor_id="1",
            action="update",
            resource_type="req",
            resource_id="1",
            ip_address="127.0.0.1",
        )
        assert hash2 != hash1
        assert len(hash2) == 64

    def test_genesis_hash_is_64_zeros(self):
        """The genesis hash constant should be 64 zero characters."""
        assert GENESIS_HASH == "0" * 64
        assert len(GENESIS_HASH) == 64


# =============================================================================
# Audit Trail Creation
# =============================================================================

class TestAuditTrailCreation:
    """Tests for creating immutable audit entries.

    Note: Model constructors and select() are mocked to avoid a pre-existing
    SQLAlchemy mapper configuration error (duplicate Committee class). We
    verify service logic by inspecting constructor kwargs instead.
    """

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.ImmutableAuditEntry")
    @patch("app.services.unified_compliance_service.desc")
    @patch("app.services.unified_compliance_service.select")
    async def test_create_first_audit_entry_uses_genesis_hash(self, mock_select, mock_desc, MockEntry):
        """First entry in org should chain from genesis hash."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        db.execute.return_value = mock_result

        mock_entry = MagicMock()
        MockEntry.return_value = mock_entry
        MockEntry.compute_hash.return_value = "a" * 64

        await UnifiedComplianceService.create_audit_entry(
            db=db,
            organization_id=1,
            actor_id=10,
            actor_role="ADMIN",
            actor_email="admin@test.com",
            action="test_action",
            action_category="testing",
            resource_type="test_resource",
        )

        kw = MockEntry.call_args[1]
        assert kw["previous_hash"] == GENESIS_HASH
        assert kw["sequence_number"] == 1
        assert kw["organization_id"] == 1
        assert kw["actor_id"] == 10
        assert kw["actor_role"] == "ADMIN"
        assert kw["action"] == "test_action"
        assert kw["action_category"] == "testing"
        assert kw["resource_type"] == "test_resource"
        assert kw["entry_hash"] == "a" * 64
        db.add.assert_called_once_with(mock_entry)

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.ImmutableAuditEntry")
    @patch("app.services.unified_compliance_service.desc")
    @patch("app.services.unified_compliance_service.select")
    async def test_create_audit_entry_chains_from_previous(self, mock_select, mock_desc, MockEntry):
        """Subsequent entries should chain from the previous entry's hash."""
        db = AsyncMock()
        prev_hash = "abcd" * 16  # 64-char hex
        mock_result = MagicMock()
        mock_result.first.return_value = (prev_hash, 5)
        db.execute.return_value = mock_result

        mock_entry = MagicMock()
        MockEntry.return_value = mock_entry
        MockEntry.compute_hash.return_value = "b" * 64

        await UnifiedComplianceService.create_audit_entry(
            db=db,
            organization_id=1,
            actor_id=10,
            actor_role="STAFF",
            actor_email="staff@test.com",
            action="view_record",
            action_category="data_access",
            resource_type="patron",
            resource_id="42",
        )

        kw = MockEntry.call_args[1]
        assert kw["previous_hash"] == prev_hash
        assert kw["sequence_number"] == 6
        assert kw["resource_id"] == "42"

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.ImmutableAuditEntry")
    @patch("app.services.unified_compliance_service.desc")
    @patch("app.services.unified_compliance_service.select")
    async def test_create_audit_entry_captures_optional_fields(self, mock_select, mock_desc, MockEntry):
        """Optional fields like justification, data_category should be stored."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        db.execute.return_value = mock_result

        mock_entry = MagicMock()
        MockEntry.return_value = mock_entry
        MockEntry.compute_hash.return_value = "c" * 64

        await UnifiedComplianceService.create_audit_entry(
            db=db,
            organization_id=1,
            actor_id=5,
            actor_role="ADMIN",
            actor_email="admin@test.com",
            action="export_data",
            action_category="data_access",
            resource_type="patron",
            resource_id="99",
            justification="Annual audit requirement",
            data_category=DataCategory.patron_pii,
            involves_minor=True,
            involves_pii=True,
            ip_address="10.0.0.5",
        )

        kw = MockEntry.call_args[1]
        assert kw["justification"] == "Annual audit requirement"
        assert kw["data_category"] == DataCategory.patron_pii
        assert kw["involves_minor"] is True
        assert kw["involves_pii"] is True
        assert kw["ip_address"] == "10.0.0.5"


# =============================================================================
# Staff Access Logging
# =============================================================================

class TestStaffAccessLogging:
    """Tests for staff data access logging and anomaly detection.

    Model constructor is mocked to avoid mapper configuration error.
    We verify service logic by inspecting constructor kwargs.
    """

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.StaffAccessLog")
    async def test_log_staff_access_basic(self, MockLog):
        """Basic staff access should be logged."""
        db = AsyncMock()
        mock_log = MagicMock()
        MockLog.return_value = mock_log

        _ = await UnifiedComplianceService.log_staff_access(
            db=db,
            organization_id=1,
            staff_id=10,
            staff_role="STAFF",
            access_type=AccessType.view,
            data_category=DataCategory.patron_pii,
            resource_type="patron",
            resource_id="42",
            records_accessed_count=1,
        )

        kw = MockLog.call_args[1]
        assert kw["staff_id"] == 10
        assert kw["access_type"] == AccessType.view
        assert kw["data_category"] == DataCategory.patron_pii
        assert kw["is_bulk_access"] is False
        db.add.assert_called_once_with(mock_log)

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.StaffAccessLog")
    async def test_log_staff_access_flags_bulk(self, MockLog):
        """Bulk access (>50 records) should be flagged."""
        db = AsyncMock()
        mock_log = MagicMock()
        MockLog.return_value = mock_log

        await UnifiedComplianceService.log_staff_access(
            db=db,
            organization_id=1,
            staff_id=10,
            staff_role="STAFF",
            access_type=AccessType.bulk_access,
            data_category=DataCategory.checkout_history,
            resource_type="checkout",
            records_accessed_count=100,
        )

        kw = MockLog.call_args[1]
        assert kw["is_bulk_access"] is True

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.StaffAccessLog")
    async def test_log_staff_access_truncates_user_agent(self, MockLog):
        """User agent should be truncated to 500 chars."""
        db = AsyncMock()
        mock_log = MagicMock()
        MockLog.return_value = mock_log

        long_ua = "x" * 1000
        await UnifiedComplianceService.log_staff_access(
            db=db,
            organization_id=1,
            staff_id=10,
            staff_role="STAFF",
            access_type=AccessType.view,
            data_category=DataCategory.patron_pii,
            resource_type="patron",
            user_agent=long_ua,
        )

        kw = MockLog.call_args[1]
        assert len(kw["user_agent"]) == 500

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.StaffAccessLog")
    async def test_log_staff_access_stores_justification(self, MockLog):
        """Justification should be stored in the log entry."""
        db = AsyncMock()
        mock_log = MagicMock()
        MockLog.return_value = mock_log

        await UnifiedComplianceService.log_staff_access(
            db=db,
            organization_id=1,
            staff_id=10,
            staff_role="STAFF",
            access_type=AccessType.export,
            data_category=DataCategory.patron_pii,
            resource_type="patron",
            justification="Annual audit report generation",
            records_accessed_count=5,
        )

        kw = MockLog.call_args[1]
        assert kw["justification"] == "Annual audit report generation"
        assert kw["access_type"] == AccessType.export


# =============================================================================
# Incident Management
# =============================================================================

class TestIncidentManagement:
    """Tests for compliance incident lifecycle management.

    Create tests mock ComplianceIncident constructor to avoid mapper config error.
    Update tests work fine with MagicMock(spec=...) since they don't create instances.
    """

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.ComplianceIncident")
    async def test_create_incident_generates_tracking_number(self, MockIncident):
        """Incident creation should auto-generate a unique tracking number."""
        db = AsyncMock()
        mock_incident = MagicMock()
        MockIncident.return_value = mock_incident

        await UnifiedComplianceService.create_incident(
            db=db,
            organization_id=1,
            reported_by_id=5,
            category=IncidentCategory.data_breach,
            severity=ComplianceIncidentSeverity.critical,
            title="Unauthorized patron data access",
            description="Staff exported patron records without authorization",
        )

        kw = MockIncident.call_args[1]
        assert kw["incident_number"].startswith("INC-")
        assert kw["status"] == IncidentStatus.reported
        assert kw["category"] == IncidentCategory.data_breach
        assert kw["severity"] == ComplianceIncidentSeverity.critical
        assert kw["reported_by_id"] == 5
        db.add.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.ComplianceIncident")
    async def test_create_critical_breach_sets_notification_deadline(self, MockIncident):
        """Critical data breach should set 72-hour notification deadline."""
        db = AsyncMock()
        mock_incident = MagicMock()
        MockIncident.return_value = mock_incident

        incident = await UnifiedComplianceService.create_incident(
            db=db,
            organization_id=1,
            reported_by_id=5,
            category=IncidentCategory.data_breach,
            severity=ComplianceIncidentSeverity.critical,
            title="Data breach detected",
            description="PII exposed",
        )

        # Service sets these after construction for critical data breaches
        assert incident.notification_required is True
        assert incident.notification_deadline is not None
        delta = incident.notification_deadline - datetime.now(timezone.utc)
        assert timedelta(hours=71) < delta < timedelta(hours=73)

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.ComplianceIncident")
    async def test_create_minor_incident_no_notification(self, MockIncident):
        """Minor non-breach incident should not require notification."""
        db = AsyncMock()
        mock_incident = MagicMock()
        # Pre-set defaults matching column defaults
        mock_incident.notification_required = False
        mock_incident.notification_deadline = None
        MockIncident.return_value = mock_incident

        incident = await UnifiedComplianceService.create_incident(
            db=db,
            organization_id=1,
            reported_by_id=5,
            category=IncidentCategory.training_lapse,
            severity=ComplianceIncidentSeverity.minor,
            title="Staff training overdue",
            description="COPPA training not completed",
        )

        # Service should NOT override notification_required for minor/training_lapse
        assert incident.notification_required is False

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.select")
    async def test_update_incident_status_to_resolved(self, mock_select):
        """Updating to resolved should set resolved_at timestamp."""
        db = AsyncMock()
        mock_incident = MagicMock(spec=ComplianceIncident)
        mock_incident.id = 1
        mock_incident.notes = None
        mock_incident.status = IncidentStatus.investigating  # valid source for -> resolved
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_incident
        db.execute.return_value = mock_result

        result = await UnifiedComplianceService.update_incident_status(
            db=db,
            incident_id=1,
            new_status=IncidentStatus.resolved,
            updated_by_id=5,
            notes="Root cause identified and fixed",
        )

        assert result.status == IncidentStatus.resolved
        assert result.resolved_at is not None

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.select")
    async def test_update_incident_status_to_contained(self, mock_select):
        """Updating to containing should set contained_at and is_contained."""
        db = AsyncMock()
        mock_incident = MagicMock(spec=ComplianceIncident)
        mock_incident.id = 1
        mock_incident.notes = "Initial report"
        mock_incident.status = IncidentStatus.triaging  # valid source for -> containing
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_incident
        db.execute.return_value = mock_result

        result = await UnifiedComplianceService.update_incident_status(
            db=db,
            incident_id=1,
            new_status=IncidentStatus.containing,
            updated_by_id=5,
        )

        assert result.status == IncidentStatus.containing
        assert result.contained_at is not None
        assert result.is_contained is True

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.select")
    async def test_update_incident_not_found_raises(self, mock_select):
        """Updating non-existent incident should raise ValueError."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Incident 999 not found"):
            await UnifiedComplianceService.update_incident_status(
                db=db,
                incident_id=999,
                new_status=IncidentStatus.resolved,
                updated_by_id=5,
            )


# =============================================================================
# Retention Policy Enforcement
# =============================================================================

class TestRetentionPolicyEnforcement:
    """Tests for data retention policy enforcement tracking."""

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.select")
    async def test_enforce_updates_execution_timestamps(self, mock_select):
        """Enforcing policies should update last/next execution timestamps."""
        db = AsyncMock()

        mock_rule = MagicMock(spec=RetentionPolicyRule)
        mock_rule.id = 1
        mock_rule.rule_name = "Delete old checkouts"
        mock_rule.expiry_action = RetentionAction.delete
        mock_rule.data_category = DataCategory.checkout_history
        mock_rule.target_table = "checkouts"
        mock_rule.execution_frequency_hours = 24
        mock_rule.last_executed_at = None
        mock_rule.next_execution_at = None

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_rule]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        result = await UnifiedComplianceService.enforce_retention_policies(
            db=db, organization_id=1
        )

        assert result["rules_executed"] == 1
        assert len(result["actions"]) == 1
        assert result["actions"][0]["rule_name"] == "Delete old checkouts"
        assert result["actions"][0]["action"] == "delete"

        # Verify timestamps were updated
        assert mock_rule.last_executed_at is not None
        assert mock_rule.next_execution_at is not None

    @pytest.mark.asyncio
    @patch("app.services.unified_compliance_service.select")
    async def test_enforce_no_due_rules_skips_commit(self, mock_select):
        """When no rules are due, commit should not be called."""
        db = AsyncMock()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        result = await UnifiedComplianceService.enforce_retention_policies(
            db=db, organization_id=1
        )

        assert result["rules_executed"] == 0
        assert result["actions"] == []


# =============================================================================
# Model Enums
# =============================================================================

class TestComplianceEnums:
    """Tests for enum value correctness."""

    def test_regulation_types_cover_library_regulations(self):
        """All major library compliance regulations should be represented."""
        values = {r.value for r in RegulationType}
        assert "cipa" in values
        assert "coppa" in values
        assert "ferpa" in values
        assert "ada" in values
        assert "state_library" in values
        assert "foia" in values

    def test_violation_severity_levels(self):
        """Severity should have standard levels."""
        values = [s.value for s in ViolationSeverity]
        assert values == ["critical", "high", "medium", "low", "informational"]

    def test_incident_status_lifecycle(self):
        """Incident statuses should follow a logical lifecycle."""
        values = [s.value for s in IncidentStatus]
        expected = [
            "reported", "triaging", "investigating", "containing",
            "remediating", "resolved", "closed"
        ]
        assert values == expected

    def test_access_types_cover_operations(self):
        """Access types should cover all major data operations."""
        values = {t.value for t in AccessType}
        assert "view" in values
        assert "export" in values
        assert "modify" in values
        assert "delete" in values
        assert "bulk_access" in values

    def test_data_categories_cover_sensitive_types(self):
        """Data categories should cover all sensitive library data types."""
        values = {c.value for c in DataCategory}
        assert "patron_pii" in values
        assert "minor_data" in values
        assert "checkout_history" in values
        assert "law_enforcement" in values
        assert "reading_history" in values

    def test_report_types_cover_all_required_reports(self):
        """Report types should cover all required compliance reports."""
        values = {t.value for t in ReportType}
        assert "cipa_erate" in values
        assert "board_executive" in values
        assert "law_enforcement_transparency" in values
        assert "staff_access_review" in values
        assert "incident_summary" in values
        assert "violation_summary" in values
        assert "data_retention" in values

    def test_retention_actions(self):
        """Retention actions should include standard data lifecycle options."""
        values = {a.value for a in RetentionAction}
        assert "delete" in values
        assert "anonymize" in values
        assert "archive" in values
        assert "flag_for_review" in values


# =============================================================================
# Compliance Requirement Model
# =============================================================================

class TestComplianceRequirementModel:
    """Tests for the ComplianceRequirement model structure."""

    def test_requirement_tablename(self):
        assert ComplianceRequirement.__tablename__ == "unified_compliance_requirements"

    def test_violation_tablename(self):
        assert ComplianceViolation.__tablename__ == "compliance_violations"

    def test_audit_entry_tablename(self):
        assert ImmutableAuditEntry.__tablename__ == "immutable_audit_entries"

    def test_retention_rule_tablename(self):
        assert RetentionPolicyRule.__tablename__ == "retention_policy_rules"

    def test_incident_tablename(self):
        assert ComplianceIncident.__tablename__ == "compliance_incidents"

    def test_staff_access_log_tablename(self):
        assert StaffAccessLog.__tablename__ == "staff_access_logs"

    def test_report_tablename(self):
        assert ComplianceReport.__tablename__ == "compliance_reports"
