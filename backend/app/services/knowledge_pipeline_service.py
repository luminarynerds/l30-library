# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeEntry
from app.models.knowledge_version import KnowledgeVersion
from app.models.embeddings import TextEmbedding
from app.models.library_document import LibraryDocument, LibraryDocumentChunk
from app.services.semantic_search_service import SemanticSearchService
from app.services.qa_extraction_service import QAExtractionService
from app.services.anonymization_service import AnonymizationService

logger = get_logger(__name__)


class KnowledgePipelineService:

    def __init__(self):
        self.qa_extraction = QAExtractionService()
        self.anonymizer = AnonymizationService()

    def _semantic_search(self, db: AsyncSession) -> SemanticSearchService:
        return SemanticSearchService(db)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def generate_and_store_embedding(
        self, db: AsyncSession, entry: KnowledgeEntry
    ) -> Optional[TextEmbedding]:
        try:
            text = f"{entry.title} {entry.content}".strip()
            if not text:
                return None

            svc = self._semantic_search(db)
            vector = await svc.generate_embedding(text)
            if vector is None:
                logger.warning("generate_embedding returned None for entry %s", entry.id)
                return None

            text_hash = hashlib.sha256(text.encode()).hexdigest()

            embedding_row = TextEmbedding(
                entity_type="knowledge_entry",
                entity_id=entry.id,
                text_content=text,
                text_hash=text_hash,
                embedding=vector,
                embedding_model=svc.embedding_model,
                embedding_dimension=len(vector),
                is_generated=True,
                generated_at=datetime.now(timezone.utc),
            )
            db.add(embedding_row)
            await db.flush()

            entry.embedding_id = embedding_row.id
            await db.flush()

            return embedding_row

        except Exception:
            logger.exception("Failed to generate/store embedding for entry %s", entry.id)
            return None

    async def create_version(
        self,
        db: AsyncSession,
        entry: KnowledgeEntry,
        changed_by_id: Optional[int] = None,
        changed_by_name: Optional[str] = None,
        change_reason: Optional[str] = None,
        previous_content: Optional[str] = None,
    ) -> KnowledgeVersion:
        version = KnowledgeVersion(
            knowledge_entry_id=entry.id,
            version_number=entry.version,
            title=entry.title,
            content=entry.content,
            category=entry.category,
            persona_domain=entry.persona_domain,
            changed_by_id=changed_by_id,
            changed_by_name=changed_by_name,
            change_reason=change_reason,
            previous_content=previous_content,
        )
        db.add(version)
        await db.flush()
        return version

    # ------------------------------------------------------------------
    # Ingestion paths
    # ------------------------------------------------------------------

    async def ingest_manual(
        self,
        db: AsyncSession,
        *,
        title: str,
        content: str,
        category: str,
        added_by_id: Optional[int] = None,
        added_by_name: Optional[str] = None,
        tags: Optional[str] = None,
        persona_domain: Optional[str] = None,
        location_id: Optional[int] = None,
        expires_at=None,
        entry_metadata: Optional[dict] = None,
    ) -> KnowledgeEntry:
        entry = KnowledgeEntry(
            title=title,
            content=content,
            category=category,
            tags=tags,
            added_by_id=added_by_id,
            added_by_name=added_by_name,
            persona_domain=persona_domain,
            location_id=location_id,
            expires_at=expires_at,
            entry_metadata=entry_metadata,
            source_type="manual",
            review_status="approved",
            version=1,
        )
        db.add(entry)
        await db.flush()

        await self.generate_and_store_embedding(db, entry)
        await self.create_version(
            db, entry,
            changed_by_id=added_by_id,
            changed_by_name=added_by_name,
            change_reason="Initial manual entry",
        )

        return entry

    async def ingest_patron_interaction(
        self,
        db: AsyncSession,
        *,
        title: str,
        content: str,
        category: str,
        source_reference_id: Optional[str] = None,
        satisfaction_signal: Optional[bool] = None,
        persona_domain: Optional[str] = None,
        location_id: Optional[int] = None,
        entry_metadata: Optional[dict] = None,
        patron_id: Optional[int] = None,
    ) -> Optional[KnowledgeEntry]:
        # Check patron opt-out
        if patron_id is not None:
            from app.models.patron_training_opt_out import PatronTrainingOptOut
            opt_out_result = await db.execute(
                select(PatronTrainingOptOut).where(PatronTrainingOptOut.patron_id == patron_id)
            )
            opt_out = opt_out_result.scalar_one_or_none()
            if opt_out and opt_out.is_opted_out:
                logger.info("Patron %d opted out of training data capture", patron_id)
                return None

        # Anonymize PII before storage
        try:
            title_result = await self.anonymizer.anonymize(title)
            content_result = await self.anonymizer.anonymize(content)
            title = title_result.cleaned_text
            content = content_result.cleaned_text
            pii_types = sorted(set(title_result.detected_pii_types + content_result.detected_pii_types))
        except Exception:
            logger.exception("Anonymization failed, storing raw text")
            pii_types = []

        meta = dict(entry_metadata or {})
        if satisfaction_signal is not None:
            meta["satisfaction_signal"] = satisfaction_signal
        if pii_types:
            meta["anonymized_pii_types"] = pii_types
            meta["anonymized"] = True

        entry = KnowledgeEntry(
            title=title,
            content=content,
            category=category,
            persona_domain=persona_domain,
            location_id=location_id,
            source_type="patron_interaction",
            review_status="pending",
            source_reference_id=source_reference_id,
            entry_metadata=meta or None,
            version=1,
        )
        db.add(entry)
        await db.flush()

        await self.generate_and_store_embedding(db, entry)

        return entry

    async def ingest_document(
        self,
        db: AsyncSession,
        document_id: int,
        *,
        category: str = "faq",
        persona_domain: Optional[str] = None,
        location_id: Optional[int] = None,
    ) -> list[KnowledgeEntry]:
        result = await db.execute(
            select(LibraryDocument).where(LibraryDocument.id == document_id)
        )
        document = result.scalar_one_or_none()
        if document is None:
            logger.error("Document %s not found", document_id)
            return []

        chunk_result = await db.execute(
            select(LibraryDocumentChunk)
            .where(LibraryDocumentChunk.document_id == document_id)
            .order_by(LibraryDocumentChunk.chunk_index)
        )
        chunks = chunk_result.scalars().all()
        if not chunks:
            logger.warning("Document %s has no chunks", document_id)
            return []

        chunk_texts = [c.chunk_text for c in chunks]
        qa_pairs = await self.qa_extraction.extract_from_chunks(chunk_texts)

        entries = []
        for pair in qa_pairs:
            question = pair.get("question", "").strip()
            answer = pair.get("answer", "").strip()
            if not question or not answer:
                continue

            entry = KnowledgeEntry(
                title=question,
                content=answer,
                category=category,
                persona_domain=persona_domain,
                location_id=location_id,
                source_type="document_import",
                review_status="pending",
                source_reference_id=str(document_id),
                entry_metadata={"source_document_id": document_id, "document_title": document.title},
                version=1,
            )
            db.add(entry)
            await db.flush()
            await self.generate_and_store_embedding(db, entry)
            entries.append(entry)

        return entries

    async def update_entry(
        self,
        db: AsyncSession,
        entry_id: int,
        *,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[str] = None,
        review_status: Optional[str] = None,
        persona_domain: Optional[str] = None,
        changed_by_id: Optional[int] = None,
        changed_by_name: Optional[str] = None,
        change_reason: Optional[str] = None,
    ) -> Optional[KnowledgeEntry]:
        result = await db.execute(
            select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            logger.error("KnowledgeEntry %s not found", entry_id)
            return None

        previous_content = entry.content
        content_changed = False

        if title is not None and title != entry.title:
            entry.title = title
            content_changed = True
        if content is not None and content != entry.content:
            entry.content = content
            content_changed = True
        if category is not None:
            entry.category = category
        if tags is not None:
            entry.tags = tags
        if review_status is not None:
            entry.review_status = review_status
        if persona_domain is not None:
            entry.persona_domain = persona_domain

        entry.version = (entry.version or 1) + 1
        entry.updated_at = datetime.now(timezone.utc)

        await db.flush()

        await self.create_version(
            db, entry,
            changed_by_id=changed_by_id,
            changed_by_name=changed_by_name,
            change_reason=change_reason,
            previous_content=previous_content,
        )

        if content_changed:
            await self.generate_and_store_embedding(db, entry)

        return entry
