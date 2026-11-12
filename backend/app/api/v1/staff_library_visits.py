"""Staff-side library-visit triage endpoint.

This file is intentionally separate from school_reading_partnerships.py so
that follow-up PRs (and PR #501, which heavily edits that file) can merge
without conflict.

Registration note: this router MUST be included BEFORE
school_reading_partnerships.router in registry.py, because that router has
a GET /library-visits/requests/{school_id} route which would otherwise
shadow our literal GET /library-visits/requests (see feedback_l30_fastapi_router_shadowing).
"""

from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...core.database import get_db
from ...models.reading import LibraryVisitRequest
from ...models.user import User
from .auth import get_current_user
from .dependencies import check_staff_access

logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/school-partnerships", tags=["school-partnerships-staff"])


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


@router.get("/library-visits/requests")
@limiter.limit("120/minute")
async def list_all_library_visit_requests(
    request: Request,
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Optional comma-separated list of statuses to include "
        "(default: pending,scheduled,rejected,cancelled)",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Staff list-all of visit requests across every school.

    Used by the staff triage page to surface pending requests for approval.
    Same staff gate as the approve/reject endpoints
    (check_staff_access -> is_staff_or_admin).
    """
    check_staff_access(current_user)

    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",") if s.strip()]
    else:
        statuses = ["pending", "scheduled", "rejected", "cancelled"]

    result = await db.execute(
        select(LibraryVisitRequest)
        .options(selectinload(LibraryVisitRequest.school))
        .where(LibraryVisitRequest.status.in_(statuses))
        .order_by(LibraryVisitRequest.created_at.desc())
    )
    rows = result.scalars().all()
    return {"requests": [_serialize_visit(r) for r in rows]}
