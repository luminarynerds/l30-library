# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the admin course-clone endpoint:

    POST /api/v1/learning/admin/courses/{course_id}/clone

What we verify:
  1. Happy-path clone preserves module + lesson counts and lesson content,
     and the new course is a draft (is_published=False).
  2. `include_unpublished_lessons=false` is accepted but doesn't drop
     lessons (documented no-op until lessons grow a publish flag).
  3. Duplicate title returns 422.
  4. Failure mid-clone rolls back - no orphan modules/lessons or course.
  5. A non-admin caller (patron) is 403'd.

Auth pattern: we override `get_current_user` in FastAPI's dep map so the
endpoint sees our fixture user, bypassing the JWT/Redis token cache that
otherwise fail-secures as "token revoked" in test envs.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.learning import Course, CourseLifecycleStage, Lesson, Module


# --------------------------------------------------------------------------
# Helpers / fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def admin_client(client, test_admin):
    """Client where get_current_user resolves to an admin user."""
    app.dependency_overrides[get_current_user] = lambda: test_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def patron_client(client, test_patron):
    """Client where get_current_user resolves to a patron user."""
    app.dependency_overrides[get_current_user] = lambda: test_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


async def _seed_course(
    test_db,
    *,
    title: str,
    n_modules: int = 2,
    lessons_per_module: int = 2,
    is_published: bool = True,
) -> Course:
    """Build a Course with `n_modules` modules, each with `lessons_per_module` lessons."""
    course = Course(
        title=title,
        description=f"{title} description",
        thumbnail_url="https://example.test/thumb.png",
        access_level="staff",
        difficulty="intermediate",
        estimated_minutes=120,
        lifecycle_stage=(
            CourseLifecycleStage.PUBLISHED
            if is_published
            else CourseLifecycleStage.DRAFT
        ),
        quiz_passing_threshold=80,
        xp_reward=250,
        sensory_warning="Includes timed quiz",
        duration_days=30,
    )
    test_db.add(course)
    await test_db.flush()

    for m_idx in range(n_modules):
        module = Module(
            course_id=course.id,
            title=f"{title} - module {m_idx}",
            description=f"module {m_idx} desc",
            sort_order=m_idx,
        )
        test_db.add(module)
        await test_db.flush()
        for l_idx in range(lessons_per_module):
            lesson = Lesson(
                module_id=module.id,
                title=f"m{m_idx} lesson {l_idx}",
                lesson_type="article",
                content={"body": f"content for m{m_idx} l{l_idx}"},
                estimated_minutes=10,
                xp_reward=20,
                sort_order=l_idx,
                summary=f"summary m{m_idx} l{l_idx}",
            )
            test_db.add(lesson)

    await test_db.commit()
    await test_db.refresh(course)
    return course


# --------------------------------------------------------------------------
# 1) Happy path
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_preserves_module_lesson_count_and_starts_as_draft(
    admin_client, test_db
):
    """A successful clone copies all modules + lessons and lands as a draft."""
    source = await _seed_course(
        test_db, title="Summer Reading 2025", n_modules=3, lessons_per_module=2
    )
    source_id = source.id

    response = await admin_client.post(
        f"/api/v1/learning/admin/courses/{source_id}/clone",
        json={"new_title": "Summer Reading 2026"},
    )
    assert response.status_code == 201, response.text
    body = response.json()

    # Response shape matches CourseListItem
    assert body["title"] == "Summer Reading 2026"
    assert body["is_published"] is False
    assert body["description"] == source.description
    assert body["module_count"] == 3
    assert body["lesson_count"] == 6
    assert body["id"] != source_id

    # Source course untouched - same id, same module/lesson rows
    source_after = (
        await test_db.execute(select(Course).where(Course.id == source_id))
    ).scalar_one()
    assert source_after.title == "Summer Reading 2025"
    assert source_after.lifecycle_stage == CourseLifecycleStage.PUBLISHED

    src_modules = (
        await test_db.execute(
            select(Module).where(Module.course_id == source_id).order_by(Module.sort_order)
        )
    ).scalars().all()
    new_modules = (
        await test_db.execute(
            select(Module).where(Module.course_id == body["id"]).order_by(Module.sort_order)
        )
    ).scalars().all()

    assert len(src_modules) == len(new_modules) == 3
    # Module IDs are distinct (deep copy, not alias)
    assert {m.id for m in src_modules}.isdisjoint({m.id for m in new_modules})

    # Lesson content matches per-module, IDs distinct
    for src_m, new_m in zip(src_modules, new_modules):
        assert src_m.title == new_m.title
        assert src_m.sort_order == new_m.sort_order
        src_lessons = (
            await test_db.execute(
                select(Lesson).where(Lesson.module_id == src_m.id).order_by(Lesson.sort_order)
            )
        ).scalars().all()
        new_lessons = (
            await test_db.execute(
                select(Lesson).where(Lesson.module_id == new_m.id).order_by(Lesson.sort_order)
            )
        ).scalars().all()
        assert len(src_lessons) == len(new_lessons) == 2
        for src_l, new_l in zip(src_lessons, new_lessons):
            assert src_l.id != new_l.id
            assert src_l.title == new_l.title
            assert src_l.content == new_l.content
            assert src_l.lesson_type == new_l.lesson_type
            assert src_l.sort_order == new_l.sort_order


