# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from app.core.logging import get_logger

from .ollama_extractor import extract_itch_book
from .rss_feeds import fetch_feed

logger = get_logger(__name__)

FEED_URL = "https://itch.io/books/new-and-popular.xml"
OUTLET = "itchio-books"


async def collect_new_books(seen_urls: set[str], max_posts: int = 12) -> list[dict]:
    """itch.io 'books: new and popular' feed -> unseen items -> Ollama book-classify.
    Returns the editorial post dict shape; non-book items come back with extracted=[] so the
    coordinator marks them processed and never re-examines them."""
    try:
        items = await fetch_feed(FEED_URL)
    except Exception as e:  # noqa: BLE001
        logger.error(f"itch.io feed fetch failed: {e}")
        return []
    out: list[dict] = []
    examined = 0
    for item in items:
        if item["url"] in seen_urls:
            continue
        if examined >= max_posts:
            break
        examined += 1
        try:
            book = await extract_itch_book(f"{item['title']}\n{item['body']}")
        except Exception as e:  # noqa: BLE001 -- one item must not abort the batch
            logger.error(f"itch classification failed for {item['url']}: {e}")
            continue
        out.append(
            {
                "url": item["url"],
                "outlet": OUTLET,
                "title": item["title"],
                "engagement": 0,
                "extracted": [book] if book else [],
            }
        )
    return out
