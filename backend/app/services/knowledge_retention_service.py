# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeEntry

logger = get_logger(__name__)

DEFAULT_RETENTION_MONTHS = 12


class KnowledgeRetentionService:

    async def purge_expired_conversations(
        self, db: AsyncSession, max_age_months: int = DEFAULT_RETENTION_MONTHS
    ) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_months * 30)
        result = await db.execute(
            delete(KnowledgeEntry).where(
                and_(
                    KnowledgeEntry.source_type == "patron_interaction",
                    KnowledgeEntry.created_at < cutoff,
                )
            ).returning(KnowledgeEntry.id)
        )
        deleted_ids = result.scalars().all()
        count = len(deleted_ids)
        if count:
            logger.info("Purged %d expired patron entries (older than %d months)", count, max_age_months)
        return count

    async def purge_by_patron(self, db: AsyncSession, patron_id: int) -> int:
        result = await db.execute(
            delete(KnowledgeEntry).where(
                and_(
                    KnowledgeEntry.source_type == "patron_interaction",
                    KnowledgeEntry.added_by_id == patron_id,
                )
            ).returning(KnowledgeEntry.id)
        )
        deleted_ids = result.scalars().all()
        count = len(deleted_ids)
        if count:
            logger.info("Purged %d knowledge entries for patron %d", count, patron_id)
        return count

    async def purge_by_date_range(self, db: AsyncSession, start: datetime, end: datetime) -> int:
        result = await db.execute(
            delete(KnowledgeEntry).where(
                and_(
                    KnowledgeEntry.created_at >= start,
                    KnowledgeEntry.created_at <= end,
                )
            ).returning(KnowledgeEntry.id)
        )
        return len(result.scalars().all())

    async def purge_by_source_type(self, db: AsyncSession, source_type: str) -> int:
        result = await db.execute(
            delete(KnowledgeEntry).where(
                KnowledgeEntry.source_type == source_type
            ).returning(KnowledgeEntry.id)
        )
        return len(result.scalars().all())

    async def get_retention_stats(self, db: AsyncSession) -> dict:
        total = await db.scalar(select(func.count(KnowledgeEntry.id))) or 0
        patron_entries = await db.scalar(
            select(func.count(KnowledgeEntry.id)).where(
                KnowledgeEntry.source_type == "patron_interaction"
            )
        ) or 0
        oldest_patron = await db.scalar(
            select(func.min(KnowledgeEntry.created_at)).where(
                KnowledgeEntry.source_type == "patron_interaction"
            )
        )
        expired = await db.scalar(
            select(func.count(KnowledgeEntry.id)).where(
                and_(
                    KnowledgeEntry.expires_at.isnot(None),
                    KnowledgeEntry.expires_at < datetime.now(timezone.utc),
                )
            )
        ) or 0

        return {
            "total_entries": total,
            "patron_interaction_entries": patron_entries,
            "oldest_patron_entry": oldest_patron.isoformat() if oldest_patron else None,
            "expired_entries": expired,
            "retention_months": DEFAULT_RETENTION_MONTHS,
        }
