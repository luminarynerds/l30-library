# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board dashboard API endpoints.

Provides dashboard-specific data for board members and the board president:
- Attention items needing board action
- Status-by-area cards (governance, administration)
- Recent board activity feed
- President sign-off queue, next meeting, and upcoming timeline

Mounted under the board aggregator at /api/v1/board.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from ....core.database import get_db
from ....models.board.meeting import BoardMeeting
from ....models.board.member import BoardMember, BoardPosition
from ....models.board.minutes import BoardMinutes, MinutesStatus
from ....models.board.public_comment import CommentStatus, PublicComment
from ....models.user import User, UserRole
from ....schemas.board_dashboard import (
    AttentionItem,
    AttentionItemsResponse,
    BoardActivityResponse,
    BoardStatusResponse,
    ChecklistItem,
    NextMeetingResponse,
    SignOffItem,
    SignOffQueueResponse,
    StatusArea,
    StatusEntry,
    UpcomingItem,
    UpcomingResponse,
)
from ..auth import get_current_user

router = APIRouter(prefix="/board/dashboard", tags=["board-dashboard"])


async def _require_board_access(
    current_user: User, db: AsyncSession
) -> None:
    if current_user.role in (
        UserRole.STAFF,
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
        UserRole.DIRECTOR,
    ):
        return
    result = await db.execute(
        select(BoardMember).where(
            BoardMember.user_id == current_user.id,
            BoardMember.is_current == True,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=403, detail="Board member or staff access required"
        )


async def _require_president(
    current_user: User, db: AsyncSession
) -> None:
    if current_user.role in (
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
        UserRole.DIRECTOR,
    ):
        return
    result = await db.execute(
        select(BoardMember).where(
            BoardMember.user_id == current_user.id,
            BoardMember.is_current == True,
            BoardMember.position == BoardPosition.PRESIDENT.value,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=403, detail="Board president or admin access required"
        )


# ---------------------------------------------------------------------------
# GET /board/dashboard/attention
# ---------------------------------------------------------------------------
@router.get("/attention", response_model=AttentionItemsResponse)
async def get_attention_items(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Items needing board attention: pending comments, upcoming meetings, draft minutes."""
    await _require_board_access(current_user, db)

    items: list[AttentionItem] = []
    now = datetime.now(timezone.utc)

    try:
        # Pending public comments
        pending_result = await db.execute(
            select(func.count(PublicComment.id)).where(
                PublicComment.status == CommentStatus.PENDING.value,
            )
        )
        pending_count = pending_result.scalar() or 0
        if pending_count > 0:
            items.append(
                AttentionItem(
                    id="pending-comments",
                    urgency="upcoming",
                    title=f"{pending_count} public comment{'s' if pending_count != 1 else ''} awaiting review",
                    description="Public comments need moderation before the next meeting.",
                    action_label="Review comments",
                    action_url="/board/public-comments?status=pending",
                )
            )

        # Upcoming meetings in next 14 days
        upcoming_result = await db.execute(
            select(BoardMeeting)
            .where(
                BoardMeeting.scheduled_date >= now,
                BoardMeeting.is_cancelled == False,
            )
            .order_by(BoardMeeting.scheduled_date.asc())
            .limit(3)
        )
        for mtg in upcoming_result.scalars().all():
            days_until = (mtg.scheduled_date.replace(tzinfo=timezone.utc) - now).days
            if days_until <= 14:
                urgency = "upcoming" if days_until <= 7 else "routine"
                items.append(
                    AttentionItem(
                        id=f"meeting-{mtg.id}",
                        urgency=urgency,
                        title=mtg.title,
                        description=f"Scheduled in {days_until} day{'s' if days_until != 1 else ''}.",
                        deadline=mtg.scheduled_date.isoformat(),
                        action_label="View meeting",
                        action_url=f"/board/meetings/{mtg.id}",
                    )
                )

        # Draft minutes needing approval
        draft_result = await db.execute(
            select(BoardMinutes).where(
                BoardMinutes.status.in_([
                    MinutesStatus.DRAFT.value,
                    MinutesStatus.UNDER_REVIEW.value,
                ])
            )
        )
        for mins in draft_result.scalars().all():
            urgency = "upcoming" if mins.status == MinutesStatus.UNDER_REVIEW.value else "routine"
            items.append(
                AttentionItem(
                    id=f"minutes-{mins.id}",
                    urgency=urgency,
                    title=f"Minutes pending approval (meeting #{mins.meeting_id})",
                    description=f"Status: {mins.status}",
                    action_label="Review minutes",
                    action_url=f"/board/minutes/{mins.id}",
                )
            )
    except SQLAlchemyError:
        pass

    return AttentionItemsResponse(items=items)


# ---------------------------------------------------------------------------
# GET /board/dashboard/status
# ---------------------------------------------------------------------------
@router.get("/status", response_model=BoardStatusResponse)
async def get_board_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Status-by-area cards for governance and administration."""
    await _require_board_access(current_user, db)

    areas: list[StatusArea] = []

    try:
        # Governance area
        member_result = await db.execute(
            select(func.count(BoardMember.id)).where(
                BoardMember.is_current == True,
            )
        )
        member_count = member_result.scalar() or 0

        meeting_result = await db.execute(
            select(func.count(BoardMeeting.id)).where(
                BoardMeeting.scheduled_date >= datetime.now(timezone.utc),
                BoardMeeting.is_cancelled == False,
            )
        )
        upcoming_meetings = meeting_result.scalar() or 0

        governance_entries = [
            StatusEntry(
                label="Current members",
                value=str(member_count),
                warning=member_count < 3,
            ),
            StatusEntry(
                label="Upcoming meetings",
                value=str(upcoming_meetings),
            ),
        ]
        areas.append(
            StatusArea(title="Governance", icon="gavel", entries=governance_entries)
        )

        # Administration area
        pending_result = await db.execute(
            select(func.count(PublicComment.id)).where(
                PublicComment.status == CommentStatus.PENDING.value,
            )
        )
        pending_comments = pending_result.scalar() or 0

        unapproved_result = await db.execute(
            select(func.count(BoardMinutes.id)).where(
                BoardMinutes.approved == False,
            )
        )
        unapproved_minutes = unapproved_result.scalar() or 0

        admin_entries = [
            StatusEntry(
                label="Pending comments",
                value=str(pending_comments),
                warning=pending_comments > 0,
            ),
            StatusEntry(
                label="Unapproved minutes",
                value=str(unapproved_minutes),
                warning=unapproved_minutes > 0,
            ),
        ]
        areas.append(
            StatusArea(title="Administration", icon="clipboard", entries=admin_entries)
        )
    except SQLAlchemyError:
        pass

    return BoardStatusResponse(areas=areas)


# ---------------------------------------------------------------------------
# GET /board/dashboard/activity
# ---------------------------------------------------------------------------
@router.get("/activity", response_model=BoardActivityResponse)
async def get_board_activity(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recent board activity feed. Returns empty for now."""
    await _require_board_access(current_user, db)
    return BoardActivityResponse(items=[])


# ---------------------------------------------------------------------------
# GET /board/dashboard/president/signoffs
# ---------------------------------------------------------------------------
@router.get("/president/signoffs", response_model=SignOffQueueResponse)
async def get_president_signoffs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Items awaiting board president sign-off."""
    await _require_president(current_user, db)

    items: list[SignOffItem] = []

    try:
        # Minutes under review that need presidential approval
        review_result = await db.execute(
            select(BoardMinutes).where(
                BoardMinutes.status == MinutesStatus.UNDER_REVIEW.value,
                BoardMinutes.approved == False,
            )
        )
        for mins in review_result.scalars().all():
            items.append(
                SignOffItem(
                    id=f"minutes-{mins.id}",
                    title=f"Approve minutes for meeting #{mins.meeting_id}",
                    description="Minutes are under review and ready for approval.",
                    action_label="Review & approve",
                    action_url=f"/board/minutes/{mins.id}",
                )
            )
    except SQLAlchemyError:
        pass

    return SignOffQueueResponse(items=items)


# ---------------------------------------------------------------------------
# GET /board/dashboard/president/next-meeting
# ---------------------------------------------------------------------------
@router.get("/president/next-meeting", response_model=NextMeetingResponse)
async def get_president_next_meeting(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Next meeting details and preparation checklist for the president."""
    await _require_president(current_user, db)

    now = datetime.now(timezone.utc)

    try:
        result = await db.execute(
            select(BoardMeeting)
            .where(
                BoardMeeting.scheduled_date >= now,
                BoardMeeting.is_cancelled == False,
            )
            .order_by(BoardMeeting.scheduled_date.asc())
            .limit(1)
        )
        meeting = result.scalar_one_or_none()
    except SQLAlchemyError:
        meeting = None

    if not meeting:
        raise HTTPException(status_code=404, detail="No upcoming meeting found")

    # Build relative time string
    delta = meeting.scheduled_date.replace(tzinfo=timezone.utc) - now
    days = delta.days
    if days == 0:
        relative = "Today"
    elif days == 1:
        relative = "Tomorrow"
    else:
        relative = f"In {days} days"

    # Check if current user is chairing
    is_chairing = False
    try:
        chair_result = await db.execute(
            select(BoardMember).where(
                BoardMember.user_id == current_user.id,
                BoardMember.is_current == True,
                BoardMember.is_chair == True,
            )
        )
        is_chairing = chair_result.scalar_one_or_none() is not None
    except SQLAlchemyError:
        pass

    # Build preparation checklist
    checklist = [
        ChecklistItem(
            label="Agenda published",
            done=meeting.agenda_published_at is not None,
        ),
        ChecklistItem(
            label="Public notice posted",
            done=meeting.notice_posted_at is not None,
        ),
        ChecklistItem(
            label="Quorum confirmed",
            done=False,
        ),
    ]

    meeting_date = meeting.scheduled_date
    return NextMeetingResponse(
        date=meeting_date.strftime("%Y-%m-%d"),
        time=meeting_date.strftime("%H:%M"),
        location=meeting.location or "TBD",
        is_chairing=is_chairing,
        relative_time=relative,
        checklist=checklist,
    )


# ---------------------------------------------------------------------------
# GET /board/dashboard/president/upcoming
# ---------------------------------------------------------------------------
@router.get("/president/upcoming", response_model=UpcomingResponse)
async def get_president_upcoming(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Future timeline for the board president (expiring terms, upcoming meetings)."""
    await _require_president(current_user, db)

    items: list[UpcomingItem] = []
    now = datetime.now(timezone.utc)

    try:
        # Board members with expiring terms (within 90 days)
        expiring_result = await db.execute(
            select(BoardMember).where(
                BoardMember.is_current == True,
                BoardMember.term_end_date.isnot(None),
            )
        )
        for member in expiring_result.scalars().all():
            end = member.term_end_date.replace(tzinfo=timezone.utc)
            days_left = (end - now).days
            if 0 <= days_left <= 90:
                items.append(
                    UpcomingItem(
                        date=end.strftime("%Y-%m-%d"),
                        title=f"Term expiring: {member.full_name}",
                        note=f"{member.position or 'member'} -- {days_left} days remaining",
                    )
                )
    except SQLAlchemyError:
        pass

    try:
        # Upcoming meetings
        meeting_result = await db.execute(
            select(BoardMeeting)
            .where(
                BoardMeeting.scheduled_date >= now,
                BoardMeeting.is_cancelled == False,
            )
            .order_by(BoardMeeting.scheduled_date.asc())
            .limit(5)
        )
        for mtg in meeting_result.scalars().all():
            items.append(
                UpcomingItem(
                    date=mtg.scheduled_date.strftime("%Y-%m-%d"),
                    title=mtg.title,
                    note=mtg.meeting_type or "regular",
                )
            )
    except SQLAlchemyError:
        pass

    items.sort(key=lambda x: x.date)
    return UpcomingResponse(items=items)
