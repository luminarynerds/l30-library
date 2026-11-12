# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression tests: strategic service state-integrity fixes (sweep 2026-07-01).

H4 — update_goal_status must coerce raw strings through GoalStatus enum
     (was: assigning bare strings like "not_started" and
     "GoalStatus.NOT_STARTED" interchangeably, creating mixed prod data).

H5 — update_goal must only update fields whitelisted in GoalUpdate schema
     (was: mass-assignment that made id, created_at, and FK columns
     writable via the API).
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.strategic import GoalStatus, StrategicGoal
from app.services.strategic_service import (
    update_goal,
    update_goal_status,
    _UPDATABLE_GOAL_FIELDS,
)


def _goal(**kwargs):
    goal = MagicMock(spec=StrategicGoal)
    goal.id = 1
    goal.plan_id = 10
    goal.status = GoalStatus.NOT_STARTED
    goal.completed_date = None
    goal.progress = 0
    goal.updated_at = None
    for k, v in kwargs.items():
        setattr(goal, k, v)
    return goal


def _db_with_goal(goal):
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = goal
    db.execute.return_value = mock_result
    return db


# ---------------------------------------------------------------------------
# H4 — update_goal_status enum coercion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_goal_status_coerces_string_to_enum():
    """Passing a raw string "on_track" must be stored as GoalStatus.ON_TRACK."""
    goal = _goal()
    db = _db_with_goal(goal)

    with patch("app.services.strategic_service.get_goal_by_id", return_value=goal):
        await update_goal_status(goal_id=1, status="on_track", db=db)

    assert goal.status is GoalStatus.ON_TRACK, (
        "Raw string 'on_track' must be coerced to GoalStatus.ON_TRACK, "
        "not stored as the bare string"
    )


@pytest.mark.asyncio
async def test_update_goal_status_rejects_invalid_string():
    """An unrecognised string must raise ValueError from GoalStatus()."""
    goal = _goal()
    db = _db_with_goal(goal)

    with patch("app.services.strategic_service.get_goal_by_id", return_value=goal):
        with pytest.raises(ValueError):
            await update_goal_status(goal_id=1, status="GoalStatus.NOT_STARTED", db=db)


@pytest.mark.asyncio
async def test_update_goal_status_accepts_enum_value():
    """Passing a GoalStatus enum member directly must work without error."""
    goal = _goal()
    db = _db_with_goal(goal)

    with patch("app.services.strategic_service.get_goal_by_id", return_value=goal):
        await update_goal_status(goal_id=1, status=GoalStatus.COMPLETED, db=db)

    assert goal.status is GoalStatus.COMPLETED


# ---------------------------------------------------------------------------
# H5 — update_goal field whitelist
# ---------------------------------------------------------------------------

def test_updatable_goal_fields_excludes_id_and_fks():
    """Whitelist must not include write-dangerous fields."""
    dangerous = {"id", "created_at", "plan_id"}
    overlap = dangerous & _UPDATABLE_GOAL_FIELDS
    assert not overlap, (
        f"_UPDATABLE_GOAL_FIELDS includes dangerous fields: {overlap}"
    )


@pytest.mark.asyncio
async def test_update_goal_ignores_id_in_payload():
    """id in goal_data must be silently ignored (not written to the model)."""
    goal = _goal()
    db = _db_with_goal(goal)

    with patch("app.services.strategic_service.get_goal_by_id", return_value=goal):
        await update_goal(
            goal_id=1,
            goal_data={"id": 999, "title": "New Title"},
            db=db,
        )

    assert goal.id == 1, "id must not be overwritten by mass-assignment"


@pytest.mark.asyncio
async def test_update_goal_applies_whitelisted_fields():
    """Whitelisted fields like title and progress must be applied."""
    goal = _goal()
    db = _db_with_goal(goal)

    with patch("app.services.strategic_service.get_goal_by_id", return_value=goal):
        await update_goal(
            goal_id=1,
            goal_data={"title": "Updated Title", "progress": 50},
            db=db,
        )

    assert goal.title == "Updated Title"
    assert goal.progress == 50


@pytest.mark.asyncio
async def test_update_goal_ignores_created_at_in_payload():
    """created_at in goal_data must be ignored."""
    goal = _goal()
    original_created_at = object()
    goal.created_at = original_created_at
    db = _db_with_goal(goal)

    with patch("app.services.strategic_service.get_goal_by_id", return_value=goal):
        await update_goal(
            goal_id=1,
            goal_data={"created_at": "2020-01-01T00:00:00", "title": "Fine"},
            db=db,
        )

    assert goal.created_at is original_created_at, "created_at must not be overwritten"
