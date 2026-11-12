# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_chunk(chunk_id: int, text: str, chunk_index: int = 0):
    chunk = MagicMock()
    chunk.id = chunk_id
    chunk.chunk_text = text
    chunk.chunk_index = chunk_index
    return chunk


def make_db_with_chunks(chunks):
    """Return a mock AsyncSession whose execute() yields the given chunks."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = chunks
    db.execute = AsyncMock(return_value=mock_result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


# SemanticSearchService is imported inside the method body, so we patch
# it on the semantic_search_service module directly.
SSS_PATH = "app.services.semantic_search_service.SemanticSearchService"


# ---------------------------------------------------------------------------
# _generate_chunk_embeddings tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_chunk_embeddings_creates_records():
    """TextEmbedding records are added for each chunk that returns an embedding."""
    from app.services.document_processing_service import DocumentProcessingService

    chunk_text = "This is a sample chunk of library document text."
    chunks = [make_chunk(chunk_id=42, text=chunk_text, chunk_index=0)]
    db = make_db_with_chunks(chunks)

    fake_embedding = [0.1] * 768
    service = DocumentProcessingService(db)

    mock_ss_instance = AsyncMock()
    mock_ss_instance.generate_embedding = AsyncMock(return_value=fake_embedding)

    with patch(SSS_PATH, return_value=mock_ss_instance):
        await service._generate_chunk_embeddings(db, document_id=1)

    assert db.add.call_count == 1
    record = db.add.call_args[0][0]

    from app.models.embeddings import TextEmbedding
    assert isinstance(record, TextEmbedding)
    assert record.entity_type == "library_document"
    assert record.entity_id == 42
    assert record.source_collection == "library_documents"
    assert record.text_content == chunk_text[:2000]
    assert record.embedding == fake_embedding
    assert record.embedding_model == "nomic-embed-text"
    assert record.embedding_dimension == len(fake_embedding)
    assert record.text_hash == hashlib.sha256(chunk_text.encode()).hexdigest()
    assert record.is_generated is True
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_chunk_embeddings_skips_failed_embeddings():
    """Chunks where generate_embedding returns None are skipped gracefully."""
    from app.services.document_processing_service import DocumentProcessingService

    chunks = [
        make_chunk(chunk_id=10, text="chunk one", chunk_index=0),
        make_chunk(chunk_id=11, text="chunk two", chunk_index=1),
    ]
    db = make_db_with_chunks(chunks)
    service = DocumentProcessingService(db)

    mock_ss_instance = AsyncMock()
    mock_ss_instance.generate_embedding = AsyncMock(
        side_effect=[None, [0.2] * 768]
    )

    with patch(SSS_PATH, return_value=mock_ss_instance):
        await service._generate_chunk_embeddings(db, document_id=2)

    assert db.add.call_count == 1
    record = db.add.call_args[0][0]
    assert record.entity_id == 11


@pytest.mark.asyncio
async def test_generate_chunk_embeddings_no_chunks():
    """No records are created and no error is raised when there are no chunks."""
    from app.services.document_processing_service import DocumentProcessingService

    db = make_db_with_chunks([])
    service = DocumentProcessingService(db)

    mock_ss_instance = AsyncMock()

    with patch(SSS_PATH, return_value=mock_ss_instance) as MockSS:
        await service._generate_chunk_embeddings(db, document_id=99)

    db.add.assert_not_called()
    db.commit.assert_not_awaited()
    MockSS.assert_not_called()


@pytest.mark.asyncio
async def test_generate_chunk_embeddings_exception_does_not_propagate():
    """An exception inside _generate_chunk_embeddings is swallowed."""
    from app.services.document_processing_service import DocumentProcessingService

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=RuntimeError("db exploded"))
    service = DocumentProcessingService(db)

    # Should not raise
    await service._generate_chunk_embeddings(db, document_id=5)


# ---------------------------------------------------------------------------
# ingest_text calls _generate_chunk_embeddings
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ingest_text_calls_generate_chunk_embeddings():
    """_generate_chunk_embeddings is called after ingest_text completes."""
    from app.services.document_processing_service import DocumentProcessingService

    fake_doc = MagicMock()
    fake_doc.id = 7

    db = AsyncMock()
    service = DocumentProcessingService(db)

    with patch.object(
        service, "_create_document", new=AsyncMock(return_value=fake_doc)
    ) as mock_create, patch.object(
        service, "_generate_chunk_embeddings", new=AsyncMock()
    ) as mock_embed:
        result = await service.ingest_text(
            text="Some document text here.",
            title="Test Doc",
            document_type="policy",
            uploaded_by_id=1,
        )

    mock_create.assert_awaited_once()
    mock_embed.assert_awaited_once_with(service.db, 7)
    assert result is fake_doc


# ---------------------------------------------------------------------------
# ingest_pdf calls _generate_chunk_embeddings
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ingest_pdf_calls_generate_chunk_embeddings():
    """_generate_chunk_embeddings is called after ingest_pdf completes."""
    from app.services.document_processing_service import DocumentProcessingService

    fake_doc = MagicMock()
    fake_doc.id = 8

    db = AsyncMock()
    service = DocumentProcessingService(db)

    fake_extracted = {
        "text": "Extracted PDF text.",
        "pages": ["Extracted PDF text."],
        "page_count": 1,
    }

    with patch(
        "app.services.document_processing_service.extract_text_from_pdf",
        return_value=fake_extracted,
    ), patch.object(
        service, "_create_document", new=AsyncMock(return_value=fake_doc)
    ) as mock_create, patch.object(
        service, "_generate_chunk_embeddings", new=AsyncMock()
    ) as mock_embed:
        result = await service.ingest_pdf(
            file_bytes=b"%PDF-1.4 fake",
            filename="test.pdf",
            title="Test PDF",
            document_type="report",
            uploaded_by_id=1,
        )

    mock_create.assert_awaited_once()
    mock_embed.assert_awaited_once_with(service.db, 8)
    assert result is fake_doc
