# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the hold aging report endpoint.
"""

from datetime import datetime, timedelta, timezone

import pytest


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


@pytest.fixture
async def test_catalog_item_with_location(test_db):
    """Create a test catalog item with a location for filtering tests."""
    from app.models.catalog import CatalogItem, ItemStatus

    item = CatalogItem(
        title="Book at Main Library",
        author="Location Author",
        isbn="978-0-111111-11-1",
        description="A test book with location",
        status=ItemStatus.available,
        call_number="LOC-001",
        location="Main Library",
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def test_catalog_item_branch(test_db):
    """Create a test catalog item at a branch location."""
    from app.models.catalog import CatalogItem, ItemStatus

    item = CatalogItem(
        title="Book at Branch Library",
        author="Branch Author",
        isbn="978-0-222222-22-2",
        description="A test book at branch",
        status=ItemStatus.available,
        call_number="LOC-002",
        location="Branch Library",
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def pending_holds_various_ages(test_db, test_patron, test_catalog_item):
    """Create pending holds with various ages for testing."""
    from app.models.circulation import Hold, HoldStatus

    now = datetime.now(timezone.utc)
    holds = []

    # Create holds at different ages
    ages_in_days = [1, 5, 10, 20, 35, 45]  # 2 in 0-7, 1 in 7-14, 1 in 14-30, 2 in 30+

    for i, days_ago in enumerate(ages_in_days):
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id + i if i > 0 else test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
            created_at=now - timedelta(days=days_ago),
        )
        test_db.add(hold)
        holds.append(hold)

    await test_db.commit()
    for hold in holds:
        await test_db.refresh(hold)
    return holds


@pytest.fixture
async def pending_hold_old(test_db, test_patron, test_catalog_item):
    """Create an old pending hold (30+ days)."""
    from app.models.circulation import Hold, HoldStatus

    hold = Hold(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.pending,
        position=1,
        created_at=datetime.now(timezone.utc) - timedelta(days=35),
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)
    return hold


@pytest.fixture
async def pending_hold_recent(test_db, test_patron, test_catalog_item):
    """Create a recent pending hold (0-7 days)."""
    from app.models.circulation import Hold, HoldStatus

    hold = Hold(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.pending,
        position=1,
        created_at=datetime.now(timezone.utc) - timedelta(days=3),
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)
    return hold


@pytest.fixture
async def pending_hold_at_location(test_db, test_patron, test_catalog_item_with_location):
    """Create a pending hold for an item at a specific location."""
    from app.models.circulation import Hold, HoldStatus

    hold = Hold(
        user_id=test_patron.id,
        item_id=test_catalog_item_with_location.id,
        status=HoldStatus.pending,
        position=1,
        created_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)
    return hold


@pytest.mark.integration
class TestHoldAgingReportAccess:
    """Test access control for the hold aging report endpoint."""

    async def test_aging_report_requires_authentication(self, client):
        """Test that the aging report requires authentication."""
        response = await client.get("/api/v1/circulation/holds/aging-report")
        assert response.status_code == 401

    async def test_aging_report_forbidden_for_patrons(
        self, client, test_patron, test_user_data
    ):
        """Test that patrons cannot access the aging report."""
        token = await get_patron_token(client, test_user_data)
        response = await client.get(
            "/api/v1/circulation/holds/aging-report",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        message = response.json()["error"]["message"]
        assert "staff" in message.lower() or "admin" in message.lower()

    async def test_aging_report_allowed_for_staff(
        self, client, test_staff, test_staff_data
    ):
        """Test that staff can access the aging report."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/circulation/holds/aging-report",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_aging_report_allowed_for_admin(
        self, client, test_admin, test_admin_data
    ):
        """Test that admins can access the aging report."""
        login_data = {
            "username": test_admin_data["email"],
            "password": test_admin_data["password"],
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/circulation/holds/aging-report",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestHoldAgingReportCalculations:
    """Test aging calculations in the hold aging report."""

    async def test_empty_report_when_no_pending_holds(
        self, client, test_staff, test_staff_data
    ):
        """Test that report handles no pending holds gracefully."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/circulation/holds/aging-report",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_pending_holds"] == 0
        assert data["average_wait_days"] == 0.0
        assert data["longest_wait_days"] == 0
        assert len(data["brackets"]) == 4

        # All brackets should have count 0
        for bracket in data["brackets"]:
            assert bracket["count"] == 0

    async def test_single_recent_hold(
        self, client, test_staff, test_staff_data, pending_hold_recent
    ):
        """Test aging report with a single recent hold."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/circulation/holds/aging-report",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_pending_holds"] == 1
        assert 2 <= data["average_wait_days"] <= 4  # Around 3 days
        assert 2 <= data["longest_wait_days"] <= 4

        # Should be in 0-7 days bracket
        bracket_0_7 = next(b for b in data["brackets"] if b["bracket_label"] == "0-7 days")
        assert bracket_0_7["count"] == 1

    async def test_single_old_hold(
        self, client, test_staff, test_staff_data, pending_hold_old
    ):
        """Test aging report with a single old hold (30+ days)."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/circulation/holds/aging-report",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_pending_holds"] == 1
        assert data["average_wait_days"] >= 34
        assert data["longest_wait_days"] >= 34

        # Should be in 30+ days bracket
        bracket_30_plus = next(b for b in data["brackets"] if b["bracket_label"] == "30+ days")
        assert bracket_30_plus["count"] == 1

    async def test_bracket_labels_and_ranges(
        self, client, test_staff, test_staff_data
    ):
        """Test that bracket labels and ranges are correct."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/circulation/holds/aging-report",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        brackets = data["brackets"]
        assert len(brackets) == 4

        # Verify bracket definitions
        expected_brackets = [
            {"label": "0-7 days", "min": 0, "max": 7},
            {"label": "7-14 days", "min": 7, "max": 14},
            {"label": "14-30 days", "min": 14, "max": 30},
            {"label": "30+ days", "min": 30, "max": None},
        ]

        for expected, actual in zip(expected_brackets, brackets):
            assert actual["bracket_label"] == expected["label"]
            assert actual["min_days"] == expected["min"]
            assert actual["max_days"] == expected["max"]


@pytest.mark.integration
class TestHoldAgingReportFiltering:
    """Test filtering in the hold aging report."""

    async def test_filter_by_item_id(
        self, client, test_staff, test_staff_data, pending_hold_recent, test_catalog_item
    ):
        """Test filtering by item ID."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            f"/api/v1/circulation/holds/aging-report?item_id={test_catalog_item.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_pending_holds"] == 1
        assert data["filtered_by_item_id"] == test_catalog_item.id

    async def test_filter_by_nonexistent_item(
        self, client, test_staff, test_staff_data, pending_hold_recent
    ):
        """Test filtering by non-existent item returns empty results."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/circulation/holds/aging-report?item_id=99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_pending_holds"] == 0
        assert data["filtered_by_item_id"] == 99999

    async def test_filter_by_location(
        self, client, test_staff, test_staff_data, pending_hold_at_location, test_catalog_item_with_location
    ):
        """Test filtering by location."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/circulation/holds/aging-report?location=Main%20Library",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_pending_holds"] == 1
        assert data["filtered_by_location"] == "Main Library"

    async def test_filter_by_nonexistent_location(
        self, client, test_staff, test_staff_data, pending_hold_at_location
    ):
        """Test filtering by non-existent location returns empty results."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/circulation/holds/aging-report?location=Nonexistent%20Location",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_pending_holds"] == 0
        assert data["filtered_by_location"] == "Nonexistent Location"

    async def test_filter_by_date_range(
        self, client, test_db, test_staff, test_staff_data, test_patron, test_catalog_item
    ):
        """Test filtering by date range."""
        from app.models.circulation import Hold, HoldStatus

        now = datetime.now(timezone.utc)

        # Create holds at different times
        # Hold 1: 5 days ago (in range)
        hold1 = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
            created_at=now - timedelta(days=5),
        )
        test_db.add(hold1)
        await test_db.commit()

        token = await get_staff_token(client, test_staff_data)

        # Filter for holds created in the last 7 days
        date_from = (now - timedelta(days=7)).isoformat()
        response = await client.get(
            "/api/v1/circulation/holds/aging-report",
            params={"date_from": date_from},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_pending_holds"] >= 1
        assert data["filtered_by_date_from"] is not None

    async def test_combined_filters(
        self, client, test_staff, test_staff_data, pending_hold_at_location, test_catalog_item_with_location
    ):
        """Test combining multiple filters."""
        token = await get_staff_token(client, test_staff_data)

        now = datetime.now(timezone.utc)
        date_from = (now - timedelta(days=30)).isoformat()

        response = await client.get(
            "/api/v1/circulation/holds/aging-report",
            params={"location": "Main Library", "date_from": date_from},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["filtered_by_location"] == "Main Library"
        assert data["filtered_by_date_from"] is not None


@pytest.mark.integration
class TestHoldAgingReportResponseStructure:
    """Test the structure of the hold aging report response."""

    async def test_response_has_all_required_fields(
        self, client, test_staff, test_staff_data
    ):
        """Test that response contains all required fields."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/circulation/holds/aging-report",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Check required fields exist
        assert "total_pending_holds" in data
        assert "average_wait_days" in data
        assert "longest_wait_days" in data
        assert "brackets" in data

        # Check optional filter fields exist
        assert "filtered_by_item_id" in data
        assert "filtered_by_location" in data
        assert "filtered_by_date_from" in data
        assert "filtered_by_date_to" in data

    async def test_brackets_have_correct_structure(
        self, client, test_staff, test_staff_data
    ):
        """Test that each bracket has the correct structure."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/circulation/holds/aging-report",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        for bracket in data["brackets"]:
            assert "bracket_label" in bracket
            assert "min_days" in bracket
            assert "max_days" in bracket
            assert "count" in bracket

            # Verify types
            assert isinstance(bracket["bracket_label"], str)
            assert isinstance(bracket["min_days"], int)
            assert bracket["max_days"] is None or isinstance(bracket["max_days"], int)
            assert isinstance(bracket["count"], int)
            assert bracket["count"] >= 0

    async def test_numeric_fields_are_correct_types(
        self, client, test_staff, test_staff_data, pending_hold_recent
    ):
        """Test that numeric fields have correct types."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/circulation/holds/aging-report",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["total_pending_holds"], int)
        assert isinstance(data["average_wait_days"], (int, float))
        assert isinstance(data["longest_wait_days"], int)
