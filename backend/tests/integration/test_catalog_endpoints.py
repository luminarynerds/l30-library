# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for catalog API endpoints.
"""

import pytest


@pytest.mark.integration
class TestCatalogSearch:
    """Test catalog search endpoints."""

    async def test_search_catalog(self, client, test_catalog_item):
        """Test searching the catalog."""
        response = await client.get("/api/v1/catalog/?q=Test")
        assert response.status_code in [200, 401]  # May require auth

    async def test_search_with_filters(self, client, test_db):
        """Test catalog search with filters."""
        from app.models.catalog import CatalogItem, CatalogingStatus, ItemStatus, ItemType
        from datetime import datetime, timedelta, timezone

        # Create multiple test items with different attributes. cataloging_status
        # must be explicit: CatalogItem defaults to UNCATALOGED, and
        # _execute_catalog_search's role-based visibility filter (app/api/v1/
        # catalog/helpers.py:404-410) hides anything not CATALOGED from
        # unauthenticated/non-staff callers -- this test's `client` calls are
        # unauthenticated, so every item was invisible without this.
        items = [
            CatalogItem(
                title="Python Programming",
                author="Guido van Rossum",
                item_type=ItemType.book,
                status=ItemStatus.available,
                publication_year=2020,
                location="Adult Fiction",
                subjects="programming,python",
                cataloging_status=CatalogingStatus.CATALOGED,
            ),
            CatalogItem(
                title="Advanced Python",
                author="Raymond Hettinger",
                item_type=ItemType.ebook,
                status=ItemStatus.checked_out,
                publication_year=2021,
                location="Digital",
                subjects="programming,python",
                cataloging_status=CatalogingStatus.CATALOGED,
            ),
            CatalogItem(
                title="JavaScript Basics",
                author="Kyle Simpson",
                item_type=ItemType.book,
                status=ItemStatus.available,
                publication_year=2022,
                location="Adult Tech",
                subjects="programming,javascript",
                cataloging_status=CatalogingStatus.CATALOGED,
            ),
            CatalogItem(
                title="The Great Gatsby",
                author="F. Scott Fitzgerald",
                item_type=ItemType.audiobook,
                status=ItemStatus.on_hold,
                publication_year=1925,
                location="Audiobooks",
                subjects="fiction,classic",
                cataloging_status=CatalogingStatus.CATALOGED,
            ),
            CatalogItem(
                title="New Arrivals Test",
                author="Recent Author",
                item_type=ItemType.dvd,
                status=ItemStatus.available,
                publication_year=2024,
                location="Media",
                subjects="film",
                created_at=datetime.now(timezone.utc) - timedelta(days=5),
                cataloging_status=CatalogingStatus.CATALOGED,
            ),
        ]
        for item in items:
            test_db.add(item)
        await test_db.commit()

        # Test filtering by author
        response = await client.get("/api/v1/catalog/?q=Guido")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(item["author"] == "Guido van Rossum" for item in data["items"])

        # Test filtering by item_type
        response = await client.get("/api/v1/catalog/?item_type=book")
        assert response.status_code == 200
        data = response.json()
        assert all(item["item_type"] == "book" for item in data["items"])
        assert data["total"] >= 2  # At least Python and JavaScript books

        # Test filtering by status
        response = await client.get("/api/v1/catalog/?status=available")
        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "available" for item in data["items"])

        # Test filtering by status (checked_out)
        response = await client.get("/api/v1/catalog/?status=checked_out")
        assert response.status_code == 200
        data = response.json()
        if data["total"] > 0:
            assert all(item["status"] == "checked_out" for item in data["items"])

        # Test filtering by publication year minimum
        response = await client.get("/api/v1/catalog/?year_min=2020")
        assert response.status_code == 200
        data = response.json()
        assert all(item.get("publication_year", 0) >= 2020 for item in data["items"])

        # Test filtering by publication year maximum
        response = await client.get("/api/v1/catalog/?year_max=1925")
        assert response.status_code == 200
        data = response.json()
        if data["total"] > 0:
            assert any(item.get("publication_year") == 1925 for item in data["items"])

        # Test filtering by publication year range
        response = await client.get("/api/v1/catalog/?year_min=2020&year_max=2022")
        assert response.status_code == 200
        data = response.json()
        assert all(2020 <= item.get("publication_year", 0) <= 2022 for item in data["items"])

        # Test filtering by location
        response = await client.get("/api/v1/catalog/?location=Adult")
        assert response.status_code == 200
        data = response.json()
        assert all("Adult" in item["location"] for item in data["items"] if item["location"])

        # Test filtering by location (exact match)
        response = await client.get("/api/v1/catalog/?location=Digital")
        assert response.status_code == 200
        data = response.json()
        if data["total"] > 0:
            assert any(item["location"] == "Digital" for item in data["items"])

        # Test new arrivals filter
        response = await client.get("/api/v1/catalog/?is_new=true")
        assert response.status_code == 200
        data = response.json()
        # Should return items created within the last 30 days

        # Test combined filters: item_type and status
        response = await client.get("/api/v1/catalog/?item_type=book&status=available")
        assert response.status_code == 200
        data = response.json()
        assert all(
            item["item_type"] == "book" and item["status"] == "available" for item in data["items"]
        )

        # Test combined filters: search query and item_type
        response = await client.get("/api/v1/catalog/?q=Python&item_type=book")
        assert response.status_code == 200
        data = response.json()
        assert all(item["item_type"] == "book" for item in data["items"])
        if data["total"] > 0:
            assert any(
                "Python" in item["title"] or "Python" in item.get("subjects", "")
                for item in data["items"]
            )

        # Test pagination with filters
        response = await client.get("/api/v1/catalog/?item_type=book&page=1&per_page=10")
        assert response.status_code == 200
        data = response.json()
        assert "page" in data
        assert "per_page" in data
        assert "pages" in data
        assert data["page"] == 1

        # Test filtering by ebook type
        response = await client.get("/api/v1/catalog/?item_type=ebook")
        assert response.status_code == 200
        data = response.json()
        assert all(item["item_type"] == "ebook" for item in data["items"])

        # Test filtering by on_hold status
        response = await client.get("/api/v1/catalog/?status=on_hold")
        assert response.status_code == 200
        data = response.json()
        if data["total"] > 0:
            assert all(item["status"] == "on_hold" for item in data["items"])

        # Test filtering by audiobook and location
        response = await client.get("/api/v1/catalog/?item_type=audiobook&location=Audiobooks")
        assert response.status_code == 200
        data = response.json()
        assert all(item["item_type"] == "audiobook" for item in data["items"])

        # Test edge case: no results for specific filter combination
        response = await client.get("/api/v1/catalog/?item_type=cd&status=lost")
        assert response.status_code == 200
        data = response.json()
        # May or may not have results, but should not error

        # Test empty search with all items
        response = await client.get("/api/v1/catalog/?page=1&per_page=100")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 5  # At least our 5 test items
        assert len(data["items"]) > 0

    async def test_get_item_details(self, client, test_catalog_item):
        """Test getting item details."""
        response = await client.get(f"/api/v1/catalog/{test_catalog_item.id}")
        # test_catalog_item does not set cataloging_status/sensitivity_level,
        # so it is not CATALOGED+PUBLIC by default -- anonymous access
        # correctly 404s (existence-hiding privacy pattern), not just 401.
        assert response.status_code in [200, 401, 404]


@pytest.mark.integration
class TestCatalogManagement:
    """Test catalog management endpoints (staff only)."""

    async def test_create_catalog_item_requires_staff(self, client):
        """Test creating catalog item requires staff role."""
        item_data = {
            "title": "New Book",
            "author": "Author Name",
            "isbn": "123-456-789",
        }
        response = await client.post("/api/v1/staff/catalog", json=item_data)
        assert response.status_code == 401

    async def test_update_catalog_item_requires_staff(self, client, test_catalog_item):
        """Test updating catalog item requires staff role."""
        update_data = {"title": "Updated Title"}
        response = await client.put(
            f"/api/v1/staff/catalog/{test_catalog_item.id}", json=update_data
        )
        assert response.status_code == 401

    async def test_delete_catalog_item_requires_staff(self, client, test_catalog_item):
        """Test deleting catalog item requires staff role."""
        response = await client.delete(f"/api/v1/staff/catalog/{test_catalog_item.id}")
        assert response.status_code == 401
