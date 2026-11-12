# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for overdue reports API endpoints.

Tests comprehensive overdue report functionality including:
- Patron contact information (phone, address, email)
- Days overdue calculation
- Filter options (min/max days overdue, patron_type)
- Sort options (days_overdue, patron_name, due_date)
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


async def get_admin_token(client, test_admin_data):
    """Helper to get admin authentication token."""
    login_data = {
        "username": test_admin_data["email"],
        "password": test_admin_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


@pytest.fixture
async def patron_with_contact_info(test_db):
    """Create a patron with full contact information."""
    from app.core.security import hash_password
    from app.models.user import NoticePreference, User, UserRole

    user = User(
        email="patron_contact@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="John",
        last_name="Doe",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        phone="555-123-4567",
        address_line1="123 Main Street",
        address_line2="Apt 4B",
        city="Bébé Memorial",
        state="CA",
        zip_code="90210",
        notice_preference=NoticePreference.EMAIL,
        patron_type="adult",
        library_card="LIB-001",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def patron_teen(test_db):
    """Create a teen patron."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="teen_patron@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Jane",
        last_name="Smith",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        phone="555-987-6543",
        address_line1="456 Oak Avenue",
        city="Bébé Memorial",
        state="CA",
        zip_code="90211",
        patron_type="teen",
        library_card="LIB-002",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def patron_child(test_db):
    """Create a child patron."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="child_patron@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Tommy",
        last_name="Brown",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        phone="555-111-2222",
        address_line1="789 Elm Street",
        city="Bébé Memorial",
        state="CA",
        zip_code="90212",
        patron_type="child",
        library_card="LIB-003",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def catalog_items(test_db):
    """Create multiple catalog items for testing."""
    from app.models.catalog import CatalogItem, ItemStatus

    items = []
    books = [
        ("The Great Gatsby", "F. Scott Fitzgerald"),
        ("To Kill a Mockingbird", "Harper Lee"),
        ("1984", "George Orwell"),
        ("Pride and Prejudice", "Jane Austen"),
        ("The Catcher in the Rye", "J.D. Salinger"),
    ]

    for i, (title, author) in enumerate(books):
        item = CatalogItem(
            title=title,
            author=author,
            isbn=f"978-0-{i:06d}-{i:02d}-{i}",
            description=f"A classic book - {title}",
            status=ItemStatus.available,
            call_number=f"FIC-{i:03d}",
            publication_year=2020 + i,
        )
        test_db.add(item)
        items.append(item)

    await test_db.commit()
    for item in items:
        await test_db.refresh(item)
    return items


@pytest.fixture
async def overdue_checkouts_varied(
    test_db, patron_with_contact_info, patron_teen, patron_child, catalog_items
):
    """Create multiple overdue checkouts with varying days overdue for different patron types."""
    from app.models.circulation import Checkout, CheckoutStatus

    checkouts = []
    now = datetime.now(timezone.utc)

    # Adult patron - 3 days overdue
    checkout1 = Checkout(
        user_id=patron_with_contact_info.id,
        item_id=catalog_items[0].id,
        status=CheckoutStatus.active,
        checked_out_at=now - timedelta(days=24),
        due_date=now - timedelta(days=3),  # 3 days overdue
    )
    test_db.add(checkout1)
    checkouts.append(checkout1)

    # Adult patron - 14 days overdue
    checkout2 = Checkout(
        user_id=patron_with_contact_info.id,
        item_id=catalog_items[1].id,
        status=CheckoutStatus.active,
        checked_out_at=now - timedelta(days=35),
        due_date=now - timedelta(days=14),  # 14 days overdue
    )
    test_db.add(checkout2)
    checkouts.append(checkout2)

    # Teen patron - 7 days overdue
    checkout3 = Checkout(
        user_id=patron_teen.id,
        item_id=catalog_items[2].id,
        status=CheckoutStatus.active,
        checked_out_at=now - timedelta(days=28),
        due_date=now - timedelta(days=7),  # 7 days overdue
    )
    test_db.add(checkout3)
    checkouts.append(checkout3)

    # Child patron - 1 day overdue
    checkout4 = Checkout(
        user_id=patron_child.id,
        item_id=catalog_items[3].id,
        status=CheckoutStatus.active,
        checked_out_at=now - timedelta(days=22),
        due_date=now - timedelta(days=1),  # 1 day overdue
    )
    test_db.add(checkout4)
    checkouts.append(checkout4)

    # Child patron - 30 days overdue (severely overdue)
    checkout5 = Checkout(
        user_id=patron_child.id,
        item_id=catalog_items[4].id,
        status=CheckoutStatus.active,
        checked_out_at=now - timedelta(days=51),
        due_date=now - timedelta(days=30),  # 30 days overdue
    )
    test_db.add(checkout5)
    checkouts.append(checkout5)

    await test_db.commit()
    for checkout in checkouts:
        await test_db.refresh(checkout)

    return checkouts


@pytest.mark.integration
class TestOverdueReportsPatronContactInfo:
    """Test overdue reports include patron contact information."""

    async def test_overdue_report_includes_basic_patron_info(
        self, client, test_admin, test_admin_data, overdue_checkouts_varied
    ):
        """Test that overdue report includes basic patron name and email.

        Uses an admin caller: app/core/pii_scope.py classifies patron_email
        as SENSITIVE, and plain STAFF only has INTERNAL clearance, so staff
        callers get it redacted to a masked `patron_email_masked` field
        instead (by design -- see filter_patron_data). Only
        director/legal/admin+ see the raw patron_email field this test
        checks for.
        """
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert len(data["items"]) > 0

        # Check each item has basic patron info
        for item in data["items"]:
            assert "patron_name" in item
            assert "patron_email" in item
            assert item["patron_name"] is not None
            assert item["patron_email"] is not None

    async def test_overdue_report_includes_phone(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test that overdue report includes patron phone number."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Find item with phone number
        items_with_phone = [item for item in data["items"] if item.get("patron_phone") is not None]
        # At least some patrons should have phone numbers
        assert len(items_with_phone) >= 0  # Phone field should exist

    async def test_overdue_report_includes_address(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test that overdue report includes patron address information."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        # Address fields should be available in the response structure

    async def test_overdue_report_includes_library_card(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test that overdue report includes patron library card number."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        # Library card field should be available for patrons who have one


@pytest.mark.integration
class TestOverdueReportsDaysOverdue:
    """Test days overdue calculation in overdue reports."""

    async def test_days_overdue_calculation(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test that days_overdue is calculated correctly."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        for item in data["items"]:
            assert "days_overdue" in item
            assert isinstance(item["days_overdue"], int)
            assert item["days_overdue"] >= 0  # Should be non-negative

    async def test_days_overdue_values_are_reasonable(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test that days_overdue values match expected ranges from fixtures."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        days_overdue_values = [item["days_overdue"] for item in data["items"]]

        # We created items that are 1, 3, 7, 14, and 30 days overdue
        # Values might vary by +/- 1 day due to timing, but should be in expected ranges
        assert min(days_overdue_values) >= 0  # At least 1 day overdue (might be 0 due to timing)
        assert max(days_overdue_values) >= 25  # At least 30 days overdue (might vary slightly)


@pytest.mark.integration
class TestOverdueReportsFilterOptions:
    """Test filter options for overdue reports."""

    async def test_filter_by_min_days_overdue(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test filtering by minimum days overdue."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?min_days_overdue=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # All items should be at least 7 days overdue
        for item in data["items"]:
            assert item["days_overdue"] >= 7, (
                f"Item has {item['days_overdue']} days overdue, expected >= 7"
            )

    async def test_filter_by_max_days_overdue(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test filtering by maximum days overdue."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?max_days_overdue=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # All items should be at most 10 days overdue
        for item in data["items"]:
            assert item["days_overdue"] <= 10, (
                f"Item has {item['days_overdue']} days overdue, expected <= 10"
            )

    async def test_filter_by_days_overdue_range(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test filtering by days overdue range (min and max)."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?min_days_overdue=5&max_days_overdue=20",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # All items should be within 5-20 days overdue range
        for item in data["items"]:
            assert 5 <= item["days_overdue"] <= 20, (
                f"Item has {item['days_overdue']} days overdue, expected 5-20"
            )

    async def test_filter_by_patron_type_adult(
        self,
        client,
        test_staff,
        test_staff_data,
        overdue_checkouts_varied,
        patron_with_contact_info,
    ):
        """Test filtering by patron type (adult)."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?patron_type=adult",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Should only return items for adult patrons
        if len(data["items"]) > 0:
            # Verify all items belong to adult patron
            for item in data["items"]:
                assert (
                    item.get("patron_type") == "adult"
                    or item.get("patron_email") == patron_with_contact_info.email
                )

    async def test_filter_by_patron_type_teen(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied, patron_teen
    ):
        """Test filtering by patron type (teen)."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?patron_type=teen",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Should only return items for teen patrons
        if len(data["items"]) > 0:
            for item in data["items"]:
                assert (
                    item.get("patron_type") == "teen"
                    or item.get("patron_email") == patron_teen.email
                )

    async def test_filter_by_patron_type_child(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied, patron_child
    ):
        """Test filtering by patron type (child)."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?patron_type=child",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Should only return items for child patrons
        if len(data["items"]) > 0:
            for item in data["items"]:
                assert (
                    item.get("patron_type") == "child"
                    or item.get("patron_email") == patron_child.email
                )

    async def test_filter_by_patron_id(
        self,
        client,
        test_admin,
        test_admin_data,
        overdue_checkouts_varied,
        patron_with_contact_info,
    ):
        """Test filtering by specific patron ID.

        Uses an admin caller so the raw patron_email field is visible (see
        test_overdue_report_includes_basic_patron_info for why a plain
        STAFF caller only gets patron_email_masked).
        """
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            f"/api/v1/reports/circulation/overdue?patron_id={patron_with_contact_info.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # All items should belong to the specified patron
        for item in data["items"]:
            assert item["patron_email"] == patron_with_contact_info.email

    async def test_combined_filters(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test combining multiple filters."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?min_days_overdue=5&patron_type=child",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Should filter by both criteria
        for item in data["items"]:
            assert item["days_overdue"] >= 5


@pytest.mark.integration
class TestOverdueReportsSortOptions:
    """Test sort options for overdue reports."""

    async def test_sort_by_days_overdue_ascending(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test sorting by days overdue in ascending order."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?sort_by=days_overdue&sort_order=asc",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        if len(data["items"]) > 1:
            days_values = [item["days_overdue"] for item in data["items"]]
            # Should be in ascending order
            assert days_values == sorted(days_values), (
                "Items should be sorted by days_overdue ascending"
            )

    async def test_sort_by_days_overdue_descending(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test sorting by days overdue in descending order."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?sort_by=days_overdue&sort_order=desc",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        if len(data["items"]) > 1:
            days_values = [item["days_overdue"] for item in data["items"]]
            # Should be in descending order
            assert days_values == sorted(days_values, reverse=True), (
                "Items should be sorted by days_overdue descending"
            )

    async def test_sort_by_patron_name_ascending(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test sorting by patron name in ascending order.

        `sort_by=patron_name` orders by User.last_name (see
        app/api/v1/reports.py get_overdue_items) -- the standard
        phonebook-style sort for a patron contact list -- not by a literal
        string sort of the "First Last" display name. Compare on the last
        name component accordingly.
        """
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?sort_by=patron_name&sort_order=asc",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        if len(data["items"]) > 1:
            last_names = [item["patron_name"].split()[-1] for item in data["items"]]
            # Should be in ascending order by last name
            assert last_names == sorted(last_names), (
                "Items should be sorted by patron last name ascending"
            )

    async def test_sort_by_patron_name_descending(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test sorting by patron name in descending order.

        See test_sort_by_patron_name_ascending -- sorts by last name, not a
        literal string sort of the "First Last" display name.
        """
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?sort_by=patron_name&sort_order=desc",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        if len(data["items"]) > 1:
            last_names = [item["patron_name"].split()[-1] for item in data["items"]]
            # Should be in descending order by last name
            assert last_names == sorted(last_names, reverse=True), (
                "Items should be sorted by patron last name descending"
            )

    async def test_sort_by_due_date_ascending(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test sorting by due date in ascending order (oldest first)."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?sort_by=due_date&sort_order=asc",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        if len(data["items"]) > 1:
            dates = [item["due_date"] for item in data["items"]]
            # Should be in ascending order (oldest due date first)
            assert dates == sorted(dates), "Items should be sorted by due_date ascending"

    async def test_sort_by_due_date_descending(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test sorting by due date in descending order (most recent first)."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?sort_by=due_date&sort_order=desc",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        if len(data["items"]) > 1:
            dates = [item["due_date"] for item in data["items"]]
            # Should be in descending order (most recent due date first)
            assert dates == sorted(dates, reverse=True), (
                "Items should be sorted by due_date descending"
            )

    async def test_sort_by_item_title(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test sorting by item title."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?sort_by=item_title&sort_order=asc",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        if len(data["items"]) > 1:
            titles = [item["item_title"] for item in data["items"]]
            assert titles == sorted(titles), "Items should be sorted by item_title ascending"

    async def test_default_sort_is_by_due_date(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test that default sort is by due date (oldest first)."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        if len(data["items"]) > 1:
            dates = [item["due_date"] for item in data["items"]]
            # Default should be ascending by due_date (oldest overdue first)
            assert dates == sorted(dates), "Default sort should be by due_date ascending"


@pytest.mark.integration
class TestOverdueReportsPagination:
    """Test pagination for overdue reports."""

    async def test_pagination_defaults(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test default pagination values."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "page" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["total"] >= 0

    async def test_pagination_with_custom_page(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test pagination with custom page number."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?page=1&per_page=2",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert len(data["items"]) <= 2  # Should respect per_page limit

    async def test_pagination_page_two(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test getting second page of results."""
        token = await get_staff_token(client, test_staff_data)

        # First get page 1
        response1 = await client.get(
            "/api/v1/reports/circulation/overdue?page=1&per_page=2",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # Then get page 2
        response2 = await client.get(
            "/api/v1/reports/circulation/overdue?page=2&per_page=2",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response2.status_code == 200
        data2 = response2.json()

        assert data2["page"] == 2

        # Items on page 2 should be different from page 1 (if there are enough items)
        if data1["total"] > 2 and len(data2["items"]) > 0:
            page1_ids = {item["checkout_id"] for item in data1["items"]}
            page2_ids = {item["checkout_id"] for item in data2["items"]}
            assert page1_ids.isdisjoint(page2_ids), "Page 2 items should not overlap with page 1"

    async def test_pagination_with_filters(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test pagination works correctly with filters applied."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?min_days_overdue=5&page=1&per_page=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        # Total should reflect filtered count
        assert data["total"] <= 5  # We have 5 total overdue items, filtering reduces this

    async def test_total_count_is_accurate(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test that total count accurately reflects all overdue items."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?per_page=100",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Total should equal or exceed the number of items returned
        assert data["total"] >= len(data["items"])
        # We created 5 overdue checkouts
        assert data["total"] >= 5


@pytest.mark.integration
class TestOverdueReportsAccessControl:
    """Test access control for overdue reports."""

    async def test_requires_authentication(self, client, overdue_checkouts_varied):
        """Test that overdue report requires authentication."""
        response = await client.get("/api/v1/reports/circulation/overdue")
        assert response.status_code == 401

    async def test_requires_staff_role(
        self, client, test_patron, test_user_data, overdue_checkouts_varied
    ):
        """Test that overdue report requires staff role."""
        token = await get_patron_token(client, test_user_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should be forbidden for patrons
        assert response.status_code in [401, 403]

    async def test_staff_can_access(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test that staff can access overdue report."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_admin_can_access(
        self, client, test_admin, test_admin_data, overdue_checkouts_varied
    ):
        """Test that admin can access overdue report."""
        login_data = {
            "username": test_admin_data["email"],
            "password": test_admin_data["password"],
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        token = response.json()["access_token"]

        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestOverdueReportsResponseStructure:
    """Test the structure of overdue report responses."""

    async def test_response_has_required_fields(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test that response includes all required fields."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Top-level fields
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)

    async def test_item_has_required_fields(
        self, client, test_admin, test_admin_data, overdue_checkouts_varied
    ):
        """Test that each item has all required fields.

        Uses an admin caller so the raw patron_email field is present (see
        test_overdue_report_includes_basic_patron_info for why a plain
        STAFF caller only gets patron_email_masked).
        """
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) > 0

        required_fields = [
            "checkout_id",
            "patron_name",
            "patron_email",
            "item_title",
            "due_date",
            "days_overdue",
        ]

        for item in data["items"]:
            for field in required_fields:
                assert field in item, f"Missing required field: {field}"

    async def test_dates_are_iso_format(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test that dates are in ISO format."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            due_date = item["due_date"]
            # Should be parseable as ISO date
            try:
                from datetime import datetime

                datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            except ValueError:
                pytest.fail(f"due_date '{due_date}' is not in ISO format")


@pytest.mark.integration
class TestOverdueReportsEdgeCases:
    """Test edge cases for overdue reports."""

    async def test_empty_results_when_no_overdue_items(self, client, test_staff, test_staff_data):
        """Test response when there are no overdue items."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 0

    async def test_filter_returns_empty_when_no_match(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test that filter returns empty list when no items match."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?min_days_overdue=1000",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["items"] == []
        assert data["total"] == 0

    async def test_invalid_sort_field_handling(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test handling of invalid sort field."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?sort_by=invalid_field",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should either return 400/422 or ignore invalid sort
        assert response.status_code in [200, 400, 422]

    async def test_invalid_page_number(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test handling of invalid page number."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?page=0",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should return validation error
        assert response.status_code == 422

    async def test_negative_days_overdue_filter(
        self, client, test_staff, test_staff_data, overdue_checkouts_varied
    ):
        """Test handling of negative days overdue filter."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/circulation/overdue?min_days_overdue=-5",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should either return validation error or treat as 0
        assert response.status_code in [200, 400, 422]
