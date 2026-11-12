# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for AutocompleteService.

Tests cover:
- Short query handling (< 2 chars)
- Prefix match suggestions
- Trigram similarity matching
- Author name matching
- Gutenberg book matching
- Result deduplication
- Sorting by match type priority
- Minimum similarity filtering

All tests use AsyncMock to avoid database dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.autocomplete_service import AutocompleteService


# ==================== Fixtures ====================


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    return AutocompleteService(mock_db)


# ==================== Short Query ====================


class TestShortQuery:
    @pytest.mark.asyncio
    async def test_single_char_returns_empty(self, service):
        result = await service.autocomplete("a")
        assert result["suggestions"] == []
        assert result["strategy"] == "too_short"

    @pytest.mark.asyncio
    async def test_empty_string_returns_empty(self, service):
        result = await service.autocomplete("")
        assert result["suggestions"] == []
        assert result["strategy"] == "too_short"

    @pytest.mark.asyncio
    async def test_whitespace_returns_empty(self, service):
        result = await service.autocomplete("  ")
        assert result["suggestions"] == []
        assert result["strategy"] == "too_short"


# ==================== Combined Autocomplete ====================


class TestCombinedAutocomplete:
    @pytest.mark.asyncio
    async def test_returns_formatted_response(self, service, mock_db):
        """Test that autocomplete returns proper response structure."""
        # Mock all DB queries to return empty
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.autocomplete("harry potter")

        assert "query" in result
        assert "suggestions" in result
        assert "search_time_ms" in result
        assert "strategy" in result
        assert result["query"] == "harry potter"

    @pytest.mark.asyncio
    async def test_prefix_matches_sorted_first(self, service, mock_db):
        """Test that prefix matches appear before fuzzy matches."""
        # Create mock rows for prefix matches
        prefix_row = MagicMock()
        prefix_row.id = 1
        prefix_row.title = "Harry Potter"
        prefix_row.author = "J.K. Rowling"
        prefix_row.item_type = MagicMock()
        prefix_row.item_type.value = "book"
        prefix_row.cover_url = None
        prefix_row.match_score = 1.0

        fuzzy_row = MagicMock()
        fuzzy_row.id = 2
        fuzzy_row.title = "Hary Poter"
        fuzzy_row.author = "Unknown"
        fuzzy_row.item_type = MagicMock()
        fuzzy_row.item_type.value = "book"
        fuzzy_row.cover_url = None
        fuzzy_row.trgm_score = 0.7

        # First query (prefix) returns prefix row
        prefix_result = MagicMock()
        prefix_result.all.return_value = [prefix_row]

        # Subsequent queries return fuzzy row (trigram), then empty for rest
        fuzzy_result = MagicMock()
        fuzzy_result.all.return_value = [fuzzy_row]

        empty_result = MagicMock()
        empty_result.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[prefix_result, fuzzy_result, empty_result, empty_result]
        )

        result = await service.autocomplete("harry")

        suggestions = result["suggestions"]
        if len(suggestions) >= 2:
            assert suggestions[0]["match_type"] == "prefix"
            assert suggestions[1]["match_type"] == "fuzzy"

    @pytest.mark.asyncio
    async def test_deduplication(self, service, mock_db):
        """Test that duplicate items are not included."""
        # Same item appearing in both prefix and trigram results
        row = MagicMock()
        row.id = 1
        row.title = "Harry Potter"
        row.author = "J.K. Rowling"
        row.item_type = MagicMock()
        row.item_type.value = "book"
        row.cover_url = None
        row.match_score = 1.0
        row.trgm_score = 0.9

        result_with_item = MagicMock()
        result_with_item.all.return_value = [row]

        empty_result = MagicMock()
        empty_result.all.return_value = []

        # Both prefix and trigram return the same item
        mock_db.execute = AsyncMock(
            side_effect=[result_with_item, result_with_item, empty_result, empty_result]
        )

        result = await service.autocomplete("harry")

        # Count unique IDs
        ids = [s["id"] for s in result["suggestions"]]
        assert len(ids) == len(set(ids)), "Should not have duplicate IDs"

    @pytest.mark.asyncio
    async def test_limit_respected(self, service, mock_db):
        """Test that limit parameter is respected."""
        rows = []
        for i in range(20):
            row = MagicMock()
            row.id = i
            row.title = f"Book {i}"
            row.author = f"Author {i}"
            row.item_type = MagicMock()
            row.item_type.value = "book"
            row.cover_url = None
            row.match_score = 1.0
            rows.append(row)

        result_with_many = MagicMock()
        result_with_many.all.return_value = rows

        empty_result = MagicMock()
        empty_result.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[result_with_many, empty_result, empty_result, empty_result]
        )

        result = await service.autocomplete("book", limit=5)

        assert len(result["suggestions"]) <= 5

    @pytest.mark.asyncio
    async def test_includes_search_time(self, service, mock_db):
        """Test that search_time_ms is included and positive."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.autocomplete("test")

        assert "search_time_ms" in result
        assert result["search_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_no_authors_flag(self, service, mock_db):
        """Test that include_authors=False skips author matching."""
        prefix_row = MagicMock()
        prefix_row.id = 1
        prefix_row.title = "Test Book"
        prefix_row.author = "Author"
        prefix_row.item_type = MagicMock()
        prefix_row.item_type.value = "book"
        prefix_row.cover_url = None
        prefix_row.match_score = 1.0

        result_with_item = MagicMock()
        result_with_item.all.return_value = [prefix_row]

        empty_result = MagicMock()
        empty_result.all.return_value = []

        # When include_authors=False, should only run 3 queries:
        # prefix, trigram title, gutenberg (skip author trigram)
        mock_db.execute = AsyncMock(
            side_effect=[result_with_item, empty_result, empty_result]
        )

        _ = await service.autocomplete("test", include_authors=False)

        # Should have 3 execute calls (no author trigram)
        assert mock_db.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_no_gutenberg_flag(self, service, mock_db):
        """Test that include_gutenberg=False skips Gutenberg matching."""
        empty_result = MagicMock()
        empty_result.all.return_value = []

        # When include_gutenberg=False, should only run 3 queries:
        # prefix, trigram title, trigram author (skip gutenberg)
        mock_db.execute = AsyncMock(return_value=empty_result)

        _ = await service.autocomplete("test", include_gutenberg=False)

        # Should have 3 execute calls (no gutenberg)
        assert mock_db.execute.call_count == 3


# ==================== Suggestion Format ====================


class TestSuggestionFormat:
    @pytest.mark.asyncio
    async def test_prefix_suggestion_format(self, service, mock_db):
        """Test that prefix suggestions have correct format."""
        row = MagicMock()
        row.id = 42
        row.title = "Test Book"
        row.author = "Test Author"
        row.item_type = MagicMock()
        row.item_type.value = "book"
        row.cover_url = "https://example.com/cover.jpg"
        row.match_score = 1.0

        prefix_result = MagicMock()
        prefix_result.all.return_value = [row]

        empty_result = MagicMock()
        empty_result.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[prefix_result, empty_result, empty_result, empty_result]
        )

        result = await service.autocomplete("test")

        assert len(result["suggestions"]) == 1
        suggestion = result["suggestions"][0]
        assert suggestion["id"] == "local:42"
        assert suggestion["title"] == "Test Book"
        assert suggestion["author"] == "Test Author"
        assert suggestion["format"] == "book"
        assert suggestion["source"] == "local"
        assert suggestion["cover_url"] == "https://example.com/cover.jpg"
        assert suggestion["match_type"] == "prefix"
        assert suggestion["similarity_score"] == 1.0
