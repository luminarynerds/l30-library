# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Duplicate-lesson endpoint tests (E1).

Verifies POST /api/v1/learning/admin/lessons/{id}/duplicate:
  * Returns 201 with a new lesson id distinct from the original.
  * Copies all content fields and appends at the next sort_order.
  * Title gets " (copy)" appended.
  * Quiz questions are copied with a new lesson_id; original questions untouched.
  * 404 when the source lesson does not exist.
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
    QuizQuestion,
)


@pytest.fixture
def admin_client(client, test_admin):
    app.dependency_overrides[get_current_user] = lambda: test_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


async def _seed_lesson(test_db, title="Intro", sort_order=0) -> tuple[Module, Lesson]:
    course = Course(
        title="Dup test course",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        access_level="patron",
    )
    test_db.add(course)
    await test_db.flush()
    module = Module(course_id=course.id, title="m0", sort_order=0)
    test_db.add(module)
    await test_db.flush()
    lesson = Lesson(
        module_id=module.id,
        title=title,
        lesson_type="article",
        content={"body": "<p>hello</p>"},
        estimated_minutes=10,
        sensory_notes="None",
        xp_reward=5,
        sort_order=sort_order,
        summary="A summary",
    )
    test_db.add(lesson)
    await test_db.commit()
    await test_db.refresh(lesson)
    return module, lesson


async def test_duplicate_returns_201_new_id(admin_client, test_db):
    _, lesson = await _seed_lesson(test_db)
    resp = await admin_client.post(
        f"/api/v1/learning/admin/lessons/{lesson.id}/duplicate"
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["id"] != lesson.id


async def test_duplicate_copies_fields(admin_client, test_db):
    _, lesson = await _seed_lesson(test_db, title="Source Lesson", sort_order=0)
    resp = await admin_client.post(
        f"/api/v1/learning/admin/lessons/{lesson.id}/duplicate"
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Source Lesson (copy)"
    assert body["lesson_type"] == "article"
    assert body["content"] == {"body": "<p>hello</p>"}
    assert body["estimated_minutes"] == 10
    assert body["module_id"] == lesson.module_id
    # copy appended after original
    assert body["sort_order"] == lesson.sort_order + 1


async def test_duplicate_copies_quiz_questions(admin_client, test_db):
    _, lesson = await _seed_lesson(test_db)
    # Add 2 quiz questions to original
    q1 = QuizQuestion(
        lesson_id=lesson.id,
        question_text="What is 1+1?",
        question_type="multiple_choice",
        options=[{"text": "2", "is_correct": True}, {"text": "3", "is_correct": False}],
        explanation="Basic arithmetic",
        sort_order=0,
    )
    q2 = QuizQuestion(
        lesson_id=lesson.id,
        question_text="True or false?",
        question_type="true_false",
        options=None,
        explanation=None,
        sort_order=1,
    )
    test_db.add(q1)
    test_db.add(q2)
    await test_db.commit()

    resp = await admin_client.post(
        f"/api/v1/learning/admin/lessons/{lesson.id}/duplicate"
    )
    assert resp.status_code == 201
    copy_id = resp.json()["id"]

    # Verify copy has 2 questions with new lesson_id
    from sqlalchemy import select as sa_select
    result = await test_db.execute(
        sa_select(QuizQuestion).where(QuizQuestion.lesson_id == copy_id)
    )
    copy_qs = result.scalars().all()
    assert len(copy_qs) == 2
    texts = {q.question_text for q in copy_qs}
    assert "What is 1+1?" in texts
    assert "True or false?" in texts

    # Original still has its own 2 questions
    result2 = await test_db.execute(
        sa_select(QuizQuestion).where(QuizQuestion.lesson_id == lesson.id)
    )
    orig_qs = result2.scalars().all()
    assert len(orig_qs) == 2


async def test_duplicate_404_missing_lesson(admin_client):
    resp = await admin_client.post(
        "/api/v1/learning/admin/lessons/999999/duplicate"
    )
    assert resp.status_code == 404
