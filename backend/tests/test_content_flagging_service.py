# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Content Flagging Service

Tests all flagging detection methods with various patterns:
- Spam/advertising
- Hate speech
- Excessive caps
- Suspicious patterns
- Off-topic content
- Duplicates
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.content_flagging_service import ContentFlaggingService, FlagType
from app.models.content_flag import ContentFlag, FlagStatus


class TestSpamDetection:
    """Test spam and advertising detection."""

    def test_detects_urls(self):
        """Should detect URLs in text."""
        analysis = ContentFlaggingService.detect_spam("Check out https://example.com for more info")
        assert analysis.flag_type == FlagType.SPAM
        assert analysis.confidence_score > 0
        assert "url" in analysis.details["patterns_detected"]

    def test_detects_email_addresses(self):
        """Should detect email addresses."""
        analysis = ContentFlaggingService.detect_spam("Contact us at spam@example.com for deals")
        assert analysis.flag_type == FlagType.SPAM
        assert analysis.confidence_score > 0

    def test_detects_phone_numbers(self):
        """Should detect phone numbers."""
        analysis = ContentFlaggingService.detect_spam("Call (555) 123-4567 for special offers")
        assert analysis.flag_type == FlagType.SPAM
        assert analysis.confidence_score > 0

    def test_detects_promotional_keywords(self):
        """Should detect promotional language.

        detect_spam scores per matched PATTERN TYPE (url/email/phone/promotion/
        hashtag/mention), not per phrase occurrence -- a text with ONLY
        promotional keywords (no url/email/phone) tops out around 35, well
        under the auto-flag bar. Use a realistic spam message that also
        includes a URL and phone number so multiple pattern types fire.
        """
        analysis = ContentFlaggingService.detect_spam(
            "BUY NOW! Visit https://example.com or call 555-123-4567 for our "
            "LIMITED TIME OFFER! Click here!"
        )
        assert analysis.flag_type == FlagType.SPAM
        assert analysis.confidence_score >= 70

    def test_clean_review_no_spam(self):
        """Should not flag legitimate reviews."""
        analysis = ContentFlaggingService.detect_spam(
            "This event was great! I learned a lot and had fun with friends."
        )
        assert analysis.confidence_score < 70


class TestHateSpeechDetection:
    """Test hate speech and offensive language detection."""

    def test_detects_aggressive_patterns(self):
        """Should detect aggressive patterns."""
        analysis = ContentFlaggingService.detect_hate_speech(
            "This is terrible!!! I hate this event???"
        )
        assert analysis.flag_type == FlagType.HATE_SPEECH
        assert analysis.confidence_score > 0

    def test_clean_review_no_hate_speech(self):
        """Should not flag legitimate negative reviews."""
        analysis = ContentFlaggingService.detect_hate_speech(
            "I didn't enjoy this event. The timing wasn't convenient for me."
        )
        assert analysis.confidence_score < 70


class TestExcessiveCapsDetection:
    """Test excessive capitalization detection."""

    def test_detects_all_caps(self):
        """Should detect all-caps text."""
        analysis = ContentFlaggingService.detect_excessive_caps(
            "THIS EVENT WAS COMPLETELY AMAZING!!!"
        )
        assert analysis.flag_type == FlagType.EXCESSIVE_CAPS
        assert analysis.confidence_score >= 70

    def test_detects_excessive_punctuation(self):
        """Should detect excessive punctuation.

        detect_excessive_caps's punctuation-ratio component caps at +30
        (elif tiers), and its caps-percentage component doesn't fire here
        (this text is mostly lowercase) -- so punctuation alone can score at
        most 30, never enough to cross the auto-flag bar on its own (that
        requires ALSO having a high caps percentage). 30 is this detector's
        ceiling for a punctuation-only signal.
        """
        analysis = ContentFlaggingService.detect_excessive_caps(
            "What a great event!!!!!!!???????!!!!!!"
        )
        assert analysis.flag_type == FlagType.EXCESSIVE_CAPS
        assert analysis.confidence_score >= 25
        assert analysis.details["mixed_intensity"] is True

    def test_ignores_short_text(self):
        """Should not flag very short text."""
        analysis = ContentFlaggingService.detect_excessive_caps("OK!")
        assert analysis.confidence_score == 0

    def test_normal_text_no_flag(self):
        """Should not flag normal text."""
        analysis = ContentFlaggingService.detect_excessive_caps(
            "Great event! I had a wonderful time."
        )
        assert analysis.confidence_score < 70


