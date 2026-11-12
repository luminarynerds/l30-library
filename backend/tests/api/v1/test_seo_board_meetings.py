# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for SSR board-meeting OG cards (/api/v1/seo/board/meetings/{id}).

The route is hit by nginx for crawler user-agents to inject per-meeting
<title>, og:*, twitter:*, canonical, and schema.org Event JSON-LD into
the SPA shell.
"""
from datetime import datetime, timedelta, timezone
import json
import re
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.models.board import BoardMeeting


@pytest.fixture(autouse=True)
def _stub_ssr_index_html(monkeypatch):
    """Make SSR tests use the real frontend/index.html template.

    Production seo_meta.py fetches http://frontend:80/ when running inside
    the backend container; on the host pytest runs from, that URL is not
    the L30 frontend. We monkeypatch the cache + the fetch function so
    tests see the actual source template that production string-replaces
    against.
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
async def sample_meeting(test_db):
    """Seed a single non-cancelled in-person meeting with full descriptive data."""
    now = datetime.now(timezone.utc)
    meeting = BoardMeeting(
        meeting_type="regular",
        title="January Regular Board Meeting",
        description="Monthly trustee business meeting; budget review and committee reports.",
        scheduled_date=now + timedelta(days=14),
        start_time=now + timedelta(days=14),
        end_time=now + timedelta(days=14, hours=2),
        location="Main Branch — Community Room",
        is_virtual=False,
        is_cancelled=False,
    )
    test_db.add(meeting)
    await test_db.commit()
    await test_db.refresh(meeting)
    return meeting


@pytest.mark.asyncio
async def test_meeting_title_appears_in_html_title(client, sample_meeting):
    """The <title> tag must contain the meeting title."""
    resp = await client.get(f"/api/v1/seo/board/meetings/{sample_meeting.id}")
    assert resp.status_code == 200
    assert sample_meeting.title in resp.text
    # And it's in the <title> specifically, not just the body
    m = re.search(r"<title>([^<]+)</title>", resp.text)
    assert m is not None
    assert sample_meeting.title in m.group(1)

@pytest.mark.asyncio
async def test_og_url_and_canonical_are_meeting_specific(client, sample_meeting):
    """og:url, twitter:url-equivalent, and <link rel='canonical'> must point at the meeting."""
    settings = get_settings()
    expected_url = f"{settings.frontend_url.rstrip('/')}/board/meetings/{sample_meeting.id}"
    resp = await client.get(f"/api/v1/seo/board/meetings/{sample_meeting.id}")
    assert resp.status_code == 200
    assert f'og:url" content="{expected_url}"' in resp.text
    assert f'canonical" href="{expected_url}"' in resp.text


@pytest.mark.asyncio
async def test_og_type_is_article_for_meetings(client, sample_meeting):
    """Meeting pages should declare og:type=article so unfurlers use the larger card."""
    resp = await client.get(f"/api/v1/seo/board/meetings/{sample_meeting.id}")
    assert resp.status_code == 200
    assert 'og:type" content="article"' in resp.text
    assert 'og:type" content="website"' not in resp.text



def _find_jsonld_payload(html: str, expected_type: str) -> dict:
    """The rendered shell always carries the base template's own
    Organization/WebSite JSON-LD <script> ahead of any per-page block
    _inject_meta appends before </head>. Scan every JSON-LD block for the
    one matching ``expected_type`` rather than assuming there's only one."""
    for m in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>',
        html,
        re.DOTALL,
    ):
        payload = json.loads(m.group(1).replace("<\\/", "</"))
        if payload.get("@type") == expected_type:
            return payload
    raise AssertionError(f"No JSON-LD block with @type={expected_type!r} found")


@pytest.mark.asyncio
async def test_jsonld_event_present_and_parses(client, sample_meeting):
    """Response must include a schema.org Event JSON-LD <script> with valid JSON."""
    resp = await client.get(f"/api/v1/seo/board/meetings/{sample_meeting.id}")
    assert resp.status_code == 200

    payload = _find_jsonld_payload(resp.text, "Event")
    assert payload["@context"] == "https://schema.org"
    assert payload["@type"] == "Event"
    assert payload["name"] == sample_meeting.title
    assert "startDate" in payload
    assert payload["eventStatus"] == "https://schema.org/EventScheduled"
    assert payload["eventAttendanceMode"] == "https://schema.org/OfflineEventAttendanceMode"
    assert payload["organizer"]["@type"] == "GovernmentOrganization"


