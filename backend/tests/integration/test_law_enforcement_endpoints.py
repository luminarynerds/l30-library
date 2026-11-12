# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for law enforcement request API endpoints.

SECURITY TESTS: These tests verify that access control is properly enforced.
Only SUPER_ADMIN, ADMIN, DIRECTOR, LEGAL roles (or users with law_enforcement_access
permission) should be able to access these endpoints.
"""

from datetime import datetime, timedelta, timezone

import pytest


# =============================================================================
# Test Fixtures
# =============================================================================


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
async def test_le_request(test_db, test_admin, test_patron):
    """Create a test law enforcement request."""
    from app.models.law_enforcement_request import (
        LawEnforcementRequest,
        RequestType,
        LegalReviewStatus,
        WorkflowStatus,
    )

    request = LawEnforcementRequest(
        tracking_number="LE-2026-TEST01",
        requesting_agency="Test Police Department",
        agency_contact_name="Detective Smith",
        agency_contact_phone="555-0100",
        agency_contact_email="smith@testpd.gov",
        request_type=RequestType.SUBPOENA,
        date_received=datetime.now(timezone.utc),
        patron_id=test_patron.id,
        patron_name_on_request="Test User",
        data_requested="Checkout history for past 6 months",
        legal_review_status=LegalReviewStatus.PENDING_REVIEW,
        workflow_status=WorkflowStatus.RECEIVED,
        created_by_id=test_admin.id,
    )
    test_db.add(request)
    await test_db.commit()
    await test_db.refresh(request)
    return request


@pytest.fixture
async def test_le_request_with_checklist(test_db, test_admin, test_patron):
    """Create a test law enforcement request with checklist items."""
    from app.models.law_enforcement_request import (
        LawEnforcementRequest,
        LawEnforcementChecklist,
        RequestType,
        LegalReviewStatus,
        WorkflowStatus,
        ChecklistItemType,
        DEFAULT_CHECKLIST_ITEMS,
    )

    request = LawEnforcementRequest(
        tracking_number="LE-2026-TEST02",
        requesting_agency="FBI Field Office",
        request_type=RequestType.WARRANT,
        date_received=datetime.now(timezone.utc),
        patron_id=test_patron.id,
        data_requested="All patron records",
        legal_review_status=LegalReviewStatus.PENDING_REVIEW,
        workflow_status=WorkflowStatus.RECEIVED,
        created_by_id=test_admin.id,
    )
    test_db.add(request)
    await test_db.flush()

    # Add checklist items
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


async def get_admin_token(client, test_admin_data) -> str:
    """Helper to get admin authentication token."""
    return await get_token(client, test_admin_data["email"], test_admin_data["password"])


async def get_staff_token(client, test_staff_data) -> str:
    """Helper to get staff authentication token."""
    return await get_token(client, test_staff_data["email"], test_staff_data["password"])


async def get_patron_token(client, test_user_data) -> str:
    """Helper to get patron authentication token."""
    return await get_token(client, test_user_data["email"], test_user_data["password"])


async def get_director_token(client) -> str:
    """Helper to get director authentication token."""
    return await get_token(client, "director@example.com", "DirectorPassword123!")


async def get_legal_token(client) -> str:
    """Helper to get legal counsel authentication token."""
    return await get_token(client, "legal@example.com", "LegalPassword123!")


# =============================================================================
# Access Control Tests (CRITICAL)
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementAccessControl:
    """Test that access control is properly enforced for all endpoints."""

    async def test_unauthenticated_access_denied(self, client):
        """Test that unauthenticated requests are rejected."""
        endpoints = [
            ("GET", "/api/v1/law-enforcement/requests"),
            ("POST", "/api/v1/law-enforcement/requests"),
            ("GET", "/api/v1/law-enforcement/stats"),
            ("GET", "/api/v1/law-enforcement/templates"),
        ]
        for method, endpoint in endpoints:
            if method == "GET":
                response = await client.get(endpoint)
            else:
                response = await client.post(endpoint, json={})
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"

    async def test_patron_access_denied(self, client, test_patron, test_user_data):
        """Test that patrons cannot access law enforcement endpoints."""
        token = await get_patron_token(client, test_user_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/law-enforcement/requests", headers=headers)
        assert response.status_code == 403

        response = await client.get("/api/v1/law-enforcement/stats", headers=headers)
        assert response.status_code == 403

    async def test_staff_access_denied(self, client, test_staff, test_staff_data):
        """Test that regular staff cannot access law enforcement endpoints."""
        token = await get_staff_token(client, test_staff_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/law-enforcement/requests", headers=headers)
        assert response.status_code == 403

        response = await client.get("/api/v1/law-enforcement/stats", headers=headers)
        assert response.status_code == 403

    async def test_admin_access_allowed(self, client, test_admin, test_admin_data):
        """Test that admins can access law enforcement endpoints."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/law-enforcement/requests", headers=headers)
        assert response.status_code == 200

        response = await client.get("/api/v1/law-enforcement/stats", headers=headers)
        assert response.status_code == 200

    async def test_director_access_allowed(self, client, test_director):
        """Test that directors can access law enforcement endpoints."""
        token = await get_director_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/law-enforcement/requests", headers=headers)
        assert response.status_code == 200

        response = await client.get("/api/v1/law-enforcement/stats", headers=headers)
        assert response.status_code == 200

    async def test_legal_access_allowed(self, client, test_legal):
        """Test that legal counsel can access law enforcement endpoints."""
        token = await get_legal_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/law-enforcement/requests", headers=headers)
        assert response.status_code == 200

        response = await client.get("/api/v1/law-enforcement/stats", headers=headers)
        assert response.status_code == 200


