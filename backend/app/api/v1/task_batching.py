# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Task Batching API Endpoints

API for intelligent task batching suggestions to reduce context-switching
and improve staff efficiency.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from .dependencies import require_staff, require_admin, get_current_user
from ...models.task_batching import TaskBatchType, TaskPriorityLevel
from ...models.user import User
from app.services.task_batching_service import TaskBatchingService

router = APIRouter()


@router.get("/staff/batch-suggestions")
async def get_batch_suggestions(
    batch_type: Optional[TaskBatchType] = Query(None, description="Filter by batch type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get active batch suggestions for the current organization

    Returns intelligent suggestions for batching similar tasks together
    to reduce context-switching and improve efficiency.
    """
    suggestions = await TaskBatchingService.get_active_suggestions(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        batch_type=batch_type,
    )

    return {
        "suggestions": [
            {
                "id": s.id,
                "batch_type": s.batch_type,
                "title": s.title,
                "description": s.description,
                "reason": s.reason,
                "confidence_score": s.confidence_score,
                "task_count": s.task_count,
                "estimated_time_minutes": s.estimated_time_minutes,
                "estimated_savings_minutes": s.estimated_savings_minutes,
                "priority_level": s.priority_level,
                "manager_priority_note": s.manager_priority_note,
                "can_wait_until": s.can_wait_until.isoformat() if s.can_wait_until else None,
                "deadline_at": s.deadline_at.isoformat() if s.deadline_at else None,
                "drop_everything": s.drop_everything,
                "protected_time_recommended": s.protected_time_recommended,
                "distraction_deflection_script": s.distraction_deflection_script,
                "completed_tasks_count": s.completed_tasks_count,
                "priority_completed_at": s.priority_completed_at.isoformat() if s.priority_completed_at else None,
                "location_hint": s.location_hint,
                "timing_hint": s.timing_hint,
                "prerequisites": s.prerequisites,
                "is_accepted": s.is_accepted,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            }
            for s in suggestions
        ]
    }


@router.post("/staff/batch-suggestions/refresh")
async def refresh_batch_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Analyze current workload and generate fresh batch suggestions

    Analyzes pending work across holds, card applications, overdue items,
    and other areas to suggest intelligent task batching opportunities.
    """
    suggestions = await TaskBatchingService.analyze_and_generate_suggestions(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        staff_id=current_user.id,
    )

    return {
        "message": f"Generated {len(suggestions)} new batch suggestions",
        "suggestions": [
            {
                "id": s.id,
                "batch_type": s.batch_type,
                "title": s.title,
                "description": s.description,
                "task_count": s.task_count,
                "estimated_time_minutes": s.estimated_time_minutes,
                "estimated_savings_minutes": s.estimated_savings_minutes,
                "priority_level": s.priority_level,
                "drop_everything": s.drop_everything,
                "deadline_at": s.deadline_at.isoformat() if s.deadline_at else None,
            }
            for s in suggestions
        ],
    }


@router.get("/staff/priorities/today")
async def get_today_priorities(
    limit: int = Query(3, ge=1, le=10, description="How many most-important items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get today's most-important priorities with conflict guidance."""
    snapshot = await TaskBatchingService.get_daily_priority_snapshot(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        limit=limit,
    )

    return {
        "generated_at": snapshot["generated_at"].isoformat(),
        "most_important": [
            {
                "id": s.id,
                "title": s.title,
                "batch_type": s.batch_type,
                "priority_level": s.priority_level,
                "drop_everything": s.drop_everything,
                "deadline_at": s.deadline_at.isoformat() if s.deadline_at else None,
                "manager_priority_note": s.manager_priority_note,
                "conflict_resolution_note": s.conflict_resolution_note,
                "protected_time_recommended": s.protected_time_recommended,
                "distraction_deflection_script": s.distraction_deflection_script,
            }
            for s in snapshot["most_important"]
        ],
        "conflicts": snapshot["conflicts"],
    }


@router.post("/staff/batch-suggestions/{suggestion_id}/accept")
async def accept_batch_suggestion(
    suggestion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Accept a batch suggestion

    Marks the suggestion as accepted by the current staff member.
    You can then create a batch session to start working on it.
    """
    try:
        suggestion = await TaskBatchingService.accept_suggestion(
            db=db,
            suggestion_id=suggestion_id,
            staff_id=current_user.id,
        )

        return {
            "message": "Batch suggestion accepted",
            "suggestion": {
                "id": suggestion.id,
                "batch_type": suggestion.batch_type,
                "title": suggestion.title,
                "is_accepted": suggestion.is_accepted,
                "accepted_at": suggestion.accepted_at.isoformat() if suggestion.accepted_at else None,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/staff/batch-suggestions/{suggestion_id}/dismiss")
async def dismiss_batch_suggestion(
    suggestion_id: int,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Dismiss a batch suggestion

    Marks the suggestion as dismissed with an optional reason.
    This helps improve future suggestions.
    """
    try:
        suggestion = await TaskBatchingService.dismiss_suggestion(
            db=db,
            suggestion_id=suggestion_id,
            reason=reason,
        )

        return {
            "message": "Batch suggestion dismissed",
            "suggestion": {
                "id": suggestion.id,
                "batch_type": suggestion.batch_type,
                "is_dismissed": suggestion.is_dismissed,
                "dismissed_reason": suggestion.dismissed_reason,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch("/staff/batch-suggestions/{suggestion_id}/manager-priority")
async def set_manager_priority(
    suggestion_id: int,
    priority_level: TaskPriorityLevel,
    manager_priority_note: Optional[str] = None,
    deadline_at: Optional[str] = None,
    can_wait_until: Optional[str] = None,
    drop_everything: bool = False,
    protected_time_recommended: bool = False,
    conflict_resolution_note: Optional[str] = None,
    distraction_deflection_script: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Set manager priority metadata so staff can see what matters most now."""
    from datetime import datetime
    from sqlalchemy import select
    from ...models.task_batching import TaskBatchSuggestion

    result = await db.execute(select(TaskBatchSuggestion).where(TaskBatchSuggestion.id == suggestion_id))
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    suggestion.priority_level = priority_level
    suggestion.manager_priority_note = manager_priority_note
    suggestion.manager_set_by_id = current_user.id
    suggestion.drop_everything = drop_everything
    suggestion.protected_time_recommended = protected_time_recommended
    suggestion.conflict_resolution_note = conflict_resolution_note
    suggestion.distraction_deflection_script = distraction_deflection_script
    suggestion.deadline_at = datetime.fromisoformat(deadline_at) if deadline_at else None
    suggestion.can_wait_until = datetime.fromisoformat(can_wait_until) if can_wait_until else None

    await db.commit()
    await db.refresh(suggestion)

    return {
        "message": "Manager priority updated",
        "suggestion": {
            "id": suggestion.id,
            "priority_level": suggestion.priority_level,
            "manager_priority_note": suggestion.manager_priority_note,
            "deadline_at": suggestion.deadline_at.isoformat() if suggestion.deadline_at else None,
            "can_wait_until": suggestion.can_wait_until.isoformat() if suggestion.can_wait_until else None,
            "drop_everything": suggestion.drop_everything,
            "protected_time_recommended": suggestion.protected_time_recommended,
        },
    }


@router.post("/staff/batch-sessions")
async def create_batch_session(
    suggestion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Create a new batch processing session

    Starts tracking time and metrics for processing a batch of tasks.
    Use this when you begin working on a batch suggestion.
    """
    try:
        session = await TaskBatchingService.create_session(
            db=db,
            suggestion_id=suggestion_id,
            staff_id=current_user.id,
        )

        return {
            "message": "Batch session started",
            "session": {
                "id": session.id,
                "suggestion_id": session.suggestion_id,
                "batch_type": session.batch_type,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "estimated_time_minutes": session.estimated_time_minutes,
                "tasks_attempted": session.tasks_attempted,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/staff/batch-sessions/{session_id}/complete")
async def complete_batch_session(
    session_id: int,
    tasks_completed: int,
    quality_rating: Optional[int] = Query(None, ge=1, le=5, description="Quality rating (1-5)"),
    efficiency_rating: Optional[int] = Query(None, ge=1, le=5, description="Efficiency rating (1-5)"),
    would_batch_again: Optional[bool] = Query(None, description="Would you batch this task type again?"),
    staff_notes: Optional[str] = Query(None, description="Additional notes or feedback"),
    interruptions_count: int = Query(0, description="Number of interruptions during batch"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Complete a batch processing session

    Records completion metrics, feedback, and calculates time savings.
    This data helps improve future batch suggestions.
    """
    try:
        session = await TaskBatchingService.complete_session(
            db=db,
            session_id=session_id,
            tasks_completed=tasks_completed,
            quality_rating=quality_rating,
            efficiency_rating=efficiency_rating,
            would_batch_again=would_batch_again,
            staff_notes=staff_notes,
            interruptions_count=interruptions_count,
        )

        return {
            "message": "Batch session completed",
            "session": {
                "id": session.id,
                "batch_type": session.batch_type,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "actual_duration_minutes": session.actual_duration_minutes,
                "tasks_completed": session.tasks_completed,
                "tasks_attempted": session.tasks_attempted,
                "completion_rate": session.completion_rate,
                "time_saved_minutes": session.time_saved_minutes,
                "quality_rating": session.quality_rating,
                "efficiency_rating": session.efficiency_rating,
                "would_batch_again": session.would_batch_again,
                "interruptions_count": session.interruptions_count,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/staff/batch-sessions/{session_id}")
async def get_batch_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get details of a specific batch processing session"""
    session = await TaskBatchingService.get_session(db=db, session_id=session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session": {
            "id": session.id,
            "batch_type": session.batch_type,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "actual_duration_minutes": session.actual_duration_minutes,
            "estimated_time_minutes": session.estimated_time_minutes,
            "tasks_completed": session.tasks_completed,
            "tasks_attempted": session.tasks_attempted,
            "completion_rate": session.completion_rate,
            "time_saved_minutes": session.time_saved_minutes,
            "quality_rating": session.quality_rating,
            "efficiency_rating": session.efficiency_rating,
            "would_batch_again": session.would_batch_again,
            "staff_notes": session.staff_notes,
            "interruptions_count": session.interruptions_count,
            "is_complete": session.is_complete,
        }
    }


@router.get("/staff/my-batch-sessions")
async def get_my_batch_sessions(
    limit: int = Query(10, ge=1, le=50, description="Number of recent sessions to retrieve"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get recent batch processing sessions for the current staff member"""
    sessions = await TaskBatchingService.get_staff_sessions(
        db=db,
        staff_id=current_user.id,
        limit=limit,
    )

    return {
        "sessions": [
            {
                "id": s.id,
                "batch_type": s.batch_type,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "actual_duration_minutes": s.actual_duration_minutes,
                "tasks_completed": s.tasks_completed,
                "tasks_attempted": s.tasks_attempted,
                "completion_rate": s.completion_rate,
                "time_saved_minutes": s.time_saved_minutes,
                "is_complete": s.is_complete,
            }
            for s in sessions
        ]
    }
