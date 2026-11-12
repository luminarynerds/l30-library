# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.release_tracker import ProcessedRssPost
from app.schemas.release_tracker import IngestionStats
from app.services.editorial_release_ingestion import EditorialReleaseIngestionService

from .release_sources.editorial_rss_source import collect_new_posts
from .release_sources.title_resolver import resolve

logger = get_logger(__name__)


async def ingest_rss(db: AsyncSession) -> IngestionStats:
    """Pull new editorial RSS posts -> resolve titles -> ingest as TrackerBooks -> mark posts processed."""
    seen = set(
        (await db.execute(select(ProcessedRssPost.url))).scalars().all()
    )
    posts = await collect_new_posts(seen_urls=seen)
    titles = []
    for post in posts:
        for item in post["extracted"]:
            titles.append(await resolve(item["title"], item["author"]))
    stats = await EditorialReleaseIngestionService(db).ingest(titles)
    for post in posts:
        db.add(ProcessedRssPost(url=post["url"], outlet=post["outlet"]))
    await db.commit()
    logger.info("Editorial RSS ingestion", extra={"posts": len(posts), "added": stats.books_added})
    return stats
