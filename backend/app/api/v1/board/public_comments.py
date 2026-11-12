# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board public-comments API endpoints.

Covers:
- Public-facing comment-period listing and comment submission
- Staff/admin moderation, read-into-record, staff response, update, delete
- Comment period CRUD and start/end markers
- Speaker registration and start/stop speaking timers

Mounted under the board aggregator at /api/v1/board.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.board import BoardMeeting
from ....models.board.public_comment import (
    CommentStatus,
    CommentType,
    PublicComment,
    PublicCommentPeriod,
)
from ....models.user import User
from ....schemas.board import (
    CommentPeriodResponse,
    CommentPeriodUpdate,
    PublicCommentModerate,
    PublicCommentReadIntoRecord,
    PublicCommentResponse,
    PublicCommentStaffResponse,
    PublicCommentUpdate,
)
from ....services.board_public_comments_service import BoardPublicCommentsService
from ..dependencies import require_admin, require_staff

router = APIRouter(tags=["board-public-comments"])


# -----------------------------------------------------------------------------
# Router-local request body (path-param meeting_id, so body omits it)
# -----------------------------------------------------------------------------


class PublicCommentSubmitBody(BaseModel):

    agenda_item_id: Optional[int] = None
    commenter_name: str = Field(..., max_length=200)
    commenter_email: Optional[str] = Field(None, max_length=255)
    commenter_phone: Optional[str] = Field(None, max_length=50)
    organization: Optional[str] = Field(None, max_length=200)
    is_resident: Optional[bool] = None
    subject: Optional[str] = Field(None, max_length=500)
    comment_text: str = Field(..., max_length=5000)


class CommentPeriodCreateBody(BaseModel):

    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    instructions: Optional[str] = None
    opens_at: datetime
    closes_at: datetime
    scheduled_start_time: Optional[datetime] = None
    max_comments: Optional[int] = None
    max_speakers: Optional[int] = None
    time_per_speaker_seconds: int = 180
    allow_written: bool = True
    allow_in_person: bool = True
    allow_virtual: bool = True
    require_advance_signup: bool = False
    agenda_item_id: Optional[int] = None


# =============================================================================
# Helpers
# =============================================================================


def _client_ip(request: Request) -> Optional[str]:
    if request.client:
        return request.client.host
    return None


def _user_agent(request: Request) -> Optional[str]:
    return request.headers.get("user-agent")


async def _get_comment(db: AsyncSession, comment_id: int) -> PublicComment:
    return await get_or_404(db, PublicComment, comment_id, "Public comment not found")


async def _get_period(db: AsyncSession, period_id: int) -> PublicCommentPeriod:
    return await get_or_404(
        db, PublicCommentPeriod, period_id, "Comment period not found"
    )


# =============================================================================
# Public (unauthenticated) endpoints
# =============================================================================


