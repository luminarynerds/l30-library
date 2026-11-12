# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Stub-lesson sweep service tests (Task 5 / W1-B).

Verifies the candidate filter + the email-cap-aware perform_sweep contract:
  * Old empty lessons -> candidates; new empty / old-with-title /
    old-with-body -> NOT candidates.
  * Email cap exhausted -> sweep defers, nothing deleted, breadcrumb
    semantics (status='deferred_email_cap').
  * Cap has room -> sweep proceeds, lesson deleted, recipients computed.
  * Orphan course (NULL created_by_id) -> no email, sweep still runs.
  * No candidates -> noop.

Async fixture pattern (test_db, test_admin) follows the existing test
suite. ``email_cap_remaining`` and ``send_pre_sweep_emails`` are async,
so monkeypatches return coroutines.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.learning import (
    Course,
    CourseLifecycleStage,
    Lesson,
    Module,
)
from app.models.user import User, UserRole
from app.services.lesson_sweep_service import (
    SweepResult,
    find_sweep_candidates,
    perform_sweep,
)


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────


async def _make_user(test_db, email: str = "creator@example.com") -> User:
    user = User(
        email=email,
        password_hash="x",
        first_name="Creator",
        last_name="User",
        role=UserRole.ADMIN,
    )
    test_db.add(user)
    await test_db.flush()
    return user


async def _make_course(
    test_db, *, creator_id: int | None = None, title: str = "course"
) -> Course:
    course = Course(
        title=title,
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        access_level="patron",
        created_by_id=creator_id,
    )
    test_db.add(course)
    await test_db.flush()
    return course


async def _make_module(test_db, course_id: int) -> Module:
    module = Module(course_id=course_id, title="m0", sort_order=0)
    test_db.add(module)
    await test_db.flush()
    return module


async def _make_lesson(
    test_db,
    module_id: int,
    *,
    title: str = "",
    body: str = "",
    age_hours: float = 0.0,
) -> Lesson:
    lesson = Lesson(
        module_id=module_id,
        title=title,
        lesson_type="article",
        content={"body": body},
        sort_order=0,
    )
    test_db.add(lesson)
    await test_db.commit()
    await test_db.refresh(lesson)
    if age_hours > 0:
        # server_default fires on INSERT; back-date the row for ageing tests.
        lesson.created_at = datetime.now(timezone.utc) - timedelta(
            hours=age_hours
        )
        await test_db.commit()
        await test_db.refresh(lesson)
    return lesson


def _async_return(value):
    """Build an async monkeypatch replacement that returns `value`."""

    async def _f(*args, **kwargs):
        return value

    return _f


# ──────────────────────────────────────────────────────────────────────────
# 1) Candidate filter
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_find_candidates_includes_old_empty_lessons(test_db):
    """Old empty -> candidate. New empty / old-with-title / old-with-body -> NOT."""
    user = await _make_user(test_db)
    course = await _make_course(test_db, creator_id=user.id)
    module = await _make_module(test_db, course.id)

    old_empty = await _make_lesson(
        test_db, module.id, title="", body="", age_hours=25
    )
    new_empty = await _make_lesson(
        test_db, module.id, title="", body="", age_hours=2
    )
    old_with_title = await _make_lesson(
        test_db, module.id, title="Real", body="", age_hours=25
    )
    old_with_body = await _make_lesson(
        test_db, module.id, title="", body="content", age_hours=25
    )

    candidates = await find_sweep_candidates(test_db)
    ids = {l.id for l in candidates}
    assert old_empty.id in ids
    assert new_empty.id not in ids
    assert old_with_title.id not in ids
    assert old_with_body.id not in ids


# ──────────────────────────────────────────────────────────────────────────
# 2) Cap exhausted -> defer, nothing deleted
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_perform_sweep_defers_when_email_cap_reached(
    test_db, monkeypatch
):
    user = await _make_user(test_db, "defer@example.com")
    course = await _make_course(test_db, creator_id=user.id, title="defer")
    module = await _make_module(test_db, course.id)
    lesson = await _make_lesson(
        test_db, module.id, title="", body="", age_hours=25
    )

    monkeypatch.setattr(
        "app.services.lesson_sweep_service.email_cap_remaining",
        _async_return(0),
    )
    sent: list[dict] = []

    async def _record_send(recipients):
        sent.extend(recipients)

    monkeypatch.setattr(
        "app.services.lesson_sweep_service.send_pre_sweep_emails",
        _record_send,
    )

    result = await perform_sweep(test_db)
    assert isinstance(result, SweepResult)
    assert result.status == "deferred_email_cap"
    assert result.deleted_count == 0
    assert result.deferred_until is not None
    # No emails sent during a defer.
    assert sent == []
    # Lesson still present.
    assert (await test_db.get(Lesson, lesson.id)) is not None


# ──────────────────────────────────────────────────────────────────────────
# 3) Cap has room -> sweep proceeds
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_perform_sweep_runs_when_cap_has_room(test_db, monkeypatch):
    user = await _make_user(test_db, "runner@example.com")
    course = await _make_course(test_db, creator_id=user.id, title="run")
    module = await _make_module(test_db, course.id)
    lesson = await _make_lesson(
        test_db, module.id, title="", body="", age_hours=25
    )

    monkeypatch.setattr(
        "app.services.lesson_sweep_service.email_cap_remaining",
        _async_return(50),
    )
    sent: list[dict] = []

    async def _record_send(recipients):
        sent.extend(recipients)

    monkeypatch.setattr(
        "app.services.lesson_sweep_service.send_pre_sweep_emails",
        _record_send,
    )

    result = await perform_sweep(test_db)
    assert result.status == "ok"
    assert result.deleted_count == 1
    # Lesson gone.
    assert (await test_db.get(Lesson, lesson.id)) is None
    # Exactly one recipient (the creator).
    assert len(sent) == 1
    assert sent[0]["user_id"] == user.id
    assert sent[0]["email"] == "runner@example.com"


# ──────────────────────────────────────────────────────────────────────────
# 4) Orphan course (NULL created_by_id) -> no email, sweep still runs
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_perform_sweep_skips_email_for_orphan_course_but_still_sweeps(
    test_db, monkeypatch
):
    course = await _make_course(test_db, creator_id=None, title="historical")
    module = await _make_module(test_db, course.id)
    lesson = await _make_lesson(
        test_db, module.id, title="", body="", age_hours=25
    )

    monkeypatch.setattr(
        "app.services.lesson_sweep_service.email_cap_remaining",
        _async_return(50),
    )
    sent: list[dict] = []

    async def _record_send(recipients):
        sent.extend(recipients)

    monkeypatch.setattr(
        "app.services.lesson_sweep_service.send_pre_sweep_emails",
        _record_send,
    )

    result = await perform_sweep(test_db)
    assert result.status == "ok"
    assert result.deleted_count == 1
    assert (await test_db.get(Lesson, lesson.id)) is None
    # No email recipients computed for orphan creator.
    assert sent == []


# ──────────────────────────────────────────────────────────────────────────
# 5) No candidates -> noop
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_perform_sweep_noop_when_no_candidates(test_db):
    result = await perform_sweep(test_db)
    assert result.status == "noop"
    assert result.deleted_count == 0
