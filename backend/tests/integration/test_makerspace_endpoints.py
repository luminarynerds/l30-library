# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for makerspace API endpoints.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
async def test_makerspace_resource(test_db):
    """Create a test makerspace resource."""
    from app.models.makerspace import MakerspaceResource, ResourceType, ResourceStatus

    resource = MakerspaceResource(
        name="Prusa MK4",
        resource_type=ResourceType.printer_3d,
        description="High-quality FDM 3D printer with automatic bed leveling.",
        location="Makerspace Room A",
        status=ResourceStatus.available,
        requires_certification=False,
        hourly_cost=Decimal("5.00"),
        max_reservation_hours=4,
    )
    test_db.add(resource)
    await test_db.commit()
    await test_db.refresh(resource)
    return resource


@pytest.fixture
async def test_makerspace_resource_requiring_cert(test_db, test_certification_type):
    """Create a makerspace resource that requires certification."""
    from app.models.makerspace import MakerspaceResource, ResourceType, ResourceStatus

    resource = MakerspaceResource(
        name="Glowforge Pro Laser Cutter",
        resource_type=ResourceType.laser_cutter,
        description="45W CO2 laser cutter for various materials.",
        location="Makerspace Room B",
        status=ResourceStatus.available,
        requires_certification=True,
        hourly_cost=Decimal("10.00"),
        max_reservation_hours=2,
    )
    test_db.add(resource)
    await test_db.commit()
    await test_db.refresh(resource)
    return resource


@pytest.fixture
async def test_certification_type(test_db):
    """Create a test certification type."""
    from app.models.makerspace import MakerspaceCertificationType

    cert_type = MakerspaceCertificationType(
        name="Laser Cutter Safety Certification",
        description="Required training for laser cutter operation.",
        training_duration_hours=2,
        validity_months=12,
        is_active=True,
    )
    test_db.add(cert_type)
    await test_db.commit()
    await test_db.refresh(cert_type)
    return cert_type


@pytest.fixture
async def test_patron_certification(test_db, test_patron, test_certification_type):
    """Create a certification for a test patron."""
    from app.models.makerspace import MakerspaceCertification, CertificationStatus

    certification = MakerspaceCertification(
        user_id=test_patron.id,
        certification_type_id=test_certification_type.id,
        status=CertificationStatus.active,
        certified_at=datetime.now(),
        expires_at=datetime.now() + timedelta(days=365),
    )
    test_db.add(certification)
    await test_db.commit()
    await test_db.refresh(certification)
    return certification


@pytest.fixture
async def test_reservation(test_db, test_patron, test_makerspace_resource):
    """Create a test reservation."""
    from app.models.makerspace import MakerspaceReservation, MakerspaceReservationStatus

    reservation = MakerspaceReservation(
        user_id=test_patron.id,
        resource_id=test_makerspace_resource.id,
        start_time=datetime.now() + timedelta(days=1),
        end_time=datetime.now() + timedelta(days=1, hours=2),
        status=MakerspaceReservationStatus.confirmed,
    )
    test_db.add(reservation)
    await test_db.commit()
    await test_db.refresh(reservation)
    return reservation


@pytest.fixture
async def test_makerspace_job(test_db, test_patron, test_makerspace_resource):
    """Create a test makerspace job."""
    from app.models.makerspace import MakerspaceJob, JobStatus, JobPriority

    job = MakerspaceJob(
        job_number="JOB-20260101-TEST01",
        user_id=test_patron.id,
        resource_id=test_makerspace_resource.id,
        project_name="Test Print Job",
        file_path="/uploads/test-file.stl",
        status=JobStatus.pending_review,
        priority=JobPriority.normal,
        notes="Test print job",
        # estimated_cost has a Column-level default=Decimal("0.00") but it
        # doesn't reliably apply through every flush path this fixture hits
        # (confirmed: a later staff review UPDATE re-sent estimated_cost as
        # NULL) -- set it explicitly rather than rely on the column default.
        estimated_cost=Decimal("0.00"),
    )
    test_db.add(job)
    await test_db.commit()
    await test_db.refresh(job)
    return job