@pytest.mark.asyncio
async def test_jsonld_cancelled_meeting_emits_cancelled_status(client, test_db):
    """Cancelled meetings get EventCancelled, not EventScheduled."""
    cancelled = BoardMeeting(
        meeting_type="regular",
        title="Cancelled Meeting",
        scheduled_date=datetime.now(timezone.utc) + timedelta(days=7),
        is_cancelled=True,
    )
    test_db.add(cancelled)
    await test_db.commit()
    await test_db.refresh(cancelled)

    resp = await client.get(f"/api/v1/seo/board/meetings/{cancelled.id}")
    assert resp.status_code == 200
    payload = _find_jsonld_payload(resp.text, "Event")
    assert payload["eventStatus"] == "https://schema.org/EventCancelled"


@pytest.mark.asyncio
async def test_jsonld_virtual_meeting_emits_virtual_location(client, test_db):
    """Virtual meetings get VirtualLocation with the meeting URL."""
    virtual = BoardMeeting(
        meeting_type="regular",
        title="Virtual Meeting",
        scheduled_date=datetime.now(timezone.utc) + timedelta(days=7),
        is_virtual=True,
        virtual_meeting_url="https://zoom.us/j/123456789",
    )
    test_db.add(virtual)
    await test_db.commit()
    await test_db.refresh(virtual)

    resp = await client.get(f"/api/v1/seo/board/meetings/{virtual.id}")
    assert resp.status_code == 200
    payload = _find_jsonld_payload(resp.text, "Event")
    assert payload["eventAttendanceMode"] == "https://schema.org/OnlineEventAttendanceMode"
    assert payload["location"]["@type"] == "VirtualLocation"
    assert payload["location"]["url"] == "https://zoom.us/j/123456789"


@pytest.mark.asyncio
async def test_jsonld_xss_safe_closing_script_tag(client, test_db):
    """A meeting title containing </script> must not break out of the JSON-LD block."""
    sneaky = BoardMeeting(
        meeting_type="regular",
        title="Evil Meeting </script><script>alert(1)</script>",
        scheduled_date=datetime.now(timezone.utc) + timedelta(days=7),
        is_cancelled=False,
    )
    test_db.add(sneaky)
    await test_db.commit()
    await test_db.refresh(sneaky)

    resp = await client.get(f"/api/v1/seo/board/meetings/{sneaky.id}")
    assert resp.status_code == 200

    # The raw closing-script sequence must NOT appear inside ANY JSON-LD
    # payload region (the base template's own Organization/WebSite block is
    # also on the page; check every block, not just the first).
    blocks = list(re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>', resp.text, re.DOTALL
    ))
    assert blocks, "No JSON-LD script tag found"
    escaped_found = False
    for m in blocks:
        assert "</script>" not in m.group(1), "JSON-LD payload contains an unescaped </script>"
        if "<\\/script>" in m.group(1):
            escaped_found = True
    # And the escape form must be present in the Event block specifically
    assert escaped_found, "No JSON-LD block contained the escaped </script> sequence"


@pytest.mark.asyncio
async def test_missing_meeting_returns_404_with_noindex(client):
    """Crawler hitting a non-existent meeting ID gets 404 + robots=noindex."""
    resp = await client.get("/api/v1/seo/board/meetings/99999999")
    assert resp.status_code == 404
    assert 'name="robots" content="noindex,follow"' in resp.text
    assert "Meeting not found" in resp.text


@pytest.mark.asyncio
async def test_missing_meeting_title_is_specific(client):
    """The 404 page <title> should not be the generic site title."""
    resp = await client.get("/api/v1/seo/board/meetings/99999999")
    assert resp.status_code == 404
    m = re.search(r"<title>([^<]+)</title>", resp.text)
    assert m is not None
    assert "Meeting not found" in m.group(1)


@pytest.mark.asyncio
async def test_html_special_chars_are_escaped_in_meta_tags(client, test_db):
    """Title/description with HTML metacharacters are escaped in all tag values."""
    spicy = BoardMeeting(
        meeting_type="regular",
        title='"Q&A" Session <with> the Director',
        description='Topics: budget & governance; goals <2030>; "open mic" segment',
        scheduled_date=datetime.now(timezone.utc) + timedelta(days=7),
        is_cancelled=False,
    )
    test_db.add(spicy)
    await test_db.commit()
    await test_db.refresh(spicy)

    resp = await client.get(f"/api/v1/seo/board/meetings/{spicy.id}")
    assert resp.status_code == 200

    title_match = re.search(r"<title>([^<]+)</title>", resp.text)
    assert title_match is not None
    title = title_match.group(1)
    assert "&amp;" in title
    assert "&quot;" in title
    assert "&lt;" in title and "&gt;" in title
    assert '"Q&A"' not in title

    assert re.search(
        r'og:description" content="[^"]*&amp;[^"]*"',
        resp.text,
    ), "ampersand must be escaped in og:description"