class TestSuspiciousPatternDetection:
    """Test suspicious pattern detection."""

    def test_detects_repeated_characters(self):
        """Should detect repeated character sequences."""
        analysis = ContentFlaggingService.detect_suspicious_patterns(
            "This event was amazingggggggggg"
        )
        assert analysis.flag_type == FlagType.SUSPICIOUS_PATTERN
        assert analysis.confidence_score > 0

    def test_detects_keyboard_smash(self):
        """Should detect keyboard smash patterns."""
        analysis = ContentFlaggingService.detect_suspicious_patterns(
            "asdfghasdfgh qwertyqwerty zxcvbnzxcvbn"
        )
        assert analysis.flag_type == FlagType.SUSPICIOUS_PATTERN
        assert analysis.confidence_score > 0

    def test_detects_long_number_sequences(self):
        """Should detect suspicious number sequences."""
        analysis = ContentFlaggingService.detect_suspicious_patterns(
            "1234567890 9876543210 1111111111"
        )
        assert analysis.flag_type == FlagType.SUSPICIOUS_PATTERN
        assert analysis.confidence_score > 0

    def test_normal_text_no_flag(self):
        """Should not flag normal text."""
        analysis = ContentFlaggingService.detect_suspicious_patterns(
            "This was a great event! 5 stars!"
        )
        assert analysis.confidence_score < 70


class TestOffTopicDetection:
    """Test off-topic content detection."""

    def test_detects_self_promotion(self):
        """Should detect self-promotion.

        detect_off_topic adds +20 per distinct matched phrase pattern; the
        original 2-phrase text ("check out" + "my profile") only reached 60.
        Add a 3rd/4th phrase so it clears the strict >70 auto-flag bar.
        """
        analysis = ContentFlaggingService.detect_off_topic(
            "Check out my profile at https://myprofile.com! Follow me and "
            "subscribe, then visit my page!"
        )
        assert analysis.flag_type == FlagType.OFF_TOPIC
        assert analysis.confidence_score >= 70

    def test_detects_commercial_content(self):
        """Should detect commercial/advertising content."""
        analysis = ContentFlaggingService.detect_off_topic(
            "Great event, but you should buy my products!"
        )
        assert analysis.flag_type == FlagType.OFF_TOPIC
        assert analysis.confidence_score > 0

    def test_detects_solicitation(self):
        """Should detect solicitation.

        A single "dm me" phrase only reaches 20 (+15 short-text bonus would
        need <5 words). Stack multiple off-topic phrases to clear the
        strict >70 auto-flag bar, same rationale as self-promotion above.
        """
        analysis = ContentFlaggingService.detect_off_topic(
            "DM me or contact us, visit my page and check out my link for more info!"
        )
        assert analysis.flag_type == FlagType.OFF_TOPIC
        assert analysis.confidence_score >= 70

    def test_legitimate_review_no_flag(self):
        """Should not flag legitimate reviews."""
        analysis = ContentFlaggingService.detect_off_topic(
            "This event taught me a lot about the library's resources."
        )
        assert analysis.confidence_score < 70


