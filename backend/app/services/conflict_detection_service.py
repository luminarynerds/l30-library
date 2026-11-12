# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeEntry
from app.models.embeddings import TextEmbedding

logger = get_logger(__name__)

CONFLICT_THRESHOLD = 0.92


class ConflictDetectionService:

    async def check_entry(self, db: AsyncSession, entry: KnowledgeEntry) -> list[dict]:
        if not entry.embedding_id:
            return []

        # Get this entry's embedding
        emb_result = await db.execute(
            select(TextEmbedding).where(TextEmbedding.id == entry.embedding_id)
        )
        source_emb = emb_result.scalar_one_or_none()
        if not source_emb or source_emb.embedding is None:
            return []

        # Use pgvector cosine distance to find similar entries
        query = (
            select(
                TextEmbedding,
                KnowledgeEntry,
                TextEmbedding.embedding.cosine_distance(source_emb.embedding).label("distance")
            )
            .join(KnowledgeEntry, and_(
                KnowledgeEntry.id == TextEmbedding.entity_id,
                TextEmbedding.entity_type == "knowledge_entry",
            ))
            .where(
                KnowledgeEntry.review_status == "approved",
                KnowledgeEntry.id != entry.id,
                TextEmbedding.embedding.isnot(None),
            )
            .order_by("distance")
            .limit(20)
        )

        results = await db.execute(query)
        rows = results.all()

        conflicts = []
        for cand_emb, cand_entry, distance in rows:
            similarity = 1 - distance
            if similarity < CONFLICT_THRESHOLD:
                break  # Ordered by distance, so no more matches

            # Domain filtering: same domain or either is "shared"
            if entry.persona_domain and cand_entry.persona_domain:
                if (entry.persona_domain != cand_entry.persona_domain
                    and entry.persona_domain != "shared"
                    and cand_entry.persona_domain != "shared"):
                    continue

            conflicts.append({
                "entry_id": cand_entry.id,
                "title": cand_entry.title,
                "content": cand_entry.content[:200] if cand_entry.content else "",
                "similarity": round(float(similarity), 4),
                "persona_domain": cand_entry.persona_domain,
            })

        return conflicts

    async def scan_all(self, db: AsyncSession, persona_domain: str = None) -> list[dict]:
        query = select(KnowledgeEntry).where(KnowledgeEntry.review_status == "approved")
        if persona_domain:
            query = query.where(KnowledgeEntry.persona_domain == persona_domain)

        result = await db.execute(query)
        entries = result.scalars().all()

        all_conflicts = []
        seen_pairs = set()

        for entry in entries:
            conflicts = await self.check_entry(db, entry)
            for c in conflicts:
                pair = tuple(sorted([entry.id, c["entry_id"]]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    all_conflicts.append({
                        "entry_a_id": entry.id,
                        "entry_a_title": entry.title,
                        "entry_b_id": c["entry_id"],
                        "entry_b_title": c["title"],
                        "similarity": c["similarity"],
                        "domain": entry.persona_domain,
                    })

        return all_conflicts
