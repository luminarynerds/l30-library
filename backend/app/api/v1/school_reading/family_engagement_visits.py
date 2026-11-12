# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Teacher-facing library visit scheduling routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from ....core.database import get_db
from ....core.rate_limit import limiter
from ....core.shortcuts import get_or_404
from ....models.outreach import OutreachPartner
from ....models.reading import LibraryVisitRequest
from ....models.user import User
from ....schemas.reading import (
    LibraryVisitApprove,
    LibraryVisitReject,
    LibraryVisitRequestCreate,
    LibraryVisitRequestResponse,
)
from ..auth import get_current_user
from ..dependencies import check_staff_access
from ..feature_guards import require_for_teachers_enabled
from ._notifications import _notify_librarian_of_teacher_action
from ._shared import assert_teacher_access_to_school, require_teacher_of_school

visits_router = APIRouter()


def _serialize_visit(row: LibraryVisitRequest) -> dict:
    return {
        "id": row.id,
        "school_id": row.school_id,
        "school_name": row.school.name if row.school is not None else None,
        "teacher_user_id": row.teacher_user_id,
        "teacher_name": row.teacher_name,
        "requested_date": row.requested_date,
        "scheduled_date": row.scheduled_date,
        "number_of_students": row.number_of_students,
        "grade_level": row.grade_level,
        "purpose": row.purpose,
        "status": row.status,
        "approved_by_user_id": row.approved_by_user_id,
        "approved_at": row.approved_at,
        "rejection_reason": row.rejection_reason,
        "created_at": row.created_at,
        "request_date": row.created_at,
    }


@visits_router.post(
    "/library-visits/request",
    response_model=LibraryVisitRequestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("60/minute")
async def create_library_visit_request(
    request: Request,
    payload: LibraryVisitRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Teacher submits a request for a library visit at their school."""
    # Per-teacher school scope: payload.school_id must match the teacher's school.
    assert_teacher_access_to_school(current_user, payload.school_id)
    await get_or_404(db, OutreachPartner, payload.school_id, "School not found")

    row = LibraryVisitRequest(
        school_id=payload.school_id,
        teacher_user_id=current_user.id,
        teacher_name=payload.teacher_name,
        requested_date=payload.requested_date,
        number_of_students=payload.number_of_students,
        grade_level=payload.grade_level,
        purpose=payload.purpose,
        status="pending",
    )
    db.add(row)
    await db.commit()

    # Reload with school relationship eagerly populated so serialization doesn't
    # trigger a lazy load on the async session (see feedback_l30_async_property_landmine).
    result = await db.execute(
        select(LibraryVisitRequest)
        .options(selectinload(LibraryVisitRequest.school))
        .where(LibraryVisitRequest.id == row.id)
    )
    row = result.scalar_one()

    # Librarian notification (best-effort; never 500s the caller).
    await _notify_librarian_of_teacher_action(
        db,
        teacher=current_user,
        school_id=row.school_id,
        action_type="library_visit_request",
        payload={
            "request_id": row.id,
            "requested_date": row.requested_date.isoformat() if row.requested_date else None,
            "number_of_students": row.number_of_students,
            "grade_level": row.grade_level,
        },
    )

    return _serialize_visit(row)


@visits_router.get(
    "/library-visits/requests/{school_id}",
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("120/minute")
async def list_library_visit_requests(
    request: Request,
    school_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current teacher's pending/rejected requests for a school.

    Returns {"requests": [...]}. Scheduled visits are surfaced separately by
    GET /library-visits/{school_id}.
    """
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    result = await db.execute(
        select(LibraryVisitRequest)
        .options(selectinload(LibraryVisitRequest.school))
        .where(
            and_(
                LibraryVisitRequest.school_id == school_id,
                LibraryVisitRequest.teacher_user_id == current_user.id,
                LibraryVisitRequest.status.in_(["pending", "rejected"]),
            )
        )
        .order_by(LibraryVisitRequest.created_at.desc())
    )
    rows = result.scalars().all()
    return {"requests": [_serialize_visit(r) for r in rows]}


@visits_router.delete(
    "/library-visits/requests/{request_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("60/minute")
async def cancel_library_visit_request(
    request: Request,
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-cancel: teacher cancels their own pending request."""
    row = await get_or_404(db, LibraryVisitRequest, request_id, "Visit request not found")

    if row.teacher_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own visit requests",
        )

    booked_at = row.created_at
    school_id = row.school_id
    row.status = "cancelled"
    await db.commit()

    # Librarian notification (skip-noise: <60s after request = silent cancel).
    await _notify_librarian_of_teacher_action(
        db,
        teacher=current_user,
        school_id=school_id,
        action_type="library_visit_cancel",
        payload={"request_id": request_id},
        booked_at=booked_at,
    )

    return {"status": "cancelled", "id": request_id}


@visits_router.post(
    "/library-visits/requests/{request_id}/approve",
    response_model=LibraryVisitRequestResponse,
)
@limiter.limit("60/minute")
async def approve_library_visit_request(
    request: Request,
    request_id: int,
    payload: LibraryVisitApprove,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Staff approves a pending request, transitioning it to scheduled."""
    check_staff_access(current_user)

    result = await db.execute(
        select(LibraryVisitRequest)
        .options(selectinload(LibraryVisitRequest.school))
        .where(LibraryVisitRequest.id == request_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit request not found")

    if row.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only pending requests can be approved (current status: {row.status})",
        )

    row.status = "scheduled"
    row.scheduled_date = payload.scheduled_date
    row.approved_by_user_id = current_user.id
    row.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return _serialize_visit(row)


@visits_router.post(
    "/library-visits/requests/{request_id}/reject",
    response_model=LibraryVisitRequestResponse,
)
@limiter.limit("60/minute")
async def reject_library_visit_request(
    request: Request,
    request_id: int,
    payload: LibraryVisitReject,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Staff rejects a pending request."""
    check_staff_access(current_user)

    result = await db.execute(
        select(LibraryVisitRequest)
        .options(selectinload(LibraryVisitRequest.school))
        .where(LibraryVisitRequest.id == request_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit request not found")

    if row.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only pending requests can be rejected (current status: {row.status})",
        )

    row.status = "rejected"
    row.rejection_reason = payload.reason
    await db.commit()
    await db.refresh(row)
    return _serialize_visit(row)


@visits_router.get(
    "/library-visits/{school_id}",
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("120/minute")
async def list_scheduled_library_visits(
    request: Request,
    school_id: int,
    current_user: User = Depends(require_teacher_of_school),
    db: AsyncSession = Depends(get_db),
):
    """List all scheduled visits at the given school. No teacher filter -
    everyone at the school sees the same scheduled-visits calendar.
    """
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    result = await db.execute(
        select(LibraryVisitRequest)
        .options(selectinload(LibraryVisitRequest.school))
        .where(
            and_(
                LibraryVisitRequest.school_id == school_id,
                LibraryVisitRequest.status == "scheduled",
            )
        )
        .order_by(LibraryVisitRequest.scheduled_date.asc())
    )
    rows = result.scalars().all()
    return {"visits": [_serialize_visit(r) for r in rows]}
