# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for DiscoveryService.

Tests cover:
- Hidden gem retrieval with filters
- Hidden gem score recalculation
- Author similarity search
- Author embedding rebuild
- Shared subjects computation
- Helper methods

All tests use AsyncMock to avoid database/numpy dependencies.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.discovery_service import DiscoveryService


# ==================== Fixtures ====================


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    with patch("app.services.discovery_service.get_settings") as mock_settings:
        settings = MagicMock()
        mock_settings.return_value = settings
        svc = DiscoveryService(mock_db)
    return svc


# ==================== _find_shared_subjects ====================


class TestFindSharedSubjects:
    def test_shared_subjects(self, service):
        subjects_a = ["Fiction", "Science", "Space"]
        subjects_b = ["fiction", "History", "space"]

        result = service._find_shared_subjects(subjects_a, subjects_b)

        assert "fiction" in result
        assert "space" in result
        assert len(result) == 2

    def test_no_shared_subjects(self, service):
        result = service._find_shared_subjects(["A", "B"], ["C", "D"])
        assert result == []

    def test_empty_lists(self, service):
        assert service._find_shared_subjects([], []) == []
        assert service._find_shared_subjects(["A"], []) == []
        assert service._find_shared_subjects([], ["A"]) == []

    def test_none_inputs(self, service):
        assert service._find_shared_subjects(None, ["A"]) == []
        assert service._find_shared_subjects(["A"], None) == []
        assert service._find_shared_subjects(None, None) == []

    def test_case_insensitive(self, service):
        result = service._find_shared_subjects(["FICTION"], ["fiction"])
        assert "fiction" in result

    def test_whitespace_handling(self, service):
        result = service._find_shared_subjects([" Fiction "], ["fiction"])
        assert "fiction" in result

    def test_sorted_output(self, service):
        result = service._find_shared_subjects(
            ["Zebra", "Apple", "Mango"],
            ["mango", "apple", "zebra"]
        )
        assert result == sorted(result)


# ==================== get_hidden_gems ====================


class TestGetHiddenGems:
    @pytest.mark.asyncio
    async def test_returns_gems(self, service, mock_db):
        """Test basic hidden gem retrieval."""
        mock_gem = MagicMock()
        mock_gem.to_dict.return_value = {
            "entity_type": "catalog_item_combined",
            "entity_id": 1,
            "title": "Hidden Book",
            "author": "Unknown Author",
            "gem_score": 0.85,
            "circulation_count": 2,
        }

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_gem]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_hidden_gems()

        assert result["total"] == 1
        assert result["gems"][0]["title"] == "Hidden Book"
        assert "search_time_ms" in result

    @pytest.mark.asyncio
    async def test_empty_results(self, service, mock_db):
        """Test when no gems meet criteria."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_hidden_gems()

        assert result["total"] == 0
        assert result["gems"] == []

    @pytest.mark.asyncio
    async def test_subject_filter(self, service, mock_db):
        """Test filtering by subject."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_hidden_gems(subject="science fiction")

        assert result["filters"]["subject"] == "science fiction"

    @pytest.mark.asyncio
    async def test_source_filter(self, service, mock_db):
        """Test filtering by source collection."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_hidden_gems(source_collection="gutenberg")

        assert result["filters"]["source_collection"] == "gutenberg"

    @pytest.mark.asyncio
    async def test_min_gem_score_filter(self, service, mock_db):
        """Test that min_gem_score parameter is included in filters."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_hidden_gems(min_gem_score=0.5)

        assert result["filters"]["min_gem_score"] == 0.5


# ==================== recalculate_gem_scores ====================


class TestRecalculateGemScores:
    @pytest.mark.asyncio
    async def test_no_popular_items(self, service, mock_db):
        """Test when no popular items have embeddings."""
        service._get_popular_embeddings = AsyncMock(return_value=[])

        result = await service.recalculate_gem_scores()

        assert result["processed"] == 0
        assert "No popular items" in result["message"]

    @pytest.mark.asyncio
    async def test_no_valid_embeddings(self, service, mock_db):
        """Test when popular embeddings exist but are None."""
        mock_emb = MagicMock()
        mock_emb.embedding = None
        service._get_popular_embeddings = AsyncMock(return_value=[mock_emb])

        # recalculate_gem_scores queries all_embeddings before checking
        # whether the popular set has any usable vectors, so db.execute
        # must be wired up even though this test's focus is the
        # "no valid popular embeddings" short-circuit.
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.recalculate_gem_scores()

        assert result["processed"] == 0
        assert "No valid popular embeddings" in result["message"]


# ==================== find_similar_authors ====================


