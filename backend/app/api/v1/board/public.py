# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public board API -- unauthenticated endpoints for meeting transparency.

Exposes upcoming/past meetings, published agendas, approved minutes,
closed vote tallies, and a WebSocket feed for live meeting updates.

Privacy constraints:
- No member contact information
- No executive session content
- No individual vote records (only aggregate tallies)
- No draft/unpublished documents
- Only meetings with notice_status in (posted, published)
"""

import asyncio
import contextlib
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....models.board import (
    AgendaItem,
    BoardMeeting,
    BoardMinutes,
    BoardVote,
)
from ....services.board_pdf import generate_meeting_agenda_pdf, generate_meeting_minutes_pdf
from ....models.board.member import BoardMember

logger = get_logger(__name__)

router = APIRouter(prefix="/board/public", tags=["board-public"])

# ---------------------------------------------------------------------------
# Pydantic response schemas (public-only projections)
# ---------------------------------------------------------------------------


class PublicAgendaItem(BaseModel):
    id: int
    item_number: str
    title: str
    description: Optional[str] = None
    presenter: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    sort_order: int = 0
    requires_action: bool = False
    action_type: Optional[str] = None

    class Config:
        from_attributes = True


class PublicMeetingSummary(BaseModel):
    id: int
    meeting_type: str
    title: str
    scheduled_date: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    is_virtual: bool = False
    is_cancelled: bool = False
    notice_status: Optional[str] = None
    has_agenda: bool = False
    has_minutes: bool = False
    public_comment_enabled: bool = False
    accessibility_info: Optional[str] = None

    class Config:
        from_attributes = True


class PublicMeetingDetail(PublicMeetingSummary):
    description: Optional[str] = None
    public_comment_instructions: Optional[str] = None
    agenda_items: List[PublicAgendaItem] = []
    quorum_met: Optional[bool] = None
    minutes_approved: bool = False

    class Config:
        from_attributes = True


class PublicVoteTally(BaseModel):
    id: int
    title: str
    description: str
    vote_type: str
    status: str
    passed: Optional[bool] = None
    ayes: int = 0
    nays: int = 0
    abstentions: int = 0
    result: Optional[str] = None
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PublicMeetingsListResponse(BaseModel):
    upcoming: List[PublicMeetingSummary]
    past: List[PublicMeetingSummary]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PUBLIC_NOTICE_STATUSES = ("posted", "published")


def _base_public_meeting_filter():
    return and_(
        BoardMeeting.is_cancelled == False,
        BoardMeeting.notice_status.in_(_PUBLIC_NOTICE_STATUSES),
    )


def _vote_result_label(vote: BoardVote) -> Optional[str]:
    if vote.status != "closed":
        return None
    if vote.passed is True:
        return "passed"
    elif vote.passed is False:
        return "failed"
    return "inconclusive"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/meetings", response_model=PublicMeetingsListResponse)
async def list_public_meetings(
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List upcoming and past public meetings.

    Returns two lists: upcoming (soonest first) and past (most recent first).
    Excludes cancelled meetings and those without published notices.
    """
    now = datetime.now(timezone.utc)
    base_filter = _base_public_meeting_filter()

    # Upcoming: scheduled_date >= now
    upcoming_q = (
        select(BoardMeeting)
        .options(
            selectinload(BoardMeeting.agenda_items),
            selectinload(BoardMeeting.minutes),
        )
        .where(and_(base_filter, BoardMeeting.scheduled_date >= now))
        .order_by(BoardMeeting.scheduled_date.asc())
        .limit(limit)
    )
    upcoming_result = await db.execute(upcoming_q)
    upcoming_meetings = upcoming_result.scalars().all()

    # Past: scheduled_date < now (include cancelled with posted notice too)
    past_filter = and_(
        BoardMeeting.notice_status.in_(_PUBLIC_NOTICE_STATUSES),
        BoardMeeting.scheduled_date < now,
    )
    past_q = (
        select(BoardMeeting)
        .options(
            selectinload(BoardMeeting.agenda_items),
            selectinload(BoardMeeting.minutes),
        )
        .where(past_filter)
        .order_by(BoardMeeting.scheduled_date.desc())
        .limit(limit)
    )
    past_result = await db.execute(past_q)
    past_meetings = past_result.scalars().all()

    def _to_summary(m: BoardMeeting) -> PublicMeetingSummary:
        return PublicMeetingSummary(
            id=m.id,
            meeting_type=m.meeting_type,
            title=m.title,
            scheduled_date=m.scheduled_date,
            start_time=m.start_time,
            end_time=m.end_time,
            location=m.location,
            is_virtual=m.is_virtual or False,
            is_cancelled=m.is_cancelled or False,
            notice_status=m.notice_status,
            has_agenda=bool(m.agenda_published_at and m.agenda_items),
            has_minutes=bool(m.minutes and m.minutes.approved),
            public_comment_enabled=m.public_comment_enabled or False,
            accessibility_info=m.accessibility_info,
        )

    return PublicMeetingsListResponse(
        upcoming=[_to_summary(m) for m in upcoming_meetings],
        past=[_to_summary(m) for m in past_meetings],
    )


