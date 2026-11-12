# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
TDD Tests for Catalog Advanced Search

Tests the advanced search functionality for catalog items with multiple fields,
boolean operators, and filters.
These tests follow TDD principles - write tests first, implement search second.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemType, ItemStatus


class TestBasicAdvancedSearch:
    """Test basic advanced search functionality"""

    @pytest.mark.asyncio
    async def test_searches_by_title_only(self, test_db: AsyncSession):
        """Test searching by title field only"""
        # Create test items
        item1 = CatalogItem(
            title="Advanced Python Programming",
            author="John Doe",
            status=ItemStatus.available,
        )
        item2 = CatalogItem(
            title="Introduction to Java",
            author="Jane Smith",
            status=ItemStatus.available,
        )
        test_db.add_all([item1, item2])
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()
        results = await service.advanced_search(
            test_db,
            title="Python"
        )

        assert len(results) == 1
        assert results[0].title == "Advanced Python Programming"

    @pytest.mark.asyncio
    async def test_searches_by_author_only(self, test_db: AsyncSession):
        """Test searching by author field only"""
        # Create test items
        item1 = CatalogItem(
            title="Book One",
            author="Smith, John",
            status=ItemStatus.available,
        )
        item2 = CatalogItem(
            title="Book Two",
            author="Doe, Jane",
            status=ItemStatus.available,
        )
        test_db.add_all([item1, item2])
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()
        results = await service.advanced_search(
            test_db,
            author="Smith"
        )

        assert len(results) == 1
        assert results[0].author == "Smith, John"

    @pytest.mark.asyncio
    async def test_searches_by_subject_only(self, test_db: AsyncSession):
        """Test searching by subject field only"""
        # Create test items
        item1 = CatalogItem(
            title="Sci-Fi Book",
            subjects="Science Fiction; Space Opera; Adventure",
            status=ItemStatus.available,
        )
        item2 = CatalogItem(
            title="Mystery Book",
            subjects="Mystery; Detective; Crime",
            status=ItemStatus.available,
        )
        test_db.add_all([item1, item2])
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()
        results = await service.advanced_search(
            test_db,
            subject="Science Fiction"
        )

        assert len(results) == 1
        assert "Science Fiction" in results[0].subjects

    @pytest.mark.asyncio
    async def test_searches_by_isbn_only(self, test_db: AsyncSession):
        """Test searching by ISBN field only"""
        # Create test items
        item1 = CatalogItem(
            title="Book One",
            isbn="978-0-123456-78-9",
            status=ItemStatus.available,
        )
        item2 = CatalogItem(
            title="Book Two",
            isbn="978-1-234567-89-0",
            status=ItemStatus.available,
        )
        test_db.add_all([item1, item2])
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()
        # Search with or without hyphens
        results = await service.advanced_search(
            test_db,
            isbn="9780123456789"
        )

        assert len(results) == 1
        assert results[0].isbn == "978-0-123456-78-9"


