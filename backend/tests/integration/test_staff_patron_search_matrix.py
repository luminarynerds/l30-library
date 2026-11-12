# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive search matrix tests for staff patron search endpoints.

Tests patron search functionality across all supported filters and criteria:
- Search by email, name, phone, library card
- Filter by status, role, library
- Pagination and sorting
- Edge cases and boundary conditions
"""

from datetime import datetime
import pytest
from sqlalchemy import select

from app.models.user import User, UserRole, PatronStatus


@pytest.fixture
def test_patron_data(test_user_data):
    """Alias onto the shared patron credentials fixture (test_patron uses these)."""
    return test_user_data


@pytest.fixture
async def search_test_patrons(test_db):
    """Create a diverse set of patrons for search testing."""
    from app.core.security import hash_password

    patrons = []

    # Active patrons with different names
    test_data = [
        {
            "email": "alice.smith@example.com",
            "first_name": "Alice",
            "last_name": "Smith",
            "phone": "555-0001",
            "library_card": "CARD-001",
            "is_active": True,
        },
        {
            "email": "bob.jones@example.com",
            "first_name": "Bob",
            "last_name": "Jones",
            "phone": "555-0002",
            "library_card": "CARD-002",
            "is_active": True,
        },
        {
            "email": "charlie.brown@example.com",
            "first_name": "Charlie",
            "last_name": "Brown",
            "phone": "555-0003",
            "library_card": "CARD-003",
            "is_active": True,
        },
        {
            "email": "diane.ross@example.com",
            "first_name": "Diane",
            "last_name": "Ross",
            "phone": "555-0004",
            "library_card": "CARD-004",
            "is_active": True,
        },
        {
            "email": "eve.miller@example.com",
            "first_name": "Eve",
            "last_name": "Miller",
            "phone": "555-0005",
            "library_card": "CARD-005",
            "is_active": False,  # Inactive patron
        },
        {
            "email": "frank.wilson@example.com",
            "first_name": "Frank",
            "last_name": "Wilson",
            "phone": "555-0006",
            "library_card": "CARD-006",
            "is_active": True,
        },
    ]

    for data in test_data:
        user = User(
            email=data["email"],
            password_hash=hash_password("TestPassword123!"),
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone=data["phone"],
            library_card=data["library_card"],
            role=UserRole.PATRON,
            is_active=data["is_active"],
            email_verified=True,
        )
        test_db.add(user)
        patrons.append(user)

    await test_db.commit()
    for patron in patrons:
        await test_db.refresh(patron)

    return patrons


@pytest.mark.integration
class TestStaffPatronSearchMatrix:
    """Test patron search with various query parameters and filters."""

    async def test_search_by_email(self, client, test_staff, test_staff_data, search_test_patrons):
        """Test searching patrons by email address."""
        from tests.conftest import get_staff_token

        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons?search=alice.smith@example.com",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["patrons"]) >= 1
        # UserResponse.email is above STAFF clearance (PIISensitivity.SENSITIVE
        # vs STAFF's INTERNAL, see app/core/pii_scope.py) so the PII filter
        # redacts it to None and populates email_masked instead
        # ("a***@example.com" -- see mask_email).
        assert any(
            p["email"] == "alice.smith@example.com" or p.get("email_masked") == "a***@example.com"
            for p in data["patrons"]
        )

    async def test_search_by_first_name(
        self, client, test_staff, test_staff_data, search_test_patrons
    ):
        """Test searching patrons by first name."""
        from tests.conftest import get_staff_token

        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons?search=Alice",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["patrons"]) >= 1
        assert any(p["first_name"] == "Alice" for p in data["patrons"])

    async def test_search_by_last_name(
        self, client, test_staff, test_staff_data, search_test_patrons
    ):
        """Test searching patrons by last name."""
        from tests.conftest import get_staff_token

        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons?search=Smith",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["patrons"]) >= 1

    async def test_search_by_phone(self, client, test_staff, test_staff_data, search_test_patrons):
        """Test searching patrons by phone number."""
        from tests.conftest import get_staff_token

        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons?search=555-0001",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["patrons"]) >= 1

    async def test_search_by_library_card(
        self, client, test_staff, test_staff_data, search_test_patrons
    ):
        """Test searching patrons by library card number."""
        from tests.conftest import get_staff_token

        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons?search=CARD-001",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["patrons"]) >= 1

    async def test_search_filters_inactive(
        self, client, test_staff, test_staff_data, search_test_patrons
    ):
        """Test that search includes inactive patrons by default."""
        from tests.conftest import get_staff_token

        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons?search=Eve",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["patrons"]) >= 1

    async def test_search_active_only_filter(
        self, client, test_staff, test_staff_data, search_test_patrons
    ):
        """Test filtering search results to active patrons only."""
        from tests.conftest import get_staff_token

        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons?search=Miller&is_active=true",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        # Eve Miller is inactive, should not appear with active_only=true
        assert not any(
            p.get("last_name") == "Miller" and not p.get("is_active") for p in data["patrons"]
        )

    async def test_search_pagination_limit(
        self, client, test_staff, test_staff_data, search_test_patrons
    ):
        """Test pagination with limit parameter."""
        from tests.conftest import get_staff_token

        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons?limit=2",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["patrons"]) <= 2

    async def test_search_pagination_offset(
        self, client, test_staff, test_staff_data, search_test_patrons
    ):
        """Test pagination with offset parameter."""
        from tests.conftest import get_staff_token

        token = await get_staff_token(client, test_staff_data)

        # Get first page
        response1 = await client.get(
            "/api/v1/staff/patrons?limit=2&offset=0",
            headers={"Authorization": f"Bearer {token}"},
        )
        data1 = response1.json()

        # Get second page
        response2 = await client.get(
            "/api/v1/staff/patrons?limit=2&offset=2",
            headers={"Authorization": f"Bearer {token}"},
        )
        data2 = response2.json()

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Results should be different
        ids1 = {p["id"] for p in data1["patrons"]}
        ids2 = {p["id"] for p in data2["patrons"]}
        assert ids1 != ids2 or len(ids1) == 0

    async def test_search_partial_match(
        self, client, test_staff, test_staff_data, search_test_patrons
    ):
        """Test that search performs partial matching.

        name_search_clause (app/models/user.py) only supports last-name
        PREFIX matching via a blind index -- first/last name are encrypted
        at rest, and "substring-anywhere is intentionally not supported"
        (maintainer decision, see the docstring). A first-name prefix like "Ali"
        for "Alice" can't match; "Smi" for last name "Smith" can.
        """
        from tests.conftest import get_staff_token

        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons?search=Smi",  # Partial match for last name Smith
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["patrons"]) >= 1

    async def test_search_case_insensitive(
        self, client, test_staff, test_staff_data, search_test_patrons
    ):
        """Test that search is case-insensitive."""
        from tests.conftest import get_staff_token

        token = await get_staff_token(client, test_staff_data)

        # Search with different cases
        response_upper = await client.get(
            "/api/v1/staff/patrons?search=ALICE",
            headers={"Authorization": f"Bearer {token}"},
        )
        response_lower = await client.get(
            "/api/v1/staff/patrons?search=alice",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response_upper.status_code == 200
        assert response_lower.status_code == 200

        # Should find same results
        data_upper = response_upper.json()
        data_lower = response_lower.json()
        assert len(data_upper["patrons"]) == len(data_lower["patrons"])

    async def test_search_empty_query(
        self, client, test_staff, test_staff_data, search_test_patrons
    ):
        """Test search with empty query returns all patrons."""
        from tests.conftest import get_staff_token

        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["patrons"]) > 0

    async def test_search_requires_staff_role(self, client, test_patron, test_patron_data):
        """Test that search requires staff or higher role."""
        from tests.conftest import get_patron_token

        token = await get_patron_token(client, test_patron_data)
        response = await client.get(
            "/api/v1/staff/patrons",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    async def test_search_returns_expected_fields(
        self, client, test_staff, test_staff_data, search_test_patrons
    ):
        """Test that search results contain expected user fields."""
        from tests.conftest import get_staff_token

        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons?search=Alice",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "patrons" in data
        assert "total_count" in data

        if data["patrons"]:
            patron = data["patrons"][0]
            # Expected fields in UserResponse
            assert "id" in patron
            assert "email" in patron
            assert "first_name" in patron
            assert "last_name" in patron
            assert "role" in patron
            assert "is_active" in patron
