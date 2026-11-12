# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import timedelta

import pytest

from app.core.datetime_utils import utc_now
from app.models.task_batching import (
    BatchSuggestReason,
    BatchProcessingSession,
    TaskBatchSuggestion,
    TaskBatchType,
    TaskPriorityLevel,
)
from app.services.task_batching_service import TaskBatchingService


@pytest.mark.asyncio
async def test_daily_priority_snapshot_handles_wait_and_conflicts(db_session):
    # can_wait_until/deadline_at are naive (UTC-implied) DateTime columns;
    # the service itself stores naive values (see task_batching_service.py),
    # so fixtures must match.
    now = utc_now().replace(tzinfo=None)

    wait_item = TaskBatchSuggestion(
        organization_id=1,
        batch_type=TaskBatchType.PROCESS_CARDS,
        title="Can wait",
        description="Not urgent",
        reason=BatchSuggestReason.STAFF_REQUEST,
        confidence_score=0.7,
        task_count=3,
        estimated_time_minutes=10,
        priority_level=TaskPriorityLevel.HIGH,
        can_wait_until=now + timedelta(hours=2),
        is_active=True,
        is_dismissed=False,
    )
    urgent_a = TaskBatchSuggestion(
        organization_id=1,
        batch_type=TaskBatchType.BATCH_CHECKINS,
        title="Urgent A",
        description="Urgent",
        reason=BatchSuggestReason.TIME_EFFICIENCY,
        confidence_score=0.95,
        task_count=8,
        estimated_time_minutes=20,
        priority_level=TaskPriorityLevel.CRITICAL,
        drop_everything=True,
        deadline_at=now + timedelta(hours=1),
        is_active=True,
        is_dismissed=False,
    )
    urgent_b = TaskBatchSuggestion(
        organization_id=1,
        batch_type=TaskBatchType.PRINT_HOLD_SLIPS,
        title="Urgent B",
        description="Urgent",
        reason=BatchSuggestReason.VOLUME_THRESHOLD,
        confidence_score=0.90,
        task_count=5,
        estimated_time_minutes=15,
        priority_level=TaskPriorityLevel.CRITICAL,
        drop_everything=True,
        deadline_at=now + timedelta(hours=1),
        is_active=True,
        is_dismissed=False,
    )

    db_session.add_all([wait_item, urgent_a, urgent_b])
    await db_session.commit()

    snapshot = await TaskBatchingService.get_daily_priority_snapshot(db_session, organization_id=1, limit=3)

    assert len(snapshot["most_important"]) == 2
    assert all(item.can_wait_until is None for item in snapshot["most_important"])
    assert len(snapshot["conflicts"]) >= 1


@pytest.mark.asyncio
async def test_complete_session_tracks_priority_completion(db_session):
    suggestion = TaskBatchSuggestion(
        organization_id=2,
        batch_type=TaskBatchType.BATCH_EMAIL_RESPONSES,
        title="Email block",
        description="Batch emails",
        reason=BatchSuggestReason.CONTEXT_SIMILARITY,
        confidence_score=0.8,
        task_count=4,
        estimated_time_minutes=15,
        priority_level=TaskPriorityLevel.HIGH,
        is_active=True,
        is_dismissed=False,
    )
    db_session.add(suggestion)
    await db_session.commit()
    await db_session.refresh(suggestion)

    session = BatchProcessingSession(
        organization_id=2,
        suggestion_id=suggestion.id,
        staff_id=None,
        batch_type=suggestion.batch_type,
        started_at=utc_now() - timedelta(minutes=25),
        estimated_time_minutes=20,
        tasks_attempted=4,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    await TaskBatchingService.complete_session(
        db=db_session,
        session_id=session.id,
        tasks_completed=4,
    )

    await db_session.refresh(suggestion)
    assert suggestion.completed_tasks_count == 4
    assert suggestion.priority_completed_at is not None
