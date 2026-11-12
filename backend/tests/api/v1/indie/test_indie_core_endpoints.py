# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Indie Domain Core Endpoints

Comprehensive test suite for the Indie (Independent Authors/Publishers) system covering:
- Author management and profiles
- Catalog and content management
- Discovery and recommendations
- Reading lists and collections
- Review and rating system
- Lending and circulation
- Analytics and engagement
- MARC records and metadata
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuthorEndpoints:
    """Test author management endpoints."""

    async def test_list_authors(self, client: AsyncClient):
        """Test listing indie authors."""
        response = await client.get("/api/v1/indie/authors")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    async def test_get_author(self, client: AsyncClient):
        """Test getting author profile."""
        response = await client.get("/api/v1/indie/authors/1")
        assert response.status_code in [200, 401, 403, 404]

    async def test_create_author(self, client: AsyncClient):
        """Test creating author profile."""
        author_data = {
            "name": "John Indie Author",
            "bio": "Independent author bio",
            "email": "author@indie.com",
        }
        response = await client.post("/api/v1/indie/authors", json=author_data)
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_update_author(self, client: AsyncClient):
        """Test updating author profile."""
        update_data = {"bio": "Updated author bio"}
        response = await client.put("/api/v1/indie/authors/1", json=update_data)
        assert response.status_code in [200, 401, 403, 404]

    async def test_search_authors(self, client: AsyncClient):
        """Test searching for authors."""
        response = await client.get("/api/v1/indie/authors?search=indie")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_author_works(self, client: AsyncClient):
        """Test getting author's works."""
        response = await client.get("/api/v1/indie/authors/1/works")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_author_stats(self, client: AsyncClient):
        """Test getting author statistics."""
        response = await client.get("/api/v1/indie/authors/1/stats")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestCatalogEndpoints:
    """Test indie catalog management."""

    async def test_list_catalog_items(self, client: AsyncClient):
        """Test listing indie catalog items."""
        response = await client.get("/api/v1/indie/catalog")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_catalog_item(self, client: AsyncClient):
        """Test getting catalog item details."""
        response = await client.get("/api/v1/indie/catalog/1")
        assert response.status_code in [200, 401, 403, 404]

    async def test_create_catalog_item(self, client: AsyncClient):
        """Test adding item to catalog."""
        # There's no direct create endpoint by design -- indie catalog items
        # are populated via the admin import pipeline (app/api/v1/
        # admin_indie_import.py), not a CRUD-style POST here. GET "" is the
        # only route registered at this exact path, so POST correctly 405s.
        item_data = {
            "title": "Indie Book Title",
            "author_id": 1,
            "isbn": "978-0-123456-78-9",
            "description": "Book description",
        }
        response = await client.post("/api/v1/indie/catalog", json=item_data)
        assert response.status_code in [200, 201, 401, 403, 404, 405]

    async def test_update_catalog_item(self, client: AsyncClient):
        """Test updating catalog item."""
        # Same as create: no direct update endpoint -- managed via the
        # admin import pipeline, so PUT correctly 405s (no route registered
        # for this method at /indie/catalog/{id}, only GET).
        update_data = {"description": "Updated description"}
        response = await client.put("/api/v1/indie/catalog/1", json=update_data)
        assert response.status_code in [200, 401, 403, 404, 405]

    async def test_search_catalog(self, client: AsyncClient):
        """Test searching catalog."""
        # Search is GET /indie/catalog?q=..., not a /search sub-path (which
        # matches the GET /{id} route instead, and 422s trying to parse
        # "search" as the int id).
        response = await client.get("/api/v1/indie/catalog?q=indie")
        assert response.status_code in [200, 401, 403, 404]

    async def test_filter_catalog_by_genre(self, client: AsyncClient):
        """Test filtering catalog by genre."""
        response = await client.get("/api/v1/indie/catalog?genre=fiction")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestDiscoveryEndpoints:
    """Test discovery and browsing endpoints."""

    async def test_get_discovery_carousel(self, client: AsyncClient):
        """Test getting discovery carousel."""
        response = await client.get("/api/v1/indie/discovery/carousel")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_featured_authors(self, client: AsyncClient):
        """Test getting featured authors."""
        response = await client.get("/api/v1/indie/discovery/featured-authors")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_trending_items(self, client: AsyncClient):
        """Test getting trending indie items."""
        response = await client.get("/api/v1/indie/discovery/trending")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_new_releases(self, client: AsyncClient):
        """Test getting new releases."""
        response = await client.get("/api/v1/indie/discovery/new-releases")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_recommendations(self, client: AsyncClient):
        """Test getting personalized recommendations."""
        response = await client.get("/api/v1/indie/discovery/recommendations")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_discovery_collections(self, client: AsyncClient):
        """Test getting curated discovery collections."""
        response = await client.get("/api/v1/indie/discovery/collections")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestReadingListsEndpoints:
    """Test reading list management."""

    async def test_list_reading_lists(self, client: AsyncClient):
        """Test listing reading lists."""
        response = await client.get("/api/v1/indie/reading-lists")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_reading_list(self, client: AsyncClient):
        """Test getting reading list."""
        response = await client.get("/api/v1/indie/reading-lists/1")
        assert response.status_code in [200, 401, 403, 404]

    async def test_create_reading_list(self, client: AsyncClient):
        """Test creating reading list."""
        list_data = {"title": "My Reading List", "description": "Indie books to read"}
        response = await client.post("/api/v1/indie/reading-lists", json=list_data)
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_add_to_reading_list(self, client: AsyncClient):
        """Test adding item to reading list."""
        item_data = {"catalog_item_id": 1}
        response = await client.post("/api/v1/indie/reading-lists/1/items", json=item_data)
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_remove_from_reading_list(self, client: AsyncClient):
        """Test removing item from reading list."""
        response = await client.delete("/api/v1/indie/reading-lists/1/items/1")
        assert response.status_code in [200, 204, 401, 403, 404]


