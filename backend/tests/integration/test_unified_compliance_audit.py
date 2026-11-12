# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for the Unified Compliance Audit API endpoints.

Tests cover:
- Compliance officer dashboard
- Requirement CRUD and verification
- Audit trail querying and integrity verification
- Compliance scanning
- Violation management
- Retention rule management
- Staff access log querying
- Incident reporting and status workflow
- Report generation and retrieval
- Role-based access control (staff vs admin)
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.unified_compliance_audit import (
    UnifiedComplianceRequirement as ComplianceRequirement,
    ComplianceViolation, ComplianceIncident,
    ComplianceReport, ImmutableAuditEntry, RetentionPolicyRule,
    StaffAccessLog,
    RegulationType, RequirementStatus, VerificationMethod,
    ViolationSeverity, ViolationStatus,
    IncidentCategory, ComplianceIncidentSeverity, IncidentStatus,
    DataCategory, AccessType, RetentionAction,
    ReportType, ReportStatus,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def compliance_requirement(test_db, test_admin):
    """Create a test compliance requirement."""
    req = ComplianceRequirement(
        organization_id=1,  # User has no organization_id -- single-tenant app
        regulation_type=RegulationType.CIPA,
        requirement_code="CIPA-001",
        requirement_title="Internet content filtering for minors",
        requirement_description="Library must filter internet content on computers accessible to minors per CIPA requirements",
        applies_to_minors=True,
        status=RequirementStatus.implemented,
        implementation_description="ContentFilter v3.2 deployed on all public terminals",
        implementation_date=date(2025, 6, 1),
        verification_method=VerificationMethod.automated_scan,
        verification_frequency_days=30,
        last_verified_date=date(2026, 1, 1),
        next_verification_due=date(2026, 1, 31),
        risk_if_non_compliant="Loss of E-Rate funding; potential CIPA violation",
        is_active=True,
    )
    test_db.add(req)
    await test_db.commit()
    await test_db.refresh(req)
    return req


@pytest.fixture
async def compliance_violation(test_db, compliance_requirement):
    """Create a test compliance violation."""
    violation = ComplianceViolation(
        organization_id=compliance_requirement.organization_id,
        requirement_id=compliance_requirement.id,
        title="Content filter bypass detected",
        description="Staff member bypassed content filter without authorization",
        severity=ViolationSeverity.high,
        status=ViolationStatus.detected,
        detected_by="automated_scan",
        detection_method="scheduled_compliance_scan",
        scan_id="scan-test123",
        affected_records_count=1,
        involves_minors=True,
    )
    test_db.add(violation)
    await test_db.commit()
    await test_db.refresh(violation)
    return violation


@pytest.fixture
async def compliance_incident(test_db, test_admin):
    """Create a test compliance incident."""
    incident = ComplianceIncident(
        organization_id=1,  # User has no organization_id -- single-tenant app
        incident_number="INC-20260207-TEST01",
        category=IncidentCategory.unauthorized_access,
        severity=ComplianceIncidentSeverity.major,
        status=IncidentStatus.reported,
        title="Unauthorized patron record access",
        description="Staff accessed patron records outside scope of duties",
        discovery_date=datetime.now(timezone.utc),
        reported_by_id=test_admin.id,
        affected_records_count=5,
        involves_minors=False,
    )
    test_db.add(incident)
    await test_db.commit()
    await test_db.refresh(incident)
    return incident


@pytest.fixture
async def audit_entries(test_db, test_admin):
    """Create a chain of test audit entries."""
    from app.services.unified_compliance_service import UnifiedComplianceService

    org_id = 1  # User has no organization_id -- single-tenant app
    entries = []
    for i in range(3):
        entry = await UnifiedComplianceService.create_audit_entry(
            db=test_db,
            organization_id=org_id,
            actor_id=test_admin.id,
            actor_role="ADMIN",
            actor_email=test_admin.email,
            action=f"test_action_{i}",
            action_category="testing",
            resource_type="test_resource",
            resource_id=str(i),
        )
        entries.append(entry)
    await test_db.commit()
    return entries


@pytest.fixture
async def retention_rule(test_db, test_admin):
    """Create a test retention policy rule."""
    rule = RetentionPolicyRule(
        organization_id=1,  # User has no organization_id -- single-tenant app
        rule_name="Delete old checkout history",
        rule_description="Remove checkout records older than 3 years",
        data_category=DataCategory.checkout_history,
        target_table="checkouts",
        retention_days=1095,
        retention_basis="State library records retention schedule",
        expiry_action=RetentionAction.delete,
        regulation_type=RegulationType.STATE_LIBRARY,
        is_active=True,
        execution_frequency_hours=24,
        approved_by_id=test_admin.id,
        approved_at=datetime.now(timezone.utc),
    )
    test_db.add(rule)
    await test_db.commit()
    await test_db.refresh(rule)
    return rule


@pytest.fixture
async def staff_access_entries(test_db, test_staff, test_patron):
    """Create test staff access log entries."""
    entries = []
    for i in range(3):
        entry = StaffAccessLog(
            organization_id=1,  # User has no organization_id -- single-tenant app
            staff_id=test_staff.id,
            staff_role="STAFF",
            access_type=AccessType.view,
            data_category=DataCategory.patron_pii,
            resource_type="patron",
            resource_id=str(test_patron.id),
            target_patron_id=test_patron.id,
            records_accessed_count=1,
            is_flagged=(i == 2),
            flag_reason="Test flag" if i == 2 else None,
        )
        test_db.add(entry)
        entries.append(entry)
    await test_db.commit()
    for e in entries:
        await test_db.refresh(e)
    return entries


def _get_admin_headers(test_admin):
    """Generate auth headers for admin user."""
    from app.core.security import create_access_token
    token = create_access_token(subject=test_admin.id, email=test_admin.email)
    return {"Authorization": f"Bearer {token}"}


def _get_staff_headers(test_staff):
    """Generate auth headers for staff user."""
    from app.core.security import create_access_token
    token = create_access_token(subject=test_staff.id, email=test_staff.email)
    return {"Authorization": f"Bearer {token}"}


def _get_patron_headers(test_patron):
    """Generate auth headers for patron user."""
    from app.core.security import create_access_token
    token = create_access_token(subject=test_patron.id, email=test_patron.email)
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Dashboard Tests
# =============================================================================

class TestComplianceDashboard:
    """Tests for the compliance officer dashboard endpoint."""

    async def test_dashboard_returns_200_for_staff(
        self, client, test_staff
    ):
        """Staff should be able to access the dashboard."""
        headers = _get_staff_headers(test_staff)
        response = await client.get("/api/v1/unified-compliance/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert "compliance_score" in data
        assert "requirements" in data
        assert "violations" in data
        assert "incidents" in data
        assert "staff_access" in data
        assert "law_enforcement" in data
        assert "upcoming_deadlines" in data

    async def test_dashboard_returns_401_without_auth(self, client):
        """Unauthenticated requests should be rejected."""
        response = await client.get("/api/v1/unified-compliance/dashboard")
        assert response.status_code in (401, 403)

    async def test_dashboard_returns_403_for_patron(
        self, client, test_patron
    ):
        """Patrons should not be able to access the dashboard."""
        headers = _get_patron_headers(test_patron)
        response = await client.get("/api/v1/unified-compliance/dashboard", headers=headers)
        assert response.status_code == 403


# =============================================================================
# Requirements Tests
# =============================================================================

class TestComplianceRequirements:
    """Tests for compliance requirement CRUD."""

    async def test_list_requirements_empty(self, client, test_staff):
        """Empty requirements list should return valid response."""
        headers = _get_staff_headers(test_staff)
        response = await client.get("/api/v1/unified-compliance/requirements", headers=headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 0

    async def test_create_requirement_as_admin(self, client, test_admin):
        """Admin should be able to create a compliance requirement."""
        headers = _get_admin_headers(test_admin)
        response = await client.post(
            "/api/v1/unified-compliance/requirements",
            headers=headers,
            json={
                "regulation_type": "coppa",
                "requirement_code": "COPPA-001",
                "requirement_title": "Parental consent for minors under 13",
                "requirement_description": "Obtain verifiable parental consent before collecting personal information from children under 13",
                "applies_to_minors": True,
                "verification_frequency_days": 90,
            },
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] > 0

    async def test_create_requirement_as_staff_fails(self, client, test_staff):
        """Staff (non-admin) should not be able to create requirements."""
        headers = _get_staff_headers(test_staff)
        response = await client.post(
            "/api/v1/unified-compliance/requirements",
            headers=headers,
            json={
                "regulation_type": "cipa",
                "requirement_code": "TEST-001",
                "requirement_title": "Test",
                "requirement_description": "Test requirement",
            },
        )
        assert response.status_code == 403

    async def test_list_requirements_with_filter(
        self, client, test_staff, compliance_requirement
    ):
        """Requirements can be filtered by regulation type."""
        headers = _get_staff_headers(test_staff)
        response = await client.get(
            "/api/v1/unified-compliance/requirements",
            headers=headers,
            params={"regulation_type": "cipa"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["regulation_type"] == "cipa"

    async def test_verify_requirement(
        self, client, test_staff, compliance_requirement
    ):
        """Staff should be able to verify a requirement."""
        headers = _get_staff_headers(test_staff)
        response = await client.post(
            f"/api/v1/unified-compliance/requirements/{compliance_requirement.id}/verify",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "next_verification_due" in data

    async def test_verify_nonexistent_requirement_returns_404(
        self, client, test_staff
    ):
        """Verifying non-existent requirement should return 404."""
        headers = _get_staff_headers(test_staff)
        response = await client.post(
            "/api/v1/unified-compliance/requirements/99999/verify",
            headers=headers,
        )
        assert response.status_code == 404


# =============================================================================
# Audit Trail Tests
# =============================================================================

class TestAuditTrail:
    """Tests for the immutable audit trail."""

    async def test_query_audit_trail(self, client, test_staff, audit_entries):
        """Staff should be able to query the audit trail."""
        headers = _get_staff_headers(test_staff)
        response = await client.get(
            "/api/v1/unified-compliance/audit-trail",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "items" in data
        assert "total" in data

    async def test_audit_trail_entries_have_hash(
        self, client, test_staff, audit_entries
    ):
        """Audit trail entries should include truncated hash."""
        headers = _get_staff_headers(test_staff)
        response = await client.get(
            "/api/v1/unified-compliance/audit-trail",
            headers=headers,
        )
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        if items:
            assert "entry_hash" in items[0]
            assert items[0]["entry_hash"].endswith("...")

    async def test_verify_audit_integrity_admin_only(
        self, client, test_admin, test_staff, audit_entries
    ):
        """Only admin should be able to verify audit integrity."""
        # Admin should work
        admin_headers = _get_admin_headers(test_admin)
        response = await client.get(
            "/api/v1/unified-compliance/audit-trail/verify-integrity",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "valid" in data
        assert "entries_checked" in data

        # Staff should fail
        staff_headers = _get_staff_headers(test_staff)
        response = await client.get(
            "/api/v1/unified-compliance/audit-trail/verify-integrity",
            headers=staff_headers,
        )
        assert response.status_code == 403


# =============================================================================
# Compliance Scan Tests
# =============================================================================

class TestComplianceScan:
    """Tests for automated compliance scanning."""

    async def test_scan_requires_admin(self, client, test_staff):
        """Scanning should require admin role."""
        headers = _get_staff_headers(test_staff)
        response = await client.post(
            "/api/v1/unified-compliance/scan",
            headers=headers,
        )
        assert response.status_code == 403

    async def test_scan_returns_results(self, client, test_admin):
        """Admin should be able to run a compliance scan."""
        headers = _get_admin_headers(test_admin)
        response = await client.post(
            "/api/v1/unified-compliance/scan",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "scan_id" in data
        assert "violations_found" in data
        assert "violations" in data
        assert data["scan_id"].startswith("scan-")


# =============================================================================
# Violation Tests
# =============================================================================

class TestViolations:
    """Tests for compliance violation management."""

    async def test_list_violations(
        self, client, test_staff, compliance_violation
    ):
        """Staff should be able to list violations."""
        headers = _get_staff_headers(test_staff)
        response = await client.get(
            "/api/v1/unified-compliance/violations",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] >= 1

    async def test_list_violations_filter_by_severity(
        self, client, test_staff, compliance_violation
    ):
        """Violations can be filtered by severity."""
        headers = _get_staff_headers(test_staff)
        response = await client.get(
            "/api/v1/unified-compliance/violations",
            headers=headers,
            params={"severity": "high"},
        )
        assert response.status_code == 200
        for item in response.json()["data"]["items"]:
            assert item["severity"] == "high"

    async def test_update_violation_status(
        self, client, test_staff, compliance_violation
    ):
        """Staff should be able to update violation status."""
        headers = _get_staff_headers(test_staff)
        response = await client.put(
            f"/api/v1/unified-compliance/violations/{compliance_violation.id}",
            headers=headers,
            json={
                "status": "investigating",
                "remediation_plan": "Review filter configuration",
            },
        )
        assert response.status_code == 200


# =============================================================================
# Retention Rule Tests
# =============================================================================

class TestRetentionRules:
    """Tests for data retention policy rules."""

    async def test_list_retention_rules(self, client, test_staff, retention_rule):
        """Staff should be able to list retention rules."""
        headers = _get_staff_headers(test_staff)
        response = await client.get(
            "/api/v1/unified-compliance/retention-rules",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] >= 1

    async def test_create_retention_rule_as_admin(self, client, test_admin):
        """Admin should be able to create retention rules."""
        headers = _get_admin_headers(test_admin)
        response = await client.post(
            "/api/v1/unified-compliance/retention-rules",
            headers=headers,
            json={
                "rule_name": "Anonymize old reading history",
                "data_category": "reading_history",
                "target_table": "reading_log_entries",
                "retention_days": 365,
                "expiry_action": "anonymize",
                "regulation_type": "state_privacy",
                "execution_frequency_hours": 48,
            },
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] > 0

    async def test_enforce_retention_requires_admin(self, client, test_staff):
        """Retention enforcement should require admin role."""
        headers = _get_staff_headers(test_staff)
        response = await client.post(
            "/api/v1/unified-compliance/retention-rules/enforce",
            headers=headers,
        )
        assert response.status_code == 403


# =============================================================================
# Staff Access Log Tests
# =============================================================================

class TestStaffAccessLogs:
    """Tests for staff data access log querying."""

    async def test_query_staff_access_requires_admin(
        self, client, test_staff
    ):
        """Staff access logs should require admin role."""
        headers = _get_staff_headers(test_staff)
        response = await client.get(
            "/api/v1/unified-compliance/staff-access",
            headers=headers,
        )
        assert response.status_code == 403

    async def test_query_staff_access_as_admin(
        self, client, test_admin, staff_access_entries
    ):
        """Admin should be able to query staff access logs."""
        headers = _get_admin_headers(test_admin)
        response = await client.get(
            "/api/v1/unified-compliance/staff-access",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "items" in data
        assert "total" in data

    async def test_staff_access_summary_as_admin(
        self, client, test_admin, staff_access_entries
    ):
        """Admin should be able to get staff access summary."""
        headers = _get_admin_headers(test_admin)
        response = await client.get(
            "/api/v1/unified-compliance/staff-access/summary",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "total_accesses" in data
        assert "by_category" in data

    async def test_filter_flagged_access(
        self, client, test_admin, staff_access_entries
    ):
        """Admin should be able to filter for flagged accesses."""
        headers = _get_admin_headers(test_admin)
        response = await client.get(
            "/api/v1/unified-compliance/staff-access",
            headers=headers,
            params={"is_flagged": True},
        )
        assert response.status_code == 200
        for item in response.json()["data"]["items"]:
            assert item["is_flagged"] is True


# =============================================================================
# Incident Tests
# =============================================================================

class TestIncidents:
    """Tests for compliance incident reporting and management."""

    async def test_list_incidents(self, client, test_staff, compliance_incident):
        """Staff should be able to list incidents."""
        headers = _get_staff_headers(test_staff)
        response = await client.get(
            "/api/v1/unified-compliance/incidents",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] >= 1

    async def test_create_incident(self, client, test_staff):
        """Staff should be able to report an incident."""
        headers = _get_staff_headers(test_staff)
        response = await client.post(
            "/api/v1/unified-compliance/incidents",
            headers=headers,
            json={
                "category": "policy_violation",
                "severity": "minor",
                "title": "Staff used personal email for patron communication",
                "description": "Staff member sent patron information via personal Gmail",
                "affected_records_count": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["incident_number"].startswith("INC-")

    async def test_update_incident_status(
        self, client, test_staff, compliance_incident
    ):
        """Staff should be able to update incident status."""
        headers = _get_staff_headers(test_staff)
        response = await client.put(
            f"/api/v1/unified-compliance/incidents/{compliance_incident.id}/status",
            headers=headers,
            json={
                "status": "investigating",
                "notes": "Reviewing access logs for the affected patron records",
            },
        )
        assert response.status_code == 200


# =============================================================================
# Report Tests
# =============================================================================

class TestReports:
    """Tests for compliance report generation."""

    async def test_generate_report_requires_admin(self, client, test_staff):
        """Report generation should require admin role."""
        headers = _get_staff_headers(test_staff)
        response = await client.post(
            "/api/v1/unified-compliance/reports/generate",
            headers=headers,
            json={
                "report_type": "board_executive",
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
            },
        )
        assert response.status_code == 403

    async def test_generate_board_executive_report(self, client, test_admin):
        """Admin should be able to generate a board executive report."""
        headers = _get_admin_headers(test_admin)
        response = await client.post(
            "/api/v1/unified-compliance/reports/generate",
            headers=headers,
            json={
                "report_type": "board_executive",
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "id" in data
        assert "title" in data
        assert "compliance_score" in data

    async def test_list_reports(self, client, test_staff):
        """Staff should be able to list reports."""
        headers = _get_staff_headers(test_staff)
        response = await client.get(
            "/api/v1/unified-compliance/reports",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "items" in data
        assert "total" in data

    async def test_get_report_detail(self, client, test_admin):
        """Generated report should be retrievable by ID."""
        headers = _get_admin_headers(test_admin)

        # Generate a report first
        gen_response = await client.post(
            "/api/v1/unified-compliance/reports/generate",
            headers=headers,
            json={
                "report_type": "incident_summary",
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
            },
        )
        assert gen_response.status_code == 200
        report_id = gen_response.json()["data"]["id"]

        # Retrieve it
        response = await client.get(
            f"/api/v1/unified-compliance/reports/{report_id}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == report_id
        assert data["report_type"] == "incident_summary"
        assert "report_data" in data

    async def test_get_nonexistent_report_returns_404(self, client, test_staff):
        """Requesting non-existent report should return 404."""
        headers = _get_staff_headers(test_staff)
        response = await client.get(
            "/api/v1/unified-compliance/reports/99999",
            headers=headers,
        )
        assert response.status_code == 404
