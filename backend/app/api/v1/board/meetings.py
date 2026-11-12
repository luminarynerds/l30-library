# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board meetings API endpoints - CRUD, agenda, and attendance management."""

from app.core.logging import get_logger
from datetime import datetime, timezone

logger = get_logger(__name__)
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.board import (
    AgendaItem,
    BoardMeeting,
    BoardMember,
    MeetingAttendance,
    BoardMeetingBrief,
)
from ....models.board.minutes import BoardMinutes
from ....models.board_audit_log import BoardAuditLog, BoardAuditAction
from ....core.audit_log import audit_log_event
from ....models.user import User, UserRole
from ....schemas.board import (
    AgendaItemBase,
    AgendaItemResponse,
    AgendaPreviewItem,
    AttendanceResponse,
    BoardMeetingCreate,
    BoardMeetingListItem,
    BoardMeetingResponse,
    BoardMeetingUpdate,
    BriefResponse,
    MeetingSearchResponse,
)
from ....services.meeting_prep_service import (
    MeetingPrepService,
    get_meeting_prep_service,
)
from ..auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/board/meetings", tags=["meetings"])


# ============ Public Endpoints ============
#
# These endpoints have no auth dependency by design -- they back the public
# transparency pages (BoardMeetingsPage / MeetingDetailPage, no RequireAuth
# wrapper). They must still respect notice-status gating: unposted/draft
# meetings and executive-session details are not for public consumption.
# Board staff/members (checked via `_is_board_privileged`) see everything,
# matching the access level they already have on the write endpoints below.

_PUBLIC_NOTICE_STATUSES = ("posted", "published")
_BOARD_STAFF_ROLES = (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR)


async def _is_board_privileged(current_user: Optional[User], db: AsyncSession) -> bool:
    """True if the caller may see draft/unposted meetings and executive-session fields."""
    if current_user is None:
        return False
    if current_user.role in _BOARD_STAFF_ROLES:
        return True
    result = await db.execute(
        select(BoardMember).where(
            BoardMember.user_id == current_user.id, BoardMember.is_current == True
        )
    )
    return result.scalar_one_or_none() is not None


def _redact_executive_session(response) -> None:
    """Strip executive-session fields from a response model in place."""
    response.has_executive_session = False
    response.executive_session_reason = None


