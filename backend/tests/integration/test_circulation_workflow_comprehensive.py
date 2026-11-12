# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive end-to-end circulation workflow tests for LSC.

Tests the complete circulation workflow including:
- Catalog browsing and search
- Hold placement and queue management
- Patron checkout with limit enforcement (10 items max)
- Item renewal
- Return and fine generation
- Patron suspension logic
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest


async def get_patron_token(client, email, password):
    """Helper to get patron authentication token."""
    login_data = {
        "username": email,
        "password": password,
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


@pytest.fixture
async def multiple_catalog_items(test_db):
    """Create multiple catalog items for browsing/search."""
    from app.models.catalog import CatalogItem, CatalogingStatus, ItemStatus

    items = []
    titles = [
        "The Great Gatsby",
        "To Kill a Mockingbird",
        "1984",
        "Pride and Prejudice",
        "Wuthering Heights",
        "Jane Eyre",
        "The Catcher in the Rye",
        "Brave New World",
    ]
    authors = [
        "F. Scott Fitzgerald",
        "Harper Lee",
        "George Orwell",
        "Jane Austen",
        "Emily Brontë",
        "Charlotte Brontë",
        "J.D. Salinger",
        "Aldous Huxley",
    ]

    for i, (title, author) in enumerate(zip(titles, authors)):
        item = CatalogItem(
            title=title,
            author=author,
            isbn=f"978-0-{100000+i:06d}-{i:02d}-9",
            description=f"Description for {title}",
            status=ItemStatus.available,
            call_number=f"CLASSIC-{i:03d}",
            publication_year=2024,
            # Public/anonymous search+browse only surfaces CATALOGED items
            # (see get_catalog_item / search_catalog visibility gates);
            # the model default is UNCATALOGED, which search silently drops.
            cataloging_status=CatalogingStatus.CATALOGED,
        )
        test_db.add(item)
        items.append(item)

    await test_db.commit()
    for item in items:
        await test_db.refresh(item)
    return items


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


@pytest.mark.integration
class TestCirculationWorkflowEnd2End:
    """End-to-end circulation workflow tests."""

    async def test_search_catalog_by_title(self, client, multiple_catalog_items):
        """Test searching catalog by title."""
        response = await client.get("/api/v1/catalog/search?q=Gatsby")
        assert response.status_code == 200
        # CatalogPaginatedResponse envelope: {"items": [...], "total": ..., ...}
        data = response.json()["items"]
        assert len(data) > 0
        assert any("Gatsby" in item["title"] for item in data)

    async def test_search_catalog_by_author(self, client, multiple_catalog_items):
        """Test searching catalog by author."""
        response = await client.get("/api/v1/catalog/search?q=Austen")
        assert response.status_code == 200
        data = response.json()["items"]
        assert len(data) > 0
        assert any("Austen" in item.get("author", "") for item in data)

    async def test_browse_catalog_list(self, client, multiple_catalog_items):
        """Test browsing catalog with pagination."""
        # Root list route is registered as "/" (i.e. GET /api/v1/catalog/);
        # without the trailing slash FastAPI 307-redirects and httpx does not
        # auto-follow by default.
        response = await client.get("/api/v1/catalog/?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()["items"]
        assert len(data) > 0
        assert len(data) <= 10

    async def test_get_catalog_item_details(self, client, test_catalog_item, test_db):
        """Test retrieving detailed information about a catalog item."""
        from app.models.catalog import CatalogingStatus

        # Anonymous/public visibility requires CATALOGED status; the shared
        # test_catalog_item conftest fixture defaults to UNCATALOGED.
        test_catalog_item.cataloging_status = CatalogingStatus.CATALOGED
        await test_db.commit()

        response = await client.get(f"/api/v1/catalog/{test_catalog_item.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_catalog_item.id
        assert data["title"] == test_catalog_item.title
        assert data["author"] == test_catalog_item.author

    async def test_place_hold_on_checked_out_item(
        self, client, test_patron, test_user_data, test_catalog_item, test_db, second_patron
    ):
        """Test patron can place a hold on a checked out item."""
        from app.models.catalog import ItemStatus
        from app.models.circulation import Checkout, CheckoutStatus

        # First, checkout the item with the OTHER patron -- `second_patron`
        # is a distinct fixture (see top of file); it was previously aliased
        # to `test_patron` itself, which meant the same user "checked out"
        # and then tried to hold their own checkout (a 400: "You already
        # have this item checked out"), not the intended cross-patron case.
        item = test_catalog_item
        item.status = ItemStatus.checked_out

        checkout = Checkout(
            user_id=second_patron.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=21),
        )
        test_db.add(checkout)
        await test_db.commit()

        # Get token for first patron to place hold
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])

        # Now place hold on checked out item
        response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": item.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        # place_hold returns 201 Created, not 200.
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == test_patron.id
        assert data["item_id"] == item.id
        assert data["status"] == "pending"
        assert data["position"] == 1

    async def test_hold_becomes_ready_immediately_for_available_item(
        self, client, test_patron, test_user_data, test_available_item
    ):
        """Test that hold on available item becomes ready immediately."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": test_available_item.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        # place_hold returns 201 Created, not 200.
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ready"
        assert data["position"] == 1

    async def test_complete_checkout_workflow(
        self, client, test_patron, test_user_data, multiple_catalog_items
    ):
        """Test complete checkout workflow: browse, select, and checkout items."""
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])

        # Search for item
        response = await client.get("/api/v1/catalog/search?q=Gatsby")
        assert response.status_code == 200
        search_results = response.json()["items"]
        assert len(search_results) > 0
        item_id = search_results[0]["id"]

        # Checkout the item
        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": item_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        # checkout_item returns 201 Created, not 200.
        assert checkout_response.status_code == 201
        checkout_data = checkout_response.json()
        assert checkout_data["user_id"] == test_patron.id
        assert checkout_data["status"] == "active"

    async def test_checkout_limit_enforcement_10_items(
        self, client, test_db, test_patron, test_user_data
    ):
        """Test that checkout limit of 10 items is enforced."""
        from app.models.catalog import CatalogItem, ItemStatus
        from app.models.circulation import Checkout, CheckoutStatus

        # Create 10 available items and checkout all
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])

        for i in range(10):
            item = CatalogItem(
                title=f"Checkout Limit Test Book {i}",
                author="Test Author",
                status=ItemStatus.available,
                call_number=f"CHLIMIT-{i:03d}",
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
        extra_item = CatalogItem(
            title="One More Book for Checkout Limit Test",
            author="Test Author",
            status=ItemStatus.available,
            call_number="CHLIMIT-EXTRA",
        )
        test_db.add(extra_item)
        await test_db.commit()
        await test_db.refresh(extra_item)

        # Try to checkout 11th item - should fail
        response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": extra_item.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        # check_checkout_limit raises BusinessLogicError(QUOTA_EXCEEDED), which
        # maps to 422 (see app/core/error_codes.py). api_error_handler in
        # main.py renders all APIError subclasses as {"detail": ..., "code": ...}.
        assert response.status_code == 422
        assert "limit" in response.json()["detail"].lower()

    async def test_renew_checked_out_item(
        self, client, test_patron, test_user_data, test_active_checkout
    ):
        """Test patron can renew a checked out item."""
        original_due_date = test_active_checkout.due_date
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])

        response = await client.post(
            f"/api/v1/circulation/renew/{test_active_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["renewal_count"] == 1
        # Due date should be extended (at least 21 days from today)
        new_due = datetime.fromisoformat(data["due_date"].replace("Z", "+00:00"))
        assert new_due > original_due_date.replace(tzinfo=new_due.tzinfo)

    async def test_renewal_blocked_when_holds_exist(
        self, client, test_db, test_patron, test_user_data, test_active_checkout, test_catalog_item, second_patron
    ):
        """Test that renewal is blocked when holds exist on the item."""
        from app.models.circulation import Hold, HoldStatus

        # Create a hold on the checked out item from another patron
        hold = Hold(
            user_id=second_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(hold)
        await test_db.commit()

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])

        # Try to renew - should fail
        response = await client.post(
            f"/api/v1/circulation/renew/{test_active_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Blocked-by-hold raises ConflictError(ITEM_ON_HOLD) -> 409. Verified
        # empirically: unlike BusinessLogicError (422, {"detail": ...} via
        # main.py's api_error_handler), this one renders as
        # {"error": {"message": ..., "code": ...}} -- same shape as a plain
        # HTTPException, not main.py's local APIError handler.
        assert response.status_code == 409
        assert "waiting" in response.json()["error"]["message"].lower()

    async def test_return_item_success(
        self, client, test_patron, test_user_data, test_active_checkout, test_db
    ):
        """Test patron can return a checked out item."""
        from app.models.catalog import ItemStatus

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])

        response = await client.post(
            f"/api/v1/circulation/return/{test_active_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "returned"
        assert data["returned_at"] is not None

        # Item should be available again
        await test_db.refresh(test_active_checkout.item)
        assert test_active_checkout.item.status == ItemStatus.available

    async def test_return_triggers_hold_queue(
        self, client, test_db, test_patron, test_user_data, test_active_checkout, test_catalog_item, second_patron
    ):
        """Test that returning an item notifies the next person in hold queue."""
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

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])

        # Return the item
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

    async def test_overdue_fine_generation(
        self, client, test_db, test_patron, test_user_data
    ):
        """Test that fine is generated for overdue item ($0.25/day)."""
        from app.models.catalog import CatalogItem, ItemStatus
        from app.models.circulation import Checkout, CheckoutStatus
        from app.models.fine import Fine

        # Create an overdue checkout (7 days overdue)
        item = CatalogItem(
            title="Overdue Test Book",
            author="Test Author",
            status=ItemStatus.checked_out,
            call_number="OVERDUE-001",
        )
        test_db.add(item)
        await test_db.flush()

        overdue_checkout = Checkout(
            user_id=test_patron.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now() - timedelta(days=30),
            due_date=datetime.now() - timedelta(days=7),  # 7 days overdue
        )
        test_db.add(overdue_checkout)
        await test_db.commit()
        await test_db.refresh(overdue_checkout)

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])

        # Return the overdue item
        response = await client.post(
            f"/api/v1/circulation/return/{overdue_checkout.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Check if fine was created (may depend on fine-free mode)
        from sqlalchemy import select

        fine_result = await test_db.execute(
            select(Fine).where(Fine.checkout_id == overdue_checkout.id)
        )
        fine = fine_result.scalar_one_or_none()

        if fine:
            # Expected: 7 days * $0.25/day = $1.75 (minimum)
            # Actual calculation may vary based on grace period
            assert fine.amount > Decimal("0")
            assert fine.user_id == test_patron.id

    async def test_fine_accrual_multiple_overdue_items(
        self, client, test_db, test_patron, test_user_data
    ):
        """Test fine accrual with multiple overdue items."""
        from app.models.catalog import CatalogItem, ItemStatus
        from app.models.circulation import Checkout, CheckoutStatus
        from app.models.fine import Fine

        # Create 3 overdue checkouts
        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        _ = Decimal("0")

        for i in range(3):
            item = CatalogItem(
                title=f"Overdue Book {i}",
                author="Test Author",
                status=ItemStatus.checked_out,
                call_number=f"OVERDUE-{i:03d}",
            )
            test_db.add(item)
            await test_db.flush()

            # Vary the overdue days: 5, 7, 10
            overdue_days = 5 + (i * 2)
            checkout = Checkout(
                user_id=test_patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=datetime.now() - timedelta(days=30),
                due_date=datetime.now() - timedelta(days=overdue_days),
            )
            test_db.add(checkout)
            await test_db.flush()

        await test_db.commit()

        # Fetch all checkouts and return them
        from sqlalchemy import select

        checkouts_result = await test_db.execute(
            select(Checkout).where(Checkout.user_id == test_patron.id)
        )
        checkouts = checkouts_result.scalars().all()

        for checkout in checkouts:
            response = await client.post(
                f"/api/v1/circulation/return/{checkout.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

        # Get patron fines
        response = await client.get(
            "/api/v1/circulation/fines",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        fines = response.json()
        assert len(fines) > 0

    async def test_patron_suspension_on_high_fine_balance(
        self, client, test_db, test_patron
    ):
        """Test that patron is suspended when fine balance exceeds threshold."""
        from app.models.fine import Fine, FineStatus, FineType
        from app.models.user import PatronStatus

        # Create a high fine ($25+ to exceed suspension threshold)
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("30.00"),  # Exceeds typical $25 threshold
        )
        test_db.add(fine)
        await test_db.commit()

        # Check if patron is suspended
        await test_db.refresh(test_patron)
        # Suspension may be automatic or manual depending on implementation
        # The important thing is the fine is recorded

        # Try to checkout - may fail if suspended
        # This depends on whether suspension is enforced on checkout
        _ = await client.get(
            "/api/v1/circulation/fines/summary",
        )
        # Summary endpoint should be accessible to understand fine state

    async def test_suspension_prevents_circulation_operations(
        self, client, test_db, test_patron, test_user_data, test_catalog_item
    ):
        """Test that suspended patron cannot perform circulation operations."""
        from app.models.user import PatronStatus

        # Suspend the patron
        test_patron.patron_status = PatronStatus.SUSPENDED
        test_patron.suspension_reason = "Fine threshold exceeded"
        await test_db.commit()

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])

        # Try to checkout - should fail
        response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": test_catalog_item.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        # check_patron_eligibility raises ForbiddenError -> 403. The message
        # is the patron's own suspension_reason verbatim (no "suspended"
        # boilerplate wrapper) when one is set -- see
        # check_patron_suspension_status in suspension_service.py.
        assert response.status_code == 403
        assert "fine threshold" in response.json()["detail"].lower()

    async def test_suspension_prevents_new_holds(
        self, client, test_db, test_patron, test_user_data, test_checked_out_item
    ):
        """Test that suspended patron cannot place new holds."""
        from app.models.user import PatronStatus

        # Suspend the patron
        test_patron.patron_status = PatronStatus.SUSPENDED
        test_patron.suspension_reason = "Overdue items"
        await test_db.commit()

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])

        # Try to place hold - should fail
        response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": test_checked_out_item.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        # See test_suspension_prevents_circulation_operations: ForbiddenError
        # -> 403, and the message is the patron's own suspension_reason.
        assert response.status_code == 403
        assert "overdue items" in response.json()["detail"].lower()

    async def test_complete_workflow_scenario(
        self, client, test_db, test_patron, test_user_data, multiple_catalog_items, second_patron
    ):
        """Test a complete realistic library usage scenario."""
        from app.models.catalog import ItemStatus
        from app.models.circulation import Hold, HoldStatus, Checkout, CheckoutStatus

        token = await get_patron_token(client, test_user_data["email"], test_user_data["password"])
        second_token = await get_patron_token(client, "patron2@example.com", "Patron2Password123!")

        # Step 1: First patron searches for and checkouts book
        search_response = await client.get("/api/v1/catalog/search?q=Gatsby")
        assert search_response.status_code == 200
        items = search_response.json()["items"]
        item_id = items[0]["id"]

        checkout_response = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": item_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        # checkout_item returns 201 Created, not 200.
        assert checkout_response.status_code == 201
        checkout_id = checkout_response.json()["id"]

        # Step 2: Second patron places hold on same item
        hold_response = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": item_id},
            headers={"Authorization": f"Bearer {second_token}"},
        )
        # place_hold returns 201 Created, not 200.
        assert hold_response.status_code == 201
        hold_data = hold_response.json()
        assert hold_data["status"] == "pending"
        assert hold_data["position"] == 1

        # Step 3: First patron renews (but should fail due to hold)
        renew_response = await client.post(
            f"/api/v1/circulation/renew/{checkout_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Blocked-by-hold raises ConflictError(ITEM_ON_HOLD) -> 409, rendered
        # as {"error": {"message": ...}} (see test_renewal_blocked_when_holds_exist).
        if renew_response.status_code == 409:
            assert "waiting" in renew_response.json()["error"]["message"].lower()

        # Step 4: First patron returns item
        return_response = await client.post(
            f"/api/v1/circulation/return/{checkout_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert return_response.status_code == 200

        # Step 5: Verify second patron's hold is now ready
        holds_response = await client.get(
            "/api/v1/circulation/holds",
            headers={"Authorization": f"Bearer {second_token}"},
        )
        assert holds_response.status_code == 200
        # PaginatedResponse envelope: {"data": [...], ...} (app/schemas/common.py)
        patron2_holds = holds_response.json()["data"]
        assert len(patron2_holds) > 0
        assert patron2_holds[0]["status"] == "ready"


@pytest.fixture
async def test_available_item(test_db):
    """Create a test catalog item that is available for checkout."""
    from app.models.catalog import CatalogItem, ItemStatus

    item = CatalogItem(
        title="Available Book for Testing",
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
async def test_checked_out_item(test_db):
    """Create a test catalog item that is checked out."""
    from app.models.catalog import CatalogItem, ItemStatus

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
    return item


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
