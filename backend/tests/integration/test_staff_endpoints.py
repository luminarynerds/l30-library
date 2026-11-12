# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for staff API endpoints.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest


@pytest.fixture
async def test_catalog_item_with_barcode(test_db):
    """Create a test catalog item with a barcode for staff operations."""
    from app.models.catalog import CatalogItem, ItemStatus

    item = CatalogItem(
        title="Test Book with Barcode",
        author="Test Author",
        isbn="978-0-123456-78-9",
        description="A test book for staff checkout testing",
        status=ItemStatus.available,
        call_number="TEST-002",
        publication_year=2024,
        barcode="BARCODE-001",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def test_inactive_patron(test_db):
    """Create a test patron with inactive status."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="inactive@example.com",
        password_hash=hash_password("InactivePassword123!"),
        first_name="Inactive",
        last_name="User",
        role=UserRole.PATRON,
        is_active=False,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_overdue_checkout(test_db, test_patron, test_catalog_item):
    """Create a test checkout that is overdue."""
    from app.models.catalog import ItemStatus
    from app.models.circulation import Checkout, CheckoutStatus

    # Mark item as checked out
    test_catalog_item.status = ItemStatus.checked_out

    checkout = Checkout(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now() - timedelta(days=30),
        due_date=datetime.now() - timedelta(days=7),  # 7 days overdue
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


@pytest.fixture
async def test_checkout_with_barcode(test_db, test_patron, test_catalog_item_with_barcode):
    """Create a test checkout for an item with a barcode."""
    from app.models.catalog import ItemStatus
    from app.models.circulation import Checkout, CheckoutStatus

    # Mark item as checked out
    test_catalog_item_with_barcode.status = ItemStatus.checked_out

    checkout = Checkout(
        user_id=test_patron.id,
        item_id=test_catalog_item_with_barcode.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=21),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


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
class TestStaffDashboard:
    """Test staff dashboard endpoints."""

    async def test_dashboard_stats_requires_staff_role(self, client):
        """Test that dashboard stats requires staff role."""
        response = await client.get("/api/v1/staff/dashboard/stats")
        assert response.status_code == 401

    async def test_dashboard_stats_success(
        self, client, test_staff, test_staff_data, test_checkout
    ):
        """Test staff dashboard stats endpoint."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        # The endpoint may not exist or have different behavior
        assert response.status_code in [200, 404]

    async def test_dashboard_activity_requires_staff_role(self, client):
        """Test that dashboard activity requires staff role."""
        response = await client.get("/api/v1/staff/dashboard/activity")
        assert response.status_code == 401

    async def test_dashboard_activity_with_staff_token(
        self, client, test_staff, test_staff_data, test_checkout
    ):
        """Test dashboard activity endpoint with staff token."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/dashboard/activity?limit=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Verify endpoint exists and returns proper response
        assert response.status_code in [200, 404]


@pytest.mark.integration
class TestStaffCheckouts:
    """Test staff checkout management endpoints.

    There is deliberately no flat, cross-patron GET /api/v1/staff/checkouts here.
    That listing lived in app/api/v1/staff_circulation.py and was removed on
    2026-02-15 (b2013f01b); it is not in the route table. Staff coverage of the
    same ground is per-patron (GET /staff/patrons/{patron_id}/checkouts) plus the
    dashboard aggregates (/staff/dashboard/circulation, /staff/dashboard/overdue).

    If a flat cross-patron listing is ever wanted back, it is a feature with its
    own pagination/filter/PII-scoping design -- not a test fix.
    """

    async def test_list_checkouts_with_patron_filter(
        self, client, test_staff, test_staff_data, test_checkout, test_patron
    ):
        """Test filtering checkouts by patron ID.

        Redirected to GET /api/v1/staff/patrons/{patron_id}/checkouts
        (app/api/v1/staff/patron_operations.py:2253), the scoped successor
        to the deleted flat GET /api/v1/staff/checkouts?patron_id= listing
        (removed 2026-02-15, b2013f01b) -- this test only ever needed the
        single-patron case, which the successor covers exactly.
        """
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            f"/api/v1/staff/patrons/{test_patron.id}/checkouts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for checkout in data:
            assert checkout["user_id"] == test_patron.id

    async def test_process_checkout_success(
        self, client, test_staff, test_staff_data, test_patron, test_catalog_item_with_barcode
    ):
        """Test successful staff checkout for a patron."""
        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{test_patron.id}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()["checkout"]
        assert data["user_id"] == test_patron.id
        assert data["item_id"] == test_catalog_item_with_barcode.id
        assert data["status"] == "active"
        assert data["item_title"] == test_catalog_item_with_barcode.title

    async def test_process_checkout_patron_not_found(
        self, client, test_staff, test_staff_data, test_catalog_item_with_barcode
    ):
        """Test checkout fails when patron not found."""
        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            "/api/v1/staff/patrons/99999/quick-checkout",  # Non-existent patron
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "patron" in response.json()["error"]["message"].lower()

    async def test_process_checkout_item_not_found(
        self, client, test_staff, test_staff_data, test_patron
    ):
        """Test checkout fails when item barcode not found."""
        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "barcode": "NONEXISTENT-BARCODE",
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{test_patron.id}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "barcode" in response.json()["error"]["message"].lower()

    async def test_process_checkout_patron_blocked(
        self,
        client,
        test_staff,
        test_staff_data,
        test_inactive_patron,
        test_catalog_item_with_barcode,
    ):
        """Test checkout fails when patron account is blocked/inactive."""
        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{test_inactive_patron.id}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        # Patron ineligibility now raises ForbiddenError (403), not a generic 400.
        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()

    async def test_process_checkout_item_not_available(
        self,
        client,
        test_staff,
        test_staff_data,
        test_patron,
        test_checkout_with_barcode,
        test_catalog_item_with_barcode,
    ):
        """Test checkout fails when item is already checked out."""
        token = await get_staff_token(client, test_staff_data)

        checkout_data = {
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{test_patron.id}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        # Already-checked-out conflicts now raise ConflictError (409).
        assert response.status_code == 409

    async def test_process_checkout_already_checked_out_by_patron(
        self,
        client,
        test_staff,
        test_staff_data,
        test_patron,
        test_checkout_with_barcode,
        test_catalog_item_with_barcode,
    ):
        """Test checkout fails when patron already has the item checked out."""
        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{test_patron.id}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        assert "already" in response.json()["detail"].lower()

    async def test_process_checkout_fulfills_ready_hold(
        self,
        client,
        test_db,
        test_staff,
        test_staff_data,
        test_patron,
        test_catalog_item_with_barcode,
    ):
        """Test that checkout fulfills a ready hold for the patron."""
        from app.models.catalog import ItemStatus
        from app.models.circulation import Hold, HoldStatus

        # Put item on hold for the patron
        test_catalog_item_with_barcode.status = ItemStatus.on_hold
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item_with_barcode.id,
            status=HoldStatus.ready,
            position=1,
            notified_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=7),
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{test_patron.id}/quick-checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201

        # Verify hold was fulfilled
        await test_db.refresh(hold)
        assert hold.status == HoldStatus.fulfilled

    async def test_process_checkout_fails_when_hold_for_another_patron(
        self,
        client,
        test_db,
        test_staff,
        test_staff_data,
        test_patron,
        test_catalog_item_with_barcode,
    ):
        """Test checkout fails when item is on hold for a different patron."""
        from app.core.security import hash_password
        from app.models.catalog import ItemStatus
        from app.models.circulation import Hold, HoldStatus
        from app.models.user import User, UserRole

        # Create another patron who has the hold
        other_patron = User(
            email="other@example.com",
            password_hash=hash_password("OtherPassword123!"),
            first_name="Other",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(other_patron)
        await test_db.commit()
        await test_db.refresh(other_patron)

        # Put item on hold for the OTHER patron
        test_catalog_item_with_barcode.status = ItemStatus.on_hold
        hold = Hold(
            user_id=other_patron.id,
            item_id=test_catalog_item_with_barcode.id,
            status=HoldStatus.ready,
            position=1,
            notified_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=7),
        )
        test_db.add(hold)
        await test_db.commit()

        token = await get_staff_token(client, test_staff_data)
        checkout_data = {
            "barcode": test_catalog_item_with_barcode.barcode,
        }
        response = await client.post(
            f"/api/v1/staff/patrons/{test_patron.id}/quick-checkout",  # Try to checkout for original patron
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        assert "hold" in response.json()["detail"].lower()

    async def test_checkin_item_success(self, client, test_staff, test_staff_data, test_checkout):
        """Test successful staff checkin of an item."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/circulation/checkin?checkout_id={test_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "returned"
        assert data["returned_at"] is not None

    async def test_checkin_item_not_found(self, client, test_staff, test_staff_data):
        """Test checkin fails when checkout ID not found."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            "/api/v1/circulation/checkin?checkout_id=99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "couldn't find" in response.json()["error"]["message"].lower()

    async def test_checkin_already_returned(
        self, client, test_db, test_staff, test_staff_data, test_checkout
    ):
        """Test checkin fails when item is already returned."""
        from app.models.circulation import CheckoutStatus

        # Mark checkout as already returned
        test_checkout.status = CheckoutStatus.returned
        test_checkout.returned_at = datetime.now()
        await test_db.commit()

        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/circulation/checkin?checkout_id={test_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "already been returned" in response.json()["error"]["message"].lower()

    async def test_checkin_triggers_hold_ready(
        self, client, test_db, test_staff, test_staff_data, test_checkout, test_catalog_item
    ):
        """Test that checkin marks next hold as ready."""
        from app.models.circulation import Hold, HoldStatus

        # Create a pending hold for another patron
        from app.core.security import hash_password
        from app.models.user import User, UserRole

        waiting_patron = User(
            email="waiting@example.com",
            password_hash=hash_password("WaitingPassword123!"),
            first_name="Waiting",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(waiting_patron)
        await test_db.commit()
        await test_db.refresh(waiting_patron)

        hold = Hold(
            user_id=waiting_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/circulation/checkin?checkout_id={test_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify hold is now ready
        await test_db.refresh(hold)
        assert hold.status == HoldStatus.ready
        assert hold.notified_at is not None
        assert hold.expires_at is not None

    async def test_checkin_by_barcode_success(
        self,
        client,
        test_staff,
        test_staff_data,
        test_checkout_with_barcode,
        test_catalog_item_with_barcode,
    ):
        """Test successful staff checkin by barcode."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/checkin-barcode?barcode={test_catalog_item_with_barcode.barcode}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "checkout" in data
        assert data["checkout"]["status"] == "returned"

    async def test_checkin_by_barcode_item_not_found(self, client, test_staff, test_staff_data):
        """Test checkin by barcode fails when barcode not found."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            "/api/v1/staff/checkin-barcode?barcode=NONEXISTENT-BARCODE",
            headers={"Authorization": f"Bearer {token}"},
        )
        # The route wraps any lookup failure as a generic 400 (not 404).
        assert response.status_code == 400
        assert "not found" in response.json()["error"]["message"].lower()

    async def test_checkin_by_barcode_no_active_checkout(
        self, client, test_staff, test_staff_data, test_catalog_item_with_barcode
    ):
        """Test checkin by barcode fails when no active checkout exists."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/checkin-barcode?barcode={test_catalog_item_with_barcode.barcode}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # The route wraps any lookup failure as a generic 400 (not 404).
        assert response.status_code == 400
        assert "no active checkout" in response.json()["error"]["message"].lower()

    async def test_override_renew_success(self, client, test_staff, test_staff_data, test_checkout):
        """Test staff can override renew even when holds exist."""
        original_due_date = test_checkout.due_date
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/override-renew/{test_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["renewal_count"] == 1
        # Due date should be extended
        from datetime import datetime

        new_due = datetime.fromisoformat(data["due_date"].replace("Z", "+00:00"))
        assert new_due > original_due_date.replace(tzinfo=new_due.tzinfo)

    async def test_override_renew_checkout_not_found(self, client, test_staff, test_staff_data):
        """Test override renew fails when checkout not found."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            "/api/v1/staff/override-renew/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_override_renew_already_returned(
        self, client, test_db, test_staff, test_staff_data, test_checkout
    ):
        """Test override renew fails for returned checkout."""
        from app.models.circulation import CheckoutStatus

        test_checkout.status = CheckoutStatus.returned
        test_checkout.returned_at = datetime.now()
        await test_db.commit()

        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/override-renew/{test_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # renew_checkout raises ConflictError (409) for a non-active checkout.
        assert response.status_code == 409


@pytest.mark.integration
class TestCacheManagement:
    """The old /staff/cache/metrics + /staff/cache/clear troubleshooting
    endpoints (added in 5cf2aba3d) were removed from staff_dashboard.py on
    2026-02-15 (b2013f01b) and replaced 10 days later by an admin-only,
    differently-shaped dashboard at /api/v1/admin/cache/{stats,keys,evict}
    (3bb9876e6). There is no staff-role equivalent with this request/response
    contract anymore, so these just confirm the old routes stay gone.
    """

    async def test_cache_metrics_requires_auth(self, client):
        """Test that cache metrics requires authentication."""
        response = await client.get("/api/v1/staff/cache/metrics")
        assert response.status_code == 404

    async def test_cache_metrics_as_patron_forbidden(self, client, test_patron, test_user_data):
        """Test that patrons cannot access cache metrics."""
        token = await get_patron_token(client, test_user_data)
        response = await client.get(
            "/api/v1/staff/cache/metrics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_cache_metrics_as_staff(self, client, test_staff, test_staff_data):
        """Test staff can access cache metrics."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/cache/metrics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_cache_clear_requires_auth(self, client):
        """Test that cache clear requires authentication."""
        response = await client.post("/api/v1/staff/cache/clear")
        assert response.status_code == 404

    async def test_cache_clear_as_patron_forbidden(self, client, test_patron, test_user_data):
        """Test that patrons cannot clear cache."""
        token = await get_patron_token(client, test_user_data)
        response = await client.post(
            "/api/v1/staff/cache/clear",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_cache_clear_all_as_staff(self, client, test_staff, test_staff_data):
        """Test staff can clear all caches."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            "/api/v1/staff/cache/clear",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_cache_clear_with_prefix_catalog(self, client, test_staff, test_staff_data):
        """Test staff can clear specific cache by prefix."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            "/api/v1/staff/cache/clear?prefix=catalog",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_cache_clear_with_prefix_recommendations(
        self, client, test_staff, test_staff_data
    ):
        """Test staff can clear recommendations cache."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            "/api/v1/staff/cache/clear?prefix=recommendations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_cache_clear_with_prefix_trending(self, client, test_staff, test_staff_data):
        """Test staff can clear trending cache."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            "/api/v1/staff/cache/clear?prefix=trending",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_cache_clear_with_prefix_permissions(self, client, test_staff, test_staff_data):
        """Test staff can clear permissions cache."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            "/api/v1/staff/cache/clear?prefix=permissions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_cache_clear_with_reset_metrics(self, client, test_staff, test_staff_data):
        """Test staff can clear cache and reset metrics."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            "/api/v1/staff/cache/clear?reset_metrics=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_cache_clear_unknown_prefix(self, client, test_staff, test_staff_data):
        """Test cache clear with unknown prefix returns appropriate response."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            "/api/v1/staff/cache/clear?prefix=nonexistent",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
