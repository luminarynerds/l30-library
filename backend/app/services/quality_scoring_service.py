# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeEntry, FAQChatbotConversation

logger = get_logger(__name__)

# Configurable weights (via env or defaults)
W_SATISFACTION = float(os.getenv("TRAINING_W_SATISFACTION", "0.30"))
W_STAFF_CORRECTION = float(os.getenv("TRAINING_W_STAFF_CORRECTION", "0.25"))
W_CONSISTENCY = float(os.getenv("TRAINING_W_CONSISTENCY", "0.20"))
W_FRESHNESS = float(os.getenv("TRAINING_W_FRESHNESS", "0.15"))
W_COMPLETENESS = float(os.getenv("TRAINING_W_COMPLETENESS", "0.10"))

APPROVED_THRESHOLD = 80
REVIEW_THRESHOLD = 40


@dataclass
class QualityScore:
    total: int  # 0-100
    breakdown: dict  # Component name -> individual score (0-100)
    bucket: str  # approved / review / rejected


class QualityScoringService:

    async def score_entry(self, db: AsyncSession, entry: KnowledgeEntry) -> QualityScore:
        satisfaction = await self._score_satisfaction(db, entry)
        staff_correction = self._score_staff_correction(entry)
        consistency = await self._score_consistency(db, entry)
        freshness = self._score_freshness(entry)
        completeness = self._score_completeness(entry)

        total = int(
            satisfaction * W_SATISFACTION
            + staff_correction * W_STAFF_CORRECTION
            + consistency * W_CONSISTENCY
            + freshness * W_FRESHNESS
            + completeness * W_COMPLETENESS
        )
        total = max(0, min(100, total))

        breakdown = {
            "satisfaction": satisfaction,
            "staff_correction": staff_correction,
            "consistency": consistency,
            "freshness": freshness,
            "completeness": completeness,
        }

        return QualityScore(
            total=total,
            breakdown=breakdown,
            bucket=self.assign_bucket(total),
        )

    @staticmethod
    def assign_bucket(score: int) -> str:
        if score >= APPROVED_THRESHOLD:
            return "approved"
        if score >= REVIEW_THRESHOLD:
            return "review"
        return "rejected"

    async def _score_satisfaction(self, db: AsyncSession, entry: KnowledgeEntry) -> int:
        if entry.source_type != "patron_interaction":
            return 75  # Default for non-interaction entries

        ref_id = entry.source_reference_id
        if not ref_id:
            return 50

        # Check if the linked conversation had positive feedback
        try:
            total = await db.scalar(
                select(func.count(FAQChatbotConversation.id)).where(
                    FAQChatbotConversation.matched_entry_id == entry.id
                )
            ) or 0
            positive = await db.scalar(
                select(func.count(FAQChatbotConversation.id)).where(
                    FAQChatbotConversation.matched_entry_id == entry.id,
                    FAQChatbotConversation.was_helpful == True,  # noqa: E712
                )
            ) or 0
            if total == 0:
                return 50
            return int((positive / total) * 100)
        except SQLAlchemyError:
            return 50

    @staticmethod
    def _score_staff_correction(entry: KnowledgeEntry) -> int:
        meta = entry.entry_metadata or {}
        if meta.get("staff_corrected"):
            return 100  # Staff-corrected version is highest quality
        if entry.source_type == "manual":
            return 100  # Staff-authored
        if entry.review_status == "approved":
            return 75  # Approved but not explicitly corrected
        if entry.source_type == "patron_interaction":
            satisfaction = meta.get("satisfaction_signal")
            if satisfaction is True:
                return 75
            if satisfaction is None:
                return 50  # Unknown
            return 0  # Negative/abandoned
        return 50

    async def _score_consistency(self, db: AsyncSession, entry: KnowledgeEntry) -> int:
        meta = entry.entry_metadata or {}
        if meta.get("conflict_flagged"):
            return 0
        # Check if entry has been flagged via conflict detection
        if meta.get("conflicts"):
            return 0
        return 100

    @staticmethod
    def _score_freshness(entry: KnowledgeEntry) -> int:
        if entry.expires_at is None:
            return 100  # No expiry = always fresh
        now = datetime.now(timezone.utc)
        if entry.expires_at < now:
            return 0  # Expired
        days_until_expiry = (entry.expires_at - now).days
        if days_until_expiry <= 30:
            return 50  # Expiring soon
        return 100

    @staticmethod
    def _score_completeness(entry: KnowledgeEntry) -> int:
        content = entry.content or ""
        title = entry.title or ""

        # For Q&A format entries, split on Q:/A: markers
        if "Q:" in content and "A:" in content:
            parts = content.split("A:", 1)
            q_words = len(parts[0].replace("Q:", "").split())
            a_words = len(parts[1].split()) if len(parts) > 1 else 0
        else:
            q_words = len(title.split())
            a_words = len(content.split())

        if q_words >= 5 and a_words >= 20:
            return 100
        if q_words >= 3 and a_words >= 10:
            return 50
        return 0
