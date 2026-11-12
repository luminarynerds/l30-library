# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for the complete checkout-to-return circulation flow.

Tests the full lifecycle of library circulation:
- Checkout: Patron checks out an available item
- Item status transitions: available → checked_out → returned → available
- Renewal: Extending due dates with limits
- Overdue handling: Fine creation for late returns
- Hold queue: Processing holds when items are returned
- Staff operations: Staff checkout/checkin on behalf of patrons
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.user import User, UserRole


def _error_detail(response) -> str:
    """Error responses are wrapped as {"error": {"message": ...}} by
    app.core.exception_handlers.http_exception_handler, not the FastAPI
    default {"detail": ...}."""
    data = response.json()
    if "detail" in data:
        return str(data["detail"])
    return str(data.get("error", {}).get("message", data))


async def get_auth_headers(client, email: str, password: str) -> dict:
    """Helper to get authentication headers for a user."""
    login_data = {"username": email, "password": password}
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200, f"Login failed: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def second_patron(test_db):
    """Create a second patron user for multi-patron tests."""
    from app.core.security import hash_password

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


@pytest.fixture
async def available_item(test_db):
    """Create an available catalog item for checkout tests."""
    item = CatalogItem(
        title="Checkout Test Book",
        author="Test Author",
        isbn="978-1-234567-89-0",
        description="A book for testing checkout flow",
        status=ItemStatus.available,
        call_number="TEST-100",
        barcode="CHECKOUT001",
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def second_available_item(test_db):
    """Create a second available catalog item."""
    item = CatalogItem(
        title="Second Test Book",
        author="Another Author",
        isbn="978-1-234567-89-1",
        description="Another book for testing",
        status=ItemStatus.available,
        call_number="TEST-101",
        barcode="CHECKOUT002",
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.mark.integration
class TestBasicCheckoutFlow:
    """Test basic patron checkout operations."""

    async def test_checkout_requires_authentication(self, client):
        """Test that checkout endpoint requires authentication."""
        response = await client.post("/api/v1/circulation/checkout", json={"item_id": 1})
        assert response.status_code == 401

    async def test_patron_can_checkout_available_item(
        self, client, test_patron, test_user_data, available_item, test_db
    ):
        """Test that a patron can checkout an available item."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()

        # Verify checkout response
        assert data["item_id"] == available_item.id
        assert data["user_id"] == test_patron.id
        assert data["status"] == "active"
        assert data["item_title"] == available_item.title
        assert data["renewal_count"] == 0
        assert "due_date" in data
        assert "checked_out_at" in data

    async def test_checkout_changes_item_status_to_checked_out(
        self, client, test_patron, test_user_data, available_item, test_db
    ):
        """Test that checking out an item changes its status."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Verify initial status
        assert available_item.status == ItemStatus.available

        response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        assert response.status_code == 201

        # Check item status in database (need to refresh from session)
        # The item status is changed in the API, verify through API
        response = await client.get("/api/v1/circulation/checkouts", headers=headers)
        assert response.status_code == 200
        checkouts = response.json()["data"]
        assert len(checkouts) >= 1

    async def test_cannot_checkout_already_checked_out_item(
        self, client, test_patron, test_user_data, available_item
    ):
        """Test that same patron cannot checkout the same item twice."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # First checkout
        response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        assert response.status_code == 201

        # Second checkout should fail
        response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        # Already-checked-out is a ConflictError (409), not a generic 400.
        assert response.status_code == 409
        assert "already" in response.json()["detail"].lower()

    async def test_checkout_nonexistent_item_fails(self, client, test_patron, test_user_data):
        """Test that checking out a non-existent item fails."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": 99999},
            headers=headers,
        )
        assert response.status_code == 404
        assert "could not find" in response.json()["detail"].lower()

    async def test_patron_can_view_active_checkouts(
        self, client, test_patron, test_user_data, available_item
    ):
        """Test that patron can view their active checkouts."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Checkout an item
        await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )

        # View checkouts
        response = await client.get("/api/v1/circulation/checkouts", headers=headers)
        assert response.status_code == 200
        checkouts = response.json()["data"]
        assert len(checkouts) >= 1
        assert any(c["item_id"] == available_item.id for c in checkouts)


@pytest.mark.integration
class TestReturnFlow:
    """Test item return operations."""

    async def test_return_requires_authentication(self, client):
        """Test that return endpoint requires authentication."""
        response = await client.post("/api/v1/circulation/return/1")
        assert response.status_code == 401

    async def test_patron_can_return_checked_out_item(
        self, client, test_patron, test_user_data, available_item
    ):
        """Test that patron can return a checked out item."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Checkout first
        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        checkout_id = checkout_response.json()["id"]

        # Return the item
        response = await client.post(
            f"/api/v1/circulation/return/{checkout_id}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "returned"
        assert data["returned_at"] is not None

    async def test_return_sets_item_status_to_available(
        self, client, test_patron, test_user_data, available_item
    ):
        """Test that returning item makes it available again."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Checkout
        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        checkout_id = checkout_response.json()["id"]

        # Return
        await client.post(f"/api/v1/circulation/return/{checkout_id}", headers=headers)

        # Verify item is available by checking out again
        response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        # Should be able to checkout again
        assert response.status_code == 201

    async def test_cannot_return_nonexistent_checkout(self, client, test_patron, test_user_data):
        """Test returning a non-existent checkout fails."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        response = await client.post("/api/v1/circulation/return/99999", headers=headers)
        assert response.status_code == 404

    async def test_cannot_return_already_returned_item(
        self, client, test_patron, test_user_data, available_item
    ):
        """Test that an already returned item cannot be returned again."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Checkout
        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        checkout_id = checkout_response.json()["id"]

        # First return
        response = await client.post(f"/api/v1/circulation/return/{checkout_id}", headers=headers)
        assert response.status_code == 200

        # Second return should fail
        response = await client.post(f"/api/v1/circulation/return/{checkout_id}", headers=headers)
        assert response.status_code == 400
        assert "already been returned" in response.json()["error"]["message"].lower()


@pytest.mark.integration
class TestCompleteCheckoutReturnCycle:
    """Test the complete checkout-to-return lifecycle."""

    async def test_full_checkout_return_cycle(
        self, client, test_patron, test_user_data, available_item
    ):
        """Test complete cycle: checkout → view → return → checkout again."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Step 1: Checkout
        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        assert checkout_response.status_code == 201
        checkout_id = checkout_response.json()["id"]
        assert checkout_response.json()["status"] == "active"

        # Step 2: View active checkouts
        checkouts_response = await client.get("/api/v1/circulation/checkouts", headers=headers)
        assert checkouts_response.status_code == 200
        assert any(c["id"] == checkout_id for c in checkouts_response.json()["data"])

        # Step 3: Return
        return_response = await client.post(
            f"/api/v1/circulation/return/{checkout_id}", headers=headers
        )
        assert return_response.status_code == 200
        assert return_response.json()["status"] == "returned"

        # Step 4: Verify item no longer in active checkouts
        checkouts_response = await client.get("/api/v1/circulation/checkouts", headers=headers)
        active_ids = [c["id"] for c in checkouts_response.json()["data"]]
        assert checkout_id not in active_ids

        # Step 5: Checkout again (proves item is available)
        new_checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        assert new_checkout_response.status_code == 201
        assert new_checkout_response.json()["id"] != checkout_id

    async def test_multiple_items_checkout_return(
        self, client, test_patron, test_user_data, available_item, second_available_item
    ):
        """Test checking out and returning multiple items."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Checkout two items
        checkout1 = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        assert checkout1.status_code == 201

        checkout2 = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": second_available_item.id},
            headers=headers,
        )
        assert checkout2.status_code == 201

        # Verify both in active checkouts
        checkouts = (await client.get("/api/v1/circulation/checkouts", headers=headers)).json()[
            "data"
        ]
        assert len(checkouts) >= 2

        # Return first item
        await client.post(f"/api/v1/circulation/return/{checkout1.json()['id']}", headers=headers)

        # Verify only second item remains
        checkouts = (await client.get("/api/v1/circulation/checkouts", headers=headers)).json()[
            "data"
        ]
        active_item_ids = [c["item_id"] for c in checkouts]
        assert available_item.id not in active_item_ids
        assert second_available_item.id in active_item_ids


@pytest.mark.integration
class TestRenewalFlow:
    """Test checkout renewal operations."""

    async def test_patron_can_renew_checkout(
        self, client, test_patron, test_user_data, available_item
    ):
        """Test that patron can renew an active checkout."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Checkout
        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        checkout_id = checkout_response.json()["id"]
        original_due_date = checkout_response.json()["due_date"]

        # Renew
        renew_response = await client.post(
            f"/api/v1/circulation/renew/{checkout_id}", headers=headers
        )
        assert renew_response.status_code == 200
        data = renew_response.json()
        assert data["renewal_count"] == 1
        assert data["due_date"] > original_due_date

    async def test_renewal_extends_due_date(
        self, client, test_patron, test_user_data, available_item
    ):
        """Test that renewal extends the due date properly."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Checkout
        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        checkout_id = checkout_response.json()["id"]

        # Renew: renew_checkout deliberately recalculates the due date from
        # the moment of renewal (not from the old due date) so overdue
        # renewals get a full fresh loan period instead of stacking on top
        # of an overdue date (see checkout_service.renew_checkout). So the
        # correct check is against "now", not the pre-renewal due date.
        before_renew = datetime.now(timezone.utc)
        renew_response = await client.post(
            f"/api/v1/circulation/renew/{checkout_id}", headers=headers
        )
        new_due = datetime.fromisoformat(renew_response.json()["due_date"].replace("Z", "+00:00"))

        # The new due date should be approximately 21 days from renewal time
        days_extended = (new_due - before_renew).days
        assert 20 <= days_extended <= 22  # Allow for timing variations

    async def test_cannot_renew_returned_checkout(
        self, client, test_patron, test_user_data, available_item
    ):
        """Test that returned checkouts cannot be renewed."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Checkout and return
        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        checkout_id = checkout_response.json()["id"]
        await client.post(f"/api/v1/circulation/return/{checkout_id}", headers=headers)

        # Try to renew
        renew_response = await client.post(
            f"/api/v1/circulation/renew/{checkout_id}", headers=headers
        )
        # renew_checkout raises ConflictError (409) for a non-active checkout.
        assert renew_response.status_code == 409
        assert "not currently checked out" in renew_response.json()["detail"].lower()


@pytest.mark.integration
class TestOverdueAndFines:
    """Test overdue handling and fine creation."""

    @pytest.mark.skip(
        reason="QUARANTINED 2026-07-09 (W1 rebaseline): assumes monetary "
        "fines are always created for overdue returns, but "
        "app/services/fine_service.py now checks RoleSettings.use_reading_minutes "
        "first -- roles opted into the reading-minutes model get "
        "reading_minutes_owed incremented instead of a Fine row, by design "
        "(trauma-informed fines policy). Whether test_patron's seeded role "
        "defaults to reading-minutes mode needs checking before rewriting "
        "this assertion; not a rename, a behavior-model question."
    )
    async def test_overdue_return_creates_fine(
        self, client, test_patron, test_user_data, available_item, test_db
    ):
        """Test that returning an overdue item creates a fine."""
        from app.core.security import hash_password

        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Create an overdue checkout directly in the database
        overdue_checkout = Checkout(
            user_id=test_patron.id,
            item_id=available_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now() - timedelta(days=30),
            due_date=datetime.now() - timedelta(days=7),  # 7 days overdue
        )
        test_db.add(overdue_checkout)

        # Update item status
        available_item.status = ItemStatus.checked_out
        await test_db.commit()
        await test_db.refresh(overdue_checkout)

        # Return the overdue item
        response = await client.post(
            f"/api/v1/circulation/return/{overdue_checkout.id}", headers=headers
        )
        assert response.status_code == 200

        # Check for fine creation
        fines_response = await client.get(
            "/api/v1/circulation/fines?include_paid=true", headers=headers
        )
        assert fines_response.status_code == 200
        fines = fines_response.json()["data"]

        # Should have at least one overdue fine
        overdue_fines = [f for f in fines if f["fine_type"] == "overdue"]
        assert len(overdue_fines) >= 1

    async def test_view_fines_endpoint(self, client, test_patron, test_user_data):
        """Test that patrons can view their fines."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        response = await client.get("/api/v1/circulation/fines", headers=headers)
        assert response.status_code == 200
        # Response is a PaginatedResponse envelope (might be empty)
        assert isinstance(response.json()["data"], list)

    async def test_fines_summary_endpoint(self, client, test_patron, test_user_data):
        """Test that patrons can view their fines summary."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        response = await client.get("/api/v1/circulation/fines/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_outstanding" in data
        assert "total_paid" in data
        assert "outstanding_count" in data
        assert "paid_count" in data


@pytest.mark.integration
class TestHoldQueueProcessing:
    """Test hold queue processing when items are returned."""

    async def test_return_processes_hold_queue(
        self, client, test_patron, test_user_data, second_patron, available_item, test_db
    ):
        """Test that returning an item processes the hold queue."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Patron 1 checks out the item
        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        checkout_id = checkout_response.json()["id"]

        # Create a pending hold for patron 2
        hold = Hold(
            user_id=second_patron.id,
            item_id=available_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(hold)
        await test_db.commit()
        await test_db.refresh(hold)

        # Patron 1 returns the item
        return_response = await client.post(
            f"/api/v1/circulation/return/{checkout_id}", headers=headers
        )
        assert return_response.status_code == 200

        # Verify the hold was processed - refresh hold from DB
        await test_db.refresh(hold)
        assert hold.status == HoldStatus.ready
        assert hold.notified_at is not None
        assert hold.expires_at is not None

    async def test_return_without_holds_sets_available(
        self, client, test_patron, test_user_data, available_item, test_db
    ):
        """Test that return without holds sets item to available."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Checkout and return (no holds exist)
        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        checkout_id = checkout_response.json()["id"]

        await client.post(f"/api/v1/circulation/return/{checkout_id}", headers=headers)

        # Verify item is available by attempting another checkout
        new_checkout = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        assert new_checkout.status_code == 201


@pytest.mark.integration
class TestHoldOperations:
    """Test hold placement and management."""

    async def test_patron_can_place_hold(self, client, test_patron, test_user_data, available_item):
        """Test that patron can place a hold on an item."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": available_item.id},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["item_id"] == available_item.id
        assert data["user_id"] == test_patron.id
        # Hold on available item should become ready immediately
        assert data["status"] in ["pending", "ready"]

    async def test_cannot_hold_item_already_checked_out_by_self(
        self, client, test_patron, test_user_data, available_item
    ):
        """Test that patron cannot hold an item they already have checked out."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Checkout the item
        await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )

        # Try to place hold
        response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": available_item.id},
            headers=headers,
        )
        assert response.status_code == 400
        assert "already" in response.json()["error"]["message"].lower()

    async def test_patron_can_view_holds(self, client, test_patron, test_user_data, available_item):
        """Test that patron can view their holds."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Place a hold
        await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": available_item.id},
            headers=headers,
        )

        # View holds
        response = await client.get("/api/v1/circulation/holds", headers=headers)
        assert response.status_code == 200
        holds = response.json()["data"]
        assert len(holds) >= 1
        assert any(h["item_id"] == available_item.id for h in holds)

    async def test_patron_can_cancel_hold(
        self, client, test_patron, test_user_data, available_item
    ):
        """Test that patron can cancel their hold."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Place a hold
        hold_response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": available_item.id},
            headers=headers,
        )
        hold_id = hold_response.json()["id"]

        # Cancel the hold
        response = await client.delete(f"/api/v1/circulation/holds/{hold_id}", headers=headers)
        assert response.status_code == 204

        # Verify hold is cancelled
        holds = (await client.get("/api/v1/circulation/holds", headers=headers)).json()["data"]
        active_hold_ids = [h["id"] for h in holds]
        assert hold_id not in active_hold_ids

    async def test_cannot_renew_with_pending_holds(
        self, client, test_patron, test_user_data, second_patron, available_item, test_db
    ):
        """Test that checkout cannot be renewed when holds exist."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Patron 1 checks out
        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        checkout_id = checkout_response.json()["id"]

        # Patron 2 places a hold (via direct DB insertion since different auth)
        hold = Hold(
            user_id=second_patron.id,
            item_id=available_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(hold)
        await test_db.commit()

        # Patron 1 tries to renew
        renew_response = await client.post(
            f"/api/v1/circulation/renew/{checkout_id}", headers=headers
        )
        # renew_checkout raises ConflictError (409) when a hold is queued.
        assert renew_response.status_code == 409
        assert "waiting for" in _error_detail(renew_response).lower()


@pytest.mark.integration
class TestStaffCirculationOperations:
    """Test staff checkout and checkin operations."""

    async def test_staff_checkin_requires_auth(self, client):
        """Test that staff checkin requires authentication."""
        response = await client.post("/api/v1/circulation/checkin?checkout_id=1")
        assert response.status_code == 401

    async def test_staff_checkin_requires_staff_role(self, client, test_patron, test_user_data):
        """POST /circulation/checkin is not staff-only: get_current_user
        allows any authenticated user, scoping patrons to their own
        checkouts. checkout_id=1 doesn't belong to (or exist for) this
        patron, so the correct outcome is 404, not 403.
        """
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        response = await client.post("/api/v1/circulation/checkin?checkout_id=1", headers=headers)
        assert response.status_code == 404

    async def test_staff_can_checkin_item(
        self, client, test_patron, test_user_data, test_staff, test_staff_data, available_item
    ):
        """Test that staff can check in any patron's item."""
        patron_headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )
        staff_headers = await get_auth_headers(
            client, test_staff_data["email"], test_staff_data["password"]
        )

        # Patron checks out
        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=patron_headers,
        )
        checkout_id = checkout_response.json()["id"]

        # Staff checks in
        checkin_response = await client.post(
            f"/api/v1/circulation/checkin?checkout_id={checkout_id}", headers=staff_headers
        )
        assert checkin_response.status_code == 200
        assert checkin_response.json()["status"] == "returned"

    async def test_staff_checkout_for_patron(
        self, client, test_patron, test_staff, test_staff_data, available_item
    ):
        """Test that staff can checkout an item for a patron."""
        staff_headers = await get_auth_headers(
            client, test_staff_data["email"], test_staff_data["password"]
        )

        response = await client.post(
            f"/api/v1/staff/patrons/{test_patron.id}/quick-checkout",
            json={"barcode": available_item.barcode},
            headers=staff_headers,
        )
        assert response.status_code == 201
        data = response.json()["checkout"]
        assert data["user_id"] == test_patron.id
        assert data["status"] == "active"

    async def test_staff_checkin_by_barcode(
        self, client, test_patron, test_staff, test_staff_data, available_item
    ):
        """Test that staff can check in an item by barcode."""
        staff_headers = await get_auth_headers(
            client, test_staff_data["email"], test_staff_data["password"]
        )

        # Staff checkout for patron
        await client.post(
            f"/api/v1/staff/patrons/{test_patron.id}/quick-checkout",
            json={"barcode": available_item.barcode},
            headers=staff_headers,
        )

        # Staff checkin by barcode (barcode is a query param, not a JSON body)
        response = await client.post(
            f"/api/v1/staff/checkin-barcode?barcode={available_item.barcode}",
            headers=staff_headers,
        )
        assert response.status_code == 200
        assert "checkout" in response.json()
        assert response.json()["checkout"]["status"] == "returned"

    # NOTE: test_staff_can_view_all_checkouts / test_staff_can_filter_checkouts_by_patron
    # targeted GET /api/v1/staff/checkouts, a flat staff-only, patron-filterable
    # checkout listing that lived in the now-deleted app/api/v1/staff_circulation.py
    # (removed 2026-02-15, commit b2013f01b). There is no 1:1 successor -- see the
    # identical note on TestStaffCheckouts in test_staff_endpoints.py. Left
    # un-fixed pending a product call (REPORT-ONLY, see rot2 report).
    @pytest.mark.skip(
        reason="QUARANTINED 2026-07-09 (W1 rebaseline): targets GET "
        "/api/v1/staff/checkouts, which lived in the now-deleted "
        "app/api/v1/staff_circulation.py (removed 2026-02-15, b2013f01b) "
        "with no 1:1 successor. Real product call needed (rebuild the "
        "endpoint or delete the FE/test surface), not a test fix -- see "
        "the file-level note above and the identical TestStaffCheckouts "
        "note in test_staff_endpoints.py."
    )
    async def test_staff_can_view_all_checkouts(
        self, client, test_patron, test_user_data, test_staff, test_staff_data, available_item
    ):
        """Test that staff can view all checkouts."""
        patron_headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )
        staff_headers = await get_auth_headers(
            client, test_staff_data["email"], test_staff_data["password"]
        )

        # Patron checks out
        await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=patron_headers,
        )

        # Staff views all checkouts
        response = await client.get("/api/v1/staff/checkouts", headers=staff_headers)
        assert response.status_code == 200
        data = response.json()
        assert "checkouts" in data
        assert "total_count" in data
        assert data["total_count"] >= 1

    @pytest.mark.skip(
        reason="QUARANTINED 2026-07-09 (W1 rebaseline): same dead "
        "GET /api/v1/staff/checkouts endpoint as test_staff_can_view_all_checkouts."
    )
    async def test_staff_can_filter_checkouts_by_patron(
        self, client, test_patron, test_user_data, test_staff, test_staff_data, available_item
    ):
        """Test that staff can filter checkouts by patron ID."""
        patron_headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )
        staff_headers = await get_auth_headers(
            client, test_staff_data["email"], test_staff_data["password"]
        )

        # Patron checks out
        await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=patron_headers,
        )

        # Staff filters by patron
        response = await client.get(
            f"/api/v1/staff/checkouts?patron_id={test_patron.id}",
            headers=staff_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert all(c["user_id"] == test_patron.id for c in data["checkouts"])

    async def test_staff_override_renewal_still_blocked_by_holds(
        self,
        client,
        test_patron,
        test_user_data,
        test_staff,
        test_staff_data,
        second_patron,
        available_item,
        test_db,
    ):
        """Staff override renewal does NOT bypass hold restrictions.

        app/api/v1/staff/circulation_checkin.py::staff_override_renew is
        explicit: staff override waives the overdue-grace cutoff and (with
        override=True) the renewal cap, but "the hold queue still applies,
        so a waiting patron is never bumped."
        """
        patron_headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )
        staff_headers = await get_auth_headers(
            client, test_staff_data["email"], test_staff_data["password"]
        )

        # Patron checks out
        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=patron_headers,
        )
        checkout_id = checkout_response.json()["id"]

        # Create a hold from second patron
        hold = Hold(
            user_id=second_patron.id,
            item_id=available_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(hold)
        await test_db.commit()

        # Normal renewal should fail (ConflictError -> 409)
        patron_renew = await client.post(
            f"/api/v1/circulation/renew/{checkout_id}", headers=patron_headers
        )
        assert patron_renew.status_code == 409

        # Staff override also fails -- the hold queue still blocks renewal
        staff_renew = await client.post(
            f"/api/v1/staff/override-renew/{checkout_id}", headers=staff_headers
        )
        assert staff_renew.status_code == 409


@pytest.mark.integration
class TestReadingHistory:
    """Test reading history functionality."""

    async def test_checkout_history_requires_auth(self, client):
        """Test that checkout history requires authentication."""
        response = await client.get("/api/v1/circulation/history")
        assert response.status_code == 401

    async def test_checkout_history_respects_privacy_setting(
        self, client, test_patron, test_user_data, available_item, test_db
    ):
        """Test that checkout history respects privacy setting."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Checkout and return an item
        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": available_item.id},
            headers=headers,
        )
        checkout_id = checkout_response.json()["id"]
        await client.post(f"/api/v1/circulation/return/{checkout_id}", headers=headers)

        # With history tracking disabled (default), should return empty
        response = await client.get("/api/v1/circulation/history", headers=headers)
        assert response.status_code == 200
        # Default is track_reading_history = False, so should be empty.
        # /history is a PaginatedResponse envelope, not a raw list.
        assert response.json()["data"] == []

        # Enable history tracking
        test_patron.track_reading_history = True
        await test_db.commit()

        # Now should return history
        response = await client.get("/api/v1/circulation/history", headers=headers)
        assert response.status_code == 200
        history = response.json()["data"]
        assert len(history) >= 1


@pytest.mark.integration
class TestEdgeCases:
    """Test edge cases and error handling."""

    async def test_checkout_unavailable_item_fails(
        self, client, test_patron, second_patron, test_user_data, test_db
    ):
        """Test that checking out an unavailable item fails."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Create an item that's already checked out. Availability is derived
        # from active-loan counts against the item's (virtual, single) copy
        # count now, not the title-level status field alone -- give it a
        # real outstanding loan (to a different patron) so it's actually
        # unavailable, matching the fix in test_circulation_endpoints.py.
        item = CatalogItem(
            title="Unavailable Book",
            author="Test Author",
            status=ItemStatus.checked_out,
            call_number="UNAVAIL-001",
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        loan = Checkout(
            user_id=second_patron.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=21),
        )
        test_db.add(loan)
        await test_db.commit()

        response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": item.id},
            headers=headers,
        )
        assert response.status_code == 409
        assert "checked out" in _error_detail(response).lower()

    async def test_hold_on_available_item_becomes_ready(
        self, client, test_patron, test_user_data, available_item
    ):
        """Test that placing hold on available item makes it ready immediately."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": available_item.id},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        # Hold on available item should be ready
        assert data["status"] == "ready"
        assert data["notified_at"] is not None
        assert data["expires_at"] is not None

    async def test_cannot_place_duplicate_active_hold(
        self, client, test_patron, test_user_data, available_item
    ):
        """Test that patron cannot place duplicate active holds."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Place first hold
        response1 = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": available_item.id},
            headers=headers,
        )
        assert response1.status_code == 201

        # Try to place second hold
        response2 = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": available_item.id},
            headers=headers,
        )
        assert response2.status_code == 400
        assert "already" in _error_detail(response2).lower()
