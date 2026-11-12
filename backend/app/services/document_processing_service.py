# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
from app.core.logging import get_logger
import re
from typing import Optional

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.library_document import LibraryDocument, LibraryDocumentChunk

logger = get_logger(__name__)

# Target ~500 words per chunk with ~50 word overlap
CHUNK_TARGET_WORDS = 500
CHUNK_OVERLAP_WORDS = 50


def extract_text_from_pdf(file_bytes: bytes) -> dict:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PyMuPDF (pymupdf) is required for PDF text extraction. "
            "Install it with: pip install pymupdf"
        ) from None

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()

    full_text = "\n\n".join(pages)
    return {
        "text": full_text.strip(),
        "pages": pages,
        "page_count": len(pages),
    }


def chunk_text(
    text: str,
    target_words: int = CHUNK_TARGET_WORDS,
    overlap_words: int = CHUNK_OVERLAP_WORDS,
) -> list[dict]:
    if not text or not text.strip():
        return []

    # Split into paragraphs first, preserving structure
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return []

    chunks = []
    current_words: list[str] = []
    current_paragraphs: list[str] = []

    for para in paragraphs:
        para_words = para.split()

        # If adding this paragraph would exceed target and we have content,
        # finalize the current chunk
        if current_words and len(current_words) + len(para_words) > target_words:
            chunk_text_str = "\n\n".join(current_paragraphs)
            chunks.append({
                "text": chunk_text_str,
                "word_count": len(current_words),
                "chunk_index": len(chunks),
            })

            # Keep overlap from end of current chunk
            if overlap_words > 0 and len(current_words) > overlap_words:
                overlap_text = " ".join(current_words[-overlap_words:])
                current_paragraphs = [overlap_text]
                current_words = current_words[-overlap_words:]
            else:
                current_paragraphs = []
                current_words = []

        current_paragraphs.append(para)
        current_words.extend(para_words)

    # Don't forget the last chunk
    if current_words:
        chunk_text_str = "\n\n".join(current_paragraphs)
        chunks.append({
            "text": chunk_text_str,
            "word_count": len(current_words),
            "chunk_index": len(chunks),
        })

    return chunks


def detect_section_title(chunk_text: str) -> Optional[str]:
    lines = chunk_text.strip().split('\n')
    if not lines:
        return None

    first_line = lines[0].strip()
    # Short lines that look like headings (all caps or title case, < 80 chars)
    if len(first_line) < 80 and first_line:
        if first_line.isupper() or first_line.istitle():
            return first_line

    return None


