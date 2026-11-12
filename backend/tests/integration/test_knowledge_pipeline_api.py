# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for the Knowledge Pipeline API.

Strategy (no live HTTP client needed):
- Router structure tests: verify route count and method/path combinations
- Schema validation tests: verify Pydantic models accept / reject inputs
- Service-call tests: verify endpoints delegate to the right service methods
  with correct arguments (services are mocked via unittest.mock)
"""

from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(is_admin: bool = False) -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.username = "teststaff"
    user.display_name = "Test Staff"
    user.role = "admin" if is_admin else "staff"
    return user


def _make_entry(entry_id: int = 1) -> MagicMock:
    entry = MagicMock()
    entry.id = entry_id
    entry.title = "Test Question"
    entry.content = "Test Answer"
    entry.category = "faq"
    entry.tags = None
    entry.persona_domain = "reference"
    entry.location_id = None
    entry.source_type = "manual"
    entry.review_status = "approved"
    entry.version = 1
    entry.added_by_id = 1
    entry.added_by_name = "Test Staff"
    entry.created_at = datetime.now(timezone.utc)
    entry.updated_at = datetime.now(timezone.utc)
    return entry


# ---------------------------------------------------------------------------
# 1. Router structure tests
# ---------------------------------------------------------------------------


class TestRouterStructure:
    """Verify the router exposes the correct routes."""

    def test_router_has_expected_routes(self):
        from app.api.v1.knowledge_pipeline import router

        routes = {(r.path, frozenset(r.methods)) for r in router.routes}

        expected_paths = {
            "/knowledge-pipeline/ingest/manual",
            "/knowledge-pipeline/ingest/document",
            "/knowledge-pipeline/generate-synthetic",
            "/knowledge-pipeline/conflicts",
            "/knowledge-pipeline/entries/{entry_id}",
            "/knowledge-pipeline/entries/{entry_id}/history",
            "/knowledge-pipeline/stats",
            # Patron opt-out/opt-in + admin retention routes added since this
            # test was written.
            "/knowledge-pipeline/patron-opt-out",
            "/knowledge-pipeline/patron-opt-in",
            "/knowledge-pipeline/patron-opt-out/status",
            "/knowledge-pipeline/admin/purge",
            "/knowledge-pipeline/admin/retention-stats",
            "/knowledge-pipeline/admin/run-retention",
            # Training-example review/export routes added since this test
            # was written.
            "/knowledge-pipeline/training/review-queue",
            "/knowledge-pipeline/training/{example_id}/approve",
            "/knowledge-pipeline/training/{example_id}/reject",
            "/knowledge-pipeline/training/{example_id}/override",
            "/knowledge-pipeline/training/stats",
            "/knowledge-pipeline/training/readiness/{persona_domain}",
            "/knowledge-pipeline/training/export",
            "/knowledge-pipeline/training/process-batch",
        }
        actual_paths = {path for path, _ in routes}
        assert expected_paths == actual_paths, (
            f"Missing paths: {expected_paths - actual_paths}; "
            f"Extra paths: {actual_paths - expected_paths}"
        )

    def test_router_route_count(self):
        from app.api.v1.knowledge_pipeline import router

        assert len(router.routes) == 21

    def test_router_prefix(self):
        from app.api.v1.knowledge_pipeline import router

        assert router.prefix == "/knowledge-pipeline"

    def test_router_tag(self):
        from app.api.v1.knowledge_pipeline import router

        assert "knowledge-pipeline" in router.tags

    def test_ingest_manual_is_post(self):
        from app.api.v1.knowledge_pipeline import router

        route = next(r for r in router.routes if r.path == "/knowledge-pipeline/ingest/manual")
        assert "POST" in route.methods

    def test_ingest_document_is_post(self):
        from app.api.v1.knowledge_pipeline import router

        route = next(r for r in router.routes if r.path == "/knowledge-pipeline/ingest/document")
        assert "POST" in route.methods

    def test_generate_synthetic_is_post(self):
        from app.api.v1.knowledge_pipeline import router

        route = next(r for r in router.routes if r.path == "/knowledge-pipeline/generate-synthetic")
        assert "POST" in route.methods

    def test_conflicts_is_get(self):
        from app.api.v1.knowledge_pipeline import router

        route = next(r for r in router.routes if r.path == "/knowledge-pipeline/conflicts")
        assert "GET" in route.methods

    def test_update_entry_is_put(self):
        from app.api.v1.knowledge_pipeline import router

        route = next(r for r in router.routes if r.path == "/knowledge-pipeline/entries/{entry_id}")
        assert "PUT" in route.methods

    def test_history_is_get(self):
        from app.api.v1.knowledge_pipeline import router

        route = next(
            r for r in router.routes if r.path == "/knowledge-pipeline/entries/{entry_id}/history"
        )
        assert "GET" in route.methods

    def test_stats_is_get(self):
        from app.api.v1.knowledge_pipeline import router

        route = next(r for r in router.routes if r.path == "/knowledge-pipeline/stats")
        assert "GET" in route.methods


# ---------------------------------------------------------------------------
# 2. Request schema validation tests
# ---------------------------------------------------------------------------


class TestManualIngestRequestSchema:
    def test_valid_minimal(self):
        from app.api.v1.knowledge_pipeline import ManualIngestRequest

        req = ManualIngestRequest(title="Q", content="A", category="faq")
        assert req.title == "Q"
        assert req.persona_domain is None

    def test_valid_full(self):
        from app.api.v1.knowledge_pipeline import ManualIngestRequest

        req = ManualIngestRequest(
            title="Where are the bathrooms?",
            content="First floor near the elevator.",
            category="faq",
            tags="directions,facilities",
            persona_domain="reference",
            location_id=3,
            entry_metadata={"source": "staff"},
        )
        assert req.location_id == 3
        assert req.tags == "directions,facilities"

    def test_empty_title_rejected(self):
        from pydantic import ValidationError

        from app.api.v1.knowledge_pipeline import ManualIngestRequest

        with pytest.raises(ValidationError):
            ManualIngestRequest(title="", content="A", category="faq")

    def test_empty_content_rejected(self):
        from pydantic import ValidationError

        from app.api.v1.knowledge_pipeline import ManualIngestRequest

        with pytest.raises(ValidationError):
            ManualIngestRequest(title="Q", content="", category="faq")

    def test_missing_required_fields_rejected(self):
        from pydantic import ValidationError

        from app.api.v1.knowledge_pipeline import ManualIngestRequest

        with pytest.raises(ValidationError):
            ManualIngestRequest(title="Q")  # missing content and category


class TestDocumentIngestRequestSchema:
    def test_valid(self):
        from app.api.v1.knowledge_pipeline import DocumentIngestRequest

        req = DocumentIngestRequest(document_id=42)
        assert req.document_id == 42
        assert req.category == "faq"  # default

    def test_custom_category(self):
        from app.api.v1.knowledge_pipeline import DocumentIngestRequest

        req = DocumentIngestRequest(document_id=1, category="policy", persona_domain="youth")
        assert req.category == "policy"
        assert req.persona_domain == "youth"

    def test_missing_document_id_rejected(self):
        from pydantic import ValidationError

        from app.api.v1.knowledge_pipeline import DocumentIngestRequest

        with pytest.raises(ValidationError):
            DocumentIngestRequest()


class TestSyntheticGenerateRequestSchema:
    def test_defaults(self):
        from app.api.v1.knowledge_pipeline import SyntheticGenerateRequest

        req = SyntheticGenerateRequest()
        assert req.limit == 50
        assert req.persona_domain is None

    def test_custom_limit(self):
        from app.api.v1.knowledge_pipeline import SyntheticGenerateRequest

        req = SyntheticGenerateRequest(limit=100, persona_domain="digital")
        assert req.limit == 100

    def test_limit_too_low_rejected(self):
        from pydantic import ValidationError

        from app.api.v1.knowledge_pipeline import SyntheticGenerateRequest

        with pytest.raises(ValidationError):
            SyntheticGenerateRequest(limit=0)

    def test_limit_too_high_rejected(self):
        from pydantic import ValidationError

        from app.api.v1.knowledge_pipeline import SyntheticGenerateRequest

        with pytest.raises(ValidationError):
            SyntheticGenerateRequest(limit=201)


class TestEntryUpdateRequestSchema:
    def test_all_optional(self):
        from app.api.v1.knowledge_pipeline import EntryUpdateRequest

        req = EntryUpdateRequest()
        assert req.title is None
        assert req.review_status is None

    def test_valid_review_status(self):
        from app.api.v1.knowledge_pipeline import EntryUpdateRequest

        for status in ("pending", "approved", "rejected"):
            req = EntryUpdateRequest(review_status=status)
            assert req.review_status == status

    def test_invalid_review_status_rejected(self):
        from pydantic import ValidationError

        from app.api.v1.knowledge_pipeline import EntryUpdateRequest

        with pytest.raises(ValidationError):
            EntryUpdateRequest(review_status="unknown_status")

    def test_empty_title_rejected(self):
        from pydantic import ValidationError

        from app.api.v1.knowledge_pipeline import EntryUpdateRequest

        with pytest.raises(ValidationError):
            EntryUpdateRequest(title="")


# ---------------------------------------------------------------------------
# 3. Service delegation tests (mocked services)
# ---------------------------------------------------------------------------


class TestIngestManualEndpoint:
    @pytest.mark.asyncio
    async def test_calls_pipeline_ingest_manual_with_correct_args(self):
        from app.api.v1.knowledge_pipeline import ingest_manual, ManualIngestRequest

        mock_entry = _make_entry()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        payload = ManualIngestRequest(
            title="Where are the bathrooms?",
            content="Near the elevator on the first floor.",
            category="faq",
            persona_domain="reference",
        )
        current_user = _make_user()

        with patch("app.api.v1.knowledge_pipeline.KnowledgePipelineService") as MockSvc:
            instance = MockSvc.return_value
            instance.ingest_manual = AsyncMock(return_value=mock_entry)

            result = await ingest_manual(payload, current_user=current_user, db=mock_db)

        instance.ingest_manual.assert_awaited_once()
        call_kwargs = instance.ingest_manual.call_args.kwargs
        assert call_kwargs["title"] == "Where are the bathrooms?"
        assert call_kwargs["category"] == "faq"
        assert call_kwargs["added_by_id"] == current_user.id
        assert call_kwargs["persona_domain"] == "reference"
        assert result is mock_entry


class TestIngestDocumentEndpoint:
    @pytest.mark.asyncio
    async def test_queues_background_task(self):
        from app.api.v1.knowledge_pipeline import ingest_document, DocumentIngestRequest

        payload = DocumentIngestRequest(document_id=99, category="policy", persona_domain="youth")
        current_user = _make_user()
        background_tasks = MagicMock()
        background_tasks.add_task = MagicMock()

        result = await ingest_document(
            payload, background_tasks=background_tasks, current_user=current_user
        )

        background_tasks.add_task.assert_called_once()
        call_args = background_tasks.add_task.call_args
        # First positional arg is the coroutine function, rest are its arguments
        assert call_args.args[1] == 99  # document_id
        assert call_args.args[2] == "policy"  # category
        assert call_args.args[3] == "youth"  # persona_domain
        assert result["status"] == "accepted"


class TestGenerateSyntheticEndpoint:
    @pytest.mark.asyncio
    async def test_queues_background_task(self):
        from app.api.v1.knowledge_pipeline import generate_synthetic, SyntheticGenerateRequest

        payload = SyntheticGenerateRequest(persona_domain="digital", limit=25)
        current_user = _make_user(is_admin=True)
        background_tasks = MagicMock()
        background_tasks.add_task = MagicMock()

        result = await generate_synthetic(
            payload, background_tasks=background_tasks, current_user=current_user
        )

        background_tasks.add_task.assert_called_once()
        call_args = background_tasks.add_task.call_args
        assert call_args.args[1] == "digital"  # persona_domain
        assert call_args.args[2] == 25  # limit
        assert result["status"] == "accepted"


class TestScanConflictsEndpoint:
    @pytest.mark.asyncio
    async def test_calls_conflict_service_scan_all(self):
        from app.api.v1.knowledge_pipeline import scan_conflicts

        mock_db = AsyncMock()
        current_user = _make_user()

        expected_conflicts = [
            {
                "entry_a_id": 1,
                "entry_a_title": "A",
                "entry_b_id": 2,
                "entry_b_title": "B",
                "similarity": 0.95,
                "domain": "reference",
            }
        ]

        with patch("app.api.v1.knowledge_pipeline.ConflictDetectionService") as MockSvc:
            instance = MockSvc.return_value
            instance.scan_all = AsyncMock(return_value=expected_conflicts)

            result = await scan_conflicts(
                persona_domain="reference", current_user=current_user, db=mock_db
            )

        instance.scan_all.assert_awaited_once_with(mock_db, persona_domain="reference")
        assert result == expected_conflicts

    @pytest.mark.asyncio
    async def test_no_domain_filter_passes_none(self):
        from app.api.v1.knowledge_pipeline import scan_conflicts

        mock_db = AsyncMock()
        current_user = _make_user()

        with patch("app.api.v1.knowledge_pipeline.ConflictDetectionService") as MockSvc:
            instance = MockSvc.return_value
            instance.scan_all = AsyncMock(return_value=[])

            await scan_conflicts(persona_domain=None, current_user=current_user, db=mock_db)

        instance.scan_all.assert_awaited_once_with(mock_db, persona_domain=None)


class TestUpdateEntryEndpoint:
    @pytest.mark.asyncio
    async def test_calls_update_with_correct_args(self):
        from app.api.v1.knowledge_pipeline import update_entry, EntryUpdateRequest

        mock_entry = _make_entry(entry_id=7)
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        current_user = _make_user()

        payload = EntryUpdateRequest(
            title="Updated Title",
            review_status="approved",
            change_reason="Fixed typo",
        )

        with patch("app.api.v1.knowledge_pipeline.KnowledgePipelineService") as MockSvc:
            instance = MockSvc.return_value
            instance.update_entry = AsyncMock(return_value=mock_entry)

            result = await update_entry(
                entry_id=7, payload=payload, current_user=current_user, db=mock_db
            )

        instance.update_entry.assert_awaited_once()
        call_kwargs = instance.update_entry.call_args.kwargs
        assert call_kwargs["title"] == "Updated Title"
        assert call_kwargs["review_status"] == "approved"
        assert call_kwargs["change_reason"] == "Fixed typo"
        assert call_kwargs["changed_by_id"] == current_user.id
        assert result is mock_entry

    @pytest.mark.asyncio
    async def test_raises_404_when_entry_not_found(self):
        from fastapi import HTTPException

        from app.api.v1.knowledge_pipeline import update_entry, EntryUpdateRequest

        mock_db = AsyncMock()
        current_user = _make_user()
        payload = EntryUpdateRequest(title="X")

        with patch("app.api.v1.knowledge_pipeline.KnowledgePipelineService") as MockSvc:
            instance = MockSvc.return_value
            instance.update_entry = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await update_entry(
                    entry_id=999, payload=payload, current_user=current_user, db=mock_db
                )

        assert exc_info.value.status_code == 404


class TestGetEntryHistoryEndpoint:
    @pytest.mark.asyncio
    async def test_returns_versions_for_existing_entry(self):
        from app.api.v1.knowledge_pipeline import get_entry_history

        mock_db = AsyncMock()
        current_user = _make_user()

        v1 = MagicMock()
        v1.id = 10
        v1.knowledge_entry_id = 5
        v1.version_number = 2
        v2 = MagicMock()
        v2.id = 9
        v2.knowledge_entry_id = 5
        v2.version_number = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [v1, v2]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_entry_history(entry_id=5, current_user=current_user, db=mock_db)

        assert len(result) == 2
        assert result[0].version_number == 2  # descending order preserved

    @pytest.mark.asyncio
    async def test_raises_404_for_unknown_entry_with_no_versions(self):
        from fastapi import HTTPException

        from app.api.v1.knowledge_pipeline import get_entry_history

        mock_db = AsyncMock()
        current_user = _make_user()

        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []

        count_result = MagicMock()
        count_result.__class__ = int

        mock_db.execute = AsyncMock(return_value=empty_result)
        mock_db.scalar = AsyncMock(return_value=0)

        with pytest.raises(HTTPException) as exc_info:
            await get_entry_history(entry_id=9999, current_user=current_user, db=mock_db)

        assert exc_info.value.status_code == 404


class TestGetStatsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_stats_structure(self):
        from app.api.v1.knowledge_pipeline import get_stats

        mock_db = AsyncMock()
        current_user = _make_user()

        # scalar() returns total count
        mock_db.scalar = AsyncMock(return_value=42)

        # execute() returns different row sets for source/status/domain queries
        source_rows = [("manual", 30), ("document_import", 10), ("synthetic", 2)]
        status_rows = [("approved", 38), ("pending", 4)]
        domain_rows = [("reference", 20), (None, 22)]

        def make_result(rows):
            r = MagicMock()
            r.__iter__ = MagicMock(return_value=iter(rows))
            return r

        mock_db.execute = AsyncMock(
            side_effect=[
                make_result(source_rows),
                make_result(status_rows),
                make_result(domain_rows),
            ]
        )

        result = await get_stats(current_user=current_user, db=mock_db)

        assert result["total_entries"] == 42
        assert "by_source" in result
        assert "by_status" in result
        assert "by_domain" in result
        assert result["by_source"]["manual"] == 30
        assert result["by_status"]["approved"] == 38
        # None domain mapped to "unset"
        assert "unset" in result["by_domain"]
