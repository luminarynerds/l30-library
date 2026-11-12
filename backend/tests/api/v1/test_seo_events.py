# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for SSR events endpoints (/api/v1/seo/events, /api/v1/seo/events/{id}).

These routes are hit by nginx for crawler user-agents to inject per-page
<title>/og/canonical and schema.org Event + BreadcrumbList JSON-LD into the
SPA shell.
"""
from datetime import datetime, timedelta, timezone
import json
import re
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.models.event import Event


@pytest.fixture(autouse=True)
def _stub_ssr_index_html(monkeypatch):
    """Make SSR tests use the real frontend/index.html template.

    Same approach as test_seo_board_meetings.py: production seo_meta.py fetches
    http://frontend:80/ when running inside the backend container; on the host
    pytest runs from, that URL is not the L30 frontend. Monkeypatch the cache +
    the fetch function so tests see the actual source template.
    """
    import app.api.v1.seo_meta as seo_meta_module

    template_path = Path(__file__).resolve().parents[4] / "frontend" / "index.html"
    template = template_path.read_text()

    async def _stubbed_get_index_html() -> str:
        return template

    monkeypatch.setattr(seo_meta_module, "_get_index_html", _stubbed_get_index_html)
    monkeypatch.setattr(seo_meta_module, "_INDEX_HTML", None)
    yield


@pytest.fixture
async def sample_event(test_db):
    """Seed a single published in-person upcoming event with full descriptive data."""
    now = datetime.now(timezone.utc)
    event = Event(
        title="Story Time with Miss Rita",
        description="A 30-minute read-aloud for ages 3-5 with songs and a craft.",
        start_time=now + timedelta(days=7),
        end_time=now + timedelta(days=7, minutes=30),
        location="Main Branch — Children's Room",
        is_virtual=False,
        audience="Children",
        category="Story Time",
        is_published=True,
        image_url="https://l30.org/uploads/storytime.jpg",
    )
    test_db.add(event)
    await test_db.commit()
    await test_db.refresh(event)
    return event


def _extract_jsonld_blocks(html: str) -> list:
    """Parse all <script type="application/ld+json"> blocks into Python objects.

    Handles both single-object and JSON-array payloads (the latter is how the
    list handler emits per-event entries in one script tag).
    """
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    parsed: list = []
    for raw in blocks:
        unescaped = raw.replace("<\\/", "</")
        obj = json.loads(unescaped)
        if isinstance(obj, list):
            parsed.extend(obj)
        else:
            parsed.append(obj)
    return parsed


# ---------- /seo/events (list) ----------

@pytest.mark.asyncio
async def test_events_list_canonical_and_og_url_are_events_page(client, sample_event):
    """The events list canonical and og:url point at /events, not /."""
    settings = get_settings()
    expected = f"{settings.frontend_url.rstrip('/')}/events"
    resp = await client.get("/api/v1/seo/events")
    assert resp.status_code == 200
    assert f'canonical" href="{expected}"' in resp.text
    assert f'og:url" content="{expected}"' in resp.text
    # And the default root canonical is gone
    assert 'canonical" href="https://l30.org/"' not in resp.text


@pytest.mark.asyncio
async def test_events_list_title_is_specific(client, sample_event):
    """The <title> for the events list is event-page specific, not the default."""
    resp = await client.get("/api/v1/seo/events")
    assert resp.status_code == 200
    m = re.search(r"<title>([^<]+)</title>", resp.text)
    assert m is not None
    assert "Events" in m.group(1)
    assert m.group(1) != "L30 - Community Library"


@pytest.mark.asyncio
async def test_events_list_emits_event_jsonld_per_upcoming_event(client, sample_event):
    """The events list emits one schema.org Event entry per upcoming event."""
    resp = await client.get("/api/v1/seo/events")
    assert resp.status_code == 200
    entries = _extract_jsonld_blocks(resp.text)
    events_in_ld = [e for e in entries if e.get("@type") == "Event"]
    assert any(e.get("name") == sample_event.title for e in events_in_ld)
    target = next(e for e in events_in_ld if e["name"] == sample_event.title)
    assert target["@context"] == "https://schema.org"
    assert target["eventStatus"] == "https://schema.org/EventScheduled"
    assert target["eventAttendanceMode"] == "https://schema.org/OfflineEventAttendanceMode"
    assert target["offers"]["price"] == "0"
    assert target["offers"]["priceCurrency"] == "USD"
    assert target["organizer"]["@type"] == "Organization"


@pytest.mark.asyncio
async def test_events_list_excludes_unpublished_events(client, test_db):
    """An unpublished event must not appear in the JSON-LD list."""
    now = datetime.now(timezone.utc)
    unpublished = Event(
        title="Draft Workshop",
        start_time=now + timedelta(days=3),
        is_published=False,
    )
    test_db.add(unpublished)
    await test_db.commit()

    resp = await client.get("/api/v1/seo/events")
    assert resp.status_code == 200
    entries = _extract_jsonld_blocks(resp.text)
    titles = [e.get("name") for e in entries if e.get("@type") == "Event"]
    assert "Draft Workshop" not in titles


@pytest.mark.asyncio
async def test_events_list_excludes_past_events(client, test_db):
    """Past events must not appear (the SSR list is upcoming-only)."""
    now = datetime.now(timezone.utc)
    past = Event(
        title="Past Talk From Last Year",
        start_time=now - timedelta(days=30),
        is_published=True,
    )
    test_db.add(past)
    await test_db.commit()

    resp = await client.get("/api/v1/seo/events")
    assert resp.status_code == 200
    entries = _extract_jsonld_blocks(resp.text)
    titles = [e.get("name") for e in entries if e.get("@type") == "Event"]
    assert "Past Talk From Last Year" not in titles


# ---------- /seo/events/{id} (detail) ----------

@pytest.mark.asyncio
async def test_event_detail_canonical_matches_route(client, sample_event):
    """canonical/og:url for an event detail page is /events/detail/{id}."""
    settings = get_settings()
    expected = f"{settings.frontend_url.rstrip('/')}/events/detail/{sample_event.id}"
    resp = await client.get(f"/api/v1/seo/events/{sample_event.id}")
    assert resp.status_code == 200
    assert f'canonical" href="{expected}"' in resp.text
    assert f'og:url" content="{expected}"' in resp.text


@pytest.mark.asyncio
async def test_event_detail_emits_event_and_breadcrumb_jsonld(client, sample_event):
    """Detail page emits both schema.org Event and BreadcrumbList JSON-LD."""
    resp = await client.get(f"/api/v1/seo/events/{sample_event.id}")
    assert resp.status_code == 200
    entries = _extract_jsonld_blocks(resp.text)
    types = [e.get("@type") for e in entries]
    assert "Event" in types
    assert "BreadcrumbList" in types

    event_ld = next(e for e in entries if e.get("@type") == "Event")
    assert event_ld["name"] == sample_event.title
    assert event_ld["location"]["@type"] == "Place"
    assert event_ld["location"]["name"] == "Main Branch — Children's Room"

    crumbs = next(e for e in entries if e.get("@type") == "BreadcrumbList")
    names = [item["name"] for item in crumbs["itemListElement"]]
    assert names == ["Home", "Events", sample_event.title]


@pytest.mark.asyncio
async def test_event_detail_og_type_article(client, sample_event):
    """Detail page is og:type=article so unfurlers use the larger card."""
    resp = await client.get(f"/api/v1/seo/events/{sample_event.id}")
    assert resp.status_code == 200
    assert 'og:type" content="article"' in resp.text
    assert 'og:type" content="website"' not in resp.text


@pytest.mark.asyncio
async def test_event_detail_virtual_emits_virtual_location(client, test_db):
    """Virtual events get OnlineEventAttendanceMode + VirtualLocation."""
    now = datetime.now(timezone.utc)
    virtual = Event(
        title="Online Coding Club",
        start_time=now + timedelta(days=2),
        is_virtual=True,
        virtual_link="https://meet.example.com/abc",
        is_published=True,
    )
    test_db.add(virtual)
    await test_db.commit()
    await test_db.refresh(virtual)

    resp = await client.get(f"/api/v1/seo/events/{virtual.id}")
    assert resp.status_code == 200
    entries = _extract_jsonld_blocks(resp.text)
    event_ld = next(e for e in entries if e.get("@type") == "Event")
    assert event_ld["eventAttendanceMode"] == "https://schema.org/OnlineEventAttendanceMode"
    assert event_ld["location"]["@type"] == "VirtualLocation"
    assert event_ld["location"]["url"] == "https://meet.example.com/abc"


@pytest.mark.asyncio
async def test_missing_event_returns_404_with_noindex(client):
    """A crawler hitting a non-existent event ID gets 404 + robots=noindex."""
    resp = await client.get("/api/v1/seo/events/99999999")
    assert resp.status_code == 404
    assert 'name="robots" content="noindex,follow"' in resp.text
    assert "Event not found" in resp.text


@pytest.mark.asyncio
async def test_unpublished_event_returns_404(client, test_db):
    """An unpublished (draft) event must 404 to a crawler, not leak."""
    now = datetime.now(timezone.utc)
    draft = Event(
        title="Internal Draft",
        start_time=now + timedelta(days=5),
        is_published=False,
    )
    test_db.add(draft)
    await test_db.commit()
    await test_db.refresh(draft)

    resp = await client.get(f"/api/v1/seo/events/{draft.id}")
    assert resp.status_code == 404
    assert 'name="robots" content="noindex,follow"' in resp.text


@pytest.mark.asyncio
async def test_event_detail_jsonld_xss_safe_closing_script_tag(client, test_db):
    """An event title containing </script> must not break out of the JSON-LD block."""
    now = datetime.now(timezone.utc)
    sneaky = Event(
        title="Evil </script><script>alert(1)</script>",
        start_time=now + timedelta(days=3),
        is_published=True,
    )
    test_db.add(sneaky)
    await test_db.commit()
    await test_db.refresh(sneaky)

    resp = await client.get(f"/api/v1/seo/events/{sneaky.id}")
    assert resp.status_code == 200
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', resp.text, re.DOTALL)
    assert blocks, "No JSON-LD block found"
    for raw in blocks:
        assert "</script>" not in raw, "Raw </script> in JSON-LD payload"
        # Escaped form must appear when the title contained it
        if "Evil" in raw:
            assert "<\\/script>" in raw


@pytest.mark.asyncio
async def test_html_special_chars_escaped_in_event_meta(client, test_db):
    """Title/description with HTML metacharacters are escaped in meta tag values."""
    now = datetime.now(timezone.utc)
    spicy = Event(
        title='"Q&A" Night <with> the Director',
        description='Topics: budget & goals; "open mic" segment',
        start_time=now + timedelta(days=3),
        is_published=True,
    )
    test_db.add(spicy)
    await test_db.commit()
    await test_db.refresh(spicy)

    resp = await client.get(f"/api/v1/seo/events/{spicy.id}")
    assert resp.status_code == 200
    title_match = re.search(r"<title>([^<]+)</title>", resp.text)
    assert title_match is not None
    title = title_match.group(1)
    assert "&amp;" in title
    assert "&quot;" in title
    assert "&lt;" in title and "&gt;" in title
    assert '"Q&A"' not in title


# ---------- sitemap-events.xml ----------

@pytest.mark.asyncio
async def test_sitemap_events_lists_published_upcoming_event(client, sample_event):
    """The sitemap-events.xml endpoint includes an upcoming published event."""
    settings = get_settings()
    expected_loc = f"{settings.frontend_url.rstrip('/')}/events/detail/{sample_event.id}"
    resp = await client.get("/api/v1/events/sitemap-events.xml")
    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]
    assert f"<loc>{expected_loc}</loc>" in resp.text
    assert "<urlset" in resp.text
    assert "</urlset>" in resp.text


@pytest.mark.asyncio
async def test_sitemap_events_excludes_unpublished(client, test_db):
    """Unpublished events must not appear in the public sitemap."""
    now = datetime.now(timezone.utc)
    draft = Event(
        title="Hidden Draft",
        start_time=now + timedelta(days=4),
        is_published=False,
    )
    test_db.add(draft)
    await test_db.commit()
    await test_db.refresh(draft)

    resp = await client.get("/api/v1/events/sitemap-events.xml")
    assert resp.status_code == 200
    assert f"/events/detail/{draft.id}<" not in resp.text


@pytest.mark.asyncio
async def test_sitemap_events_is_publicly_cacheable(client, sample_event):
    """sitemap-events.xml must be public-cacheable so CDNs serve it from the edge."""
    resp = await client.get("/api/v1/events/sitemap-events.xml")
    assert resp.status_code == 200
    cc = resp.headers.get("cache-control", "")
    assert "public" in cc
    assert "max-age" in cc


# ---------- Cache-Control on /api/v1/events (anonymous list) ----------

@pytest.mark.asyncio
async def test_anonymous_events_list_is_publicly_cacheable(client, sample_event):
    """The anonymous list endpoint sends public+SWR so CDNs (Cloudflare) can cache."""
    resp = await client.get("/api/v1/events?upcoming=true")
    assert resp.status_code == 200
    cc = resp.headers.get("cache-control", "")
    assert "public" in cc, f"expected public Cache-Control, got: {cc!r}"
    assert "stale-while-revalidate=600" in cc
    assert "max-age=300" in cc


@pytest.mark.asyncio
async def test_authenticated_events_list_is_not_publicly_cached(client, sample_event):
    """When an Authorization header is present, do not promote to public cache.

    The endpoint itself is identical for anon/auth users today, but the safety
    invariant is: never set ``public`` Cache-Control on a request that carried
    credentials, so a future personalization change can't leak across users.
    """
    resp = await client.get(
        "/api/v1/events?upcoming=true",
        headers={"Authorization": "Bearer fake-token-not-validated-by-this-route"},
    )
    assert resp.status_code == 200
    cc = resp.headers.get("cache-control", "")
    # CachingHeadersMiddleware fallback is "private, max-age=300" — anything
    # else is fine as long as it's not "public".
    assert "public" not in cc.split(","), f"public leaked into auth path: {cc!r}"
