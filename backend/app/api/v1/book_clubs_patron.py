# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Book Club Patron API Endpoints

Provides patron-facing book club operations: browsing, joining,
discussion forums, and real-time chat.
"""

from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.branding import branding
from ...schemas.book_club_patron import (
    BookClubListResponse,
    BookClubDetail,
    DiscussionThread,
    DiscussionReply,
    CreateDiscussionRequest,
    CreateReplyRequest,
    DiscussionSearchHit,
    DiscussionSearchResponse,
)
from ...models.user import User, UserRole
from ...models.book_club import BookClubMember
from ...services.book_club_patron_service import BookClubPatronService
from ...services import book_club_service
from sqlalchemy import select, and_
from .auth import get_current_user, get_optional_user
from .feature_guards import require_book_club_history_enabled
from .feature_guards import require_book_club_waitlist_enabled

router = APIRouter(prefix="/book-clubs", tags=["Book Clubs"])


# ---------------------------------------------------------------------------
# iCalendar feed helpers (RFC 5545)
# ---------------------------------------------------------------------------
# Hand-rolled because `icalendar` is not in the backend deps. Output is small
# and RFC 5545's TEXT escaping is straightforward. Line endings must be CRLF.
# Line-folding at 75 octets is NOT applied: no real-world calendar client
# enforces it, and our SUMMARY/LOCATION/DESCRIPTION strings rarely exceed it.


def _ical_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def _format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _build_meetings_ics(club, meetings, base_url: str = "") -> str:
    from datetime import timedelta

    crlf = "\r\n"
    now = _format_utc(datetime.now(timezone.utc))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{branding.library_name}//Book Club Meetings//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_ical_escape(club.name)} Meetings",
    ]

    for mtg in meetings:
        if not mtg.meeting_date:
            continue
        dtstart = _format_utc(mtg.meeting_date)
        dtend = _format_utc(mtg.meeting_date + timedelta(hours=1))
        summary = _ical_escape(f"{club.name}: {mtg.title}")
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:book-club-meeting-{mtg.id}@example.com",
            f"DTSTAMP:{now}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{summary}",
        ])
        if mtg.location:
            lines.append(f"LOCATION:{_ical_escape(mtg.location)}")
        if mtg.description:
            lines.append(f"DESCRIPTION:{_ical_escape(mtg.description)}")
        lines.append(f"URL:{base_url}/book-clubs/{club.id}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return crlf.join(lines) + crlf


@router.get("", response_model=BookClubListResponse)
async def list_book_clubs(
    genre: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List public book clubs with optional filtering."""
    user_id = None
    return await BookClubPatronService.list_clubs(
        genre=genre, search=search, page=page, per_page=per_page,
        user_id=user_id, db=db,
    )


@router.get("/genres", response_model=List[str])
async def list_book_club_genres(
    db: AsyncSession = Depends(get_db),
):
    """Return distinct genres in use across active, public book clubs."""
    return await BookClubPatronService.list_genres(db=db)


@router.get("/{club_id}", response_model=Optional[BookClubDetail])
async def get_book_club(
    club_id: int = Path(...),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get book club details. Public endpoint; is_member reflects auth state."""
    return await BookClubPatronService.get_club_detail(
        club_id=club_id,
        user_id=current_user.id if current_user else None,
        db=db,
    )


@router.get("/{club_id}/meetings.ics")
async def get_book_club_meetings_ics(
    club_id: int = Path(...),
    db: AsyncSession = Depends(get_db),
):
    """Return future meetings for a book club as an RFC 5545 iCalendar feed.

    Public read (no auth) — visibility matches the patron detail page,
    which is reachable anonymously. Returns `text/calendar; charset=utf-8`
    so subscribing clients (Calendar.app, Google Calendar, Outlook) accept
    the response from a webcal:// URL.
    """
    result = await BookClubPatronService.get_meetings_for_ics(
        club_id=club_id, db=db,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book club not found"
        )
    club, meetings = result
    body = _build_meetings_ics(club, meetings)
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="book-club-{club_id}-meetings.ics"',
            "Cache-Control": "public, max-age=300",
        },
    )


@router.post("/{club_id}/join")
async def join_book_club(
    response: Response,
    club_id: int = Path(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Join a book club.

    Routes to the waitlist when a capped club is full. Response codes:
    201 joined, 202 waitlisted, 409 already a member/waitlisted, 404
    club not found. Body: ``{"status", "position", "success"}``.
    """
    result = await BookClubPatronService.join_club(
        club_id=club_id, user_id=current_user.id, db=db,
    )
    status_value = result.get("status")
    if status_value == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book club not found",
        )
    if status_value in ("already_member", "already_waitlisted"):
        response.status_code = status.HTTP_409_CONFLICT
        return {**result, "success": False}
    if status_value == "waitlisted":
        response.status_code = status.HTTP_202_ACCEPTED
        return {**result, "success": True}
    # joined / uncapped-fallback
    response.status_code = status.HTTP_201_CREATED
    return {**result, "success": True}


