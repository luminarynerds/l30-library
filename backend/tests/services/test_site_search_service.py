# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for SiteSearchService — current pipeline (post indie-author removal).

Covers ebook dedup in search() (PRIMARY), happy-paths for each active _search_*
method, and orchestrator concerns (ranking, capping, faceting, filter, gating).

Mocks at the right boundary: _search_* methods on the service for dedup tests,
db.execute / metislib client for per-method tests. _is_postgres is falsy under
AsyncMock db, forcing the catalog ILIKE path.
"""

from contextlib import ExitStack

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.site_search_service import (
    SiteSearchService,
    SiteSearchResult,
    SiteSearchResponse,
    _score_text,
)


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    return SiteSearchService(mock_db)


def _make_result(
    id: str,
    entity_type: str,
    title: str,
    score: float,
    *,
    url: str = "/test",
    source: str = "test",
) -> SiteSearchResult:
    return SiteSearchResult(
        id=id, entity_type=entity_type, title=title, snippet=None,
        url=url, score=score, source=source,
    )


def _patch_subs(service, **overrides):
    """Patch every _search_* method. Returns an ExitStack context manager.
    Pass keyword overrides to provide non-empty results for specific subs."""
    defaults = {
        "_search_catalog": [], "_search_ebooks": [], "_search_events": [],
        "_search_announcements": [], "_search_pages": [],
    }
    defaults.update(overrides)
    stack = ExitStack()
    for name, value in defaults.items():
        stack.enter_context(patch.object(service, name, AsyncMock(return_value=value)))
    return stack


@pytest.fixture
def patched_analytics():
    """Stub analytics + feature flags: no CTR boosts, no did-you-mean,
    all feature flags ON, log_query is a no-op."""
    with patch(
        "app.services.site_search_service.analytics.ctr_boosts_for_query",
        AsyncMock(return_value={}),
    ), patch(
        "app.services.site_search_service.analytics.did_you_mean",
        AsyncMock(return_value=None),
    ), patch(
        "app.services.site_search_service.analytics.log_query",
        AsyncMock(return_value=None),
    ), patch(
        "app.services.site_search_service.OrganizationFeaturesService.is_feature_enabled",
        AsyncMock(return_value=True),
    ):
        yield


# ---- Ebook dedup (PRIMARY) ----


class TestEbookDedup:
    """Locks down the dedup loop in SiteSearchService.search():
    same-titled ebooks collapse, higher-score wins, case-insensitive,
    non-ebooks unaffected, cross-type same-title preserved.
    """

    @pytest.mark.asyncio
    async def test_same_title_ebooks_dedupe_to_one(self, service, patched_analytics):
        local = _make_result("catalog:1", "ebook", "The Garden", 0.85)
        network = _make_result("ebook:99", "ebook", "The Garden", 0.90)
        with _patch_subs(service, _search_ebooks=[local, network]):
            response = await service.search("garden")
        ebooks = [r for r in response.results if r.entity_type == "ebook"]
        assert len(ebooks) == 1

    @pytest.mark.asyncio
    async def test_higher_score_ebook_wins_dedup(self, service, patched_analytics):
        low = _make_result("ebook:low", "ebook", "Same Title", 0.50)
        high = _make_result("ebook:high", "ebook", "Same Title", 0.95)
        with _patch_subs(service, _search_ebooks=[low, high]):
            response = await service.search("title")
        ebooks = [r for r in response.results if r.entity_type == "ebook"]
        assert len(ebooks) == 1
        assert ebooks[0].id == "ebook:high"
        assert ebooks[0].score == pytest.approx(0.95)

    @pytest.mark.asyncio
    async def test_title_dedup_is_case_insensitive(self, service, patched_analytics):
        upper = _make_result("ebook:1", "ebook", "THE GARDEN", 0.80)
        mixed = _make_result("ebook:2", "ebook", "The Garden", 0.90)
        with _patch_subs(service, _search_ebooks=[upper, mixed]):
            response = await service.search("garden")
        assert len([r for r in response.results if r.entity_type == "ebook"]) == 1

    @pytest.mark.asyncio
    async def test_different_ebook_titles_both_kept(self, service, patched_analytics):
        a = _make_result("ebook:1", "ebook", "Alpha Book", 0.90)
        b = _make_result("ebook:2", "ebook", "Beta Book", 0.80)
        with _patch_subs(service, _search_ebooks=[a, b]):
            response = await service.search("book")
        titles = {r.title for r in response.results if r.entity_type == "ebook"}
        assert titles == {"Alpha Book", "Beta Book"}

    @pytest.mark.asyncio
    async def test_non_ebook_results_not_deduped_by_title(
        self, service, patched_analytics
    ):
        """Catalog dedup is intentionally NOT in this pipeline. Two catalog
        items with the same title must both survive."""
        a = _make_result("catalog:1", "catalog", "Same Title", 0.85)
        b = _make_result("catalog:2", "catalog", "Same Title", 0.80)
        with _patch_subs(service, _search_catalog=[a, b]):
            response = await service.search("title")
        assert len([r for r in response.results if r.entity_type == "catalog"]) == 2

    @pytest.mark.asyncio
    async def test_catalog_and_ebook_same_title_both_kept(
        self, service, patched_analytics
    ):
        """Different entity_types with the same title are NOT cross-deduped."""
        cat = _make_result("catalog:1", "catalog", "The Garden", 0.85)
        ebk = _make_result("ebook:99", "ebook", "The Garden", 0.90)
        with _patch_subs(
            service, _search_catalog=[cat], _search_ebooks=[ebk]
        ):
            response = await service.search("garden")
        assert sorted(r.entity_type for r in response.results) == ["catalog", "ebook"]


# ---- Per-method happy paths ----


def _row(**attrs) -> MagicMock:
    r = MagicMock()
    for k, v in attrs.items():
        setattr(r, k, v)
    return r


def _execute_returning(rows):
    return AsyncMock(return_value=MagicMock(all=MagicMock(return_value=rows)))


class TestSearchCatalogIlike:
    """ILIKE fallback runs because _is_postgres is False under our mock_db."""

    @pytest.mark.asyncio
    async def test_returns_cataloged_item_with_expected_shape(self, service, mock_db):
        row = _row(
            id=42, title="The Hobbit", author="J.R.R. Tolkien",
            description="There and back again.", total_checkouts=100,
        )
        mock_db.execute = _execute_returning([row])

        results = await service._search_catalog("%hobbit%", "hobbit", limit=20)

        assert len(results) == 1
        r = results[0]
        assert r.id == "catalog:42"
        assert r.entity_type == "catalog"
        assert r.title == "The Hobbit"
        assert r.url == "/catalog/42"
        assert r.source == "catalog"
        assert r.score > 0

    @pytest.mark.asyncio
    async def test_empty_when_no_rows(self, service, mock_db):
        mock_db.execute = _execute_returning([])
        assert await service._search_catalog("%zzz%", "zzz", limit=20) == []


class TestSearchEbooks:
    @pytest.mark.asyncio
    async def test_returns_metislib_items_when_enabled(self, service):
        fake_client = MagicMock()
        fake_client.search_catalog = AsyncMock(return_value={
            "items": [{
                "id": 7, "title": "Indie Book",
                "author_name": "Author Name", "description": "An indie ebook.",
            }]
        })
        with patch(
            "app.services.site_search_service.get_settings",
            return_value=MagicMock(metislib_enabled=True),
        ), patch(
            "app.services.metislib_client.get_metislib_client",
            return_value=fake_client,
        ):
            results = await service._search_ebooks("indie", limit=10)

        assert len(results) == 1
        r = results[0]
        assert r.id == "ebook:7"
        assert r.entity_type == "ebook"
        assert r.title == "Indie Book"
        assert r.url == "/ebooks/7"
        assert r.source == "ebooks"

    @pytest.mark.asyncio
    async def test_returns_empty_when_metislib_disabled(self, service):
        with patch(
            "app.services.site_search_service.get_settings",
            return_value=MagicMock(metislib_enabled=False),
        ):
            assert await service._search_ebooks("anything", limit=10) == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_metislib_client_errors(self, service):
        fake_client = MagicMock()
        fake_client.search_catalog = AsyncMock(side_effect=RuntimeError("boom"))
        with patch(
            "app.services.site_search_service.get_settings",
            return_value=MagicMock(metislib_enabled=True),
        ), patch(
            "app.services.metislib_client.get_metislib_client",
            return_value=fake_client,
        ):
            assert await service._search_ebooks("anything", limit=10) == []


class TestSearchEvents:
    @pytest.mark.asyncio
    async def test_returns_published_future_event(self, service, mock_db):
        row = _row(
            id=11, title="Book Club", description="Monthly book club.",
            location="Main Branch", start_time=None,
        )
        mock_db.execute = _execute_returning([row])

        results = await service._search_events("%book%", "book", limit=10)

        assert len(results) == 1
        r = results[0]
        assert r.id == "event:11"
        assert r.entity_type == "event"
        assert r.url == "/events/detail/11"
        assert r.source == "events"


class TestSearchAnnouncements:
    @pytest.mark.asyncio
    async def test_returns_active_published_announcement(self, service, mock_db):
        row = _row(id=5, title="Holiday Hours", content="We are closed on Monday.")
        mock_db.execute = _execute_returning([row])

        results = await service._search_announcements("%holiday%", "holiday", limit=10)

        assert len(results) == 1
        r = results[0]
        assert r.id == "announcement:5"
        assert r.entity_type == "announcement"
        assert r.url == "/announcements#announcement-5"
        assert r.source == "announcements"


class TestSearchPages:
    @pytest.mark.asyncio
    async def test_returns_unflagged_page_match(self, service):
        """Pages with no feature flag are always available."""
        with patch(
            "app.services.site_search_service.OrganizationFeaturesService.is_feature_enabled",
            AsyncMock(return_value=True),
        ):
            results = await service._search_pages("contact")
        assert any(r.url == "/contact" for r in results)

    @pytest.mark.asyncio
    async def test_flagged_page_hidden_when_feature_disabled(self, service):
        """events_enabled=False must hide the /events page."""
        async def feature(_db, name):
            return name != "events_enabled"
        with patch(
            "app.services.site_search_service.OrganizationFeaturesService.is_feature_enabled",
            side_effect=feature,
        ):
            results = await service._search_pages("events")
        assert "/events" not in {r.url for r in results}


# ---- Orchestrator-level ----


class TestSearchOrchestrator:
    @pytest.mark.asyncio
    async def test_empty_query_short_circuits(self, service):
        """Whitespace query returns an empty SiteSearchResponse."""
        with _patch_subs(service):
            response = await service.search("   ")
        assert isinstance(response, SiteSearchResponse)
        assert response.total_results == 0
        assert response.results == []
        assert response.has_more is False

    @pytest.mark.asyncio
    async def test_results_ranked_by_score_descending(
        self, service, patched_analytics
    ):
        low = _make_result("announcement:1", "announcement", "Low", 0.55)
        mid = _make_result("event:1", "event", "Mid", 0.70)
        high = _make_result("catalog:1", "catalog", "High", 0.95)
        with _patch_subs(
            service,
            _search_catalog=[high],
            _search_events=[mid],
            _search_announcements=[low],
        ):
            response = await service.search("anything")
        scores = [r.score for r in response.results]
        assert scores == sorted(scores, reverse=True)
        assert response.results[0].id == "catalog:1"
        assert response.results[-1].id == "announcement:1"

    @pytest.mark.asyncio
    async def test_per_page_caps_results(self, service, patched_analytics):
        many = [
            _make_result(f"catalog:{i}", "catalog", f"T{i}", 0.9 - i * 0.01)
            for i in range(10)
        ]
        with _patch_subs(service, _search_catalog=many):
            response = await service.search("t", per_page=3)
        assert len(response.results) == 3
        assert response.total_results == 10
        assert response.has_more is True

    @pytest.mark.asyncio
    async def test_facets_count_by_entity_type(self, service, patched_analytics):
        with _patch_subs(
            service,
            _search_catalog=[
                _make_result("catalog:1", "catalog", "A", 0.9),
                _make_result("catalog:2", "catalog", "B", 0.8),
            ],
            _search_events=[_make_result("event:1", "event", "E", 0.7)],
        ):
            response = await service.search("anything")
        assert response.facets.get("catalog") == 2
        assert response.facets.get("event") == 1

    @pytest.mark.asyncio
    async def test_entity_type_filter_narrows_results(
        self, service, patched_analytics
    ):
        """entity_types filter drops other types but facets are computed
        BEFORE filtering so dropped buckets still report counts."""
        with _patch_subs(
            service,
            _search_catalog=[_make_result("catalog:1", "catalog", "A", 0.9)],
            _search_events=[_make_result("event:1", "event", "E", 0.7)],
        ):
            response = await service.search("anything", entity_types=["catalog"])
        assert {r.entity_type for r in response.results} == {"catalog"}
        assert response.facets.get("event") == 1


# ---- Feature flag gating ----


class TestFeatureFlagGating:
    @pytest.mark.asyncio
    async def test_events_skipped_when_flag_disabled(self, service):
        """events_enabled=False: orchestrator must NOT call _search_events."""
        events_mock = AsyncMock(return_value=[])
        with patch(
            "app.services.site_search_service.OrganizationFeaturesService.is_feature_enabled",
            AsyncMock(return_value=False),
        ), patch(
            "app.services.site_search_service.analytics.ctr_boosts_for_query",
            AsyncMock(return_value={}),
        ), patch(
            "app.services.site_search_service.analytics.did_you_mean",
            AsyncMock(return_value=None),
        ), patch(
            "app.services.site_search_service.analytics.log_query",
            AsyncMock(return_value=None),
        ), patch.object(service, "_search_catalog", AsyncMock(return_value=[])
        ), patch.object(service, "_search_ebooks", AsyncMock(return_value=[])
        ), patch.object(service, "_search_events", events_mock
        ), patch.object(service, "_search_announcements", AsyncMock(return_value=[])
        ), patch.object(service, "_search_pages", AsyncMock(return_value=[])):
            await service.search("anything")
        events_mock.assert_not_called()


# ---- Cursor decoding ----


class TestDecodeCursor:
    """Tests for _decode_cursor: narrow exception handling + logging.

    The cursor is base64(json({"s": <float>, "id": <str>})) with "=" padding
    stripped. Malformed input must degrade to None (page 1) AND emit a warning.
    """

    def test_valid_cursor_round_trips(self):
        """Happy path: encode -> decode returns the same (score, id)."""
        from app.services.site_search_service import _encode_cursor, _decode_cursor

        token = _encode_cursor(0.875432, "catalog:123")
        result = _decode_cursor(token)

        assert result is not None
        score, result_id = result
        assert score == pytest.approx(0.875432, abs=1e-6)
        assert result_id == "catalog:123"

    def test_malformed_base64_returns_none_and_logs(self, caplog):
        """Garbage base64 (non-b64 chars) degrades to None and emits a warning."""
        import logging
        from app.services.site_search_service import _decode_cursor

        with caplog.at_level(logging.WARNING, logger="app.services.site_search_service"):
            result = _decode_cursor("!!!not-valid-base64$$$")

        assert result is None
        assert any(
            r.levelno == logging.WARNING and "cursor" in r.message.lower()
            for r in caplog.records
        ), f"expected a warning mentioning cursor, got: {[r.message for r in caplog.records]}"

    def test_valid_base64_invalid_json_returns_none_and_logs(self, caplog):
        """Valid base64 wrapping non-JSON bytes degrades to None and logs."""
        import base64
        import logging
        from app.services.site_search_service import _decode_cursor

        bogus = base64.urlsafe_b64encode(b"this is not json at all").decode().rstrip("=")
        with caplog.at_level(logging.WARNING, logger="app.services.site_search_service"):
            result = _decode_cursor(bogus)

        assert result is None
        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_valid_json_wrong_shape_returns_none(self, caplog):
        """JSON that decodes but lacks the expected keys degrades to None."""
        import base64
        import json
        import logging
        from app.services.site_search_service import _decode_cursor

        wrong_shape = base64.urlsafe_b64encode(
            json.dumps({"unrelated": "field"}).encode()
        ).decode().rstrip("=")

        with caplog.at_level(logging.WARNING, logger="app.services.site_search_service"):
            result = _decode_cursor(wrong_shape)

        assert result is None
# ---- Body-length-aware scoring ----


class TestScoreText:
    """Body-match scoring must differentiate by body length: a short body that
    mentions the query is more topical than a long body that mentions it once
    in passing. Title-match dominance must be preserved."""

    def test_short_body_outscores_long_body_on_substring_hit(self):
        """A ~50-word body containing the query once must score strictly
        higher than a ~5000-word body containing the query once."""
        query = "garden"
        # ~50-word body, one "garden" occurrence
        short_body = "garden " + " ".join(f"word{i}" for i in range(49))
        # ~5000-word body, one "garden" occurrence
        long_body = "garden " + " ".join(f"word{i}" for i in range(4999))
        assert short_body.lower().count(query) == 1
        assert long_body.lower().count(query) == 1
        assert len(short_body.split()) == 50
        assert len(long_body.split()) == 5000

        short_score = _score_text(query, title="Unrelated", body=short_body)
        long_score = _score_text(query, title="Unrelated", body=long_body)

        assert short_score > long_score, (
            f"short body ({short_score}) must outscore long body "
            f"({long_score}) on substring hit"
        )

    def test_title_match_still_dominates_any_body_match(self):
        """Title-only hits (>=0.7) must still outscore any body-only hit,
        regardless of body length, after normalization."""
        query = "garden"
        title_substring = _score_text(query, title="The Garden Path", body=None)
        body_short = _score_text(query, title="Unrelated", body="A garden here.")
        body_huge = _score_text(
            query, title="Unrelated", body="garden " + ("x " * 10_000)
        )

        assert title_substring >= 0.7
        assert title_substring > body_short
        assert title_substring > body_huge

    def test_body_match_still_beats_no_match(self):
        """Even a very long body that mentions the query once must score
        strictly higher than a body with no match at all."""
        query = "garden"
        long_body_with_hit = "garden " + ("filler " * 5_000)
        no_match_body = "filler " * 50

        hit_score = _score_text(query, title="Unrelated", body=long_body_with_hit)
        no_match_score = _score_text(query, title="Unrelated", body=no_match_body)

        assert hit_score > no_match_score



# ---- _is_postgres dialect detection ----


class TestIsPostgres:
    """_is_postgres must NOT default to True when db.bind is None.

    History: half-constructed services (no bound engine) silently flipped
    to the FTS branch and then blew up downstream on a Postgres-specific
    tsquery. The safe default is False → ILIKE fallback, which works on
    every supported dialect.
    """

    def test_returns_false_when_db_bind_is_none(self):
        """Unbound session → graceful ILIKE fallback, never an FTS attempt."""
        db = MagicMock()
        db.bind = None
        service = SiteSearchService(db)
        assert service._is_postgres is False

    def test_returns_true_for_postgresql_dialect(self):
        db = MagicMock()
        db.bind.dialect.name = "postgresql"
        service = SiteSearchService(db)
        assert service._is_postgres is True

    def test_returns_false_for_sqlite_dialect(self):
        db = MagicMock()
        db.bind.dialect.name = "sqlite"
        service = SiteSearchService(db)
        assert service._is_postgres is False
