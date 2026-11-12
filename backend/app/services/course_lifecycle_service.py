# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning import (Course, CourseLifecycleStage,
                                 CourseStageTransition, Lesson, Module)
from app.models.user import User


# Allowed stage transitions. Read as: from KEY you may move to any stage in
# VALUE. Anything not in the set raises ValueError.
#
# Notes:
#   - ARCHIVED is a one-way terminal-ish stage; only DRAFT can come back out.
#   - PUBLISHED can go directly to DRAFT ("Unpublish") — no intermediate
#     review stage exists any more. The audit log captures the transition.
#   - Every stage has at least one outbound transition (verified by test).
ALLOWED_TRANSITIONS: dict[CourseLifecycleStage, set[CourseLifecycleStage]] = {
    CourseLifecycleStage.DRAFT: {
        CourseLifecycleStage.PUBLISHED,
        CourseLifecycleStage.ARCHIVED,
    },
    CourseLifecycleStage.PUBLISHED: {
        CourseLifecycleStage.DRAFT,
        CourseLifecycleStage.ARCHIVED,
    },
    CourseLifecycleStage.ARCHIVED: {
        CourseLifecycleStage.DRAFT,
    },
}


# How long after publishing/last review a course is considered current.
# 365 days (intentionally a fixed number of days, not "12 months") to keep
# the migration backfill and the runtime computation aligned exactly.
REVIEW_CADENCE = timedelta(days=365)


class EmptyCourseError(ValueError):
    pass


def is_transition_allowed(
    current: CourseLifecycleStage, target: CourseLifecycleStage
) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def compute_review_due(now: datetime) -> datetime:
    return now + REVIEW_CADENCE


async def _course_has_lessons(db: AsyncSession, course_id: int) -> bool:
    result = await db.execute(
        select(func.count(Lesson.id))
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.course_id == course_id)
    )
    return (result.scalar_one() or 0) > 0


async def transition_course_stage(
    db: AsyncSession,
    course: Course,
    to_stage: CourseLifecycleStage,
    actor: User,
    note: Optional[str] = None,
) -> Course:
    # SQLite returns the enum column as a raw ``str`` even when declared
    # ``native_enum=False``; PostgreSQL adapts cleanly. Coerce defensively
    # so the lookup table + the audit-row write both see the enum.
    if isinstance(course.lifecycle_stage, str):
        course.lifecycle_stage = CourseLifecycleStage(course.lifecycle_stage)
    current = course.lifecycle_stage
    if not is_transition_allowed(current, to_stage):
        raise ValueError(
            f"Disallowed course lifecycle transition: {current.value} -> {to_stage.value}"
        )

    if to_stage == CourseLifecycleStage.PUBLISHED:
        if not await _course_has_lessons(db, course.id):
            raise EmptyCourseError(
                "Cannot publish an empty course. Add at least one module "
                "with at least one lesson before publishing."
            )

    now = datetime.now(timezone.utc)

    # Audit row first so a downstream commit failure on the course mutation
    # doesn't leave a Course updated without a transition record. Both flush
    # to the same session, so the caller's commit lands them together.
    transition = CourseStageTransition(
        course_id=course.id,
        from_stage=current,
        to_stage=to_stage,
        actor_id=actor.id,
        note=note,
    )
    db.add(transition)

    course.lifecycle_stage = to_stage
    if to_stage == CourseLifecycleStage.PUBLISHED:
        course.last_reviewed_at = now
        course.last_reviewed_by_id = actor.id
        course.review_due_at = compute_review_due(now)

    await db.flush()
    return course
