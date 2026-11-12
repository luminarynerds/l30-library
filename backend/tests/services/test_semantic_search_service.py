# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for SemanticSearchService.

Tests cover:
- Embedding generation (single + batch)
- Semantic search with pgvector
- Hybrid search (semantic + keyword RRF fusion)
- Find similar items
- Cross-collection search
- Result caching
- Batch embedding pipeline
- Helper methods (_build_combined_text, _merge_results_rrf)

All tests use AsyncMock to avoid database/API dependencies.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.services.semantic_search_service import SemanticSearchService


# ==================== Fixtures ====================


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    """Create SemanticSearchService with mocked dependencies."""
    with patch("app.services.semantic_search_service.get_settings") as mock_settings:
        settings = MagicMock()
        settings.ANTHROPIC_API_KEY = "test-api-key"
        mock_settings.return_value = settings
        svc = SemanticSearchService(mock_db)
    return svc


# ==================== _build_combined_text ====================


class TestBuildCombinedText:
    def test_title_only(self, service):
        result = service._build_combined_text("The Great Gatsby")
        assert result == "The Great Gatsby"

    def test_title_and_author(self, service):
        result = service._build_combined_text("The Great Gatsby", "F. Scott Fitzgerald")
        assert result == "The Great Gatsby by F. Scott Fitzgerald"

    def test_all_fields(self, service):
        result = service._build_combined_text(
            "The Great Gatsby",
            "F. Scott Fitzgerald",
            "A novel about the American Dream",
            "Fiction, Classic"
        )
        assert "The Great Gatsby" in result
        assert "by F. Scott Fitzgerald" in result
        assert "A novel about the American Dream" in result
        assert "subjects: Fiction, Classic" in result

    def test_subjects_as_list(self, service):
        result = service._build_combined_text(
            "Test Book", None, None, ["Fiction", "Science"]
        )
        assert "subjects: Fiction, Science" in result

    def test_description_truncated(self, service):
        long_desc = "a" * 5000
        result = service._build_combined_text("Title", None, long_desc, None)
        # Description should be truncated to 2000 chars
        assert len(result) < 2100

    def test_none_author_excluded(self, service):
        result = service._build_combined_text("Title", None, None, None)
        assert "by" not in result

    def test_empty_subjects_excluded(self, service):
        result = service._build_combined_text("Title", None, None, "")
        assert "subjects" not in result


# ==================== _merge_results_rrf ====================


