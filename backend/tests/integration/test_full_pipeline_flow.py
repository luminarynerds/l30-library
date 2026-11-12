# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for the full knowledge pipeline flow.

These tests verify end-to-end behaviour with mocked infrastructure
boundaries (Ollama, pgvector, database).
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ---------------------------------------------------------------------------
# Test 1: Manual entry -> embedding -> FAQ chatbot finds it via semantic search
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manual_entry_to_rag_flow():
    """Full flow: manual entry -> embedding -> FAQ chatbot finds it via semantic search."""
    from app.services.knowledge_pipeline_service import KnowledgePipelineService
    from app.services.faq_chatbot_service import FAQChatbotService

    pipeline = KnowledgePipelineService()
    faq = FAQChatbotService()
    mock_db = AsyncMock()

    # Step 1: Ingest a manual entry (embedding call mocked out)
    with patch.object(pipeline, 'generate_and_store_embedding', new_callable=AsyncMock):
        with patch.object(pipeline, 'create_version', new_callable=AsyncMock):
            entry = await pipeline.ingest_manual(
                db=mock_db,
                title="Fine Policy",
                content="Overdue fines are $0.25 per day, capped at $10 per item.",
                category="policy",
                persona_domain="shared",
                added_by_id=1,
                added_by_name="Sam",
            )

    assert entry.source_type == "manual"
    assert entry.review_status == "approved"
    assert entry.version == 1
    assert entry.title == "Fine Policy"

    # Step 2: FAQ chatbot finds it via semantic search
    mock_kb_entry = MagicMock()
    mock_kb_entry.title = "Fine Policy"
    mock_kb_entry.content = "Overdue fines are $0.25 per day, capped at $10 per item."
    mock_kb_entry.location_id = None

    mock_semantic_results = {"results": [{
        "text_content": "Fine Policy Overdue fines are $0.25 per day, capped at $10 per item.",
        "similarity": 0.91,
        "entity_id": 1,
        "location_id": None,
        "title": "Fine Policy",
        "_kb_entry": mock_kb_entry,
    }]}

    with patch.object(faq, '_semantic_search', new_callable=AsyncMock, return_value=mock_semantic_results):
        result = await faq.find_matching_faq_enhanced(mock_db, "how much are overdue fines?")

    assert result is not None
    assert result["match_type"] == "semantic"
    assert result["confidence"] == 91
    assert result["kb_entry"] is mock_kb_entry


# ---------------------------------------------------------------------------
# Test 2: Patron interactions enter pipeline as pending
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patron_interaction_captured_as_pending():
    """Patron interactions enter pipeline with pending review status."""
    from app.services.knowledge_pipeline_service import KnowledgePipelineService

    pipeline = KnowledgePipelineService()
    mock_db = AsyncMock()

    with patch.object(pipeline, 'generate_and_store_embedding', new_callable=AsyncMock):
        entry = await pipeline.ingest_patron_interaction(
            db=mock_db,
            title="Gardening books question",
            content="Q: Do you have gardening books?\nA: Yes, check Dewey 635.",
            category="patron_qa",
            persona_domain="reference",
            source_reference_id="conv-123",
            # satisfaction_signal is Optional[bool], not a string
            satisfaction_signal=True,
        )

    assert entry.source_type == "patron_interaction"
    assert entry.review_status == "pending"
    assert entry.version == 1
    assert entry.source_reference_id == "conv-123"
    # Satisfaction signal is stored in entry_metadata
    assert entry.entry_metadata is not None
    assert entry.entry_metadata.get("satisfaction_signal") is True


# ---------------------------------------------------------------------------
# Test 3: Document import extracts Q&A pairs via QAExtractionService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_document_import_extracts_qa_pairs():
    """Document import extracts Q&A pairs from chunks and creates pending entries."""
    from app.services.knowledge_pipeline_service import KnowledgePipelineService

    pipeline = KnowledgePipelineService()
    mock_db = AsyncMock()

    # ingest_document does two db.execute calls:
    #   1. select(LibraryDocument) -> scalar_one_or_none -> mock document
    #   2. select(LibraryDocumentChunk) -> scalars().all() -> [chunk]
    mock_document = MagicMock()
    mock_document.id = 1
    mock_document.title = "Borrowing Policy"

    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = mock_document

    mock_chunk = MagicMock()
    mock_chunk.chunk_text = "Patrons may borrow up to 50 items. Loan period is 21 days."

    chunk_result = MagicMock()
    chunk_result.scalars.return_value.all.return_value = [mock_chunk]

    mock_db.execute = AsyncMock(side_effect=[doc_result, chunk_result])

    mock_qa = [{"question": "What is the borrowing limit?", "answer": "50 items"}]

    with patch.object(pipeline, 'generate_and_store_embedding', new_callable=AsyncMock):
        # extract_from_chunks is the method actually called by ingest_document
        with patch.object(pipeline.qa_extraction, 'extract_from_chunks', new_callable=AsyncMock, return_value=mock_qa):
            entries = await pipeline.ingest_document(mock_db, document_id=1, persona_domain="shared")

    assert len(entries) == 1
    assert entries[0].source_type == "document_import"
    assert entries[0].review_status == "pending"
    assert entries[0].title == "What is the borrowing limit?"
    assert entries[0].content == "50 items"


# ---------------------------------------------------------------------------
# Test 4: Synthetic generation respects the 40% cap
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_synthetic_generation_respects_40_percent_cap():
    """Synthetic generation blocks when synthetic entries already exceed 40% of pool."""
    from app.services.synthetic_generation_service import SyntheticGenerationService

    service = SyntheticGenerationService()
    mock_db = AsyncMock()

    # 60 approved total, 25 synthetic -> 25/60 = 41.6% -> over the 40% cap
    mock_db.scalar = AsyncMock(side_effect=[60, 25])

    result = await service._check_ratio(mock_db, "reference")
    assert result is False, "Should block when synthetic ratio exceeds 40%"


