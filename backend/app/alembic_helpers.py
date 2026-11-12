# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning import Course, CourseLifecycleStage, CourseStageTransition


async def backfill_course_stage_transitions(db: AsyncSession) -> int:
    has_history = exists().where(
        CourseStageTransition.course_id == Course.id
    )
    result = await db.execute(
        select(Course).where(
            Course.lifecycle_stage == CourseLifecycleStage.PUBLISHED,
            ~has_history,
        )
    )
    candidates = list(result.scalars().all())
    if not candidates:
        return 0

    now = datetime.now(timezone.utc)
    for course in candidates:
        db.add(
            CourseStageTransition(
                course_id=course.id,
                from_stage=None,
                to_stage=CourseLifecycleStage.PUBLISHED,
                actor_id=None,
                note="imported_from_pre_lifecycle",
                created_at=getattr(course, "created_at", None) or now,
            )
        )
    await db.commit()
    return len(candidates)
