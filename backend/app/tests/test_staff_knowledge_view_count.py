# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for staff-knowledge detail endpoints that bump view_count.

The GET-detail endpoints increment view_count and commit before returning the
ORM object. DecisionTree/VideoTutorial.updated_at carries onupdate=func.now(),
so the commit expires it server-side; serializing the response_model then reads
updated_at synchronously and raised MissingGreenlet -> 500. The endpoints must
refresh the instance after commit. See get_decision_tree / get_video_tutorial.
"""
from __future__ import annotations

import pytest

from app.api.v1.dependencies import require_staff
from app.api.v1.auth.helpers import get_current_user
from app.core.database import get_db
from app.main import app
from sqlalchemy import text

from app.models.knowledge_base import DecisionTree, VideoTutorial
from app.models.user import User, UserRole


@pytest.fixture
async def staff(db):
    user = User(
        email="kb-staff@example.com",
        first_name="KB",
        last_name="Staff",
        password_hash="x",
        role=UserRole.STAFF,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def decision_tree(db, staff):
    tree = DecisionTree(
        title="Patron Behavior Issue",
        description="What to do when a patron is disruptive.",
        category="Conduct",
        tree_data={
            "root_node": "is_threatening",
            "nodes": {
                "is_threatening": {
                    "id": "is_threatening",
                    "question": "Is the patron threatening?",
                    "yes_next": {"action": "call", "result": "Call security."},
                    "no_next": {"action": "warn", "result": "Issue a warning."},
                }
            },
        },
        is_published=True,
        created_by_id=staff.id,
    )
    db.add(tree)
    await db.commit()
    await db.refresh(tree)
    return tree


@pytest.fixture
async def video_tutorial(db, staff):
    video = VideoTutorial(
        title="Using the self-checkout",
        description="A short walkthrough.",
        category="Circulation",
        video_url="https://example.com/v.mp4",
        is_published=True,
        created_by_id=staff.id,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video


def _override_auth(staff_user, db):
    async def _db():
        yield db

    async def _staff():
        return staff_user

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _staff
    app.dependency_overrides[require_staff] = _staff
    app.state.setup_complete = True


def _clear_overrides():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_staff, None)


@pytest.mark.asyncio
async def test_get_decision_tree_detail_serializes_after_view_count_bump(db, staff, decision_tree):
    """GET a single decision tree returns 200 (was 500: MissingGreenlet on updated_at)."""
    from httpx import AsyncClient, ASGITransport

    _override_auth(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            resp = await ac.get(f"/api/v1/staff-knowledge/decision-trees/{decision_tree.id}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == decision_tree.id
        assert body["tree_data"]["root_node"] == "is_threatening"
        assert body["view_count"] == 1
        assert body["updated_at"]
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_get_video_tutorial_detail_serializes_after_view_count_bump(db, staff, video_tutorial):
    """GET a single video tutorial returns 200 (same onupdate/refresh class of bug)."""
    from httpx import AsyncClient, ASGITransport

    _override_auth(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            resp = await ac.get(f"/api/v1/staff-knowledge/video-tutorials/{video_tutorial.id}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == video_tutorial.id
        assert body["view_count"] == 1
        assert body["updated_at"]
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_get_video_tutorial_with_null_related_article_ids(db, staff):
    """A row whose related_article_ids is NULL (seeded past the ORM default)
    must still serialize: the response schema coerces None -> []."""
    from httpx import AsyncClient, ASGITransport

    # Raw INSERT so related_article_ids stays NULL (the ORM default=[] would
    # otherwise fill it). created_at/updated_at come from server_default.
    row = (await db.execute(
        text(
            "INSERT INTO video_tutorials "
            "(title, category, video_url, related_article_ids, is_published, view_count, created_by_id) "
            "VALUES (:t, :c, :u, NULL, true, 0, :cb) RETURNING id"
        ),
        {"t": "Legacy clip", "c": "Circulation", "u": "https://example.com/legacy.mp4", "cb": staff.id},
    )).scalar_one()
    await db.commit()

    _override_auth(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            resp = await ac.get(f"/api/v1/staff-knowledge/video-tutorials/{row}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["related_article_ids"] == []
    finally:
        _clear_overrides()
