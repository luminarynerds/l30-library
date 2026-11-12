# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Teacher-facing classroom reading-list request routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from ....core.database import get_db
from ....core.rate_limit import limiter
from ....core.shortcuts import get_or_404
from ....models.outreach import OutreachPartner
from ....models.reading import ReadingListRequest, SharedReadingList
from ....models.user import User
from ....schemas.reading import (
    ReadingListRequestCreate,
    ReadingListRequestReject,
    ReadingListRequestResponse,
)
from ..auth import get_current_user
from ..dependencies import check_staff_access
from ..feature_guards import require_for_teachers_enabled
from ._notifications import _notify_librarian_of_teacher_action
from ._shared import require_teacher_of_school

reading_lists_router = APIRouter()


def _serialize_reading_list_request(row: ReadingListRequest) -> dict:
    return {
        "id": row.id,
        "school_id": row.school_id,
        "list_id": row.reading_list_id,
        "list_title": row.reading_list.name if row.reading_list is not None else "",
        "teacher_user_id": row.teacher_user_id,
        "copies": row.copies,
        "notes": row.notes,
        "status": row.status,
        "request_date": row.created_at,
        "fulfilled_by_user_id": row.fulfilled_by_user_id,
        "fulfilled_at": row.fulfilled_at,
        "rejection_reason": row.rejection_reason,
        "updated_at": row.updated_at,
    }


@reading_lists_router.post(
    "/schools/{school_id}/reading-lists/{list_id}/request",
    response_model=ReadingListRequestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("60/minute")
async def create_reading_list_request(
    request: Request,
    school_id: int,
    list_id: int,
    payload: ReadingListRequestCreate,
    current_user: User = Depends(require_teacher_of_school),
    db: AsyncSession = Depends(get_db),
):
    """Teacher requests copies of a reading list for their classroom."""
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    # Verify the reading list exists and belongs to this school
    rl_result = await db.execute(
        select(SharedReadingList).where(
            and_(
                SharedReadingList.id == list_id,
                SharedReadingList.partner_id == school_id,
            )
        )
    )
    reading_list = rl_result.scalar_one_or_none()
    if reading_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reading list not found for this school",
        )

    row = ReadingListRequest(
        school_id=school_id,
        reading_list_id=list_id,
        teacher_user_id=current_user.id,
        copies=payload.copies,
        notes=payload.notes,
        status="pending",
    )
    db.add(row)
    await db.commit()

    # Reload with reading_list eagerly populated so serialization doesn't
    # lazy-load on the async session (see feedback_l30_async_property_landmine).
    result = await db.execute(
        select(ReadingListRequest)
        .options(selectinload(ReadingListRequest.reading_list))
        .where(ReadingListRequest.id == row.id)
    )
    row = result.scalar_one()

    # Librarian notification (best-effort; never 500s the caller).
    await _notify_librarian_of_teacher_action(
        db,
        teacher=current_user,
        school_id=school_id,
        action_type="reading_list_request",
        payload={
            "request_id": row.id,
            "reading_list_id": list_id,
            "list_title": row.reading_list.name if row.reading_list else None,
            "copies": row.copies,
        },
    )

    return _serialize_reading_list_request(row)


@reading_lists_router.get(
    "/schools/{school_id}/reading-list-requests",
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("120/minute")
async def list_reading_list_requests(
    request: Request,
    school_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current teacher's reading-list requests for a school.

    Excludes cancelled requests. Returns {"requests": [...]} with each row in
    camelCase to match the page's ListRequest interface.
    """
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    result = await db.execute(
        select(ReadingListRequest)
        .options(selectinload(ReadingListRequest.reading_list))
        .where(
            and_(
                ReadingListRequest.school_id == school_id,
                ReadingListRequest.teacher_user_id == current_user.id,
                ReadingListRequest.status != "cancelled",
            )
        )
        .order_by(ReadingListRequest.created_at.desc())
    )
    rows = result.scalars().all()
    # Run each row through the Pydantic response model so the keys come out
    # camelCase (matching POST /request and the page's TS interface), rather
    # than the snake_case _serialize_reading_list_request() emits directly.
    return {
        "requests": [
            ReadingListRequestResponse.model_validate(
                _serialize_reading_list_request(r)
            ).model_dump(by_alias=True, mode="json")
            for r in rows
        ]
    }


@reading_lists_router.post(
    "/reading-list-requests/{request_id}/approve",
    response_model=ReadingListRequestResponse,
)
@limiter.limit("60/minute")
async def approve_reading_list_request(
    request: Request,
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Staff approves a pending reading-list request (queued for fulfillment)."""
    check_staff_access(current_user)

    result = await db.execute(
        select(ReadingListRequest)
        .options(selectinload(ReadingListRequest.reading_list))
        .where(ReadingListRequest.id == request_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reading list request not found"
        )

    if row.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only pending requests can be approved (current status: {row.status})",
        )

    row.status = "approved"
    await db.commit()
    await db.refresh(row)
    return _serialize_reading_list_request(row)


@reading_lists_router.post(
    "/reading-list-requests/{request_id}/fulfill",
    response_model=ReadingListRequestResponse,
)
@limiter.limit("60/minute")
async def fulfill_reading_list_request(
    request: Request,
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Staff marks an approved request as fulfilled (copies delivered)."""
    check_staff_access(current_user)

    result = await db.execute(
        select(ReadingListRequest)
        .options(selectinload(ReadingListRequest.reading_list))
        .where(ReadingListRequest.id == request_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reading list request not found"
        )

    if row.status not in ("pending", "approved"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only pending or approved requests can be fulfilled (current status: {row.status})",
        )

    row.status = "fulfilled"
    row.fulfilled_by_user_id = current_user.id
    row.fulfilled_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return _serialize_reading_list_request(row)


@reading_lists_router.post(
    "/reading-list-requests/{request_id}/reject",
    response_model=ReadingListRequestResponse,
)
@limiter.limit("60/minute")
async def reject_reading_list_request(
    request: Request,
    request_id: int,
    payload: ReadingListRequestReject,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Staff rejects a pending request."""
    check_staff_access(current_user)

    result = await db.execute(
        select(ReadingListRequest)
        .options(selectinload(ReadingListRequest.reading_list))
        .where(ReadingListRequest.id == request_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reading list request not found"
        )

    if row.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only pending requests can be rejected (current status: {row.status})",
        )

    row.status = "rejected"
    row.rejection_reason = payload.reason
    await db.commit()
    await db.refresh(row)
    return _serialize_reading_list_request(row)


@reading_lists_router.delete(
    "/reading-list-requests/{request_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("60/minute")
async def cancel_reading_list_request(
    request: Request,
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-cancel: teacher cancels their own pending request."""
    row = await get_or_404(db, ReadingListRequest, request_id, "Reading list request not found")

    if row.teacher_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own reading list requests",
        )

    if row.status not in ("pending", "approved"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a request in status: {row.status}",
        )

    row.status = "cancelled"
    await db.commit()
    return {"status": "cancelled", "id": request_id}