@router.get("/search", response_model=MeetingSearchResponse)
async def search_meetings(
    q: Optional[str] = Query(None, description="Full-text search across title, description, location, agenda items"),
    meeting_type: Optional[str] = Query(None, description="Filter by meeting type"),
    status: Optional[str] = Query(None, description="Filter by status: scheduled, completed, cancelled"),
    date_from: Optional[str] = Query(None, description="Meetings on or after this date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Meetings on or before this date (YYYY-MM-DD)"),
    has_recording: Optional[bool] = Query(None, description="Only meetings with a recording URL"),
    committee_id: Optional[int] = Query(None, description="Filter by committee ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Full-text search across board meetings.

    Searches title, description, location, and agenda item titles/descriptions.
    Supports filtering by meeting type, status, date range, recording availability,
    and committee. Returns paginated results.
    """
    privileged = await _is_board_privileged(current_user, db)

    # Build the base query — use a subquery approach so we can distinct on meetings
    # that match agenda item text without duplicating rows.
    base_query = select(BoardMeeting)

    filters = []
    if not privileged:
        filters.append(BoardMeeting.notice_status.in_(_PUBLIC_NOTICE_STATUSES))

    # Full-text search across meeting fields and agenda items
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        # Subquery: meeting IDs where an agenda item matches
        agenda_match_subquery = (
            select(AgendaItem.meeting_id)
            .where(
                or_(
                    AgendaItem.title.ilike(pattern),
                    AgendaItem.description.ilike(pattern),
                )
            )
            .scalar_subquery()
        )
        text_filter = or_(
            BoardMeeting.title.ilike(pattern),
            BoardMeeting.description.ilike(pattern),
            BoardMeeting.location.ilike(pattern),
            BoardMeeting.id.in_(agenda_match_subquery),
        )
        filters.append(text_filter)

    # Meeting type filter
    if meeting_type:
        filters.append(BoardMeeting.meeting_type == meeting_type)

    # Status filter
    if status == "cancelled":
        filters.append(BoardMeeting.is_cancelled == True)
    elif status == "scheduled":
        filters.append(or_(BoardMeeting.is_cancelled == False, BoardMeeting.is_cancelled.is_(None)))
        filters.append(BoardMeeting.scheduled_date >= datetime.now(timezone.utc))
    elif status == "completed":
        filters.append(or_(BoardMeeting.is_cancelled == False, BoardMeeting.is_cancelled.is_(None)))
        filters.append(BoardMeeting.scheduled_date < datetime.now(timezone.utc))

    # Date range filters
    if date_from:
        try:
            from datetime import date
            dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            filters.append(BoardMeeting.scheduled_date >= dt_from)
        except ValueError as e:
            logger.warning("Invalid date_from filter value: %s - %s", date_from, e)
            # Continue filtering without this constraint - client should fix format

    if date_to:
        try:
            from datetime import date, timedelta
            dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            # Include the full day
            dt_to = dt_to.replace(hour=23, minute=59, second=59)
            filters.append(BoardMeeting.scheduled_date <= dt_to)
        except ValueError as e:
            logger.warning("Invalid date_to filter value: %s - %s", date_to, e)
            # Continue filtering without this constraint - client should fix format

    # Committee filter
    if committee_id is not None:
        filters.append(BoardMeeting.committee_id == committee_id)

    # Has recording filter — recording_url lives on BoardMinutes
    if has_recording is not None:
        meetings_with_recording = (
            select(BoardMinutes.meeting_id)
            .where(BoardMinutes.recording_url.isnot(None))
            .scalar_subquery()
        )
        if has_recording:
            filters.append(BoardMeeting.id.in_(meetings_with_recording))
        else:
            filters.append(BoardMeeting.id.notin_(meetings_with_recording))

    if filters:
        base_query = base_query.where(and_(*filters))

    # Count total matching rows
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply ordering and pagination
    paginated_query = (
        base_query
        .order_by(BoardMeeting.scheduled_date.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(paginated_query)
    meetings = result.scalars().all()

    response = MeetingSearchResponse(
        results=meetings,
        total=total,
        skip=skip,
        limit=limit,
    )
    if not privileged:
        for item in response.results:
            _redact_executive_session(item)
    return response


@router.get("", response_model=List[BoardMeetingListItem])
async def get_public_meetings(
    upcoming_only: bool = Query(False, description="Only return upcoming meetings"),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Get public meeting schedule.

    Surfaces minutes/recording/agenda-packet URLs so meeting cards can render
    artifact badges without a follow-up fetch per meeting.

    Unprivileged callers (unauthenticated or non-board-staff) only ever see
    meetings whose notice has been posted/published, and never see
    executive-session details.
    """
    privileged = await _is_board_privileged(current_user, db)

    # selectinload(minutes) is required: meeting.minutes is touched during
    # response build, which 500s with MissingGreenlet on lazy-load.
    query = select(BoardMeeting).options(
        selectinload(BoardMeeting.agenda_items),
        selectinload(BoardMeeting.minutes),
    ).where(or_(BoardMeeting.is_cancelled == False, BoardMeeting.is_cancelled.is_(None)))
    if not privileged:
        query = query.where(BoardMeeting.notice_status.in_(_PUBLIC_NOTICE_STATUSES))
    if upcoming_only:
        query = query.where(BoardMeeting.scheduled_date >= datetime.now(timezone.utc))
    query = query.order_by(BoardMeeting.scheduled_date.desc()).limit(limit)

    result = await db.execute(query)
    meetings = result.scalars().all()

    # Build response with agenda preview (first 3 items by sort_order) + artifact URLs.
    responses = []
    for meeting in meetings:
        list_item = BoardMeetingListItem.model_validate(meeting)
        if not privileged:
            _redact_executive_session(list_item)
        agenda_source = meeting.agenda_items if (privileged or meeting.agenda_published_at) else []
        sorted_items = sorted(agenda_source, key=lambda x: x.sort_order)[:3]
        list_item.agenda_preview = [
            AgendaPreviewItem(title=ai.title, item_number=ai.item_number)
            for ai in sorted_items
        ]
        minutes = meeting.minutes  # eager-loaded above
        if minutes is not None and minutes.approved and (not minutes.is_sealed or privileged):
            list_item.minutes_url = f"/board/meetings/{meeting.id}#minutes"
            list_item.recording_url = minutes.recording_url or None
        # agenda_packet_url: no direct FK on BoardMeeting today; see PR notes.
        list_item.agenda_packet_url = None
        responses.append(list_item)
    return responses




@router.get("/calendar.ics")
async def meetings_ical_feed(db: AsyncSession = Depends(get_db)):
    """iCal feed of board meetings (all non-cancelled, past and future).

    Subscribers (trustees, public, open-meetings retention) expect the full
    record, not a rolling window.
    """
    from fastapi.responses import Response
    from ....core.config import get_settings

    now = datetime.now(timezone.utc)
    base = (getattr(get_settings(), "frontend_url", None) or "").rstrip("/")

    query = (
        select(BoardMeeting)
        .where(
            or_(BoardMeeting.is_cancelled == False, BoardMeeting.is_cancelled.is_(None)),
            BoardMeeting.notice_status.in_(_PUBLIC_NOTICE_STATUSES),
        )
        .order_by(BoardMeeting.scheduled_date)
    )
    result = await db.execute(query)
    meetings = result.scalars().all()

    def fmt_dt(dt):
        if dt is None:
            return None
        return dt.strftime("%Y%m%dT%H%M%SZ")

    def escape_ical(text):
        if not text:
            return ""
        return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//L30//Board Meetings//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:L30 Board Meetings",
    ]

    for m in meetings:
        dtstart = fmt_dt(m.start_time or m.scheduled_date)
        dtend = fmt_dt(m.end_time) if m.end_time else None
        uid = f"meeting-{m.id}@l30.library"

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{fmt_dt(now)}")
        lines.append(f"DTSTART:{dtstart}")
        if dtend:
            lines.append(f"DTEND:{dtend}")
        lines.append(f"SUMMARY:{escape_ical(m.title)}")
        if m.location:
            lines.append(f"LOCATION:{escape_ical(m.location)}")
        if m.description:
            lines.append(f"DESCRIPTION:{escape_ical(m.description)}")
        lines.append(f"URL:{base}/board/meetings/{m.id}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    cal_text = "\r\n".join(lines) + "\r\n"
    return Response(content=cal_text, media_type="text/calendar")


@router.get("/feed.xml")
async def meetings_rss_feed(db: AsyncSession = Depends(get_db)):
    """RSS feed of board meetings (50 most-recent non-cancelled, by scheduled date)."""
    from fastapi.responses import Response
    from ....core.config import get_settings

    now = datetime.now(timezone.utc)
    base = (getattr(get_settings(), "frontend_url", None) or "").rstrip("/")

    query = (
        select(BoardMeeting)
        .where(
            or_(BoardMeeting.is_cancelled == False, BoardMeeting.is_cancelled.is_(None)),
            BoardMeeting.notice_status.in_(_PUBLIC_NOTICE_STATUSES),
        )
        .order_by(BoardMeeting.scheduled_date.desc())
        .limit(50)
    )
    result = await db.execute(query)
    meetings = result.scalars().all()

    def escape_xml(text):
        if not text:
            return ""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    def rfc822(dt):
        if dt is None:
            return ""
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

    items_xml = ""
    for m in meetings:
        desc = escape_xml(m.description or "")
        if m.location:
            desc += f" | Location: {escape_xml(m.location)}"
        items_xml += (
            "    <item>\n"
            f"      <title>{escape_xml(m.title)}</title>\n"
            f"      <link>{base}/board/meetings/{m.id}</link>\n"
            f'      <guid isPermaLink="false">meeting-{m.id}</guid>\n'
            f"      <pubDate>{rfc822(m.scheduled_date)}</pubDate>\n"
            f"      <description>{desc}</description>\n"
            "    </item>\n"
        )

    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        "    <title>L30 Board Meetings</title>\n"
        f"    <link>{base}/board/meetings</link>\n"
        "    <description>Board meeting schedule for the L30 Community Library</description>\n"
        f"    <lastBuildDate>{rfc822(now)}</lastBuildDate>\n"
        f"{items_xml}"
        "  </channel>\n"
        "</rss>"
    )

    return Response(content=rss, media_type="application/rss+xml")



@router.get("/{meeting_id}", response_model=BoardMeetingResponse)
async def get_public_meeting(
    meeting_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific meeting.

    Unprivileged callers (unauthenticated or non-board-staff) only get
    meetings whose notice has been posted/published, with executive-session
    fields redacted and no agenda preview for an unpublished agenda. A
    draft/unposted meeting 404s for these callers rather than leaking its
    existence.
    """
    privileged = await _is_board_privileged(current_user, db)

    # Eager-load agenda_items so we can build agenda_preview without a lazy-load
    # MissingGreenlet, matching the list endpoint contract (first 3 by sort_order).
    query = (
        select(BoardMeeting)
        .options(selectinload(BoardMeeting.agenda_items))
        .where(BoardMeeting.id == meeting_id)
    )
    if not privileged:
        query = query.where(BoardMeeting.notice_status.in_(_PUBLIC_NOTICE_STATUSES))
    result = await db.execute(query)
    meeting = result.scalar_one_or_none()
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    response = BoardMeetingResponse.model_validate(meeting)
    if not privileged:
        _redact_executive_session(response)
    agenda_source = meeting.agenda_items if (privileged or meeting.agenda_published_at) else []
    sorted_items = sorted(agenda_source, key=lambda x: x.sort_order)[:3]
    response.agenda_preview = [
        AgendaPreviewItem(title=ai.title, item_number=ai.item_number)
        for ai in sorted_items
    ]
    return response


@router.get("/{meeting_id}/agenda", response_model=List[AgendaItemResponse])
async def get_meeting_agenda(
    meeting_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Get agenda items for a meeting.

    Unprivileged callers only get items for a meeting whose notice has been
    posted/published (404 otherwise, to avoid confirming a draft meeting's
    existence), and only once its agenda has actually been published.
    """
    privileged = await _is_board_privileged(current_user, db)

    if not privileged:
        meeting_result = await db.execute(
            select(BoardMeeting.agenda_published_at).where(
                and_(
                    BoardMeeting.id == meeting_id,
                    BoardMeeting.notice_status.in_(_PUBLIC_NOTICE_STATUSES),
                )
            )
        )
        row = meeting_result.first()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
        if row[0] is None:
            return []

    query = (
        select(AgendaItem)
        .where(AgendaItem.meeting_id == meeting_id)
        .order_by(AgendaItem.sort_order)
    )
    result = await db.execute(query)
    return result.scalars().all()


# ============ Authenticated Endpoints (Board Members/Staff) ============


@router.post("", response_model=BoardMeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting_endpoint(
    meeting: BoardMeetingCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new board meeting (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    from ....services.board_service import create_meeting as create_meeting_svc
    db_meeting = await create_meeting_svc(meeting.model_dump(), current_user.id, db)

    db.add(BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.MEETING_CREATED,
        entity_type="BoardMeeting",
        entity_id=db_meeting.id,
        meeting_id=db_meeting.id,
        details={"title": db_meeting.title, "meeting_type": db_meeting.meeting_type,
                 "scheduled_date": db_meeting.scheduled_date.isoformat() if db_meeting.scheduled_date else None},
    ))
    await db.commit()
    audit_log_event(
        event_type="BOARD_MEETING_CREATED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="INFO",
        details={"meeting_id": db_meeting.id, "entity_type": "BoardMeeting", "title": db_meeting.title, "meeting_type": db_meeting.meeting_type},
    )
    return db_meeting


@router.put("/{meeting_id}", response_model=BoardMeetingResponse)
async def update_meeting(
    meeting_id: int,
    meeting: BoardMeetingUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a meeting (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    db_meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")

    update_data = meeting.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_meeting, key, value)

    db.add(BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.MEETING_UPDATED,
        entity_type="BoardMeeting",
        entity_id=meeting_id,
        meeting_id=meeting_id,
        details={"updated_fields": list(update_data.keys())},
    ))
    await db.commit()
    await db.refresh(db_meeting)
    audit_log_event(
        event_type="BOARD_MEETING_UPDATED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="INFO",
        details={"meeting_id": meeting_id, "entity_type": "BoardMeeting", "updated_fields": list(update_data.keys())},
    )
    return db_meeting


@router.post("/{meeting_id}/cancel")
async def cancel_meeting(
    meeting_id: int,
    request: Request,
    reason: str = Query(..., description="Cancellation reason"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a meeting (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    db_meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")

    now = datetime.now(timezone.utc)
    db_meeting.is_cancelled = True
    db_meeting.cancellation_reason = reason
    db_meeting.updated_at = now

    # Log meeting cancellation to audit trail
    audit_entry = BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.MEETING_CANCELLED,
        entity_type="BoardMeeting",
        entity_id=meeting_id,
        meeting_id=meeting_id,
        details={
            "reason": reason,
            "cancelled_at": now.isoformat(),
            "meeting_title": db_meeting.title,
            "scheduled_date": db_meeting.scheduled_date.isoformat() if db_meeting.scheduled_date else None,
            "cancelled_by": f"{current_user.first_name} {current_user.last_name}"
        },
        notes=f"Meeting cancelled: {reason[:100]}"
    )
    db.add(audit_entry)

    await db.commit()
    audit_log_event(
        event_type="BOARD_MEETING_CANCELLED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="WARNING",
        details={"meeting_id": meeting_id, "entity_type": "BoardMeeting", "title": db_meeting.title, "reason": reason},
    )
    return {"message": "Meeting cancelled"}


@router.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a meeting (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

    db_meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")

    # Guard: cannot delete meeting with approved minutes
    minutes_result = await db.execute(
        select(BoardMinutes).where(BoardMinutes.meeting_id == meeting_id)
    )
    meeting_minutes = minutes_result.scalar_one_or_none()
    if meeting_minutes and meeting_minutes.approved:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete meeting with approved minutes. Minutes are permanent records.",
        )

    db.add(BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.MEETING_DELETED,
        entity_type="BoardMeeting",
        entity_id=meeting_id,
        meeting_id=meeting_id,
        details={"title": db_meeting.title,
                 "scheduled_date": db_meeting.scheduled_date.isoformat() if db_meeting.scheduled_date else None},
    ))
    audit_log_event(
        event_type="BOARD_MEETING_DELETED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="WARNING",
        details={"meeting_id": meeting_id, "entity_type": "BoardMeeting", "title": db_meeting.title},
    )
    await db.delete(db_meeting)
    await db.commit()
    return {"message": "Meeting deleted"}


@router.post("/{meeting_id}/agenda", response_model=AgendaItemResponse)
async def add_agenda_item(
    meeting_id: int,
    item: AgendaItemBase,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add an agenda item to a meeting (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    # Verify meeting exists and is not cancelled
    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")
    if meeting.is_cancelled:
        raise HTTPException(
            status_code=400, detail="Cannot add agenda items to a cancelled meeting"
        )

    db_item = AgendaItem(
        **item.model_dump(), meeting_id=meeting_id, created_by_id=current_user.id
    )
    db.add(db_item)
    await db.flush()

    db.add(BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.AGENDA_ITEM_ADDED,
        entity_type="AgendaItem",
        entity_id=db_item.id,
        meeting_id=meeting_id,
        details={"title": db_item.title, "item_number": db_item.item_number},
    ))
    await db.commit()
    await db.refresh(db_item)
    audit_log_event(
        event_type="BOARD_AGENDA_ITEM_ADDED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="INFO",
        details={"agenda_item_id": db_item.id, "entity_type": "AgendaItem", "meeting_id": meeting_id, "title": db_item.title},
    )
    return db_item


# ============ Meeting Prep & Brief Endpoints ============


@router.post("/{meeting_id}/brief", response_model=BriefResponse)
async def generate_meeting_brief(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI brief for a meeting (staff/admin/board members)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        # Check if user is a board member
        result = await db.execute(
            select(BoardMember).where(
                BoardMember.user_id == current_user.id, BoardMember.is_current == True
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=403, detail="Board member or staff access required"
            )

    # Verify meeting exists
    await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")

    # Check for existing brief
    result = await db.execute(
        select(BoardMeetingBrief).where(
            BoardMeetingBrief.meeting_id == meeting_id,
            BoardMeetingBrief.status != "failed",
        )
    )
    existing = result.scalar_one_or_none()
    if existing and existing.status == "completed":
        return BriefResponse.from_orm_brief(existing)

    # Delete any failed briefs before regenerating
    if existing and existing.status == "failed":
        await db.delete(existing)
        await db.commit()

    # Generate new brief
    service = get_meeting_prep_service(db)
    brief = await service.generate_brief(meeting_id, current_user.id)
    return BriefResponse.from_orm_brief(brief)


@router.get("/{meeting_id}/brief", response_model=Optional[BriefResponse])
async def get_meeting_brief(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the AI brief for a meeting if one exists."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        result = await db.execute(
            select(BoardMember).where(
                BoardMember.user_id == current_user.id, BoardMember.is_current == True
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=403, detail="Board member or staff access required"
            )

    service = get_meeting_prep_service(db)
    brief = await service.get_brief(meeting_id)
    if brief is None:
        return None
    return BriefResponse.from_orm_brief(brief)


@router.get("/{meeting_id}/checklist")
async def get_meeting_checklist(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a pre-meeting checklist for board members."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        result = await db.execute(
            select(BoardMember).where(
                BoardMember.user_id == current_user.id, BoardMember.is_current == True
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=403, detail="Board member or staff access required"
            )

    service = get_meeting_prep_service(db)
    checklist = await service.get_meeting_checklist(meeting_id)
    return checklist


@router.delete("/{meeting_id}/brief")
async def delete_meeting_brief(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a meeting brief to allow regeneration (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(BoardMeetingBrief).where(BoardMeetingBrief.meeting_id == meeting_id))
    brief = result.scalar_one_or_none()
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    await db.delete(brief)
    await db.commit()
    return {"message": "Brief deleted"}


# ============ Attendance Tracking Endpoints ============


@router.get("/{meeting_id}/attendance", response_model=List[AttendanceResponse])
async def get_meeting_attendance(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get attendance records for a meeting (staff/admin/board members)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        result = await db.execute(
            select(BoardMember).where(
                BoardMember.user_id == current_user.id, BoardMember.is_current == True
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=403, detail="Board member or staff access required"
            )

    query = (
        select(MeetingAttendance)
        .where(MeetingAttendance.meeting_id == meeting_id)
        .order_by(MeetingAttendance.created_at)
    )
    result = await db.execute(query)
    return result.scalars().all()



@router.get("/{meeting_id}/quorum")
async def check_meeting_quorum(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if meeting has quorum based on attendance (staff/admin/board members)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        result = await db.execute(
            select(BoardMember).where(
                BoardMember.user_id == current_user.id, BoardMember.is_current == True
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=403, detail="Board member or staff access required"
            )

    # Count current board members
    member_result = await db.execute(
        select(BoardMember).where(BoardMember.is_current == True)
    )
    total_members = len(member_result.scalars().all())

    # Count present voting members
    attendance_result = await db.execute(
        select(MeetingAttendance).where(
            and_(
                MeetingAttendance.meeting_id == meeting_id,
                MeetingAttendance.attendance_status.in_(["present", "tardy"]),
                MeetingAttendance.is_voting_member == True,
            )
        )
    )
    present_voting = len(attendance_result.scalars().all())

    # Quorum is typically majority of members
    quorum_needed = (total_members // 2) + 1
    quorum_met = present_voting >= quorum_needed

    return {
        "total_board_members": total_members,
        "present_voting_members": present_voting,
        "quorum_needed": quorum_needed,
        "quorum_met": quorum_met,
    }
