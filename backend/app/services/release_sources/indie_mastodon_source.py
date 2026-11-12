# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import re

import httpx

from app.core.logging import get_logger

from .ollama_extractor import extract_announcement

logger = get_logger(__name__)

_TIMEOUT = 25.0
_TAG_RE = re.compile(r"<[^>]+>")

INSTANCE = "https://mastodon.social"
TAGS = ["indieauthor", "newrelease", "selfpublishing"]
MIN_ENGAGEMENT = 2
MAX_PAGES_PER_TAG = 5
USER_AGENT = "l30-releasebot/1.0 (+https://l30.org; howdy@l30.org)"


def _strip_html(text: str) -> str:
    return _TAG_RE.sub(" ", text or "").strip()


async def fetch_tag_timeline(tag: str, max_pages: int = MAX_PAGES_PER_TAG) -> list[dict]:
    """Fetch up to max_pages*40 recent public toots for one hashtag. Raises on HTTP error."""
    toots: list[dict] = []
    max_id: str | None = None
    async with httpx.AsyncClient(
        timeout=_TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True
    ) as client:
        for _ in range(max_pages):
            params: dict = {"limit": 40}
            if max_id:
                params["max_id"] = max_id
            resp = await client.get(f"{INSTANCE}/api/v1/timelines/tag/{tag}", params=params)
            resp.raise_for_status()
            page = resp.json()
            if not page:
                break
            toots.extend(page)
            max_id = page[-1].get("id")
            if not max_id:
                break
    return toots


async def collect_buzzed_posts(
    seen_urls: set[str],
    tags=TAGS,
    max_posts: int = 12,
    min_engagement: int = MIN_ENGAGEMENT,
) -> list[dict]:
    """Buzz-gated Mastodon collection: bot-filter -> engagement gate -> unseen -> top-N by
    engagement -> Ollama announcement extraction. Returns the editorial post dict shape plus
    'engagement'. Compliance: only extracted facts + toot URL leave this function; toot bodies
    are never returned or persisted."""
    candidates: dict[str, dict] = {}
    for tag in tags:
        try:
            toots = await fetch_tag_timeline(tag)
        except Exception as e:  # noqa: BLE001 -- one tag down must not abort the rest
            logger.error(f"Mastodon tag '{tag}' fetch failed: {e}")
            continue
        for toot in toots:
            url = (toot.get("url") or "").strip()
            if not url or url in seen_urls or url in candidates:
                continue
            account = toot.get("account") or {}
            if account.get("bot"):
                continue
            engagement = (toot.get("favourites_count") or 0) + (toot.get("reblogs_count") or 0)
            if engagement < min_engagement:
                continue
            text = _strip_html(toot.get("content") or "")
            candidates[url] = {
                "url": url,
                "outlet": f"mastodon-{tag}",
                "title": text[:120],
                "text": text,
                "display_name": (account.get("display_name") or account.get("acct") or "").strip(),
                "engagement": engagement,
            }
    ranked = sorted(candidates.values(), key=lambda c: c["engagement"], reverse=True)[:max_posts]
    out: list[dict] = []
    for cand in ranked:
        try:
            item = await extract_announcement(cand["text"])
        except Exception as e:  # noqa: BLE001 -- one extraction failure must not abort the batch
            logger.error(f"Announcement extraction failed for {cand['url']}: {e}")
            continue
        if item and not item.get("author"):
            item = {**item, "author": cand["display_name"]}
        out.append(
            {
                "url": cand["url"],
                "outlet": cand["outlet"],
                "title": cand["title"],
                "engagement": cand["engagement"],
                "extracted": [item] if item else [],
            }
        )
    return out