class TestFindSimilarAuthors:
    @pytest.mark.asyncio
    async def test_author_not_found(self, service, mock_db):
        """Test when author has no embedding."""
        service._get_or_build_author_embedding = AsyncMock(return_value=None)

        result = await service.find_similar_authors("Unknown Author")

        assert result["similar_authors"] == []
        assert "error" in result

    @pytest.mark.asyncio
    async def test_author_embedding_not_generated(self, service, mock_db):
        """Test when author embedding couldn't be generated."""
        mock_author_emb = MagicMock()
        mock_author_emb.embedding = None

        service._get_or_build_author_embedding = AsyncMock(return_value=mock_author_emb)

        result = await service.find_similar_authors("Some Author")

        assert result["similar_authors"] == []
        assert "error" in result

    @pytest.mark.asyncio
    async def test_successful_similarity_search(self, service, mock_db):
        """Test successful author similarity search."""
        mock_author_emb = MagicMock()
        mock_author_emb.embedding = [0.1] * 1536
        mock_author_emb.book_count = 5
        mock_author_emb.genres = ["fiction"]
        mock_author_emb.subjects = ["space", "robots"]

        service._get_or_build_author_embedding = AsyncMock(return_value=mock_author_emb)

        # Mock the similarity query results
        similar_row = MagicMock()
        similar_row.author_name = "Similar Author"
        similar_row.book_count = 3
        similar_row.source_collections = ["local"]
        similar_row.genres = ["fiction"]
        similar_row.subjects = ["space", "aliens"]
        similar_row.similarity = 0.85

        mock_result = MagicMock()
        mock_result.all.return_value = [similar_row]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.find_similar_authors("Test Author")

        assert len(result["similar_authors"]) == 1
        assert result["similar_authors"][0]["author_name"] == "Similar Author"
        assert result["similar_authors"][0]["similarity_score"] == 0.85
        assert "space" in result["similar_authors"][0]["shared_subjects"]
        assert result["author_book_count"] == 5

    @pytest.mark.asyncio
    async def test_normalizes_author_name(self, service, mock_db):
        """Test that author name is normalized (lowercased, stripped)."""
        service._get_or_build_author_embedding = AsyncMock(return_value=None)

        await service.find_similar_authors("  Isaac Asimov  ")

        # Should call with normalized name
        call_args = service._get_or_build_author_embedding.call_args
        assert call_args[0][0] == "isaac asimov"  # normalized


# ==================== rebuild_author_embeddings ====================


class TestRebuildAuthorEmbeddings:
    @pytest.mark.asyncio
    async def test_no_authors_found(self, service, mock_db):
        """Test when no authors have enough books."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.rebuild_author_embeddings()

        assert result["processed"] == 0
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_processes_authors(self, service, mock_db):
        """Test processing authors with books."""
        # Mock author query result
        author_row = MagicMock()
        author_row.author_norm = "test author"
        author_row.author = "Test Author"

        mock_result = MagicMock()
        mock_result.all.return_value = [author_row]
        mock_db.execute = AsyncMock(return_value=mock_result)

        service._build_single_author_embedding = AsyncMock(return_value=MagicMock())

        result = await service.rebuild_author_embeddings()

        assert result["processed"] == 1
        assert result["errors"] == 0
        service._build_single_author_embedding.assert_called_once_with(
            "test author", "Test Author"
        )

    @pytest.mark.asyncio
    async def test_handles_individual_errors(self, service, mock_db):
        """Test that errors for one author don't stop processing others."""
        author1 = MagicMock()
        author1.author_norm = "author1"
        author1.author = "Author 1"

        author2 = MagicMock()
        author2.author_norm = "author2"
        author2.author = "Author 2"

        mock_result = MagicMock()
        mock_result.all.return_value = [author1, author2]
        mock_db.execute = AsyncMock(return_value=mock_result)

        # First author fails, second succeeds
        service._build_single_author_embedding = AsyncMock(
            side_effect=[Exception("Build failed"), MagicMock()]
        )

        result = await service.rebuild_author_embeddings()

        assert result["processed"] == 1
        assert result["errors"] == 1


# ==================== _get_circulation_count ====================


class TestGetCirculationCount:
    @pytest.mark.asyncio
    async def test_gutenberg_uses_download_count(self, service, mock_db):
        """Test that Gutenberg items use download_count."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1500
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await service._get_circulation_count(
            "gutenberg_combined", 42, "gutenberg"
        )

        assert count == 1500

    @pytest.mark.asyncio
    async def test_local_uses_checkout_count(self, service, mock_db):
        """Test that local items count checkouts."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await service._get_circulation_count(
            "catalog_item_combined", 1, "local"
        )

        assert count == 5

    @pytest.mark.asyncio
    async def test_null_count_returns_zero(self, service, mock_db):
        """Test that null count returns 0."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await service._get_circulation_count(
            "catalog_item_combined", 1, "local"
        )

        assert count == 0


# ==================== _get_item_metadata ====================


class TestGetItemMetadata:
    @pytest.mark.asyncio
    async def test_local_item(self, service, mock_db):
        """Test metadata for local catalog item."""
        mock_item = MagicMock()
        mock_item.title = "Test Book"
        mock_item.author = "Test Author"
        mock_item.subjects = ["Fiction", "Science"]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute = AsyncMock(return_value=mock_result)

        title, author, subjects = await service._get_item_metadata(
            "catalog_item_combined", 1, "local"
        )

        assert title == "Test Book"
        assert author == "Test Author"
        assert subjects == ["Fiction", "Science"]

    @pytest.mark.asyncio
    async def test_gutenberg_item(self, service, mock_db):
        """Test metadata for Gutenberg item."""
        mock_book = MagicMock()
        mock_book.title = "Gutenberg Book"
        mock_book.authors = '[{"name": "Jane Austen"}]'
        mock_book.subjects = '["Fiction", "Romance"]'

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_book
        mock_db.execute = AsyncMock(return_value=mock_result)

        title, author, subjects = await service._get_item_metadata(
            "gutenberg_combined", 42, "gutenberg"
        )

        assert title == "Gutenberg Book"
        assert author == "Jane Austen"
        assert subjects == ["Fiction", "Romance"]

    @pytest.mark.asyncio
    async def test_missing_item_returns_defaults(self, service, mock_db):
        """Test that missing item returns default values."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        title, author, subjects = await service._get_item_metadata(
            "catalog_item_combined", 999, "local"
        )

        assert title == "Unknown"
        assert author is None
        assert subjects is None
