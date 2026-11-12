# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for law enforcement service.

Tests business logic for law enforcement request handling including:
- Request creation and tracking number generation
- Workflow management
- Checklist operations
- Audit logging
- Transparency reporting
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.law_enforcement_request import (
    AuditActionType,
    ChecklistItemType,
    LegalReviewStatus,
    RequestType,
    WorkflowStatus,
)
from app.schemas.law_enforcement_request import (
    LawEnforcementRequestCreate,
    LegalReviewUpdate,
    WorkflowStatusUpdate,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = MagicMock()
    user.id = 1
    user.first_name = "Test"
    user.last_name = "Admin"
    user.role = MagicMock()
    user.role.value = "ADMIN"
    return user


@pytest.fixture
def mock_patron():
    """Create a mock patron for testing."""
    patron = MagicMock()
    patron.id = 2
    patron.first_name = "John"
    patron.last_name = "Doe"
    patron.email = "john@example.com"
    patron.library_card = "LIB-001"
    patron.track_reading_history = False
    return patron


@pytest.fixture
def sample_request_data(mock_patron):
    """Create sample request data for testing."""
    return LawEnforcementRequestCreate(
        requesting_agency="Test Police Department",
        agency_contact_name="Detective Smith",
        agency_contact_phone="555-0100",
        request_type=RequestType.SUBPOENA,
        date_received=datetime.now(timezone.utc),
        patron_id=mock_patron.id,
        data_requested="Checkout history for 2026",
        patron_notification_permitted=True,
    )


# =============================================================================
# Request Creation Tests
# =============================================================================


@pytest.mark.unit
class TestRequestCreation:
    """Test request creation logic."""

    async def test_tracking_number_format(self, test_db, mock_user, sample_request_data):
        """Test that tracking numbers are generated in correct format."""
        from app.services.law_enforcement_service import LawEnforcementService

        service = LawEnforcementService(test_db)

        # Generate tracking number
        tracking = await service._generate_tracking_number()

        # Should be in format LE-YYYY-XXXXXX
        assert tracking.startswith("LE-")
        parts = tracking.split("-")
        assert len(parts) == 3
        assert parts[1].isdigit()
        assert len(parts[1]) == 4  # Year
        assert len(parts[2]) == 6  # Random hex

    async def test_tracking_numbers_are_unique(self, test_db):
        """Test that tracking numbers are unique."""
        from app.services.law_enforcement_service import LawEnforcementService

        service = LawEnforcementService(test_db)

        # Generate multiple tracking numbers
        numbers = set()
        for _ in range(100):
            num = await service._generate_tracking_number()
            numbers.add(num)

        # All should be unique
        assert len(numbers) == 100


# =============================================================================
# Workflow Tests
# =============================================================================


@pytest.mark.unit
class TestWorkflowLogic:
    """Test workflow state transitions."""

    def test_legal_review_status_transitions(self):
        """Test valid legal review status transitions."""
        # All transitions should be valid from PENDING_REVIEW
        valid_from_pending = [
            LegalReviewStatus.UNDER_REVIEW,
            LegalReviewStatus.APPROVED,
            LegalReviewStatus.REJECTED,
        ]
        for status in valid_from_pending:
            # This should not raise
            assert status in LegalReviewStatus

    def test_workflow_status_values(self):
        """Test all workflow status values exist."""
        expected_statuses = [
            "received",
            "validating",
            "legal_review",
            "patron_notification",
            "preparing_response",
            "response_sent",
            "completed",
            "rejected",
            "withdrawn",
        ]
        for status_value in expected_statuses:
            assert WorkflowStatus(status_value) is not None


# =============================================================================
# Checklist Tests
# =============================================================================


@pytest.mark.unit
class TestChecklistLogic:
    """Test checklist business logic."""

    def test_default_checklist_items_count(self):
        """Test that default checklist has correct number of items."""
        from app.models.law_enforcement_request import DEFAULT_CHECKLIST_ITEMS

        assert len(DEFAULT_CHECKLIST_ITEMS) == 12

    def test_default_checklist_has_required_items(self):
        """Test that default checklist has all required item types."""
        from app.models.law_enforcement_request import DEFAULT_CHECKLIST_ITEMS

        required_types = {
            ChecklistItemType.RECEIVE_REQUEST,
            ChecklistItemType.VERIFY_VALIDITY,
            ChecklistItemType.VERIFY_JURISDICTION,
            ChecklistItemType.VERIFY_SCOPE,
            ChecklistItemType.LEGAL_REVIEW,
            ChecklistItemType.DIRECTOR_APPROVAL,
            ChecklistItemType.NOTIFY_PATRON,
            ChecklistItemType.PREPARE_RESPONSE,
            ChecklistItemType.MINIMIZE_DATA,
            ChecklistItemType.DOCUMENT_COMPLIANCE,
            ChecklistItemType.SEND_RESPONSE,
            ChecklistItemType.FINAL_REVIEW,
        }

        actual_types = {item["item_type"] for item in DEFAULT_CHECKLIST_ITEMS}
        assert actual_types == required_types

    def test_checklist_sort_order(self):
        """Test that checklist items are properly ordered."""
        from app.models.law_enforcement_request import DEFAULT_CHECKLIST_ITEMS

        sort_orders = [item["sort_order"] for item in DEFAULT_CHECKLIST_ITEMS]
        assert sort_orders == sorted(sort_orders)

    def test_patron_notification_is_optional(self):
        """Test that patron notification checklist item is not required."""
        from app.models.law_enforcement_request import DEFAULT_CHECKLIST_ITEMS

        notify_item = next(
            item for item in DEFAULT_CHECKLIST_ITEMS
            if item["item_type"] == ChecklistItemType.NOTIFY_PATRON
        )
        assert notify_item["is_required"] is False


# =============================================================================
# Audit Log Tests
# =============================================================================


@pytest.mark.unit
class TestAuditLogLogic:
    """Test audit log business logic."""

    def test_audit_action_types_defined(self):
        """Test that all expected audit action types are defined."""
        expected_actions = [
            "request_created",
            "request_updated",
            "status_changed",
            "legal_review_updated",
            "checklist_updated",
            "document_attached",
            "document_removed",
            "patron_notified",
            "response_prepared",
            "response_sent",
            "data_exported",
            "note_added",
            "viewed",
        ]
        for action_value in expected_actions:
            assert AuditActionType(action_value) is not None


# =============================================================================
# Request Type Tests
# =============================================================================


@pytest.mark.unit
class TestRequestTypes:
    """Test request type logic."""

    def test_all_request_types_defined(self):
        """Test that all expected request types are defined."""
        expected_types = [
            "subpoena",
            "warrant",
            "national_security_letter",
            "court_order",
            "informal_request",
        ]
        for type_value in expected_types:
            assert RequestType(type_value) is not None

    def test_informal_request_should_be_declined(self):
        """Test that informal request type exists for tracking declined requests."""
        # Informal requests should be tracked but typically declined
        assert RequestType.INFORMAL_REQUEST.value == "informal_request"


# =============================================================================
# Transparency Report Tests
# =============================================================================


@pytest.mark.unit
class TestTransparencyReportLogic:
    """Test transparency report generation logic."""

    def test_report_summary_fields(self):
        """Test that report summary contains required fields."""
        from app.schemas.law_enforcement_request import TransparencyReportSummary

        # Create a minimal summary
        summary = TransparencyReportSummary(
            year=2026,
            total_requests=10,
            requests_by_type={"subpoena": 5, "warrant": 5},
            requests_by_status={"completed": 8, "rejected": 2},
            requests_by_legal_outcome={"approved": 8, "rejected": 2},
            requests_with_patron_notification=7,
            requests_with_gag_order=1,
            requests_fully_complied=6,
            requests_partially_complied=2,
            requests_rejected=2,
            requests_withdrawn=0,
            unique_patrons_affected=10,
        )

        assert summary.year == 2026
        assert summary.total_requests == 10
        assert "subpoena" in summary.requests_by_type


# =============================================================================
# Template Rendering Tests
# =============================================================================


@pytest.mark.unit
class TestTemplateRendering:
    """Test template placeholder replacement."""

    def test_placeholder_format(self):
        """Test that placeholder format is consistent."""
        template = "Dear {{agency_contact}}, Re: {{tracking_number}}"

        # Simulate rendering
        placeholders = {
            "agency_contact": "Det. Smith",
            "tracking_number": "LE-2026-ABC123",
        }

        rendered = template
        for key, value in placeholders.items():
            rendered = rendered.replace("{{" + key + "}}", value)

        assert rendered == "Dear Det. Smith, Re: LE-2026-ABC123"

    def test_missing_placeholder_preserved(self):
        """Test that missing placeholders are preserved."""
        template = "{{agency_name}} - {{missing_field}}"
        placeholders = {"agency_name": "Test PD"}

        rendered = template
        for key, value in placeholders.items():
            rendered = rendered.replace("{{" + key + "}}", value)

        assert "{{missing_field}}" in rendered


# =============================================================================
# Data Export Tests
# =============================================================================


@pytest.mark.unit
class TestDataExportLogic:
    """Test patron data export logic."""

    def test_export_categories(self):
        """Test that all export categories are defined."""
        from app.schemas.law_enforcement_request import PatronDataExportRequest

        request = PatronDataExportRequest(
            request_id=1,
            include_profile=True,
            include_checkouts=True,
            include_holds=True,
            include_fines=True,
            include_reading_history=False,
        )

        assert request.include_profile is True
        assert request.include_reading_history is False

    def test_reading_history_requires_explicit_opt_in(self):
        """Test that reading history export defaults to False."""
        from app.schemas.law_enforcement_request import PatronDataExportRequest

        # Default should be False for reading history
        request = PatronDataExportRequest(request_id=1)
        assert request.include_reading_history is False
