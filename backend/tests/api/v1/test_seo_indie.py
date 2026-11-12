# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for indie author/book SEO SSR handlers.

/api/v1/seo/indie/author/{slug} and /api/v1/seo/indie/book/{slug}
are hit by nginx for crawler user-agents so they get page-specific
<title>/og:* instead of the generic SPA shell.
"""
import re
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.models.indie_author import IndieAuthor


@pytest.fixture(autouse=True)
def _stub_ssr_index_html(monkeypatch):
    """Use the real frontend/index.html template, same pattern as test_seo_board_meetings."""
    import app.api.v1.seo_meta as seo_meta_module

    template_path = Path(__file__).resolve().parents[4] / "frontend" / "index.html"
    template = template_path.read_text()

    async def _stubbed_get_index_html() -> str:
        return template

    monkeypatch.setattr(seo_meta_module, "_get_index_html", _stubbed_get_index_html)
    monkeypatch.setattr(seo_meta_module, "_INDEX_HTML", None)
    yield


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def sample_author(test_db):
    """Seed one IndieAuthor with a known pen_name and bio."""
    author = IndieAuthor(
        pen_name="Wren Calloway",
        bio="Author of dark romantasy set in the bayou.",
        profile_image_url=None,
    )
    test_db.add(author)
    await test_db.commit()
    await test_db.refresh(author)
    return author


@pytest.fixture
def author_slug(sample_author):
    """Slug in the same format the frontend generates: <safe-pen_name>-<id>."""
    safe = sample_author.pen_name.lower().replace(" ", "-")[:50]
    return f"{safe}-{sample_author.id}"


@pytest.fixture
def metislib_book_data():
    """Fake MetisLib ebook payload for book SEO tests."""
    return {
        "id": 42,
        "title": "Bayou Midnight",
        "author_name": "Wren Calloway",
        "author_pen_name": "Wren Calloway",
        "description": "A dark romance set in the Louisiana bayou, where magic is currency.",
        "cover_url": "https://metislib.org/covers/42.jpg",
    }


# ---------------------------------------------------------------------------
# Author SEO tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seo_indie_author_returns_author_specific_title(client, sample_author, author_slug):
    """GET /seo/indie/author/{slug} must return 200 with the author's pen_name in <title>."""
    resp = await client.get(f"/api/v1/seo/indie/author/{author_slug}")
    assert resp.status_code == 200
    m = re.search(r"<title>([^<]+)</title>", resp.text)
    assert m is not None, "No <title> tag found"
    assert sample_author.pen_name in m.group(1), (
        f"pen_name '{sample_author.pen_name}' missing from title: {m.group(1)!r}"
    )


@pytest.mark.asyncio
async def test_seo_indie_author_404_for_unknown_slug(client):
    """Unknown author slug returns 200 + unmodified shell (no deindex on stale URL)."""
    resp = await client.get("/api/v1/seo/indie/author/nobody-here-99999999")
    # Mirror ebook handler: degrade gracefully, don't 404 (avoids crawler deindex on slug drift)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Book SEO tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seo_indie_book_returns_book_specific_title(client, metislib_book_data):
    """GET /seo/indie/book/{slug} must return 200 with the book title in <title>."""
    ebook_id = metislib_book_data["id"]
    slug = f"bayou-midnight-{ebook_id}"

    mock_client = AsyncMock()
    mock_client.get_ebook = AsyncMock(return_value=metislib_book_data)

    with patch("app.api.v1.seo_meta.get_metislib_client", return_value=mock_client):
        with patch("app.api.v1.seo_meta.get_settings") as mock_settings:
            mock_settings.return_value.metislib_enabled = True
            mock_settings.return_value.frontend_url = "https://l30.org"
            resp = await client.get(f"/api/v1/seo/indie/book/{slug}")

    assert resp.status_code == 200
    m = re.search(r"<title>([^<]+)</title>", resp.text)
    assert m is not None, "No <title> tag found"
    assert metislib_book_data["title"] in m.group(1), (
        f"book title '{metislib_book_data['title']}' missing from: {m.group(1)!r}"
    )


@pytest.mark.asyncio
async def test_seo_indie_book_404_for_unknown_slug(client):
    """Unknown book slug (MetisLib miss) returns 200 + unmodified shell."""
    from app.services.metislib_errors import MetisLibError

    mock_client = AsyncMock()
    mock_client.get_ebook = AsyncMock(side_effect=MetisLibError("not found"))

    with patch("app.api.v1.seo_meta.get_metislib_client", return_value=mock_client):
        with patch("app.api.v1.seo_meta.get_settings") as mock_settings:
            mock_settings.return_value.metislib_enabled = True
            mock_settings.return_value.frontend_url = "https://l30.org"
            resp = await client.get("/api/v1/seo/indie/book/ghost-book-99999999")

    assert resp.status_code == 200
