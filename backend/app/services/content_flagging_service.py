# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy import and_, select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.content_flag import ContentFlag, FlagType, FlagStatus, FlagAnalysisResult
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


# Define regex patterns for detection
SPAM_PATTERNS = {
    "url": r"(?:https?://|www\.)[^\s]+",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?(?:\d{3})?\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "promotion": r"\b(?:buy|purchase|order|click|link|visit|check\s+out|limited\s+time|sale|discount|coupon|promo|free\s+shipping|offer)\b",
    "hashtag": r"#[A-Za-z0-9_]+",
    "mention": r"@[A-Za-z0-9_]+",
}

HATE_SPEECH_SLURS = [
    # Common slurs and offensive language
    "slur1", "slur2", "slur3",  # Placeholder - would be replaced with real moderation lists
]

SUSPICIOUS_PATTERNS = {
    "random_chars": r"[a-zA-Z]{1,2}\d{1,2}[a-zA-Z]{1,2}\d{1,2}",
    "repeated_chars": r"(.)\1{4,}",  # 5+ repeated characters
    "keyboard_smash": r"[qwerty]{5,}|[asdfgh]{5,}|[zxcvbn]{5,}",
    "unicode_spam": r"[\u0080-\uFFFF]{20,}",  # Long unicode sequences
}

# Hate speech detection - using more ethical approach
OFFENSIVE_KEYWORDS = [
    # This is a placeholder - in production, use a proper moderation API
    # or well-maintained offensive language detection library
]


@dataclass
class FlagAnalysis:
    flag_type: FlagType
    confidence_score: int  # 0-100
    details: Dict[str, Any]
    is_flagged: bool  # True if score > 70


@dataclass
class ContentAnalysisResult:
    flags: list[FlagAnalysis]
    overall_score: int  # Max confidence across all categories
    should_flag: bool  # True if any flag > 70
    analysis_details: Dict[str, Any]


