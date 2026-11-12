# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for blog preview share-link endpoints.

Endpoints under test:
* POST /api/v1/blog/posts/{post_id}/preview-link  (staff only)
* GET  /api/v1/blog/posts/preview/{slug}?sig=...  (token bypass OR staff)
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.blog import _sign_preview_token
from app.models.blog import BlogPost, BlogPostStatus


# ---------- Fixtures ----------


@pytest.fixture
async def draft_post(test_db: AsyncSession) -> BlogPost:
    post = BlogPost(
        title="Preview Test Draft",
        slug="preview-test-draft",
        body="<p>Draft body</p>",
        author_name="Test Author",
        status=BlogPostStatus.draft,
        read_time_minutes=1,
    )
    test_db.add(post)
    await test_db.commit()
    await test_db.refresh(post)
    return post


@pytest.fixture
async def published_post(test_db: AsyncSession) -> BlogPost:
    post = BlogPost(
        title="Preview Test Published",
        slug="preview-test-published",
        body="<p>Published body</p>",
        author_name="Test Author",
        status=BlogPostStatus.published,
        published_at=datetime.now(timezone.utc),
        read_time_minutes=1,
    )
    test_db.add(post)
    await test_db.commit()
    await test_db.refresh(post)
    return post


@pytest.fixture
async def second_draft_post(test_db: AsyncSession) -> BlogPost:
    post = BlogPost(
        title="Preview Test Second Draft",
        slug="preview-test-second-draft",
        body="<p>Second body</p>",
        author_name="Test Author",
        status=BlogPostStatus.draft,
        read_time_minutes=1,
    )
    test_db.add(post)
    await test_db.commit()
    await test_db.refresh(post)
    return post


# ---------- POST /posts/{id}/preview-link ----------


@pytest.mark.asyncio
async def test_staff_creates_preview_link_for_draft(staff_client, draft_post):
    resp = await staff_client.post(f"/api/v1/blog/posts/{draft_post.id}/preview-link")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "url" in body and "expires_at" in body
    assert "sig=" in body["url"]
    assert draft_post.slug in body["url"]


@pytest.mark.asyncio
async def test_preview_link_rejects_published(staff_client, published_post):
    resp = await staff_client.post(
        f"/api/v1/blog/posts/{published_post.id}/preview-link"
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_preview_link_404_for_missing(staff_client):
    resp = await staff_client.post("/api/v1/blog/posts/99999999/preview-link")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_preview_link_anon_blocked(public_client, draft_post):
    resp = await public_client.post(
        f"/api/v1/blog/posts/{draft_post.id}/preview-link"
    )
    assert resp.status_code in (401, 403)


# ---------- GET /posts/preview/{slug}?sig=... ----------


@pytest.mark.asyncio
async def test_anon_can_view_with_valid_sig(public_client, draft_post):
    token, _ = _sign_preview_token(draft_post.id)
    resp = await public_client.get(
        f"/api/v1/blog/posts/preview/{draft_post.slug}?sig={token}"
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["title"] == draft_post.title


@pytest.mark.asyncio
async def test_expired_sig_returns_410(public_client, draft_post):
    token, _ = _sign_preview_token(draft_post.id, ttl_seconds=-60)
    resp = await public_client.get(
        f"/api/v1/blog/posts/preview/{draft_post.slug}?sig={token}"
    )
    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_tampered_sig_returns_401(public_client, draft_post):
    token, _ = _sign_preview_token(draft_post.id)
    # Flip a character in the signature half (after the `.`)
    head, tail = token.split(".", 1)
    tampered = head + "." + ("A" + tail[1:] if tail[0] != "A" else "B" + tail[1:])
    resp = await public_client.get(
        f"/api/v1/blog/posts/preview/{draft_post.slug}?sig={tampered}"
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sig_for_other_post_returns_401(
    public_client, draft_post, second_draft_post
):
    # Sign for second_draft_post but request first by slug
    token, _ = _sign_preview_token(second_draft_post.id)
    resp = await public_client.get(
        f"/api/v1/blog/posts/preview/{draft_post.slug}?sig={token}"
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_no_sig_still_requires_staff(public_client, draft_post):
    resp = await public_client.get(
        f"/api/v1/blog/posts/preview/{draft_post.slug}"
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_no_sig_with_staff_succeeds(staff_client, test_staff, draft_post):
    # The route declares get_optional_user (so the sig path can be anon).
    # staff_client only overrides get_current_user; add the optional override
    # for this test so the staff-fallback branch sees an authed user.
    from app.api.v1.auth.helpers import get_optional_user
    from app.main import app

    async def _override_optional_authed():
        return test_staff

    app.dependency_overrides[get_optional_user] = _override_optional_authed
    try:
        resp = await staff_client.get(
            f"/api/v1/blog/posts/preview/{draft_post.slug}"
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == draft_post.title
    finally:
        app.dependency_overrides.pop(get_optional_user, None)
