# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board meeting attendance management endpoints with check-in/out and absence tracking."""

from datetime import datetime, timezone
from typing import Optional
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.exceptions import InternalServerError
from ....core.error_codes import ErrorCode
from ....core.shortcuts import get_or_404

logger = get_logger(__name__)
from ....core.audit_log import audit_log_event
from ....models.board import BoardMeeting, MeetingAttendance, AttendanceStatus
from ....models.board_audit_log import BoardAuditLog, BoardAuditAction
from ....models.user import User, UserRole
from ....schemas.board import AttendanceResponse
from ..auth import get_current_user

router = APIRouter(prefix="/board/meetings", tags=["board-attendance"])


def _check_director_or_staff(current_user: User):
    valid_roles = [UserRole.DIRECTOR, UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN]
    if current_user.role not in valid_roles:
        raise HTTPException(status_code=403, detail="Director or staff access required")


@router.post(
    "/{meeting_id}/attendance/mark-absent",
    response_model=AttendanceResponse,
    status_code=status.HTTP_200_OK
)
async def mark_absent_endpoint(
    meeting_id: int,
    request: Request,
    user_id: int = Query(..., description="User ID to mark absent"),
    excused: bool = Query(False, description="Whether the absence is excused"),
    reason: Optional[str] = Query(None, description="Reason for absence"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a user as absent from a meeting.
    Requires DIRECTOR or STAFF/ADMIN role.
    """
    _check_director_or_staff(current_user)

    # Verify meeting exists and is not cancelled
    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")
    if meeting.is_cancelled:
        raise HTTPException(status_code=400, detail="Cannot modify attendance for a cancelled meeting")

    # Get or create attendance record
    query = select(MeetingAttendance).where(
        and_(
            MeetingAttendance.meeting_id == meeting_id,
            MeetingAttendance.user_id == user_id,
        )
    )
    result = await db.execute(query)
    attendance = result.scalar_one_or_none()

    if not attendance:
        # Create new attendance record with absent status
        attendance = MeetingAttendance(
            meeting_id=meeting_id,
            user_id=user_id,
            created_by_id=current_user.id,
        )
        db.add(attendance)
        # Assign the PK now -- the audit log entry below references
        # attendance.id, which is NULL (and violates entity_id's NOT NULL
        # constraint) until this row is flushed.
        await db.flush()

    # Use transaction for state change
    try:
        now = datetime.now(timezone.utc)
        old_status = attendance.attendance_status
        attendance.attendance_status = AttendanceStatus.EXCUSED.value if excused else AttendanceStatus.ABSENT.value
        attendance.absence_reason = reason
        if excused:
            attendance.excused_by_id = current_user.id
        attendance.updated_at = now

        # Log absence marking to audit trail
        audit_entry = BoardAuditLog(
            user_id=current_user.id,
            action=BoardAuditAction.ATTENDANCE_MARKED_ABSENT,
            entity_type="MeetingAttendance",
            entity_id=attendance.id,
            meeting_id=meeting_id,
            details={
                "old_status": old_status,
                "new_status": attendance.attendance_status,
                "user_id": user_id,
                "excused": excused,
                "reason": reason,
                "marked_at": now.isoformat(),
                "marked_by": f"{current_user.first_name} {current_user.last_name}"
            },
            notes=f"User {user_id} marked {'excused' if excused else 'absent'}: {reason or 'No reason provided'}"
        )
        db.add(audit_entry)
        audit_log_event(
            event_type="BOARD_ATTENDANCE_MARKED_ABSENT",
            user_id=current_user.id,
            email=current_user.email,
            ip_address=str(request.client.host) if request.client else "unknown",
            severity="INFO",
            details={"meeting_id": meeting_id, "entity_type": "MeetingAttendance", "target_user_id": user_id, "excused": excused},
        )

        await db.commit()
        await db.refresh(attendance)
        return attendance
    except Exception:
        await db.rollback()
        logger.exception("Failed to mark absent")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.post(
    "/{meeting_id}/attendance/checkin",
    response_model=AttendanceResponse,
    status_code=status.HTTP_200_OK
)
async def checkin_endpoint(
    meeting_id: int,
    request: Request,
    user_id: int = Query(..., description="User ID to check in"),
    status_value: str = Query("present", pattern="^(present|tardy)$"),
    attended_remotely: bool = Query(False),
    remote_connection_method: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check in a user to a meeting.
    Requires DIRECTOR or STAFF/ADMIN role.
    Attendance tracking with timestamps.
    """
    _check_director_or_staff(current_user)

    # Verify meeting exists and is not cancelled
    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")
    if meeting.is_cancelled:
        raise HTTPException(status_code=400, detail="Cannot check in for a cancelled meeting")

    # Get or create attendance record
    query = select(MeetingAttendance).where(
        and_(
            MeetingAttendance.meeting_id == meeting_id,
            MeetingAttendance.user_id == user_id,
        )
    )
    result = await db.execute(query)
    attendance = result.scalar_one_or_none()

    if not attendance:
        # Create new attendance record
        attendance = MeetingAttendance(
            meeting_id=meeting_id,
            user_id=user_id,
            created_by_id=current_user.id,
        )
        db.add(attendance)
        # Assign the PK now -- the audit log entry below references
        # attendance.id, which is NULL (and violates entity_id's NOT NULL
        # constraint) until this row is flushed.
        await db.flush()

    # Verify not already checked in
    if attendance.checked_in_at:
        raise HTTPException(status_code=400, detail="User already checked in")

    # Use transaction for state change
    try:
        now = datetime.now(timezone.utc)
        attendance.attendance_status = status_value
        attendance.checked_in_at = now
        attendance.attended_remotely = attended_remotely
        if remote_connection_method:
            attendance.remote_connection_method = remote_connection_method
        attendance.updated_at = now

        # Log check-in to audit trail
        audit_entry = BoardAuditLog(
            user_id=current_user.id,
            action=BoardAuditAction.ATTENDANCE_CHECKED_IN,
            entity_type="MeetingAttendance",
            entity_id=attendance.id,
            meeting_id=meeting_id,
            details={
                "attendance_status": status_value,
                "user_id": user_id,
                "checked_in_at": now.isoformat(),
                "attended_remotely": attended_remotely,
                "remote_method": remote_connection_method,
                "checked_in_by": f"{current_user.first_name} {current_user.last_name}"
            },
            notes=f"User {user_id} checked in ({'remote' if attended_remotely else 'in-person'})"
        )
        db.add(audit_entry)
        audit_log_event(
            event_type="BOARD_ATTENDANCE_CHECKED_IN",
            user_id=current_user.id,
            email=current_user.email,
            ip_address=str(request.client.host) if request.client else "unknown",
            severity="INFO",
            details={"meeting_id": meeting_id, "entity_type": "MeetingAttendance", "target_user_id": user_id, "attended_remotely": attended_remotely},
        )

        await db.commit()
        await db.refresh(attendance)
        return attendance
    except Exception:
        await db.rollback()
        logger.exception("Failed to check in")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.post(
    "/{meeting_id}/attendance/checkout",
    response_model=AttendanceResponse,
    status_code=status.HTTP_200_OK
)
async def checkout_endpoint(
    meeting_id: int,
    request: Request,
    user_id: int = Query(..., description="User ID to check out"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check out a user from a meeting.
    Requires DIRECTOR or STAFF/ADMIN role.
    Attendance tracking with timestamps.
    """
    _check_director_or_staff(current_user)

    # Verify meeting exists and is not cancelled
    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")
    if meeting.is_cancelled:
        raise HTTPException(status_code=400, detail="Cannot check out from a cancelled meeting")

    # Get attendance record
    query = select(MeetingAttendance).where(
        and_(
            MeetingAttendance.meeting_id == meeting_id,
            MeetingAttendance.user_id == user_id,
        )
    )
    result = await db.execute(query)
    attendance = result.scalar_one_or_none()

    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    # Verify already checked in
    if not attendance.checked_in_at:
        raise HTTPException(status_code=400, detail="User has not checked in yet")

    # Verify not already checked out
    if attendance.checked_out_at:
        raise HTTPException(status_code=400, detail="User already checked out")

    # Use transaction for state change
    try:
        now = datetime.now(timezone.utc)
        attendance.checked_out_at = now

        # Calculate session duration
        session_duration_minutes = 0
        if attendance.checked_in_at:
            session_duration_seconds = (now - attendance.checked_in_at).total_seconds()
            session_duration_minutes = int(session_duration_seconds / 60)

        # If was present, mark as left early
        old_status = attendance.attendance_status
        if attendance.attendance_status == AttendanceStatus.PRESENT.value:
            attendance.attendance_status = AttendanceStatus.LEFT_EARLY.value
        attendance.updated_at = now

        # Log check-out to audit trail
        audit_entry = BoardAuditLog(
            user_id=current_user.id,
            action=BoardAuditAction.ATTENDANCE_CHECKED_OUT,
            entity_type="MeetingAttendance",
            entity_id=attendance.id,
            meeting_id=meeting_id,
            details={
                "old_status": old_status,
                "new_status": attendance.attendance_status,
                "user_id": user_id,
                "checked_in_at": attendance.checked_in_at.isoformat() if attendance.checked_in_at else None,
                "checked_out_at": now.isoformat(),
                "session_duration_minutes": session_duration_minutes,
                "checked_out_by": f"{current_user.first_name} {current_user.last_name}"
            },
            notes=f"User {user_id} checked out (session: {session_duration_minutes} min)"
        )
        db.add(audit_entry)
        audit_log_event(
            event_type="BOARD_ATTENDANCE_CHECKED_OUT",
            user_id=current_user.id,
            email=current_user.email,
            ip_address=str(request.client.host) if request.client else "unknown",
            severity="INFO",
            details={"meeting_id": meeting_id, "entity_type": "MeetingAttendance", "target_user_id": user_id, "session_duration_minutes": session_duration_minutes},
        )

        await db.commit()
        await db.refresh(attendance)
        return attendance
    except Exception:
        await db.rollback()
        logger.exception("Failed to check out")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.post("/{meeting_id}/attendance/rsvp")
async def submit_rsvp(
    meeting_id: int,
    rsvp_status: str = Query(..., description="attending, not_attending, tentative"),
    rsvp_notes: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit or update RSVP for a meeting."""
    from ....models.board import BoardMeeting
    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")
    if meeting.is_cancelled:
        raise HTTPException(status_code=400, detail="Cannot RSVP to a cancelled meeting")

    # Check valid status
    valid_statuses = ["attending", "not_attending", "tentative"]
    if rsvp_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid RSVP status. Must be one of: {', '.join(valid_statuses)}")

    # Find or create attendance record
    result = await db.execute(
        select(MeetingAttendance).where(
            MeetingAttendance.meeting_id == meeting_id,
            MeetingAttendance.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if record:
        record.rsvp_status = rsvp_status
        record.rsvp_at = now
        record.rsvp_notes = rsvp_notes
        record.updated_at = now
    else:
        record = MeetingAttendance(
            meeting_id=meeting_id,
            user_id=current_user.id,
            rsvp_status=rsvp_status,
            rsvp_at=now,
            rsvp_notes=rsvp_notes,
        )
        db.add(record)

    await db.commit()
    await db.refresh(record)
    return {"message": f"RSVP recorded: {rsvp_status}", "rsvp_status": rsvp_status}


@router.get("/{meeting_id}/attendance/rsvps")
async def get_meeting_rsvps(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all RSVPs for a meeting (staff+)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    result = await db.execute(
        select(MeetingAttendance)
        .where(MeetingAttendance.meeting_id == meeting_id)
        .where(MeetingAttendance.rsvp_status.isnot(None))
    )
    records = result.scalars().all()
    return [
        {
            "user_id": r.user_id,
            "rsvp_status": r.rsvp_status,
            "rsvp_at": r.rsvp_at.isoformat() if r.rsvp_at else None,
            "rsvp_notes": r.rsvp_notes,
        }
        for r in records
    ]