@router.get("/meetings/{meeting_id}", response_model=PublicMeetingDetail)
async def get_public_meeting(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get public meeting detail with agenda items (if published).

    No private notes, no executive session content.
    """
    result = await db.execute(
        select(BoardMeeting)
        .options(
            selectinload(BoardMeeting.agenda_items),
            selectinload(BoardMeeting.minutes),
        )
        .where(
            and_(
                BoardMeeting.id == meeting_id,
                BoardMeeting.notice_status.in_(_PUBLIC_NOTICE_STATUSES),
            )
        )
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Only include agenda items if agenda has been published
    agenda_items = []
    if meeting.agenda_published_at:
        agenda_items = sorted(meeting.agenda_items, key=lambda x: x.sort_order)

    return PublicMeetingDetail(
        id=meeting.id,
        meeting_type=meeting.meeting_type,
        title=meeting.title,
        description=meeting.description,
        scheduled_date=meeting.scheduled_date,
        start_time=meeting.start_time,
        end_time=meeting.end_time,
        location=meeting.location,
        is_virtual=meeting.is_virtual or False,
        is_cancelled=meeting.is_cancelled or False,
        notice_status=meeting.notice_status,
        has_agenda=bool(meeting.agenda_published_at and meeting.agenda_items),
        has_minutes=bool(meeting.minutes and meeting.minutes.approved),
        public_comment_enabled=meeting.public_comment_enabled or False,
        public_comment_instructions=meeting.public_comment_instructions,
        accessibility_info=meeting.accessibility_info,
        quorum_met=meeting.quorum_met,
        minutes_approved=meeting.minutes_approved or False,
        agenda_items=[PublicAgendaItem.model_validate(item) for item in agenda_items],
    )


@router.get("/meetings/{meeting_id}/agenda")
async def get_public_agenda_pdf(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Download published agenda as PDF. Returns 404 if not yet published."""
    result = await db.execute(
        select(BoardMeeting)
        .options(selectinload(BoardMeeting.agenda_items))
        .where(
            and_(
                BoardMeeting.id == meeting_id,
                BoardMeeting.notice_status.in_(_PUBLIC_NOTICE_STATUSES),
            )
        )
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting.agenda_published_at:
        raise HTTPException(status_code=404, detail="Agenda not yet published")

    agenda_items = sorted(meeting.agenda_items, key=lambda x: x.sort_order)

    members_result = await db.execute(
        select(BoardMember).where(BoardMember.is_current == True)
    )
    members = members_result.scalars().all()
    board_members = [
        {"name": m.full_name, "position": m.position, "email": m.public_email}
        for m in members
    ]

    pdf_bytes = generate_meeting_agenda_pdf(
        meeting=meeting,
        agenda_items=agenda_items,
        board_members=board_members,
    )

    date_str = meeting.scheduled_date.strftime("%Y-%m-%d")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="agenda-{date_str}.pdf"',
        },
    )


