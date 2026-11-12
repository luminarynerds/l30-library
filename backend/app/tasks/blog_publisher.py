# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.blog import BlogPost, BlogPostStatus

logger = get_logger(__name__)


async def publish_scheduled_blog_posts(
    db: AsyncSession | None = None,
) -> dict:
    if db is not None:
        return await _run(db)

    async with AsyncSessionLocal() as owned_db:
        return await _run(owned_db)


async def _run(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(BlogPost)
        .where(
            BlogPost.status == BlogPostStatus.scheduled,
            BlogPost.scheduled_at <= now,
        )
        .with_for_update(skip_locked=True)
    )
    rows = list(result.scalars().all())
    promoted = 0
    for post in rows:
        post.status = BlogPostStatus.published
        if not post.published_at:
            post.published_at = post.scheduled_at or now
        promoted += 1
    if promoted:
        await db.commit()
        logger.info("Promoted %d scheduled blog post(s)", promoted)
    return {"considered": len(rows), "promoted": promoted}
