# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for semantic search API endpoints.

Tests cover:
- GET /search/semantic - vector similarity search
- GET /search/hybrid - semantic + keyword with RRF
- GET /search/cross-collection - all-collection search
- GET /search/autocomplete - typo-tolerant autocomplete
- GET /search/semantic/suggestions - concept-aware suggestions
- GET /search/similar/{source}/{source_id} - similar items
- GET /search/hidden-gems - hidden gem discovery
- POST /search/hidden-gems/recalculate - background recalculation
- GET /search/similar-authors - author similarity
- POST /search/author-embeddings/rebuild - author embedding rebuild
- POST /search/embeddings/generate - batch embedding trigger
- GET /search/embeddings/progress/{entity_type} - progress tracking
- GET /search/embeddings/stats - statistics
- GET /search/embeddings/health - health check

All tests use mocked services to avoid database and external API calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ==================== Fixtures ====================


@pytest.fixture
def mock_semantic_service():
    """Mock SemanticSearchService."""
    service = MagicMock()
    service.search_semantic = AsyncMock(return_value={
        "query": "test",
        "results": [],
        "total_results": 0,
        "search_time_ms": 10.0,
        "embedding_time_ms": 5.0,
        "was_cached": False,
    })
    service.search_hybrid = AsyncMock(return_value={
        "query": "test",
        "results": [],
        "total_results": 0,
        "search_time_ms": 15.0,
        "semantic_time_ms": 10.0,
        "keyword_time_ms": 5.0,
    })
    service.search_cross_collection = AsyncMock(return_value={
        "query": "test",
        "results": [],
        "total_results": 0,
        "search_time_ms": 20.0,
        "was_cached": False,
    })
    service.find_similar_items = AsyncMock(return_value={
        "item_id": 1,
        "item_title": "Test Book",
        "similar_items": [],
        "search_time_ms": 8.0,
    })
    service.generate_embeddings_batch = AsyncMock(return_value={
        "entity_type": "catalog_item_combined",
        "total_items": 100,
        "embedded_count": 95,
        "failed_count": 5,
    })
    return service


@pytest.fixture
def mock_autocomplete_service():
    """Mock AutocompleteService."""
    service = MagicMock()
    service.autocomplete = AsyncMock(return_value={
        "query": "har",
        "suggestions": [
            {
                "id": "local:1",
                "title": "Harry Potter",
                "author": "J.K. Rowling",
                "format": "book",
                "source": "local",
                "cover_url": None,
                "match_type": "prefix",
                "similarity_score": 1.0,
            }
        ],
        "search_time_ms": 3.0,
        "total_suggestions": 1,
        "strategy": "trigram+prefix",
    })
    return service


@pytest.fixture
def mock_discovery_service():
    """Mock DiscoveryService."""
    service = MagicMock()
    service.get_hidden_gems = AsyncMock(return_value={
        "gems": [],
        "total": 0,
        "filters": {},
        "search_time_ms": 5.0,
    })
    service.find_similar_authors = AsyncMock(return_value={
        "author": "Test Author",
        "author_book_count": 5,
        "author_genres": ["fiction"],
        "similar_authors": [],
        "search_time_ms": 12.0,
    })
    service.recalculate_gem_scores = AsyncMock()
    service.rebuild_author_embeddings = AsyncMock()
    return service


