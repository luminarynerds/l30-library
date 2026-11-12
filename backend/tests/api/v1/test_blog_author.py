# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API tests for the blog author FK + co-authors M2M wiring.

Covers:
- Create defaults author_id to current_user.id when omitted.
- Create accepts explicit author_id + co_author_ids.
- Bad author_id => 400.
- Legacy posts (author_id=NULL, free-text author_name/author_role)
  still serialize and render via byline fallback.
- Update changes author_id and clears co-authors with [].
"""

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.models.blog import BlogPost
from app.models.user import User, UserRole


async def _make_user(db, *, email: str, first: str, last: str, role: UserRole = UserRole.STAFF):
    user = User(
        email=email,
        password_hash=hash_password("Password123!"),
        first_name=first,
        last_name=last,
        role=role,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_create_post_with_explicit_author_id(
    staff_client: AsyncClient, test_db, test_staff
):
    other = await _make_user(
        test_db, email="other.author@example.com", first="Other", last="Author"
    )
    resp = await staff_client.post(
        "/api/v1/blog/posts",
        json={
            "title": "Hello world",
            "body": "<p>hi</p>",
            "author_id": other.id,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["author_id"] == other.id
    assert body["author"] is not None
    assert body["author"]["id"] == other.id
    assert body["author"]["full_name"] == "Other Author"
    # No co-authors supplied
    assert body["co_authors"] == []
    # byline computed from FK, not legacy string
    assert body["byline"].startswith("Other Author")


@pytest.mark.asyncio
async def test_create_post_without_author_id_defaults_to_current_user(
    staff_client: AsyncClient, test_db, test_staff
):
    resp = await staff_client.post(
        "/api/v1/blog/posts",
        json={"title": "Default author", "body": "<p>x</p>"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["author_id"] == test_staff.id
    assert body["author"]["id"] == test_staff.id
    assert body["author"]["full_name"] == "Staff Member"


@pytest.mark.asyncio
async def test_create_post_with_co_authors(
    staff_client: AsyncClient, test_db, test_staff
):
    co1 = await _make_user(
        test_db, email="co1@example.com", first="Co", last="One"
    )
    co2 = await _make_user(
        test_db, email="co2@example.com", first="Co", last="Two"
    )
    resp = await staff_client.post(
        "/api/v1/blog/posts",
        json={
            "title": "With co-authors",
            "body": "<p>x</p>",
            "author_id": test_staff.id,
            "co_author_ids": [co1.id, co2.id],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["author_id"] == test_staff.id
    returned_co_ids = [c["id"] for c in body["co_authors"]]
    assert returned_co_ids == [co1.id, co2.id]


@pytest.mark.asyncio
async def test_create_post_with_nonexistent_author_id_returns_400(
    staff_client: AsyncClient, test_db, test_staff
):
    resp = await staff_client.post(
        "/api/v1/blog/posts",
        json={
            "title": "Bad author",
            "body": "<p>x</p>",
            "author_id": 999_999,
        },
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_legacy_post_renders_byline_from_strings(
    staff_client: AsyncClient, test_db
):
    """A row written before the FK existed should still serialize."""
    post = BlogPost(
        title="Legacy",
        slug="legacy-post",
        body="<p>old</p>",
        author_name="Jane Doe",
        author_role="Director",
        # author_id intentionally left NULL
    )
    test_db.add(post)
    await test_db.commit()
    await test_db.refresh(post)

    resp = await staff_client.get(f"/api/v1/blog/posts/admin/{post.id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["author_id"] is None
    assert body["author"] is None
    assert body["author_name"] == "Jane Doe"
    assert body["author_role"] == "Director"
    assert body["byline"] == "Jane Doe, Director"


@pytest.mark.asyncio
async def test_update_post_changes_author_id(
    staff_client: AsyncClient, test_db, test_staff
):
    new_author = await _make_user(
        test_db, email="new.author@example.com", first="New", last="Author"
    )
    # Create the post via API so we exercise the full create path.
    create = await staff_client.post(
        "/api/v1/blog/posts",
        json={"title": "Will reassign", "body": "<p>x</p>"},
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]

    resp = await staff_client.put(
        f"/api/v1/blog/posts/{post_id}",
        json={"author_id": new_author.id},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["author_id"] == new_author.id
    assert body["author"]["full_name"] == "New Author"


@pytest.mark.asyncio
async def test_update_post_clears_co_authors(
    staff_client: AsyncClient, test_db, test_staff
):
    co1 = await _make_user(
        test_db, email="clearme1@example.com", first="Clear", last="One"
    )
    co2 = await _make_user(
        test_db, email="clearme2@example.com", first="Clear", last="Two"
    )
    create = await staff_client.post(
        "/api/v1/blog/posts",
        json={
            "title": "Clear test",
            "body": "<p>x</p>",
            "author_id": test_staff.id,
            "co_author_ids": [co1.id, co2.id],
        },
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]
    assert len(create.json()["co_authors"]) == 2

    resp = await staff_client.put(
        f"/api/v1/blog/posts/{post_id}",
        json={"co_author_ids": []},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["co_authors"] == []
