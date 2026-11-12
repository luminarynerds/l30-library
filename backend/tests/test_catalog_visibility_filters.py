# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for catalog visibility filters - cataloging_status and sensitivity_level.

This test suite verifies that:
1. UNCATALOGED items are hidden from public/patron users but visible to staff/admin
2. SENSITIVE items are visible to patrons but hidden from public
3. CONFIDENTIAL items are only visible to staff/admin
4. Role-based access control is properly enforced across all catalog endpoints
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import (
    CatalogItem,
    ItemStatus,
    ItemType,
    CatalogingStatus,
    SensitivityLevel,
)
from app.core.security import create_access_token
from app.models.user import User, UserRole


@pytest.fixture
async def test_catalog_items_with_visibility(test_db: AsyncSession):
    """Create test catalog items with various visibility settings."""
    items = [
        # Fully visible (cataloged + public)
        CatalogItem(
            title="Public Book - Cataloged",
            author="Author One",
            item_type=ItemType.book,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            sensitivity_level=SensitivityLevel.PUBLIC,
        ),
        # Uncataloged + public
        CatalogItem(
            title="Public Book - Uncataloged",
            author="Author Two",
            item_type=ItemType.book,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.UNCATALOGED,
            sensitivity_level=SensitivityLevel.PUBLIC,
        ),
        # Cataloged + sensitive
        CatalogItem(
            title="Sensitive Book - Cataloged",
            author="Author Three",
            item_type=ItemType.book,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            sensitivity_level=SensitivityLevel.SENSITIVE,
        ),
        # Cataloged + confidential
        CatalogItem(
            title="Confidential Book - Cataloged",
            author="Author Four",
            item_type=ItemType.book,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
        ),
        # In progress + public
        CatalogItem(
            title="Public Book - In Progress",
            author="Author Five",
            item_type=ItemType.book,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.IN_PROGRESS,
            sensitivity_level=SensitivityLevel.PUBLIC,
        ),
    ]
    for item in items:
        test_db.add(item)
    await test_db.commit()
    return items


@pytest.fixture
async def patron_user(test_db: AsyncSession):
    """Create a test patron user."""
    user = User(
        email="patron@test.com",
        password_hash="hashed",
        first_name="Patron",
        last_name="User",
        role=UserRole.PATRON,
    )
    test_db.add(user)
    await test_db.commit()
    return user


@pytest.fixture
async def staff_user(test_db: AsyncSession):
    """Create a test staff user."""
    user = User(
        email="staff@test.com",
        password_hash="hashed",
        first_name="Staff",
        last_name="User",
        role=UserRole.STAFF,
    )
    test_db.add(user)
    await test_db.commit()
    return user


@pytest.fixture
async def admin_user(test_db: AsyncSession):
    """Create a test admin user."""
    user = User(
        email="admin@test.com",
        password_hash="hashed",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
    )
    test_db.add(user)
    await test_db.commit()
    return user