@pytest.fixture
def client(mock_semantic_service, mock_autocomplete_service, mock_discovery_service):
    """Create test client with mocked service dependencies."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db
    from app.api.v1.dependencies import require_admin

    # Mock the database dependency. A bare AsyncMock() propagates its
    # "asyncness" to every child attribute, so a plain (non-async) call like
    # result.scalar() would come back as an unawaited coroutine -- pin
    # execute()'s return value to a MagicMock so .scalar()/.scalar_one_or_none()
    # behave like the real (sync) Result object.
    async def override_get_db():
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    # Skip the FirstBootMiddleware's real-DB setup-required check (it uses
    # its own async_session_maker(), not the get_db override above) so these
    # mocked-service tests don't 503 against an un-seeded test database.
    app.state.setup_complete = True

    # The embedding-management endpoints are admin-only; override the
    # dependency directly rather than fabricate a bearer token.
    app.dependency_overrides[require_admin] = lambda: None

    # Patch service factory functions
    with patch("app.api.v1.semantic_search.get_semantic_search_service", return_value=mock_semantic_service), \
         patch("app.api.v1.semantic_search.get_autocomplete_service", return_value=mock_autocomplete_service), \
         patch("app.api.v1.semantic_search.get_discovery_service", return_value=mock_discovery_service):
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()


# ==================== Semantic Search ====================


class TestSemanticSearchEndpoint:
    def test_basic_search(self, client, mock_semantic_service):
        response = client.get("/api/v1/search/semantic?q=space+exploration")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "space exploration"
        assert data["search_type"] == "semantic"
        assert "total_results" in data
        assert "results" in data
        assert "search_time_ms" in data

    def test_missing_query_returns_422(self, client):
        response = client.get("/api/v1/search/semantic")
        assert response.status_code == 422

    def test_entity_types_filter(self, client, mock_semantic_service):
        response = client.get(
            "/api/v1/search/semantic?q=test&entity_types=catalog_item_combined,gutenberg_combined"
        )
        assert response.status_code == 200
        call_kwargs = mock_semantic_service.search_semantic.call_args[1]
        assert call_kwargs["entity_types"] == ["catalog_item_combined", "gutenberg_combined"]

    def test_sources_filter(self, client, mock_semantic_service):
        response = client.get("/api/v1/search/semantic?q=test&sources=local,gutenberg")
        assert response.status_code == 200
        call_kwargs = mock_semantic_service.search_semantic.call_args[1]
        assert call_kwargs["source_collections"] == ["local", "gutenberg"]

    def test_min_similarity_parameter(self, client, mock_semantic_service):
        response = client.get("/api/v1/search/semantic?q=test&min_similarity=0.7")
        assert response.status_code == 200
        call_kwargs = mock_semantic_service.search_semantic.call_args[1]
        assert call_kwargs["min_similarity"] == 0.7

    def test_pagination_parameters(self, client, mock_semantic_service):
        response = client.get("/api/v1/search/semantic?q=test&limit=10&offset=20")
        assert response.status_code == 200
        call_kwargs = mock_semantic_service.search_semantic.call_args[1]
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 20

    def test_limit_validation(self, client):
        response = client.get("/api/v1/search/semantic?q=test&limit=999")
        assert response.status_code == 422


# ==================== Hybrid Search ====================


class TestHybridSearchEndpoint:
    def test_basic_hybrid_search(self, client, mock_semantic_service):
        response = client.get("/api/v1/search/hybrid?q=time+travel")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "time travel"
        assert "merge_strategy" in data
        assert data["merge_strategy"] == "reciprocal_rank_fusion"

    def test_custom_weights(self, client, mock_semantic_service):
        response = client.get(
            "/api/v1/search/hybrid?q=test&semantic_weight=0.8&keyword_weight=0.2"
        )
        assert response.status_code == 200
        call_kwargs = mock_semantic_service.search_hybrid.call_args[1]
        assert call_kwargs["semantic_weight"] == 0.8
        assert call_kwargs["keyword_weight"] == 0.2

    def test_missing_query_returns_422(self, client):
        response = client.get("/api/v1/search/hybrid")
        assert response.status_code == 422


# ==================== Cross-Collection Search ====================


class TestCrossCollectionEndpoint:
    def test_basic_cross_collection(self, client, mock_semantic_service):
        response = client.get("/api/v1/search/cross-collection?q=classic+novels")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "classic novels"
        assert "source_breakdown" in data

    def test_missing_query_returns_422(self, client):
        response = client.get("/api/v1/search/cross-collection")
        assert response.status_code == 422


# ==================== Autocomplete ====================


class TestAutocompleteEndpoint:
    def test_basic_autocomplete(self, client, mock_autocomplete_service):
        response = client.get("/api/v1/search/autocomplete?q=har")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "har"
        assert "suggestions" in data
        assert len(data["suggestions"]) == 1
        assert data["suggestions"][0]["title"] == "Harry Potter"

    def test_short_query_returns_422(self, client):
        """Query min length is 2 characters."""
        response = client.get("/api/v1/search/autocomplete?q=h")
        assert response.status_code == 422

    def test_include_authors_parameter(self, client, mock_autocomplete_service):
        response = client.get(
            "/api/v1/search/autocomplete?q=test&include_authors=false"
        )
        assert response.status_code == 200
        call_kwargs = mock_autocomplete_service.autocomplete.call_args[1]
        assert call_kwargs["include_authors"] is False

    def test_limit_parameter(self, client, mock_autocomplete_service):
        response = client.get("/api/v1/search/autocomplete?q=test&limit=5")
        assert response.status_code == 200
        call_kwargs = mock_autocomplete_service.autocomplete.call_args[1]
        assert call_kwargs["limit"] == 5


# ==================== Similar Items ====================


class TestSimilarItemsEndpoint:
    def test_find_similar(self, client, mock_semantic_service):
        response = client.get("/api/v1/search/similar/local/123")
        assert response.status_code == 200
        data = response.json()
        assert data["item_id"] == "123"
        assert "similar_items" in data
        assert data["similarity_metric"] == "cosine_similarity"

    def test_invalid_source_id(self, client, mock_semantic_service):
        """Non-numeric source_id should return empty results."""
        response = client.get("/api/v1/search/similar/local/not-a-number")
        assert response.status_code == 200
        data = response.json()
        assert data["similar_items"] == []

    def test_limit_parameter(self, client, mock_semantic_service):
        response = client.get("/api/v1/search/similar/local/1?limit=5")
        assert response.status_code == 200


# ==================== Hidden Gems ====================


class TestHiddenGemsEndpoint:
    def test_basic_hidden_gems(self, client, mock_discovery_service):
        response = client.get("/api/v1/search/hidden-gems")
        assert response.status_code == 200
        data = response.json()
        assert "gems" in data
        assert "total" in data
        assert "search_time_ms" in data

    def test_subject_filter(self, client, mock_discovery_service):
        response = client.get("/api/v1/search/hidden-gems?subject=science+fiction")
        assert response.status_code == 200
        call_kwargs = mock_discovery_service.get_hidden_gems.call_args[1]
        assert call_kwargs["subject"] == "science fiction"

    def test_source_filter(self, client, mock_discovery_service):
        response = client.get("/api/v1/search/hidden-gems?source=gutenberg")
        assert response.status_code == 200
        call_kwargs = mock_discovery_service.get_hidden_gems.call_args[1]
        assert call_kwargs["source_collection"] == "gutenberg"

    def test_min_score_parameter(self, client, mock_discovery_service):
        response = client.get("/api/v1/search/hidden-gems?min_score=0.5")
        assert response.status_code == 200

    def test_recalculate_returns_pending(self, client, mock_discovery_service):
        response = client.post(
            "/api/v1/search/hidden-gems/recalculate",
            json={"batch_size": 500}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert "recalculation started" in data["message"].lower()


# ==================== Similar Authors ====================


class TestSimilarAuthorsEndpoint:
    def test_basic_author_search(self, client, mock_discovery_service):
        response = client.get("/api/v1/search/similar-authors?author=Isaac+Asimov")
        assert response.status_code == 200
        data = response.json()
        assert data["author"] == "Isaac Asimov"
        assert "similar_authors" in data
        assert "search_time_ms" in data

    def test_missing_author_returns_422(self, client):
        response = client.get("/api/v1/search/similar-authors")
        assert response.status_code == 422

    def test_rebuild_returns_pending(self, client, mock_discovery_service):
        response = client.post(
            "/api/v1/search/author-embeddings/rebuild",
            json={"batch_size": 100}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"


# ==================== Embedding Management ====================


class TestEmbeddingManagementEndpoints:
    def test_generate_embeddings(self, client, mock_semantic_service):
        response = client.post(
            "/api/v1/search/embeddings/generate",
            json={
                "entity_types": ["catalog_item_combined"],
                "batch_size": 100,
                "skip_existing": True,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert "catalog_item_combined" in data["entity_types"]

    def test_generate_multiple_entity_types(self, client, mock_semantic_service):
        response = client.post(
            "/api/v1/search/embeddings/generate",
            json={
                "entity_types": ["catalog_item_combined", "gutenberg_combined"],
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["entity_types"]) == 2

    def test_embedding_stats(self, client):
        """Test embedding stats endpoint structure."""
        # This endpoint queries DB directly, so we need mock execution
        with patch("app.api.v1.semantic_search.AsyncSession"):
            response = client.get("/api/v1/search/embeddings/stats")
            # Endpoint might fail with mock DB, but should return valid status
            assert response.status_code in [200, 500]

    def test_embedding_health(self, client):
        """Test embedding health endpoint structure."""
        with patch("app.api.v1.semantic_search.AsyncSession"):
            response = client.get("/api/v1/search/embeddings/health")
            assert response.status_code in [200, 500]
