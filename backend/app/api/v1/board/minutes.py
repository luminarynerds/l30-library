# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board meeting minutes management API endpoints with lifecycle and approval workflow."""

from datetime import datetime, timezone
from typing import List, Optional
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.exceptions import InternalServerError
from ....core.error_codes import ErrorCode
from ....core.shortcuts import get_or_404

logger = get_logger(__name__)
from ....models.board import BoardMeeting, BoardMinutes, MinutesStatus, BoardVote
from ....models.board_audit_log import BoardAuditLog, BoardAuditAction
from ....models.user import User, UserRole
from ....schemas.board import (BoardMinutesCreate, BoardMinutesResponse,
                              BoardMinutesUpdate, MinutesAmendmentCreate,
                              MinutesAmendmentResponse)
from ..auth import get_current_user

router = APIRouter(prefix="/board/meetings", tags=["board-minutes"])


# ============ Authenticated Minutes Management ============

async def _lock_meeting_votes(db, meeting_id, user_id):
    result = await db.execute(
        select(BoardVote).where(BoardVote.meeting_id == meeting_id, BoardVote.locked_at.is_(None))
    )
    now = datetime.now(timezone.utc)
    for vote in result.scalars().all():
        vote.locked_at = now
        db.add(BoardAuditLog(user_id=user_id, action=BoardAuditAction.VOTE_LOCKED,
            entity_type="BoardVote", entity_id=vote.id, meeting_id=meeting_id,
            details={"reason": "meeting_adjourned"}))
    await db.flush()



