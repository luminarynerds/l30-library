# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for reports API endpoints.
"""

from datetime import datetime, timedelta

import pytest


async def get_staff_token(client, test_staff_data):
    """Helper to get staff authentication token."""
    login_data = {
        "username": test_staff_data["email"],
        "password": test_staff_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


@pytest.fixture
async def test_overdue_checkout(test_db, test_patron, test_catalog_item):
    """Create a test checkout that is overdue."""
    from app.models.circulation import Checkout, CheckoutStatus

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
async def test_multiple_checkouts(test_db, test_patron, test_catalog_item):
    """Create multiple checkouts for trend testing."""
    from app.models.circulation import Checkout, CheckoutStatus

    checkouts = []
    for i in range(5):
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now() - timedelta(days=i),
            due_date=datetime.now() + timedelta(days=21 - i),
        )
        test_db.add(checkout)
        checkouts.append(checkout)

    await test_db.commit()
    for checkout in checkouts:
        await test_db.refresh(checkout)
    return checkouts


@pytest.fixture
async def test_ready_hold(test_db, test_patron):
    """Create a hold that is ready for pickup.

    Uses its own CatalogItem rather than the shared test_catalog_item: the
    conftest `test_hold` fixture (status=pending) already holds
    (test_patron, test_catalog_item), and ix_active_user_item_hold is a
    partial unique index on (user_id, item_id) WHERE status IN ('pending',
    'ready') -- reusing test_catalog_item here would collide whenever a
    test pulls in both fixtures together.
    """
    from app.models.catalog import CatalogItem, ItemStatus, ItemType
    from app.models.circulation import Hold, HoldStatus

    item = CatalogItem(
        title="Ready Hold Test Item",
        author="Test Author",
        isbn="978-0-999999-99-9",
        item_type=ItemType.book,
        status=ItemStatus.on_hold,
    )
    test_db.add(item)
    await test_db.flush()

    hold = Hold(
        user_id=test_patron.id,
        item_id=item.id,
        status=HoldStatus.ready,
        position=1,
        created_at=datetime.now(),
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)
    return hold


@pytest.fixture
async def test_paid_fine(test_db, test_patron):
    """Create a paid fine for testing."""
    from decimal import Decimal
    from app.models.fine import Fine, FineStatus, FineType

    fine = Fine(
        user_id=test_patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.paid,
        amount=Decimal("15.00"),
        amount_paid=Decimal("15.00"),
        description="Paid late return fine",
        created_at=datetime.now() - timedelta(days=5),
        paid_at=datetime.now() - timedelta(days=2),
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)
    return fine


@pytest.mark.integration
class TestCirculationReports:
    """Test circulation report endpoints."""

    async def test_daily_stats_requires_staff(self, client):
        """Test daily stats requires staff role."""
        response = await client.get("/api/v1/reports/circulation/daily")
        assert response.status_code == 401

    async def test_daily_stats_structure(self, client, test_staff, test_staff_data, test_checkout):
        """Test daily stats returns proper structure with authenticated staff user."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/daily", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # Verify required fields exist
        assert "date" in data
        assert "checkouts_today" in data
        assert "returns_today" in data
        assert "active_checkouts" in data
        assert "overdue_count" in data

        # Verify data types
        assert isinstance(data["checkouts_today"], int)
        assert isinstance(data["returns_today"], int)
        assert isinstance(data["active_checkouts"], int)
        assert isinstance(data["overdue_count"], int)
        assert isinstance(data["date"], str)

        # Verify counts are reasonable (should have at least 1 active checkout from fixture)
        assert data["active_checkouts"] >= 1

    async def test_overdue_items_report(
        self, client, test_staff, test_staff_data, test_overdue_checkout
    ):
        """Test overdue items report returns list of overdue checkouts."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert data["page"] == 1

        # Verify at least one overdue item is in the list
        assert len(data["items"]) > 0

        # Check first overdue item structure
        overdue_item = data["items"][0]
        assert "checkout_id" in overdue_item
        assert "patron_name" in overdue_item
        # @pii_filtered (app/api/v1/reports.py) drops the raw patron_email
        # for roles below SENSITIVE clearance (STAFF is INTERNAL) and emits
        # patron_email_masked instead -- see app/core/pii_scope.py's
        # _MASKABLE_FIELDS / filter_patron_data.
        assert "patron_email" in overdue_item or "patron_email_masked" in overdue_item
        assert "item_title" in overdue_item
        assert "due_date" in overdue_item
        assert "days_overdue" in overdue_item
        assert isinstance(overdue_item["days_overdue"], int)
        assert overdue_item["days_overdue"] >= 0

    async def test_popular_items_report(
        self, client, test_staff, test_staff_data, test_multiple_checkouts
    ):
        """Test popular items report returns ranked items by checkout count."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/popular?days=30&limit=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "items" in data
        assert "period_days" in data
        assert isinstance(data["items"], list)
        assert data["period_days"] == 30

        # Verify at least one popular item is returned
        assert len(data["items"]) > 0

        # Check popular item structure
        popular_item = data["items"][0]
        assert "catalog_item_id" in popular_item
        assert "title" in popular_item
        assert "author" in popular_item
        assert "checkout_count" in popular_item
        assert isinstance(popular_item["checkout_count"], int)
        assert popular_item["checkout_count"] > 0

    async def test_holds_stats(
        self, client, test_staff, test_staff_data, test_hold, test_ready_hold
    ):
        """Test hold queue statistics endpoint."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/holds", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "pending_holds" in data
        assert "ready_for_pickup" in data
        assert "avg_wait_days" in data

        # Verify data types
        assert isinstance(data["pending_holds"], int)
        assert isinstance(data["ready_for_pickup"], int)
        assert data["avg_wait_days"] is None or isinstance(data["avg_wait_days"], (int, float))

        # Verify we have at least one pending and one ready hold from fixtures
        assert data["pending_holds"] >= 1
        assert data["ready_for_pickup"] >= 1


@pytest.mark.integration
class TestFineReports:
    """Test fine-related reports."""

    async def test_fine_stats_requires_staff(self, client):
        """Test fine stats requires staff role."""
        response = await client.get("/api/v1/reports/circulation/fines")
        assert response.status_code == 401

    async def test_fine_stats_structure(
        self, client, test_staff, test_staff_data, test_fine, test_paid_fine
    ):
        """Test fine stats returns proper structure with authenticated staff user."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/fines", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()

        # Verify required fields exist
        assert "outstanding_total" in data
        assert "paid_this_month" in data
        assert "waived_this_month" in data
        assert "patrons_with_fines" in data

        # Verify data types
        assert isinstance(data["outstanding_total"], (int, float))
        assert isinstance(data["paid_this_month"], (int, float))
        assert isinstance(data["waived_this_month"], (int, float))
        assert isinstance(data["patrons_with_fines"], int)

        # Verify reasonable values
        assert data["outstanding_total"] >= 0
        assert data["paid_this_month"] >= 0
        assert data["waived_this_month"] >= 0
        assert data["patrons_with_fines"] >= 1  # At least the patron with unpaid fine


@pytest.mark.integration
class TestCirculationTrends:
    """Test circulation trend endpoints."""

    async def test_circulation_trends(
        self, client, test_staff, test_staff_data, test_multiple_checkouts
    ):
        """Test circulation trends endpoint returns daily checkout data."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/trends?days=30",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "data" in data
        assert "period_days" in data
        assert isinstance(data["data"], list)
        assert data["period_days"] == 30

        # Verify trend data points structure
        if len(data["data"]) > 0:
            data_point = data["data"][0]
            assert "date" in data_point
            assert "checkouts" in data_point
            assert isinstance(data_point["checkouts"], int)
            assert isinstance(data_point["date"], str)

        # Should have trend data from our test checkouts
        assert len(data["data"]) > 0
