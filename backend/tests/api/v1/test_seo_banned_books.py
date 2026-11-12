# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the /api/v1/seo/banned-books crawler SSR template.

Renders the SPA shell with banned-books-specific <title>, meta description,
and a body snippet (mission text, stats summary, public challenge stories)
injected into <div id="root"> so crawlers and screen-reader-without-JS users
get meaningful content instead of an empty root div.
"""
import logging
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import app.api.v1.seo_meta as seo_meta


# ---------------------------------------------------------------------------
# Drift validator coverage for the new placeholder
# ---------------------------------------------------------------------------

def test_required_placeholders_includes_root_div():
    """The body-injection target must be tracked by the drift validator so
    a Vite-side rename doesn't silently break the no-JS SSR."""
    assert '<div id="root">' in seo_meta._REQUIRED_PLACEHOLDERS


def test_drift_validator_flags_missing_root_div(caplog):
    """If a future frontend rename drops <div id="root">, the drift validator
    must log ERROR on the next index.html fetch."""
    caplog.set_level(logging.ERROR, logger="app.api.v1.seo_meta")
    # Shell missing the root div but otherwise intact.
    shell = "\n".join([
        "<!DOCTYPE html><html><head>",
        "<title>Library</title>",
        "</head><body><div id=\"not-root\"></div></body></html>",
    ])
    seo_meta._validate_template_placeholders(shell)
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1
    assert "root" in errors[0].getMessage()


def test_real_frontend_index_has_root_div():
    """Lock in: the real frontend index.html contains the body placeholder."""
    template_path = Path(__file__).resolve().parents[4] / "frontend" / "index.html"
    if not template_path.exists():
        pytest.skip(f"frontend/index.html not at {template_path}")
    contents = template_path.read_text()
    assert '<div id="root">' in contents, (
        "Vite shell no longer contains <div id=\"root\">; update the SSR body "
        "injection target."
    )


# ---------------------------------------------------------------------------
# Body renderer (pure-function unit tests)
# ---------------------------------------------------------------------------

def test_render_banned_books_body_includes_mission_text():
    """The mission copy must appear in the SSR body (this is the main value
    of the page for non-JS readers)."""
    html = seo_meta._render_banned_books_body(
        library_name="Test Public Library",
        stats={"total_challenges": 0, "pending_challenges": 0, "resolved_this_year": 0, "outcomes": {}},
        challenges=[],
    )
    assert "Intellectual Freedom" in html
    assert "freedom of thought" in html.lower() or "right to read" in html.lower()
    assert "Test Public Library" in html
    assert "Library Bill of Rights" in html


def test_render_banned_books_body_includes_stats_summary():
    """Total / under-review / retained / removed values must be visible."""
    html = seo_meta._render_banned_books_body(
        library_name="Test Public Library",
        stats={
            "total_challenges": 12,
            "pending_challenges": 3,
            "resolved_this_year": 5,
            "outcomes": {"RETAINED": 7, "REMOVED": 2, "RETAINED_WITH_CHANGES": 1},
        },
        challenges=[],
    )
    assert ">12<" in html, f"total_challenges count missing: {html!r}"
    assert ">3<" in html, "pending count missing"
    # Retained should sum RETAINED + RETAINED_WITH_CHANGES = 8.
    assert ">8<" in html, "retained sum (incl. with_changes) missing"
    assert ">2<" in html, "removed count missing"
    assert ">5<" in html, "resolved-this-year count missing"


def test_render_banned_books_body_includes_public_stories():
    """Public-challenge story records must appear with title + outcome."""
    challenges = [
        SimpleNamespace(
            public_title="Anonymous Book A",
            title="Real Title A",
            author="Author A",
            outcome="retained",
            public_summary="A community review concluded the book belongs in the collection.",
            lessons_learned="Engagement matters.",
        ),
        SimpleNamespace(
            public_title=None,
            title="Real Title B",
            author=None,
            outcome="removed",
            public_summary=None,
            lessons_learned=None,
        ),
    ]
    html = seo_meta._render_banned_books_body(
        library_name="Test Public Library",
        stats={},
        challenges=challenges,
    )
    # First story uses public_title, second falls back to title.
    assert "Anonymous Book A" in html
    assert "Real Title B" in html
    assert "Retained" in html
    assert "Removed" in html
    assert "A community review concluded" in html
    assert "Engagement matters." in html


def test_render_banned_books_body_handles_empty_challenges():
    html = seo_meta._render_banned_books_body(
        library_name="Test Public Library",
        stats={},
        challenges=[],
    )
    assert "No public challenge records" in html


