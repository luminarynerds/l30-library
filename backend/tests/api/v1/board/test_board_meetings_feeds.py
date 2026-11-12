# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the public board-meetings iCal/RSS feeds.

Regressions covered:
  - Defect A: feeds emitted relative URLs (`/board/meetings/{id}`); calendar
    clients and most RSS readers can't resolve those. URLs must be absolute,
    rooted at settings.frontend_url.
  - Defect B: iCal feed restricted to a ±180-day window, hiding past meetings
    that subscribers (trustees, open-meetings retention) expect to see.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import get_settings
from app.models.board import BoardMeeting


@pytest.fixture
async def meetings_across_time(test_db):
    """Seed a past, a future, and a cancelled meeting for feed coverage."""
    now = datetime.now(timezone.utc)
    past = BoardMeeting(
        meeting_type="regular",
        title="Past Regular Meeting",
        description="Archived meeting",
        scheduled_date=now - timedelta(days=365),
        start_time=now - timedelta(days=365),
        end_time=now - timedelta(days=365) + timedelta(hours=2),
        location="Main Branch",
        is_cancelled=False,
        notice_status="posted",
    )
    upcoming = BoardMeeting(
        meeting_type="regular",
        title="Upcoming Regular Meeting",
        description="Next month",
        scheduled_date=now + timedelta(days=30),
        start_time=now + timedelta(days=30),
        end_time=now + timedelta(days=30) + timedelta(hours=2),
        location="Main Branch",
        is_cancelled=False,
        notice_status="posted",
    )
    cancelled = BoardMeeting(
        meeting_type="regular",
        title="Cancelled Meeting",
        description="Should not appear",
        scheduled_date=now + timedelta(days=14),
        is_cancelled=True,
        notice_status="posted",
    )
    test_db.add_all([past, upcoming, cancelled])
    await test_db.commit()
    for m in (past, upcoming, cancelled):
        await test_db.refresh(m)
    return {"past": past, "upcoming": upcoming, "cancelled": cancelled}


@pytest.mark.asyncio
async def test_ical_feed_urls_are_absolute(client, meetings_across_time):
    """Every VEVENT URL must be an absolute https URL, not a relative path."""
    resp = await client.get("/api/v1/board/meetings/calendar.ics")
    assert resp.status_code == 200
    body = resp.text

    base = (getattr(get_settings(), "frontend_url", None) or "https://l30.org").rstrip("/")

    upcoming_id = meetings_across_time["upcoming"].id
    past_id = meetings_across_time["past"].id

    assert f"URL:{base}/board/meetings/{upcoming_id}" in body
    assert f"URL:{base}/board/meetings/{past_id}" in body
    # No relative-URL form should remain
    assert "URL:/board/meetings/" not in body


@pytest.mark.asyncio
async def test_ical_feed_includes_past_meetings(client, meetings_across_time):
    """iCal feed must surface past non-cancelled meetings (defect B)."""
    resp = await client.get("/api/v1/board/meetings/calendar.ics")
    assert resp.status_code == 200
    body = resp.text

    past = meetings_across_time["past"]
    upcoming = meetings_across_time["upcoming"]
    cancelled = meetings_across_time["cancelled"]

    assert f"UID:meeting-{past.id}@l30.library" in body
    assert f"UID:meeting-{upcoming.id}@l30.library" in body
    # Cancelled meetings are still excluded
    assert f"UID:meeting-{cancelled.id}@l30.library" not in body
    # Sanity: DTSTART for the past meeting (year-month prefix from scheduled_date)
    past_stamp = (past.start_time or past.scheduled_date).strftime("%Y%m%d")
    assert f"DTSTART:{past_stamp}" in body


@pytest.mark.asyncio
async def test_rss_feed_links_are_absolute(client, meetings_across_time):
    """RSS item <link> and channel <link> must be absolute URLs."""
    resp = await client.get("/api/v1/board/meetings/feed.xml")
    assert resp.status_code == 200
    body = resp.text

    base = (getattr(get_settings(), "frontend_url", None) or "https://l30.org").rstrip("/")
    upcoming_id = meetings_across_time["upcoming"].id

    assert f"<link>{base}/board/meetings/{upcoming_id}</link>" in body
    assert f"<link>{base}/board/meetings</link>" in body
    assert "<link>/board/meetings/" not in body
    assert "<link>/board/meetings</link>" not in body


@pytest.mark.asyncio
async def test_feeds_honor_frontend_url_setting(client, meetings_across_time, monkeypatch):
    """Changing settings.frontend_url changes the emitted absolute URLs."""
    monkeypatch.setattr(get_settings(), "frontend_url", "https://staging.example.test/")

    ical = await client.get("/api/v1/board/meetings/calendar.ics")
    rss = await client.get("/api/v1/board/meetings/feed.xml")
    assert ical.status_code == 200
    assert rss.status_code == 200

    upcoming_id = meetings_across_time["upcoming"].id
    assert f"URL:https://staging.example.test/board/meetings/{upcoming_id}" in ical.text
    assert f"<link>https://staging.example.test/board/meetings/{upcoming_id}</link>" in rss.text
