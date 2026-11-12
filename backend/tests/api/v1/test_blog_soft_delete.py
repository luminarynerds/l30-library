# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for blog soft-delete + restore."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog import BlogPost, BlogPostStatus


def _make_published(slug: str) -> BlogPost:
    return BlogPost(
        title=f"SD {slug}",
        slug=f"sd-{slug}",
        body="<p>body</p>",
        author_name="A",
        status=BlogPostStatus.published,
        published_at=datetime.now(timezone.utc),
        read_time_minutes=1,
    )


@pytest.fixture
async def post_a(test_db: AsyncSession) -> BlogPost:
    p = _make_published("a")
    test_db.add(p)
    await test_db.commit()
    await test_db.refresh(p)
    return p


@pytest.fixture
async def post_b(test_db: AsyncSession) -> BlogPost:
    p = _make_published("b")
    test_db.add(p)
    await test_db.commit()
    await test_db.refresh(p)
    return p


# ---------- DELETE (soft) ----------


@pytest.mark.asyncio
async def test_delete_sets_deleted_at(staff_client, test_db, post_a):
    resp = await staff_client.delete(f"/api/v1/blog/posts/{post_a.id}")
    assert resp.status_code == 204
    # Row still exists with deleted_at set
    refreshed = await test_db.get(BlogPost, post_a.id)
    assert refreshed is not None
    assert refreshed.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_404_when_already_deleted(staff_client, test_db, post_a):
    post_a.deleted_at = datetime.now(timezone.utc)
    await test_db.commit()
    resp = await staff_client.delete(f"/api/v1/blog/posts/{post_a.id}")
    assert resp.status_code == 404


# ---------- RESTORE ----------


@pytest.mark.asyncio
async def test_restore_clears_deleted_at(staff_client, test_db, post_a):
    post_id = post_a.id
    post_a.deleted_at = datetime.now(timezone.utc)
    await test_db.commit()
    resp = await staff_client.post(f"/api/v1/blog/posts/{post_id}/restore")
    assert resp.status_code == 200
    # Expire identity map so we see the route's commit
    test_db.expire_all()
    result = await test_db.execute(select(BlogPost).where(BlogPost.id == post_id))
    refreshed = result.scalar_one()
    assert refreshed.deleted_at is None


@pytest.mark.asyncio
async def test_restore_400_if_not_deleted(staff_client, post_a):
    resp = await staff_client.post(f"/api/v1/blog/posts/{post_a.id}/restore")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_restore_404_if_missing(staff_client):
    resp = await staff_client.post("/api/v1/blog/posts/99999/restore")
    assert resp.status_code == 404


# ---------- Public read paths filter soft-deleted ----------


@pytest.mark.asyncio
async def test_public_list_hides_deleted(public_client, test_db, post_a, post_b):
    post_a.deleted_at = datetime.now(timezone.utc)
    await test_db.commit()
    resp = await public_client.get("/api/v1/blog/posts")
    assert resp.status_code == 200
    slugs = {item["slug"] for item in resp.json()["items"]}
    assert post_a.slug not in slugs
    assert post_b.slug in slugs


