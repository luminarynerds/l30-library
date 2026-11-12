# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Attendance Tracking API Routes.

Endpoints for:
- Session management (CRUD, open/close/finalize)
- QR code check-in (self-service, no auth)
- Library card scan check-in (staff)
- Walk-in quick-add (staff)
- Head count mode (staff)
- Post-event survey sending (staff)
- Attendance dashboard and trends (staff)
- ROI reporting (staff/admin)
"""

from app.core.logging import get_logger
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.user import User
from ...schemas.attendance import (
    AttendanceSessionCreate,
    AttendanceSessionResponse,
    AttendanceSessionUpdate,
    CheckInResponse,
    HeadCountUpdate,
    LibraryCardCheckIn,
    QRCodeCheckIn,
    SurveySendRequest,
    WalkInCheckIn,
)
from ...schemas.common import PaginatedResponse, PaginationInfo
from ...services.attendance_service import AttendanceService
from .auth import get_current_user
from .dependencies import require_staff as require_staff_role

logger = get_logger(__name__)

router = APIRouter(prefix="/attendance", tags=["attendance"])




def _session_to_response(session) -> dict:
    effective = (session.total_checked_in or 0) + (session.head_count_total or 0)
    cost_per = None
    if session.event_cost and effective > 0:
        cost_per = round(float(session.event_cost) / effective, 2)

    return {
        "id": session.id,
        "event_id": session.event_id,
        "program_id": session.program_id,
        "session_name": session.session_name,
        "session_date": session.session_date,
        "status": session.status.value if hasattr(session.status, 'value') else session.status,
        "qr_code_token": session.qr_code_token,
        "head_count_mode": session.head_count_mode,
        "head_count_total": session.head_count_total or 0,
        "head_count_by_age": session.head_count_by_age,
        "total_checked_in": session.total_checked_in or 0,
        "total_walk_ins": session.total_walk_ins or 0,
        "total_pre_registered": session.total_pre_registered or 0,
        "total_card_scans": session.total_card_scans or 0,
        "total_qr_scans": session.total_qr_scans or 0,
        "event_cost": session.event_cost,
        "cost_notes": session.cost_notes,
        "survey_enabled": session.survey_enabled,
        "survey_link": session.survey_link,
        "survey_sent_at": session.survey_sent_at,
        "opened_by_id": session.opened_by_id,
        "closed_by_id": session.closed_by_id,
        "closed_at": session.closed_at,
        "notes": session.notes,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "effective_total": effective,
        "cost_per_attendee": cost_per,
    }


def _checkin_to_response(check_in, patron_name: str = None) -> dict:
    return {
        "id": check_in.id,
        "session_id": check_in.session_id,
        "patron_id": check_in.patron_id,
        "registration_id": check_in.registration_id,
        "guest_name": check_in.guest_name,
        "guest_email": check_in.guest_email,
        "check_in_method": check_in.check_in_method.value if hasattr(check_in.check_in_method, 'value') else check_in.check_in_method,
        "checked_in_at": check_in.checked_in_at,
        "library_card_number": check_in.library_card_number,
        "age_range": check_in.age_range.value if hasattr(check_in.age_range, 'value') else check_in.age_range,
        "is_repeat_attendee": check_in.is_repeat_attendee,
        "previous_visit_count": check_in.previous_visit_count,
        "first_visit_date": check_in.first_visit_date,
        "patron_name": patron_name,
        "notes": check_in.notes,
    }


# ============================================================================
# Session Management
# ============================================================================


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_session(
    request: Request,
    data: AttendanceSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Create a new attendance tracking session for an event or program."""
    try:
        session = await AttendanceService.create_session(
            db=db,
            session_name=data.session_name,
            session_date=data.session_date,
            staff_id=current_user.id,
            event_id=data.event_id,
            program_id=data.program_id,
            head_count_mode=data.head_count_mode,
            event_cost=data.event_cost,
            cost_notes=data.cost_notes,
            survey_enabled=data.survey_enabled,
            survey_link=data.survey_link,
            notes=data.notes,
        )
        await db.commit()
        logger.info(f"Attendance session created: {session.id} by user_id={current_user.id}")
        return _session_to_response(session)
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create attendance session")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sessions")
@limiter.limit("60/minute")
async def list_sessions(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    event_id: Optional[int] = Query(None),
    program_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """List attendance sessions with filtering."""
    sessions, total = await AttendanceService.list_sessions(
        db=db,
        status=status_filter,
        start_date=start_date,
        end_date=end_date,
        event_id=event_id,
        program_id=program_id,
        page=page,
        per_page=per_page,
    )

    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    return {
        "data": [_session_to_response(s) for s in sessions],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
    }


@router.get("/sessions/{session_id}")
@limiter.limit("60/minute")
async def get_session(
    request: Request,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get details of a specific attendance session."""
    session = await AttendanceService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_to_response(session)


@router.put("/sessions/{session_id}")
@limiter.limit("30/minute")
async def update_session(
    request: Request,
    session_id: int,
    data: AttendanceSessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Update an attendance session."""
    session = await AttendanceService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(session, field, value)

    await db.commit()
    await db.refresh(session)
    return _session_to_response(session)


@router.post("/sessions/{session_id}/close")
@limiter.limit("30/minute")
async def close_session(
    request: Request,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Close a session to stop accepting check-ins."""
    try:
        session = await AttendanceService.close_session(db, session_id, current_user.id)
        await db.commit()
        logger.info(f"Attendance session {session_id} closed by user_id={current_user.id}")
        return _session_to_response(session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/sessions/{session_id}/finalize")
@limiter.limit("30/minute")
async def finalize_session(
    request: Request,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Finalize a session (lock all data)."""
    try:
        session = await AttendanceService.finalize_session(db, session_id)
        await db.commit()
        logger.info(f"Attendance session {session_id} finalized by user_id={current_user.id}")
        return _session_to_response(session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Check-In Endpoints
# ============================================================================


@router.post("/check-in/qr")
@limiter.limit("120/minute")
async def check_in_qr(  # noqa: role-check -- public QR self-check-in, rate-limited
    request: Request,
    data: QRCodeCheckIn,
    db: AsyncSession = Depends(get_db),
):
    """
    Self-service QR code check-in. No authentication required.

    Attendees scan the QR code displayed at the event to check themselves in.
    """
    try:
        check_in = await AttendanceService.check_in_qr(
            db=db,
            qr_token=data.qr_token,
            patron_id=data.patron_id,
            guest_name=data.guest_name,
            guest_email=data.guest_email,
            age_range=data.age_range or "unknown",
        )
        await db.commit()
        return _checkin_to_response(check_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/check-in/library-card")
@limiter.limit("120/minute")
async def check_in_library_card(
    request: Request,
    data: LibraryCardCheckIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Check in a patron by scanning their library card."""
    try:
        check_in = await AttendanceService.check_in_library_card(
            db=db,
            session_id=data.session_id,
            library_card_number=data.library_card_number,
            staff_id=current_user.id,
            age_range_override=data.age_range,
        )
        await db.commit()

        # Get patron name if available
        patron_name = None
        if check_in.patron_id:
            from sqlalchemy import select
            from ...models.user import User as UserModel
            result = await db.execute(
                select(UserModel.first_name, UserModel.last_name)
                .where(UserModel.id == check_in.patron_id)
            )
            row = result.one_or_none()
            if row:
                patron_name = f"{row[0]} {row[1]}"

        return _checkin_to_response(check_in, patron_name=patron_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/check-in/walk-in")
@limiter.limit("120/minute")
async def check_in_walk_in(
    request: Request,
    data: WalkInCheckIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Quick-add a walk-in attendee."""
    try:
        check_in = await AttendanceService.check_in_walk_in(
            db=db,
            session_id=data.session_id,
            staff_id=current_user.id,
            guest_name=data.guest_name,
            guest_email=data.guest_email,
            guest_phone=data.guest_phone,
            age_range=data.age_range,
            notes=data.notes,
        )
        await db.commit()
        return _checkin_to_response(check_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/check-in/head-count")
@limiter.limit("60/minute")
async def update_head_count(
    request: Request,
    data: HeadCountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Update head count for large events."""
    try:
        session = await AttendanceService.update_head_count(
            db=db,
            session_id=data.session_id,
            total=data.total,
            by_age=data.by_age,
        )
        await db.commit()
        return _session_to_response(session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/sessions/{session_id}/check-ins")
@limiter.limit("60/minute")
async def get_session_check_ins(
    request: Request,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get all check-ins for a session."""
    session = await AttendanceService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    check_ins = await AttendanceService.get_session_check_ins(db, session_id)

    # Batch load patron names
    patron_ids = [ci.patron_id for ci in check_ins if ci.patron_id]
    patron_names = {}
    if patron_ids:
        from sqlalchemy import select
        from ...models.user import User as UserModel
        result = await db.execute(
            select(UserModel.id, UserModel.first_name, UserModel.last_name)
            .where(UserModel.id.in_(patron_ids))
        )
        for uid, fn, ln in result.all():
            patron_names[uid] = f"{fn} {ln}"

    return [
        _checkin_to_response(ci, patron_name=patron_names.get(ci.patron_id))
        for ci in check_ins
    ]


# ============================================================================
# Survey Distribution
# ============================================================================


@router.post("/sessions/{session_id}/send-surveys")
@limiter.limit("10/minute")
async def send_surveys(
    request: Request,
    session_id: int,
    data: Optional[SurveySendRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Send post-event survey to all attendees with email addresses."""
    try:
        survey_link = data.survey_link if data else None
        result = await AttendanceService.send_surveys(
            db=db,
            session_id=session_id,
            survey_link=survey_link,
        )
        await db.commit()
        logger.info(f"Surveys sent for session {session_id}: {result['total_sent']} sent")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Dashboard & Analytics
# ============================================================================


@router.get("/dashboard")
@limiter.limit("60/minute")
async def get_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get attendance tracking dashboard with today's stats, trends, and recent sessions."""
    return await AttendanceService.get_dashboard(db)


@router.get("/trends")
@limiter.limit("30/minute")
async def get_trends(
    request: Request,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    program_type: Optional[str] = Query(None),
    period_type: str = Query("monthly"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get attendance trends by program type over time."""
    return await AttendanceService.get_trends(
        db=db,
        start_date=start_date,
        end_date=end_date,
        program_type=program_type,
        period_type=period_type,
    )


@router.get("/roi")
@limiter.limit("30/minute")
async def get_roi_report(
    request: Request,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get ROI report showing cost per attendee and program effectiveness."""
    return await AttendanceService.get_roi_report(
        db=db,
        start_date=start_date,
        end_date=end_date,
    )