# =============================================================================
# Request CRUD Tests
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementRequestCRUD:
    """Test law enforcement request CRUD operations."""

    async def test_create_request(self, client, test_admin, test_admin_data, test_patron):
        """Test creating a new law enforcement request."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        request_data = {
            "requesting_agency": "State Police",
            "agency_contact_name": "Sgt. Johnson",
            "request_type": "subpoena",
            "date_received": datetime.now(timezone.utc).isoformat(),
            "patron_id": test_patron.id,
            "data_requested": "Checkout records for January 2026",
            "patron_notification_permitted": True,
        }

        response = await client.post(
            "/api/v1/law-enforcement/requests",
            json=request_data,
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["requesting_agency"] == "State Police"
        assert data["tracking_number"].startswith("LE-")
        assert data["workflow_status"] == "received"
        assert data["legal_review_status"] == "pending_review"

    async def test_list_requests(self, client, test_admin, test_admin_data, test_le_request):
        """Test listing law enforcement requests."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/law-enforcement/requests", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1

    async def test_list_requests_with_filters(
        self, client, test_admin, test_admin_data, test_le_request
    ):
        """Test listing requests with filters."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        # Filter by request type
        response = await client.get(
            "/api/v1/law-enforcement/requests?request_type=subpoena",
            headers=headers,
        )
        assert response.status_code == 200

        # Filter by workflow status
        response = await client.get(
            "/api/v1/law-enforcement/requests?workflow_status=received",
            headers=headers,
        )
        assert response.status_code == 200

    async def test_get_request(self, client, test_admin, test_admin_data, test_le_request):
        """Test getting a specific law enforcement request."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            f"/api/v1/law-enforcement/requests/{test_le_request.id}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_le_request.id
        assert data["tracking_number"] == test_le_request.tracking_number

    async def test_get_request_not_found(self, client, test_admin, test_admin_data):
        """Test getting a non-existent request."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            "/api/v1/law-enforcement/requests/99999",
            headers=headers,
        )
        assert response.status_code == 404

    async def test_update_request(self, client, test_admin, test_admin_data, test_le_request):
        """Test updating a law enforcement request."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        update_data = {
            "internal_notes": "Updated notes for testing",
            "agency_contact_phone": "555-0200",
        }

        response = await client.patch(
            f"/api/v1/law-enforcement/requests/{test_le_request.id}",
            json=update_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["internal_notes"] == "Updated notes for testing"


# =============================================================================
# Workflow Tests
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementWorkflow:
    """Test law enforcement request workflow operations."""

    async def test_update_legal_review(self, client, test_admin, test_admin_data, test_le_request):
        """Test updating legal review status."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        review_data = {
            "legal_review_status": "approved",
            "legal_review_notes": "Request is valid and properly scoped",
        }

        response = await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request.id}/legal-review",
            json=review_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["legal_review_status"] == "approved"

    async def test_update_workflow_status(
        self, client, test_admin, test_admin_data, test_le_request
    ):
        """Test updating workflow status."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        status_data = {
            "workflow_status": "validating",
            "notes": "Beginning validation process",
        }

        response = await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request.id}/workflow-status",
            json=status_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_status"] == "validating"

    async def test_get_checklist(
        self, client, test_admin, test_admin_data, test_le_request_with_checklist
    ):
        """Test getting the workflow checklist."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            f"/api/v1/law-enforcement/requests/{test_le_request_with_checklist.id}/checklist",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all("item_type" in item for item in data)
        assert all("is_completed" in item for item in data)

    async def test_update_checklist_item(
        self, client, test_admin, test_admin_data, test_le_request_with_checklist
    ):
        """Test updating a checklist item."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        update_data = {
            "is_completed": True,
            "completion_notes": "Verified request form is complete",
        }

        response = await client.patch(
            f"/api/v1/law-enforcement/requests/{test_le_request_with_checklist.id}/checklist/verify_validity",
            json=update_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_completed"] is True


# =============================================================================
# Audit Log Tests
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementAuditLog:
    """Test law enforcement audit logging (immutable)."""

    async def test_get_audit_log(self, client, test_admin, test_admin_data, test_le_request):
        """Test retrieving the audit log."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        # First, view the request to generate an audit entry
        await client.get(
            f"/api/v1/law-enforcement/requests/{test_le_request.id}",
            headers=headers,
        )

        # Now get the audit log
        response = await client.get(
            f"/api/v1/law-enforcement/requests/{test_le_request.id}/audit-log",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least one entry from viewing
        assert len(data) >= 1
        assert all("action" in entry for entry in data)
        assert all("created_at" in entry for entry in data)

    async def test_add_note(self, client, test_admin, test_admin_data, test_le_request):
        """Test adding a note to the audit log."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        note_data = {"note": "Contacted agency for clarification on scope"}

        response = await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request.id}/notes",
            json=note_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "note_added"
        assert data["details"]["note"] == note_data["note"]