class TestMergeResultsRRF:
    def test_only_semantic_results(self, service):
        semantic = [
            {"source": "local", "source_id": "1", "title": "Book A"},
            {"source": "local", "source_id": "2", "title": "Book B"},
        ]
        merged = service._merge_results_rrf(semantic, [], semantic_weight=0.6, keyword_weight=0.4)
        assert len(merged) == 2
        assert all(r["matched_by"] == "semantic" for r in merged)

    def test_only_keyword_results(self, service):
        keyword = [
            {"source": "local", "source_id": "1", "title": "Book A"},
        ]
        merged = service._merge_results_rrf([], keyword, semantic_weight=0.6, keyword_weight=0.4)
        assert len(merged) == 1
        assert merged[0]["matched_by"] == "keyword"

    def test_overlapping_results_marked_both(self, service):
        semantic = [
            {"source": "local", "source_id": "1", "title": "Book A"},
            {"source": "local", "source_id": "2", "title": "Book B"},
        ]
        keyword = [
            {"source": "local", "source_id": "1", "title": "Book A"},
            {"source": "local", "source_id": "3", "title": "Book C"},
        ]
        merged = service._merge_results_rrf(semantic, keyword)

        # Book A appears in both -> matched_by = "both"
        book_a = next(r for r in merged if r["source_id"] == "1")
        assert book_a["matched_by"] == "both"

        # Book B is only semantic
        book_b = next(r for r in merged if r["source_id"] == "2")
        assert book_b["matched_by"] == "semantic"

        # Book C is only keyword
        book_c = next(r for r in merged if r["source_id"] == "3")
        assert book_c["matched_by"] == "keyword"

    def test_rrf_score_calculation(self, service):
        """Verify RRF scores use the formula 1/(k+rank) * weight."""
        semantic = [{"source": "local", "source_id": "1", "title": "A"}]
        keyword = []
        k = 60

        merged = service._merge_results_rrf(semantic, keyword, semantic_weight=0.6, keyword_weight=0.4, k=k)

        # Score for rank 0 in semantic: (1/(60+0)) * 0.6
        expected_score = (1 / (k + 0)) * 0.6
        assert abs(merged[0]["rrf_score"] - expected_score) < 1e-10

    def test_overlapping_items_get_higher_rrf(self, service):
        """Items in both lists should rank higher than items in one list."""
        semantic = [
            {"source": "local", "source_id": "1", "title": "Both"},
            {"source": "local", "source_id": "2", "title": "Semantic Only"},
        ]
        keyword = [
            {"source": "local", "source_id": "1", "title": "Both"},
            {"source": "local", "source_id": "3", "title": "Keyword Only"},
        ]

        merged = service._merge_results_rrf(semantic, keyword)

        both_item = next(r for r in merged if r["source_id"] == "1")
        semantic_only = next(r for r in merged if r["source_id"] == "2")
        keyword_only = next(r for r in merged if r["source_id"] == "3")

        assert both_item["rrf_score"] > semantic_only["rrf_score"]
        assert both_item["rrf_score"] > keyword_only["rrf_score"]

    def test_sorted_by_rrf_score_descending(self, service):
        semantic = [
            {"source": "local", "source_id": "1", "title": "A"},
            {"source": "local", "source_id": "2", "title": "B"},
        ]
        keyword = [
            {"source": "local", "source_id": "3", "title": "C"},
            {"source": "local", "source_id": "1", "title": "A"},
        ]

        merged = service._merge_results_rrf(semantic, keyword)
        scores = [r["rrf_score"] for r in merged]
        assert scores == sorted(scores, reverse=True)

    def test_empty_inputs(self, service):
        merged = service._merge_results_rrf([], [])
        assert merged == []


# ==================== generate_embedding ====================