class DocumentProcessingService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        title: str,
        document_type: str,
        uploaded_by_id: int,
        description: Optional[str] = None,
        publish_date=None,
        tags: Optional[list[str]] = None,
        file_path: Optional[str] = None,
    ) -> LibraryDocument:
        extracted = extract_text_from_pdf(file_bytes)

        if not extracted["text"]:
            raise ValueError("No text could be extracted from the PDF. It may be scanned/image-only.")

        doc = await self._create_document(
            title=title,
            document_type=document_type,
            full_text=extracted["text"],
            uploaded_by_id=uploaded_by_id,
            description=description,
            publish_date=publish_date,
            tags=tags,
            filename=filename,
            file_path=file_path,
            file_size_bytes=len(file_bytes),
            mime_type="application/pdf",
            page_count=extracted["page_count"],
        )
        await self._generate_chunk_embeddings(self.db, doc.id)
        return doc

    async def ingest_text(
        self,
        text: str,
        title: str,
        document_type: str,
        uploaded_by_id: int,
        description: Optional[str] = None,
        publish_date=None,
        tags: Optional[list[str]] = None,
    ) -> LibraryDocument:
        if not text or not text.strip():
            raise ValueError("Text content cannot be empty.")

        doc = await self._create_document(
            title=title,
            document_type=document_type,
            full_text=text.strip(),
            uploaded_by_id=uploaded_by_id,
            description=description,
            publish_date=publish_date,
            tags=tags,
        )
        await self._generate_chunk_embeddings(self.db, doc.id)
        return doc

    async def _create_document(
        self,
        title: str,
        document_type: str,
        full_text: str,
        uploaded_by_id: int,
        description: Optional[str] = None,
        publish_date=None,
        tags: Optional[list[str]] = None,
        filename: Optional[str] = None,
        file_path: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        mime_type: Optional[str] = None,
        page_count: Optional[int] = None,
    ) -> LibraryDocument:
        # Chunk the text
        chunks_data = chunk_text(full_text)

        doc = LibraryDocument(
            title=title,
            document_type=document_type,
            description=description,
            publish_date=publish_date,
            tags=tags or [],
            filename=filename,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            full_text=full_text,
            page_count=page_count,
            chunk_count=len(chunks_data),
            uploaded_by_id=uploaded_by_id,
        )
        self.db.add(doc)
        await self.db.flush()  # Get doc.id

        # Create chunks
        for chunk_data in chunks_data:
            section = detect_section_title(chunk_data["text"])
            chunk = LibraryDocumentChunk(
                document_id=doc.id,
                chunk_index=chunk_data["chunk_index"],
                section_title=section,
                chunk_text=chunk_data["text"],
                word_count=chunk_data["word_count"],
            )
            self.db.add(chunk)

        await self.db.commit()
        await self.db.refresh(doc)

        logger.info(
            "Ingested document '%s' (%s): %d chunks from %d words",
            title, document_type, len(chunks_data),
            sum(c["word_count"] for c in chunks_data),
        )

        return doc


    async def _generate_chunk_embeddings(self, db, document_id: int) -> None:
        from ..models.embeddings import TextEmbedding
        from .semantic_search_service import SemanticSearchService

        try:
            stmt = select(LibraryDocumentChunk).where(
                LibraryDocumentChunk.document_id == document_id
            ).order_by(LibraryDocumentChunk.chunk_index)
            result = await db.execute(stmt)
            chunks = result.scalars().all()

            if not chunks:
                logger.warning("No chunks found for document %d, skipping embedding", document_id)
                return

            search_service = SemanticSearchService(db)
            generated = 0

            for chunk in chunks:
                text_content = chunk.chunk_text[:2000]
                embedding = await search_service.generate_embedding(text_content)
                if embedding is None:
                    logger.warning("Failed to generate embedding for chunk %d", chunk.id)
                    continue

                text_hash = hashlib.sha256(chunk.chunk_text.encode()).hexdigest()

                record = TextEmbedding(
                    entity_type="library_document",
                    entity_id=chunk.id,
                    source_collection="library_documents",
                    text_content=text_content,
                    embedding=embedding,
                    embedding_model="nomic-embed-text",
                    embedding_dimension=len(embedding),
                    text_hash=text_hash,
                    is_generated=True,
                )
                db.add(record)
                generated += 1

            await db.commit()
            logger.info(
                "Generated %d embeddings for document %d", generated, document_id
            )

        except Exception:
            logger.exception(
                "Failed to generate embeddings for document %d; document upload succeeded",
                document_id,
            )

    async def list_documents(
        self,
        document_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        stmt = select(LibraryDocument).order_by(LibraryDocument.created_at.desc())

        if document_type:
            stmt = stmt.where(LibraryDocument.document_type == document_type)

        # Total count
        count_stmt = select(func.count(LibraryDocument.id))
        if document_type:
            count_stmt = count_stmt.where(LibraryDocument.document_type == document_type)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        docs = result.scalars().all()

        return {
            "documents": [d.to_dict() for d in docs],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_document(self, document_id: int) -> Optional[LibraryDocument]:
        stmt = (
            select(LibraryDocument)
            .options(selectinload(LibraryDocument.chunks))
            .where(LibraryDocument.id == document_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_document(self, document_id: int) -> bool:
        from ..models.embeddings import TextEmbedding

        doc = await self.get_document(document_id)
        if not doc:
            return False

        # Delete associated embeddings
        chunk_ids = [c.id for c in doc.chunks]
        if chunk_ids:
            await self.db.execute(
                delete(TextEmbedding).where(
                    TextEmbedding.entity_type == "library_document",
                    TextEmbedding.entity_id.in_(chunk_ids),
                )
            )

        await self.db.delete(doc)
        await self.db.commit()

        logger.info("Deleted document %d and %d chunks", document_id, len(chunk_ids))
        return True

    async def get_document_stats(self) -> dict:
        total_docs = (await self.db.execute(
            select(func.count(LibraryDocument.id))
        )).scalar() or 0

        total_chunks = (await self.db.execute(
            select(func.count(LibraryDocumentChunk.id))
        )).scalar() or 0

        # Count by type
        type_counts_stmt = (
            select(
                LibraryDocument.document_type,
                func.count(LibraryDocument.id),
            )
            .group_by(LibraryDocument.document_type)
        )
        type_results = (await self.db.execute(type_counts_stmt)).all()
        by_type = {row[0]: row[1] for row in type_results}

        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "by_type": by_type,
        }


def get_document_processing_service(db: AsyncSession) -> DocumentProcessingService:
    return DocumentProcessingService(db)
