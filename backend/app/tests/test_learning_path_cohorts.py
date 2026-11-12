# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for the learning-path cohort feature (V1).

Covers the round-trip the PR description specifies:

    user A joins path's cohort → lists members (sees self) →
    user B joins → A sees both →
    user B leaves → A sees only self

Plus quick guards on:
  - discussion read/post requires cohort membership (403 for outsiders)
  - join is idempotent
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.auth.helpers import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.learning_path import LearningPath
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
def _cohort_feature_enabled():
    """learning_path_cohorts.router is mounted behind require_cohort_enabled
    (app/api/v1/registry.py), which checks OrganizationFeaturesService --
    every route in this file otherwise 404s with "Learning path cohorts
    feature is not enabled". Mirrors the flag_on-style patch used elsewhere
    (e.g. tests/integration/test_home_visit_day_plan.py) rather than
    seeding a real organization_features row.
    """
    from app.services.organization_features_service import OrganizationFeaturesService
    with patch.object(
        OrganizationFeaturesService, "is_feature_enabled",
        new=AsyncMock(return_value=True),
    ):
        yield


@pytest.fixture
async def path(db):
    p = LearningPath(
        title="Test Path",
        description="A path for cohort tests",
        status="published",
        is_public=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def _make_user(db, suffix: str) -> User:
    u = User(
        email=f"cohort-{suffix}@example.com",
        first_name=f"First{suffix}",
        last_name="Last",
        password_hash="x",
        role=UserRole.PATRON,
        is_active=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest.fixture
async def alice(db):
    return await _make_user(db, "alice")


@pytest.fixture
async def bob(db):
    return await _make_user(db, "bob")


def _override_auth(user: User, db):
    async def _db():
        yield db

    async def _user():
        return user

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user
    app.state.setup_complete = True


def _clear_overrides():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


async def _client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_cohort_full_roundtrip(db, path, alice, bob):
    """alice joins → lists (sees self); bob joins → alice sees both;
    bob leaves → alice sees only self."""
    base = f"/api/v1/learning-paths/{path.id}/cohort"

    # ---- alice joins ----
    _override_auth(alice, db)
    try:
        async with await _client() as ac:
            resp = await ac.post(f"{base}/join")
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["is_member"] is True
            assert data["member_count"] == 1
            assert {m["user_id"] for m in data["members"]} == {alice.id}

            # listing members returns same data
            resp = await ac.get(f"{base}/members")
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["is_member"] is True
            assert data["member_count"] == 1
            assert data["members"][0]["first_name"] == alice.first_name

            # join is idempotent
            resp = await ac.post(f"{base}/join")
            assert resp.status_code == 200, resp.text
            assert resp.json()["member_count"] == 1
    finally:
        _clear_overrides()

    # ---- bob joins ----
    _override_auth(bob, db)
    try:
        async with await _client() as ac:
            resp = await ac.post(f"{base}/join")
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["is_member"] is True
            assert data["member_count"] == 2
    finally:
        _clear_overrides()

    # ---- alice sees both ----
    _override_auth(alice, db)
    try:
        async with await _client() as ac:
            resp = await ac.get(f"{base}/members")
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["is_member"] is True
            assert data["member_count"] == 2
            assert {m["user_id"] for m in data["members"]} == {alice.id, bob.id}
            # Only first names — no last name, no email
            for m in data["members"]:
                assert "last_name" not in m
                assert "email" not in m
    finally:
        _clear_overrides()

    # ---- bob leaves ----
    _override_auth(bob, db)
    try:
        async with await _client() as ac:
            resp = await ac.post(f"{base}/leave")
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["is_member"] is False
            assert data["member_count"] == 1
    finally:
        _clear_overrides()

    # ---- alice sees only self ----
    _override_auth(alice, db)
    try:
        async with await _client() as ac:
            resp = await ac.get(f"{base}/members")
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["member_count"] == 1
            assert {m["user_id"] for m in data["members"]} == {alice.id}
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_discussion_requires_membership(db, path, alice, bob):
    """alice (non-member) cannot read or post the discussion;
    bob (member) can do both."""
    base = f"/api/v1/learning-paths/{path.id}/cohort"

    # bob joins
    _override_auth(bob, db)
    try:
        async with await _client() as ac:
            assert (await ac.post(f"{base}/join")).status_code == 200
    finally:
        _clear_overrides()

    # alice (non-member) is rejected on read AND write
    _override_auth(alice, db)
    try:
        async with await _client() as ac:
            resp = await ac.get(f"{base}/discussion")
            assert resp.status_code == 403, resp.text
            resp = await ac.post(f"{base}/discussion", json={"body": "hi"})
            assert resp.status_code == 403, resp.text
    finally:
        _clear_overrides()

    # bob (member) can post and read
    _override_auth(bob, db)
    try:
        async with await _client() as ac:
            resp = await ac.post(f"{base}/discussion", json={"body": "hello cohort"})
            assert resp.status_code == 201, resp.text
            post = resp.json()
            assert post["body"] == "hello cohort"
            assert post["author_display_name"] == bob.first_name

            resp = await ac.get(f"{base}/discussion")
            assert resp.status_code == 200, resp.text
            posts = resp.json()
            assert len(posts) == 1
            assert posts[0]["body"] == "hello cohort"
    finally:
        _clear_overrides()
