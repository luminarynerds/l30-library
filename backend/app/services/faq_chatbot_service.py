# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from difflib import SequenceMatcher

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from app.core.logging import get_logger

from ..models.knowledge_base import (
    KnowledgeEntry, FAQPattern, FAQAnalytics, SeasonalFAQ,
    FAQChatbotConversation, PatronChatbotContext
)
from ..models.support_ticket import SupportTicket

logger = get_logger(__name__)


class FAQChatbotService:

    # Common question patterns mapped to FAQ categories
    QUESTION_PATTERNS = {
        "hours": {
            "keywords": ["hours", "open", "close", "when", "time", "available"],
            "category": "facility_hours"
        },
        "book_search": {
            "keywords": ["book", "catalog", "search", "have", "do you have", "looking for", "available"],
            "category": "catalog"
        },
        "library_card": {
            "keywords": ["library card", "card", "register", "account", "sign up", "member"],
            "category": "accounts"
        },
        "bathroom": {
            "keywords": ["bathroom", "restroom", "toilet", "where", "locate", "facilities"],
            "category": "facilities"
        },
        "checkout": {
            "keywords": ["checkout", "borrow", "return", "due date", "renew", "loan"],
            "category": "circulation"
        },
        "help": {
            "keywords": ["help", "assist", "support", "staff", "question", "help me"],
            "category": "support"
        }
    }

    @staticmethod
    def normalize_question(question: str) -> str:
        # Convert to lowercase, remove extra whitespace, remove punctuation
        normalized = question.lower().strip()
        normalized = re.sub(r'[?!.,;:]', '', normalized)
        normalized = normalized.replace("-", "")  # wifi == wi-fi
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized

    @staticmethod
    def extract_keywords(question: str) -> List[str]:
        normalized = FAQChatbotService.normalize_question(question)
        # Remove common stopwords
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'what', 'which', 'who', 'when', 'where', 'why', 'how', 'can', 'you', 'your',
            'have', 'has', 'had', 'get', 'got', 'need', 'want', 'like', 'there', 'here',
            'just', 'about', 'some', 'any', 'not', 'also', 'much', 'many'
        }
        words = [w for w in normalized.split() if w not in stopwords and len(w) > 2]
        return words

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        matcher = SequenceMatcher(None, text1.lower(), text2.lower())
        return matcher.ratio()

    async def _semantic_search(
        self,
        db: AsyncSession,
        question: str,
        location_id: Optional[int] = None,
        limit: int = 3,
    ) -> Dict[str, Any]:
        try:
            from ..services.semantic_search_service import SemanticSearchService
            from ..models.embeddings import TextEmbedding
            from app.core.datetime_utils import utc_now

            svc = SemanticSearchService(db)
            embedding_vector = await svc.generate_embedding(question, input_type="query")
            if embedding_vector is None:
                return {"results": []}

            now = utc_now()

            # Build location filter: entry is system-wide OR matches requested location
            if location_id is not None:
                location_filter = (
                    (KnowledgeEntry.location_id == None) |  # noqa: E711
                    (KnowledgeEntry.location_id == location_id)
                )
            else:
                location_filter = (KnowledgeEntry.location_id == None)  # noqa: E711

            query = (
                select(
                    TextEmbedding,
                    KnowledgeEntry,
                    TextEmbedding.embedding.cosine_distance(embedding_vector).label("distance")
                )
                .join(KnowledgeEntry, and_(
                    KnowledgeEntry.id == TextEmbedding.entity_id,
                    TextEmbedding.entity_type == "knowledge_entry",
                ))
                .where(
                    KnowledgeEntry.review_status == "approved",
                    TextEmbedding.embedding.isnot(None),
                    (KnowledgeEntry.expires_at == None) | (KnowledgeEntry.expires_at > now),  # noqa: E711
                    location_filter,
                )
                .order_by("distance")
                .limit(limit * 2)
            )

            result = await db.execute(query)
            rows = result.all()

            results = []
            for row in rows[:limit]:
                text_emb, kb_entry, distance = row
                similarity = max(0.0, 1.0 - float(distance))
                results.append({
                    "text_content": text_emb.text_content,
                    "similarity": similarity,
                    "entity_id": text_emb.entity_id,
                    "location_id": kb_entry.location_id,
                    "title": kb_entry.title,
                    "_kb_entry": kb_entry,
                })

            return {"results": results}

        except Exception as e:  # noqa: BLE001 -- semantic search optional: fall back to empty results, pattern match still attempted
            logger.warning(f"Semantic search unavailable: {e}")
            return {"results": []}

    async def _pattern_match(
        self,
        db: AsyncSession,
        question: str,
        threshold: float = 0.6,
    ) -> Optional[Tuple[KnowledgeEntry, FAQPattern, int]]:
        normalized_question = self.normalize_question(question)

        # Try exact pattern matches first
        stmt = select(FAQPattern).where(
            and_(
                FAQPattern.is_active == True,
                FAQPattern.match_type == "exact"
            )
        ).order_by(desc(FAQPattern.priority))

        result = await db.execute(stmt)
        patterns = result.scalars().all()

        for pattern in patterns:
            if self.normalize_question(pattern.pattern_text) == normalized_question:
                # Found exact match
                knowledge_stmt = select(KnowledgeEntry).where(
                    KnowledgeEntry.id == pattern.knowledge_entry_id
                )
                kb_result = await db.execute(knowledge_stmt)
                kb_entry = kb_result.scalar_one_or_none()
                if kb_entry:
                    return (kb_entry, pattern, 100)

        # Try keyword matching -- load keyword patterns (exact patterns checked above)
        kw_stmt = select(FAQPattern).where(
            and_(
                FAQPattern.is_active == True,
                FAQPattern.match_type == "keyword"
            )
        ).order_by(desc(FAQPattern.priority))

        kw_result = await db.execute(kw_stmt)
        keyword_patterns = kw_result.scalars().all()

        keywords = self.extract_keywords(question)
        best_match = None
        best_score = 0

        for pattern in keyword_patterns:
            # Use curated pattern_keywords if available, else extract from text
            if getattr(pattern, "pattern_keywords", None):
                pattern_keywords = set(
                    kw.strip().lower().replace("-", "")
                    for kw in pattern.pattern_keywords.split(",")
                    if kw.strip()
                )
            else:
                pattern_keywords = set(
                    self.extract_keywords(pattern.pattern_text)
                )
            question_keywords = set(keywords)

            if not question_keywords:
                continue

            # Score: fraction of question keywords found in pattern keywords
            overlap = len(question_keywords & pattern_keywords)
            total = len(question_keywords)  # recall: what fraction of question words matched
            score = overlap / total if total > 0 else 0

            if score > best_score and score >= threshold:
                best_score = score
                best_match = pattern

        # If we found a good keyword match
        if best_match and best_score >= threshold:
            knowledge_stmt = select(KnowledgeEntry).where(
                KnowledgeEntry.id == best_match.knowledge_entry_id
            )
            kb_result = await db.execute(knowledge_stmt)
            kb_entry = kb_result.scalar_one_or_none()
            if kb_entry:
                confidence = int(best_score * 100)
                return (kb_entry, best_match, confidence)

        # Try string similarity matching on FAQ titles
        stmt = select(KnowledgeEntry).where(
            KnowledgeEntry.entry_type == "faq"
        ).order_by(desc(KnowledgeEntry.view_count))

        result = await db.execute(stmt)
        faq_entries = result.scalars().all()

        for entry in faq_entries[:20]:  # Check top 20 FAQs
            similarity = self.calculate_similarity(question, entry.title)
            if similarity >= threshold and similarity > best_score:
                best_score = similarity
                best_match = entry

        if best_match:
            confidence = int(best_score * 100)
            return (best_match, None, confidence)

        return None

    async def find_matching_faq(
        self,
        db: AsyncSession,
        question: str,
        threshold: float = 0.6
    ) -> Optional[Tuple[KnowledgeEntry, FAQPattern, int]]:
        # Attempt semantic search
        semantic_result = await self._semantic_search(db, question)
        results = semantic_result.get("results", [])

        SEMANTIC_THRESHOLD = 0.7
        if results and results[0]["similarity"] >= SEMANTIC_THRESHOLD:
            top = results[0]
            kb_entry = top["_kb_entry"]
            confidence = int(top["similarity"] * 100)
            return (kb_entry, None, confidence)

        # Fall back to pattern matching
        return await self._pattern_match(db, question, threshold)

    async def find_matching_faq_enhanced(
        self,
        db: AsyncSession,
        question: str,
        location_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        semantic_result = await self._semantic_search(db, question, location_id=location_id)
        results = semantic_result.get("results", [])

        SEMANTIC_THRESHOLD = 0.7
        if results and results[0]["similarity"] >= SEMANTIC_THRESHOLD:
            top = results[0]
            return {
                "match_type": "semantic",
                "confidence": int(top["similarity"] * 100),
                "kb_entry": top["_kb_entry"],
                "faq_pattern": None,
                "semantic_results": results,
            }

        pattern_match = await self._pattern_match(db, question)
        if pattern_match:
            kb_entry, faq_pattern, confidence = pattern_match
            return {
                "match_type": "pattern",
                "confidence": confidence,
                "kb_entry": kb_entry,
                "faq_pattern": faq_pattern,
                "semantic_results": results,
            }

        return {
            "match_type": "none",
            "confidence": 0,
            "kb_entry": None,
            "faq_pattern": None,
            "semantic_results": results,
        }

    async def get_seasonal_faqs(
        self,
        db: AsyncSession,
        current_date: Optional[datetime] = None
    ) -> List[KnowledgeEntry]:
        if current_date is None:
            current_date = datetime.now()

        month_day = current_date.strftime("%m-%d")

        # Get seasonal FAQs that are active for this date
        stmt = select(SeasonalFAQ).where(
            and_(
                SeasonalFAQ.is_active == True,
                SeasonalFAQ.start_date <= month_day,
                SeasonalFAQ.end_date >= month_day
            )
        ).order_by(desc(SeasonalFAQ.priority))

        result = await db.execute(stmt)
        seasonal = result.scalars().all()

        knowledge_ids = [s.knowledge_entry_id for s in seasonal]

        if not knowledge_ids:
            return []

        knowledge_stmt = select(KnowledgeEntry).where(
            KnowledgeEntry.id.in_(knowledge_ids)
        )

        kb_result = await db.execute(knowledge_stmt)
        return kb_result.scalars().all()

    async def record_conversation(
        self,
        db: AsyncSession,
        user_id: Optional[int],
        session_id: str,
        question: str,
        faq_entry: Optional[KnowledgeEntry],
        faq_pattern: Optional[FAQPattern],
        confidence_score: int,
        device_type: str = "web",
        location: str = "homepage"
    ) -> FAQChatbotConversation:
        conversation = FAQChatbotConversation(
            user_id=user_id,
            session_id=session_id,
            original_question=question,
            question_category=faq_entry.category if faq_entry else None,
            matched_faq_id=faq_entry.id if faq_entry else None,
            matched_pattern_id=faq_pattern.id if faq_pattern else None,
            chatbot_response=faq_entry.content if faq_entry else None,
            confidence_score=confidence_score,
            device_type=device_type,
            location=location
        )

        db.add(conversation)

        # Update pattern match count
        if faq_pattern:
            faq_pattern.match_count = (faq_pattern.match_count or 0) + 1

        # Update patron context
        if user_id:
            patron_context_stmt = select(PatronChatbotContext).where(
                PatronChatbotContext.user_id == user_id
            )
            context_result = await db.execute(patron_context_stmt)
            context = context_result.scalar_one_or_none()

            if not context:
                context = PatronChatbotContext(user_id=user_id)
                db.add(context)

            context.last_question = question
            context.last_interaction_at = datetime.now()
            context.total_interactions = (context.total_interactions or 0) + 1

        return conversation

    async def record_feedback(
        self,
        db: AsyncSession,
        conversation_id: int,
        was_helpful: bool,
        escalated: bool = False
    ) -> None:
        stmt = select(FAQChatbotConversation).where(
            FAQChatbotConversation.id == conversation_id
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            return

        conversation.was_helpful = was_helpful
        conversation.escalated_to_support = escalated

        # Update analytics
        if conversation.original_question:
            normalized = self.normalize_question(conversation.original_question)

            analytics_stmt = select(FAQAnalytics).where(
                FAQAnalytics.normalized_question == normalized
            )
            analytics_result = await db.execute(analytics_stmt)
            analytics = analytics_result.scalar_one_or_none()

            if not analytics:
                analytics = FAQAnalytics(
                    question_text=conversation.original_question,
                    normalized_question=normalized,
                    category=conversation.question_category
                )
                db.add(analytics)

            analytics.ask_count = (analytics.ask_count or 0) + 1
            if was_helpful:
                analytics.chatbot_answered_count = (analytics.chatbot_answered_count or 0) + 1
            if escalated:
                analytics.escalated_count = (analytics.escalated_count or 0) + 1

            # Calculate satisfaction rate
            total_useful = analytics.chatbot_answered_count or 0
            total_asks = analytics.ask_count or 0
            if total_asks > 0:
                analytics.satisfaction_rate = int((total_useful / total_asks) * 100)

        # Update patron context
        if conversation.user_id:
            patron_context_stmt = select(PatronChatbotContext).where(
                PatronChatbotContext.user_id == conversation.user_id
            )
            context_result = await db.execute(patron_context_stmt)
            context = context_result.scalar_one_or_none()

            if context:
                if was_helpful:
                    context.questions_resolved_count = (context.questions_resolved_count or 0) + 1
                else:
                    context.questions_escalated_count = (context.questions_escalated_count or 0) + 1
                    context.current_unresolved_question = conversation.original_question

    async def get_trending_questions(
        self,
        db: AsyncSession,
        days: int = 7,
        limit: int = 10
    ) -> List[Tuple[str, int]]:
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=days)

        stmt = select(
            FAQAnalytics.question_text,
            FAQAnalytics.ask_count
        ).where(
            FAQAnalytics.updated_at >= cutoff_date
        ).order_by(
            desc(FAQAnalytics.ask_count)
        ).limit(limit)

        result = await db.execute(stmt)
        return result.all()

    async def get_top_questions_for_signage(
        self,
        db: AsyncSession,
        limit: int = 5
    ) -> List[FAQAnalytics]:
        stmt = select(FAQAnalytics).where(
            FAQAnalytics.ask_count > 10
        ).order_by(
            desc(FAQAnalytics.ask_count)
        ).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_patron_context(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Optional[PatronChatbotContext]:
        stmt = select(PatronChatbotContext).where(
            PatronChatbotContext.user_id == user_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def suggest_signage_updates(self, db: AsyncSession) -> List[FAQAnalytics]:
        # Questions asked frequently but have low satisfaction rate
        stmt = select(FAQAnalytics).where(
            and_(
                FAQAnalytics.ask_count > 20,
                FAQAnalytics.satisfaction_rate < 70,
                FAQAnalytics.suggested_signage == False
            )
        ).order_by(
            desc(FAQAnalytics.ask_count)
        ).limit(10)

        result = await db.execute(stmt)
        return result.scalars().all()
