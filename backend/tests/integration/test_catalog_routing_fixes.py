# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test suite for catalog endpoint routing fixes.

Tests for:
- GET /catalog/search - Dedicated search endpoint
- GET /catalog/books - List only books
- GET /catalog/materials - List materials by type
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.models.catalog import CatalogItem, ItemType, ItemStatus, CatalogingStatus


@pytest.fixture
async def sample_books(test_db):
    """Create sample book items for testing."""
    books = [
        CatalogItem(
            title="Understanding Autism",
            author="Temple Grandin",
            isbn="978-0-547-51924-0",
            item_type=ItemType.book,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            publication_year=2010,
            location="Main Library",
            subjects="autism, psychology, neurodiversity",
        ),
        CatalogItem(
            title="The Curious Incident of the Dog in the Night-Time",
            author="Mark Haddon",
            isbn="978-0-385-72712-0",
            item_type=ItemType.book,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            publication_year=2003,
            location="Young Adult",
            subjects="autism, mystery, fiction",
        ),
        CatalogItem(
            title="Python Programming for Everyone",
            author="John Smith",
            isbn="978-1-234567-89-0",
            item_type=ItemType.book,
            status=ItemStatus.checked_out,
            cataloging_status=CatalogingStatus.CATALOGED,
            publication_year=2020,
            location="Technology",
            subjects="python, programming, computer science",
        ),
    ]

    for book in books:
        test_db.add(book)
    await test_db.commit()

    for book in books:
        await test_db.refresh(book)

    return books


@pytest.fixture
async def sample_materials(test_db):
    """Create sample non-book materials for testing."""
    materials = [
        CatalogItem(
            title="The Matrix",
            director="The Wachowskis",
            item_type=ItemType.dvd,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            publication_year=1999,
            location="Movies",
            runtime_minutes=136,
        ),
        CatalogItem(
            title="Inception",
            director="Christopher Nolan",
            item_type=ItemType.bluray,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            publication_year=2010,
            location="Movies",
            runtime_minutes=148,
        ),
        CatalogItem(
            title="Dark Side of the Moon",
            artist="Pink Floyd",
            item_type=ItemType.cd,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            publication_year=1973,
            location="Music",
        ),
        CatalogItem(
            title="Abbey Road",
            artist="The Beatles",
            item_type=ItemType.vinyl,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            publication_year=1969,
            location="Music",
        ),
        CatalogItem(
            title="Harry Potter and the Sorcerer's Stone (Audiobook)",
            author="J.K. Rowling",
            item_type=ItemType.audiobook,
            status=ItemStatus.available,
            cataloging_status=CatalogingStatus.CATALOGED,
            publication_year=1998,
            location="Audiobooks",
        ),
    ]

    for material in materials:
        test_db.add(material)
    await test_db.commit()

    for material in materials:
        await test_db.refresh(material)

    return materials