class TestGenerateEmbedding:
    @pytest.mark.asyncio
    async def test_successful_embedding(self, service):
        """Test successful embedding generation via API."""
        fake_embedding = [0.1] * 1536

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [{"embedding": fake_embedding, "index": 0}]
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await service.generate_embedding("test text")

            assert result == fake_embedding
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_text_returns_none(self, service):
        result = await service.generate_embedding("")
        assert result is None

    @pytest.mark.asyncio
    async def test_whitespace_text_returns_none(self, service):
        result = await service.generate_embedding("   ")
        assert result is None

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self, service):
        """Test that API errors return None gracefully."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("API error"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await service.generate_embedding("test text")
            assert result is None

    @pytest.mark.asyncio
    async def test_text_truncation(self, service):
        """Test that long text is truncated to 32000 chars."""
        long_text = "a" * 50000

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [{"embedding": [0.1] * 1536, "index": 0}]
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await service.generate_embedding(long_text)

            call_args = mock_client.post.call_args
            sent_text = call_args[1]["json"]["input"]
            assert len(sent_text) <= 32000


# ==================== generate_embeddings_batch_api ====================


class TestGenerateEmbeddingsBatchAPI:
    @pytest.mark.asyncio
    async def test_successful_batch(self, service):
        """Test batch embedding generation."""
        fake_embeddings = [[0.1] * 1536, [0.2] * 1536]

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [
                    {"embedding": fake_embeddings[0], "index": 0},
                    {"embedding": fake_embeddings[1], "index": 1},
                ]
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await service.generate_embeddings_batch_api(["text1", "text2"])

            assert len(result) == 2
            assert result[0] == fake_embeddings[0]
            assert result[1] == fake_embeddings[1]

    @pytest.mark.asyncio
    async def test_api_error_returns_nones(self, service):
        """Test that batch API error returns list of Nones."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("Batch API error"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await service.generate_embeddings_batch_api(["a", "b", "c"])
            assert result == [None, None, None]

    @pytest.mark.asyncio
    async def test_out_of_order_results(self, service):
        """Test that results are correctly reordered by index."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [
                    {"embedding": [0.2] * 1536, "index": 1},
                    {"embedding": [0.1] * 1536, "index": 0},
                ]
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await service.generate_embeddings_batch_api(["first", "second"])

            # Index 0 should have [0.1], index 1 should have [0.2]
            assert result[0][0] == pytest.approx(0.1)
            assert result[1][0] == pytest.approx(0.2)


# ==================== search_semantic ====================


class TestSearchSemantic:
    @pytest.mark.asyncio
    async def test_returns_cached_results(self, service, mock_db):
        """Test that cached results are returned when available."""
        cached_data = {
            "query": "test query",
            "results": [{"title": "Cached Book"}],
            "total_results": 1,
            "search_time_ms": 5.0,
        }

        service._get_cached_search = AsyncMock(return_value=cached_data)

        result = await service.search_semantic("test query")

        assert result["was_cached"] is True
        assert result["results"] == [{"title": "Cached Book"}]

    @pytest.mark.asyncio
    async def test_returns_error_on_failed_embedding(self, service):
        """Test graceful handling when embedding generation fails."""
        service._get_cached_search = AsyncMock(return_value=None)
        service.generate_embedding = AsyncMock(return_value=None)

        result = await service.search_semantic("test query")

        assert result["total_results"] == 0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_successful_search_caches_result(self, service, mock_db):
        """Test that successful search results are cached."""
        service._get_cached_search = AsyncMock(return_value=None)
        service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        service._cache_search = AsyncMock()
        service._enrich_search_results = AsyncMock(return_value=[])

        # Mock db.execute to return empty results
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.search_semantic("test query")

        assert result["was_cached"] is False
        assert result["query"] == "test query"
        service._cache_search.assert_called_once()


# ==================== search_hybrid ====================


class TestSearchHybrid:
    @pytest.mark.asyncio
    async def test_calls_both_search_methods(self, service):
        """Test that hybrid search runs both semantic and keyword."""
        service.search_semantic = AsyncMock(return_value={
            "results": [{"source": "local", "source_id": "1", "title": "Semantic"}],
            "search_time_ms": 10.0,
        })
        service._keyword_search = AsyncMock(return_value={
            "results": [{"source": "local", "source_id": "2", "title": "Keyword"}],
            "search_time_ms": 5.0,
        })

        result = await service.search_hybrid("test query")

        service.search_semantic.assert_called_once()
        service._keyword_search.assert_called_once()
        assert result["search_type"] == "hybrid"
        assert result["total_results"] == 2

    @pytest.mark.asyncio
    async def test_respects_weights(self, service):
        """Test that semantic and keyword weights are passed."""
        service.search_semantic = AsyncMock(return_value={
            "results": [],
            "search_time_ms": 0,
        })
        service._keyword_search = AsyncMock(return_value={
            "results": [],
            "search_time_ms": 0,
        })

        await service.search_hybrid(
            "test", semantic_weight=0.8, keyword_weight=0.2
        )

        # Verify search was called
        service.search_semantic.assert_called_once()

    @pytest.mark.asyncio
    async def test_pagination(self, service):
        """Test that hybrid search paginates results."""
        results = [
            {"source": "local", "source_id": str(i), "title": f"Book {i}"}
            for i in range(10)
        ]
        service.search_semantic = AsyncMock(return_value={
            "results": results,
            "search_time_ms": 10.0,
        })
        service._keyword_search = AsyncMock(return_value={
            "results": [],
            "search_time_ms": 5.0,
        })

        result = await service.search_hybrid("test", limit=3, offset=2)

        assert len(result["results"]) == 3


# ==================== find_similar_items ====================


class TestFindSimilarItems:
    @pytest.mark.asyncio
    async def test_item_not_found(self, service, mock_db):
        """Test handling when source item doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.find_similar_items(item_id=999)

        assert "error" in result
        assert result["similar_items"] == []

    @pytest.mark.asyncio
    async def test_embedding_generation_failure(self, service, mock_db):
        """Test handling when embedding can't be generated for item."""
        mock_item = MagicMock()
        mock_item.title = "Test Book"
        mock_item.author = "Author"
        mock_item.description = "Desc"
        mock_item.subjects = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute = AsyncMock(return_value=mock_result)

        service._get_or_create_embedding = AsyncMock(return_value=None)

        result = await service.find_similar_items(item_id=1)

        assert "error" in result
        assert result["similar_items"] == []


