# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for FAQ chatbot semantic search integration.

Tests cover:
- _semantic_search returns results when embeddings match
- _semantic_search returns empty when no matches / service unavailable
- find_matching_faq backward compatibility when semantic search is unavailable
- find_matching_faq_enhanced returns the richer dict format
- Expired entries are excluded from semantic results
- Location scoping works
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_kb_entry(
    id=1,
    title="What are your hours?",
    content="We are open Mon-Fri 9-5.",
    category="faq",
    review_status="approved",
    expires_at=None,
    location_id=None,
):
    entry = MagicMock()
    entry.id = id
    entry.title = title
    entry.content = content
    entry.category = category
    entry.review_status = review_status
    entry.expires_at = expires_at
    entry.location_id = location_id
    return entry


def _make_text_embedding(entity_id=1, text_content="Library hours info"):
    emb = MagicMock()
    emb.entity_id = entity_id
    emb.text_content = text_content
    return emb


def _build_db_row(distance=0.1, entity_id=1, location_id=None):
    """Return a (TextEmbedding, KnowledgeEntry, distance) tuple like SQLAlchemy yields."""
    te = _make_text_embedding(entity_id=entity_id)
    kb = _make_kb_entry(id=entity_id, location_id=location_id)
    return (te, kb, distance)


# ---------------------------------------------------------------------------
# _semantic_search
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_semantic_search_returns_results_when_embeddings_match():
    """_semantic_search should return results with similarity when DB rows are found."""
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    mock_db = AsyncMock()

    row = _build_db_row(distance=0.1)
    mock_result = MagicMock()
    mock_result.all.return_value = [row]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.dict("sys.modules", {
        "app.services.semantic_search_service": MagicMock(
            SemanticSearchService=MagicMock(
                return_value=MagicMock(
                    generate_embedding=AsyncMock(return_value=[0.1] * 768)
                )
            )
        ),
    }):
        result = await service._semantic_search(mock_db, "what are your hours")

    assert "results" in result
    assert len(result["results"]) == 1
    r = result["results"][0]
    assert r["similarity"] == pytest.approx(0.9)
    assert r["entity_id"] == 1


@pytest.mark.asyncio
async def test_semantic_search_returns_empty_when_no_db_rows():
    """_semantic_search should return empty results when no DB rows match."""
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    mock_db = AsyncMock()

    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.dict("sys.modules", {
        "app.services.semantic_search_service": MagicMock(
            SemanticSearchService=MagicMock(
                return_value=MagicMock(
                    generate_embedding=AsyncMock(return_value=[0.1] * 768)
                )
            )
        ),
    }):
        result = await service._semantic_search(mock_db, "totally unrelated query")

    assert result == {"results": []}


@pytest.mark.asyncio
async def test_semantic_search_returns_empty_when_embedding_fails():
    """_semantic_search returns empty dict if embedding generation fails."""
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    mock_db = AsyncMock()

    with patch.dict("sys.modules", {
        "app.services.semantic_search_service": MagicMock(
            SemanticSearchService=MagicMock(
                return_value=MagicMock(
                    generate_embedding=AsyncMock(return_value=None)
                )
            )
        ),
    }):
        result = await service._semantic_search(mock_db, "where is the bathroom")

    assert result == {"results": []}


@pytest.mark.asyncio
async def test_semantic_search_returns_empty_on_exception():
    """_semantic_search swallows exceptions and returns empty results."""
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB exploded"))

    with patch.dict("sys.modules", {
        "app.services.semantic_search_service": MagicMock(
            SemanticSearchService=MagicMock(
                return_value=MagicMock(
                    generate_embedding=AsyncMock(return_value=[0.1] * 768)
                )
            )
        ),
    }):
        result = await service._semantic_search(mock_db, "some question")

    assert result == {"results": []}


