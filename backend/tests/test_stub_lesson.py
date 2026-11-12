# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Stub-lesson endpoint tests (Task 5 / W1-B).

Verifies POST /api/v1/learning/admin/modules/{id}/lessons/stub:
  * Creates a minimal empty lesson with lesson_type='article' and
    content={"body": ""}.
  * Appends at the next available sort_order slot.
  * 404s when the module does not exist.

Async fixture pattern (test_db, test_admin, admin_client) follows
tests/test_quiz_question_endpoints.py.
"""
from __future__ import annotations

import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.learning import (
    Course,
    CourseLifecycleStage,
    Lesson,
    Module,
)


# ──────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────


@pytest.fixture
def admin_client(client, test_admin):
    """Client where get_current_user resolves to an admin user."""
    app.dependency_overrides[get_current_user] = lambda: test_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


async def _seed_module(test_db) -> Module:
    course = Course(
        title="Stub-lesson test course",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        access_level="patron",
    )
    test_db.add(course)
    await test_db.flush()
    module = Module(course_id=course.id, title="m0", sort_order=0)
    test_db.add(module)
    await test_db.commit()
    await test_db.refresh(module)
    return module


async def _seed_module_with_n_lessons(test_db, n: int) -> Module:
    module = await _seed_module(test_db)
    for i in range(n):
        test_db.add(
            Lesson(
                module_id=module.id,
                title=f"existing-{i}",
                lesson_type="article",
                content={"body": "some body"},
                sort_order=i,
            )
        )
    await test_db.commit()
    return module


# ──────────────────────────────────────────────────────────────────────────
# 1) POST creates a minimal empty lesson row
# ──────────────────────────────────────────────────────────────────────────


async def test_post_stub_lesson_creates_minimal_row(admin_client, test_db):
    module = await _seed_module(test_db)
    resp = await admin_client.post(
        f"/api/v1/learning/admin/modules/{module.id}/lessons/stub"
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == ""
    assert body["lesson_type"] == "article"
    assert body["content"] == {"body": ""}
    assert body["module_id"] == module.id
    assert isinstance(body["sort_order"], int)


# ──────────────────────────────────────────────────────────────────────────
# 2) Stub appends at next sort_order slot
# ──────────────────────────────────────────────────────────────────────────


async def test_post_stub_assigns_sort_order_after_existing(
    admin_client, test_db
):
    module = await _seed_module_with_n_lessons(test_db, 2)
    resp = await admin_client.post(
        f"/api/v1/learning/admin/modules/{module.id}/lessons/stub"
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["sort_order"] == 2  # existing 0,1 -> stub gets 2


async def test_post_stub_first_lesson_sort_order_is_zero(
    admin_client, test_db
):
    """When the module has no lessons yet, the stub takes sort_order=0."""
    module = await _seed_module(test_db)
    resp = await admin_client.post(
        f"/api/v1/learning/admin/modules/{module.id}/lessons/stub"
    )
    assert resp.status_code == 201
    assert resp.json()["sort_order"] == 0


# ──────────────────────────────────────────────────────────────────────────
# 3) Missing module -> 404
# ──────────────────────────────────────────────────────────────────────────


async def test_post_stub_404_when_module_missing(admin_client):
    resp = await admin_client.post(
        "/api/v1/learning/admin/modules/999999/lessons/stub"
    )
    assert resp.status_code == 404