# ==================== Caching ====================


class TestCaching:
    @pytest.mark.asyncio
    async def test_cache_hit_increments_count(self, service, mock_db):
        """Test that cache hits increment the hit counter."""
        mock_cache = MagicMock()
        mock_cache.hit_count = 0
        mock_cache.results_json = {"query": "test", "results": []}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_cache
        mock_db.execute = AsyncMock(return_value=mock_result)

        cached = await service._get_cached_search("test", "semantic")

        assert cached is not None
        assert mock_cache.hit_count == 1

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, service, mock_db):
        """Test that cache miss returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        cached = await service._get_cached_search("unknown", "semantic")

        assert cached is None

    @pytest.mark.asyncio
    async def test_cache_stores_results(self, service, mock_db):
        """Test that results are stored in cache."""
        results = {"query": "test", "results": [], "search_time_ms": 10.0}

        await service._cache_search("test query", results, "semantic")

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()


# ==================== _enrich_search_results ====================


class TestEnrichSearchResults:
    @pytest.mark.asyncio
    async def test_enriches_local_item(self, service, mock_db):
        """Test enrichment of local catalog items."""
        mock_item = MagicMock()
        mock_item.id = 1
        mock_item.title = "Test Book"
        mock_item.author = "Author"
        mock_item.description = "A description"
        mock_item.cover_url = None
        mock_item.item_type = MagicMock()
        mock_item.item_type.value = "book"
        mock_item.subjects = ["Fiction"]
        mock_item.status = MagicMock()
        mock_item.status.value = "available"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute = AsyncMock(return_value=mock_result)

        rows = [
            (1, "catalog_item_combined", 1, "local", "text", 0.85),
        ]

        results = await service._enrich_search_results(rows)

        assert len(results) == 1
        assert results[0]["title"] == "Test Book"
        assert results[0]["source"] == "local"
        assert results[0]["search_confidence"] == "high"
        assert results[0]["matched_by"] == "semantic"

    @pytest.mark.asyncio
    async def test_enriches_gutenberg_item(self, service, mock_db):
        """Test enrichment of Gutenberg items."""
        mock_gb = MagicMock()
        mock_gb.gutenberg_id = 42
        mock_gb.title = "Gutenberg Book"
        mock_gb.authors = '[{"name": "Jane Austen"}]'
        mock_gb.cover_url = None
        mock_gb.subjects = '["Fiction", "Romance"]'

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_gb
        mock_db.execute = AsyncMock(return_value=mock_result)

        rows = [
            (2, "gutenberg_combined", 42, "gutenberg", "text", 0.6),
        ]

        results = await service._enrich_search_results(rows)

        assert len(results) == 1
        assert results[0]["source"] == "gutenberg"
        assert results[0]["author"] == "Jane Austen"
        assert results[0]["is_available"] is True  # Gutenberg always available

    @pytest.mark.asyncio
    async def test_confidence_levels(self, service, mock_db):
        """Test confidence classification based on similarity score."""
        mock_item = MagicMock()
        mock_item.id = 1
        mock_item.title = "Test"
        mock_item.author = None
        mock_item.description = None
        mock_item.cover_url = None
        mock_item.item_type = MagicMock()
        mock_item.item_type.value = "book"
        mock_item.subjects = None
        mock_item.status = MagicMock()
        mock_item.status.value = "available"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute = AsyncMock(return_value=mock_result)

        # High confidence
        rows = [(1, "catalog_item_combined", 1, "local", "text", 0.85)]
        results = await service._enrich_search_results(rows)
        assert results[0]["search_confidence"] == "high"

        # Medium confidence
        rows = [(1, "catalog_item_combined", 1, "local", "text", 0.55)]
        results = await service._enrich_search_results(rows)
        assert results[0]["search_confidence"] == "medium"

        # Low confidence
        rows = [(1, "catalog_item_combined", 1, "local", "text", 0.35)]
        results = await service._enrich_search_results(rows)
        assert results[0]["search_confidence"] == "low"

    @pytest.mark.asyncio
    async def test_missing_item_skipped(self, service, mock_db):
        """Test that items not found in DB are skipped."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        rows = [
            (1, "catalog_item_combined", 999, "local", "text", 0.8),
        ]

        results = await service._enrich_search_results(rows)
        assert len(results) == 0


