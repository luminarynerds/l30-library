# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board PDF export API endpoints - agenda, minutes, notice, vote record, and board packet PDFs."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.board import (
    BoardMeeting,
    BoardMember,
    BoardMeetingBrief,
    BoardVote,
    BoardVoteCast,
    MeetingActionItem,
)
from ....models.user import User, UserRole
from ....services.board_pdf import (
    generate_meeting_agenda_pdf,
    generate_meeting_minutes_pdf,
    generate_public_notice_pdf,
    generate_vote_record_pdf,
    generate_board_packet_pdf,
)
from ....services.board_pdf_print import generate_print_friendly_board_packet_pdf
from ....services.pdf_tagging_service import tag_pdf
from ..auth import get_current_user

router = APIRouter(tags=["board-pdf-exports"])


# ============ Meeting Agenda PDF ============


@router.get("/board/meetings/{meeting_id}/agenda/pdf")
async def export_meeting_agenda_pdf(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Export meeting agenda as PDF.

    This endpoint is publicly accessible for transparency.
    """
    # Get meeting with agenda items
    result = await db.execute(
        select(BoardMeeting)
        .options(selectinload(BoardMeeting.agenda_items))
        .where(BoardMeeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Sort agenda items by sort_order
    agenda_items = sorted(meeting.agenda_items, key=lambda x: x.sort_order)

    # Get board members for packet
    members_result = await db.execute(
        select(BoardMember).where(BoardMember.is_current == True)
    )
    members = members_result.scalars().all()
    board_members = [
        {"name": f"{m.full_name}", "position": m.position, "email": m.public_email}
        for m in members
    ]

    # Generate PDF
    pdf_bytes = generate_meeting_agenda_pdf(
        meeting=meeting,
        agenda_items=agenda_items,
        board_members=board_members,
    )

    # Create filename
    meeting_date = meeting.scheduled_date.strftime("%Y-%m-%d") if meeting.scheduled_date else "draft"
    filename = f"board-agenda-{meeting_date}.pdf"

    pdf_bytes = tag_pdf(pdf_bytes, title=filename.replace(".pdf", ""))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ============ Meeting Minutes PDF ============


@router.get("/board/meetings/{meeting_id}/minutes/pdf")
async def export_meeting_minutes_pdf(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Export meeting minutes as PDF.

    Minutes must be approved or published to be exported.
    """
    # Get meeting with minutes and agenda items
    result = await db.execute(
        select(BoardMeeting)
        .options(
            selectinload(BoardMeeting.minutes),
            selectinload(BoardMeeting.agenda_items)
        )
        .where(BoardMeeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting.minutes:
        raise HTTPException(status_code=404, detail="Minutes not found for this meeting")

    # Check if minutes are ready for export (approved or published)
    if meeting.minutes.status not in ["approved", "published", "draft"]:
        raise HTTPException(
            status_code=400,
            detail="Minutes must be at least in draft status to export"
        )

    # Sort agenda items by sort_order
    agenda_items = sorted(meeting.agenda_items, key=lambda x: x.sort_order)

    # Generate PDF
    pdf_bytes = generate_meeting_minutes_pdf(
        meeting=meeting,
        minutes=meeting.minutes,
        agenda_items=agenda_items,
    )

    # Create filename
    meeting_date = meeting.scheduled_date.strftime("%Y-%m-%d") if meeting.scheduled_date else "draft"
    status_suffix = f"-{meeting.minutes.status}" if meeting.minutes.status != "published" else ""
    filename = f"board-minutes-{meeting_date}{status_suffix}.pdf"

    pdf_bytes = tag_pdf(pdf_bytes, title=filename.replace(".pdf", ""))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ============ Public Notice PDF ============


@router.get("/board/meetings/{meeting_id}/notice/pdf")
async def export_public_notice_pdf(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Export public meeting notice as PDF for posting.

    This endpoint is publicly accessible.
    """
    # Get meeting with agenda items
    result = await db.execute(
        select(BoardMeeting)
        .options(selectinload(BoardMeeting.agenda_items))
        .where(BoardMeeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Sort agenda items by sort_order
    agenda_items = sorted(meeting.agenda_items, key=lambda x: x.sort_order)

    # Generate PDF
    pdf_bytes = generate_public_notice_pdf(
        meeting=meeting,
        agenda_items=agenda_items,
        posting_date=datetime.now(timezone.utc),
    )

    # Create filename
    meeting_date = meeting.scheduled_date.strftime("%Y-%m-%d") if meeting.scheduled_date else "draft"
    filename = f"public-notice-{meeting_date}.pdf"

    pdf_bytes = tag_pdf(pdf_bytes, title=filename.replace(".pdf", ""))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ============ Vote Record PDF ============


@router.get("/board/votes/{vote_id}/pdf")
async def export_vote_record_pdf(
    vote_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export vote record as PDF.

    Requires authentication. Only closed votes can be exported.
    """
    # Get vote with votes cast
    result = await db.execute(
        select(BoardVote)
        .options(
            selectinload(BoardVote.votes_cast).selectinload(BoardVoteCast.board_member),
            selectinload(BoardVote.meeting)
        )
        .where(BoardVote.id == vote_id)
    )
    vote = result.scalar_one_or_none()
    if not vote:
        raise HTTPException(status_code=404, detail="Vote not found")

    if vote.status != "closed":
        raise HTTPException(
            status_code=400,
            detail="Only closed votes can be exported as PDF"
        )

    # Generate PDF
    pdf_bytes = generate_vote_record_pdf(
        vote=vote,
        votes_cast=vote.votes_cast,
    )

    # Create filename
    vote_date = vote.closes_at.strftime("%Y-%m-%d") if vote.closes_at else "record"
    safe_title = "".join(c for c in vote.title[:30] if c.isalnum() or c in " -_").strip().replace(" ", "-")
    filename = f"vote-record-{safe_title}-{vote_date}.pdf"

    pdf_bytes = tag_pdf(pdf_bytes, title=filename.replace(".pdf", ""))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ============ Board Packet PDF ============


@router.get("/board/meetings/{meeting_id}/packet/pdf")
async def export_board_packet_pdf(
    meeting_id: int,
    include_previous_minutes: bool = Query(True, description="Include previous meeting minutes"),
    include_action_items: bool = Query(True, description="Include outstanding action items"),
    include_brief: bool = Query(True, description="Include AI meeting brief if available"),
    print_friendly: bool = Query(False, description="Print-optimized layout with TOC and section dividers"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export comprehensive board packet as PDF.

    Includes agenda, board directory, previous minutes, pending votes,
    action items, and meeting brief. Requires authentication.
    """
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        # Check if user is a current board member
        member_result = await db.execute(
            select(BoardMember).where(
                BoardMember.user_id == current_user.id, BoardMember.is_current == True
            )
        )
        if not member_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Staff or board member access required")

    # Get meeting with all related data
    result = await db.execute(
        select(BoardMeeting)
        .options(
            selectinload(BoardMeeting.agenda_items),
            selectinload(BoardMeeting.action_items),
        )
        .where(BoardMeeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Sort agenda items
    agenda_items = sorted(meeting.agenda_items, key=lambda x: x.sort_order)

    # Get board members
    members_result = await db.execute(
        select(BoardMember).where(BoardMember.is_current == True)
    )
    members = members_result.scalars().all()
    board_members = [
        {
            "name": m.full_name,
            "position": m.position,
            "email": m.public_email,
            "term_end": m.term_end_date.strftime("%B %Y") if m.term_end_date else None
        }
        for m in members
    ]

    # Get previous meeting minutes if requested
    previous_minutes = None
    if include_previous_minutes:
        prev_meeting_result = await db.execute(
            select(BoardMeeting)
            .options(selectinload(BoardMeeting.minutes))
            .where(
                BoardMeeting.scheduled_date < meeting.scheduled_date,
                BoardMeeting.is_cancelled == False
            )
            .order_by(BoardMeeting.scheduled_date.desc())
            .limit(1)
        )
        prev_meeting = prev_meeting_result.scalar_one_or_none()
        if prev_meeting and prev_meeting.minutes:
            previous_minutes = prev_meeting.minutes

    # Get pending votes for this meeting
    votes_result = await db.execute(
        select(BoardVote).where(
            BoardVote.meeting_id == meeting_id,
            BoardVote.status.in_(["upcoming", "open"])
        )
    )
    pending_votes = votes_result.scalars().all()

    # Get action items if requested
    action_items_list = None
    if include_action_items:
        action_items_result = await db.execute(
            select(MeetingActionItem)
            .options(selectinload(MeetingActionItem.assigned_to))
            .where(MeetingActionItem.status.in_(["not_started", "in_progress"]))
            .order_by(MeetingActionItem.due_date)
            .limit(20)
        )
        items = action_items_result.scalars().all()
        action_items_list = [
            {
                "title": item.title,
                "assigned_to": f"{item.assigned_to.first_name} {item.assigned_to.last_name}" if item.assigned_to else "Unassigned",
                "due_date": item.due_date.strftime("%m/%d/%Y") if item.due_date else "No due date",
                "status": item.status,
            }
            for item in items
        ]

    # Get meeting brief if requested and available
    brief_content = None
    if include_brief:
        brief_result = await db.execute(
            select(BoardMeetingBrief).where(
                BoardMeetingBrief.meeting_id == meeting_id,
                BoardMeetingBrief.status == "completed"
            )
        )
        brief = brief_result.scalar_one_or_none()
        if brief and brief.executive_summary:
            brief_content = brief.executive_summary
            if brief.recommended_prep:
                brief_content += f"\n\nRecommended Preparation:\n{brief.recommended_prep}"

    # Generate PDF
    gen_args = dict(
        meeting=meeting,
        agenda_items=agenda_items,
        board_members=board_members,
        previous_minutes=previous_minutes,
        pending_votes=pending_votes if pending_votes else None,
        action_items=action_items_list,
        brief_content=brief_content,
    )
    if print_friendly:
        pdf_bytes = generate_print_friendly_board_packet_pdf(**gen_args)
    else:
        pdf_bytes = generate_board_packet_pdf(**gen_args)

    # Create filename
    meeting_date = meeting.scheduled_date.strftime("%Y-%m-%d") if meeting.scheduled_date else "draft"
    filename = f"board-packet-{meeting_date}.pdf"

    pdf_bytes = tag_pdf(pdf_bytes, title=filename.replace(".pdf", ""))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
