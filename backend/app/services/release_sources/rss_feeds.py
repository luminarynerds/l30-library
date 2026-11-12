# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import re
from xml.etree import ElementTree as ET

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

_TIMEOUT = 25.0
_CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}encoded"
_TAG_RE = re.compile(r"<[^>]+>")

# Note: Book Riot excluded — its robots.txt forbids AI bots (ai-train=no).
FEEDS = [
    ("millions", "https://themillions.com/feed"),
    ("lithub", "https://lithub.com/feed/"),
    ("tlt", "https://teenlibrariantoolbox.com/feed/"),
    ("brown-bookshelf", "https://thebrownbookshelf.com/feed/"),
]


def _strip_html(text: str) -> str:
    return _TAG_RE.sub(" ", text or "").strip()


def parse_feed(xml_text: str) -> list[dict]:
    """Parse an RSS 2.0 document into [{'url','title','body'}]. body prefers content:encoded, else description."""
    items: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.error(f"RSS parse error: {e}")
        return []
    for item in root.iter("item"):
        link = (item.findtext("link") or "").strip()
        title = (item.findtext("title") or "").strip()
        if not link or not title:
            continue
        content_el = item.find(_CONTENT_NS)
        raw = content_el.text if content_el is not None and content_el.text else (item.findtext("description") or "")
        items.append({"url": link, "title": title, "body": _strip_html(raw)})
    return items


async def fetch_feed(url: str) -> list[dict]:
    """Fetch + parse one feed; [] on network error."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "l30-releasebot/1.0"})
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"RSS fetch failed for {url}: {e}")
        return []
    return parse_feed(resp.text)