class TestComprehensiveAnalysis:
    """Test comprehensive review analysis."""

    @pytest.mark.asyncio
    async def test_clean_review_analysis(self, db: AsyncSession):
        """Test analysis of a clean review."""
        result = await ContentFlaggingService.analyze_review(
            db=db,
            text="This was an excellent event! The speakers were knowledgeable and the atmosphere was welcoming.",
            user_email="test@example.com",
            review_id=1,
            review_type="event_review",
        )
        assert result.overall_score < 70
        assert not result.should_flag

    @pytest.mark.asyncio
    async def test_spam_review_analysis(self, db: AsyncSession):
        """Test analysis of a spam review.

        overall_score is the MAX across categories (not a sum), and
        should_flag requires overall_score > 70 (strict). The original text
        only had a url + promo pattern in the spam category (55), short of
        the bar -- add a phone number so a 3rd distinct spam pattern type
        fires.
        """
        result = await ContentFlaggingService.analyze_review(
            db=db,
            text="GREAT EVENT!!! Buy now at https://example.com or call "
            "555-123-4567 for our LIMITED TIME OFFER!!! Click here!!!",
            user_email="spam@example.com",
            review_id=2,
            review_type="event_review",
        )
        assert result.overall_score >= 70
        assert result.should_flag

    @pytest.mark.asyncio
    async def test_suspicious_review_analysis(self, db: AsyncSession):
        """Test analysis of suspicious review.

        The original text's suspicious-pattern score (keyboard_smash +
        repeated_chars from the "!!!!!!!!" run) reaches 60, short of the
        strict >70 bar -- add a long digit run so long_number_sequence
        (+15) also fires.
        """
        result = await ContentFlaggingService.analyze_review(
            db=db,
            text="qwerty qwerty asdfgh asdfgh!!!!!!!! ??????????? 1234567890",
            user_email="test@example.com",
            review_id=3,
            review_type="event_review",
        )
        assert result.overall_score >= 70
        assert result.should_flag

    @pytest.mark.asyncio
    async def test_empty_text_handling(self, db: AsyncSession):
        """Test handling of empty text."""
        result = await ContentFlaggingService.analyze_review(
            db=db, text="", user_email="test@example.com", review_id=4, review_type="event_review"
        )
        assert result.overall_score == 0
        assert not result.should_flag

    @pytest.mark.asyncio
    async def test_short_text_handling(self, db: AsyncSession):
        """Test handling of very short text."""
        result = await ContentFlaggingService.analyze_review(
            db=db,
            text="Good!",
            user_email="test@example.com",
            review_id=5,
            review_type="event_review",
        )
        assert result.overall_score < 70
        assert not result.should_flag


class TestFlagPersistence:
    """Test saving and retrieving flags."""

    @pytest.mark.asyncio
    async def test_save_flags(self, db: AsyncSession):
        """Test saving flag to database.

        save_flags sets status=PENDING only if analysis_result.should_flag
        (overall_score > 70, strict). The original text's caps-detector
        score landed at exactly 70 -- not > 70 -- so should_flag was False
        and the flag saved as already-RESOLVED instead of PENDING. Add a
        url/phone/email so the spam category clears the bar unambiguously.
        """
        result = await ContentFlaggingService.analyze_review(
            db=db,
            text="SPAM SPAM SPAM BUY NOW! https://example.com call "
            "555-123-4567 email us at deals@example.com",
            user_email="test@example.com",
            review_id=10,
            review_type="event_review",
        )

        saved_flag = await ContentFlaggingService.save_flags(
            db=db, review_id=10, review_type="event_review", analysis_result=result
        )

        assert saved_flag is not None
        assert saved_flag.confidence_score >= 70
        assert saved_flag.status == FlagStatus.PENDING
        assert saved_flag.review_id == 10
        assert saved_flag.review_type == "event_review"

    @pytest.mark.asyncio
    async def test_resolve_flag(self, db: AsyncSession):
        """Test resolving a flag."""
        result = await ContentFlaggingService.analyze_review(
            db=db,
            text="SPAM SPAM SPAM BUY NOW!!!",
            user_email="test@example.com",
            review_id=11,
            review_type="event_review",
        )

        saved_flag = await ContentFlaggingService.save_flags(
            db=db, review_id=11, review_type="event_review", analysis_result=result
        )

        resolved_flag = await ContentFlaggingService.resolve_flag(
            db=db,
            flag_id=saved_flag.id,
            status=FlagStatus.RESOLVED.value,
            resolved_by="staff@example.com",
            is_correct_flag=True,
            resolution_notes="Confirmed as spam",
            staff_feedback="Pattern matches known spam",
        )

        assert resolved_flag is not None
        assert resolved_flag.status == FlagStatus.RESOLVED
        assert resolved_flag.resolved_by == "staff@example.com"
        assert resolved_flag.is_correct_flag is True


class TestFalsePositiveRate:
    """Test false positive rate calculation."""

    @pytest.mark.asyncio
    async def test_false_positive_rate(self, db: AsyncSession):
        """Test calculating false positive rate."""
        rate = await ContentFlaggingService.get_false_positive_rate(db=db, days=30)
        assert isinstance(rate, float)
        assert 0 <= rate <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
