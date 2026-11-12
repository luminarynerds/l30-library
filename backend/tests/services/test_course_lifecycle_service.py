# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for ``app.services.course_lifecycle_service``.

Three-stage lifecycle (draft / published / archived). These tests exercise
the service helpers + audit behavior directly against the test DB.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.learning import (Course, CourseLifecycleStage,
                                 CourseStageTransition, Lesson, Module)
from app.models.user import User, UserRole
from app.services.course_lifecycle_service import (ALLOWED_TRANSITIONS,
                                                   REVIEW_CADENCE,
                                                   EmptyCourseError,
                                                   compute_review_due,
                                                   is_transition_allowed,
                                                   transition_course_stage)

# Note: no module-level ``pytestmark = pytest.mark.asyncio``. The three
# pure-helper tests below are synchronous; only the DB-backed tests are
# marked async individually.


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


async def _make_admin(db, email: str = "admin-lifecycle@example.com") -> User:
    user = User(
        email=email,
        password_hash=hash_password("AdminPass123!"),
        first_name="Life",
        last_name="Cycle",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _make_course(
    db,
    *,
    title: str = "Lifecycle Test Course",
    with_lesson: bool = True,
    stage: CourseLifecycleStage = CourseLifecycleStage.DRAFT,
) -> Course:
    course = Course(
        title=title,
        description="Stage test",
        access_level="patron",
        lifecycle_stage=stage,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)

    if with_lesson:
        module = Module(course_id=course.id, title="M1", sort_order=0)
        db.add(module)
        await db.commit()
        await db.refresh(module)

        lesson = Lesson(
            module_id=module.id,
            title="L1",
            lesson_type="article",
            content={"body": "hello"},
            sort_order=0,
        )
        db.add(lesson)
        await db.commit()

    return course


# ──────────────────────────────────────────────────────────────────────────────
# Pure helpers (no DB)
# ──────────────────────────────────────────────────────────────────────────────


def test_allowed_transitions_table_is_consistent_and_exhaustive():
    """Every stage must have at least one outbound transition, and every
    transition must land in a known stage. Guards against accidentally
    dropping a stage from the table or pointing a transition at a
    typo."""
    stages = set(CourseLifecycleStage)

    # Every stage must appear as a key.
    assert set(ALLOWED_TRANSITIONS.keys()) == stages, (
        "ALLOWED_TRANSITIONS is missing or has extra stage keys"
    )

    for stage, targets in ALLOWED_TRANSITIONS.items():
        assert targets, f"Stage {stage} has no outbound transitions"
        for target in targets:
            assert target in stages, (
                f"Transition {stage} -> {target} lands in unknown stage"
            )
            assert target != stage, (
                f"Self-transition {stage} -> {target} is not meaningful"
            )


def test_is_transition_allowed_matches_three_stage_model():
    # draft <-> published is now a direct, one-step edge (Publish / Unpublish).
    assert is_transition_allowed(
        CourseLifecycleStage.DRAFT, CourseLifecycleStage.PUBLISHED
    )
    assert is_transition_allowed(
        CourseLifecycleStage.PUBLISHED, CourseLifecycleStage.DRAFT
    )
    # archived only comes back out as draft (Restore).
    assert is_transition_allowed(
        CourseLifecycleStage.ARCHIVED, CourseLifecycleStage.DRAFT
    )
    # archived -> published is NOT a legal edge (must restore to draft first).
    assert not is_transition_allowed(
        CourseLifecycleStage.ARCHIVED, CourseLifecycleStage.PUBLISHED
    )
    # self-transitions are never allowed.
    assert not is_transition_allowed(
        CourseLifecycleStage.PUBLISHED, CourseLifecycleStage.PUBLISHED
    )


def test_compute_review_due_uses_cadence():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert compute_review_due(now) == now + REVIEW_CADENCE
    assert REVIEW_CADENCE == timedelta(days=365)


# ──────────────────────────────────────────────────────────────────────────────
# DB-backed transitions
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transition_logs_audit_row(test_db):
    """Each successful transition must insert a CourseStageTransition row
    with from_stage, to_stage, actor_id, note correctly populated."""
    actor = await _make_admin(test_db, email="audit-actor@example.com")
    course = await _make_course(test_db, title="Audit Course")

    await transition_course_stage(
        test_db,
        course,
        CourseLifecycleStage.PUBLISHED,
        actor=actor,
        note="publishing it",
    )
    await test_db.commit()

    rows = (
        await test_db.execute(
            select(CourseStageTransition).where(
                CourseStageTransition.course_id == course.id
            )
        )
    ).scalars().all()

    assert len(rows) == 1
    row = rows[0]
    assert row.from_stage == CourseLifecycleStage.DRAFT
    assert row.to_stage == CourseLifecycleStage.PUBLISHED
    assert row.actor_id == actor.id
    assert row.note == "publishing it"
    assert row.created_at is not None


@pytest.mark.asyncio
async def test_publish_sets_review_due_at(test_db):
    """Transitioning into PUBLISHED must stamp last_reviewed_at,
    last_reviewed_by_id, and review_due_at (= now + 365 days)."""
    actor = await _make_admin(test_db, email="publisher@example.com")
    course = await _make_course(
        test_db,
        title="Publish Course",
        stage=CourseLifecycleStage.DRAFT,
    )

    before = datetime.now(timezone.utc)
    await transition_course_stage(
        test_db,
        course,
        CourseLifecycleStage.PUBLISHED,
        actor=actor,
    )
    await test_db.commit()
    await test_db.refresh(course)

    assert course.lifecycle_stage == CourseLifecycleStage.PUBLISHED
    assert course.last_reviewed_by_id == actor.id
    assert course.last_reviewed_at is not None
    assert course.review_due_at is not None

    # SQLite strips tzinfo on roundtrip even though we declared
    # ``DateTime(timezone=True)``. Normalize both sides to naive UTC so
    # the assertion is portable across Postgres (tz-aware) and SQLite
    # (tz-naive).
    def _naive_utc(dt):
        return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt

    last_reviewed_naive = _naive_utc(course.last_reviewed_at)
    review_due_naive = _naive_utc(course.review_due_at)
    before_naive = _naive_utc(before)

    # last_reviewed_at should be within a few seconds of "before".
    delta = last_reviewed_naive - before_naive
    assert timedelta(seconds=-2) <= delta <= timedelta(seconds=30)

    # review_due_at must be exactly 365 days after last_reviewed_at.
    assert review_due_naive - last_reviewed_naive == REVIEW_CADENCE


@pytest.mark.asyncio
async def test_publish_blocked_when_course_empty(test_db):
    """A course with no lessons cannot be published, even though the
    draft -> published transition itself is allowed."""
    actor = await _make_admin(test_db, email="empty-publisher@example.com")
    course = await _make_course(
        test_db,
        title="Empty Course",
        with_lesson=False,
        stage=CourseLifecycleStage.DRAFT,
    )

    with pytest.raises(EmptyCourseError):
        await transition_course_stage(
            test_db,
            course,
            CourseLifecycleStage.PUBLISHED,
            actor=actor,
        )

    # The flushed change must NOT have landed.
    await test_db.rollback()
    await test_db.refresh(course)
    assert course.lifecycle_stage == CourseLifecycleStage.DRAFT

    # And no audit row was written.
    rows = (
        await test_db.execute(
            select(CourseStageTransition).where(
                CourseStageTransition.course_id == course.id
            )
        )
    ).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_disallowed_transition_raises(test_db):
    """A transition that isn't in ALLOWED_TRANSITIONS[current] must raise
    ValueError and NOT write an audit row."""
    actor = await _make_admin(test_db, email="bad-actor@example.com")
    course = await _make_course(
        test_db, title="Bad Transition Course", stage=CourseLifecycleStage.ARCHIVED
    )

    with pytest.raises(ValueError):
        await transition_course_stage(
            test_db,
            course,
            CourseLifecycleStage.PUBLISHED,  # archived -> published is disallowed
            actor=actor,
        )

    # Stage unchanged, no audit row.
    await test_db.rollback()
    await test_db.refresh(course)
    assert course.lifecycle_stage == CourseLifecycleStage.ARCHIVED
    rows = (
        await test_db.execute(
            select(CourseStageTransition).where(
                CourseStageTransition.course_id == course.id
            )
        )
    ).scalars().all()
    assert rows == []
