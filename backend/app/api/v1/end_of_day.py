# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
End-of-Day Automation API Endpoints.

Provides endpoints for:
- Creating and managing EOD closing sessions
- Auto-executing EOD tasks
- Security check verification
- Statistics summaries
- Auto-logout scheduling

All endpoints require staff authentication.
"""

from app.core.logging import get_logger
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.branch_resolver import label_to_branch_id
from ...core.shortcuts import get_or_404
from ...models.end_of_day import (
    EODTemplate, EODSession, EODTask, EODSecurityCheck, EODStatistics,
    EODTaskType, EODTaskStatus, EODSessionStatus, SecurityCheckType
)
from ...models.user import User, UserRole
from ...services.end_of_day_service import EndOfDayService
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/end-of-day", tags=["end-of-day"])



# =============================================================================
# Pydantic Schemas
# =============================================================================

class EODTaskResponse(BaseModel):
    id: int
    session_id: int
    task_type: str
    display_name: str
    status: str
    task_data: dict
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: int
    assigned_to_id: Optional[int]
    completed_by_id: Optional[int]
    error_message: Optional[str]

    # NULL in DB on these required fields 500'd serialization; coerce to defaults.
    @field_validator("task_data", mode="before")
    @classmethod
    def _task_data_default(cls, v):
        return {} if v is None else v

    @field_validator("duration_seconds", mode="before")
    @classmethod
    def _duration_default(cls, v):
        return 0 if v is None else v

    class Config:
        from_attributes = True


class EODSecurityCheckResponse(BaseModel):
    id: int
    session_id: int
    check_type: str
    display_name: str
    passed: bool
    notes: Optional[str]
    location: Optional[str]
    checked_by_id: int
    checked_at: datetime

    class Config:
        from_attributes = True


class EODSessionResponse(BaseModel):
    id: int
    session_code: str
    template_id: int
    branch_id: Optional[int] = None
    branch_location: str
    closing_date: date
    staff_id: int
    assisted_by_ids: List[int]
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_duration_seconds: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    skipped_tasks: int
    backup_status: Optional[str]
    statistics_summary: Optional[dict]
    notes: Optional[str]
    auto_logout_at: Optional[datetime]
    auto_logout_performed: bool
    tasks: List[EODTaskResponse]

    # NULL in DB on these required fields 500'd serialization; coerce to defaults.
    @field_validator("assisted_by_ids", mode="before")
    @classmethod
    def _assisted_default(cls, v):
        return [] if v is None else v

    @field_validator("auto_logout_performed", mode="before")
    @classmethod
    def _auto_logout_default(cls, v):
        return False if v is None else v

    class Config:
        from_attributes = True


class CreateSessionRequest(BaseModel):
    branch_id: Optional[int] = Field(None, description="Branch id for closing")
    branch_location: str = Field(..., description="Branch location for closing (deprecated; prefer branch_id)")
    assisted_by_ids: Optional[List[int]] = Field(None, description="IDs of additional staff assisting")


class ExecuteTaskRequest(BaseModel):
    task_data: Optional[dict] = Field(None, description="Staff-provided data (e.g., drawer_count, discrepancy_notes)")


class SecurityCheckRequest(BaseModel):
    check_type: str = Field(..., description="Type of security check")
    passed: bool = Field(..., description="Whether check passed")
    notes: Optional[str] = Field(None, description="Notes about the check")
    location: Optional[str] = Field(None, description="Location checked")


class EODStatisticsResponse(BaseModel):
    id: int
    closing_date: date
    branch_id: Optional[int] = None
    branch_location: str
    total_checkouts: int
    total_checkins: int
    total_holds_placed: int
    total_holds_ready: int
    overdue_items_count: int
    total_fines_amount: float
    total_fines_paid: float
    total_fines_waived: float
    total_sessions: int
    avg_closing_time_minutes: float
    total_staff_involved: int
    total_exceptions: int
    tomorrow_events_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# EOD Session Endpoints
# =============================================================================

@router.post("/sessions", response_model=EODSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_closing_session(
    request: CreateSessionRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new end-of-day closing session.

    Starts a new EOD session with automated task generation based on
    the branch's closing template. Tasks are ready to execute one-by-one.

    """
    try:
        session = await EndOfDayService.create_closing_session(
            db=db,
            branch_location=request.branch_location,
            branch_id=request.branch_id,
            staff_id=current_user.id,
            assisted_by_ids=request.assisted_by_ids,
        )
        await db.commit()

        # Reload with relationships
        await db.refresh(session, ["tasks"])

        logger.info(
            f"EOD session created: {session.session_code} "
            f"by user {current_user.id} for {request.branch_location}"
        )
        return session

    except Exception as e:
        logger.error(f"Failed to create EOD session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create EOD session"
        ) from e


