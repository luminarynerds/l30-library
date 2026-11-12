# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from app.core.logging import get_logger

from .ollama_extractor import extract_titles
from .rss_feeds import FEEDS, fetch_feed

logger = get_logger(__name__)


async def collect_new_posts(
    seen_urls: set[str], feeds=FEEDS, max_posts: int = 12
) -> list[dict]:
    """For each feed, fetch posts, skip already-seen URLs, and Ollama-extract titles from the rest.
    Returns [{'url','outlet','title','extracted': [{'title','author'}]}] for every new, examined
    (non-errored) post; `extracted` may be empty.

    Caps the number of new (unseen) posts examined this run at `max_posts` (across all feeds) so a
    first run does not fire tens of sequential LLM calls on a CPU host; the weekly cadence drains the
    rest."""
    out: list[dict] = []
    examined = 0
    for outlet, url in feeds:
        if examined >= max_posts:
            break
        try:
            posts = await fetch_feed(url)
        except Exception as e:  # noqa: BLE001 -- one feed down must not abort the rest
            logger.error(f"Feed {outlet} failed: {e}")
            continue
        for post in posts:
            if post["url"] in seen_urls:
                continue
            if examined >= max_posts:
                break
            examined += 1
            try:
                extracted = await extract_titles(post["body"])
            except Exception as e:  # noqa: BLE001 -- one post extraction failure must not abort
                logger.error(f"Extraction failed for {post['url']}: {e}")
                continue
            out.append({"url": post["url"], "outlet": outlet, "title": post["title"], "extracted": extracted})
    return out
