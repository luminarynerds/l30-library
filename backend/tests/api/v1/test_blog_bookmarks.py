# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for patron blog bookmark endpoints.

Endpoints under test:
* GET /api/v1/blog/bookmarks
* POST /api/v1/blog/bookmarks/{post_id}
* DELETE /api/v1/blog/bookmarks/{post_id}
"""

import asyncio
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.blog import BlogPost, BlogPostStatus
from app.models.blog_bookmark import BlogPostBookmark
from app.models.user import User, UserRole


# ---------- Fixtures ----------


@pytest.fixture
async def patron(test_db: AsyncSession) -> User:
    user = User(
        email="patron@blogbm.test",
        password_hash=hash_password("PatronPassword123!"),
        first_name="Patron",
        last_name="A",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def published_post(test_db: AsyncSession) -> BlogPost:
    post = BlogPost(
        title="Patron Bookmark Test Post",
        slug="patron-bookmark-test-post",
        body="A published post.",
        author_name="Library Staff",
        status=BlogPostStatus.published,
        published_at=datetime.now(timezone.utc),
        read_time_minutes=1,
    )
    test_db.add(post)
    await test_db.commit()
    await test_db.refresh(post)
    return post


@pytest.fixture
async def second_published_post(test_db: AsyncSession) -> BlogPost:
    post = BlogPost(
        title="Second Patron Bookmark Post",
        slug="second-patron-bookmark-post",
        body="Another published post.",
        author_name="Library Staff",
        status=BlogPostStatus.published,
        published_at=datetime.now(timezone.utc),
        read_time_minutes=1,
    )
    test_db.add(post)
    await test_db.commit()
    await test_db.refresh(post)
    return post


@pytest.fixture
async def draft_post(test_db: AsyncSession) -> BlogPost:
    post = BlogPost(
        title="Draft Bookmark Test Post",
        slug="draft-bookmark-test-post",
        body="A draft post (not bookmarkable).",
        author_name="Library Staff",
        status=BlogPostStatus.draft,
        read_time_minutes=1,
    )
    test_db.add(post)
    await test_db.commit()
    await test_db.refresh(post)
    return post


@pytest.fixture
async def patron_client(test_db: AsyncSession, patron: User) -> AsyncClient:
    # Override the canonical source -- the alias re-export will not be picked
    # up by dependency_overrides. See [[feedback_l30_authcontext_global_mock_override]]
    # and conftest pattern in test_hub_favorites.py.
    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return patron

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def anon_client(test_db: AsyncSession) -> AsyncClient:
    """AsyncClient with no get_current_user override -- routes must 401."""
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------- Tests ----------


@pytest.mark.asyncio
async def test_post_creates_bookmark(
    patron_client: AsyncClient, published_post: BlogPost
):
    post_id = published_post.id
    resp = await patron_client.post(f"/api/v1/blog/bookmarks/{post_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["post_id"] == post_id
    assert body["already_bookmarked"] is False
    assert "created_at" in body


@pytest.mark.asyncio
async def test_post_is_idempotent(
    patron_client: AsyncClient, published_post: BlogPost, test_db: AsyncSession
):
    # Snapshot before the shared-session commits inside the route expire
    # the ORM instance.
    post_id = published_post.id

    first = await patron_client.post(f"/api/v1/blog/bookmarks/{post_id}")
    assert first.status_code == 200
    assert first.json()["already_bookmarked"] is False

    second = await patron_client.post(f"/api/v1/blog/bookmarks/{post_id}")
    assert second.status_code == 200
    assert second.json()["already_bookmarked"] is True
    # No duplicate row was created.
    count_result = await test_db.execute(
        select(BlogPostBookmark).where(BlogPostBookmark.post_id == post_id)
    )
    rows = count_result.scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_post_missing_post_404(patron_client: AsyncClient):
    resp = await patron_client.post("/api/v1/blog/bookmarks/999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_post_unpublished_post_404(
    patron_client: AsyncClient, draft_post: BlogPost
):
    post_id = draft_post.id
    resp = await patron_client.post(f"/api/v1/blog/bookmarks/{post_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_post_anon_401(anon_client: AsyncClient, published_post: BlogPost):
    post_id = published_post.id
    resp = await anon_client.post(f"/api/v1/blog/bookmarks/{post_id}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_removes_bookmark(
    patron_client: AsyncClient, published_post: BlogPost
):
    post_id = published_post.id
    create = await patron_client.post(f"/api/v1/blog/bookmarks/{post_id}")
    assert create.status_code == 200

    delete = await patron_client.delete(f"/api/v1/blog/bookmarks/{post_id}")
    assert delete.status_code == 204

    # Listing now empty
    listing = await patron_client.get("/api/v1/blog/bookmarks")
    assert listing.status_code == 200
    assert listing.json() == []


@pytest.mark.asyncio
async def test_delete_not_bookmarked_404(
    patron_client: AsyncClient, published_post: BlogPost
):
    post_id = published_post.id
    resp = await patron_client.delete(f"/api/v1/blog/bookmarks/{post_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_returns_bookmarks_desc(
    patron_client: AsyncClient,
    published_post: BlogPost,
    second_published_post: BlogPost,
):
    post1_id = published_post.id
    post2_id = second_published_post.id

    # Bookmark first, then second -- second should appear first (desc order).
    r1 = await patron_client.post(f"/api/v1/blog/bookmarks/{post1_id}")
    assert r1.status_code == 200
    # Tiny sleep to guarantee distinct timestamps even on coarse-clock backends.
    await asyncio.sleep(0.01)
    r2 = await patron_client.post(f"/api/v1/blog/bookmarks/{post2_id}")
    assert r2.status_code == 200

    listing = await patron_client.get("/api/v1/blog/bookmarks")
    assert listing.status_code == 200
    items = listing.json()
    assert len(items) == 2
    assert items[0]["id"] == post2_id
    assert items[1]["id"] == post1_id
    assert "bookmarked_at" in items[0]
    assert "bookmarked_at" in items[1]


@pytest.mark.asyncio
async def test_get_paginated(
    patron_client: AsyncClient,
    published_post: BlogPost,
    second_published_post: BlogPost,
):
    post1_id = published_post.id
    post2_id = second_published_post.id

    await patron_client.post(f"/api/v1/blog/bookmarks/{post1_id}")
    await asyncio.sleep(0.01)
    await patron_client.post(f"/api/v1/blog/bookmarks/{post2_id}")

    page1 = await patron_client.get("/api/v1/blog/bookmarks?limit=1&offset=0")
    assert page1.status_code == 200
    assert len(page1.json()) == 1
    assert page1.json()[0]["id"] == post2_id

    page2 = await patron_client.get("/api/v1/blog/bookmarks?limit=1&offset=1")
    assert page2.status_code == 200
    assert len(page2.json()) == 1
    assert page2.json()[0]["id"] == post1_id


@pytest.mark.asyncio
async def test_get_anon_401(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/blog/bookmarks")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_db_unique_constraint_enforced(
    test_db: AsyncSession, patron: User, published_post: BlogPost
):
    """Sanity check: the DB enforces the (user_id, post_id) unique constraint.

    The POST route relies on catching IntegrityError, so this constraint must
    actually be present in the test DB.
    """
    user_id = patron.id
    post_id = published_post.id

    b1 = BlogPostBookmark(user_id=user_id, post_id=post_id)
    test_db.add(b1)
    await test_db.commit()

    b2 = BlogPostBookmark(user_id=user_id, post_id=post_id)
    test_db.add(b2)
    with pytest.raises(IntegrityError):
        await test_db.commit()
    await test_db.rollback()
