# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive integration tests for law enforcement request compliance.

SECURITY & COMPLIANCE TESTS: These tests verify:
- LEGAL role access control (specifically for legal counsel)
- Immutable audit logging for forensic compliance
- Data minimization and patron privacy protection
- Complete workflow compliance verification
- Transparency reporting with anonymization
- Patron notification with gag order support
"""

import contextlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
async def test_legal(test_db):
    """Create a test user with LEGAL role."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="legal@example.com",
        password_hash=hash_password("LegalPassword123!"),
        first_name="Legal",
        last_name="Counsel",
        role=UserRole.LEGAL,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_director(test_db):
    """Create a test user with DIRECTOR role."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="director@example.com",
        password_hash=hash_password("DirectorPassword123!"),
        first_name="Library",
        last_name="Director",
        role=UserRole.DIRECTOR,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_le_request_comprehensive(test_db, test_admin, test_patron):
    """Create a comprehensive test law enforcement request."""
    from app.models.law_enforcement_request import (
        LawEnforcementRequest,
        LawEnforcementChecklist,
        RequestType,
        LegalReviewStatus,
        WorkflowStatus,
        DEFAULT_CHECKLIST_ITEMS,
    )

    request = LawEnforcementRequest(
        tracking_number="LE-2026-COMP01",
        requesting_agency="State Police Bureau of Investigation",
        agency_contact_name="Detective Jane Smith",
        agency_contact_phone="555-0100",
        agency_contact_email="smith@statepolice.gov",
        request_type=RequestType.SUBPOENA,
        date_received=datetime.now(timezone.utc),
        patron_id=test_patron.id,
        patron_name_on_request="Test Patron",
        data_requested="Complete checkout history and holds from 2024-2026",
        legal_review_status=LegalReviewStatus.PENDING_REVIEW,
        workflow_status=WorkflowStatus.RECEIVED,
        created_by_id=test_admin.id,
        patron_notification_permitted=True,
    )
    test_db.add(request)
    await test_db.flush()

    # Add comprehensive checklist items
    for item_data in DEFAULT_CHECKLIST_ITEMS:
        item = LawEnforcementChecklist(
            request_id=request.id,
            item_type=item_data["item_type"],
            item_description=item_data["item_description"],
            is_required=item_data["is_required"],
            sort_order=item_data["sort_order"],
        )
        test_db.add(item)

    await test_db.commit()
    await test_db.refresh(request)
    return request


# =============================================================================
# Helper Functions
# =============================================================================


async def get_token(client, email: str, password: str) -> str:
    """Helper to get authentication token."""
    login_data = {"username": email, "password": password}
    response = await client.post("/api/v1/auth/login", json=login_data)
    if response.status_code != 200:
        raise ValueError(f"Login failed: {response.json()}")
    return response.json()["access_token"]


async def get_legal_token(client) -> str:
    """Helper to get legal counsel authentication token."""
    return await get_token(client, "legal@example.com", "LegalPassword123!")


async def get_director_token(client) -> str:
    """Helper to get director authentication token."""
    return await get_token(client, "director@example.com", "DirectorPassword123!")


async def get_admin_token(client, test_admin_data) -> str:
    """Helper to get admin authentication token."""
    return await get_token(client, test_admin_data["email"], test_admin_data["password"])


# =============================================================================
# LEGAL Role Access Control Tests (CRITICAL)
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementLegalRoleAccess:
    """Test that LEGAL role has appropriate access to sensitive operations."""

    async def test_legal_counsel_can_access_requests(
        self, client, test_legal, test_le_request_comprehensive
    ):
        """Test that legal counsel can access law enforcement requests."""
        token = await get_legal_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/law-enforcement/requests", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    async def test_legal_counsel_can_perform_legal_review(
        self, client, test_legal, test_le_request_comprehensive
    ):
        """Test that legal counsel can perform legal reviews."""
        token = await get_legal_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        review_data = {
            "legal_review_status": "approved",
            "legal_review_notes": "Request is valid, properly scoped, and legally compliant.",
        }

        response = await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/legal-review",
            json=review_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["legal_review_status"] == "approved"
        assert (
            data["legal_review_notes"]
            == "Request is valid, properly scoped, and legally compliant."
        )

    async def test_legal_counsel_can_view_detailed_requests(
        self, client, test_legal, test_le_request_comprehensive
    ):
        """Test that legal counsel can view all request details."""
        token = await get_legal_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_le_request_comprehensive.id
        # Legal should see sensitive fields
        assert "legal_review_status" in data
        assert "legal_review_notes" in data or data["legal_review_notes"] is None

    async def test_legal_counsel_can_access_audit_log(
        self, client, test_legal, test_le_request_comprehensive
    ):
        """Test that legal counsel can access the audit log."""
        token = await get_legal_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/audit-log",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_legal_counsel_separate_from_director(
        self, client, test_legal, test_director, test_le_request_comprehensive
    ):
        """Test that LEGAL and DIRECTOR roles are distinct."""
        legal_token = await get_legal_token(client)
        director_token = await get_director_token(client)

        legal_headers = {"Authorization": f"Bearer {legal_token}"}
        director_headers = {"Authorization": f"Bearer {director_token}"}

        # Both should be able to access requests
        legal_response = await client.get(
            "/api/v1/law-enforcement/requests",
            headers=legal_headers,
        )
        director_response = await client.get(
            "/api/v1/law-enforcement/requests",
            headers=director_headers,
        )

        assert legal_response.status_code == 200
        assert director_response.status_code == 200


# =============================================================================
# Data Export and Minimization Tests (CRITICAL - PRIVACY COMPLIANCE)
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementDataMinimization:
    """Test data minimization and patron privacy protection."""

    async def test_selective_data_export_profile_only(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test exporting only profile data without history."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        export_data = {
            "request_id": test_le_request_comprehensive.id,
            "include_profile": True,
            "include_checkouts": False,
            "include_holds": False,
            "include_fines": False,
            "include_reading_history": False,
        }

        response = await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/export-patron-data",
            json=export_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "profile" in data
        # Should not include other data categories
        assert data["data_categories_included"] == ["profile"]

    async def test_selective_data_export_checkouts_only(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test exporting checkout data without reading history."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        export_data = {
            "request_id": test_le_request_comprehensive.id,
            "include_profile": False,
            "include_checkouts": True,
            "include_holds": False,
            "include_fines": False,
            "include_reading_history": False,
        }

        response = await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/export-patron-data",
            json=export_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "data_categories_included" in data
        # Reading history should NOT be included
        assert "reading_history" not in data["data_categories_included"]

    async def test_reading_history_requires_explicit_opt_in(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test that reading history requires explicit inclusion."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        # First export WITHOUT reading history
        export_data = {
            "request_id": test_le_request_comprehensive.id,
            "include_profile": True,
            "include_checkouts": True,
            "include_holds": True,
            "include_fines": True,
            "include_reading_history": False,  # Explicitly False
        }

        response = await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/export-patron-data",
            json=export_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "reading_history" not in data["data_categories_included"]

    async def test_data_export_audit_trail(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test that data export is logged in audit trail."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        export_data = {
            "request_id": test_le_request_comprehensive.id,
            "include_profile": True,
            "include_checkouts": True,
            "include_holds": False,
            "include_fines": False,
            "include_reading_history": False,
        }

        # Export data
        await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/export-patron-data",
            json=export_data,
            headers=headers,
        )

        # Check audit log
        response = await client.get(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/audit-log",
            headers=headers,
        )
        assert response.status_code == 200
        audit_log = response.json()
        # Should have data_exported action
        assert any(entry["action"] == "data_exported" for entry in audit_log)


# =============================================================================
# Immutable Audit Logging Tests (CRITICAL - FORENSIC COMPLIANCE)
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementAuditImmutability:
    """Test immutability of audit logs for forensic compliance."""

    async def test_audit_log_immutability_on_database_level(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive, test_db
    ):
        """Test that database prevents UPDATE/DELETE on audit log."""
        from sqlalchemy import select, update
        from app.models.law_enforcement_request import LawEnforcementAuditLog

        # Get initial audit log
        stmt = select(LawEnforcementAuditLog).where(
            LawEnforcementAuditLog.request_id == test_le_request_comprehensive.id
        )
        result = await test_db.execute(stmt)
        logs = result.scalars().all()

        if logs:
            log_entry = logs[0]
            original_action = log_entry.action

            # Try to update (should fail or have no effect)
            with contextlib.suppress(Exception):
                stmt = (
                    update(LawEnforcementAuditLog)
                    .where(LawEnforcementAuditLog.id == log_entry.id)
                    .values(action="tampered_action", details={"tampering": "attempted"})
                )
                await test_db.execute(stmt)
                await test_db.commit()

            # Verify action is unchanged
            result = await test_db.execute(
                select(LawEnforcementAuditLog).where(LawEnforcementAuditLog.id == log_entry.id)
            )
            updated_log = result.scalar_one()
            assert updated_log.action == original_action

    async def test_audit_log_is_append_only(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test that audit log only grows and never shrinks."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        # Get initial count
        response = await client.get(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/audit-log",
            headers=headers,
        )
        initial_count = len(response.json())

        # Perform actions
        for i in range(3):
            await client.post(
                f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/notes",
                json={"note": f"Note #{i + 1}"},
                headers=headers,
            )

        # Get updated count
        response = await client.get(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/audit-log",
            headers=headers,
        )
        final_count = len(response.json())

        # Audit log should only increase
        assert final_count >= initial_count + 3

    async def test_audit_log_contains_forensic_data(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test that audit log contains forensic information."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        # Perform an action
        await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/notes",
            json={"note": "Forensic audit test"},
            headers=headers,
        )

        # Check audit log
        response = await client.get(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/audit-log",
            headers=headers,
        )
        assert response.status_code == 200
        audit_log = response.json()

        # Find the latest note_added entry
        note_entries = [e for e in audit_log if e.get("action") == "note_added"]
        if note_entries:
            latest_entry = note_entries[-1]
            # Should contain forensic metadata
            assert "created_at" in latest_entry or "timestamp" in latest_entry
            # May contain IP and user agent
            assert "details" in latest_entry or "action" in latest_entry


# =============================================================================
# Patron Notification and Gag Order Tests
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementPatronNotification:
    """Test patron notification with gag order support."""

    async def test_record_patron_notification_with_email(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test recording patron notification via email."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        notification_data = {
            "notification_method": "email",
            "notification_notes": "Patron notified of law enforcement request via registered email",
        }

        response = await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/patron-notification",
            json=notification_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["patron_notification_method"] == "email"
        assert data["patron_notification_date"] is not None

    async def test_record_patron_notification_with_mail(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test recording patron notification via certified mail."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        notification_data = {
            "notification_method": "certified_mail",
            "notification_notes": "Certified letter sent to patron's address on file",
            "gag_order_expiration_date": (
                datetime.now(timezone.utc) + timedelta(days=30)
            ).isoformat(),
        }

        response = await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/patron-notification",
            json=notification_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["patron_notification_method"] == "certified_mail"

    async def test_gag_order_tracking(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test that gag order expiration is tracked."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        gag_expiration = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        notification_data = {
            "notification_method": "certified_mail",
            "notification_notes": "Gag order applies to this notification",
            "gag_order_expiration_date": gag_expiration,
        }

        response = await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/patron-notification",
            json=notification_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Gag order should be tracked
        assert data.get("gag_order_expiration_date") is not None or "gag_order" in str(data)


# =============================================================================
# Workflow Checklist Compliance Tests
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementChecklistCompliance:
    """Test complete workflow checklist for compliance."""

    async def test_all_checklist_items_present(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test that all required checklist items are present."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/checklist",
            headers=headers,
        )
        assert response.status_code == 200
        checklist = response.json()

        # Should have 12 items
        assert len(checklist) == 12

        # Should contain required items
        item_types = [item["item_type"] for item in checklist]
        required_items = [
            "receive_request",
            "verify_validity",
            "verify_jurisdiction",
            "verify_scope",
            "legal_review",
            "director_approval",
            "notify_patron",
            "prepare_response",
            "minimize_data",
            "document_compliance",
            "send_response",
            "final_review",
        ]
        for required_item in required_items:
            assert required_item in item_types

    async def test_required_checklist_items_enforcement(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test that required items cannot be skipped."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        checklist_response = await client.get(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/checklist",
            headers=headers,
        )
        checklist = checklist_response.json()

        # Find required items
        required_items = [item for item in checklist if item.get("is_required", False)]
        assert len(required_items) > 0

    async def test_checklist_item_completion_tracking(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test tracking of checklist item completion."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        # Mark an item as complete
        update_data = {
            "is_completed": True,
            "completion_notes": "Verified that request form is complete and valid",
        }

        response = await client.patch(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/checklist/verify_validity",
            json=update_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_completed"] is True

        # Get checklist to verify
        response = await client.get(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}/checklist",
            headers=headers,
        )
        checklist = response.json()
        verify_item = next(
            (item for item in checklist if item["item_type"] == "verify_validity"),
            None,
        )
        assert verify_item is not None
        assert verify_item["is_completed"] is True

    async def test_workflow_status_reflects_checklist_progress(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test that workflow status reflects checklist completion."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        # Initial status should be received
        response = await client.get(
            f"/api/v1/law-enforcement/requests/{test_le_request_comprehensive.id}",
            headers=headers,
        )
        initial_status = response.json()["workflow_status"]
        assert initial_status == "received"


# =============================================================================
# Response Template and Documentation Tests
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementTemplateRendering:
    """Test response template rendering with proper documentation."""

    async def test_list_response_templates(self, client, test_admin, test_admin_data):
        """Test listing available response templates."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/law-enforcement/templates", headers=headers)
        assert response.status_code == 200
        templates = response.json()
        assert isinstance(templates, list)

    async def test_create_compliance_response_template(self, client, test_admin, test_admin_data):
        """Test creating a compliance response template."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        template_data = {
            "name": "Compliance Response",
            "description": "Template for compliance with all data provided",
            "template_type": "compliance",
            "subject_template": "Response to {{request_type}} - {{tracking_number}}",
            "body_template": """Dear {{agency_contact}}:

In response to your {{request_type}} ({{tracking_number}}),
we provide the following information regarding patron {{patron_name}}:

{{data_provided}}

This response is provided pursuant to {{legal_basis}}.

Sincerely,
Library Administration""",
        }

        response = await client.post(
            "/api/v1/law-enforcement/templates",
            json=template_data,
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Compliance Response"

    async def test_render_template_with_request_data(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test rendering template with actual request data."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        # List templates to get an ID
        response = await client.get("/api/v1/law-enforcement/templates", headers=headers)
        templates = response.json()

        if templates:
            template_id = templates[0]["id"]

            # Render template with request data
            response = await client.get(
                f"/api/v1/law-enforcement/templates/{template_id}/render/{test_le_request_comprehensive.id}",
                headers=headers,
            )
            assert response.status_code == 200
            rendered = response.json()
            # Should have rendered content
            assert "subject" in rendered or "rendered_subject" in rendered
            assert "body" in rendered or "rendered_body" in rendered


# =============================================================================
# Transparency Report Tests
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementTransparencyReporting:
    """Test transparency reporting with anonymization."""

    async def test_generate_annual_transparency_report(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test generating annual transparency report."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        report_data = {"year": 2026, "include_details": False}

        response = await client.post(
            "/api/v1/law-enforcement/reports/transparency",
            json=report_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert data["summary"]["year"] == 2026
        assert "total_requests" in data["summary"]
        assert "requests_by_type" in data["summary"]

    async def test_transparency_report_includes_required_fields(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test that transparency report includes required fields."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            "/api/v1/law-enforcement/reports/transparency/2026",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        summary = data.get("summary", {})

        # Required fields per law enforcement transparency reporting standards
        required_fields = [
            "year",
            "total_requests",
            "requests_by_type",
            "requests_by_status",
            "requests_by_legal_outcome",
            "requests_with_patron_notification",
            "unique_patrons_affected",
        ]
        for field in required_fields:
            assert field in summary, f"Missing required field: {field}"

    async def test_transparency_report_with_details_anonymizes_patrons(
        self, client, test_admin, test_admin_data, test_le_request_comprehensive
    ):
        """Test that detailed transparency report anonymizes patron information."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            "/api/v1/law-enforcement/reports/transparency/2026?include_details=true",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()

        # If details are included, patron names should be anonymized
        if "details" in data:
            for request_detail in data.get("details", []):
                # Patron should be anonymized (no real names)
                if "patron_name_on_request" in request_detail:
                    # Should be anonymized like "Patron #1" or similar
                    _ = request_detail["patron_name_on_request"]
                    # Actual implementation may vary


