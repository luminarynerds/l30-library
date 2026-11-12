# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Patron Home Delivery Request API Endpoints

Tests patron delivery request functionality:
- Creating delivery requests from items
- Patrons viewing their requests
- Staff approving/declining requests
- Status tracking and transitions
"""
import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User,
    UserRole,
    CatalogItem,
    DeliveryRequest,
    DeliveryRequestStatus,
)
from app.models.home_delivery import DeliveryFrequency


@pytest.fixture(autouse=True)
def _override_auth(request):
    """Swap `get_current_user` to return whichever user a test's headers
    imply, keyed off which fixture (`test_staff`/`test_patron`) the test
    requested. `client.headers["Authorization"] = f"Bearer {user.id}"`
    doesn't work standalone -- that's not a real JWT, and JWT verification
    falls through to `is_token_revoked()`, which is fail-secure when Redis
    is unavailable in host-venv test runs. See tests/api/v1/test_blog.py's
    `_override_auth` for the same pattern.
    """
    from app.main import app
    from app.api.v1.auth.helpers import get_current_user

    chosen = None
    if "test_staff" in request.fixturenames:
        chosen = request.getfixturevalue("test_staff")
    elif "test_patron" in request.fixturenames:
        chosen = request.getfixturevalue("test_patron")

    if chosen is None:
        yield
        return

    async def _override():
        return chosen

    app.dependency_overrides[get_current_user] = _override
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def test_patron(db: AsyncSession) -> User:
    """Create a test patron."""
    patron = User(
        email="patron@example.com",
        password_hash="hashed",
        first_name="John",
        last_name="Doe",
        role=UserRole.PATRON,
    )
    db.add(patron)
    await db.commit()
    await db.refresh(patron)
    return patron


@pytest.fixture
async def test_staff(db: AsyncSession) -> User:
    """Create a test staff member."""
    staff = User(
        email="staff@example.com",
        password_hash="hashed",
        first_name="Jane",
        last_name="Staff",
        role=UserRole.STAFF,
    )
    db.add(staff)
    await db.commit()
    await db.refresh(staff)
    return staff


@pytest.fixture
async def test_item(db: AsyncSession) -> CatalogItem:
    """Create a test catalog item."""
    item = CatalogItem(
        title="Test Book",
        author="Test Author",
        isbn="123456789",
        item_type="book",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


class TestDeliveryRequestCreate:
    """Test creating delivery requests."""

    async def test_create_delivery_request_requires_auth(
        self, client: AsyncClient
    ):
        """Unauthenticated request should fail."""
        response = await client.post(
            "/api/v1/delivery-requests",
            json={
                "item_id": 1,
                "frequency": "on_demand",
            },
        )
        assert response.status_code == 401

    async def test_create_delivery_request_patron_only(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_staff: User,
        test_item: CatalogItem,
    ):
        """Non-patron roles should not be able to create delivery requests."""
        client.headers["Authorization"] = f"Bearer {test_staff.id}"
        response = await client.post(
            "/api/v1/delivery-requests",
            json={
                "item_id": test_item.id,
                "frequency": "on_demand",
            },
        )
        # Staff should have require_patron check fail
        assert response.status_code == 403

    async def test_create_delivery_request_success(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Patron should be able to create a delivery request."""
        client.headers["Authorization"] = f"Bearer {test_patron.id}"
        response = await client.post(
            "/api/v1/delivery-requests",
            json={
                "item_id": test_item.id,
                "frequency": "on_demand",
                "delivery_notes": "Please leave at door",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["item_id"] == test_item.id
        assert data["status"] == "pending"
        assert data["frequency"] == "on_demand"
        assert data["delivery_notes"] == "Please leave at door"

    async def test_create_delivery_request_invalid_item(
        self,
        client: AsyncClient,
        test_patron: User,
    ):
        """Creating request for non-existent item should fail."""
        client.headers["Authorization"] = f"Bearer {test_patron.id}"
        response = await client.post(
            "/api/v1/delivery-requests",
            json={
                "item_id": 99999,
                "frequency": "on_demand",
            },
        )
        assert response.status_code == 404

    async def test_create_delivery_request_prevents_duplicates(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Should prevent active requests for same item."""
        client.headers["Authorization"] = f"Bearer {test_patron.id}"

        # First request should succeed
        response1 = await client.post(
            "/api/v1/delivery-requests",
            json={
                "item_id": test_item.id,
                "frequency": "on_demand",
            },
        )
        assert response1.status_code == 201

        # Second request for same item should fail
        response2 = await client.post(
            "/api/v1/delivery-requests",
            json={
                "item_id": test_item.id,
                "frequency": "weekly",
            },
        )
        assert response2.status_code == 409


class TestDeliveryRequestPatronView:
    """Test patron viewing their requests."""

    async def test_get_my_delivery_requests(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Patron should see their delivery requests."""
        # Create a delivery request
        dr = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.pending,
            frequency=DeliveryFrequency.on_demand,
        )
        db.add(dr)
        await db.commit()

        client.headers["Authorization"] = f"Bearer {test_patron.id}"
        response = await client.get("/api/v1/delivery-requests/me")
        assert response.status_code == 200
        requests = response.json()
        assert len(requests) > 0
        assert requests[0]["item_id"] == test_item.id
        assert requests[0]["status"] == "pending"

    async def test_get_my_delivery_requests_with_status_filter(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Should filter by status."""
        # Create requests with different statuses
        dr1 = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.pending,
            frequency=DeliveryFrequency.on_demand,
        )
        dr2 = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.approved,
            frequency=DeliveryFrequency.weekly,
            approved_at=datetime.now(timezone.utc),
        )
        db.add_all([dr1, dr2])
        await db.commit()

        client.headers["Authorization"] = f"Bearer {test_patron.id}"
        response = await client.get(
            "/api/v1/delivery-requests/me?status=pending"
        )
        assert response.status_code == 200
        requests = response.json()
        assert len(requests) == 1
        assert requests[0]["status"] == "pending"

    async def test_get_specific_request(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Should get specific request."""
        dr = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.pending,
            frequency=DeliveryFrequency.on_demand,
        )
        db.add(dr)
        await db.commit()
        await db.refresh(dr)

        client.headers["Authorization"] = f"Bearer {test_patron.id}"
        response = await client.get(f"/api/v1/delivery-requests/{dr.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == dr.id

    async def test_cannot_view_others_requests(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Patron cannot view another patron's request."""
        # Create another patron
        other_patron = User(
            email="other@example.com",
            password_hash="hashed",
            first_name="Other",
            last_name="Patron",
            role=UserRole.PATRON,
        )
        db.add(other_patron)
        await db.commit()
        await db.refresh(other_patron)

        # Create request from other patron
        dr = DeliveryRequest(
            user_id=other_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.pending,
            frequency=DeliveryFrequency.on_demand,
        )
        db.add(dr)
        await db.commit()
        await db.refresh(dr)

        # Try to access as different patron
        client.headers["Authorization"] = f"Bearer {test_patron.id}"
        response = await client.get(f"/api/v1/delivery-requests/{dr.id}")
        assert response.status_code == 403


class TestDeliveryRequestPatronCancel:
    """Test patron cancelling requests."""

    async def test_cancel_pending_request(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Patron should be able to cancel pending request."""
        dr = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.pending,
            frequency=DeliveryFrequency.on_demand,
        )
        db.add(dr)
        await db.commit()
        await db.refresh(dr)

        client.headers["Authorization"] = f"Bearer {test_patron.id}"
        response = await client.patch(f"/api/v1/delivery-requests/{dr.id}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["cancelled_at"] is not None

    async def test_cannot_cancel_completed_request(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Cannot cancel already completed request."""
        dr = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.completed,
            frequency=DeliveryFrequency.on_demand,
            delivered_at=datetime.now(timezone.utc),
        )
        db.add(dr)
        await db.commit()
        await db.refresh(dr)

        client.headers["Authorization"] = f"Bearer {test_patron.id}"
        response = await client.patch(f"/api/v1/delivery-requests/{dr.id}/cancel")
        assert response.status_code == 400


class TestStaffDeliveryRequestManagement:
    """Test staff managing delivery requests."""

    async def test_staff_list_requests(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_staff: User,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Staff should be able to list requests."""
        dr = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.pending,
            frequency=DeliveryFrequency.on_demand,
        )
        db.add(dr)
        await db.commit()

        client.headers["Authorization"] = f"Bearer {test_staff.id}"
        response = await client.get("/api/v1/delivery-requests")
        assert response.status_code == 200
        requests = response.json()
        assert len(requests) > 0

    async def test_staff_list_requests_by_status(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_staff: User,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Staff should filter by status."""
        dr1 = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.pending,
            frequency=DeliveryFrequency.on_demand,
        )
        dr2 = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.approved,
            frequency=DeliveryFrequency.weekly,
            approved_at=datetime.now(timezone.utc),
        )
        db.add_all([dr1, dr2])
        await db.commit()

        client.headers["Authorization"] = f"Bearer {test_staff.id}"
        response = await client.get(
            "/api/v1/delivery-requests?status=pending"
        )
        assert response.status_code == 200
        requests = response.json()
        assert len(requests) == 1
        assert requests[0]["status"] == "pending"

    async def test_staff_approve_request(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_staff: User,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Staff should be able to approve pending requests."""
        dr = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.pending,
            frequency=DeliveryFrequency.on_demand,
        )
        db.add(dr)
        await db.commit()
        await db.refresh(dr)

        client.headers["Authorization"] = f"Bearer {test_staff.id}"
        response = await client.patch(
            f"/api/v1/delivery-requests/{dr.id}/approve",
            json={"notes": "Approved for delivery"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approved_at"] is not None
        assert data["approved_by_id"] == test_staff.id

    async def test_staff_decline_request(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_staff: User,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Staff should be able to decline pending requests."""
        dr = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.pending,
            frequency=DeliveryFrequency.on_demand,
        )
        db.add(dr)
        await db.commit()
        await db.refresh(dr)

        client.headers["Authorization"] = f"Bearer {test_staff.id}"
        response = await client.patch(
            f"/api/v1/delivery-requests/{dr.id}/decline",
            json={"reason": "Item not available for delivery"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "declined"
        assert data["declined_at"] is not None
        assert data["decline_reason"] == "Item not available for delivery"

    async def test_staff_mark_in_delivery(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_staff: User,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Staff should be able to mark request as in_delivery."""
        dr = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.approved,
            frequency=DeliveryFrequency.on_demand,
            approved_at=datetime.now(timezone.utc),
        )
        db.add(dr)
        await db.commit()
        await db.refresh(dr)

        client.headers["Authorization"] = f"Bearer {test_staff.id}"
        response = await client.patch(
            f"/api/v1/delivery-requests/{dr.id}/mark-in-delivery"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_delivery"

    async def test_staff_mark_delivered(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_staff: User,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Staff should be able to mark request as completed."""
        dr = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.in_delivery,
            frequency=DeliveryFrequency.on_demand,
        )
        db.add(dr)
        await db.commit()
        await db.refresh(dr)

        client.headers["Authorization"] = f"Bearer {test_staff.id}"
        response = await client.patch(
            f"/api/v1/delivery-requests/{dr.id}/mark-delivered"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["delivered_at"] is not None


class TestStatusTransitions:
    """Test valid status transitions."""

    async def test_cannot_approve_already_approved(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_staff: User,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Cannot approve already approved request."""
        dr = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.approved,
            frequency=DeliveryFrequency.on_demand,
            approved_at=datetime.now(timezone.utc),
        )
        db.add(dr)
        await db.commit()
        await db.refresh(dr)

        client.headers["Authorization"] = f"Bearer {test_staff.id}"
        response = await client.patch(
            f"/api/v1/delivery-requests/{dr.id}/approve",
            json={},
        )
        assert response.status_code == 400

    async def test_cannot_mark_declined_as_in_delivery(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_staff: User,
        test_patron: User,
        test_item: CatalogItem,
    ):
        """Cannot mark declined request as in_delivery."""
        dr = DeliveryRequest(
            user_id=test_patron.id,
            item_id=test_item.id,
            status=DeliveryRequestStatus.declined,
            frequency=DeliveryFrequency.on_demand,
            declined_at=datetime.now(timezone.utc),
        )
        db.add(dr)
        await db.commit()
        await db.refresh(dr)

        client.headers["Authorization"] = f"Bearer {test_staff.id}"
        response = await client.patch(
            f"/api/v1/delivery-requests/{dr.id}/mark-in-delivery"
        )
        assert response.status_code == 400