@router.get("/sessions/{session_id}", response_model=EODSessionResponse)
async def get_session(
    session_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific EOD session with all tasks and status"""
    session = await get_or_404(db, EODSession, session_id, "EOD session not found")

    # Reload with tasks
    await db.refresh(session, ["tasks"])
    return session


@router.get("/sessions", response_model=List[EODSessionResponse])
async def list_sessions(
    branch_location: Optional[str] = Query(None, deprecated=True),
    branch_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    closing_date: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List EOD sessions with optional filtering.

    branch_id is preferred over branch_location; the label resolves via the
    canonical map and falls back to legacy match when unresolvable.
    """
    if branch_id is None and branch_location:
        branch_id = label_to_branch_id(branch_location)

    query = select(EODSession).options(selectinload(EODSession.tasks))

    if branch_id is not None:
        query = query.where(EODSession.branch_id == branch_id)
    elif branch_location:
        query = query.where(EODSession.branch_location == branch_location)
    if status_filter:
        query = query.where(EODSession.status == status_filter)
    if closing_date:
        query = query.where(EODSession.closing_date == closing_date)

    query = query.limit(limit).offset(offset).order_by(EODSession.started_at.desc())

    result = await db.execute(query)
    sessions = result.scalars().all()
    return sessions


@router.post("/sessions/{session_id}/complete", response_model=EODSessionResponse)
async def complete_session(
    session_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark an EOD session as complete.

    Finalizes the session, calculates totals, and prepares for auto-logout.
    """
    session = await get_or_404(db, EODSession, session_id, "EOD session not found")

    try:
        completed_session = await EndOfDayService.complete_session(db, session_id)
        await db.commit()

        logger.info(f"EOD session completed: {session.session_code} by user {current_user.id}")
        return completed_session

    except Exception as e:
        logger.error(f"Failed to complete EOD session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete EOD session"
        ) from e


# =============================================================================
# Task Execution Endpoints
# =============================================================================

@router.post("/tasks/{task_id}/execute", response_model=EODTaskResponse)
async def execute_task(
    task_id: int,
    request: Optional[ExecuteTaskRequest] = None,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a single EOD task.

    Runs the task (e.g., generates holds pull list, sends notices, etc.)
    and updates its status. Most tasks complete automatically in seconds.

    Optionally accepts task_data in the request body for manual tasks
    like close_registers (e.g., drawer_count, discrepancy_notes).
    """
    task = await get_or_404(db, EODTask, task_id, "Task not found")

    try:
        staff_task_data = request.task_data if request else None
        await EndOfDayService.execute_task(db, task, current_user.id, task_data=staff_task_data)
        await db.commit()

        logger.info(f"EOD task executed: {task.id} ({task.task_type}) by user {current_user.id}")
        return task

    except Exception as e:
        logger.error(f"Failed to execute EOD task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute task"
        ) from e


@router.get("/tasks/{task_id}", response_model=EODTaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific task"""
    task = await get_or_404(db, EODTask, task_id, "Task not found")

    return task


@router.post("/tasks/{task_id}/skip")
async def skip_task(
    task_id: int,
    reason: str = Query(..., description="Reason for skipping task"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Skip a task if not applicable"""
    task = await get_or_404(db, EODTask, task_id, "Task not found")

    task.status = EODTaskStatus.SKIPPED
    task.skip_reason = reason
    task.completed_by_id = current_user.id
    task.completed_at = datetime.now()

    await db.commit()
    logger.info(f"EOD task skipped: {task.id} by user {current_user.id}")
    return {"message": "Task skipped", "task_id": task.id}


@router.post("/tasks/{task_id}/retry", response_model=EODTaskResponse)
async def retry_task(
    task_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Retry a previously failed task.

    Only failed tasks can be retried. Useful for transient failures
    like database connection issues.
    """
    try:
        task = await EndOfDayService.retry_failed_task(
            db=db,
            task_id=task_id,
            completed_by_id=current_user.id,
        )
        await db.commit()

        logger.info(
            f"EOD task retry completed: {task.id} by user {current_user.id}",
            extra={"task_status": task.status},
        )
        return task

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to retry task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry task"
        ) from e


# =============================================================================
# Auto-Logout Endpoints
# =============================================================================

@router.post("/sessions/{session_id}/schedule-logout")
async def schedule_auto_logout(
    session_id: int,
    logout_delay_minutes: int = Query(5, ge=1, le=60, description="Minutes until logout"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Schedule automatic logout after session completion.

    After all tasks complete, staff can set auto-logout to happen in
    N minutes, giving them time to review everything before being logged out.
    """
    session = await get_or_404(db, EODSession, session_id, "EOD session not found")

    try:
        await EndOfDayService.schedule_auto_logout(db, session_id, logout_delay_minutes)
        await db.commit()

        logger.info(
            f"Auto-logout scheduled for EOD session {session.session_code}: "
            f"{logout_delay_minutes} minutes by user {current_user.id}"
        )
        return {
            "message": "Auto-logout scheduled",
            "logout_at": session.auto_logout_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to schedule auto-logout: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule auto-logout"
        ) from e


# =============================================================================
# Statistics Endpoints
# =============================================================================

@router.get("/statistics/{date_str}/{branch_location}", response_model=EODStatisticsResponse)
async def get_statistics(
    date_str: str,
    branch_location: str,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get EOD statistics for a specific date and branch"""
    try:
        closing_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format (use YYYY-MM-DD)"
        ) from None

    result = await db.execute(
        select(EODStatistics).where(
            (EODStatistics.closing_date == closing_date) &
            (EODStatistics.branch_location == branch_location)
        )
    )
    stats = result.scalars().first()

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Statistics not found for this date and branch"
        )

    return stats


@router.get("/statistics", response_model=List[EODStatisticsResponse])
async def list_statistics(
    branch_location: Optional[str] = Query(None, deprecated=True),
    branch_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(30, ge=1, le=365),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List EOD statistics with optional filtering by date range.

    branch_id is preferred; branch_location resolves via the canonical map.
    """
    if branch_id is None and branch_location:
        branch_id = label_to_branch_id(branch_location)

    query = select(EODStatistics)

    if branch_id is not None:
        query = query.where(EODStatistics.branch_id == branch_id)
    elif branch_location:
        query = query.where(EODStatistics.branch_location == branch_location)
    if start_date:
        query = query.where(EODStatistics.closing_date >= start_date)
    if end_date:
        query = query.where(EODStatistics.closing_date <= end_date)

    query = query.limit(limit).offset(offset).order_by(EODStatistics.closing_date.desc())

    result = await db.execute(query)
    stats = result.scalars().all()
    return stats


# =============================================================================
# Quick Close Endpoint (One-Click Closing)
# =============================================================================

@router.post("/quick-close")
async def quick_close(
    branch_location: str = Query(..., description="Branch location to close"),
    skip_overdue_notices: bool = Query(False, description="Skip overdue notices"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    One-click EOD closing that executes all tasks automatically.

    Executes critical tasks in sequence (registers, holds, backup, security)
    and optionally skips lower-priority tasks. Should complete in under 5 minutes.

    """
    # Validate branch_location against known branches to prevent closing phantom branches
    from ...models.multi_branch import Branch
    branch_result = await db.execute(
        select(Branch).where(Branch.name == branch_location)
    )
    branch = branch_result.scalar_one_or_none()
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown branch location: '{branch_location}'. Please select a valid branch.",
        )

    try:
        # Create session
        session = await EndOfDayService.create_closing_session(
            db=db,
            branch_location=branch_location,
            staff_id=current_user.id,
        )
        await db.flush()

        # Load tasks
        await db.refresh(session, ["tasks"])

        # Execute tasks in order
        for task in session.tasks:
            # Skip optional tasks if requested
            if skip_overdue_notices and task.task_type == EODTaskType.SEND_OVERDUE_NOTICES:
                task.status = EODTaskStatus.SKIPPED
                task.skip_reason = "Skipped via quick-close"
                continue

            await EndOfDayService.execute_task(db, task, current_user.id)
            await db.flush()

        # Complete session
        await EndOfDayService.complete_session(db, session.id)
        await db.commit()

        logger.info(
            f"Quick-close completed for {branch_location} by user {current_user.id} "
            f"in {session.total_duration_seconds} seconds"
        )

        return {
            "message": "Quick close completed successfully",
            "session_code": session.session_code,
            "session_id": session.id,
            "total_duration_seconds": session.total_duration_seconds,
            "tasks_completed": session.completed_tasks,
        }

    except Exception as e:
        logger.error(f"Quick-close failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Quick-close failed"
        ) from e