class TestBooleanOperators:
    """Test boolean operators in advanced search"""

    @pytest.mark.asyncio
    async def test_combines_multiple_fields_with_and(self, test_db: AsyncSession):
        """Test combining multiple fields with AND operator"""
        # Create test items
        item1 = CatalogItem(
            title="Python Programming",
            author="Smith, John",
            subjects="Programming; Python; Software",
            status=ItemStatus.available,
        )
        item2 = CatalogItem(
            title="Java Programming",
            author="Smith, John",
            subjects="Programming; Java; Software",
            status=ItemStatus.available,
        )
        item3 = CatalogItem(
            title="Python Cookbook",
            author="Doe, Jane",
            subjects="Programming; Python; Recipes",
            status=ItemStatus.available,
        )
        test_db.add_all([item1, item2, item3])
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()
        results = await service.advanced_search(
            test_db,
            title="Python",
            author="Smith",
            operator="AND"
        )

        # Should only return item1 (Python + Smith)
        assert len(results) == 1
        assert results[0].title == "Python Programming"

    @pytest.mark.asyncio
    async def test_combines_multiple_fields_with_or(self, test_db: AsyncSession):
        """Test combining multiple fields with OR operator"""
        # Create test items
        item1 = CatalogItem(
            title="Python Programming",
            author="Smith, John",
            status=ItemStatus.available,
        )
        item2 = CatalogItem(
            title="Java Programming",
            author="Doe, Jane",
            status=ItemStatus.available,
        )
        item3 = CatalogItem(
            title="Cookbook",
            author="Smith, John",
            status=ItemStatus.available,
        )
        test_db.add_all([item1, item2, item3])
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()
        results = await service.advanced_search(
            test_db,
            title="Python",
            author="Doe",
            operator="OR"
        )

        # Should return item1 (Python) and item2 (Doe)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_excludes_terms_with_not(self, test_db: AsyncSession):
        """Test excluding terms with NOT operator"""
        # Create test items
        item1 = CatalogItem(
            title="Introduction to Python",
            subjects="Programming; Python; Beginner",
            status=ItemStatus.available,
        )
        item2 = CatalogItem(
            title="Advanced Python",
            subjects="Programming; Python; Advanced",
            status=ItemStatus.available,
        )
        item3 = CatalogItem(
            title="Python Basics",
            subjects="Programming; Python; Beginner",
            status=ItemStatus.available,
        )
        test_db.add_all([item1, item2, item3])
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()
        results = await service.advanced_search(
            test_db,
            title="Python",
            exclude_subject="Beginner"
        )

        # Should only return item2 (no "Beginner" in subjects)
        assert len(results) == 1
        assert results[0].title == "Advanced Python"


class TestSearchFilters:
    """Test search filters"""

    @pytest.mark.asyncio
    async def test_filters_by_item_type(self, test_db: AsyncSession):
        """Test filtering by item type"""
        # Create test items of different types
        item1 = CatalogItem(
            title="Programming Book",
            item_type=ItemType.book,
            status=ItemStatus.available,
        )
        item2 = CatalogItem(
            title="Programming Audiobook",
            item_type=ItemType.audiobook,
            status=ItemStatus.available,
        )
        item3 = CatalogItem(
            title="Programming DVD",
            item_type=ItemType.dvd,
            status=ItemStatus.available,
        )
        test_db.add_all([item1, item2, item3])
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()
        results = await service.advanced_search(
            test_db,
            title="Programming",
            item_type=ItemType.book
        )

        assert len(results) == 1
        assert results[0].item_type == ItemType.book

    @pytest.mark.asyncio
    async def test_filters_by_publication_year_range(self, test_db: AsyncSession):
        """Test filtering by publication year range"""
        # Create test items with different publication years
        item1 = CatalogItem(
            title="Old Book",
            publication_year=2010,
            status=ItemStatus.available,
        )
        item2 = CatalogItem(
            title="Recent Book",
            publication_year=2020,
            status=ItemStatus.available,
        )
        item3 = CatalogItem(
            title="New Book",
            publication_year=2024,
            status=ItemStatus.available,
        )
        test_db.add_all([item1, item2, item3])
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()
        results = await service.advanced_search(
            test_db,
            year_min=2015,
            year_max=2025
        )

        # Should return item2 and item3
        assert len(results) == 2
        assert all(2015 <= item.publication_year <= 2025 for item in results)

    @pytest.mark.asyncio
    async def test_filters_by_location(self, test_db: AsyncSession):
        """Test filtering by location"""
        # Create test items at different locations
        item1 = CatalogItem(
            title="Main Library Book",
            location="Main Library",
            status=ItemStatus.available,
        )
        item2 = CatalogItem(
            title="Branch Library Book",
            location="East Branch",
            status=ItemStatus.available,
        )
        test_db.add_all([item1, item2])
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()
        results = await service.advanced_search(
            test_db,
            location="Main Library"
        )

        assert len(results) == 1
        assert results[0].location == "Main Library"