class TestCatalogSearchEndpoint:
    """Tests for GET /catalog/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_endpoint_exists(self, client, sample_books, sample_materials):
        """Test that /catalog/search endpoint responds without 422 error."""
        response = await client.get("/api/v1/catalog/search")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

    @pytest.mark.asyncio
    async def test_search_with_query(self, client, sample_books):
        """Test search with query parameter."""
        response = await client.get("/api/v1/catalog/search?q=autism")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1, "Should find at least one item with 'autism' in title or subjects"
        assert len(data["items"]) > 0

    @pytest.mark.asyncio
    async def test_search_with_item_type_filter(self, client, sample_books, sample_materials):
        """Test search with item_type filter."""
        response = await client.get("/api/v1/catalog/search?item_type=book")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3, "Should find at least 3 books"
        # Verify all items are books
        for item in data["items"]:
            assert item["item_type"] == "book"

    @pytest.mark.asyncio
    async def test_search_with_status_filter(self, client, sample_books):
        """Test search with status filter."""
        response = await client.get("/api/v1/catalog/search?status=available")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2, "Should find at least 2 available items"
        for item in data["items"]:
            assert item["status"] == "available"

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, client, sample_books):
        """Test search with pagination parameters."""
        response = await client.get("/api/v1/catalog/search?page=1&per_page=2")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 2
        assert len(data["items"]) <= 2

    @pytest.mark.asyncio
    async def test_search_with_year_range(self, client, sample_books):
        """Test search with publication year range."""
        response = await client.get("/api/v1/catalog/search?year_min=2000&year_max=2015")
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            if item["publication_year"]:
                assert 2000 <= item["publication_year"] <= 2015


class TestCatalogBooksEndpoint:
    """Tests for GET /catalog/books endpoint."""

    @pytest.mark.asyncio
    async def test_books_endpoint_exists(self, client, sample_books):
        """Test that /catalog/books endpoint responds without 422 error."""
        response = await client.get("/api/v1/catalog/books")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_books_endpoint_returns_only_books(self, client, sample_books, sample_materials):
        """Test that /catalog/books returns only book items."""
        response = await client.get("/api/v1/catalog/books")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3, "Should return exactly 3 books"
        for item in data["items"]:
            assert item["item_type"] == "book", "All items should be books"

    @pytest.mark.asyncio
    async def test_books_with_pagination(self, client, sample_books):
        """Test /catalog/books with pagination."""
        response = await client.get("/api/v1/catalog/books?page=1&per_page=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert len(data["items"]) <= 10

    @pytest.mark.asyncio
    async def test_books_with_search_query(self, client, sample_books):
        """Test /catalog/books with search query."""
        response = await client.get("/api/v1/catalog/books?q=autism")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        # All items should be books and contain 'autism'
        for item in data["items"]:
            assert item["item_type"] == "book"

    @pytest.mark.asyncio
    async def test_books_with_status_filter(self, client, sample_books):
        """Test /catalog/books with status filter."""
        response = await client.get("/api/v1/catalog/books?status=available")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        for item in data["items"]:
            assert item["item_type"] == "book"
            assert item["status"] == "available"


class TestCatalogMaterialsEndpoint:
    """Tests for GET /catalog/materials endpoint."""

    @pytest.mark.asyncio
    async def test_materials_endpoint_exists(self, client, sample_materials):
        """Test that /catalog/materials endpoint responds without 422 error."""
        response = await client.get("/api/v1/catalog/materials")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_materials_endpoint_excludes_books(self, client, sample_books, sample_materials):
        """Test that /catalog/materials doesn't return books."""
        response = await client.get("/api/v1/catalog/materials")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5, "Should return exactly 5 materials (non-books)"
        for item in data["items"]:
            assert item["item_type"] != "book", "Materials should not include books"

    @pytest.mark.asyncio
    async def test_materials_with_type_dvd(self, client, sample_materials):
        """Test /catalog/materials filtered by DVD type."""
        response = await client.get("/api/v1/catalog/materials?type=dvd")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1, "Should find at least one DVD"
        for item in data["items"]:
            assert item["item_type"] == "dvd"

    @pytest.mark.asyncio
    async def test_materials_with_type_bluray(self, client, sample_materials):
        """Test /catalog/materials filtered by Blu-ray type."""
        response = await client.get("/api/v1/catalog/materials?type=bluray")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1, "Should find at least one Blu-ray"
        for item in data["items"]:
            assert item["item_type"] == "bluray"

    @pytest.mark.asyncio
    async def test_materials_with_type_cd(self, client, sample_materials):
        """Test /catalog/materials filtered by CD type."""
        response = await client.get("/api/v1/catalog/materials?type=cd")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1, "Should find at least one CD"
        for item in data["items"]:
            assert item["item_type"] == "cd"

    @pytest.mark.asyncio
    async def test_materials_with_type_vinyl(self, client, sample_materials):
        """Test /catalog/materials filtered by vinyl type."""
        response = await client.get("/api/v1/catalog/materials?type=vinyl")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1, "Should find at least one vinyl record"
        for item in data["items"]:
            assert item["item_type"] == "vinyl"

    @pytest.mark.asyncio
    async def test_materials_with_invalid_type(self, client):
        """Test /catalog/materials with invalid type parameter."""
        response = await client.get("/api/v1/catalog/materials?type=invalid_type")
        assert response.status_code == 400, "Should return 400 for invalid material type"

    @pytest.mark.asyncio
    async def test_materials_with_pagination(self, client, sample_materials):
        """Test /catalog/materials with pagination."""
        response = await client.get("/api/v1/catalog/materials?page=1&per_page=2")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 2
        assert len(data["items"]) <= 2

    @pytest.mark.asyncio
    async def test_materials_with_search_query(self, client, sample_materials):
        """Test /catalog/materials with search query."""
        response = await client.get("/api/v1/catalog/materials?q=matrix")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1, "Should find 'The Matrix'"
        for item in data["items"]:
            assert item["item_type"] != "book"