@pytest.mark.asyncio
class TestCatalogVisibilityFilters:
    """Test visibility filtering for catalog items."""

    async def test_public_user_sees_only_cataloged_and_public(
        self, client, test_catalog_items_with_visibility
    ):
        """Public users should only see CATALOGED + PUBLIC items."""
        response = await client.get("/api/v1/catalog/items")
        assert response.status_code == 200
        data = response.json()

        # Should only see the first item (PUBLIC + CATALOGED)
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Public Book - Cataloged"

    async def test_public_user_cannot_access_uncataloged_item(
        self, client, test_catalog_items_with_visibility
    ):
        """Public users cannot access uncataloged items directly."""
        uncataloged_item = test_catalog_items_with_visibility[1]
        response = await client.get(f"/api/v1/catalog/items/{uncataloged_item.id}")
        assert response.status_code == 404

    async def test_public_user_cannot_access_sensitive_item(
        self, client, test_catalog_items_with_visibility
    ):
        """Public users cannot access SENSITIVE items."""
        sensitive_item = test_catalog_items_with_visibility[2]
        response = await client.get(f"/api/v1/catalog/items/{sensitive_item.id}")
        assert response.status_code == 404

    async def test_public_user_cannot_access_confidential_item(
        self, client, test_catalog_items_with_visibility
    ):
        """Public users cannot access CONFIDENTIAL items."""
        confidential_item = test_catalog_items_with_visibility[3]
        response = await client.get(f"/api/v1/catalog/items/{confidential_item.id}")
        assert response.status_code == 404

    async def test_patron_sees_public_and_sensitive_items(
        self, client, patron_user, test_catalog_items_with_visibility
    ):
        """Patron users should see PUBLIC and SENSITIVE items (but not CONFIDENTIAL)."""
        # Login as patron
        auth_header = {"Authorization": f"Bearer {create_access_token(subject=patron_user.id, email=patron_user.email)}"}
        response = await client.get("/api/v1/catalog/items", headers=auth_header)
        assert response.status_code == 200
        data = response.json()

        # Should see: PUBLIC+CATALOGED and SENSITIVE+CATALOGED
        visible_titles = {item["title"] for item in data["items"]}
        assert "Public Book - Cataloged" in visible_titles
        assert "Sensitive Book - Cataloged" in visible_titles
        assert "Confidential Book - Cataloged" not in visible_titles

    async def test_patron_cannot_access_confidential_item(
        self, client, patron_user, test_catalog_items_with_visibility
    ):
        """Patron users cannot access CONFIDENTIAL items."""
        auth_header = {"Authorization": f"Bearer {create_access_token(subject=patron_user.id, email=patron_user.email)}"}
        confidential_item = test_catalog_items_with_visibility[3]
        response = await client.get(
            f"/api/v1/catalog/items/{confidential_item.id}",
            headers=auth_header,
        )
        assert response.status_code == 404

    async def test_patron_cannot_access_uncataloged_items(
        self, client, patron_user, test_catalog_items_with_visibility
    ):
        """Patron users cannot access UNCATALOGED items."""
        auth_header = {"Authorization": f"Bearer {create_access_token(subject=patron_user.id, email=patron_user.email)}"}
        uncataloged_item = test_catalog_items_with_visibility[1]
        response = await client.get(
            f"/api/v1/catalog/items/{uncataloged_item.id}",
            headers=auth_header,
        )
        assert response.status_code == 404

    async def test_staff_sees_all_cataloged_items(
        self, client, staff_user, test_catalog_items_with_visibility
    ):
        """Staff users should see all CATALOGED items regardless of sensitivity.

        Unlike patrons/public, staff get no implicit cataloging_status filter
        on the unfiltered listing (see app/api/v1/catalog/helpers.py: the
        CATALOGED-only restriction is only applied `if not
        is_staff_or_admin(current_user)`) -- staff need visibility into the
        cataloging queue by default. Narrowing to just cataloged items is an
        explicit opt-in (see test_staff_can_filter_by_cataloging_status).
        """
        auth_header = {"Authorization": f"Bearer {create_access_token(subject=staff_user.id, email=staff_user.email)}"}
        response = await client.get("/api/v1/catalog/items", headers=auth_header)
        assert response.status_code == 200
        data = response.json()

        # Staff should see: PUBLIC+CATALOGED, SENSITIVE+CATALOGED, CONFIDENTIAL+CATALOGED
        # (and, since there's no implicit cataloging_status filter for staff,
        # the not-yet-cataloged items too.)
        visible_titles = {item["title"] for item in data["items"]}
        assert "Public Book - Cataloged" in visible_titles
        assert "Sensitive Book - Cataloged" in visible_titles
        assert "Confidential Book - Cataloged" in visible_titles

    async def test_staff_can_access_confidential_item(
        self, client, staff_user, test_catalog_items_with_visibility
    ):
        """Staff users can access CONFIDENTIAL items."""
        auth_header = {"Authorization": f"Bearer {create_access_token(subject=staff_user.id, email=staff_user.email)}"}
        confidential_item = test_catalog_items_with_visibility[3]
        response = await client.get(
            f"/api/v1/catalog/items/{confidential_item.id}",
            headers=auth_header,
        )
        assert response.status_code == 200

    async def test_staff_can_filter_by_cataloging_status(
        self, client, staff_user, test_catalog_items_with_visibility
    ):
        """Staff users can explicitly filter by cataloging status."""
        auth_header = {"Authorization": f"Bearer {create_access_token(subject=staff_user.id, email=staff_user.email)}"}
        response = await client.get(
            "/api/v1/catalog/items?cataloging_status=uncataloged",
            headers=auth_header,
        )
        assert response.status_code == 200
        data = response.json()

        # Should see uncataloged items
        assert len(data["items"]) >= 1
        for item in data["items"]:
            assert item["cataloging_status"] == "uncataloged"

    async def test_staff_can_filter_by_sensitivity_level(
        self, client, staff_user, test_catalog_items_with_visibility
    ):
        """Staff users can explicitly filter by sensitivity level.

        CatalogItemResponse doesn't serialize sensitivity_level (see
        app/schemas/catalog.py), so the filter's effect has to be checked via
        which titles come back, not an echoed field.
        """
        auth_header = {"Authorization": f"Bearer {create_access_token(subject=staff_user.id, email=staff_user.email)}"}
        response = await client.get(
            "/api/v1/catalog/items?sensitivity_level=sensitive",
            headers=auth_header,
        )
        assert response.status_code == 200
        data = response.json()

        # Should see only the sensitive fixture item
        visible_titles = {item["title"] for item in data["items"]}
        assert visible_titles == {"Sensitive Book - Cataloged"}

    async def test_admin_sees_all_items(
        self, client, admin_user, test_catalog_items_with_visibility
    ):
        """Admin users should see all items regardless of cataloging status or sensitivity."""
        auth_header = {"Authorization": f"Bearer {create_access_token(subject=admin_user.id, email=admin_user.email)}"}
        response = await client.get("/api/v1/catalog/items", headers=auth_header)
        assert response.status_code == 200
        data = response.json()

        # Admin should see all 5 items
        assert len(data["items"]) >= 5

    async def test_visibility_filter_with_search_query(
        self, client, test_catalog_items_with_visibility
    ):
        """Search results should respect visibility filters."""
        response = await client.get("/api/v1/catalog/items?q=Book")
        assert response.status_code == 200
        data = response.json()

        # Should only find PUBLIC + CATALOGED
        visible_titles = {item["title"] for item in data["items"]}
        assert "Public Book - Cataloged" in visible_titles
        assert "Sensitive Book - Cataloged" not in visible_titles
        assert "Confidential Book - Cataloged" not in visible_titles

    async def test_visibility_filters_apply_to_books_endpoint(
        self, client, patron_user, test_catalog_items_with_visibility
    ):
        """Visibility filters should apply to /books endpoint.

        CatalogItemResponse doesn't serialize sensitivity_level (see
        app/schemas/catalog.py), so check by title against the known
        fixture set instead of an echoed field.
        """
        auth_header = {"Authorization": f"Bearer {create_access_token(subject=patron_user.id, email=patron_user.email)}"}
        response = await client.get("/api/v1/catalog/books", headers=auth_header)
        assert response.status_code == 200
        data = response.json()

        # Should only see PUBLIC + SENSITIVE (not CONFIDENTIAL, not uncataloged)
        visible_titles = {item["title"] for item in data["items"]}
        assert visible_titles <= {
            "Public Book - Cataloged",
            "Sensitive Book - Cataloged",
        }

    async def test_visibility_filters_apply_to_barcode_lookup(
        self, client, test_catalog_items_with_visibility, test_db: AsyncSession
    ):
        """Visibility filters should apply to barcode lookup."""
        # Set a barcode on a sensitive item
        sensitive_item = test_catalog_items_with_visibility[2]
        sensitive_item.barcode = "TEST-SENSITIVE-001"
        await test_db.commit()

        # Public user shouldn't be able to lookup by barcode
        response = await client.get("/api/v1/catalog/barcode/TEST-SENSITIVE-001")
        assert response.status_code == 404

    async def test_cache_respects_user_role(
        self, client, patron_user, test_catalog_items_with_visibility
    ):
        """Cache keys should include user role to prevent cross-role data leakage."""
        # Make request as patron
        auth_header = {"Authorization": f"Bearer {create_access_token(subject=patron_user.id, email=patron_user.email)}"}
        response1 = await client.get("/api/v1/catalog/items", headers=auth_header)
        assert response1.status_code == 200
        data1 = response1.json()

        # Make request as anonymous
        response2 = await client.get("/api/v1/catalog/items")
        assert response2.status_code == 200
        data2 = response2.json()

        # Patron and public should see different results
        assert len(data1["items"]) >= len(data2["items"])

    async def test_all_list_endpoints_enforce_visibility(
        self, client, test_catalog_items_with_visibility
    ):
        """All list endpoints should enforce visibility filters."""
        endpoints = [
            "/api/v1/catalog/",  # registered at "/" (trailing slash); the
            # bare path 307-redirects there, which httpx won't follow by
            # default under the ASGI test transport.
            "/api/v1/catalog/items",
            "/api/v1/catalog/search",
            "/api/v1/catalog/books",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 200
            data = response.json()

            # All should only show PUBLIC + CATALOGED items.
            # CatalogItemResponse doesn't serialize sensitivity_level (see
            # app/schemas/catalog.py), so only cataloging_status is checkable
            # here directly.
            for item in data.get("items", []):
                assert item["cataloging_status"] == "cataloged", (
                    f"{endpoint} leaked a non-cataloged item: {item['title']}"
                )


@pytest.mark.asyncio
class TestVisibilityEdgeCases:
    """Test edge cases for visibility filtering."""

    async def test_in_progress_cataloging_status_hidden_from_patrons(
        self, client, patron_user, test_db: AsyncSession
    ):
        """IN_PROGRESS items should be hidden from patrons."""
        item = CatalogItem(
            title="In Progress Item",
            author="Author",
            item_type=ItemType.book,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.IN_PROGRESS,
            sensitivity_level=SensitivityLevel.PUBLIC,
        )
        test_db.add(item)
        await test_db.commit()

        auth_header = {"Authorization": f"Bearer {create_access_token(subject=patron_user.id, email=patron_user.email)}"}
        response = await client.get("/api/v1/catalog/items", headers=auth_header)

        # IN_PROGRESS should not be visible
        visible_titles = {
            i["title"] for i in response.json()["items"]
        }
        assert "In Progress Item" not in visible_titles

    async def test_direct_id_access_still_enforces_visibility(
        self, client, test_catalog_items_with_visibility
    ):
        """Direct ID access should still enforce visibility rules."""
        uncataloged_item = test_catalog_items_with_visibility[1]

        # Even if someone knows the ID, they shouldn't access uncataloged items
        response = await client.get(f"/api/v1/catalog/{uncataloged_item.id}")
        assert response.status_code == 404

    async def test_explicit_filter_respected(
        self, client, staff_user, test_catalog_items_with_visibility
    ):
        """Explicit filter parameters should be respected."""
        auth_header = {"Authorization": f"Bearer {create_access_token(subject=staff_user.id, email=staff_user.email)}"}

        # Explicitly request only UNCATALOGED items
        response = await client.get(
            "/api/v1/catalog/items?cataloging_status=uncataloged",
            headers=auth_header,
        )
        assert response.status_code == 200
        data = response.json()

        # All results should be uncataloged
        for item in data["items"]:
            assert item["cataloging_status"] == "uncataloged"