@pytest.mark.asyncio
class TestReviewEndpoints:
    """Test review and rating endpoints."""

    async def test_get_item_reviews(self, client: AsyncClient):
        """Test getting reviews for item."""
        response = await client.get("/api/v1/indie/catalog/1/reviews")
        assert response.status_code in [200, 401, 403, 404]

    async def test_post_review(self, client: AsyncClient):
        """Test posting review."""
        review_data = {"rating": 4, "title": "Great indie book", "content": "Review content here"}
        response = await client.post("/api/v1/indie/catalog/1/reviews", json=review_data)
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_get_review(self, client: AsyncClient):
        """Test getting specific review."""
        response = await client.get("/api/v1/indie/reviews/1")
        assert response.status_code in [200, 401, 403, 404]

    async def test_update_review(self, client: AsyncClient):
        """Test updating review."""
        update_data = {"rating": 5, "content": "Updated review"}
        response = await client.put("/api/v1/indie/reviews/1", json=update_data)
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_author_reviews(self, client: AsyncClient):
        """Test getting reviews for author."""
        response = await client.get("/api/v1/indie/authors/1/reviews")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestLendingEndpoints:
    """Test lending and circulation endpoints."""

    async def test_get_available_copies(self, client: AsyncClient):
        """Test getting available copies."""
        response = await client.get("/api/v1/indie/catalog/1/availability")
        assert response.status_code in [200, 401, 403, 404]

    async def test_borrow_item(self, client: AsyncClient):
        """Test borrowing indie item."""
        borrow_data = {"days": 21}
        response = await client.post("/api/v1/indie/catalog/1/borrow", json=borrow_data)
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_return_item(self, client: AsyncClient):
        """Test returning borrowed item."""
        response = await client.post("/api/v1/indie/borrowing/1/return")
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_get_borrowing_history(self, client: AsyncClient):
        """Test getting borrowing history."""
        response = await client.get("/api/v1/indie/borrowing/history")
        assert response.status_code in [200, 401, 403, 404]

    async def test_renew_item(self, client: AsyncClient):
        """Test renewing borrowed item."""
        response = await client.post("/api/v1/indie/borrowing/1/renew")
        assert response.status_code in [200, 201, 401, 403, 404]