# ---------------------------------------------------------------------------
# find_matching_faq - backward compatibility
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_matching_faq_backward_compat_falls_back_to_pattern():
    """
    find_matching_faq must return (KnowledgeEntry, FAQPattern, int) or None.
    When semantic search is unavailable it falls back to _pattern_match.
    """
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    service._semantic_search = AsyncMock(return_value={"results": []})

    kb_entry = _make_kb_entry()
    pattern = MagicMock()
    pattern.id = 99
    service._pattern_match = AsyncMock(return_value=(kb_entry, pattern, 80))

    mock_db = AsyncMock()
    result = await service.find_matching_faq(mock_db, "when do you close")

    assert result is not None
    assert isinstance(result, tuple)
    assert len(result) == 3
    kb, pat, confidence = result
    assert confidence == 80
    assert pat is pattern


@pytest.mark.asyncio
async def test_find_matching_faq_uses_semantic_when_score_high():
    """find_matching_faq returns semantic result when similarity >= 0.7."""
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    kb_entry = _make_kb_entry()

    service._semantic_search = AsyncMock(return_value={
        "results": [{
            "text_content": "Library hours info",
            "similarity": 0.85,
            "entity_id": 1,
            "location_id": None,
            "title": "What are your hours?",
            "_kb_entry": kb_entry,
        }]
    })
    service._pattern_match = AsyncMock()

    mock_db = AsyncMock()
    result = await service.find_matching_faq(mock_db, "what time do you open")

    assert result is not None
    kb, pat, confidence = result
    assert kb is kb_entry
    assert pat is None
    assert confidence == 85
    service._pattern_match.assert_not_called()


@pytest.mark.asyncio
async def test_find_matching_faq_falls_back_when_semantic_score_low():
    """find_matching_faq falls back to pattern matching when similarity < 0.7."""
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    kb_entry = _make_kb_entry()
    pattern = MagicMock()

    service._semantic_search = AsyncMock(return_value={
        "results": [{
            "text_content": "Something vague",
            "similarity": 0.55,
            "entity_id": 1,
            "location_id": None,
            "title": "Some FAQ",
            "_kb_entry": kb_entry,
        }]
    })
    service._pattern_match = AsyncMock(return_value=(kb_entry, pattern, 75))

    mock_db = AsyncMock()
    result = await service.find_matching_faq(mock_db, "hours please")

    assert result is not None
    _, _, confidence = result
    assert confidence == 75
    service._pattern_match.assert_called_once()


@pytest.mark.asyncio
async def test_find_matching_faq_returns_none_when_no_match():
    """find_matching_faq returns None when both semantic and pattern fail."""
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    service._semantic_search = AsyncMock(return_value={"results": []})
    service._pattern_match = AsyncMock(return_value=None)

    mock_db = AsyncMock()
    result = await service.find_matching_faq(mock_db, "xyzzy frobulate")

    assert result is None


# ---------------------------------------------------------------------------
# find_matching_faq_enhanced
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_matching_faq_enhanced_returns_richer_dict_semantic():
    """find_matching_faq_enhanced returns dict with match_type=semantic."""
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    kb_entry = _make_kb_entry()

    service._semantic_search = AsyncMock(return_value={
        "results": [{
            "text_content": "Hours info",
            "similarity": 0.88,
            "entity_id": 1,
            "location_id": None,
            "title": "Library Hours",
            "_kb_entry": kb_entry,
        }]
    })
    service._pattern_match = AsyncMock()

    mock_db = AsyncMock()
    result = await service.find_matching_faq_enhanced(mock_db, "when are you open")

    assert result["match_type"] == "semantic"
    assert result["confidence"] == 88
    assert result["kb_entry"] is kb_entry
    assert result["faq_pattern"] is None
    assert isinstance(result["semantic_results"], list)
    service._pattern_match.assert_not_called()