@pytest.mark.asyncio
async def test_public_get_slug_404_for_deleted(public_client, test_db, post_a):
    post_a.deleted_at = datetime.now(timezone.utc)
    await test_db.commit()
    resp = await public_client.get(f"/api/v1/blog/posts/{post_a.slug}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_feed_excludes_deleted(public_client, test_db, post_a, post_b):
    post_a.deleted_at = datetime.now(timezone.utc)
    await test_db.commit()
    resp = await public_client.get("/api/v1/blog/feed")
    assert resp.status_code == 200
    body = resp.text
    assert post_b.slug in body
    assert post_a.slug not in body


@pytest.mark.asyncio
async def test_sitemap_excludes_deleted(public_client, test_db, post_a, post_b):
    post_a.deleted_at = datetime.now(timezone.utc)
    await test_db.commit()
    resp = await public_client.get("/api/v1/blog/sitemap.xml")
    assert resp.status_code == 200
    body = resp.text
    assert post_b.slug in body
    assert post_a.slug not in body


# ---------- Bulk delete ----------


@pytest.mark.asyncio
async def test_bulk_delete_returns_actual_count(staff_client, test_db, post_a, post_b):
    # Pre-soft-delete post_a so it's "already deleted"; include a missing id too
    post_a.deleted_at = datetime.now(timezone.utc)
    await test_db.commit()
    resp = await staff_client.post(
        "/api/v1/blog/posts/bulk/delete",
        json=[post_a.id, post_b.id, 99999],
    )
    assert resp.status_code == 200
    body = resp.json()
    # Only post_b actually transitioned
    assert body["deleted"] == 1
    assert body["requested"] == 3
    # post_b is now soft-deleted
    refreshed = await test_db.get(BlogPost, post_b.id)
    assert refreshed.deleted_at is not None


# ---------- Admin list: trash filter + deleted_at exclusion ----------


@pytest.fixture
async def post_draft(test_db: AsyncSession) -> BlogPost:
    p = BlogPost(
        title="SD draft",
        slug="sd-draft",
        body="<p>body</p>",
        author_name="A",
        status=BlogPostStatus.draft,
        read_time_minutes=1,
    )
    test_db.add(p)
    await test_db.commit()
    await test_db.refresh(p)
    return p


@pytest.mark.asyncio
async def test_admin_list_trash_returns_only_deleted_ordered_by_deleted_at(
    staff_client, test_db, post_a, post_b, post_draft
):
    """?status=trash returns only deleted posts, ordered by deleted_at DESC."""
    older = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer = datetime(2026, 2, 1, tzinfo=timezone.utc)
    post_a.deleted_at = older
    post_b.deleted_at = newer
    await test_db.commit()

    resp = await staff_client.get("/api/v1/blog/posts/admin?status=trash")
    assert resp.status_code == 200
    body = resp.json()
    slugs = [item["slug"] for item in body["items"]]
    assert post_a.slug in slugs
    assert post_b.slug in slugs
    assert post_draft.slug not in slugs
    # Newer deleted_at first
    assert slugs.index(post_b.slug) < slugs.index(post_a.slug)
    # deleted_at exposed on list items
    for item in body["items"]:
        assert item["deleted_at"] is not None


@pytest.mark.asyncio
async def test_admin_list_no_filter_excludes_deleted(
    staff_client, test_db, post_a, post_b, post_draft
):
    """No status filter excludes soft-deleted rows."""
    post_a.deleted_at = datetime.now(timezone.utc)
    await test_db.commit()

    resp = await staff_client.get("/api/v1/blog/posts/admin")
    assert resp.status_code == 200
    slugs = {item["slug"] for item in resp.json()["items"]}
    assert post_a.slug not in slugs
    assert post_b.slug in slugs
    assert post_draft.slug in slugs


@pytest.mark.asyncio
async def test_admin_list_status_published_excludes_deleted(
    staff_client, test_db, post_a, post_b
):
    """?status=published excludes a deleted-but-published post."""
    post_a.deleted_at = datetime.now(timezone.utc)
    await test_db.commit()

    resp = await staff_client.get("/api/v1/blog/posts/admin?status=published")
    assert resp.status_code == 200
    slugs = {item["slug"] for item in resp.json()["items"]}
    assert post_a.slug not in slugs
    assert post_b.slug in slugs


@pytest.mark.asyncio
async def test_admin_list_header_counts_exclude_deleted(
    staff_client, test_db, post_a, post_b, post_draft
):
    """draft_count / published_count / scheduled_count exclude soft-deleted rows."""
    resp0 = await staff_client.get("/api/v1/blog/posts/admin")
    b0 = resp0.json()
    base_published = b0["published_count"]
    base_draft = b0["draft_count"]

    post_a.deleted_at = datetime.now(timezone.utc)
    post_draft.deleted_at = datetime.now(timezone.utc)
    await test_db.commit()

    resp = await staff_client.get("/api/v1/blog/posts/admin")
    body = resp.json()
    assert body["published_count"] == base_published - 1
    assert body["draft_count"] == base_draft - 1


@pytest.mark.asyncio
async def test_admin_list_roundtrip_delete_then_restore(
    staff_client, test_db, post_a
):
    """Delete -> appears in trash, not in published. Restore -> reverse."""
    resp = await staff_client.get("/api/v1/blog/posts/admin")
    assert post_a.slug in {item["slug"] for item in resp.json()["items"]}

    del_resp = await staff_client.delete(f"/api/v1/blog/posts/{post_a.id}")
    assert del_resp.status_code == 204

    trash = await staff_client.get("/api/v1/blog/posts/admin?status=trash")
    assert post_a.slug in {item["slug"] for item in trash.json()["items"]}

    pub = await staff_client.get("/api/v1/blog/posts/admin?status=published")
    assert post_a.slug not in {item["slug"] for item in pub.json()["items"]}

    restore_resp = await staff_client.post(f"/api/v1/blog/posts/{post_a.id}/restore")
    assert restore_resp.status_code == 200

    trash2 = await staff_client.get("/api/v1/blog/posts/admin?status=trash")
    assert post_a.slug not in {item["slug"] for item in trash2.json()["items"]}

    pub2 = await staff_client.get("/api/v1/blog/posts/admin?status=published")
    assert post_a.slug in {item["slug"] for item in pub2.json()["items"]}
