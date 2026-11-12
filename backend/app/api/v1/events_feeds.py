# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public iCal and RSS feeds for upcoming published events.

Mirrors the blueprint in ``backend/app/api/v1/board/meetings.py``. Helpers are
duplicated locally rather than imported across modules to keep the events and
board surfaces independent.
"""

from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.event import Event

logger = get_logger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

# Cap the number of upcoming events returned to keep feed responses bounded.
MAX_FEED_EVENTS = 500


def _fmt_dt(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape_ical(text):
    if not text:
        return ""
    return (
        text.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
    )


def _escape_xml(text):
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _rfc822(dt):
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")


def _event_url(event_id: int) -> str:
    base = (getattr(get_settings(), "frontend_url", None) or "").rstrip("/")
    return f"{base}/events/{event_id}"


async def _fetch_upcoming_events(db: AsyncSession):
    now = datetime.now(timezone.utc)
    query = (
        select(Event)
        .where(Event.is_published == True)  # noqa: E712 - SQLAlchemy expression
        .where(Event.start_time >= now)
        .order_by(Event.start_time.asc())
        .limit(MAX_FEED_EVENTS)
    )
    result = await db.execute(query)
    return now, result.scalars().all()


@router.get("/feed.ics")
@limiter.limit("60/minute")
async def events_ical_feed(request: Request, db: AsyncSession = Depends(get_db)):
    """iCal feed of upcoming published events (capped at 500)."""
    now, events = await _fetch_upcoming_events(db)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//L30//Events//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:L30 Events",
    ]

    dtstamp = _fmt_dt(now)
    for event in events:
        dtstart = _fmt_dt(event.start_time)
        dtend = _fmt_dt(event.end_time) if event.end_time else None
        if not dtstart:
            continue
        uid = f"event-{event.id}@example.com"

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{dtstamp}")
        lines.append(f"DTSTART:{dtstart}")
        if dtend:
            lines.append(f"DTEND:{dtend}")
        lines.append(f"SUMMARY:{_escape_ical(event.title)}")
        if event.location:
            lines.append(f"LOCATION:{_escape_ical(event.location)}")
        if event.description:
            lines.append(f"DESCRIPTION:{_escape_ical(event.description)}")
        lines.append(f"URL:{_event_url(event.id)}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    cal_text = "\r\n".join(lines) + "\r\n"
    return Response(content=cal_text, media_type="text/calendar")


@router.get("/feed.rss")
@limiter.limit("60/minute")
async def events_rss_feed(request: Request, db: AsyncSession = Depends(get_db)):
    """RSS feed of upcoming published events (capped at 500)."""
    now, events = await _fetch_upcoming_events(db)

    base = (getattr(get_settings(), "frontend_url", None) or "").rstrip("/")
    channel_link = f"{base}/events"

    items_xml = ""
    for event in events:
        desc = _escape_xml(event.description or "")
        if event.location:
            location = _escape_xml(event.location)
            desc = f"{desc} | Location: {location}" if desc else f"Location: {location}"
        items_xml += (
            "    <item>\n"
            f"      <title>{_escape_xml(event.title)}</title>\n"
            f"      <link>{_escape_xml(_event_url(event.id))}</link>\n"
            f'      <guid isPermaLink="false">event-{event.id}@example.com</guid>\n'
            f"      <pubDate>{_rfc822(event.start_time)}</pubDate>\n"
            f"      <description>{desc}</description>\n"
            "    </item>\n"
        )

    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        "    <title>L30 Events</title>\n"
        f"    <link>{_escape_xml(channel_link)}</link>\n"
        "    <description>Upcoming public events at the L30 Community Library</description>\n"
        f"    <lastBuildDate>{_rfc822(now)}</lastBuildDate>\n"
        f"{items_xml}"
        "  </channel>\n"
        "</rss>"
    )

    return Response(content=rss, media_type="application/rss+xml")
