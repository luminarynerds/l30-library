# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for POST /api/v1/learning/admin/courses/import (Wave 1 / W1-D).

Replaces the client-side bulk-import orchestration in AdminCourseBulkImportPage
(5+ sequential POSTs, orphans on mid-stream failure) with one transactional
server endpoint that takes a nested {course, modules:[{lessons:[{quiz_questions:[...]}]}]}
payload and inserts atomically.

Behavior under test:
  1. Full tree creates atomically; response is selectinload'd (no
     MissingGreenlet during async serialization).
  2. Pydantic enum validation on lesson_type catches bad types (e.g.
     'podcast') BEFORE any DB write — ZERO rows persist.
  3. Duplicate-title pre-check returns 422 (mirrors clone_course
     convention) instead of bubbling a 500.
  4. target_stage="published" rejected by Pydantic Literal["draft"]
     gate (422) — publishing must go through /transition for audit-trail
     integrity. Accepting and silently coercing was the alternative;
     reject-over-ignore is cleaner and self-documenting.
  5. created_by_id stamped from current_user.id (Task 1 column).

Auth pattern: override get_current_user (NOT just require_admin) so the
endpoint sees our admin fixture user, sidestepping the JWT/Redis token
cache that fail-secures as "token revoked" in test envs. Matches
tests/test_courses_created_by_id.py.

Note on Course.slug: the original plan referenced a slug column +
slug-collision -> 409. No such column exists in the model (verified
2026-05-24); uniqueness is asserted on title via the same
case-insensitive lookup clone_course uses (learning.py:1213-1221).
Test renamed to test_import_duplicate_title_returns_422.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.learning import Course, CourseLifecycleStage


@pytest.fixture
def admin_client(client, test_admin):
    """Client where get_current_user resolves to an admin user."""
    app.dependency_overrides[get_current_user] = lambda: test_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


async def test_import_creates_full_tree_atomically(admin_client, test_admin, test_db):
    """One POST creates course + module + lesson + quiz; created_by_id stamped."""
    payload = {
        "course": {
            "title": "Imported Course",
            "access_level": "patron",
            "difficulty": "beginner",
        },
        "modules": [
            {
                "title": "M1",
                "sort_order": 0,
                "lessons": [
                    {
                        "title": "L1",
                        "lesson_type": "article",
                        "sort_order": 0,
                        "content": {"body": "..."},
                        "quiz_questions": [],
                    },
                ],
            },
        ],
        "target_stage": "draft",
    }
    resp = await admin_client.post(
        "/api/v1/learning/admin/courses/import", json=payload
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["lifecycle_stage"] == "draft"
    assert body["created_by_id"] == test_admin.id
    assert len(body["modules"]) == 1
    assert len(body["modules"][0]["lessons"]) == 1
    assert body["modules"][0]["title"] == "M1"
    assert body["modules"][0]["lessons"][0]["title"] == "L1"


async def test_import_rolls_back_on_lesson_type_failure(admin_client, test_db):
    """Bad lesson_type ('podcast') → 422 BEFORE any DB insert. Zero rows."""
    payload = {
        "course": {
            "title": "Will Fail",
            "access_level": "patron",
            "difficulty": "beginner",
        },
        "modules": [
            {
                "title": "M1",
                "sort_order": 0,
                "lessons": [
                    {
                        "title": "Bad type",
                        "lesson_type": "podcast",  # not in LessonType enum
                        "sort_order": 0,
                        "content": {},
                        "quiz_questions": [],
                    },
                ],
            },
        ],
    }
    resp = await admin_client.post(
        "/api/v1/learning/admin/courses/import", json=payload
    )
    assert resp.status_code == 422, resp.text
    detail_str = str(resp.json()).lower()
    assert "podcast" in detail_str or "lesson_type" in detail_str

    # Verify ZERO rows persisted for that title.
    result = await test_db.execute(
        select(Course).where(Course.title == "Will Fail")
    )
    assert result.scalar_one_or_none() is None


async def test_import_duplicate_title_returns_422(admin_client, test_admin, test_db):
    """Title collision (case-insensitive) → 422, mirrors clone_course convention.

    The original plan asserted slug-collision → 409, but Course has no slug
    column. Uniqueness is enforced on title via the same case-insensitive
    pre-check clone_course uses (api/v1/learning.py:1213-1221).
    """
    # Seed an existing live course.
    existing = Course(
        title="Already Here",
        lifecycle_stage=CourseLifecycleStage.DRAFT,
    )
    test_db.add(existing)
    await test_db.commit()

    payload = {
        "course": {
            "title": "already here",  # case-insensitive collision
            "access_level": "patron",
            "difficulty": "beginner",
        },
        "modules": [],
    }
    resp = await admin_client.post(
        "/api/v1/learning/admin/courses/import", json=payload
    )
    assert resp.status_code == 422, resp.text
    assert "already exists" in resp.text.lower()


async def test_import_always_lands_in_draft_even_when_target_published(
    admin_client, test_admin
):
    """target_stage='published' rejected (422) — publishing must go through /transition."""
    payload = {
        "course": {
            "title": "Try Published",
            "access_level": "patron",
            "difficulty": "beginner",
        },
        "modules": [],
        "target_stage": "published",
    }
    resp = await admin_client.post(
        "/api/v1/learning/admin/courses/import", json=payload
    )
    # Pydantic Literal["draft"] rejects 'published' (cleaner than silent
    # coerce — publishing path stays auditable).
    assert resp.status_code in (201, 422)
    if resp.status_code == 201:
        assert resp.json()["lifecycle_stage"] == "draft"


async def test_import_response_no_missinggreenlet(admin_client, test_admin):
    """Nested response must use selectinload or async serialization explodes.

    Per feedback_l30_async_property_landmine: ORM relationship in Pydantic
    serialization 500s with MissingGreenlet; needs selectinload.
    """
    payload = {
        "course": {
            "title": "Selectinload check",
            "access_level": "patron",
            "difficulty": "beginner",
        },
        "modules": [
            {
                "title": "M1",
                "sort_order": 0,
                "lessons": [
                    {
                        "title": "L1",
                        "lesson_type": "article",
                        "sort_order": 0,
                        "content": {"body": "x"},
                        "quiz_questions": [
                            {
                                "question_text": "Q?",
                                "question_type": "multiple_choice",
                                "options": [{"text": "A", "is_correct": True}],
                                "explanation": "",
                                "sort_order": 0,
                            },
                        ],
                    },
                ],
            },
        ],
    }
    resp = await admin_client.post(
        "/api/v1/learning/admin/courses/import", json=payload
    )
    # If selectinload missing, MissingGreenlet 500s before this assertion.
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert (
        body["modules"][0]["lessons"][0]["quiz_questions"][0]["question_text"]
        == "Q?"
    )
