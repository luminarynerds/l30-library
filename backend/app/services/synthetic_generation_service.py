# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.knowledge_base import KnowledgeEntry
from app.services.qa_extraction_service import QAExtractionService
from app.services.knowledge_pipeline_service import KnowledgePipelineService

logger = get_logger(__name__)
MAX_SYNTHETIC_RATIO = 0.4

class SyntheticGenerationService:
    def __init__(self):
        self.qa_service = QAExtractionService()
        self.pipeline = KnowledgePipelineService()

    async def _store_synthetic(self, db, question, answer, persona_domain, source_entry_id):
        entry = KnowledgeEntry(
            title=question[:500],
            content=f"Q: {question}\nA: {answer}",
            category="synthetic_qa",
            source_type="synthetic",
            persona_domain=persona_domain,
            version=1,
            review_status="pending",
            source_reference_id=f"synthetic_from_{source_entry_id}",
        )
        db.add(entry)
        await db.flush()
        await self.pipeline.generate_and_store_embedding(db, entry)
        await self.pipeline.create_version(db, entry, change_reason=f"Synthetically generated from entry {source_entry_id}")
        return entry

    async def generate_from_entry(self, db, source_entry):
        if not await self._check_ratio(db, source_entry.persona_domain or "shared"):
            logger.info(f"Synthetic ratio exceeded for domain {source_entry.persona_domain}")
            return []
        qa_pairs = await self.qa_service.extract_from_text(source_entry.content)
        entries = []
        for qa in qa_pairs:
            entry = await self._store_synthetic(db, qa["question"], qa["answer"], source_entry.persona_domain or "shared", source_entry.id)
            entries.append(entry)
        await db.commit()
        return entries

    async def generate_batch(self, db, persona_domain=None, limit=50):
        query = select(KnowledgeEntry).where(
            KnowledgeEntry.review_status == "approved",
            KnowledgeEntry.source_type != "synthetic",
        )
        if persona_domain:
            query = query.where(KnowledgeEntry.persona_domain == persona_domain)
        query = query.limit(limit)
        result = await db.execute(query)
        source_entries = result.scalars().all()
        all_entries = []
        for source in source_entries:
            entries = await self.generate_from_entry(db, source)
            all_entries.extend(entries)
        return all_entries

    async def _check_ratio(self, db, persona_domain):
        total = await db.scalar(
            select(func.count(KnowledgeEntry.id)).where(
                KnowledgeEntry.review_status == "approved",
                KnowledgeEntry.persona_domain == persona_domain,
            )
        ) or 0
        synthetic = await db.scalar(
            select(func.count(KnowledgeEntry.id)).where(
                KnowledgeEntry.review_status == "approved",
                KnowledgeEntry.source_type == "synthetic",
                KnowledgeEntry.persona_domain == persona_domain,
            )
        ) or 0
        if total == 0:
            return True
        return (synthetic / total) < MAX_SYNTHETIC_RATIO