@router.get("/meetings/{meeting_id}/minutes")
async def get_public_minutes_pdf(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Download approved minutes as PDF. Returns 404 if not approved or sealed."""
    result = await db.execute(
        select(BoardMeeting)
        .options(
            selectinload(BoardMeeting.minutes),
            selectinload(BoardMeeting.agenda_items),
            selectinload(BoardMeeting.attendance_records),
        )
        .where(
            and_(
                BoardMeeting.id == meeting_id,
                BoardMeeting.notice_status.in_(_PUBLIC_NOTICE_STATUSES),
            )
        )
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting.minutes or not meeting.minutes.approved:
        raise HTTPException(status_code=404, detail="Approved minutes not available")

    if meeting.minutes.is_sealed:
        raise HTTPException(status_code=404, detail="Minutes are sealed")

    pdf_bytes = generate_meeting_minutes_pdf(
        meeting=meeting,
        minutes=meeting.minutes,
    )

    date_str = meeting.scheduled_date.strftime("%Y-%m-%d")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="minutes-{date_str}.pdf"',
        },
    )


@router.get("/meetings/{meeting_id}/votes", response_model=List[PublicVoteTally])
async def get_public_vote_tallies(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get closed vote results for a meeting. Only aggregate tallies, no individual votes."""
    # Verify meeting is publicly visible
    meeting_result = await db.execute(
        select(BoardMeeting.id).where(
            and_(
                BoardMeeting.id == meeting_id,
                BoardMeeting.notice_status.in_(_PUBLIC_NOTICE_STATUSES),
            )
        )
    )
    if not meeting_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Meeting not found")

    result = await db.execute(
        select(BoardVote).where(
            and_(
                BoardVote.meeting_id == meeting_id,
                BoardVote.status == "closed",
            )
        ).order_by(BoardVote.closed_at_actual.asc())
    )
    votes = result.scalars().all()

    return [
        PublicVoteTally(
            id=v.id,
            title=v.title,
            description=v.description,
            vote_type=v.vote_type,
            status=v.status,
            passed=v.passed,
            ayes=v.final_tally_yes,
            nays=v.final_tally_no,
            abstentions=v.final_tally_abstain,
            result=_vote_result_label(v),
            closed_at=v.closed_at_actual,
        )
        for v in votes
    ]


# ---------------------------------------------------------------------------
# WebSocket -- Live meeting feed
# ---------------------------------------------------------------------------


class _LiveMeetingBroadcaster:

    _instances: dict[int, "_LiveMeetingBroadcaster"] = {}

    def __init__(self, meeting_id: int):
        self.meeting_id = meeting_id
        self._subscribers: list[asyncio.Queue] = []

    @classmethod
    def get(cls, meeting_id: int) -> "_LiveMeetingBroadcaster":
        if meeting_id not in cls._instances:
            cls._instances[meeting_id] = cls(meeting_id)
        return cls._instances[meeting_id]

    @classmethod
    def cleanup(cls, meeting_id: int) -> None:
        cls._instances.pop(meeting_id, None)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        # Idempotent: already-removed queues are fine.
        with contextlib.suppress(ValueError):
            self._subscribers.remove(q)
        if not self._subscribers:
            self.cleanup(self.meeting_id)

    async def broadcast(self, event: dict) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass


async def broadcast_board_event(meeting_id: int, event: dict) -> None:
    if meeting_id in _LiveMeetingBroadcaster._instances:
        await _LiveMeetingBroadcaster._instances[meeting_id].broadcast(event)


@router.websocket("/meetings/{meeting_id}/live")
async def live_meeting_feed(
    websocket: WebSocket,
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
):
    # Verify meeting exists and is publicly visible
    result = await db.execute(
        select(BoardMeeting).where(
            and_(
                BoardMeeting.id == meeting_id,
                BoardMeeting.notice_status.in_(_PUBLIC_NOTICE_STATUSES),
            )
        )
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        await websocket.close(code=4004, reason="Meeting not found")
        return

    await websocket.accept()

    broadcaster = _LiveMeetingBroadcaster.get(meeting_id)
    queue = broadcaster.subscribe()

    try:
        await websocket.send_json({
            "type": "connected",
            "meeting_id": meeting_id,
            "meeting_title": meeting.title,
        })

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:  # noqa: BLE001  # WebSocket send may fail mid-pipe — break to close
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error for meeting %d", meeting_id)
    finally:
        broadcaster.unsubscribe(queue)