# =============================================================================
# Transparency Report Tests
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementTransparencyReport:
    """Test transparency report generation."""

    async def test_generate_transparency_report(
        self, client, test_admin, test_admin_data, test_le_request
    ):
        """Test generating a transparency report."""
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
        assert "report_generated_at" in data
        assert data["summary"]["year"] == 2026
        assert "total_requests" in data["summary"]

    async def test_get_transparency_report_by_year(
        self, client, test_admin, test_admin_data, test_le_request
    ):
        """Test getting transparency report for a specific year."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            "/api/v1/law-enforcement/reports/transparency/2026",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["year"] == 2026

    async def test_transparency_report_with_details(
        self, client, test_admin, test_admin_data, test_le_request
    ):
        """Test transparency report with request details included."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            "/api/v1/law-enforcement/reports/transparency/2026?include_details=true",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "details" in data
        # Details should include request-level info (anonymized)


# =============================================================================
# Response Template Tests
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementTemplates:
    """Test response template operations."""

    async def test_list_templates(self, client, test_admin, test_admin_data):
        """Test listing response templates."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/law-enforcement/templates", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_create_template(self, client, test_admin, test_admin_data):
        """Test creating a response template."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        template_data = {
            "name": "Test Template",
            "description": "A test template for automated testing",
            "template_type": "acknowledgment",
            "subject_template": "Re: {{tracking_number}}",
            "body_template": "Dear {{agency_contact}},\n\nThank you for your request.",
        }

        response = await client.post(
            "/api/v1/law-enforcement/templates",
            json=template_data,
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Template"


# =============================================================================
# Statistics Tests
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementStatistics:
    """Test statistics endpoint."""

    async def test_get_statistics(self, client, test_admin, test_admin_data, test_le_request):
        """Test getting overall statistics."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/law-enforcement/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "pending_review" in data
        assert "in_progress" in data
        assert "completed" in data
        assert "this_year" in data


# =============================================================================
# Data Export Tests
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementDataExport:
    """Test patron data export for law enforcement compliance."""

    async def test_export_patron_data(
        self, client, test_admin, test_admin_data, test_le_request, test_patron
    ):
        """Test exporting patron data for a request."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        export_data = {
            "request_id": test_le_request.id,
            "include_profile": True,
            "include_checkouts": True,
            "include_holds": True,
            "include_fines": True,
            "include_reading_history": False,
        }

        response = await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request.id}/export-patron-data",
            json=export_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["patron_id"] == test_patron.id
        assert "profile" in data
        assert "exported_at" in data
        assert "data_categories_included" in data


# =============================================================================
# Response Recording Tests
# =============================================================================


@pytest.mark.integration
class TestLawEnforcementResponse:
    """Test response recording operations."""

    async def test_record_response(self, client, test_admin, test_admin_data, test_le_request):
        """Test recording a response sent to law enforcement."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        response_data = {
            "response_method": "certified_mail",
            "response_summary": "Provided requested checkout records",
            "data_provided_summary": "Checkout history from Jan-Jun 2026",
        }

        response = await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request.id}/response",
            json=response_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_status"] == "response_sent"
        assert data["response_method"] == "certified_mail"

    async def test_record_patron_notification(
        self, client, test_admin, test_admin_data, test_le_request
    ):
        """Test recording patron notification."""
        token = await get_admin_token(client, test_admin_data)
        headers = {"Authorization": f"Bearer {token}"}

        notification_data = {
            "notification_method": "email",
            "notification_notes": "Patron notified via registered email",
        }

        response = await client.post(
            f"/api/v1/law-enforcement/requests/{test_le_request.id}/patron-notification",
            json=notification_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["patron_notification_date"] is not None
        assert data["patron_notification_method"] == "email"