# ==================== Batch Embedding Pipeline ====================


class TestBatchEmbeddingPipeline:
    @pytest.mark.asyncio
    async def test_no_items_to_embed(self, service, mock_db):
        """Test batch pipeline with no items to process."""
        mock_metadata = MagicMock()
        mock_metadata.status = "pending"
        service._get_or_create_metadata = AsyncMock(return_value=mock_metadata)
        service._get_items_to_embed = AsyncMock(return_value=[])

        result = await service.generate_embeddings_batch("catalog_item_combined")

        assert result["total_items"] == 0
        assert result["embedded_count"] == 0
        assert mock_metadata.status == "completed"

    @pytest.mark.asyncio
    async def test_successful_batch_processing(self, service, mock_db):
        """Test successful batch embedding generation."""
        mock_metadata = MagicMock()
        mock_metadata.status = "pending"
        service._get_or_create_metadata = AsyncMock(return_value=mock_metadata)
        service._get_items_to_embed = AsyncMock(return_value=[
            {"id": 1, "title": "Book 1", "author": "Author 1", "description": None, "subjects": None, "source_collection": "local"},
            {"id": 2, "title": "Book 2", "author": "Author 2", "description": None, "subjects": None, "source_collection": "local"},
        ])
        service.generate_embeddings_batch_api = AsyncMock(return_value=[
            [0.1] * 1536,
            [0.2] * 1536,
        ])

        # Mock existing check - no existing embeddings
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.generate_embeddings_batch(
            "catalog_item_combined", batch_size=100
        )

        assert result["total_items"] == 2
        assert result["embedded_count"] == 2
        assert result["failed_count"] == 0
        assert mock_metadata.status == "completed"

    @pytest.mark.asyncio
    async def test_batch_with_failed_embeddings(self, service, mock_db):
        """Test batch processing when some embeddings fail."""
        mock_metadata = MagicMock()
        mock_metadata.status = "pending"
        service._get_or_create_metadata = AsyncMock(return_value=mock_metadata)
        service._get_items_to_embed = AsyncMock(return_value=[
            {"id": 1, "title": "Book 1", "author": None, "description": None, "subjects": None, "source_collection": "local"},
            {"id": 2, "title": "Book 2", "author": None, "description": None, "subjects": None, "source_collection": "local"},
        ])
        service.generate_embeddings_batch_api = AsyncMock(return_value=[
            [0.1] * 1536,
            None,  # Failed embedding
        ])

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.generate_embeddings_batch("catalog_item_combined")

        assert result["embedded_count"] == 1
        assert result["failed_count"] == 1


# ==================== _get_or_create_metadata ====================


class TestGetOrCreateMetadata:
    @pytest.mark.asyncio
    async def test_returns_existing_metadata(self, service, mock_db):
        """Test returning existing metadata."""
        existing = MagicMock()
        existing.entity_type = "catalog_item_combined"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute = AsyncMock(return_value=mock_result)

        metadata = await service._get_or_create_metadata("catalog_item_combined")
        assert metadata == existing

    @pytest.mark.asyncio
    async def test_creates_new_metadata_for_catalog(self, service, mock_db):
        """Test creating new metadata for catalog entity type."""
        # First call returns None (no existing), second returns count
        mock_no_result = MagicMock()
        mock_no_result.scalar_one_or_none.return_value = None

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 42

        mock_db.execute = AsyncMock(side_effect=[mock_no_result, mock_count_result])

        metadata = await service._get_or_create_metadata("catalog_item_combined")

        mock_db.add.assert_called_once()
        assert metadata.entity_type == "catalog_item_combined"
        assert metadata.total_count == 42