class TestAdvancedSearchAPI:
    """Test advanced search API endpoints"""

    @pytest.mark.asyncio
    async def test_advanced_search_endpoint(self, test_db: AsyncSession, client):
        """Test POST /catalog/search/advanced endpoint"""
        # Create test items
        item1 = CatalogItem(
            title="Advanced Python Programming",
            author="Smith, John",
            subjects="Programming; Python; Advanced",
            item_type=ItemType.book,
            publication_year=2023,
            status=ItemStatus.available,
        )
        item2 = CatalogItem(
            title="Introduction to Java",
            author="Doe, Jane",
            subjects="Programming; Java; Beginner",
            item_type=ItemType.book,
            publication_year=2022,
            status=ItemStatus.available,
        )
        test_db.add_all([item1, item2])
        await test_db.commit()

        # Advanced search -- use the shared `client` fixture, which overrides
        # get_db to reuse this test's own engine/session; a manually built
        # AsyncClient(transport=ASGITransport(app=app)) instead falls through
        # to the app's real get_db and can bind to a stale event loop from an
        # earlier test ("RuntimeError: Event loop is closed").
        response = await client.post(
            "/api/v1/catalog/search/advanced",
            json={
                "title": "Python",
                "subject": "Programming",
                "operator": "AND"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["title"] == "Advanced Python Programming"

    @pytest.mark.asyncio
    async def test_advanced_search_returns_paginated_results(self, test_db: AsyncSession):
        """Test that advanced search returns paginated results"""
        from app.main import app

        # Create many test items
        for i in range(25):
            item = CatalogItem(
                title=f"Programming Book {i}",
                subjects="Programming; Software",
                status=ItemStatus.available,
            )
            test_db.add(item)
        await test_db.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Advanced search with pagination
            response = await client.post(
                "/api/v1/catalog/search/advanced",
                json={
                    "subject": "Programming",
                    "page": 1,
                    "per_page": 10
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 10
            assert data["total"] == 25
            assert data["page"] == 1
            assert data["pages"] == 3


class TestSearchSecurity:
    """Test search security against SQL injection"""

    @pytest.mark.asyncio
    async def test_handles_sql_injection_attempts_safely_in_title(self, test_db: AsyncSession):
        """Test that SQL injection attempts in title field are handled safely"""
        # Create test item
        item = CatalogItem(
            title="Legitimate Book",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()

        # Attempt SQL injection
        try:
            results = await service.advanced_search(
                test_db,
                title="' OR '1'='1"
            )
            # Should not return all records
            # Should treat as literal string search
            assert len(results) == 0 or all("OR" not in r.title for r in results)
        except Exception as e:
            # Should not raise SQL errors
            assert "sql" not in str(e).lower()

    @pytest.mark.asyncio
    async def test_handles_sql_injection_attempts_safely_in_author(self, test_db: AsyncSession):
        """Test that SQL injection attempts in author field are handled safely"""
        # Create test item
        item = CatalogItem(
            title="Book",
            author="Real Author",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()

        # Attempt SQL injection
        try:
            results = await service.advanced_search(
                test_db,
                author="'; DROP TABLE catalog_items; --"
            )
            # Should not cause SQL error
            assert isinstance(results, list)
        except Exception as e:
            # Should not be a SQL error
            assert "syntax" not in str(e).lower()

    @pytest.mark.asyncio
    async def test_sanitizes_special_characters_in_search(self, test_db: AsyncSession):
        """Test that special characters in search are properly escaped"""
        # Create test items
        item1 = CatalogItem(
            title="C++ Programming",
            status=ItemStatus.available,
        )
        item2 = CatalogItem(
            title="C# Programming",
            status=ItemStatus.available,
        )
        test_db.add_all([item1, item2])
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()

        # Search for C++ (should work correctly)
        results = await service.advanced_search(
            test_db,
            title="C++"
        )

        assert len(results) == 1
        assert results[0].title == "C++ Programming"

    @pytest.mark.asyncio
    async def test_handles_wildcard_characters_safely(self, test_db: AsyncSession):
        """Test that wildcard characters are handled safely"""
        # Create test items
        item1 = CatalogItem(
            title="Python Programming",
            status=ItemStatus.available,
        )
        item2 = CatalogItem(
            title="Java Programming",
            status=ItemStatus.available,
        )
        test_db.add_all([item1, item2])
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()

        # Search with wildcards (should be treated as literals or properly handled)
        results = await service.advanced_search(
            test_db,
            title="%"
        )

        # Should not return all records
        assert len(results) == 0


class TestSearchCaseInsensitivity:
    """Test case-insensitive search"""

    @pytest.mark.asyncio
    async def test_search_is_case_insensitive(self, test_db: AsyncSession):
        """Test that search is case-insensitive"""
        # Create test item
        item = CatalogItem(
            title="Advanced Python Programming",
            author="Smith, John",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()

        # Search with different cases
        results_lower = await service.advanced_search(test_db, title="python")
        results_upper = await service.advanced_search(test_db, title="PYTHON")
        results_mixed = await service.advanced_search(test_db, title="PyThOn")

        # All should return the same result
        assert len(results_lower) == 1
        assert len(results_upper) == 1
        assert len(results_mixed) == 1


class TestSearchEdgeCases:
    """Test search edge cases"""

    @pytest.mark.asyncio
    async def test_empty_search_returns_all_results(self, test_db: AsyncSession):
        """Test that empty search returns all results (paginated)"""
        # Create test items
        for i in range(5):
            item = CatalogItem(
                title=f"Book {i}",
                status=ItemStatus.available,
            )
            test_db.add(item)
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()

        # Empty search
        results = await service.advanced_search(test_db)

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_with_no_results(self, test_db: AsyncSession):
        """Test search that returns no results"""
        # Create test item
        item = CatalogItem(
            title="Python Book",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()

        from app.services.catalog_search_service import CatalogSearchService

        service = CatalogSearchService()

        # Search for non-existent term
        results = await service.advanced_search(
            test_db,
            title="Nonexistent"
        )

        assert len(results) == 0


class TestAdvancedSearchEagerLoadsImages:
    """Regression: CatalogItemResponse serializes .images. If the advanced-search
    queries omit selectinload(CatalogItem.images), async ORM access during
    Pydantic serialization 500s with MissingGreenlet. This has bitten the team
    three times -- these tests fail fast if the selectinload is removed.
    """

    @pytest.mark.asyncio
    async def test_post_advanced_search_with_image_does_not_500(
        self, test_db: AsyncSession, client
    ):
        """POST /api/v1/catalog/advanced-search must serialize items with
        attached catalog_images rows without raising MissingGreenlet."""
        from app.models.catalog import CatalogImage

        item = CatalogItem(
            title="Greenlet Regression Title",
            author="Test Author",
            subjects="Regression",
            item_type=ItemType.book,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.flush()
        test_db.add(
            CatalogImage(
                catalog_item_id=item.id,
                image_url="https://example.invalid/cover.jpg",
                image_key="test/cover.jpg",
                is_primary=True,
                display_order=0,
            )
        )
        await test_db.commit()

        response = await client.post(
            "/api/v1/catalog/advanced-search",
            json={
                "queries": [
                    {"field": "title", "value": "Greenlet Regression", "operator": "AND"}
                ]
            },
        )

        # The whole point: must NOT 500 with MissingGreenlet.
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["total"] >= 1
        titles = [row["title"] for row in data["items"]]
        assert "Greenlet Regression Title" in titles
        # And the images must round-trip through serialization.
        match = next(row for row in data["items"] if row["title"] == "Greenlet Regression Title")
        assert isinstance(match["images"], list)
        assert len(match["images"]) == 1
        assert match["images"][0]["image_url"] == "https://example.invalid/cover.jpg"

    @pytest.mark.asyncio
    async def test_post_search_advanced_with_image_does_not_500(
        self, test_db: AsyncSession, client
    ):
        """POST /api/v1/catalog/search/advanced (simple form, powered by
        advanced_search_with_count) must also eager-load images."""
        from app.models.catalog import CatalogImage

        item = CatalogItem(
            title="Greenlet Simple Title",
            author="Test Author",
            subjects="Regression",
            item_type=ItemType.book,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.flush()
        test_db.add(
            CatalogImage(
                catalog_item_id=item.id,
                image_url="https://example.invalid/simple.jpg",
                image_key="test/simple.jpg",
                is_primary=True,
                display_order=0,
            )
        )
        await test_db.commit()

        response = await client.post(
            "/api/v1/catalog/search/advanced",
            json={"title": "Greenlet Simple"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["total"] >= 1
        match = next(
            row for row in data["results"] if row["title"] == "Greenlet Simple Title"
        )
        assert isinstance(match["images"], list)
        assert len(match["images"]) == 1
        assert match["images"][0]["image_url"] == "https://example.invalid/simple.jpg"