@router.post("/{meeting_id}/minutes", response_model=BoardMinutesResponse)
async def create_minutes(
    meeting_id: int,
    minutes: BoardMinutesCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update meeting minutes (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    # Verify meeting exists and is not cancelled
    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")
    if meeting.is_cancelled:
        raise HTTPException(
            status_code=400, detail="Cannot create minutes for a cancelled meeting"
        )

    # Check if minutes already exist
    result = await db.execute(
        select(BoardMinutes).where(BoardMinutes.meeting_id == meeting_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Cannot modify approved minutes
        if existing.approved:
            raise HTTPException(
                status_code=400,
                detail="Cannot modify approved minutes. Create an amendment instead.",
            )
        for key, value in minutes.model_dump(exclude_unset=True).items():
            if key != "meeting_id":
                setattr(existing, key, value)
        existing.updated_at = datetime.now(timezone.utc)
        if meeting.end_time:
            await _lock_meeting_votes(db, meeting_id, current_user.id)
        await db.commit()
        await db.refresh(existing)
        return existing

    # Create new minutes with meeting_id from path parameter
    minutes_data = minutes.model_dump(exclude={"meeting_id"} if hasattr(minutes, "meeting_id") else set())
    db_minutes = BoardMinutes(
        **minutes_data,
        meeting_id=meeting_id,
        created_by_id=current_user.id,
    )
    db.add(db_minutes)
    await db.commit()
    if meeting.end_time:
        await _lock_meeting_votes(db, meeting_id, current_user.id)
    await db.refresh(db_minutes)
    return db_minutes


@router.get("/{meeting_id}/minutes", response_model=Optional[BoardMinutesResponse])
async def get_meeting_minutes(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get minutes for a specific meeting (staff/admin).
    Endpoint 8: GET /api/v1/board/meetings/{id}/minutes
    Returns full minutes (including draft, unapproved, and sealed
    executive-session content) for this meeting. Public, approved,
    non-sealed minutes are served separately as a PDF by
    /api/v1/board/public/meetings/{id}/minutes.
    """
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    # Verify meeting exists
    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")

    # Get minutes if they exist
    query = select(BoardMinutes).where(BoardMinutes.meeting_id == meeting_id)
    result = await db.execute(query)
    minutes = result.scalar_one_or_none()

    if not minutes:
        raise HTTPException(status_code=404, detail="Minutes not found for this meeting")

    return minutes


@router.post("/{meeting_id}/minutes/approve", response_model=BoardMinutesResponse, status_code=status.HTTP_200_OK)
async def approve_minutes(
    meeting_id: int,
    vote_result: str = Query(..., description="Vote result (e.g., Approved 5-0)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve meeting minutes (admin/director with separation of duties).
    Endpoint 9: POST /api/v1/board/meetings/{id}/minutes/approve
    Minutes approval workflow with transaction support.
    """
    # Verify ADMIN, SUPER_ADMIN, or DIRECTOR role
    valid_roles = [UserRole.DIRECTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN]
    if current_user.role not in valid_roles:
        raise HTTPException(status_code=403, detail="Director or admin access required for approval")

    # Get minutes by meeting_id (minutes table has unique meeting_id)
    query = select(BoardMinutes).where(BoardMinutes.meeting_id == meeting_id)
    result = await db.execute(query)
    db_minutes = result.scalar_one_or_none()

    if not db_minutes:
        raise HTTPException(status_code=404, detail="Minutes not found for this meeting")

    # Prevent re-approval
    if db_minutes.approved:
        raise HTTPException(
            status_code=400, detail="Minutes have already been approved"
        )

    # Separation of duties - approver should not be the creator
    if db_minutes.created_by_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Minutes cannot be approved by the same person who created them",
        )

    # Use transaction for approval
    try:
        now = datetime.now(timezone.utc)
        db_minutes.approved = True
        db_minutes.approved_at = now
        db_minutes.approved_by_id = current_user.id
        db_minutes.approval_vote_result = vote_result
        db_minutes.status = MinutesStatus.APPROVED.value

        # Log minutes approval to audit trail
        audit_entry = BoardAuditLog(
            user_id=current_user.id,
            action=BoardAuditAction.MINUTES_APPROVED,
            entity_type="BoardMinutes",
            entity_id=db_minutes.id,
            meeting_id=meeting_id,
            details={
                "vote_result": vote_result,
                "approved_at": now.isoformat(),
                "approved_by": f"{current_user.first_name} {current_user.last_name}",
                "created_by_id": db_minutes.created_by_id,
                "meeting_title": db_minutes.meeting.title if db_minutes.meeting else "Unknown"
            },
            notes=f"Minutes approved with vote: {vote_result}"
        )
        db.add(audit_entry)

        await db.commit()
        await db.refresh(db_minutes)
        return db_minutes
    except Exception:
        await db.rollback()
        logger.exception("Failed to approve minutes")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


# ============ Minutes Amendments ============


@router.post("/{meeting_id}/minutes/amendments", response_model=MinutesAmendmentResponse, status_code=201)
async def create_minutes_amendment(
    meeting_id: int,
    body: MinutesAmendmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an amendment to approved minutes (director/admin with separation of duties)."""
    valid_roles = [UserRole.DIRECTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN]
    if current_user.role not in valid_roles:
        raise HTTPException(status_code=403, detail="Director or admin access required")

    query = select(BoardMinutes).where(BoardMinutes.meeting_id == meeting_id)
    result = await db.execute(query)
    db_minutes = result.scalar_one_or_none()

    if not db_minutes:
        raise HTTPException(status_code=404, detail="Minutes not found for this meeting")

    if not db_minutes.approved:
        raise HTTPException(status_code=400, detail="Only approved minutes can be amended")

    from ....models.board.minutes_amendment import BoardMinutesAmendment

    now = datetime.now(timezone.utc)
    amendment = BoardMinutesAmendment(
        minutes_id=db_minutes.id,
        amendment_text=body.amendment_text,
        section_title=body.section_title,
        original_text=body.original_text,
        amendment_reason=body.amendment_reason,
        amendment_vote_result=body.amendment_vote_result,
        approved_at=now,
        approved_by_id=current_user.id,
        created_by_id=current_user.id,
    )
    db.add(amendment)

    audit_entry = BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.MINUTES_UPDATED,
        entity_type="BoardMinutesAmendment",
        entity_id=0,
        meeting_id=meeting_id,
        details={
            "amendment_reason": body.amendment_reason,
            "vote_result": body.amendment_vote_result,
            "section": body.section_title,
            "amended_by": f"{current_user.first_name} {current_user.last_name}",
        },
    )
    db.add(audit_entry)

    await db.commit()
    await db.refresh(amendment)
    audit_entry.entity_id = amendment.id
    await db.commit()

    return amendment


@router.get("/{meeting_id}/minutes/amendments", response_model=List[MinutesAmendmentResponse])
async def list_minutes_amendments(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List amendments to meeting minutes (public)."""
    from ....models.board.minutes_amendment import BoardMinutesAmendment

    query = select(BoardMinutes).where(BoardMinutes.meeting_id == meeting_id)
    result = await db.execute(query)
    db_minutes = result.scalar_one_or_none()

    if not db_minutes:
        raise HTTPException(status_code=404, detail="Minutes not found for this meeting")

    amendments_result = await db.execute(
        select(BoardMinutesAmendment)
        .where(BoardMinutesAmendment.minutes_id == db_minutes.id)
        .order_by(BoardMinutesAmendment.created_at.asc())
    )
    return amendments_result.scalars().all()
