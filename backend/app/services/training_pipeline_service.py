# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeEntry
from app.models.training_example import TrainingExample
from app.services.quality_scoring_service import QualityScoringService
from app.services.training_data_formatter_service import TrainingDataFormatterService

logger = get_logger(__name__)

SOURCE_DIVERSITY_CAP = 0.50  # No single source > 50% of approved pool


class TrainingPipelineService:

    def __init__(self):
        self.scorer = QualityScoringService()
        self.formatter = TrainingDataFormatterService()

    async def process_entry(self, db: AsyncSession, knowledge_entry_id: int) -> list[TrainingExample]:
        result = await db.execute(
            select(KnowledgeEntry).where(KnowledgeEntry.id == knowledge_entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            logger.warning("KnowledgeEntry %d not found", knowledge_entry_id)
            return []

        # Check if already processed
        existing = await db.scalar(
            select(func.count(TrainingExample.id)).where(
                TrainingExample.knowledge_entry_id == knowledge_entry_id
            )
        )
        if existing:
            logger.debug("Entry %d already has %d training examples", knowledge_entry_id, existing)
            return []

        # Format into instruction/response pairs
        formatted = self.formatter.format_entry(entry)
        if not formatted:
            logger.debug("Entry %d produced no training pairs", knowledge_entry_id)
            return []

        # Score the entry
        quality = await self.scorer.score_entry(db, entry)

        examples = []
        for pair in formatted:
            te = TrainingExample(
                knowledge_entry_id=entry.id,
                persona_domain=entry.persona_domain,
                instruction=pair["instruction"],
                response=pair["response"],
                source_type=entry.source_type or "unknown",
                quality_score=quality.total,
                quality_breakdown=quality.breakdown,
                bucket=quality.bucket,
                location_id=entry.location_id,
                is_multi_turn=pair.get("is_multi_turn", False),
                turn_index=pair.get("turn_index"),
                conversation_id=entry.source_reference_id,
            )
            db.add(te)
            examples.append(te)

        await db.flush()
        return examples

    async def process_batch(
        self, db: AsyncSession, persona_domain: Optional[str] = None, limit: int = 100
    ) -> list[TrainingExample]:
        # Find entries that don't have training examples yet
        subq = select(TrainingExample.knowledge_entry_id).distinct()
        query = select(KnowledgeEntry).where(
            KnowledgeEntry.id.notin_(subq)
        )
        if persona_domain:
            query = query.where(KnowledgeEntry.persona_domain == persona_domain)
        query = query.limit(limit)

        result = await db.execute(query)
        entries = result.scalars().all()

        all_examples = []
        for entry in entries:
            try:
                examples = await self.process_entry(db, entry.id)
                all_examples.extend(examples)
            except Exception:
                logger.exception("Failed to process entry %d", entry.id)
                continue

        return all_examples

    async def reprocess_entry(self, db: AsyncSession, training_example_id: int) -> Optional[TrainingExample]:
        result = await db.execute(
            select(TrainingExample).where(TrainingExample.id == training_example_id)
        )
        te = result.scalar_one_or_none()
        if not te:
            return None

        entry_result = await db.execute(
            select(KnowledgeEntry).where(KnowledgeEntry.id == te.knowledge_entry_id)
        )
        entry = entry_result.scalar_one_or_none()
        if not entry:
            return None

        quality = await self.scorer.score_entry(db, entry)
        te.quality_score = quality.total
        te.quality_breakdown = quality.breakdown
        if not te.staff_override:
            te.bucket = quality.bucket
        await db.flush()
        return te

    async def check_source_diversity(self, db: AsyncSession, persona_domain: str) -> dict:
        total = await db.scalar(
            select(func.count(TrainingExample.id)).where(
                and_(
                    TrainingExample.bucket == "approved",
                    TrainingExample.persona_domain == persona_domain,
                )
            )
        ) or 0

        if total == 0:
            return {"compliant": True, "total": 0, "breakdown": {}, "violations": []}

        source_rows = await db.execute(
            select(TrainingExample.source_type, func.count(TrainingExample.id)).where(
                and_(
                    TrainingExample.bucket == "approved",
                    TrainingExample.persona_domain == persona_domain,
                )
            ).group_by(TrainingExample.source_type)
        )

        breakdown = {}
        violations = []
        for source, count in source_rows:
            pct = count / total
            breakdown[source] = {"count": count, "percentage": round(pct * 100, 1)}
            if pct > SOURCE_DIVERSITY_CAP:
                violations.append(f"{source} is {pct*100:.1f}% (cap: {SOURCE_DIVERSITY_CAP*100:.0f}%)")

        return {
            "compliant": len(violations) == 0,
            "total": total,
            "breakdown": breakdown,
            "violations": violations,
        }

    async def get_readiness(self, db: AsyncSession, persona_domain: str) -> dict:
        THRESHOLD = 1000
        approved = await db.scalar(
            select(func.count(TrainingExample.id)).where(
                and_(
                    TrainingExample.bucket == "approved",
                    TrainingExample.persona_domain == persona_domain,
                )
            )
        ) or 0

        review = await db.scalar(
            select(func.count(TrainingExample.id)).where(
                and_(
                    TrainingExample.bucket == "review",
                    TrainingExample.persona_domain == persona_domain,
                )
            )
        ) or 0

        diversity = await self.check_source_diversity(db, persona_domain)

        return {
            "persona_domain": persona_domain,
            "approved_count": approved,
            "review_count": review,
            "threshold": THRESHOLD,
            "progress_pct": round(min(approved / THRESHOLD * 100, 100), 1),
            "ready": approved >= THRESHOLD and diversity["compliant"],
            "source_diversity": diversity,
        }

    async def get_stats(self, db: AsyncSession) -> dict:
        # Per-persona counts
        persona_rows = await db.execute(
            select(
                TrainingExample.persona_domain,
                TrainingExample.bucket,
                func.count(TrainingExample.id),
            ).group_by(TrainingExample.persona_domain, TrainingExample.bucket)
        )
        by_persona: dict[str, dict] = {}
        for domain, bucket, count in persona_rows:
            domain_key = domain or "unset"
            if domain_key not in by_persona:
                by_persona[domain_key] = {"approved": 0, "review": 0, "rejected": 0, "total": 0}
            by_persona[domain_key][bucket] = count
            by_persona[domain_key]["total"] += count

        # Source breakdown
        source_rows = await db.execute(
            select(TrainingExample.source_type, func.count(TrainingExample.id))
            .group_by(TrainingExample.source_type)
        )
        by_source = {row[0]: row[1] for row in source_rows}

        # Quality distribution
        total = await db.scalar(select(func.count(TrainingExample.id))) or 0
        avg_score = await db.scalar(select(func.avg(TrainingExample.quality_score))) or 0
        pending_review = await db.scalar(
            select(func.count(TrainingExample.id)).where(TrainingExample.bucket == "review")
        ) or 0

        return {
            "total_examples": total,
            "pending_review": pending_review,
            "average_quality_score": round(float(avg_score), 1),
            "by_persona": by_persona,
            "by_source": by_source,
        }