@router.delete("/{club_id}/leave")
async def leave_book_club(
    club_id: int = Path(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Leave a book club. Promotes the next waitlisted patron, if any."""
    success = await BookClubPatronService.leave_club(
        club_id=club_id, user_id=current_user.id, db=db,
    )
    return {"success": success}


@router.post("/{club_id}/waitlist", status_code=status.HTTP_202_ACCEPTED)
async def join_book_club_waitlist(
    response: Response,
    club_id: int = Path(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _flag: None = Depends(require_book_club_waitlist_enabled),
):
    """Explicitly join a club's waitlist.

    Gated by ``book_club_waitlist_enabled``. 202 waitlisted, 409
    already member/waitlisted, 404 club not found, 409 uncapped (no
    waitlist for uncapped clubs).
    """
    result = await BookClubPatronService.add_to_waitlist(
        club_id=club_id, user_id=current_user.id, db=db,
    )
    status_value = result.get("status")
    if status_value == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book club not found",
        )
    if status_value == "uncapped":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This club has no member limit; no waitlist.",
        )
    if status_value in ("already_member", "already_waitlisted"):
        response.status_code = status.HTTP_409_CONFLICT
        return {**result, "success": False}
    return {**result, "success": True}


@router.delete(
    "/{club_id}/waitlist", status_code=status.HTTP_204_NO_CONTENT
)
async def leave_book_club_waitlist(
    club_id: int = Path(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _flag: None = Depends(require_book_club_waitlist_enabled),
):
    """Patron leaves their own waitlist entry. No promotion (a patron
    leaving the waitlist does not free a membership seat). 204 on
    success, 404 if not waitlisted."""
    removed = await BookClubPatronService.leave_waitlist(
        club_id=club_id, user_id=current_user.id, db=db,
    )
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No waitlist entry to remove",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{club_id}/meetings/{meeting_id}/discussions", response_model=List[DiscussionThread])
async def list_discussions(
    club_id: int = Path(...),
    meeting_id: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List discussion threads for a meeting."""
    return await BookClubPatronService.list_discussions(
        club_id=club_id, meeting_id=meeting_id, db=db,
    )


@router.post("/{club_id}/meetings/{meeting_id}/discussions", response_model=DiscussionThread)
async def create_discussion(
    body: CreateDiscussionRequest,
    club_id: int = Path(...),
    meeting_id: int = Path(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new discussion thread."""
    return await BookClubPatronService.create_discussion(
        club_id=club_id,
        meeting_id=meeting_id,
        user_id=current_user.id,
        title=body.title,
        content=body.content,
        db=db,
    )


@router.get("/{club_id}/discussions/{discussion_id}/replies", response_model=List[DiscussionReply])
async def list_replies(
    club_id: int = Path(...),
    discussion_id: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List replies for a discussion."""
    return await BookClubPatronService.list_replies(discussion_id=discussion_id, db=db)


@router.post("/{club_id}/discussions/{discussion_id}/replies", response_model=DiscussionReply)
async def create_reply(
    body: CreateReplyRequest,
    club_id: int = Path(...),
    discussion_id: int = Path(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Post a reply to a discussion."""
    return await BookClubPatronService.create_reply(
        discussion_id=discussion_id,
        user_id=current_user.id,
        content=body.content,
        db=db,
    )


# ---------------------------------------------------------------------------
# Discussion archive search (gated by book_club_history_enabled)
# ---------------------------------------------------------------------------


_STAFF_ROLES = {
    UserRole.STAFF,
    UserRole.ADMIN,
    UserRole.SUPER_ADMIN,
    UserRole.DIRECTOR,
    UserRole.LEGAL,
}


@router.get(
    "/{club_id}/discussions/search",
    response_model=DiscussionSearchResponse,
)
async def search_book_club_discussions(
    club_id: int = Path(...),
    q: str = Query(..., min_length=1, max_length=200),
    date_from: Optional[datetime] = Query(None, alias="from"),
    date_to: Optional[datetime] = Query(None, alias="to"),
    include_archived: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _flag: None = Depends(require_book_club_history_enabled),
) -> DiscussionSearchResponse:
    """Full-text search across a club's discussions.

    Staff (STAFF/ADMIN/SUPER_ADMIN/DIRECTOR/LEGAL) can opt into
    ``include_archived``. Patron callers are forced to active-only
    regardless of the param AND must already be a member of the club —
    archive search is staff-only in v1 (spec: "No archive access in v1
    (optional follow-up: read-only archive for members)").
    """
    is_staff = current_user.role in _STAFF_ROLES

    if not is_staff:
        # Patron path: require active membership, force include_archived
        # off. We don't 403 on non-members so the membership state isn't
        # disclosed — return empty results instead (same shape as
        # "no matches").
        membership_row = await db.execute(
            select(BookClubMember).where(
                and_(
                    BookClubMember.book_club_id == club_id,
                    BookClubMember.user_id == current_user.id,
                )
            )
        )
        if membership_row.scalars().first() is None:
            return DiscussionSearchResponse(
                hits=[], total=0, q=q, include_archived=False,
            )
        include_archived = False

    hits_raw = await book_club_service.search_discussions(
        club_id=club_id,
        q=q,
        db=db,
        include_archived=include_archived,
        date_from=date_from,
        date_to=date_to,
        limit=50,
    )
    hits = [DiscussionSearchHit(**h) for h in hits_raw]
    return DiscussionSearchResponse(
        hits=hits,
        total=len(hits),
        q=q,
        include_archived=include_archived,
    )