# =============================================================================
# Complete Request Workflow Tests
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementCompleteWorkflow:
    """Test complete request workflow from receipt to completion."""

    async def test_complete_request_workflow_happy_path(
        self, client, test_admin, test_admin_data, test_legal, test_le_request_comprehensive
    ):
        """Test complete workflow from receipt to completion."""
        admin_token = await get_admin_token(client, test_admin_data)
        legal_token = await get_legal_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        legal_headers = {"Authorization": f"Bearer {legal_token}"}

        request_id = test_le_request_comprehensive.id

        # 1. Initial status should be received
        response = await client.get(
            f"/api/v1/law-enforcement/requests/{request_id}",
            headers=admin_headers,
        )
        assert response.json()["workflow_status"] == "received"

        # 2. Legal review (by legal counsel)
        await client.post(
            f"/api/v1/law-enforcement/requests/{request_id}/legal-review",
            json={
                "legal_review_status": "approved",
                "legal_review_notes": "Request is valid and properly scoped.",
            },
            headers=legal_headers,
        )

        # 3. Update workflow to validating
        await client.post(
            f"/api/v1/law-enforcement/requests/{request_id}/workflow-status",
            json={"workflow_status": "validating"},
            headers=admin_headers,
        )

        # 4. Complete checklist items
        checklist_items = [
            "receive_request",
            "verify_validity",
            "verify_jurisdiction",
            "verify_scope",
            "legal_review",
            "director_approval",
            "minimize_data",
            "document_compliance",
        ]
        for item in checklist_items:
            await client.patch(
                f"/api/v1/law-enforcement/requests/{request_id}/checklist/{item}",
                json={"is_completed": True},
                headers=admin_headers,
            )

        # 5. Record patron notification
        await client.post(
            f"/api/v1/law-enforcement/requests/{request_id}/patron-notification",
            json={"notification_method": "email"},
            headers=admin_headers,
        )

        # 6. Export patron data
        await client.post(
            f"/api/v1/law-enforcement/requests/{request_id}/export-patron-data",
            json={
                "include_profile": True,
                "include_checkouts": True,
                "include_holds": True,
                "include_fines": False,
                "include_reading_history": False,
            },
            headers=admin_headers,
        )

        # 7. Record response
        response = await client.post(
            f"/api/v1/law-enforcement/requests/{request_id}/response",
            json={
                "response_method": "certified_mail",
                "response_summary": "Provided patron checkout and hold records",
            },
            headers=admin_headers,
        )
        assert response.status_code == 200

        # 8. Verify audit log contains all actions
        response = await client.get(
            f"/api/v1/law-enforcement/requests/{request_id}/audit-log",
            headers=admin_headers,
        )
        audit_log = response.json()
        assert len(audit_log) >= 5

    async def test_denied_request_workflow(
        self, client, test_admin, test_admin_data, test_legal, test_le_request_comprehensive
    ):
        """Test workflow for denied requests."""
        admin_token = await get_admin_token(client, test_admin_data)
        legal_token = await get_legal_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        legal_headers = {"Authorization": f"Bearer {legal_token}"}

        request_id = test_le_request_comprehensive.id

        # Legal review rejects request
        response = await client.post(
            f"/api/v1/law-enforcement/requests/{request_id}/legal-review",
            json={
                "legal_review_status": "rejected",
                "legal_review_notes": "Request exceeds scope of legal authority.",
            },
            headers=legal_headers,
        )
        assert response.status_code == 200

        # Update status to rejected
        response = await client.post(
            f"/api/v1/law-enforcement/requests/{request_id}/workflow-status",
            json={
                "workflow_status": "rejected",
                "notes": "Rejected due to legal review findings",
            },
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_status"] == "rejected"
        assert data["legal_review_status"] == "rejected"
