# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for KnowledgePipelineService."""

import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(**kwargs):
    entry = MagicMock()
    entry.id = kwargs.get("id", 1)
    entry.title = kwargs.get("title", "Test title")
    entry.content = kwargs.get("content", "Test content")
    entry.category = kwargs.get("category", "faq")
    entry.version = kwargs.get("version", 1)
    entry.persona_domain = kwargs.get("persona_domain", None)
    entry.embedding_id = None
    entry.updated_at = None
    return entry


def _make_db():
    """Return a mock AsyncSession where db.add is synchronous and db.flush is async."""
    db = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock()
    # add() is synchronous in SQLAlchemy
    db.add = MagicMock()
    return db


def _make_service():
    """Create KnowledgePipelineService with SemanticSearchService mocked out."""
    from app.services.knowledge_pipeline_service import KnowledgePipelineService
    svc = KnowledgePipelineService()
    fake_ss = MagicMock()
    fake_ss.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
    fake_ss.embedding_model = "test-model"
    svc._semantic_search = MagicMock(return_value=fake_ss)
    return svc, fake_ss


# ---------------------------------------------------------------------------
# ingest_manual
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ingest_manual_creates_approved_entry():
    svc, _ = _make_service()
    svc.generate_and_store_embedding = AsyncMock(return_value=None)
    svc.create_version = AsyncMock(return_value=MagicMock())

    db = _make_db()
    captured = {}

    def _add(obj):
        obj.id = 42
        captured["entry"] = obj

    db.add.side_effect = _add

    result = await svc.ingest_manual(
        db,
        title="How do I renew?",
        content="You can renew online.",
        category="faq",
        added_by_name="Alice",
    )

    assert result is not None
    assert captured["entry"].source_type == "manual"
    assert captured["entry"].review_status == "approved"
    svc.generate_and_store_embedding.assert_awaited_once()
    svc.create_version.assert_awaited_once()


# ---------------------------------------------------------------------------
# ingest_patron_interaction
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ingest_patron_interaction_creates_pending_entry():
    svc, _ = _make_service()
    svc.generate_and_store_embedding = AsyncMock(return_value=None)

    db = _make_db()
    captured = {}

    def _add(obj):
        obj.id = 10
        captured["entry"] = obj

    db.add.side_effect = _add

    await svc.ingest_patron_interaction(
        db,
        title="What time do you close?",
        content="We close at 8pm on weekdays.",
        category="faq",
        satisfaction_signal=True,
    )

    assert captured["entry"].source_type == "patron_interaction"
    assert captured["entry"].review_status == "pending"
    assert captured["entry"].entry_metadata is not None
    assert captured["entry"].entry_metadata.get("satisfaction_signal") is True
    svc.generate_and_store_embedding.assert_awaited_once()


# ---------------------------------------------------------------------------
# ingest_document
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ingest_document_creates_entries_from_qa_pairs():
    from app.models.library_document import LibraryDocument, LibraryDocumentChunk

    svc, _ = _make_service()
    svc.generate_and_store_embedding = AsyncMock(return_value=None)

    fake_doc = MagicMock(spec=LibraryDocument)
    fake_doc.id = 5
    fake_doc.title = "Summer Newsletter"

    fake_chunk = MagicMock(spec=LibraryDocumentChunk)
    fake_chunk.chunk_text = "The library offers free notary services on Tuesdays."
    fake_chunk.chunk_index = 0

    qa_pairs = [
        {"question": "Do you have notary services?", "answer": "Yes, free on Tuesdays."},
        {"question": "When is notary available?", "answer": "Every Tuesday."},
    ]
    svc.qa_extraction.extract_from_chunks = AsyncMock(return_value=qa_pairs)

    added_entries = []

    db = _make_db()

    def _add(obj):
        obj.id = len(added_entries) + 100
        added_entries.append(obj)

    db.add.side_effect = _add

    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = fake_doc
    chunk_result = MagicMock()
    chunk_result.scalars.return_value.all.return_value = [fake_chunk]
    db.execute = AsyncMock(side_effect=[doc_result, chunk_result])

    entries = await svc.ingest_document(db, document_id=5, category="faq")

    assert len(entries) == 2
    for e in entries:
        assert e.source_type == "document_import"
        assert e.source_reference_id == "5"
    assert svc.generate_and_store_embedding.await_count == 2


@pytest.mark.asyncio
async def test_ingest_document_returns_empty_when_not_found():
    svc, _ = _make_service()

    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    entries = await svc.ingest_document(db, document_id=999)
    assert entries == []


# ---------------------------------------------------------------------------
# update_entry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_entry_increments_version():
    svc, _ = _make_service()
    svc.create_version = AsyncMock(return_value=MagicMock())
    svc.generate_and_store_embedding = AsyncMock(return_value=None)

    fake_entry = _make_entry(version=2, content="Old content")

    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = fake_entry
    db.execute = AsyncMock(return_value=result_mock)

    returned = await svc.update_entry(
        db,
        entry_id=1,
        content="New content",
        change_reason="Policy updated",
    )

    assert returned is not None
    assert returned.version == 3
    svc.create_version.assert_awaited_once()
    svc.generate_and_store_embedding.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_entry_no_reembed_when_content_unchanged():
    svc, _ = _make_service()
    svc.create_version = AsyncMock(return_value=MagicMock())
    svc.generate_and_store_embedding = AsyncMock(return_value=None)

    fake_entry = _make_entry(version=1, content="Unchanged content")

    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = fake_entry
    db.execute = AsyncMock(return_value=result_mock)

    await svc.update_entry(
        db,
        entry_id=1,
        tags="new-tag",
        change_reason="Tag update",
    )

    svc.generate_and_store_embedding.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_entry_returns_none_when_not_found():
    svc, _ = _make_service()

    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    result = await svc.update_entry(db, entry_id=9999, title="Anything")
    assert result is None


# ---------------------------------------------------------------------------
# generate_and_store_embedding
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_and_store_embedding_creates_text_embedding_with_hash():
    svc, fake_ss = _make_service()

    entry = _make_entry(title="Hours", content="We open at 9am.")

    stored = {}
    db = _make_db()

    def _add(obj):
        obj.id = 77
        stored["last"] = obj

    db.add.side_effect = _add

    result = await svc.generate_and_store_embedding(db, entry)

    assert result is not None
    emb = stored["last"]
    expected_text = "Hours We open at 9am."
    expected_hash = hashlib.sha256(expected_text.encode()).hexdigest()
    assert emb.text_hash == expected_hash
    assert emb.entity_type == "knowledge_entry"
    assert emb.is_generated is True
    assert entry.embedding_id == 77


@pytest.mark.asyncio
async def test_generate_and_store_embedding_returns_none_on_failure():
    svc, fake_ss = _make_service()
    fake_ss.generate_embedding = AsyncMock(return_value=None)

    entry = _make_entry()
    db = _make_db()

    result = await svc.generate_and_store_embedding(db, entry)
    assert result is None
    db.add.assert_not_called()