# --------------------------------------------------------------------------
# 2) include_unpublished_lessons=False - currently a no-op (Lesson model
#    has no publish flag). The flag is accepted; all lessons still copy.
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_include_unpublished_lessons_false_is_accepted_and_copies_all(
    admin_client, test_db
):
    source = await _seed_course(
        test_db, title="Civics 101", n_modules=1, lessons_per_module=3
    )

    response = await admin_client.post(
        f"/api/v1/learning/admin/courses/{source.id}/clone",
        json={
            "new_title": "Civics 101 - rerun",
            "include_unpublished_lessons": False,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    # All lessons still cloned because Lesson has no is_published field;
    # the parameter is reserved for future use.
    assert body["module_count"] == 1
    assert body["lesson_count"] == 3


# --------------------------------------------------------------------------
# 3) Duplicate title returns 422
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_title_returns_422(admin_client, test_db):
    source = await _seed_course(test_db, title="Intro to Civic Tech")

    response = await admin_client.post(
        f"/api/v1/learning/admin/courses/{source.id}/clone",
        json={"new_title": "Intro to Civic Tech"},
    )
    assert response.status_code == 422
    body = response.json()
    # Global exception handler wraps HTTPException.detail under error.message.
    message = body.get("error", {}).get("message") or body.get("detail", "")
    assert "already exists" in message.lower(), body


@pytest.mark.asyncio
async def test_short_title_returns_422(admin_client, test_db):
    source = await _seed_course(test_db, title="A Decent Length Title")

    response = await admin_client.post(
        f"/api/v1/learning/admin/courses/{source.id}/clone",
        json={"new_title": "ab"},
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------
# 4) Mid-clone failure rolls back - no orphan course, modules, or lessons
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failure_mid_clone_rolls_back(admin_client, test_db, monkeypatch):
    """If lesson creation explodes partway through, nothing is persisted."""
    source = await _seed_course(
        test_db, title="Will Fail Halfway", n_modules=2, lessons_per_module=2
    )

    courses_before = (
        await test_db.execute(select(Course.id))
    ).scalars().all()
    modules_before = (
        await test_db.execute(select(Module.id))
    ).scalars().all()
    lessons_before = (
        await test_db.execute(select(Lesson.id))
    ).scalars().all()

    # Force Lesson() construction to raise on the third call. The first
    # module copies fine, the first lesson of module 2 trips the wire.
    original_init = Lesson.__init__
    call_count = {"n": 0}

    def exploding_init(self, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 3:
            raise RuntimeError("simulated lesson copy failure")
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(Lesson, "__init__", exploding_init)

    response = await admin_client.post(
        f"/api/v1/learning/admin/courses/{source.id}/clone",
        json={"new_title": "Will Fail Clone"},
    )
    # Server-side exception -> 500
    assert response.status_code == 500

    # Restore for the assertions below
    monkeypatch.setattr(Lesson, "__init__", original_init)

    courses_after = (
        await test_db.execute(select(Course.id))
    ).scalars().all()
    modules_after = (
        await test_db.execute(select(Module.id))
    ).scalars().all()
    lessons_after = (
        await test_db.execute(select(Lesson.id))
    ).scalars().all()

    # No new rows persisted from the failed clone.
    assert set(courses_after) == set(courses_before)
    assert set(modules_after) == set(modules_before)
    assert set(lessons_after) == set(lessons_before)


# --------------------------------------------------------------------------
# 5) Non-admin gets 403
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patron_gets_403(patron_client, test_db):
    source = await _seed_course(test_db, title="Patron Cant Clone")

    response = await patron_client.post(
        f"/api/v1/learning/admin/courses/{source.id}/clone",
        json={"new_title": "Patron Cant Clone Copy"},
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------
# 6) Source course not found -> 404
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_source_returns_404(admin_client):
    response = await admin_client.post(
        "/api/v1/learning/admin/courses/999999/clone",
        json={"new_title": "Never Born Clone"},
    )
    assert response.status_code == 404