@router.get(
    "/board/meetings/{meeting_id}/comment-periods",
    response_model=List[CommentPeriodResponse],
)
async def get_meeting_comment_periods(
    meeting_id: int,
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """List comment periods for a meeting (public)."""
    await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")

    query = select(PublicCommentPeriod).where(
        PublicCommentPeriod.meeting_id == meeting_id
    )
    if active_only:
        query = query.where(PublicCommentPeriod.is_active == True)  # noqa: E712
    query = query.order_by(PublicCommentPeriod.opens_at.asc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get(
    "/board/comment-periods/active",
    response_model=List[CommentPeriodResponse],
)
async def get_active_comment_periods(
    db: AsyncSession = Depends(get_db),
):
    """List all currently-open comment periods across all meetings (public)."""
    now = datetime.now(timezone.utc)
    query = (
        select(PublicCommentPeriod)
        .where(
            PublicCommentPeriod.is_active == True,  # noqa: E712
            PublicCommentPeriod.opens_at <= now,
            PublicCommentPeriod.closes_at >= now,
        )
        .order_by(PublicCommentPeriod.closes_at.asc())
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/board/meetings/{meeting_id}/public-comments/submit",
    response_model=PublicCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_public_comment(
    meeting_id: int,
    payload: PublicCommentSubmitBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Submit a public comment for a meeting (public endpoint)."""
    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")
    if meeting.is_cancelled:
        raise HTTPException(
            status_code=400,
            detail="Cannot submit a comment for a cancelled meeting",
        )

    # Rate limit: max 5 comments per IP per hour
    from sqlalchemy import func as sa_func
    client_ip = _client_ip(request)
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    rate_result = await db.execute(
        select(sa_func.count(PublicComment.id)).where(
            PublicComment.ip_address == client_ip,
            PublicComment.created_at >= one_hour_ago,
        )
    )
    comment_count = rate_result.scalar() or 0
    if comment_count >= 5:
        raise HTTPException(
            status_code=429,
            detail="Too many comments. Please try again later."
        )

    comment = PublicComment(
        meeting_id=meeting_id,
        agenda_item_id=payload.agenda_item_id,
        comment_type=CommentType.WRITTEN.value,
        status=CommentStatus.PENDING.value,
        commenter_name=payload.commenter_name,
        commenter_email=payload.commenter_email,
        commenter_phone=payload.commenter_phone,
        organization=payload.organization,
        is_resident=payload.is_resident,
        subject=payload.subject,
        comment_text=payload.comment_text,
        ip_address=_client_ip(request),
    )

    comment = await BoardPublicCommentsService.submit_comment(
        db=db,
        comment=comment,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    await db.commit()
    await db.refresh(comment)
    return comment


# =============================================================================
# Staff/admin comment management
# =============================================================================


@router.get(
    "/board/meetings/{meeting_id}/public-comments",
    response_model=List[PublicCommentResponse],
)
async def list_meeting_comments(
    meeting_id: int,
    status_filter: Optional[str] = Query(None),
    comment_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List all public comments for a meeting (staff/admin)."""
    await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")

    query = select(PublicComment).where(PublicComment.meeting_id == meeting_id)
    if status_filter:
        query = query.where(PublicComment.status == status_filter)
    if comment_type:
        query = query.where(PublicComment.comment_type == comment_type)
    query = query.order_by(PublicComment.submitted_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get(
    "/board/public-comments/pending",
    response_model=List[PublicCommentResponse],
)
async def list_pending_comments(
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get all pending comments across meetings (staff/admin)."""
    query = (
        select(PublicComment)
        .where(PublicComment.status == CommentStatus.PENDING.value)
        .order_by(PublicComment.submitted_at.asc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/board/public-comments/{comment_id}/moderate",
    response_model=PublicCommentResponse,
)
async def moderate_comment(
    comment_id: int,
    payload: PublicCommentModerate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Approve or reject a pending public comment."""
    comment = await _get_comment(db, comment_id)

    if comment.status not in (
        CommentStatus.PENDING.value,
        CommentStatus.APPROVED.value,
        CommentStatus.REJECTED.value,
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot moderate comment with status '{comment.status}'",
        )

    comment = await BoardPublicCommentsService.moderate(
        db=db,
        comment=comment,
        status_value=payload.status,
        moderator_id=current_user.id,
        moderation_notes=payload.moderation_notes,
        rejection_reason=payload.rejection_reason,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    await db.commit()
    await db.refresh(comment)
    return comment


@router.post(
    "/board/public-comments/{comment_id}/read-into-record",
    response_model=PublicCommentResponse,
)
async def read_comment_into_record(
    comment_id: int,
    payload: PublicCommentReadIntoRecord,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark a comment as read into the meeting record."""
    comment = await _get_comment(db, comment_id)

    if comment.status not in (
        CommentStatus.APPROVED.value,
        CommentStatus.READ_INTO_RECORD.value,
    ):
        raise HTTPException(
            status_code=400,
            detail="Only approved comments can be read into the record",
        )

    comment = await BoardPublicCommentsService.read_into_record(
        db=db,
        comment=comment,
        reader_id=current_user.id,
        reading_notes=payload.reading_notes,
        time_allocated_seconds=payload.time_allocated_seconds,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    await db.commit()
    await db.refresh(comment)
    return comment


@router.post(
    "/board/public-comments/{comment_id}/staff-response",
    response_model=PublicCommentResponse,
)
async def add_staff_response(
    comment_id: int,
    payload: PublicCommentStaffResponse,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Attach an official staff response to a public comment."""
    comment = await _get_comment(db, comment_id)

    now = datetime.now(timezone.utc)
    comment.staff_response = payload.staff_response
    comment.staff_response_by_id = current_user.id
    comment.staff_response_at = now
    comment.updated_at = now

    await db.commit()
    await db.refresh(comment)
    return comment


@router.put(
    "/board/public-comments/{comment_id}",
    response_model=PublicCommentResponse,
)
async def update_comment(
    comment_id: int,
    payload: PublicCommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update editable fields on a public comment (staff/admin)."""
    comment = await _get_comment(db, comment_id)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(comment, field, value)
    comment.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(comment)
    return comment


@router.delete("/board/public-comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a public comment (admin only)."""
    comment = await _get_comment(db, comment_id)
    await db.delete(comment)
    await db.commit()
    return {"message": "Public comment deleted"}


# =============================================================================
# Speaker registration and timing
# =============================================================================


@router.post(
    "/board/meetings/{meeting_id}/public-comments/register-speaker",
    response_model=PublicCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_speaker(
    meeting_id: int,
    payload: PublicCommentSubmitBody,
    request: Request,
    comment_type: str = Query("in_person"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Register an in-person or virtual speaker for public comment."""
    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")
    if meeting.is_cancelled:
        raise HTTPException(
            status_code=400,
            detail="Cannot register a speaker for a cancelled meeting",
        )

    if comment_type not in (CommentType.IN_PERSON.value, CommentType.VIRTUAL.value):
        raise HTTPException(
            status_code=400,
            detail="comment_type must be 'in_person' or 'virtual'",
        )

    # Determine speaker order as next-highest for this meeting/type
    order_query = select(PublicComment).where(
        PublicComment.meeting_id == meeting_id,
        PublicComment.comment_type == comment_type,
    )
    existing = (await db.execute(order_query)).scalars().all()
    max_order = 0
    for existing_comment in existing:
        if existing_comment.speaker_order and existing_comment.speaker_order > max_order:
            max_order = existing_comment.speaker_order

    comment = PublicComment(
        meeting_id=meeting_id,
        agenda_item_id=payload.agenda_item_id,
        comment_type=comment_type,
        status=CommentStatus.APPROVED.value,
        commenter_name=payload.commenter_name,
        commenter_email=payload.commenter_email,
        commenter_phone=payload.commenter_phone,
        organization=payload.organization,
        is_resident=payload.is_resident,
        subject=payload.subject,
        comment_text=payload.comment_text,
        speaker_order=max_order + 1,
        ip_address=_client_ip(request),
        moderated_by_id=current_user.id,
        moderated_at=datetime.now(timezone.utc),
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


@router.post("/board/public-comments/{comment_id}/start-speaking")
async def start_speaking(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark a speaker's actual start time."""
    comment = await _get_comment(db, comment_id)
    start = await BoardPublicCommentsService.start_speaking(db, comment)
    await db.commit()
    return {
        "message": "Speaker start recorded",
        "start_time": start.isoformat(),
    }


@router.post("/board/public-comments/{comment_id}/stop-speaking")
async def stop_speaking(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark a speaker's actual end time and compute duration."""
    comment = await _get_comment(db, comment_id)
    if not comment.actual_start_time:
        raise HTTPException(
            status_code=400,
            detail="Speaker has not started — cannot stop",
        )
    end, duration = await BoardPublicCommentsService.stop_speaking(db, comment)
    await db.commit()
    return {
        "message": "Speaker end recorded",
        "end_time": end.isoformat(),
        "duration_seconds": duration,
    }


# =============================================================================
# Comment period management
# =============================================================================


@router.post(
    "/board/meetings/{meeting_id}/comment-periods",
    response_model=CommentPeriodResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment_period(
    meeting_id: int,
    payload: CommentPeriodCreateBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a comment period for a meeting."""
    await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")

    data = payload.model_dump()
    data["meeting_id"] = meeting_id
    period = PublicCommentPeriod(**data, created_by_id=current_user.id)
    db.add(period)
    await db.commit()
    await db.refresh(period)
    return period


@router.put(
    "/board/comment-periods/{period_id}",
    response_model=CommentPeriodResponse,
)
async def update_comment_period(
    period_id: int,
    payload: CommentPeriodUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a comment period (staff/admin)."""
    period = await _get_period(db, period_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(period, field, value)
    period.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(period)
    return period


@router.post("/board/comment-periods/{period_id}/start")
async def start_comment_period(
    period_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark actual start time of a comment period during meeting."""
    period = await _get_period(db, period_id)
    start = await BoardPublicCommentsService.start_period(db, period)
    await db.commit()
    return {
        "message": "Comment period started",
        "start_time": start.isoformat(),
    }


@router.post("/board/comment-periods/{period_id}/end")
async def end_comment_period(
    period_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark actual end time of a comment period during meeting."""
    period = await _get_period(db, period_id)
    end = await BoardPublicCommentsService.end_period(db, period)
    await db.commit()
    return {
        "message": "Comment period ended",
        "end_time": end.isoformat(),
    }


@router.delete("/board/comment-periods/{period_id}")
async def delete_comment_period(
    period_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a comment period (admin only)."""
    period = await _get_period(db, period_id)
    await db.delete(period)
    await db.commit()
    return {"message": "Comment period deleted"}