@pytest.fixture
async def test_consumable(test_db):
    """Create a test consumable item."""
    from app.models.makerspace import ConsumableItem, ConsumableUnit

    consumable = ConsumableItem(
        name="PLA Filament - White",
        description="1.75mm PLA filament, 1kg spool",
        unit=ConsumableUnit.grams,
        cost_per_unit=Decimal("0.03"),
        quantity_in_stock=Decimal("5000"),
        reorder_threshold=Decimal("500"),
        is_active=True,
    )
    test_db.add(consumable)
    await test_db.commit()
    await test_db.refresh(consumable)
    return consumable


async def get_staff_token(client, test_staff_data):
    """Helper to get staff authentication token."""
    login_data = {
        "username": test_staff_data["email"],
        "password": test_staff_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


async def get_patron_token(client, test_user_data):
    """Helper to get patron authentication token."""
    login_data = {
        "username": test_user_data["email"],
        "password": test_user_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


@pytest.mark.integration
class TestMakerspaceResources:
    """Test makerspace resource endpoints."""

    async def test_list_resources(self, client, test_makerspace_resource):
        """Test listing makerspace resources."""
        response = await client.get("/api/v1/makerspace/resources")
        assert response.status_code == 200
        # PaginatedMakerspaceResourceSummaryResponse envelope key is "data",
        # not "items" (app/api/v1/makerspace.py list_resources).
        data = response.json()["data"]
        assert len(data) >= 1
        assert any(r["name"] == "Prusa MK4" for r in data)

    async def test_get_resource_detail(self, client, test_makerspace_resource):
        """Test getting resource details."""
        response = await client.get(f"/api/v1/makerspace/resources/{test_makerspace_resource.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Prusa MK4"
        assert data["resource_type"] == "printer_3d"

    async def test_get_resource_not_found(self, client):
        """Test getting non-existent resource."""
        response = await client.get("/api/v1/makerspace/resources/99999")
        assert response.status_code == 404

    async def test_get_resource_availability(self, client, test_makerspace_resource):
        """Test getting resource availability."""
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = await client.get(
            f"/api/v1/makerspace/resources/{test_makerspace_resource.id}/availability?target_date={date}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "available_slots" in data or "slots" in data


@pytest.mark.integration
class TestMakerspaceCertifications:
    """Test certification endpoints."""

    async def test_list_certification_types(self, client, test_certification_type):
        """Test listing certification types."""
        response = await client.get("/api/v1/makerspace/certifications/types")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(ct["name"] == "Laser Cutter Safety Certification" for ct in data)

    async def test_get_my_certifications_requires_auth(self, client):
        """Test that getting certifications requires authentication."""
        response = await client.get("/api/v1/makerspace/my/certifications")
        assert response.status_code == 401

    async def test_get_my_certifications(
        self, client, test_patron, test_user_data, test_patron_certification
    ):
        """Test patron can view their certifications."""
        token = await get_patron_token(client, test_user_data)
        response = await client.get(
            "/api/v1/makerspace/my/certifications",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_enroll_in_certification(
        self, client, test_patron, test_user_data, test_certification_type
    ):
        """Test enrolling in a certification."""
        token = await get_patron_token(client, test_user_data)
        response = await client.post(
            f"/api/v1/makerspace/certifications/enroll/{test_certification_type.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should either succeed or fail if already enrolled
        assert response.status_code in [200, 201, 400]


@pytest.mark.integration
class TestMakerspaceReservations:
    """Test reservation endpoints."""

    async def test_get_my_reservations_requires_auth(self, client):
        """Test that getting reservations requires authentication."""
        response = await client.get("/api/v1/makerspace/my/reservations")
        assert response.status_code == 401

    async def test_get_my_reservations(self, client, test_patron, test_user_data, test_reservation):
        """Test patron can view their reservations."""
        token = await get_patron_token(client, test_user_data)
        response = await client.get(
            "/api/v1/makerspace/my/reservations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_create_reservation(
        self, client, test_patron, test_user_data, test_makerspace_resource
    ):
        """Test creating a reservation."""
        token = await get_patron_token(client, test_user_data)
        start_time = datetime.now() + timedelta(days=2)
        end_time = start_time + timedelta(hours=2)

        reservation_data = {
            "resource_id": test_makerspace_resource.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "notes": "Test reservation",
        }
        response = await client.post(
            "/api/v1/makerspace/reservations",
            json=reservation_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["resource_id"] == test_makerspace_resource.id

    async def test_create_reservation_for_unavailable_resource(
        self, client, test_db, test_patron, test_user_data, test_makerspace_resource
    ):
        """Test creating reservation for unavailable resource fails."""
        from app.models.makerspace import ResourceStatus

        # Mark resource as maintenance
        test_makerspace_resource.status = ResourceStatus.maintenance
        await test_db.commit()

        token = await get_patron_token(client, test_user_data)
        start_time = datetime.now() + timedelta(days=3)
        end_time = start_time + timedelta(hours=2)

        reservation_data = {
            "resource_id": test_makerspace_resource.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }
        response = await client.post(
            "/api/v1/makerspace/reservations",
            json=reservation_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400


@pytest.mark.integration
class TestMakerspaceJobs:
    """Test job queue endpoints."""

    async def test_get_my_jobs_requires_auth(self, client):
        """Test that getting jobs requires authentication."""
        response = await client.get("/api/v1/makerspace/my/jobs")
        assert response.status_code == 401

    async def test_get_my_jobs(self, client, test_patron, test_user_data, test_makerspace_job):
        """Test patron can view their jobs."""
        token = await get_patron_token(client, test_user_data)
        response = await client.get(
            "/api/v1/makerspace/my/jobs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_submit_job(self, client, test_patron, test_user_data, test_makerspace_resource):
        """Test submitting a print job."""
        token = await get_patron_token(client, test_user_data)
        job_data = {
            "resource_id": test_makerspace_resource.id,
            "project_name": "Blue PLA Test Print",
            "notes": "Please print in blue PLA",
        }
        response = await client.post(
            "/api/v1/makerspace/jobs",
            json=job_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in [200, 201]
        data = response.json()
        # JobQueueService.submit() sets the initial status to "submitted",
        # not "pending_review" (app/services/makerspace/job_queue_service.py).
        assert data["status"] == "submitted"

    async def test_get_queue_status(self, client, test_makerspace_job):
        """Test getting queue status."""
        response = await client.get("/api/v1/makerspace/queue")
        assert response.status_code == 200
        data = response.json()
        # QueueStatusResponse's real key is "total_jobs", not "queue_length".
        assert "total_jobs" in data


@pytest.mark.integration
class TestStaffMakerspaceManagement:
    """Test staff makerspace management endpoints."""

    async def test_staff_list_resources(
        self, client, test_staff, test_staff_data, test_makerspace_resource
    ):
        """Test staff can list all resources."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/makerspace/resources",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_staff_create_resource(self, client, test_staff, test_staff_data):
        """Test staff can create a resource."""
        token = await get_staff_token(client, test_staff_data)
        resource_data = {
            "name": "New 3D Printer",
            "resource_type": "printer_3d",
            "description": "A brand new 3D printer",
            "location": "Makerspace Room C",
            "status": "available",
            "requires_certification": False,
            "hourly_cost": "3.00",
        }
        response = await client.post(
            "/api/v1/staff/makerspace/resources",
            json=resource_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "New 3D Printer"

    async def test_staff_update_resource(
        self, client, test_staff, test_staff_data, test_makerspace_resource
    ):
        """Test staff can update a resource."""
        token = await get_staff_token(client, test_staff_data)
        update_data = {
            "name": "Prusa MK4 Updated",
            "description": "Updated description",
        }
        # The resource-update route is PUT, not PATCH (PATCH is reserved
        # for the separate .../status sub-route).
        response = await client.put(
            f"/api/v1/staff/makerspace/resources/{test_makerspace_resource.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Prusa MK4 Updated"

    async def test_patron_cannot_create_resource(self, client, test_patron, test_user_data):
        """Test that patrons cannot create resources."""
        token = await get_patron_token(client, test_user_data)
        resource_data = {
            "name": "Unauthorized Resource",
            "resource_type": "printer_3d",
            "description": "Should not be created",
        }
        response = await client.post(
            "/api/v1/staff/makerspace/resources",
            json=resource_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestStaffJobManagement:
    """Test staff job queue management endpoints."""

    async def test_staff_list_jobs(self, client, test_staff, test_staff_data, test_makerspace_job):
        """Test staff can list all jobs."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/makerspace/jobs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_staff_approve_job(
        self, client, test_staff, test_staff_data, test_makerspace_job
    ):
        """Test staff can approve a job."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/makerspace/jobs/{test_makerspace_job.id}/review",
            json={"approved": True, "notes": "Looks good"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["approved", "queued"]

    async def test_staff_reject_job(
        self, client, test_db, test_staff, test_staff_data, test_makerspace_resource
    ):
        """Test staff can reject a job."""
        from app.models.makerspace import MakerspaceJob, JobStatus, JobPriority
        from app.models.user import User

        # Create a new job to reject
        # First, get a user
        user = await test_db.get(User, 1)
        if not user:
            from app.core.security import hash_password
            from app.models.user import UserRole

            user = User(
                email="jobuser@example.com",
                password_hash=hash_password("TestPassword123!"),
                first_name="Job",
                last_name="User",
                role=UserRole.PATRON,
                is_active=True,
                email_verified=True,
            )
            test_db.add(user)
            await test_db.commit()
            await test_db.refresh(user)

        job = MakerspaceJob(
            job_number="JOB-20260101-REJECT1",
            user_id=user.id,
            resource_id=test_makerspace_resource.id,
            project_name="Reject Test Print",
            file_path="/uploads/reject-test.stl",
            status=JobStatus.pending_review,
            priority=JobPriority.normal,
            estimated_cost=Decimal("0.00"),
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)

        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/makerspace/jobs/{job.id}/review",
            json={"approved": False, "notes": "File not suitable for printing"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_staff_start_job(
        self, client, test_db, test_staff, test_staff_data, test_makerspace_job
    ):
        """Test staff can start a job."""
        from app.models.makerspace import JobStatus

        # First approve the job
        test_makerspace_job.status = JobStatus.queued
        await test_db.commit()

        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/makerspace/jobs/{test_makerspace_job.id}/start",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    async def test_staff_complete_job(
        self, client, test_db, test_staff, test_staff_data, test_makerspace_job
    ):
        """Test staff can complete a job."""
        from app.models.makerspace import JobStatus

        # Set job to in_progress
        test_makerspace_job.status = JobStatus.in_progress
        await test_db.commit()

        token = await get_staff_token(client, test_staff_data)
        # JobComplete requires actual_print_time_minutes + actual_material_grams
        # (both required, no default).
        response = await client.post(
            f"/api/v1/staff/makerspace/jobs/{test_makerspace_job.id}/complete",
            json={"actual_print_time_minutes": 90, "actual_material_grams": "25.5"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_staff_mark_ready_for_pickup(
        self, client, test_db, test_staff, test_staff_data, test_makerspace_job
    ):
        """Test staff can mark job ready for pickup."""
        from app.models.makerspace import JobStatus

        # Set job to completed
        test_makerspace_job.status = JobStatus.completed
        await test_db.commit()

        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/makerspace/jobs/{test_makerspace_job.id}/ready-pickup",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        # JobStatus.ready_pickup == "ready_pickup" (the column is ready_for_pickup_at,
        # the status is not); the makerspace frontend keys off "ready_pickup" too.
        assert data["status"] == "ready_pickup"


@pytest.mark.integration
class TestStaffCertificationManagement:
    """Test staff certification management endpoints."""

    async def test_staff_certify_patron(
        self, client, test_db, test_staff, test_staff_data, test_patron, test_certification_type
    ):
        """Test staff can certify a patron."""
        token = await get_staff_token(client, test_staff_data)
        # certify_user (app/api/v1/staff_makerspace.py) takes user_id in the
        # path and certification_type_id/notes as query params, not a JSON
        # body -- there's no POST /certifications collection endpoint.
        response = await client.post(
            f"/api/v1/staff/makerspace/certifications/{test_patron.id}/certify"
            f"?certification_type_id={test_certification_type.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # May return 200/201 for success or 400 if already certified
        assert response.status_code in [200, 201, 400]


@pytest.mark.integration
class TestStaffConsumablesManagement:
    """Test staff consumables management endpoints."""

    async def test_staff_list_consumables(
        self, client, test_staff, test_staff_data, test_consumable
    ):
        """Test staff can list consumables."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/makerspace/consumables",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_staff_create_consumable(self, client, test_staff, test_staff_data):
        """Test staff can create a consumable."""
        token = await get_staff_token(client, test_staff_data)
        consumable_data = {
            "name": "PETG Filament - Black",
            "description": "1.75mm PETG filament, 1kg spool",
            "unit": "grams",
            "cost_per_unit": "0.04",
            "quantity_in_stock": "3000",
            "reorder_threshold": "500",
        }
        response = await client.post(
            "/api/v1/staff/makerspace/consumables",
            json=consumable_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in [200, 201]

    async def test_staff_update_consumable_stock(
        self, client, test_staff, test_staff_data, test_consumable
    ):
        """Test staff can update consumable stock."""
        token = await get_staff_token(client, test_staff_data)
        # Stock changes go through the dedicated adjust-stock action
        # (app/api/v1/staff_makerspace.py adjust_consumable_stock,
        # ConsumableStockAdjustment: quantity delta + reason), not a
        # PATCH on the base resource -- there is no PATCH route at all
        # (base update is PUT, and it doesn't accept a bare stock delta).
        adjust_data = {
            "quantity": "500",
            "reason": "Restock",
        }
        response = await client.post(
            f"/api/v1/staff/makerspace/consumables/{test_consumable.id}/adjust-stock",
            json=adjust_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestStaffReservationManagement:
    """Test staff reservation management endpoints."""

    async def test_staff_list_reservations(
        self, client, test_staff, test_staff_data, test_reservation
    ):
        """Test staff can list all reservations."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/makerspace/reservations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_staff_approve_reservation(
        self, client, test_db, test_staff, test_staff_data, test_reservation
    ):
        """Test staff can approve a reservation."""
        from app.models.makerspace import MakerspaceReservationStatus

        # Set to pending for approval
        test_reservation.status = MakerspaceReservationStatus.pending
        await test_db.commit()

        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/makerspace/reservations/{test_reservation.id}/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_staff_check_in_reservation(
        self, client, test_staff, test_staff_data, test_reservation
    ):
        """Test staff can check in a reservation."""
        token = await get_staff_token(client, test_staff_data)
        # check_in_reservation requires a ReservationCheckIn body (all
        # fields optional, but FastAPI still needs *a* JSON body to parse
        # into the model -- an empty POST with no json= 422s).
        response = await client.post(
            f"/api/v1/staff/makerspace/reservations/{test_reservation.id}/check-in",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestMakerspaceReports:
    """Test makerspace reports endpoints."""

    async def test_staff_utilization_report(
        self, client, test_staff, test_staff_data, test_reservation
    ):
        """Test staff can get utilization report."""
        # start_date/end_date are required query params on every report
        # endpoint below (app/api/v1/staff_makerspace.py).
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            f"/api/v1/staff/makerspace/reports/utilization?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_staff_revenue_report(self, client, test_staff, test_staff_data):
        """Test staff can get revenue report."""
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            f"/api/v1/staff/makerspace/reports/revenue?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_staff_popular_equipment_report(
        self, client, test_staff, test_staff_data, test_reservation
    ):
        """Test staff can get popular equipment report."""
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            f"/api/v1/staff/makerspace/reports/popular-equipment?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_patron_cannot_access_reports(self, client, test_patron, test_user_data):
        """Test that patrons cannot access reports."""
        token = await get_patron_token(client, test_user_data)
        response = await client.get(
            "/api/v1/staff/makerspace/reports/utilization",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestSafetyIncidents:
    """Test safety incident endpoints."""

    async def test_staff_create_incident(
        self, client, test_staff, test_staff_data, test_makerspace_resource, test_patron
    ):
        """Test staff can create a safety incident."""
        token = await get_staff_token(client, test_staff_data)
        # SafetyIncidentCreate/SafetyIncidentBase (StrictInputSchema, extra
        # fields forbidden) require incident_date + title, and use
        # involved_user_id / immediate_action_taken -- not user_id /
        # action_taken.
        incident_data = {
            "resource_id": test_makerspace_resource.id,
            "involved_user_id": test_patron.id,
            "incident_date": datetime.now().isoformat(),
            "title": "Minor burn from heated bed",
            "description": "Minor burn from heated bed",
            "severity": "minor",
            "immediate_action_taken": "First aid administered, patron instructed on safety procedures",
        }
        response = await client.post(
            "/api/v1/staff/makerspace/incidents",
            json=incident_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in [200, 201]

    async def test_staff_list_incidents(self, client, test_staff, test_staff_data):
        """Test staff can list safety incidents."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/makerspace/incidents",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestEquipmentMaintenance:
    """Test equipment maintenance endpoints."""

    async def test_staff_schedule_maintenance(
        self, client, test_staff, test_staff_data, test_makerspace_resource
    ):
        """Test staff can schedule maintenance."""
        token = await get_staff_token(client, test_staff_data)
        maintenance_data = {
            "resource_id": test_makerspace_resource.id,
            "maintenance_type": "preventive",
            "title": "Monthly calibration",
            "description": "Monthly calibration and cleaning",
            "scheduled_date": (datetime.now() + timedelta(days=7)).date().isoformat(),
        }
        response = await client.post(
            "/api/v1/staff/makerspace/maintenance",
            json=maintenance_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in [200, 201]

    async def test_staff_list_maintenance(self, client, test_staff, test_staff_data):
        """Test staff can list maintenance records."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/makerspace/maintenance",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestCostCalculation:
    """Test cost calculation endpoints."""

    async def test_calculate_cost(
        self, client, test_patron, test_user_data, test_makerspace_resource
    ):
        """Test calculating cost for a job."""
        token = await get_patron_token(client, test_user_data)
        # CostCalculationRequest (StrictInputSchema) wants duration_hours,
        # not estimated_duration_minutes.
        cost_data = {
            "resource_id": test_makerspace_resource.id,
            "duration_hours": 2,
            "consumables": [],
        }
        response = await client.post(
            "/api/v1/makerspace/calculate-cost",
            json=cost_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_cost" in data or "estimated_cost" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_walk_in_queue_sends_sms_notification(test_db, test_patron):
    """Test that walk-in queue notifications send SMS via SMSService."""
    from app.models.room import Room, RoomQueue
    from app.models.sms import SMSNotificationType
    from app.services.walk_in_service import notify_queue_patrons
    from app.services.sms_service import SMSService

    # Create a test room with walk-in enabled
    room = Room(
        name="Study Room A",
        capacity=4,
        is_active=True,
        is_walkable=True,
        walk_in_enabled=True,
        walk_in_duration_minutes=60,
        max_concurrent_walkins=2,
        walkout_grace_minutes=15,
    )
    test_db.add(room)
    await test_db.commit()
    await test_db.refresh(room)

    # Give patron a phone number
    test_patron.phone = "+15555551234"
    await test_db.commit()

    # Create a queued walk-in reservation
    queue_entry = RoomQueue(
        room_id=room.id,
        patron_id=test_patron.id,
        position=1,
    )
    test_db.add(queue_entry)
    await test_db.commit()
    await test_db.refresh(queue_entry)

    # Mock SMSService.queue_sms
    with patch.object(SMSService, "queue_sms", new_callable=AsyncMock) as mock_queue_sms:
        # Call notify_queue_patrons
        count = await notify_queue_patrons(test_db, room.id)

        # Assert SMSService.queue_sms was called
        assert mock_queue_sms.called, "SMSService.queue_sms should have been called"

        # Get the call arguments
        call_args = mock_queue_sms.call_args
        assert call_args is not None, "queue_sms should have been called with arguments"

        # Check positional and keyword arguments
        kwargs = call_args.kwargs if call_args.kwargs else {}

        # Assert correct arguments
        assert kwargs.get("user_id") == test_patron.id, "Should send to correct patron"
        assert kwargs.get("phone_number") == test_patron.phone, "Should use patron's phone number"
        assert kwargs.get("notification_type") == SMSNotificationType.WALK_IN_ALERT, (
            "Should use WALK_IN_ALERT notification type"
        )

        # Check message contains expected content
        message = kwargs.get("message", "")
        assert "ready" in message.lower() or "reservation" in message.lower(), (
            "Message should mention ready or reservation"
        )
        assert room.name in message, "Message should include room name"

        # Check bypass flags
        assert kwargs.get("check_opt_out") == False, (
            "Should bypass opt-out for emergency notification"
        )
        assert kwargs.get("check_dnd") == False, "Should bypass DND for emergency notification"

        # Check context data
        context_data = kwargs.get("context_data", {})
        assert context_data.get("room_id") == room.id, "Context should include room_id"
        assert context_data.get("room_name") == room.name, "Context should include room_name"
        assert "queue_position" in context_data, "Context should include queue_position"

        # Assert return value indicates notification was sent
        assert count > 0, "Should return count > 0 indicating notification was sent"
