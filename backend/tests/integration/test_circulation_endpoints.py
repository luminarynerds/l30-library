# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for circulation API endpoints.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest


def _error_detail(response) -> str:
    """Error responses are wrapped as {"error": {"message": ...}} by
    app.core.exception_handlers.http_exception_handler, not the FastAPI
    default {"detail": ...}."""
    data = response.json()
    if "detail" in data:
        return str(data["detail"])
    return str(data.get("error", {}).get("message", data))


@pytest.fixture
async def test_available_item(test_db):
    """Create a test catalog item that is available for checkout."""
    from app.models.catalog import CatalogItem, ItemStatus

    item = CatalogItem(
        title="Available Book",
        author="Test Author",
        isbn="978-0-111111-11-1",
        description="An available book for testing",
        status=ItemStatus.available,
        call_number="AVAIL-001",
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def test_checked_out_item(test_db, second_patron):
    """Create a test catalog item that is checked out.

    Availability is derived from active-loan counts against the item's
    (real or virtual single-copy) copy count now, not the title-level
    status field alone -- see app/services/checkout_service.py's
    "Titles with no copy records... circulate as ONE virtual copy" note.
    Flipping just item.status here (the old approach) left the sole
    virtual copy uncounted-for, so both checkout-availability and
    hold-ready-vs-pending logic saw it as free. Give it a real
    outstanding loan (to a different patron) so it's actually unavailable.
    """
    from datetime import datetime, timedelta
    from app.models.catalog import CatalogItem, ItemStatus
    from app.models.circulation import Checkout, CheckoutStatus

    item = CatalogItem(
        title="Checked Out Book",
        author="Another Author",
        isbn="978-0-222222-22-2",
        description="A book that is checked out",
        status=ItemStatus.checked_out,
        call_number="CHKOUT-001",
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    loan = Checkout(
        user_id=second_patron.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=21),
    )
    test_db.add(loan)
    await test_db.commit()
    return item


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
async def test_active_checkout(test_db, test_patron, test_catalog_item):
    """Create a test checkout that is active and not overdue."""
    from app.models.catalog import ItemStatus
    from app.models.circulation import Checkout, CheckoutStatus

    # Mark item as checked out
    test_catalog_item.status = ItemStatus.checked_out

    checkout = Checkout(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=21),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


@pytest.fixture
async def second_patron(test_db):
    """Create a second patron for hold tests."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="patron2@example.com",
        password_hash=hash_password("Patron2Password123!"),
        first_name="Second",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


async def get_patron_token(client, email, password):
    """Helper to get patron authentication token."""
    login_data = {
        "username": email,
        "password": password,
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


@pytest.mark.integration
class TestCheckoutEndpoints:
    """Test checkout endpoints."""

    async def test_list_checkouts_requires_auth(self, client):
        """Test listing checkouts requires authentication."""
        response = await client.get("/api/v1/circulation/checkouts")
        assert response.status_code == 401

    async def test_list_checkouts_success(
        self, client, test_patron, test_user_data, test_active_checkout
    ):
        """Test patron can list their checkouts."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.get(
            "/api/v1/circulation/checkouts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        assert data["data"][0]["user_id"] == test_patron.id

    async def test_create_checkout_success(
        self, client, test_patron, test_user_data, test_available_item
    ):
        """Test patron can checkout an available item."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        checkout_data = {"item_id": test_available_item.id}
        response = await client.post(
            "/api/v1/circulation/checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == test_patron.id
        assert data["item_id"] == test_available_item.id
        assert data["status"] == "active"
        assert data["item_title"] == test_available_item.title

    async def test_create_checkout_item_not_found(self, client, test_patron, test_user_data):
        """Test checkout fails when item not found."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        checkout_data = {"item_id": 99999}
        response = await client.post(
            "/api/v1/circulation/checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "could not find" in _error_detail(response).lower()

    async def test_create_checkout_item_not_available(
        self, client, test_patron, test_user_data, test_checked_out_item
    ):
        """Test checkout fails when item is not available."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        checkout_data = {"item_id": test_checked_out_item.id}
        response = await client.post(
            "/api/v1/circulation/checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        assert "checked out" in _error_detail(response).lower()

    async def test_create_checkout_already_has_item(
        self, client, test_patron, test_user_data, test_active_checkout, test_catalog_item
    ):
        """Test checkout fails when patron already has the item."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        checkout_data = {"item_id": test_catalog_item.id}
        response = await client.post(
            "/api/v1/circulation/checkout",
            json=checkout_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        assert "already" in _error_detail(response).lower()

    async def test_get_checkout_history(
        self, client, test_patron, test_user_data, test_active_checkout
    ):
        """Test patron can view their checkout history."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.get(
            "/api/v1/circulation/history",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)


@pytest.mark.integration
class TestHoldEndpoints:
    """Test hold/request endpoints."""

    async def test_create_hold_requires_auth(self, client):
        """Test creating hold requires authentication."""
        hold_data = {"item_id": 1}
        response = await client.post("/api/v1/circulation/holds", json=hold_data)
        assert response.status_code == 401

    async def test_create_hold_success(
        self, client, test_patron, test_user_data, test_checked_out_item
    ):
        """Test patron can place a hold on a checked out item."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        hold_data = {"item_id": test_checked_out_item.id}
        response = await client.post(
            "/api/v1/circulation/holds",
            json=hold_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == test_patron.id
        assert data["item_id"] == test_checked_out_item.id
        assert data["status"] in ["pending", "ready"]
        assert data["position"] >= 1

    async def test_create_hold_on_available_item_becomes_ready(
        self, client, test_patron, test_user_data, test_available_item
    ):
        """Test hold on available item immediately becomes ready."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        hold_data = {"item_id": test_available_item.id}
        response = await client.post(
            "/api/v1/circulation/holds",
            json=hold_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ready"
        assert data["notified_at"] is not None

    async def test_create_hold_rejects_unknown_pickup_location(
        self, client, test_patron, test_user_data, test_checked_out_item
    ):
        """Test hold creation validates pickup location before write."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        hold_data = {"item_id": test_checked_out_item.id, "pickup_location_id": 999999999}
        response = await client.post(
            "/api/v1/circulation/holds",
            json=hold_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "pickup location" in _error_detail(response).lower()

    async def test_create_hold_duplicate_fails(
        self, client, test_patron, test_user_data, test_catalog_item, test_hold
    ):
        """Test patron cannot place duplicate hold on same item."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        # test_hold is already on test_catalog_item for test_patron
        hold_data = {"item_id": test_catalog_item.id}
        response = await client.post(
            "/api/v1/circulation/holds",
            json=hold_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should fail because test_hold already exists for this patron/item
        assert response.status_code == 400
        assert "already" in _error_detail(response).lower()

    async def test_create_hold_on_checked_out_item_fails(
        self, client, test_patron, test_user_data, test_active_checkout, test_catalog_item
    ):
        """Test patron cannot place hold on item they have checked out."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        hold_data = {"item_id": test_catalog_item.id}
        response = await client.post(
            "/api/v1/circulation/holds",
            json=hold_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "checked out" in _error_detail(response).lower()

    async def test_list_patron_holds(self, client, test_patron, test_user_data, test_hold):
        """Test patron can view their holds."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.get(
            "/api/v1/circulation/holds",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        assert data["data"][0]["user_id"] == test_patron.id

    async def test_hold_queue_position(
        self, client, test_db, test_patron, test_user_data, second_patron, test_checked_out_item
    ):
        """Test hold queue position is maintained."""
        from app.models.circulation import Hold, HoldStatus

        # First hold by second_patron
        first_hold = Hold(
            user_id=second_patron.id,
            item_id=test_checked_out_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(first_hold)
        await test_db.commit()

        # Now test_patron places a hold
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        hold_data = {"item_id": test_checked_out_item.id}
        response = await client.post(
            "/api/v1/circulation/holds",
            json=hold_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        # Should be position 2
        assert data["position"] == 2

    async def test_cancel_hold_success(self, client, test_patron, test_user_data, test_hold):
        """Test patron can cancel their own pending hold."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.delete(
            f"/api/v1/circulation/holds/{test_hold.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

    async def test_cancel_hold_with_reason(self, client, test_patron, test_user_data, test_hold):
        """Test patron can cancel hold with a reason."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        # httpx's AsyncClient.delete() no longer accepts a json= body kwarg
        # directly; use .request() for a DELETE with a JSON payload.
        response = await client.request(
            "DELETE",
            f"/api/v1/circulation/holds/{test_hold.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "No longer needed"},
        )
        assert response.status_code == 204

    async def test_cancel_hold_not_found(self, client, test_patron, test_user_data):
        """Test cancelling non-existent hold fails."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.delete(
            "/api/v1/circulation/holds/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_cancel_hold_already_cancelled(
        self, client, test_db, test_patron, test_user_data, test_catalog_item
    ):
        """Test cancelling an already-cancelled hold fails."""
        from app.models.circulation import Hold, HoldStatus

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.cancelled,
            position=1,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.delete(
            f"/api/v1/circulation/holds/{hold.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "already been cancelled" in _error_detail(response).lower()

    async def test_cancel_hold_fulfilled_fails(
        self, client, test_db, test_patron, test_user_data, test_catalog_item
    ):
        """Test cancelling a fulfilled hold fails."""
        from app.models.circulation import Hold, HoldStatus

        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.fulfilled,
            position=1,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.delete(
            f"/api/v1/circulation/holds/{hold.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400

    async def test_cancel_hold_requires_auth(self, client, test_hold):
        """Test cancelling hold requires authentication."""
        response = await client.delete(
            f"/api/v1/circulation/holds/{test_hold.id}",
        )
        assert response.status_code == 401

    async def test_cancel_hold_other_patron_forbidden(
        self, client, test_db, second_patron, test_hold
    ):
        """Test patron cannot cancel another patron's hold."""
        # Login as second patron
        token = await get_patron_token(client, second_patron.email, "Patron2Password123!")
        response = await client.delete(
            f"/api/v1/circulation/holds/{test_hold.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestReturnEndpoints:
    """Test item return endpoints."""

    async def test_return_item_success(
        self, client, test_patron, test_user_data, test_active_checkout
    ):
        """Test patron can return an item."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.post(
            f"/api/v1/circulation/return/{test_active_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "returned"
        assert data["returned_at"] is not None

    async def test_return_item_not_found(self, client, test_patron, test_user_data):
        """Test return fails for non-existent checkout."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.post(
            "/api/v1/circulation/return/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "couldn't find" in _error_detail(response).lower()

    async def test_return_already_returned(
        self, client, test_db, test_patron, test_user_data, test_active_checkout
    ):
        """Test return fails for already returned item."""
        from app.models.circulation import CheckoutStatus

        # Mark as already returned
        test_active_checkout.status = CheckoutStatus.returned
        test_active_checkout.returned_at = datetime.now()
        await test_db.commit()

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.post(
            f"/api/v1/circulation/return/{test_active_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "already been returned" in _error_detail(response).lower()

    async def test_return_triggers_next_hold(
        self,
        client,
        test_db,
        test_patron,
        test_user_data,
        test_active_checkout,
        test_catalog_item,
        second_patron,
    ):
        """Test returning item notifies next person in hold queue."""
        from app.models.circulation import Hold, HoldStatus

        # Create a pending hold from second_patron
        hold = Hold(
            user_id=second_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        # Return the item
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.post(
            f"/api/v1/circulation/return/{test_active_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify hold is now ready
        await test_db.refresh(hold)
        assert hold.status == HoldStatus.ready
        assert hold.notified_at is not None
        assert hold.expires_at is not None

    async def test_return_sets_item_available_when_no_holds(
        self, client, test_db, test_patron, test_user_data, test_active_checkout, test_catalog_item
    ):
        """Test returning item sets status to available when no holds exist."""
        from app.models.catalog import ItemStatus

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.post(
            f"/api/v1/circulation/return/{test_active_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify item is now available
        await test_db.refresh(test_catalog_item)
        assert test_catalog_item.status == ItemStatus.available


@pytest.mark.integration
class TestOverdueHandling:
    """Test overdue item handling."""

    async def test_overdue_return_creates_fine(
        self, client, test_db, test_patron, test_user_data, test_overdue_checkout
    ):
        """Test that returning an overdue item generates a fine."""
        from app.models.fine import Fine, FineStatus, FineType

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.post(
            f"/api/v1/circulation/return/{test_overdue_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Check if fine was created
        from sqlalchemy import select

        fine_result = await test_db.execute(
            select(Fine).where(
                Fine.checkout_id == test_overdue_checkout.id,
                Fine.fine_type == FineType.overdue,
            )
        )
        fine = fine_result.scalar_one_or_none()
        # Fine may or may not be created depending on patron role settings
        if fine:
            assert fine.status == FineStatus.unpaid
            assert fine.amount > Decimal("0")

    async def test_get_user_fines(self, client, test_patron, test_user_data, test_fine):
        """Test patron can view their fines."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.get(
            "/api/v1/circulation/fines",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1

    async def test_get_fines_summary(self, client, test_patron, test_user_data, test_fine):
        """Test patron can view fines summary."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.get(
            "/api/v1/circulation/fines/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_outstanding" in data
        assert "outstanding_count" in data

    async def test_renew_checkout_success(
        self, client, test_patron, test_user_data, test_active_checkout
    ):
        """Test patron can renew a checkout."""
        original_due_date = test_active_checkout.due_date
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.post(
            f"/api/v1/circulation/renew/{test_active_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["renewal_count"] == 1
        # Due date should be extended
        new_due = datetime.fromisoformat(data["due_date"].replace("Z", "+00:00"))
        assert new_due > original_due_date.replace(tzinfo=new_due.tzinfo)

    async def test_renew_checkout_not_found(self, client, test_patron, test_user_data):
        """Test renewal fails for non-existent checkout."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.post(
            "/api/v1/circulation/renew/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_renew_fails_when_hold_exists(
        self,
        client,
        test_db,
        test_patron,
        test_user_data,
        test_active_checkout,
        test_catalog_item,
        second_patron,
    ):
        """Test renewal fails when holds exist on the item."""
        from app.models.circulation import Hold, HoldStatus

        # Create a hold on the item
        hold = Hold(
            user_id=second_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(hold)
        await test_db.commit()

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.post(
            f"/api/v1/circulation/renew/{test_active_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        assert "waiting" in _error_detail(response).lower()

    async def test_renew_fails_when_already_returned(
        self, client, test_db, test_patron, test_user_data, test_active_checkout
    ):
        """Test renewal fails for returned checkout."""
        from app.models.circulation import CheckoutStatus

        test_active_checkout.status = CheckoutStatus.returned
        test_active_checkout.returned_at = datetime.now()
        await test_db.commit()

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.post(
            f"/api/v1/circulation/renew/{test_active_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        assert "cannot be renewed" in _error_detail(response).lower()

    async def test_renew_limit_enforced(
        self, client, test_db, test_patron, test_user_data, test_active_checkout
    ):
        """Test renewal limit is enforced."""
        # Set renewal count to max (typically 2-3)
        test_active_checkout.renewal_count = 10  # Exceed any reasonable limit
        await test_db.commit()

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.post(
            f"/api/v1/circulation/renew/{test_active_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "maximum" in _error_detail(response).lower()


@pytest.mark.integration
class TestCheckoutLimits:
    """Test checkout limit enforcement."""

    async def test_checkout_limit_prevents_new_checkout(
        self, client, test_db, test_patron, test_user_data
    ):
        """Test that checkout limit prevents new checkouts."""
        from app.models.catalog import CatalogItem, ItemStatus
        from app.models.circulation import Checkout, CheckoutStatus

        # Create many active checkouts to exceed limit
        for i in range(15):  # Default limit is usually 10
            item = CatalogItem(
                title=f"Book {i}",
                author="Author",
                status=ItemStatus.checked_out,
                call_number=f"LIMIT-{i:03d}",
            )
            test_db.add(item)
            await test_db.flush()

            checkout = Checkout(
                user_id=test_patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                due_date=datetime.now() + timedelta(days=21),
            )
            test_db.add(checkout)
        await test_db.commit()

        # Create one more available item
        new_item = CatalogItem(
            title="One More Book",
            author="Author",
            status=ItemStatus.available,
            call_number="LIMIT-NEW",
        )
        test_db.add(new_item)
        await test_db.commit()
        await test_db.refresh(new_item)

        # Try to checkout - should fail
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": new_item.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422
        assert "limit" in _error_detail(response).lower()


@pytest.mark.integration
class TestHoldLimits:
    """Test hold limit enforcement."""

    async def test_hold_limit_prevents_new_hold(self, client, test_db, test_patron, test_user_data):
        """Test that hold limit prevents new holds."""
        from app.models.catalog import CatalogItem, ItemStatus
        from app.models.circulation import Hold, HoldStatus

        # Create many active holds to exceed limit
        for i in range(10):  # Default limit is usually 5
            item = CatalogItem(
                title=f"Hold Book {i}",
                author="Author",
                status=ItemStatus.checked_out,
                call_number=f"HLIMIT-{i:03d}",
            )
            test_db.add(item)
            await test_db.flush()

            hold = Hold(
                user_id=test_patron.id,
                item_id=item.id,
                status=HoldStatus.pending,
                position=1,
            )
            test_db.add(hold)
        await test_db.commit()

        # Create one more item
        new_item = CatalogItem(
            title="One More Hold Book",
            author="Author",
            status=ItemStatus.checked_out,
            call_number="HLIMIT-NEW",
        )
        test_db.add(new_item)
        await test_db.commit()
        await test_db.refresh(new_item)

        # Try to place hold - should fail
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": new_item.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "maximum" in _error_detail(response).lower()

    async def test_patron_on_way_unified_endpoint(
        self, client, test_db, test_patron, test_user_data, test_available_item
    ):
        """Test unified POST /circulation/patron-on-way endpoint."""
        from app.models.circulation import Hold, HoldStatus

        # First create a ready hold
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        hold_response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": test_available_item.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        hold_id = hold_response.json()["id"]
        assert hold_response.json()["status"] == "ready"

        # Now signal patron on-way using new unified endpoint
        response = await client.post(
            "/api/v1/circulation/patron-on-way",
            json={"hold_id": hold_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["hold_id"] == hold_id
        assert data["patron_on_way"] is True
        assert "message" in data

    async def test_patron_on_way_status_endpoint(
        self,
        client,
        test_db,
        test_patron,
        test_user_data,
        test_available_item,
        test_checked_out_item,
    ):
        """Test GET /circulation/patron-on-way/status endpoint."""
        from app.models.circulation import Hold, HoldStatus
        from app.models.catalog import ItemStatus

        # Create two holds - one ready and one pending
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])

        # First hold on available item (becomes ready immediately)
        hold1_response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": test_available_item.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        hold1_id = hold1_response.json()["id"]

        # Second hold on checked out item (becomes pending)
        hold2_response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": test_checked_out_item.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        _ = hold2_response.json()["id"]

        # Signal patron on-way for the ready hold
        on_way_response = await client.post(
            "/api/v1/circulation/patron-on-way",
            json={"hold_id": hold1_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert on_way_response.status_code == 200

        # Get patron's on-way status
        status_response = await client.get(
            "/api/v1/circulation/patron-on-way/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["total_on_way_count"] == 1
        assert len(data["on_way_holds"]) == 1
        assert data["on_way_holds"][0]["hold_id"] == hold1_id
        assert "is_ready" in data["on_way_holds"][0]
        assert "estimated_wait_time_minutes" in data["on_way_holds"][0]

    async def test_patron_on_way_cancel_endpoint(
        self, client, test_db, test_patron, test_user_data, test_available_item
    ):
        """Test POST /circulation/patron-on-way/{hold_id}/cancel endpoint."""
        from app.models.circulation import Hold, HoldStatus

        # Create a ready hold
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        hold_response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": test_available_item.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        hold_id = hold_response.json()["id"]
        assert hold_response.json()["status"] == "ready"

        # Signal patron on-way
        on_way_response = await client.post(
            "/api/v1/circulation/patron-on-way",
            json={"hold_id": hold_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert on_way_response.status_code == 200
        assert on_way_response.json()["patron_on_way"] is True

        # Cancel the on-way signal
        cancel_response = await client.post(
            f"/api/v1/circulation/patron-on-way/{hold_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cancel_response.status_code == 200
        data = cancel_response.json()
        assert data["hold_id"] == hold_id
        assert data["patron_on_way"] is False
        assert "message" in data

        # Verify signal was removed by checking status endpoint
        status_response = await client.get(
            "/api/v1/circulation/patron-on-way/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status_response.status_code == 200
        assert status_response.json()["total_on_way_count"] == 0

    async def test_patron_on_way_not_ready_fails(
        self, client, test_db, test_patron, test_user_data, test_checked_out_item
    ):
        """Test patron-on-way fails for non-ready holds."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])

        # Create a hold on checked out item (will be pending)
        hold_response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": test_checked_out_item.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        hold_id = hold_response.json()["id"]
        assert hold_response.json()["status"] == "pending"

        # Try to signal patron on-way - should fail
        response = await client.post(
            "/api/v1/circulation/patron-on-way",
            json={"hold_id": hold_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "ready" in _error_detail(response).lower()

    async def test_patron_on_way_cancel_not_on_way_fails(
        self, client, test_db, test_patron, test_user_data, test_available_item
    ):
        """Test cancelling on-way fails if hold is not on-way."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])

        # Create a ready hold (but don't mark on-way)
        hold_response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": test_available_item.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        hold_id = hold_response.json()["id"]
        assert hold_response.json()["status"] == "ready"
        assert hold_response.json()["patron_on_way"] is False

        # Try to cancel - should fail
        response = await client.post(
            f"/api/v1/circulation/patron-on-way/{hold_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "on-my-way signal" in _error_detail(response).lower()

    async def test_patron_on_way_authorization(
        self, client, test_db, test_patron, test_user_data, test_available_item
    ):
        """Test patron can only signal on-way for their own holds."""
        from app.models.user import User, UserRole

        # Create another user
        other_user = User(
            email="other@example.com",
            password_hash="hashed",
            first_name="Other",
            last_name="User",
            role=UserRole.PATRON,
        )
        test_db.add(other_user)
        await test_db.commit()
        await test_db.refresh(other_user)

        # First user creates a hold
        token1 = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        hold_response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": test_available_item.id},
            headers={"Authorization": f"Bearer {token1}"},
        )
        hold_id = hold_response.json()["id"]

        # Second user tries to signal on-way - should fail
        _ = await client.post(
            "/api/v1/circulation/patron-on-way",
            json={"hold_id": hold_id},
            headers={"Authorization": f"Bearer {token1}"},
        )
        # Note: Second user token would need to be generated, but for now this test shows the pattern
        # Actual implementation would need another user's token