@pytest.mark.asyncio
async def test_synthetic_generation_allowed_under_cap():
    """Synthetic generation proceeds when ratio is under 40%."""
    from app.services.synthetic_generation_service import SyntheticGenerationService

    service = SyntheticGenerationService()
    mock_db = AsyncMock()

    # 60 approved total, 20 synthetic -> 20/60 = 33.3% -> under cap
    mock_db.scalar = AsyncMock(side_effect=[60, 20])

    result = await service._check_ratio(mock_db, "reference")
    assert result is True, "Should allow when synthetic ratio is under 40%"


# ---------------------------------------------------------------------------
# Test 5: Version tracking increments on update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_version_tracking_on_update():
    """Updating an entry increments its version and re-embeds changed content."""
    from app.services.knowledge_pipeline_service import KnowledgePipelineService

    pipeline = KnowledgePipelineService()
    mock_db = AsyncMock()

    mock_entry = MagicMock()
    mock_entry.id = 1
    mock_entry.version = 1
    mock_entry.title = "Old Title"
    mock_entry.content = "Old content"
    mock_entry.category = "policy"
    mock_entry.persona_domain = "shared"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_entry
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.object(pipeline, 'generate_and_store_embedding', new_callable=AsyncMock) as mock_embed:
        with patch.object(pipeline, 'create_version', new_callable=AsyncMock) as mock_version:
            updated = await pipeline.update_entry(
                mock_db,
                entry_id=1,
                changed_by_id=1,
                changed_by_name="Sam",
                change_reason="Updated policy",
                title="New Title",
                content="New content",
            )

    # Version should have been bumped
    assert updated.version == 2
    # Content changed, so embedding should be regenerated
    mock_embed.assert_called_once()
    # Version history should be recorded
    mock_version.assert_called_once()


@pytest.mark.asyncio
async def test_version_not_reembedded_when_content_unchanged():
    """Updating only metadata (no title/content change) does not re-embed."""
    from app.services.knowledge_pipeline_service import KnowledgePipelineService

    pipeline = KnowledgePipelineService()
    mock_db = AsyncMock()

    mock_entry = MagicMock()
    mock_entry.id = 2
    mock_entry.version = 3
    mock_entry.title = "Same Title"
    mock_entry.content = "Same content"
    mock_entry.category = "policy"
    mock_entry.persona_domain = "shared"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_entry
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.object(pipeline, 'generate_and_store_embedding', new_callable=AsyncMock) as mock_embed:
        with patch.object(pipeline, 'create_version', new_callable=AsyncMock):
            await pipeline.update_entry(
                mock_db,
                entry_id=2,
                changed_by_id=1,
                changed_by_name="Sam",
                change_reason="Status change only",
                review_status="approved",
                # title and content deliberately omitted — no content change
            )

    mock_embed.assert_not_called()


# ---------------------------------------------------------------------------
# Test 6: FAQ chatbot falls back to pattern matching when semantic fails
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_faq_chatbot_falls_back_to_pattern_matching():
    """When semantic search returns nothing, chatbot falls back to pattern matching."""
    from app.services.faq_chatbot_service import FAQChatbotService

    faq = FAQChatbotService()
    mock_db = AsyncMock()

    with patch.object(faq, '_semantic_search', new_callable=AsyncMock, return_value={"results": []}) as mock_semantic:
        with patch.object(faq, '_pattern_match', new_callable=AsyncMock, return_value=None) as mock_pattern:
            result = await faq.find_matching_faq(mock_db, "some obscure question")

    # Semantic was tried first
    mock_semantic.assert_called_once()
    # Pattern match was attempted after semantic returned nothing
    mock_pattern.assert_called_once()
    # Both returned nothing -> None result
    assert result is None


@pytest.mark.asyncio
async def test_faq_chatbot_enhanced_falls_back_to_pattern():
    """find_matching_faq_enhanced returns match_type='pattern' when semantic finds nothing."""
    from app.services.faq_chatbot_service import FAQChatbotService

    faq = FAQChatbotService()
    mock_db = AsyncMock()

    mock_kb_entry = MagicMock()
    mock_kb_entry.title = "Library Hours"

    # Semantic below threshold, pattern match succeeds
    with patch.object(faq, '_semantic_search', new_callable=AsyncMock, return_value={"results": []}):
        with patch.object(faq, '_pattern_match', new_callable=AsyncMock,
                          return_value=(mock_kb_entry, None, 75)):
            result = await faq.find_matching_faq_enhanced(mock_db, "when are you open?")

    assert result["match_type"] == "pattern"
    assert result["confidence"] == 75
    assert result["kb_entry"] is mock_kb_entry


@pytest.mark.asyncio
async def test_faq_chatbot_enhanced_returns_none_match_type_when_both_fail():
    """find_matching_faq_enhanced returns match_type='none' when both search paths fail."""
    from app.services.faq_chatbot_service import FAQChatbotService

    faq = FAQChatbotService()
    mock_db = AsyncMock()

    with patch.object(faq, '_semantic_search', new_callable=AsyncMock, return_value={"results": []}):
        with patch.object(faq, '_pattern_match', new_callable=AsyncMock, return_value=None):
            result = await faq.find_matching_faq_enhanced(mock_db, "some question")

    assert result["match_type"] == "none"
    assert result["confidence"] == 0
    assert result["kb_entry"] is None
