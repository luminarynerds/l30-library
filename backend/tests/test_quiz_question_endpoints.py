# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Quiz-question endpoint tests (Task 3 / W1-C).

These verify lesson-scoped POST/PUT/DELETE/PATCH-reorder semantics, including
the quiz_attempts guards: 409 on DELETE if attempts exist, warn-log on PUT
options reorder if attempts exist (don't block - instructors fix typos).

Async fixture pattern (test_db, test_admin) follows
tests/test_courses_created_by_id.py; ``asyncio_mode = "auto"`` in
pyproject.toml means we don't need @pytest.mark.asyncio decorators.

Auth pattern: override ``get_current_user`` in FastAPI's dep map so the
endpoint sees our fixture user, bypassing the JWT/Redis token cache that
otherwise fail-secures as "token revoked" in test envs.
"""
from __future__ import annotations

import logging

import pytest
from sqlalchemy import select

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.learning import (
    Course,
    CourseLifecycleStage,
    Lesson,
    Module,
    QuizAttempt,
    QuizQuestion,
)
from app.models.user import User


# ──────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────


@pytest.fixture
def admin_client(client, test_admin):
    """Client where get_current_user resolves to an admin user."""
    app.dependency_overrides[get_current_user] = lambda: test_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


async def _seed_lesson(test_db, *, lesson_type: str = "quiz") -> Lesson:
    course = Course(
        title="QQ test course",
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
        title="Quiz lesson",
        lesson_type=lesson_type,
        content={"body": "irrelevant"},
        sort_order=0,
    )
    test_db.add(lesson)
    await test_db.commit()
    await test_db.refresh(lesson)
    return lesson


async def _seed_question(
    test_db,
    lesson: Lesson,
    *,
    text: str = "What?",
    options=None,
    sort_order: int = 0,
) -> QuizQuestion:
    if options is None:
        options = [
            {"text": "A", "is_correct": True},
            {"text": "B", "is_correct": False},
        ]
    q = QuizQuestion(
        lesson_id=lesson.id,
        question_text=text,
        question_type="multiple_choice",
        options=options,
        explanation="",
        sort_order=sort_order,
    )
    test_db.add(q)
    await test_db.commit()
    await test_db.refresh(q)
    return q


async def _seed_attempt(test_db, lesson: Lesson, user: User) -> QuizAttempt:
    attempt = QuizAttempt(
        user_id=user.id,
        lesson_id=lesson.id,
        score=0,
        passed=False,
        answers=[],
    )
    test_db.add(attempt)
    await test_db.commit()
    await test_db.refresh(attempt)
    return attempt


# ──────────────────────────────────────────────────────────────────────────
# 1) POST creates a question
# ──────────────────────────────────────────────────────────────────────────


async def test_post_question_creates_row(admin_client, test_db):
    lesson = await _seed_lesson(test_db)
    body = {
        "question_text": "What is 2+2?",
        "question_type": "multiple_choice",
        "options": [
            {"text": "3", "is_correct": False},
            {"text": "4", "is_correct": True},
        ],
        "explanation": "Basic math",
        "sort_order": 0,
    }
    resp = await admin_client.post(
        f"/api/v1/learning/admin/lessons/{lesson.id}/quiz-questions",
        json=body,
    )
    assert resp.status_code == 201, resp.text
    payload = resp.json()
    assert payload["id"] > 0
    assert payload["lesson_id"] == lesson.id
    assert payload["question_text"] == "What is 2+2?"
    assert len(payload["options"]) == 2
    assert payload["options"][1]["is_correct"] is True

    # DB confirms persistence.
    db_q = (
        await test_db.execute(
            select(QuizQuestion).where(QuizQuestion.id == payload["id"])
        )
    ).scalar_one()
    assert db_q.lesson_id == lesson.id
    assert db_q.question_text == "What is 2+2?"


# ──────────────────────────────────────────────────────────────────────────
# 2) DELETE returns 409 when quiz_attempts exist for the lesson
# ──────────────────────────────────────────────────────────────────────────


async def test_delete_question_409_when_attempts_exist(
    admin_client, test_db, test_admin
):
    lesson = await _seed_lesson(test_db)
    q = await _seed_question(test_db, lesson)
    await _seed_attempt(test_db, lesson, test_admin)

    resp = await admin_client.delete(
        f"/api/v1/learning/admin/lessons/{lesson.id}/quiz-questions/{q.id}"
    )
    assert resp.status_code == 409, resp.text
    # Global handler reshapes HTTPException → {"error": {"message": ...}}.
    body = resp.json()
    message = body.get("error", {}).get("message") or body.get("detail", "")
    assert "quiz_attempts" in message, body
    # The question should still exist.
    still_there = (
        await test_db.execute(select(QuizQuestion).where(QuizQuestion.id == q.id))
    ).scalar_one_or_none()
    assert still_there is not None


# ──────────────────────────────────────────────────────────────────────────
# 3) PUT options reorder warn-logs but succeeds when attempts exist
# ──────────────────────────────────────────────────────────────────────────


async def test_put_options_reorder_with_attempts_warns_but_succeeds(
    admin_client, test_db, test_admin, caplog
):
    lesson = await _seed_lesson(test_db)
    original = [
        {"text": "A", "is_correct": True},
        {"text": "B", "is_correct": False},
    ]
    q = await _seed_question(test_db, lesson, options=original)
    await _seed_attempt(test_db, lesson, test_admin)

    reversed_opts = list(reversed(original))
    body = {
        "question_text": q.question_text,
        "question_type": q.question_type,
        "options": reversed_opts,
        "explanation": q.explanation or "",
        "sort_order": q.sort_order,
    }

    # L30 configures a json-handler on the module logger with propagate=False
    # (see app/core/logging_config.py); caplog's root handler never sees the
    # record. Attach caplog's handler directly to the module logger so warning
    # records flow into caplog.records.
    target_logger = logging.getLogger("app.api.v1.learning_quizzes")
    prior_level = target_logger.level
    target_logger.setLevel(logging.WARNING)
    target_logger.addHandler(caplog.handler)
    try:
        resp = await admin_client.put(
            f"/api/v1/learning/admin/lessons/{lesson.id}/quiz-questions/{q.id}",
            json=body,
        )
    finally:
        target_logger.removeHandler(caplog.handler)
        target_logger.setLevel(prior_level)

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["options"][0]["text"] == "B"

    # Warn log fired, mentions both lesson_id and question_id.
    warnings = [
        r for r in caplog.records
        if r.name == "app.api.v1.learning_quizzes" and r.levelno >= logging.WARNING
    ]
    assert warnings, "expected a warning log on options change with attempts"
    msg = warnings[-1].getMessage()
    assert str(lesson.id) in msg
    assert str(q.id) in msg


# ──────────────────────────────────────────────────────────────────────────
# 4) PATCH /reorder updates sort_order in one transaction
# ──────────────────────────────────────────────────────────────────────────


async def test_reorder_bulk_updates_sort_order(admin_client, test_db):
    lesson = await _seed_lesson(test_db)
    q1 = await _seed_question(test_db, lesson, text="Q1", sort_order=0)
    q2 = await _seed_question(test_db, lesson, text="Q2", sort_order=1)
    q3 = await _seed_question(test_db, lesson, text="Q3", sort_order=2)

    # Stash primitive ids before expire_all() so we don't trip lazy-load
    # on an expired attribute (async session would raise MissingGreenlet).
    lesson_id = lesson.id
    q1_id, q2_id, q3_id = q1.id, q2.id, q3.id

    payload = [
        {"question_id": q3_id, "sort_order": 0},
        {"question_id": q1_id, "sort_order": 1},
        {"question_id": q2_id, "sort_order": 2},
    ]
    resp = await admin_client.patch(
        f"/api/v1/learning/admin/lessons/{lesson_id}/quiz-questions/reorder",
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["reordered"] == 3

    test_db.expire_all()
    rows = (
        await test_db.execute(
            select(QuizQuestion).where(QuizQuestion.lesson_id == lesson_id)
        )
    ).scalars().all()
    by_id = {r.id: r for r in rows}
    assert by_id[q3_id].sort_order == 0
    assert by_id[q1_id].sort_order == 1
    assert by_id[q2_id].sort_order == 2


# ──────────────────────────────────────────────────────────────────────────
# 5) POST 404 if lesson_id doesn't exist
# ──────────────────────────────────────────────────────────────────────────


async def test_post_question_404_when_lesson_missing(admin_client):
    body = {
        "question_text": "ghost lesson?",
        "question_type": "multiple_choice",
        "options": [{"text": "A", "is_correct": True}],
        "explanation": "",
        "sort_order": 0,
    }
    resp = await admin_client.post(
        "/api/v1/learning/admin/lessons/999999/quiz-questions",
        json=body,
    )
    assert resp.status_code == 404, resp.text


# ──────────────────────────────────────────────────────────────────────────
# 6) DELETE succeeds (204) when no attempts exist
# ──────────────────────────────────────────────────────────────────────────


async def test_delete_question_204_when_no_attempts(admin_client, test_db):
    lesson = await _seed_lesson(test_db)
    q = await _seed_question(test_db, lesson)

    resp = await admin_client.delete(
        f"/api/v1/learning/admin/lessons/{lesson.id}/quiz-questions/{q.id}"
    )
    assert resp.status_code == 204, resp.text

    test_db.expire_all()
    gone = (
        await test_db.execute(select(QuizQuestion).where(QuizQuestion.id == q.id))
    ).scalar_one_or_none()
    assert gone is None


# ──────────────────────────────────────────────────────────────────────────
# 7) POST returns 422 on unknown question_type (W1-C tightening)
# ──────────────────────────────────────────────────────────────────────────


async def test_post_question_422_on_invalid_question_type(admin_client, test_db):
    """Admin write endpoints reject unknown question_type values (W1-C tightening)."""
    lesson = await _seed_lesson(test_db)
    resp = await admin_client.post(
        f"/api/v1/learning/admin/lessons/{lesson.id}/quiz-questions",
        json={
            "question_text": "Q?",
            "question_type": "nonsense",
            "options": [{"text": "A", "is_correct": True}],
            "explanation": "",
            "sort_order": 0,
        },
    )
    assert resp.status_code == 422, resp.text
    # Detail surface differs by Pydantic version; just confirm question_type is named.
    assert "question_type" in str(resp.json())
