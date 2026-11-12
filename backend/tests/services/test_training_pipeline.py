# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for training data pipeline: scoring, formatting, and orchestration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from app.services.quality_scoring_service import QualityScoringService, QualityScore
from app.services.training_data_formatter_service import TrainingDataFormatterService
from app.services.training_pipeline_service import TrainingPipelineService


class TestQualityScoring:
    @pytest.mark.asyncio
    async def test_manual_entry_scores_high(self):
        """Manual staff entries should score well on staff_correction and consistency."""
        scorer = QualityScoringService()
        entry = MagicMock()
        entry.source_type = "manual"
        entry.review_status = "approved"
        entry.entry_metadata = {}
        entry.expires_at = None
        entry.title = "Library Hours"
        entry.content = "Q: What are your hours?\nA: We are open Monday through Friday from 9am to 8pm and Saturday from 10am to 5pm."
        entry.source_reference_id = None
        entry.id = 1

        db = AsyncMock()
        db.scalar = AsyncMock(return_value=0)

        result = await scorer.score_entry(db, entry)
        assert result.total >= 60
        assert result.breakdown["staff_correction"] == 100
        assert result.breakdown["freshness"] == 100
        assert result.bucket in ("approved", "review")

    @pytest.mark.asyncio
    async def test_expired_entry_scores_zero_freshness(self):
        scorer = QualityScoringService()
        entry = MagicMock()
        entry.source_type = "manual"
        entry.review_status = "approved"
        entry.entry_metadata = {}
        entry.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        entry.title = "Summer Program"
        entry.content = "Q: Summer program?\nA: It ended."
        entry.source_reference_id = None
        entry.id = 2

        db = AsyncMock()
        db.scalar = AsyncMock(return_value=0)

        result = await scorer.score_entry(db, entry)
        assert result.breakdown["freshness"] == 0

    def test_bucket_assignment(self):
        assert QualityScoringService.assign_bucket(85) == "approved"
        assert QualityScoringService.assign_bucket(60) == "review"
        assert QualityScoringService.assign_bucket(30) == "rejected"
        assert QualityScoringService.assign_bucket(80) == "approved"
        assert QualityScoringService.assign_bucket(40) == "review"
        assert QualityScoringService.assign_bucket(39) == "rejected"

    def test_completeness_scoring(self):
        scorer = QualityScoringService()

        # Good completeness — both Q and A exceed word thresholds
        entry = MagicMock()
        entry.title = "What are the library hours on weekdays and weekends for all branches"
        entry.content = "Q: What are the library hours on weekdays and weekends for all branches?\nA: The library is open Monday through Friday from 9am to 8pm and Saturday from 10am to 5pm. We have extended hours during finals week for university students."
        assert scorer._score_completeness(entry) == 100

        # Short answer
        entry2 = MagicMock()
        entry2.title = "Hours?"
        entry2.content = "Q: Hours?\nA: 9 to 5."
        assert scorer._score_completeness(entry2) == 0


class TestTrainingDataFormatter:
    def test_format_qa_entry(self):
        formatter = TrainingDataFormatterService()
        entry = MagicMock()
        entry.title = "Library Hours"
        entry.content = "Q: What are your hours?\nA: We are open 9am to 8pm weekdays."

        pairs = formatter.format_entry(entry)
        assert len(pairs) == 1
        assert "hours" in pairs[0]["instruction"].lower()
        assert "9am" in pairs[0]["response"]

    def test_format_plain_entry(self):
        formatter = TrainingDataFormatterService()
        entry = MagicMock()
        entry.title = "How do I get a library card?"
        entry.content = "Visit any branch with a valid photo ID and proof of address."

        pairs = formatter.format_entry(entry)
        assert len(pairs) == 1
        assert pairs[0]["instruction"] == "How do I get a library card?"

    def test_format_multi_turn(self):
        formatter = TrainingDataFormatterService()
        entry = MagicMock()
        entry.title = "Gardening conversation"
        entry.content = (
            "User: Do you have gardening books?\n"
            "Assistant: Yes! Check section 635.\n"
            "User: Any about container gardening?\n"
            "Assistant: We have three great container gardening guides."
        )

        pairs = formatter.format_entry(entry)
        assert len(pairs) == 2
        assert pairs[0]["is_multi_turn"] is True
        assert pairs[0]["turn_index"] == 0
        assert pairs[1]["turn_index"] == 1

    def test_export_jsonl(self):
        formatter = TrainingDataFormatterService()
        data = [
            {"instruction": "What time do you close?", "response": "We close at 8pm."},
            {"instruction": "Do you have WiFi?", "response": "Yes, free WiFi is available."},
        ]
        jsonl = formatter.export_jsonl(data)
        lines = jsonl.strip().split("\n")
        assert len(lines) == 2
        import json
        first = json.loads(lines[0])
        assert first["messages"][0]["role"] == "user"
        assert first["messages"][1]["role"] == "assistant"

    def test_empty_entry(self):
        formatter = TrainingDataFormatterService()
        entry = MagicMock()
        entry.title = ""
        entry.content = ""
        assert formatter.format_entry(entry) == []


class TestTrainingPipeline:
    @pytest.mark.asyncio
    async def test_process_entry_creates_examples(self):
        pipeline = TrainingPipelineService()
        db = AsyncMock()

        entry = MagicMock()
        entry.id = 1
        entry.title = "Library card"
        entry.content = "Q: How do I get a card?\nA: Visit any branch with valid ID and proof of address to get your free library card."
        entry.source_type = "manual"
        entry.review_status = "approved"
        entry.entry_metadata = {}
        entry.expires_at = None
        entry.persona_domain = "shared"
        entry.location_id = None
        entry.source_reference_id = None

        # Mock db.execute to return entry and no existing examples
        mock_entry_result = MagicMock()
        mock_entry_result.scalar_one_or_none.return_value = entry

        db.execute = AsyncMock(return_value=mock_entry_result)
        db.scalar = AsyncMock(return_value=0)  # No existing examples
        db.add = MagicMock()
        db.flush = AsyncMock()

        examples = await pipeline.process_entry(db, 1)
        assert len(examples) >= 1
        assert examples[0].instruction is not None

    @pytest.mark.asyncio
    async def test_readiness_check(self):
        pipeline = TrainingPipelineService()
        db = AsyncMock()
        db.scalar = AsyncMock(return_value=500)
        db.execute = AsyncMock(return_value=MagicMock(
            __iter__=lambda self: iter([("manual", 300), ("patron_interaction", 200)])
        ))

        result = await pipeline.get_readiness(db, "reference")
        assert result["persona_domain"] == "reference"
        assert result["approved_count"] == 500
        assert result["threshold"] == 1000
        assert result["ready"] is False  # < 1000