class ContentFlaggingService:

    @staticmethod
    def detect_spam(text: str) -> FlagAnalysis:
        details = {
            "patterns_detected": [],
            "matches": [],
            "text_snippets": []
        }

        spam_score = 0
        total_patterns = 0

        for pattern_name, pattern in SPAM_PATTERNS.items():
            total_patterns += 1
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                details["patterns_detected"].append(pattern_name)
                details["matches"].extend(matches[:3])  # Keep first 3 matches
                spam_score += 20  # Each pattern adds weight

        # Check for excessive promotional language
        text_lower = text.lower()
        promo_keywords = ["buy", "purchase", "order", "click", "link", "visit", "limited"]
        promo_count = sum(text_lower.count(kw) for kw in promo_keywords)
        if promo_count > 2:
            spam_score += 15
            details["patterns_detected"].append("excessive_promotional_language")

        # Normalize score
        confidence_score = min(100, spam_score)

        return FlagAnalysis(
            flag_type=FlagType.SPAM,
            confidence_score=confidence_score,
            details=details,
            is_flagged=confidence_score > 70
        )

    @staticmethod
    def detect_hate_speech(text: str) -> FlagAnalysis:
        details = {
            "offensive_terms": [],
            "severity": "low",
            "context": ""
        }

        # Placeholder implementation - in production, use a proper NLP model
        # or established moderation service
        hate_speech_score = 0

        # This is a simplified placeholder - real implementation would use:
        # 1. Perspective API
        # 2. Better Word lists from reputable sources
        # 3. NLP-based context analysis
        # 4. Machine learning models trained on hate speech detection

        text_lower = text.lower()

        # Simple keyword matching (placeholder)
        if any(term in text_lower for term in ["racist", "hateful", "discriminatory"]):
            hate_speech_score += 30
            details["offensive_terms"].append("detected_harmful_content")

        # Check for excessive profanity or aggression patterns
        aggressive_patterns = [r"!!!+", r"\?\?+", r"damn", r"hate"]
        for pattern in aggressive_patterns:
            if re.search(pattern, text_lower):
                hate_speech_score += 5

        confidence_score = min(100, hate_speech_score)

        return FlagAnalysis(
            flag_type=FlagType.HATE_SPEECH,
            confidence_score=confidence_score,
            details=details,
            is_flagged=confidence_score > 70
        )

    @staticmethod
    def detect_excessive_caps(text: str) -> FlagAnalysis:
        details = {
            "caps_percentage": 0,
            "exclamation_count": 0,
            "question_count": 0,
            "mixed_intensity": False
        }

        # Only analyze text longer than 10 characters
        if len(text) < 10:
            return FlagAnalysis(
                flag_type=FlagType.EXCESSIVE_CAPS,
                confidence_score=0,
                details=details,
                is_flagged=False
            )

        # Count uppercase letters
        letters = [c for c in text if c.isalpha()]
        if letters:
            caps_count = sum(1 for c in letters if c.isupper())
            caps_percentage = (caps_count / len(letters)) * 100
            details["caps_percentage"] = round(caps_percentage, 2)
        else:
            caps_percentage = 0

        # Count punctuation
        exclamation_count = text.count("!")
        question_count = text.count("?")
        details["exclamation_count"] = exclamation_count
        details["question_count"] = question_count

        score = 0

        # Score based on caps percentage
        if caps_percentage > 70:
            score += 40
        elif caps_percentage > 50:
            score += 25
        elif caps_percentage > 30:
            score += 10

        # Score based on punctuation
        punct_ratio = (exclamation_count + question_count) / max(1, len(text.split()))
        if punct_ratio > 0.3:
            score += 30
            details["mixed_intensity"] = True
        elif punct_ratio > 0.1:
            score += 15

        confidence_score = min(100, score)

        return FlagAnalysis(
            flag_type=FlagType.EXCESSIVE_CAPS,
            confidence_score=confidence_score,
            details=details,
            is_flagged=confidence_score > 70
        )

    @staticmethod
    def detect_suspicious_patterns(text: str) -> FlagAnalysis:
        details = {
            "patterns_detected": [],
            "suspicious_sequences": []
        }

        score = 0

        for pattern_name, pattern in SUSPICIOUS_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                details["patterns_detected"].append(pattern_name)
                details["suspicious_sequences"].extend(matches[:3])  # Keep first 3
                if pattern_name == "repeated_chars":
                    score += 25
                elif pattern_name in ["random_chars", "keyboard_smash"]:
                    score += 35
                elif pattern_name == "unicode_spam":
                    score += 40

        # Check for mixed character types that don't make sense
        if re.search(r"[0-9]{10,}", text):  # Long number sequences
            score += 15
            details["patterns_detected"].append("long_number_sequence")

        confidence_score = min(100, score)

        return FlagAnalysis(
            flag_type=FlagType.SUSPICIOUS_PATTERN,
            confidence_score=confidence_score,
            details=details,
            is_flagged=confidence_score > 70
        )

    @staticmethod
    def detect_off_topic(text: str, context: Optional[str] = None) -> FlagAnalysis:
        details = {
            "off_topic_indicators": [],
            "text_characteristics": {}
        }

        score = 0

        # Check for common off-topic indicators
        off_topic_phrases = [
            r"check\s+(?:out|this)",
            r"follow\s+(?:me|us)",
            r"subscribe",
            r"dm\s+(?:me|us)",
            r"message\s+(?:me|us)",
            r"contact\s+(?:me|us)",
            r"(?:look\s+)?(?:at\s+)?my\s+(?:profile|page|website|blog|instagram|twitter|youtube)",
        ]

        text_lower = text.lower()
        for phrase_pattern in off_topic_phrases:
            if re.search(phrase_pattern, text_lower):
                score += 20
                details["off_topic_indicators"].append(phrase_pattern)

        # Check if text is very short (< 5 words) and seems off-topic
        word_count = len(text.split())
        if word_count < 5 and score > 0:
            score += 15

        # Check for advertisements or self-promotion
        if re.search(r"\b(buy|sell|price|discount|offer|promo|code)\b", text_lower):
            score += 15
            details["off_topic_indicators"].append("commercial_content")

        confidence_score = min(100, score)

        return FlagAnalysis(
            flag_type=FlagType.OFF_TOPIC,
            confidence_score=confidence_score,
            details=details,
            is_flagged=confidence_score > 70
        )

    @staticmethod
    async def detect_duplicates(
        db: AsyncSession,
        review_id: int,
        user_email: str,
        text: str,
        review_type: str = "event_review",
        similarity_threshold: float = 0.85
    ) -> FlagAnalysis:
        details = {
            "similar_reviews": [],
            "similarity_score": 0,
            "time_window_days": 30
        }

        score = 0

        # Look for reviews from same user in last 30 days
        thirty_days_ago = utc_now() - timedelta(days=30)

        try:
            result = await db.execute(
                select(ContentFlag).where(
                    and_(
                        ContentFlag.review_type == review_type,
                        # In real implementation, would join to get user email
                        ContentFlag.created_at > thirty_days_ago
                    )
                )
            )
            recent_flags = result.scalars().all()

            # Simple similarity check using character overlap
            for flag in recent_flags:
                if flag.review_id != review_id:  # Don't compare with self
                    # Would need to get the actual review text to compare
                    # This is a placeholder showing the structure
                    pass

            # Exact duplicate check would be based on reviewing similar text
            # In production, use Levenshtein distance or semantic similarity

        except SQLAlchemyError as e:
            logger.warning(f"Failed to check for duplicates: {e}")

        confidence_score = min(100, score)

        return FlagAnalysis(
            flag_type=FlagType.DUPLICATE,
            confidence_score=confidence_score,
            details=details,
            is_flagged=confidence_score > 70
        )

    @classmethod
    async def analyze_review(
        cls,
        db: AsyncSession,
        text: str,
        user_email: Optional[str] = None,
        review_id: Optional[int] = None,
        review_type: str = "event_review",
        context: Optional[str] = None
    ) -> ContentAnalysisResult:
        try:
            # Validate input
            if not text or len(text.strip()) < 2:
                return ContentAnalysisResult(
                    flags=[],
                    overall_score=0,
                    should_flag=False,
                    analysis_details={"error": "Text too short"}
                )

            flags = []

            # Run all detection methods
            flags.append(cls.detect_spam(text))
            flags.append(cls.detect_hate_speech(text))
            flags.append(cls.detect_excessive_caps(text))
            flags.append(cls.detect_suspicious_patterns(text))
            flags.append(cls.detect_off_topic(text, context))

            # Duplicate detection (async)
            if user_email and review_id:
                duplicate_flag = await cls.detect_duplicates(
                    db, review_id, user_email, text, review_type
                )
                flags.append(duplicate_flag)

            # Calculate overall score (max of all flags)
            overall_score = max((f.confidence_score for f in flags), default=0)

            # Build analysis details
            analysis_details = {
                "flag_categories": {
                    str(f.flag_type): {
                        "score": f.confidence_score,
                        "details": f.details
                    }
                    for f in flags
                },
                "analysis_timestamp": utc_now().isoformat(),
                "text_length": len(text),
                "word_count": len(text.split())
            }

            should_flag = overall_score > 70

            return ContentAnalysisResult(
                flags=flags,
                overall_score=overall_score,
                should_flag=should_flag,
                analysis_details=analysis_details
            )

        except Exception as e:  # noqa: BLE001 - service-entrypoint boundary — must return ContentAnalysisResult on any failure
            logger.error(f"Error analyzing review content: {e}")
            return ContentAnalysisResult(
                flags=[],
                overall_score=0,
                should_flag=False,
                analysis_details={"error": str(e)}
            )

    @staticmethod
    async def save_flags(
        db: AsyncSession,
        review_id: int,
        review_type: str,
        analysis_result: ContentAnalysisResult
    ) -> Optional[ContentFlag]:
        try:
            if not analysis_result.flags:
                return None

            # Create content flag record
            content_flag = ContentFlag(
                review_id=review_id,
                review_type=review_type,
                flag_type=FlagType(
                    analysis_result.flags[0].flag_type
                    if analysis_result.flags[0].confidence_score == analysis_result.overall_score
                    else FlagType.SUSPICIOUS_PATTERN
                ),
                confidence_score=analysis_result.overall_score,
                analysis_details=analysis_result.analysis_details,
                status=FlagStatus.PENDING if analysis_result.should_flag else FlagStatus.RESOLVED
            )

            db.add(content_flag)
            await db.flush()

            # Create analysis result records for each flag type
            for flag in analysis_result.flags:
                if flag.confidence_score > 0:
                    analysis_record = FlagAnalysisResult(
                        content_flag_id=content_flag.id,
                        flag_category=flag.flag_type,
                        category_score=flag.confidence_score,
                        evidence=flag.details
                    )
                    db.add(analysis_record)

            await db.commit()
            await db.refresh(content_flag)

            logger.info(
                f"Saved content flag: review={review_id}, score={analysis_result.overall_score}, "
                f"should_flag={analysis_result.should_flag}"
            )

            return content_flag

        except SQLAlchemyError as e:
            logger.error(f"Failed to save content flags: {e}")
            await db.rollback()
            return None

    @staticmethod
    async def get_pending_flags(
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
        review_type: Optional[str] = None,
        min_score: int = 70
    ) -> tuple[list[ContentFlag], int]:
        query = select(ContentFlag).where(
            and_(
                ContentFlag.status == FlagStatus.PENDING,
                ContentFlag.confidence_score >= min_score
            )
        )

        if review_type:
            query = query.where(ContentFlag.review_type == review_type)

        # Get total count
        count_result = await db.execute(
            select(func.count(ContentFlag.id)).where(
                and_(
                    ContentFlag.status == FlagStatus.PENDING,
                    ContentFlag.confidence_score >= min_score
                )
            )
        )
        total = count_result.scalar() or 0

        # Get paginated results
        query = query.order_by(ContentFlag.confidence_score.desc(), ContentFlag.created_at.asc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await db.execute(query)
        flags = result.scalars().all()

        return flags, total

    @staticmethod
    async def resolve_flag(
        db: AsyncSession,
        flag_id: int,
        status: str,
        resolved_by: str,
        is_correct_flag: Optional[bool] = None,
        resolution_notes: Optional[str] = None,
        staff_feedback: Optional[str] = None
    ) -> Optional[ContentFlag]:
        try:
            result = await db.execute(
                select(ContentFlag).where(ContentFlag.id == flag_id)
            )
            flag = result.scalar_one_or_none()

            if not flag:
                return None

            flag.status = FlagStatus(status)
            flag.resolved_by = resolved_by
            flag.resolved_at = utc_now()
            flag.resolution_notes = resolution_notes
            flag.is_correct_flag = is_correct_flag
            flag.staff_feedback = staff_feedback

            await db.commit()
            await db.refresh(flag)

            logger.info(
                f"Resolved flag: id={flag_id}, status={status}, is_correct={is_correct_flag}"
            )

            return flag

        except SQLAlchemyError as e:
            logger.error(f"Failed to resolve flag: {e}")
            await db.rollback()
            return None

    @staticmethod
    async def get_false_positive_rate(
        db: AsyncSession,
        days: int = 30
    ) -> float:
        cutoff_date = utc_now() - timedelta(days=days)

        # Get total resolved flags
        total_result = await db.execute(
            select(func.count(ContentFlag.id)).where(
                and_(
                    ContentFlag.status != FlagStatus.PENDING,
                    ContentFlag.updated_at >= cutoff_date
                )
            )
        )
        total_resolved = total_result.scalar() or 0

        if total_resolved == 0:
            return 0.0

        # Get false positives
        fp_result = await db.execute(
            select(func.count(ContentFlag.id)).where(
                and_(
                    ContentFlag.status == FlagStatus.FALSE_POSITIVE,
                    ContentFlag.updated_at >= cutoff_date
                )
            )
        )
        false_positives = fp_result.scalar() or 0

        return (false_positives / total_resolved) * 100 if total_resolved > 0 else 0.0
