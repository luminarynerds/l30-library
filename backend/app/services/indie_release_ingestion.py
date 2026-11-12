# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.release_tracker import ProcessedRssPost, ReleaseSource
from app.schemas.release_tracker import IngestionStats
from app.services.editorial_release_ingestion import EditorialReleaseIngestionService

from .release_sources.indie_itchio_source import collect_new_books
from .release_sources.indie_mastodon_source import collect_buzzed_posts
from .release_sources.title_resolver import resolve

logger = get_logger(__name__)

INDIE_SOURCES = (ReleaseSource.INDIE_MASTODON.value, ReleaseSource.INDIE_ITCHIO.value)


async def ingest_indie(db: AsyncSession, sources: list[str] | None = None) -> IngestionStats:
    """Buzz-gated indie ingest (Mastodon + itch.io) -> resolve -> TrackerBooks -> mark processed.
    `sources` limits the run (values from INDIE_SOURCES); None runs both. Mirrors ingest_rss."""
    wanted = set(sources or INDIE_SOURCES)
    seen = set((await db.execute(select(ProcessedRssPost.url))).scalars().all())

    posts: list[tuple[str, dict]] = []  # (source_value, post)
    if ReleaseSource.INDIE_MASTODON.value in wanted:
        try:
            for p in await collect_buzzed_posts(seen_urls=seen):
                posts.append((ReleaseSource.INDIE_MASTODON.value, p))
        except Exception as e:  # noqa: BLE001 -- one connector down must not abort the other
            logger.error(f"Mastodon indie collection failed: {e}")
    if ReleaseSource.INDIE_ITCHIO.value in wanted:
        try:
            for p in await collect_new_books(seen_urls=seen):
                posts.append((ReleaseSource.INDIE_ITCHIO.value, p))
        except Exception as e:  # noqa: BLE001
            logger.error(f"itch.io indie collection failed: {e}")

    titles = []
    for source_value, post in posts:
        buzz = (
            f"Mastodon buzz: {post['engagement']} interactions"
            if source_value == ReleaseSource.INDIE_MASTODON.value
            else None
        )
        for item in post["extracted"]:
            titles.append(
                await resolve(
                    item["title"],
                    item["author"],
                    source=source_value,
                    source_url=post["url"],
                    blurb_credit=buzz,
                )
            )

    stats = await EditorialReleaseIngestionService(db).ingest(titles)
    for _, post in posts:
        db.add(ProcessedRssPost(url=post["url"], outlet=post["outlet"]))
    await db.commit()
    logger.info(
        "Indie release ingestion",
        extra={"posts": len(posts), "added": stats.books_added, "sources": sorted(wanted)},
    )
    return stats