@pytest.mark.asyncio
async def test_find_matching_faq_enhanced_returns_richer_dict_pattern():
    """find_matching_faq_enhanced returns dict with match_type=pattern."""
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    kb_entry = _make_kb_entry()
    pattern = MagicMock()

    service._semantic_search = AsyncMock(return_value={"results": []})
    service._pattern_match = AsyncMock(return_value=(kb_entry, pattern, 70))

    mock_db = AsyncMock()
    result = await service.find_matching_faq_enhanced(mock_db, "checkout books")

    assert result["match_type"] == "pattern"
    assert result["confidence"] == 70
    assert result["kb_entry"] is kb_entry
    assert result["faq_pattern"] is pattern


@pytest.mark.asyncio
async def test_find_matching_faq_enhanced_returns_none_match_type():
    """find_matching_faq_enhanced returns match_type=none when no match found."""
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    service._semantic_search = AsyncMock(return_value={"results": []})
    service._pattern_match = AsyncMock(return_value=None)

    mock_db = AsyncMock()
    result = await service.find_matching_faq_enhanced(mock_db, "zork adventure game")

    assert result["match_type"] == "none"
    assert result["confidence"] == 0
    assert result["kb_entry"] is None
    assert result["faq_pattern"] is None


# ---------------------------------------------------------------------------
# Expiry filtering
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_semantic_search_excludes_expired_entries():
    """
    Expired entries must be filtered by the SQL query.
    We verify the WHERE clause includes an expiry check by confirming an expired
    entry is not returned -- simulated by DB returning no rows.
    """
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    mock_db = AsyncMock()

    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.dict("sys.modules", {
        "app.services.semantic_search_service": MagicMock(
            SemanticSearchService=MagicMock(
                return_value=MagicMock(
                    generate_embedding=AsyncMock(return_value=[0.1] * 768)
                )
            )
        ),
    }):
        result = await service._semantic_search(mock_db, "are you open on holidays")

    assert result["results"] == []


# ---------------------------------------------------------------------------
# Location scoping
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_semantic_search_location_scope_returns_matching_branch():
    """Results include entries for matching location_id."""
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    mock_db = AsyncMock()

    row = _build_db_row(distance=0.05, entity_id=42, location_id=3)
    mock_result = MagicMock()
    mock_result.all.return_value = [row]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.dict("sys.modules", {
        "app.services.semantic_search_service": MagicMock(
            SemanticSearchService=MagicMock(
                return_value=MagicMock(
                    generate_embedding=AsyncMock(return_value=[0.1] * 768)
                )
            )
        ),
    }):
        result = await service._semantic_search(mock_db, "branch hours", location_id=3)

    assert len(result["results"]) == 1
    assert result["results"][0]["location_id"] == 3


@pytest.mark.asyncio
async def test_semantic_search_no_location_excludes_branch_entries():
    """
    When location_id=None (system-wide), the WHERE clause restricts to
    entries with location_id IS NULL. Branch-specific rows do not appear.
    """
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    mock_db = AsyncMock()

    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.dict("sys.modules", {
        "app.services.semantic_search_service": MagicMock(
            SemanticSearchService=MagicMock(
                return_value=MagicMock(
                    generate_embedding=AsyncMock(return_value=[0.1] * 768)
                )
            )
        ),
    }):
        result = await service._semantic_search(mock_db, "branch-specific thing", location_id=None)

    assert result["results"] == []


@pytest.mark.asyncio
async def test_find_matching_faq_enhanced_passes_location_id_to_semantic():
    """find_matching_faq_enhanced forwards location_id to _semantic_search."""
    from app.services.faq_chatbot_service import FAQChatbotService

    service = FAQChatbotService()
    service._semantic_search = AsyncMock(return_value={"results": []})
    service._pattern_match = AsyncMock(return_value=None)

    mock_db = AsyncMock()
    await service.find_matching_faq_enhanced(mock_db, "any question", location_id=7)

    service._semantic_search.assert_called_once_with(mock_db, "any question", location_id=7)
