# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the scheduled blog publisher task."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog import BlogPost, BlogPostStatus
from app.tasks.blog_publisher import publish_scheduled_blog_posts


def _make_post(slug: str, status: BlogPostStatus, scheduled_at=None) -> BlogPost:
    return BlogPost(
        title=f"Publisher Test {slug}",
        slug=f"publisher-test-{slug}",
        body="<p>body</p>",
        author_name="Author",
        status=status,
        scheduled_at=scheduled_at,
        read_time_minutes=1,
    )


@pytest.mark.asyncio
async def test_promotes_past_scheduled(test_db: AsyncSession):
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    p = _make_post("past", BlogPostStatus.scheduled, scheduled_at=past)
    test_db.add(p)
    await test_db.commit()
    counts = await publish_scheduled_blog_posts(test_db)
    assert counts["promoted"] == 1
    refreshed = await test_db.get(BlogPost, p.id)
    assert refreshed.status == BlogPostStatus.published
    assert refreshed.published_at == past


@pytest.mark.asyncio
async def test_skips_future_scheduled(test_db: AsyncSession):
    future = datetime.now(timezone.utc) + timedelta(minutes=30)
    p = _make_post("future", BlogPostStatus.scheduled, scheduled_at=future)
    test_db.add(p)
    await test_db.commit()
    counts = await publish_scheduled_blog_posts(test_db)
    assert counts["promoted"] == 0
    refreshed = await test_db.get(BlogPost, p.id)
    assert refreshed.status == BlogPostStatus.scheduled


@pytest.mark.asyncio
async def test_ignores_already_published(test_db: AsyncSession):
    p = _make_post("pub", BlogPostStatus.published)
    p.published_at = datetime.now(timezone.utc) - timedelta(days=1)
    test_db.add(p)
    await test_db.commit()
    counts = await publish_scheduled_blog_posts(test_db)
    assert counts["promoted"] == 0


@pytest.mark.asyncio
async def test_ignores_drafts(test_db: AsyncSession):
    p = _make_post("draft", BlogPostStatus.draft)
    test_db.add(p)
    await test_db.commit()
    counts = await publish_scheduled_blog_posts(test_db)
    assert counts["promoted"] == 0


@pytest.mark.asyncio
async def test_published_at_defaults_to_scheduled_at(test_db: AsyncSession):
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    p = _make_post("past2", BlogPostStatus.scheduled, scheduled_at=past)
    test_db.add(p)
    await test_db.commit()
    await publish_scheduled_blog_posts(test_db)
    refreshed = await test_db.get(BlogPost, p.id)
    assert refreshed.published_at == past


@pytest.mark.asyncio
async def test_idempotent_on_empty(test_db: AsyncSession):
    counts = await publish_scheduled_blog_posts(test_db)
    assert counts == {"considered": 0, "promoted": 0}


@pytest.mark.asyncio
async def test_list_posts_no_longer_writes(test_db: AsyncSession, public_client):
    """Ensure the public list endpoint no longer auto-publishes (the inline
    block was removed in favor of the scheduler job)."""
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    p = _make_post("noauto", BlogPostStatus.scheduled, scheduled_at=past)
    test_db.add(p)
    await test_db.commit()

    resp = await public_client.get("/api/v1/blog/posts")
    assert resp.status_code == 200

    # Post should NOT have been promoted by the read path
    result = await test_db.execute(select(BlogPost).where(BlogPost.id == p.id))
    row = result.scalar_one()
    assert row.status == BlogPostStatus.scheduled


@pytest.mark.asyncio
async def test_feed_no_longer_writes(test_db: AsyncSession, public_client):
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    p = _make_post("noauto2", BlogPostStatus.scheduled, scheduled_at=past)
    test_db.add(p)
    await test_db.commit()

    resp = await public_client.get("/api/v1/blog/feed")
    assert resp.status_code == 200

    result = await test_db.execute(select(BlogPost).where(BlogPost.id == p.id))
    row = result.scalar_one()
    assert row.status == BlogPostStatus.scheduled