def test_render_banned_books_body_escapes_html_in_user_strings():
    """User-provided fields (challenger summary, library_name, etc.) must
    be escaped so a malicious or accidental angle bracket doesn't break the
    rendered shell."""
    challenges = [
        SimpleNamespace(
            public_title="<script>alert(1)</script>",
            title=None,
            author=None,
            outcome="pending",
            public_summary=None,
            lessons_learned=None,
        ),
    ]
    html = seo_meta._render_banned_books_body(
        library_name="<b>Test</b>",
        stats={},
        challenges=challenges,
    )
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert "<b>Test</b>" not in html
    assert "&lt;b&gt;Test&lt;/b&gt;" in html


# ---------------------------------------------------------------------------
# Endpoint integration
# ---------------------------------------------------------------------------

@pytest.fixture
def _stub_ssr_index_html(monkeypatch):
    """Use the real frontend/index.html template (same pattern as test_seo_indie)."""
    template_path = Path(__file__).resolve().parents[4] / "frontend" / "index.html"
    if not template_path.exists():
        pytest.skip(f"frontend/index.html not at {template_path}")
    template = template_path.read_text()

    async def _stubbed_get_index_html() -> str:
        return template

    monkeypatch.setattr(seo_meta, "_get_index_html", _stubbed_get_index_html)
    monkeypatch.setattr(seo_meta, "_INDEX_HTML", None)
    yield


@pytest.mark.asyncio
async def test_seo_banned_books_renders_title_meta_and_body(client, _stub_ssr_index_html):
    """GET /api/v1/seo/banned-books returns 200 with banned-books title +
    mission text in the body."""
    sample_challenges = [
        SimpleNamespace(
            public_title="A Brave Story",
            title="A Brave Story",
            author="J. Doe",
            outcome="retained",
            public_summary="Reviewed and retained after committee process.",
            lessons_learned=None,
        ),
    ]
    sample_stats = {
        "total_challenges": 9,
        "pending_challenges": 1,
        "resolved_this_year": 4,
        "outcomes": {"RETAINED": 7, "REMOVED": 1},
        "reasons": {},
    }

    with patch(
        "app.services.organization_features_service.OrganizationFeaturesService.is_feature_enabled",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.services.book_challenge_service.BookChallengeService.get_statistics",
        new_callable=AsyncMock,
        return_value=sample_stats,
    ), patch(
        "app.services.book_challenge_service.BookChallengeService.list_public_challenges",
        new_callable=AsyncMock,
        return_value=sample_challenges,
    ):
        resp = await client.get("/api/v1/seo/banned-books")

    assert resp.status_code == 200, resp.text
    body = resp.text

    # Title contains the banned-books phrase.
    m = re.search(r"<title>([^<]+)</title>", body)
    assert m is not None
    assert "Intellectual Freedom" in m.group(1) or "Banned Books" in m.group(1)

    # Body snippet was injected.
    assert "banned-books-ssr" in body, "SSR body wrapper missing"
    assert "Our Commitment" in body
    assert "A Brave Story" in body
    assert "Retained" in body
    assert ">9<" in body, "total_challenges count missing in rendered output"


@pytest.mark.asyncio
async def test_seo_banned_books_degrades_when_feature_disabled(client, _stub_ssr_index_html):
    """When the feature flag is off, return the unmodified shell (200, no
    banned-books body) — don't 404, which would harm crawler indexing of
    any prior link."""
    with patch(
        "app.services.organization_features_service.OrganizationFeaturesService.is_feature_enabled",
        new_callable=AsyncMock,
        return_value=False,
    ):
        resp = await client.get("/api/v1/seo/banned-books")

    assert resp.status_code == 200
    assert "banned-books-ssr" not in resp.text


@pytest.mark.asyncio
async def test_seo_banned_books_survives_stats_lookup_failure(client, _stub_ssr_index_html):
    """If the stats query raises, the page must still render with the meta
    + mission text (graceful degradation, not 500)."""
    with patch(
        "app.services.organization_features_service.OrganizationFeaturesService.is_feature_enabled",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.services.book_challenge_service.BookChallengeService.get_statistics",
        new_callable=AsyncMock,
        side_effect=RuntimeError("DB unavailable"),
    ), patch(
        "app.services.book_challenge_service.BookChallengeService.list_public_challenges",
        new_callable=AsyncMock,
        return_value=[],
    ):
        resp = await client.get("/api/v1/seo/banned-books")

    assert resp.status_code == 200
    assert "Our Commitment" in resp.text