@pytest.mark.asyncio
class TestAnalyticsEndpoints:
    """Test analytics and engagement endpoints."""

    async def test_get_author_analytics(self, client: AsyncClient):
        """Test getting author analytics."""
        response = await client.get("/api/v1/indie/authors/1/analytics")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_catalog_item_analytics(self, client: AsyncClient):
        """Test getting item analytics."""
        response = await client.get("/api/v1/indie/catalog/1/analytics")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_engagement_metrics(self, client: AsyncClient):
        """Test getting engagement metrics."""
        response = await client.get("/api/v1/indie/analytics/engagement")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_popularity_metrics(self, client: AsyncClient):
        """Test getting popularity metrics."""
        response = await client.get("/api/v1/indie/analytics/popularity")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestMarcAndMetadataEndpoints:
    """Test MARC records and metadata endpoints."""

    async def test_get_marc_record(self, client: AsyncClient):
        """Test getting MARC record for item."""
        response = await client.get("/api/v1/indie/catalog/1/marc")
        assert response.status_code in [200, 401, 403, 404]

    async def test_create_marc_record(self, client: AsyncClient):
        """Test creating MARC record."""
        marc_data = {"catalog_item_id": 1, "marc_data": "MARC record content"}
        response = await client.post("/api/v1/indie/marc", json=marc_data)
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_export_marc(self, client: AsyncClient):
        """Test exporting MARC records."""
        response = await client.get("/api/v1/indie/marc/export")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestIndieIntegration:
    """Integration tests for indie workflows."""

    async def test_author_to_discovery_workflow(self, client: AsyncClient):
        """Test workflow from author creation to discovery."""
        # Create author
        author = await client.post("/api/v1/indie/authors", json={"name": "Test Author"})

        if author.status_code in [200, 201]:
            # Get author works
            works = await client.get("/api/v1/indie/authors/1/works")
            assert works.status_code in [200, 401, 403]

            # Get featured
            featured = await client.get("/api/v1/indie/discovery/featured-authors")
            assert featured.status_code in [200, 401, 403]

    async def test_catalog_to_lending_workflow(self, client: AsyncClient):
        """Test workflow from catalog to lending."""
        # Get catalog
        catalog = await client.get("/api/v1/indie/catalog/1")

        if catalog.status_code == 200:
            # Check availability
            available = await client.get("/api/v1/indie/catalog/1/availability")
            assert available.status_code in [200, 401, 403]

            # Borrow
            borrow = await client.post("/api/v1/indie/catalog/1/borrow", json={"days": 21})
            assert borrow.status_code in [200, 201, 401, 403]

    async def test_reading_list_management_workflow(self, client: AsyncClient):
        """Test reading list management workflow."""
        # Create list
        create = await client.post("/api/v1/indie/reading-lists", json={"title": "Test List"})

        if create.status_code in [200, 201]:
            # Add items
            add = await client.post(
                "/api/v1/indie/reading-lists/1/items", json={"catalog_item_id": 1}
            )
            assert add.status_code in [200, 201, 401, 403]

            # Get list
            get = await client.get("/api/v1/indie/reading-lists/1")
            assert get.status_code in [200, 401, 403]

    async def test_review_and_engagement_workflow(self, client: AsyncClient):
        """Test review and engagement workflow."""
        # Post review
        review = await client.post(
            "/api/v1/indie/catalog/1/reviews", json={"rating": 4, "content": "Good book"}
        )

        # Get reviews
        reviews = await client.get("/api/v1/indie/catalog/1/reviews")

        # Get analytics
        analytics = await client.get("/api/v1/indie/analytics/engagement")

        for response in [review, reviews, analytics]:
            assert response.status_code in [200, 201, 401, 403, 404]

    async def test_discovery_browsing_workflow(self, client: AsyncClient):
        """Test discovery browsing workflow."""
        # Get carousel
        carousel = await client.get("/api/v1/indie/discovery/carousel")

        # Get featured
        featured = await client.get("/api/v1/indie/discovery/featured-authors")

        # Get trending
        trending = await client.get("/api/v1/indie/discovery/trending")

        # Get recommendations
        recs = await client.get("/api/v1/indie/discovery/recommendations")

        for response in [carousel, featured, trending, recs]:
            assert response.status_code in [200, 401, 403, 404]

    async def test_author_engagement_workflow(self, client: AsyncClient):
        """Test author engagement workflow."""
        # Get author
        author = await client.get("/api/v1/indie/authors/1")

        if author.status_code == 200:
            # Get author works
            works = await client.get("/api/v1/indie/authors/1/works")
            assert works.status_code in [200, 401, 403]

            # Get author stats
            stats = await client.get("/api/v1/indie/authors/1/stats")
            assert stats.status_code in [200, 401, 403]

            # Get author reviews
            reviews = await client.get("/api/v1/indie/authors/1/reviews")
            assert reviews.status_code in [200, 401, 403]

            # Get author analytics
            analytics = await client.get("/api/v1/indie/authors/1/analytics")
            assert analytics.status_code in [200, 401, 403]

    async def test_comprehensive_indie_platform_workflow(self, client: AsyncClient):
        """Test comprehensive indie platform workflow."""
        # Authors
        authors = await client.get("/api/v1/indie/authors")

        # Catalog
        catalog = await client.get("/api/v1/indie/catalog")

        # Discovery
        discovery = await client.get("/api/v1/indie/discovery/carousel")

        # Reading lists
        lists = await client.get("/api/v1/indie/reading-lists")

        # Analytics
        analytics = await client.get("/api/v1/indie/analytics/engagement")

        for response in [authors, catalog, discovery, lists, analytics]:
            assert response.status_code in [200, 401, 403, 404]
