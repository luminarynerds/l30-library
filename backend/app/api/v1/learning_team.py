# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manager-facing learning routes."""

from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.learning import Course, CourseLifecycleStage, Enrollment
from ...models.operations_audit_log import (
    OperationCategory,
    OperationType,
    OperationsAuditLog,
)
from ...models.user import User
from ...schemas.learning import AssignCourseRequest, EnrollmentResponse, TeamMemberProgress
from ...services import operations_audit_service as ops_audit
from ...services.learning_team_service import get_team_progress, is_report_of
from .dependencies import require_staff

router = APIRouter()


@router.get("/team/progress", response_model=List[TeamMemberProgress])
async def get_team_progress_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Return aggregate training progress for the caller's direct reports."""
    return await get_team_progress(db, current_user.id)


@router.post(
    "/enrollments/assign",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_course_to_report(
    payload: AssignCourseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Assign or update a course enrollment for one of the caller's reports."""
    if not await is_report_of(
        db, manager_id=current_user.id, target_user_id=payload.user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only assign training to your direct reports.",
        )

    course_result = await db.execute(
        select(Course).where(Course.id == payload.course_id)
    )
    course = course_result.scalar_one_or_none()
    if course is None or course.lifecycle_stage != CourseLifecycleStage.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    now = datetime.now(timezone.utc)
    if payload.due_at is not None:
        effective_due_at = payload.due_at
    elif course.duration_days:
        effective_due_at = now + timedelta(days=course.duration_days)
    else:
        effective_due_at = None

    existing_result = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == payload.user_id,
            Enrollment.course_id == payload.course_id,
        )
    )
    enrollment = existing_result.scalar_one_or_none()
    is_new = enrollment is None
    if enrollment is None:
        enrollment = Enrollment(
            user_id=payload.user_id,
            course_id=payload.course_id,
            enrolled_at=now,
            due_at=effective_due_at,
            is_required=payload.is_required,
            assigned_by_id=current_user.id,
        )
        db.add(enrollment)
    else:
        enrollment.is_required = payload.is_required
        enrollment.due_at = effective_due_at
        enrollment.assigned_by_id = current_user.id

    await db.flush()
    await db.refresh(enrollment)

    await ops_audit._safe_add(
        db,
        OperationsAuditLog(
            category=OperationCategory.PATRON.value,
            operation_type=OperationType.TRAINING_ASSIGNED.value,
            patron_id=payload.user_id,
            staff_id=current_user.id,
            staff_identifier=ops_audit._user_identifier(current_user),
            after_state={
                "course_id": payload.course_id,
                "course_title": course.title,
                "is_required": payload.is_required,
                "due_at": effective_due_at.isoformat() if effective_due_at else None,
                "is_new_enrollment": is_new,
            },
        ),
    )

    return enrollment
