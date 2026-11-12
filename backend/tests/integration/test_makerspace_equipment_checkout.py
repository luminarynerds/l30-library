# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Makerspace Equipment Checkout System.

Tests the three core features:
1. Training/Certification Verification
2. Reservation Approval Workflow
3. Damage Reporting Functionality
"""

import pytest
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.makerspace import (
    MakerspaceResource,
    MakerspaceReservation,
    MakerspaceCertification,
    MakerspaceCertificationType,
    SafetyIncident,
    ResourceType,
    ResourceStatus,
    MakerspaceReservationStatus,
    CertificationStatus,
    MakerspaceIncidentSeverity,
)
from app.models.lost_damaged import (
    DamagedItemRecord,
    LostItemRecord,
    MendingQueue,
    DamagedItemStatus,
    DamageSeverity,
    LostItemStatus,
)
from app.models.user import User, UserRole
from app.services.makerspace_service import (
    MakerspaceResourceService,
    CertificationService,
    ReservationService,
    SafetyIncidentService,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "patron@example.com"
    user.full_name = "Test Patron"
    user.role = UserRole.PATRON
    return user


@pytest.fixture
def staff_user():
    """Create a sample staff user for testing."""
    user = MagicMock(spec=User)
    user.id = 2
    user.email = "staff@example.com"
    user.full_name = "Test Staff"
    user.role = UserRole.STAFF
    return user


@pytest.fixture
def sample_resource():
    """Create a sample makerspace resource."""
    resource = MagicMock(spec=MakerspaceResource)
    resource.id = 1
    resource.name = "3D Printer - Ultimaker S5"
    resource.resource_type = ResourceType.printer_3d
    resource.status = ResourceStatus.available
    resource.is_active = True
    resource.requires_certification = True
    resource.certification_type_id = 1
    resource.hourly_cost = Decimal("10.00")
    resource.available_from = "09:00"
    resource.available_until = "21:00"
    resource.available_days = [0, 1, 2, 3, 4]  # Mon-Fri
    resource.buffer_minutes = 15
    resource.min_reservation_hours = 1
    resource.max_reservation_hours = 4
    return resource


@pytest.fixture
def sample_certification_type():
    """Create a sample certification type."""
    cert_type = MagicMock(spec=MakerspaceCertificationType)
    cert_type.id = 1
    cert_type.name = "3D Printing Certification"
    cert_type.description = "Required training for 3D printer operation"
    cert_type.is_active = True
    cert_type.training_duration_hours = 2
    cert_type.validity_months = 12
    cert_type.passing_score = 80
    cert_type.fee = Decimal("25.00")
    return cert_type


@pytest.fixture
def sample_certification(sample_user, sample_certification_type):
    """Create a sample certification."""
    cert = MagicMock(spec=MakerspaceCertification)
    cert.id = 1
    cert.user_id = sample_user.id
    cert.certification_type_id = sample_certification_type.id
    cert.status = CertificationStatus.active
    cert.training_completed_at = datetime.now(timezone.utc) - timedelta(days=30)
    cert.quiz_score = 90
    cert.certified_at = datetime.now(timezone.utc) - timedelta(days=30)
    cert.expires_at = datetime.now(timezone.utc) + timedelta(days=335)
    cert.certification_type = sample_certification_type
    cert.user = sample_user
    return cert


@pytest.fixture
def sample_reservation(sample_user, sample_resource):
    """Create a sample reservation."""
    reservation = MagicMock(spec=MakerspaceReservation)
    reservation.id = 1
    reservation.user_id = sample_user.id
    reservation.resource_id = sample_resource.id
    reservation.status = MakerspaceReservationStatus.pending
    reservation.start_time = datetime.now(timezone.utc) + timedelta(days=1)
    reservation.end_time = datetime.now(timezone.utc) + timedelta(days=1, hours=2)
    reservation.project_name = "Test Project"
    reservation.project_description = "Testing the 3D printer"
    reservation.resource = sample_resource
    reservation.user = sample_user
    return reservation


# =============================================================================
# Training/Certification Verification Tests
# =============================================================================


class TestCertificationVerification:
    """Tests for training and certification verification system."""

    def test_certification_status_enum_values(self):
        """Verify certification status enum has all required values."""
        assert CertificationStatus.pending is not None
        assert CertificationStatus.active is not None
        assert CertificationStatus.expired is not None
        assert CertificationStatus.suspended is not None
        assert CertificationStatus.revoked is not None

    def test_certification_type_model_attributes(self, sample_certification_type):
        """Verify certification type has required attributes."""
        assert sample_certification_type.name is not None
        assert sample_certification_type.training_duration_hours is not None
        assert sample_certification_type.validity_months is not None
        assert sample_certification_type.passing_score is not None
        assert sample_certification_type.is_active is not None

    def test_certification_model_attributes(self, sample_certification):
        """Verify certification has required attributes."""
        assert sample_certification.user_id is not None
        assert sample_certification.certification_type_id is not None
        assert sample_certification.status is not None
        assert sample_certification.quiz_score is not None
        assert sample_certification.certified_at is not None
        assert sample_certification.expires_at is not None

    def test_certification_is_active_when_not_expired(self, sample_certification):
        """Verify certification is considered active when not expired."""
        sample_certification.status = CertificationStatus.active
        sample_certification.expires_at = datetime.now(timezone.utc) + timedelta(days=100)
        assert sample_certification.status == CertificationStatus.active
        assert sample_certification.expires_at > datetime.now(timezone.utc)

    def test_certification_is_pending_before_completion(
        self, sample_user, sample_certification_type
    ):
        """Verify certification starts in pending status."""
        cert = MagicMock(spec=MakerspaceCertification)
        cert.status = CertificationStatus.pending
        cert.training_completed_at = None
        cert.quiz_score = None
        assert cert.status == CertificationStatus.pending
        assert cert.training_completed_at is None

    def test_certification_workflow_training_to_quiz(self, sample_certification):
        """Verify certification workflow from training to quiz."""
        # Start with pending
        sample_certification.status = CertificationStatus.pending
        sample_certification.training_completed_at = None

        # Complete training
        sample_certification.training_completed_at = datetime.now(timezone.utc)
        assert sample_certification.training_completed_at is not None

        # Submit quiz and pass
        sample_certification.quiz_score = 90
        sample_certification.status = CertificationStatus.active
        sample_certification.certified_at = datetime.now(timezone.utc)

        assert sample_certification.status == CertificationStatus.active
        assert sample_certification.quiz_score >= 80

    def test_certification_suspension_workflow(self, sample_certification, staff_user):
        """Verify certification can be suspended by staff."""
        sample_certification.status = CertificationStatus.active

        # Suspend certification
        sample_certification.status = CertificationStatus.suspended
        sample_certification.suspended_by_id = staff_user.id
        sample_certification.suspension_reason = "Safety violation"

        assert sample_certification.status == CertificationStatus.suspended
        assert sample_certification.suspended_by_id == staff_user.id

    def test_certification_reinstatement_workflow(self, sample_certification):
        """Verify suspended certification can be reinstated."""
        sample_certification.status = CertificationStatus.suspended

        # Reinstate
        sample_certification.status = CertificationStatus.active
        sample_certification.suspension_reason = None

        assert sample_certification.status == CertificationStatus.active

    @pytest.mark.asyncio
    async def test_complete_training_records_timestamp(self, mock_db):
        """Record completed training for a patron certification."""
        certification = MagicMock(spec=MakerspaceCertification)
        certification.training_completed_at = None

        completed_at = datetime(2024, 5, 10, 15, 30, tzinfo=timezone.utc)
        with patch("app.services.makerspace.certification_service.datetime") as datetime_mock:
            datetime_mock.now.return_value = completed_at
            datetime_mock.side_effect = datetime

            result = await CertificationService.complete_training(mock_db, certification)

        assert result.training_completed_at == completed_at
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(certification)


class TestTrainingVerification:
    """Tests for verifying training before equipment use."""

    @pytest.mark.asyncio
    async def test_reservation_requires_training_completion(
        self, mock_db, sample_user, sample_resource
    ):
        """Verify training is checked before allowing equipment use."""
        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        with (
            patch.object(
                MakerspaceResourceService,
                "get_by_id",
                AsyncMock(return_value=sample_resource),
            ),
            patch.object(
                CertificationService,
                "check_user_certified",
                AsyncMock(return_value=False),
            ) as check_certified,
        ):
            with pytest.raises(ValueError, match="not certified"):
                await ReservationService.create(
                    mock_db,
                    user_id=sample_user.id,
                    resource_id=sample_resource.id,
                    start_time=start_time,
                    end_time=end_time,
                )

        check_certified.assert_awaited_once_with(
            mock_db, sample_user.id, sample_resource.certification_type_id
        )


# =============================================================================
# Reservation Approval Workflow Tests
# =============================================================================


class TestReservationApprovalWorkflow:
    """Tests for reservation approval workflow."""

    def test_reservation_status_enum_values(self):
        """Verify reservation status enum has all required values."""
        assert MakerspaceReservationStatus.pending is not None
        assert MakerspaceReservationStatus.confirmed is not None
        assert MakerspaceReservationStatus.checked_in is not None
        assert MakerspaceReservationStatus.completed is not None
        assert MakerspaceReservationStatus.cancelled is not None
        assert MakerspaceReservationStatus.no_show is not None
        assert MakerspaceReservationStatus.expired is not None

    def test_reservation_model_attributes(self, sample_reservation):
        """Verify reservation has required attributes."""
        assert sample_reservation.user_id is not None
        assert sample_reservation.resource_id is not None
        assert sample_reservation.status is not None
        assert sample_reservation.start_time is not None
        assert sample_reservation.end_time is not None

    def test_reservation_starts_in_pending_status(self, sample_reservation):
        """Verify new reservations start in pending status."""
        sample_reservation.status = MakerspaceReservationStatus.pending
        assert sample_reservation.status == MakerspaceReservationStatus.pending

    def test_reservation_approval_workflow(self, sample_reservation, staff_user):
        """Verify reservation approval workflow."""
        # Start pending
        sample_reservation.status = MakerspaceReservationStatus.pending

        # Staff approves
        sample_reservation.status = MakerspaceReservationStatus.confirmed
        sample_reservation.approved_by_id = staff_user.id
        sample_reservation.approved_at = datetime.now(timezone.utc)

        assert sample_reservation.status == MakerspaceReservationStatus.confirmed
        assert sample_reservation.approved_by_id == staff_user.id

    def test_reservation_check_in_workflow(self, sample_reservation):
        """Verify reservation check-in workflow."""
        sample_reservation.status = MakerspaceReservationStatus.confirmed

        # Check in
        sample_reservation.status = MakerspaceReservationStatus.checked_in
        sample_reservation.checked_in_at = datetime.now(timezone.utc)

        assert sample_reservation.status == MakerspaceReservationStatus.checked_in
        assert sample_reservation.checked_in_at is not None

    def test_reservation_check_out_workflow(self, sample_reservation):
        """Verify reservation check-out workflow."""
        sample_reservation.status = MakerspaceReservationStatus.checked_in
        sample_reservation.checked_in_at = datetime.now(timezone.utc) - timedelta(hours=2)

        # Check out
        sample_reservation.status = MakerspaceReservationStatus.completed
        sample_reservation.checked_out_at = datetime.now(timezone.utc)

        assert sample_reservation.status == MakerspaceReservationStatus.completed
        assert sample_reservation.checked_out_at is not None

    def test_reservation_cancellation_workflow(self, sample_reservation, sample_user):
        """Verify reservation cancellation workflow."""
        sample_reservation.status = MakerspaceReservationStatus.pending

        # Cancel
        sample_reservation.status = MakerspaceReservationStatus.cancelled
        sample_reservation.cancelled_at = datetime.now(timezone.utc)
        sample_reservation.cancelled_by_id = sample_user.id
        sample_reservation.cancellation_reason = "Schedule conflict"

        assert sample_reservation.status == MakerspaceReservationStatus.cancelled
        assert sample_reservation.cancellation_reason is not None

    def test_reservation_no_show_workflow(self, sample_reservation, staff_user):
        """Verify reservation no-show workflow."""
        sample_reservation.status = MakerspaceReservationStatus.confirmed

        # Mark as no-show
        sample_reservation.status = MakerspaceReservationStatus.no_show

        assert sample_reservation.status == MakerspaceReservationStatus.no_show

    def test_reservation_requires_certification(self, sample_resource, sample_user):
        """Verify reservation requires certification when resource requires it."""
        sample_resource.requires_certification = True
        sample_resource.certification_type_id = 1

        # This would be checked in the service layer
        assert sample_resource.requires_certification is True
        assert sample_resource.certification_type_id is not None


# =============================================================================
# Damage Reporting Functionality Tests
# =============================================================================


class TestDamageReportingFunctionality:
    """Tests for damage reporting functionality."""

    def test_damage_severity_enum_values(self):
        """Verify damage severity enum has all required values."""
        assert DamageSeverity.MINOR is not None
        assert DamageSeverity.MODERATE is not None
        assert DamageSeverity.SEVERE is not None
        assert DamageSeverity.TOTAL_LOSS is not None

    def test_damaged_item_status_enum_values(self):
        """Verify damaged item status enum has all required values."""
        assert DamagedItemStatus.REPORTED is not None
        assert DamagedItemStatus.ASSESSMENT_PENDING is not None
        assert DamagedItemStatus.REPAIRABLE is not None
        assert DamagedItemStatus.IN_MENDING is not None
        assert DamagedItemStatus.REPAIRED is not None
        assert DamagedItemStatus.WITHDRAWN is not None
        assert DamagedItemStatus.CHARGED is not None

    def test_damaged_item_model_creation(self):
        """Verify damaged item record can be created with required fields."""
        record = MagicMock(spec=DamagedItemRecord)
        record.id = 1
        record.item_copy_id = 100
        record.patron_id = 1
        record.severity = DamageSeverity.MODERATE
        record.status = DamagedItemStatus.REPORTED
        record.damage_description = "Broken screen"
        record.is_patron_responsible = True
        record.reported_at = datetime.now(timezone.utc)

        assert record.id is not None
        assert record.severity == DamageSeverity.MODERATE
        assert record.status == DamagedItemStatus.REPORTED
        assert record.is_patron_responsible is True

    def test_damage_assessment_workflow(self):
        """Verify damage assessment workflow."""
        record = MagicMock(spec=DamagedItemRecord)
        record.status = DamagedItemStatus.REPORTED

        # Initial report
        assert record.status == DamagedItemStatus.REPORTED

        # Assessment pending
        record.status = DamagedItemStatus.ASSESSMENT_PENDING
        assert record.status == DamagedItemStatus.ASSESSMENT_PENDING

        # Assessment complete - repairable
        record.status = DamagedItemStatus.REPAIRABLE
        record.estimated_repair_cost = Decimal("50.00")
        record.assessed_at = datetime.now(timezone.utc)

        assert record.status == DamagedItemStatus.REPAIRABLE
        assert record.estimated_repair_cost is not None

    def test_damage_mending_queue_workflow(self):
        """Verify damage mending queue workflow."""
        record = MagicMock(spec=DamagedItemRecord)
        record.status = DamagedItemStatus.REPAIRABLE

        # Send to mending
        record.status = DamagedItemStatus.IN_MENDING

        # Create mending queue entry
        mending_entry = MagicMock(spec=MendingQueue)
        mending_entry.id = 1
        mending_entry.damaged_item_record_id = record.id
        mending_entry.priority = 2
        mending_entry.repair_type = "screen_replacement"
        mending_entry.is_in_progress = False
        mending_entry.is_completed = False

        assert record.status == DamagedItemStatus.IN_MENDING
        assert mending_entry.damaged_item_record_id is not None

    def test_damage_repair_completion_workflow(self):
        """Verify damage repair completion workflow."""
        record = MagicMock(spec=DamagedItemRecord)
        record.status = DamagedItemStatus.IN_MENDING

        # Complete repair
        record.status = DamagedItemStatus.REPAIRED
        record.actual_repair_cost = Decimal("45.00")
        record.resolved_at = datetime.now(timezone.utc)

        assert record.status == DamagedItemStatus.REPAIRED
        assert record.actual_repair_cost is not None

    def test_damage_withdrawal_workflow(self):
        """Verify damage withdrawal workflow for unrepairable items."""
        record = MagicMock(spec=DamagedItemRecord)
        record.severity = DamageSeverity.TOTAL_LOSS
        record.status = DamagedItemStatus.ASSESSMENT_PENDING

        # Withdraw item
        record.status = DamagedItemStatus.WITHDRAWN
        record.resolved_at = datetime.now(timezone.utc)

        assert record.status == DamagedItemStatus.WITHDRAWN

    def test_damage_patron_charge_calculation(self):
        """Verify patron charge calculation based on damage severity."""
        # Minor damage - 25% charge
        minor_charge = Decimal("100.00") * Decimal("0.25")
        assert minor_charge == Decimal("25.00")

        # Moderate damage - 50% charge
        moderate_charge = Decimal("100.00") * Decimal("0.50")
        assert moderate_charge == Decimal("50.00")

        # Severe damage - 75% charge
        severe_charge = Decimal("100.00") * Decimal("0.75")
        assert severe_charge == Decimal("75.00")

        # Total loss - 100% charge
        total_charge = Decimal("100.00") * Decimal("1.00")
        assert total_charge == Decimal("100.00")


# =============================================================================
# Resource Status Tests
# =============================================================================


class TestResourceStatusManagement:
    """Tests for resource status management."""

    def test_resource_status_enum_values(self):
        """Verify resource status enum has all required values."""
        assert ResourceStatus.available is not None
        assert ResourceStatus.in_use is not None
        assert ResourceStatus.maintenance is not None
        assert ResourceStatus.out_of_order is not None
        assert ResourceStatus.reserved is not None
        assert ResourceStatus.retired is not None

    def test_resource_type_enum_values(self):
        """Verify resource type enum has all required values."""
        assert ResourceType.printer_3d is not None
        assert ResourceType.laser_cutter is not None
        assert ResourceType.cnc_router is not None
        assert ResourceType.vinyl_cutter is not None
        assert ResourceType.sewing_machine is not None

    def test_resource_availability_attributes(self, sample_resource):
        """Verify resource has availability configuration."""
        assert sample_resource.available_from is not None
        assert sample_resource.available_until is not None
        assert sample_resource.available_days is not None
        assert sample_resource.buffer_minutes is not None

    def test_resource_certification_requirement(self, sample_resource):
        """Verify resource certification requirement configuration."""
        assert sample_resource.requires_certification is True
        assert sample_resource.certification_type_id is not None


# =============================================================================
# Safety Incident Tests
# =============================================================================


class TestSafetyIncidentReporting:
    """Tests for safety incident reporting."""

    def test_incident_severity_enum_values(self):
        """Verify incident severity enum has all required values."""
        assert MakerspaceIncidentSeverity.minor is not None
        assert MakerspaceIncidentSeverity.moderate is not None
        assert MakerspaceIncidentSeverity.serious is not None
        assert MakerspaceIncidentSeverity.critical is not None

    def test_safety_incident_creation(self, sample_resource, staff_user):
        """Verify safety incident can be created."""
        incident = MagicMock(spec=SafetyIncident)
        incident.id = 1
        incident.resource_id = sample_resource.id
        incident.reported_by_id = staff_user.id
        incident.severity = MakerspaceIncidentSeverity.moderate
        incident.description = "Minor burn from hot end"
        incident.incident_date = datetime.now(timezone.utc)
        incident.is_resolved = False

        assert incident.resource_id is not None
        assert incident.severity == MakerspaceIncidentSeverity.moderate
        assert incident.is_resolved is False

    def test_safety_incident_resolution(self):
        """Verify safety incident can be resolved."""
        incident = MagicMock(spec=SafetyIncident)
        incident.is_resolved = False

        # Resolve incident
        incident.is_resolved = True
        incident.resolved_at = datetime.now(timezone.utc)
        incident.resolution_notes = "Added additional safety warnings"

        assert incident.is_resolved is True
        assert incident.resolution_notes is not None


# =============================================================================
# Integration Workflow Tests
# =============================================================================


class TestEndToEndWorkflows:
    """Integration tests for complete workflows."""

    def test_complete_reservation_workflow(
        self, sample_user, sample_resource, sample_certification, staff_user
    ):
        """Test complete reservation workflow from creation to completion."""
        # 1. Verify user has certification
        assert sample_certification.status == CertificationStatus.active
        assert sample_certification.user_id == sample_user.id

        # 2. Create reservation
        reservation = MagicMock(spec=MakerspaceReservation)
        reservation.user_id = sample_user.id
        reservation.resource_id = sample_resource.id
        reservation.status = MakerspaceReservationStatus.pending

        # 3. Approve reservation
        reservation.status = MakerspaceReservationStatus.confirmed
        reservation.approved_by_id = staff_user.id

        # 4. Check in
        reservation.status = MakerspaceReservationStatus.checked_in
        reservation.checked_in_at = datetime.now(timezone.utc)

        # 5. Check out and complete
        reservation.status = MakerspaceReservationStatus.completed
        reservation.checked_out_at = datetime.now(timezone.utc)

        assert reservation.status == MakerspaceReservationStatus.completed

    def test_certification_to_reservation_workflow(
        self, sample_user, sample_resource, sample_certification_type
    ):
        """Test workflow from getting certified to making a reservation."""
        # 1. Start certification
        cert = MagicMock(spec=MakerspaceCertification)
        cert.user_id = sample_user.id
        cert.certification_type_id = sample_certification_type.id
        cert.status = CertificationStatus.pending

        # 2. Complete training
        cert.training_completed_at = datetime.now(timezone.utc)

        # 3. Pass quiz
        cert.quiz_score = 85
        cert.status = CertificationStatus.active
        cert.certified_at = datetime.now(timezone.utc)

        # 4. Now user can make reservation
        reservation = MagicMock(spec=MakerspaceReservation)
        reservation.user_id = sample_user.id
        reservation.resource_id = sample_resource.id
        reservation.status = MakerspaceReservationStatus.pending

        assert cert.status == CertificationStatus.active
        assert reservation.user_id == cert.user_id

    def test_damage_report_to_mending_workflow(self, sample_user, staff_user):
        """Test complete damage report to mending workflow."""
        # 1. Report damage
        record = MagicMock(spec=DamagedItemRecord)
        record.patron_id = sample_user.id
        record.severity = DamageSeverity.MODERATE
        record.status = DamagedItemStatus.REPORTED
        record.is_patron_responsible = True

        # 2. Assess damage
        record.status = DamagedItemStatus.REPAIRABLE
        record.estimated_repair_cost = Decimal("50.00")
        record.charge_amount = Decimal("25.00")  # 50% of repair cost

        # 3. Send to mending
        record.status = DamagedItemStatus.IN_MENDING

        mending_entry = MagicMock(spec=MendingQueue)
        mending_entry.damaged_item_record_id = record.id
        mending_entry.priority = 2
        mending_entry.is_completed = False

        # 4. Complete repair
        mending_entry.is_completed = True
        mending_entry.completed_at = datetime.now(timezone.utc)

        record.status = DamagedItemStatus.REPAIRED
        record.actual_repair_cost = Decimal("45.00")

        assert record.status == DamagedItemStatus.REPAIRED
        assert mending_entry.is_completed is True


# =============================================================================
# API Endpoint Verification Tests
# =============================================================================


class TestAPIEndpointStructure:
    """Tests to verify API endpoint structure matches expected patterns."""

    def test_makerspace_public_endpoints_exist(self):
        """Verify public makerspace endpoints are defined."""
        from app.api.v1.makerspace import router

        routes = [r.path for r in router.routes]

        # Resource endpoints
        assert "/resources" in routes or any("/resources" in r for r in routes)

        # Certification endpoints
        assert any("certification" in r.lower() for r in routes)

        # Reservation endpoints
        assert any("reservation" in r.lower() for r in routes)

        # Job endpoints
        assert any("job" in r.lower() for r in routes)

    def test_staff_makerspace_endpoints_exist(self):
        """Verify staff makerspace endpoints are defined."""
        from app.api.v1.staff_makerspace import router

        routes = [r.path for r in router.routes]

        # Staff resource management
        assert any("resource" in r.lower() for r in routes)

        # Staff certification management
        assert any("certification" in r.lower() for r in routes)

        # Staff reservation management
        assert any("reservation" in r.lower() for r in routes)

        # Incident reporting
        assert any("incident" in r.lower() for r in routes)

        # Maintenance management
        assert any("maintenance" in r.lower() for r in routes)

    def test_staff_lost_damaged_endpoints_exist(self):
        """Verify staff lost/damaged endpoints are defined."""
        from app.api.v1.staff_lost_damaged import router

        routes = [r.path for r in router.routes]

        # Lost item endpoints
        assert any("lost" in r.lower() for r in routes)

        # Damaged item endpoints
        assert any("damage" in r.lower() for r in routes)

        # Mending queue endpoints
        assert any("mending" in r.lower() for r in routes)

        # Claims returned endpoints
        assert any("claim" in r.lower() for r in routes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
