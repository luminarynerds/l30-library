# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Wave 2 / W2-E: alembic data migration backfills one
CourseStageTransition row per pre-existing published course.

Tests the unit-testable helper at ``app.alembic_helpers``; the alembic
file is a thin raw-SQL mirror of the same logic.

asyncio_mode = "auto" (pyproject.toml) -- no @pytest.mark.asyncio.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.learning import Course, CourseLifecycleStage, CourseStageTransition


# ----------------------------------------------------------------------
# Local fixtures -- keep them in this file (test-specific, not general).
# ----------------------------------------------------------------------


@pytest.fixture
async def make_published_course(test_db):
    counter = {"n": 0}

    async def _make(title: str = "Course"):
        counter["n"] += 1
        c = Course(
            title=f"{title} {counter['n']}",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
            difficulty="beginner",
        )
        test_db.add(c)
        await test_db.flush()
        return c

    return _make


@pytest.fixture
async def make_draft_course(test_db):
    counter = {"n": 0}

    async def _make(title: str = "Draft"):
        counter["n"] += 1
        c = Course(
            title=f"{title} {counter['n']}",
            lifecycle_stage=CourseLifecycleStage.DRAFT,
            access_level="patron",
            difficulty="beginner",
        )
        test_db.add(c)
        await test_db.flush()
        return c

    return _make


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


async def test_backfill_inserts_one_row_per_published_course_with_no_existing_history(
    test_db, make_published_course
):
    c1 = await make_published_course(title="Historical")
    c2 = await make_published_course(title="Historical")
    await test_db.commit()

    from app.alembic_helpers import backfill_course_stage_transitions

    inserted = await backfill_course_stage_transitions(test_db)
    assert inserted == 2

    rows = (
        await test_db.execute(
            select(CourseStageTransition).where(
                CourseStageTransition.course_id.in_([c1.id, c2.id])
            )
        )
    ).scalars().all()
    assert len(rows) == 2
    for r in rows:
        assert r.from_stage is None
        assert r.to_stage == CourseLifecycleStage.PUBLISHED
        assert r.actor_id is None
        assert r.note == "imported_from_pre_lifecycle"


async def test_backfill_skips_courses_that_already_have_history(
    test_db, make_published_course
):
    c = await make_published_course(title="Already audited")
    existing = CourseStageTransition(
        course_id=c.id,
        from_stage=None,
        to_stage=CourseLifecycleStage.PUBLISHED,
        note="real_transition",
        actor_id=None,
        created_at=datetime.now(timezone.utc),
    )
    test_db.add(existing)
    await test_db.commit()

    from app.alembic_helpers import backfill_course_stage_transitions

    inserted = await backfill_course_stage_transitions(test_db)
    assert inserted == 0

    rows = (
        await test_db.execute(
            select(CourseStageTransition).where(
                CourseStageTransition.course_id == c.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].note == "real_transition"


async def test_backfill_skips_draft_courses(test_db, make_draft_course):
    await make_draft_course(title="Draft only")
    await test_db.commit()

    from app.alembic_helpers import backfill_course_stage_transitions

    inserted = await backfill_course_stage_transitions(test_db)
    assert inserted == 0
