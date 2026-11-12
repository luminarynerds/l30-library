# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for SSR /discover landing (/api/v1/seo/discover).

Crawler user-agents hit this route via nginx (location = /discover) to get
per-route <title>, og:*, twitter:*, canonical, an SSR <h1>Discover</h1>
hero, and <link rel="preload" as="image" fetchpriority="high"> hints for
the first two carousel cover images. Mirrors the test pattern from
test_seo_board_meetings.py / test_seo_learning.py.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

import pytest

from app.core.config import get_settings
from app.models.catalog import CatalogItem, CatalogingStatus, ItemStatus


@pytest.fixture(autouse=True)
def _stub_ssr_index_html(monkeypatch):
    """Use the real frontend/index.html template for SSR tests.

    Production seo_meta.py fetches http://frontend:80/ when running inside
    the backend container; on the host pytest runs from, that URL is not
    the L30 frontend. Monkeypatch the cache + fetch function so tests see
    the actual source template that production string-replaces against.
    """
    import app.api.v1.seo_meta as seo_meta_module

    template_path = Path(__file__).resolve().parents[4] / "frontend" / "index.html"
    template = template_path.read_text()

    async def _stubbed_get_index_html() -> str:
        return template

    monkeypatch.setattr(seo_meta_module, "_get_index_html", _stubbed_get_index_html)
    monkeypatch.setattr(seo_meta_module, "_INDEX_HTML", None)
    yield


async def _seed_new_arrival(test_db, *, title: str, cover_url: str | None) -> CatalogItem:
    """Insert a catalog item dated within the is_new=True 30-day window.

    Mirrors anonymous-visible defaults (CATALOGED + default PUBLIC sensitivity +
    non-withdrawn status) so the SSR query — which applies the same filters
    crawlers see — actually picks it up.
    """
    item = CatalogItem(
        title=title,
        author="Test Author",
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
        cover_url=cover_url,
        created_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.mark.asyncio
async def test_route_specific_title(client):
    """<title> reflects /discover, not the homepage default."""
    resp = await client.get("/api/v1/seo/discover")
    assert resp.status_code == 200
    m = re.search(r"<title>([^<]+)</title>", resp.text)
    assert m is not None
    title = m.group(1)
    assert "Discover" in title
    # And the homepage title is not still present
    assert title != "L30 - Community Library"


@pytest.mark.asyncio
async def test_canonical_and_og_url_point_at_discover(client):
    """canonical and og:url must point at /discover, not the site root."""
    settings = get_settings()
    expected = f"{settings.frontend_url.rstrip('/')}/discover"
    resp = await client.get("/api/v1/seo/discover")
    assert resp.status_code == 200
    assert f'canonical" href="{expected}"' in resp.text
    assert f'og:url" content="{expected}"' in resp.text
    # The site-root canonical placeholder must be gone
    assert '<link rel="canonical" href="https://l30.org/" />' not in resp.text


@pytest.mark.asyncio
async def test_route_specific_description(client):
    """meta[description], og:description, twitter:description all updated."""
    resp = await client.get("/api/v1/seo/discover")
    assert resp.status_code == 200
    # Original homepage description must not still be present in any tag
    assert 'content="Search the catalog, reserve a room, check your holds, find events."' not in resp.text
    assert 'L30 Library - Search the catalog, reserve a room, check your holds, find events.' not in resp.text
    # New description appears at least in name=description
    assert 'name="description" content="Browse staff picks' in resp.text


@pytest.mark.asyncio
async def test_og_type_is_website(client):
    """/discover is a landing page → og:type=website (not article)."""
    resp = await client.get("/api/v1/seo/discover")
    assert resp.status_code == 200
    assert 'og:type" content="website"' in resp.text


@pytest.mark.asyncio
async def test_h1_present_in_body(client):
    """Body contains <h1>Discover</h1> SSR'd into the root div for crawlers."""
    resp = await client.get("/api/v1/seo/discover")
    assert resp.status_code == 200
    # H1 sits inside the root div, before React hydrates
    assert "<h1" in resp.text and ">Discover</h1>" in resp.text
    # And the subhead is present
    assert "Staff picks, new arrivals" in resp.text


@pytest.mark.asyncio
async def test_preload_tags_for_first_two_covers(client, test_db):
    """Two new-arrival items with covers → two LCP preload tags in <head>."""
    # Title order is "Aardvark Tales", "Beach Days" — both within is_new window
    await _seed_new_arrival(test_db, title="Aardvark Tales", cover_url="https://example.com/a.jpg")
    await _seed_new_arrival(test_db, title="Beach Days", cover_url="https://example.com/b.jpg")
    # A third without a cover — should NOT appear in preload (limit 2 + cover required)
    await _seed_new_arrival(test_db, title="Catch the Light", cover_url=None)

    resp = await client.get("/api/v1/seo/discover")
    assert resp.status_code == 200

    preloads = re.findall(
        r'<link rel="preload" as="image" fetchpriority="high" href="([^"]+)"',
        resp.text,
    )
    assert "https://example.com/a.jpg" in preloads
    assert "https://example.com/b.jpg" in preloads
    # No-cover row is filtered server-side
    assert len(preloads) == 2


@pytest.mark.asyncio
async def test_no_preload_tags_when_no_new_arrivals(client):
    """Empty corpus → no preload tags, no crash, 200 still."""
    resp = await client.get("/api/v1/seo/discover")
    assert resp.status_code == 200
    assert 'rel="preload" as="image"' not in resp.text
    # And the hero still renders so crawlers see something useful
    assert ">Discover</h1>" in resp.text


@pytest.mark.asyncio
async def test_old_items_excluded_from_preload(client, test_db):
    """Items older than 30 days must not appear in the carousel preload set."""
    old = CatalogItem(
        title="Ancient Tome",
        author="Test Author",
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
        cover_url="https://example.com/old.jpg",
        created_at=datetime.now(timezone.utc) - timedelta(days=90),
    )
    test_db.add(old)
    await test_db.commit()

    resp = await client.get("/api/v1/seo/discover")
    assert resp.status_code == 200
    assert "https://example.com/old.jpg" not in resp.text


@pytest.mark.asyncio
async def test_uncataloged_items_excluded_from_preload(client, test_db):
    """Uncataloged items aren't surfaced to anonymous users — SSR must match.

    Crawlers are anonymous, and the public /catalog query at
    catalog/helpers.py:364 filters to ``cataloging_status == CATALOGED``.
    Preloading an uncataloged cover means hinting an LCP that doesn't
    actually render in the carousel.
    """
    uncataloged = CatalogItem(
        title="Awaiting Catalog",
        author="Test Author",
        status=ItemStatus.available,
        # Default cataloging_status is UNCATALOGED — leave it unset
        cover_url="https://example.com/uncataloged.jpg",
        created_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    test_db.add(uncataloged)
    await test_db.commit()

    resp = await client.get("/api/v1/seo/discover")
    assert resp.status_code == 200
    assert "https://example.com/uncataloged.jpg" not in resp.text
