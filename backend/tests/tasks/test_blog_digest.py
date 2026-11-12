# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the blog digest scheduled task."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.blog import BlogPost, BlogPostStatus
from app.models.blog_subscription import BlogEmailSubscription
from app.tasks.blog_digest import send_blog_digests


def _make_sub(
    *,
    email: str,
    frequency: str = "weekly",
    confirmed: bool = True,
    last_sent_at=None,
) -> BlogEmailSubscription:
    return BlogEmailSubscription(
        email=email,
        frequency=frequency,
        confirmation_token=f"ct-{email}",
        unsubscribe_token=f"ut-{email}",
        confirmed_at=(datetime.now(timezone.utc) if confirmed else None),
        last_sent_at=last_sent_at,
    )


async def _seed_post(db, *, days_ago: int = 1) -> BlogPost:
    now = datetime.now(timezone.utc)
    post = BlogPost(
        title="Fresh post",
        slug=f"fresh-post-{days_ago}-{datetime.now(timezone.utc).timestamp()}",
        body="<p>Body</p>",
        tldr="A summary.",
        author_name="Author",
        status=BlogPostStatus.published,
        published_at=now - timedelta(days=days_ago),
    )
    db.add(post)
    await db.commit()
    return post


@pytest.mark.asyncio
async def test_digest_only_processes_confirmed_subs(test_db):
    """2 unconfirmed + 1 confirmed -> only confirmed is sent."""
    await _seed_post(test_db, days_ago=1)

    test_db.add_all(
        [
            _make_sub(email="unconfirmed1@example.com", confirmed=False),
            _make_sub(email="unconfirmed2@example.com", confirmed=False),
            _make_sub(email="confirmed@example.com", confirmed=True),
        ]
    )
    await test_db.commit()

    with patch(
        "app.tasks.blog_digest.send_email",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_send:
        counters = await send_blog_digests(test_db)

    assert counters["sent"] == 1
    assert counters["failed"] == 0

    sent_to = [c.kwargs["to_email"] for c in mock_send.await_args_list]
    assert sent_to == ["confirmed@example.com"]


@pytest.mark.asyncio
async def test_digest_skips_recently_sent_weekly(test_db):
    """Confirmed weekly sub with last_sent_at < 7 days ago is skipped."""
    await _seed_post(test_db, days_ago=1)

    recently_sent = _make_sub(
        email="recent@example.com",
        frequency="weekly",
        confirmed=True,
        last_sent_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    test_db.add(recently_sent)
    await test_db.commit()

    with patch(
        "app.tasks.blog_digest.send_email",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_send:
        counters = await send_blog_digests(test_db)

    assert counters["sent"] == 0
    assert counters["skipped_window"] == 1
    assert mock_send.await_count == 0


@pytest.mark.asyncio
async def test_digest_skips_when_no_new_posts(test_db):
    """Confirmed sub with last_sent_at after all posts -> no posts, skipped."""
    # Old post (older than the last_sent_at floor)
    now = datetime.now(timezone.utc)
    old_post = BlogPost(
        title="Old",
        slug=f"old-post-{now.timestamp()}",
        body="b",
        author_name="a",
        status=BlogPostStatus.published,
        published_at=now - timedelta(days=60),
    )
    test_db.add(old_post)

    sub = _make_sub(
        email="quiet@example.com",
        frequency="weekly",
        confirmed=True,
        last_sent_at=now - timedelta(days=30),  # older than 7d window, eligible
    )
    test_db.add(sub)
    await test_db.commit()

    with patch(
        "app.tasks.blog_digest.send_email",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_send:
        counters = await send_blog_digests(test_db)

    assert counters["sent"] == 0
    assert counters["skipped_no_posts"] == 1
    assert mock_send.await_count == 0


@pytest.mark.asyncio
async def test_digest_one_failure_does_not_block_others(test_db):
    """If send_email raises on one sub, the others still get processed."""
    await _seed_post(test_db, days_ago=1)

    test_db.add_all(
        [
            _make_sub(email="ok-a@example.com", confirmed=True),
            _make_sub(email="boom@example.com", confirmed=True),
            _make_sub(email="ok-b@example.com", confirmed=True),
        ]
    )
    await test_db.commit()

    async def side_effect(*args, **kwargs):
        if kwargs.get("to_email") == "boom@example.com":
            raise RuntimeError("smtp boom")
        return True

    with patch(
        "app.tasks.blog_digest.send_email",
        new_callable=AsyncMock,
        side_effect=side_effect,
    ) as mock_send:
        counters = await send_blog_digests(test_db)

    assert counters["sent"] == 2
    assert counters["failed"] == 1
    # All three were attempted.
    attempted = [c.kwargs["to_email"] for c in mock_send.await_args_list]
    assert set(attempted) == {
        "ok-a@example.com",
        "boom@example.com",
        "ok-b@example.com",
    }