class TestEndpointIntegration:
    """Integration tests comparing different endpoints."""

    @pytest.mark.asyncio
    async def test_search_endpoint_returns_all_types(self, client, sample_books, sample_materials):
        """Test that /catalog/search returns all item types."""
        response = await client.get("/api/v1/catalog/search")
        assert response.status_code == 200
        data = response.json()
        # Should have 3 books + 5 materials = 8 items
        assert data["total"] == 8

    @pytest.mark.asyncio
    async def test_books_and_materials_are_mutually_exclusive(self, client, sample_books, sample_materials):
        """Test that books and materials endpoints return different sets."""
        books_response = await client.get("/api/v1/catalog/books")
        materials_response = await client.get("/api/v1/catalog/materials")

        assert books_response.status_code == 200
        assert materials_response.status_code == 200

        books_data = books_response.json()
        materials_data = materials_response.json()

        # Combined count should equal total items
        assert books_data["total"] + materials_data["total"] == 8

    @pytest.mark.asyncio
    async def test_items_endpoint_is_general(self, client, sample_books, sample_materials):
        """Test that /catalog/items works as a general endpoint."""
        response = await client.get("/api/v1/catalog/items")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 8, "Should return all items"

    @pytest.mark.asyncio
    async def test_search_and_items_return_same_data(self, client, sample_books):
        """Test that /catalog/search and /catalog/items return consistent data."""
        search_response = await client.get("/api/v1/catalog/search?q=python")
        items_response = await client.get("/api/v1/catalog/items?q=python")

        assert search_response.status_code == 200
        assert items_response.status_code == 200

        search_data = search_response.json()
        items_data = items_response.json()

        assert search_data["total"] == items_data["total"]


class TestRoutingValidation:
    """Tests to ensure 422 validation errors don't occur."""

    @pytest.mark.asyncio
    async def test_no_422_on_search_endpoint(self, client, sample_books):
        """Verify /catalog/search doesn't return 422 errors."""
        response = await client.get("/api/v1/catalog/search")
        assert response.status_code != 422, "GET /catalog/search returned 422 validation error"

    @pytest.mark.asyncio
    async def test_no_422_on_books_endpoint(self, client, sample_books):
        """Verify /catalog/books doesn't return 422 errors."""
        response = await client.get("/api/v1/catalog/books")
        assert response.status_code != 422, "GET /catalog/books returned 422 validation error"

    @pytest.mark.asyncio
    async def test_no_422_on_materials_endpoint(self, client, sample_materials):
        """Verify /catalog/materials doesn't return 422 errors."""
        response = await client.get("/api/v1/catalog/materials")
        assert response.status_code != 422, "GET /catalog/materials returned 422 validation error"

    @pytest.mark.asyncio
    async def test_no_422_on_items_endpoint(self, client, sample_books):
        """Verify /catalog/items doesn't return 422 errors."""
        response = await client.get("/api/v1/catalog/items")
        assert response.status_code != 422, "GET /catalog/items returned 422 validation error"
