# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Security regression: board meeting/document reads must not leak draft or
executive-session content to unauthenticated/unprivileged callers.

Part 1 (unchanged from the original fix): board minutes + document-version
reads require staff auth.

  - GET /api/v1/board/meetings/{id}/minutes        (full minutes, incl.
                                                     sealed executive-session
                                                     content)
  - GET /api/v1/board/documents/{id}/versions      (file_url of every version,
                                                     incl. drafts / non-public
                                                     docs)
  - GET /api/v1/board/documents/{id}/versions/{n}

These pin: unauthenticated -> 401; authenticated staff -> reaches the
handler; authenticated patron -> 403.

Part 2 (this fix): the *public* meeting endpoints in board/meetings.py --
GET /api/v1/board/meetings, GET /api/v1/board/meetings/{id}, and
GET /api/v1/board/meetings/{id}/agenda -- have no auth requirement by
design (they back the public transparency pages), but previously applied
no notice-status gate at all. Any unauthenticated caller who enumerated a
meeting ID could read a draft/unposted meeting's full detail, including
`has_executive_session` / `executive_session_reason`, and every agenda item
regardless of publication state.

Fixed behavior pinned here:
  - A draft/unposted meeting 404s for unauthenticated callers on both the
    list and detail endpoints (it simply doesn't appear/resolve), and its
    agenda 404s too.
  - A posted/published meeting is visible, but `has_executive_session` and
    `executive_session_reason` are always redacted (False/None) for
    unauthenticated callers, even when true in the database.
  - An unpublished agenda on an otherwise-public meeting returns no items
    to unauthenticated callers (empty list, not the draft items).
  - Board staff (STAFF/ADMIN/SUPER_ADMIN/DIRECTOR) continue to see full,
    unredacted detail for draft meetings and executive-session fields --
    this fix must not regress staff/board workflows.

Part 3: `board/public.py` -- the dedicated notice-gated public transparency
router -- is now mounted at /api/v1/board/public/* (it previously existed
in the codebase but was never wired into board/main.py). A basic smoke test
confirms it responds.
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, get_current_user_optional
from app.main import app
from app.models.board.agenda import AgendaItem
from app.models.board.meeting import BoardMeeting
from app.models.board.minutes import BoardMinutes
from app.models.user import User, UserRole

pytestmark = pytest.mark.asyncio

_MISSING_ID = 999999

_GUARDED_PATHS = [
    f"/api/v1/board/meetings/{_MISSING_ID}/minutes",
    f"/api/v1/board/documents/{_MISSING_ID}/versions",
    f"/api/v1/board/documents/{_MISSING_ID}/versions/1",
]


# ============ Part 1: minutes / document-version auth (unchanged) ============


@pytest.mark.parametrize("path", _GUARDED_PATHS)
async def test_unauthenticated_is_rejected(client: AsyncClient, path: str):
    """No credentials -> 401 from the auth dependency, never a handler response."""
    response = await client.get(path)
    assert response.status_code == 401, (
        f"{path} returned {response.status_code}; expected 401. "
        "A 200/404 means the endpoint reached its handler without auth."
    )


@pytest.mark.parametrize("path", _GUARDED_PATHS)
async def test_staff_reaches_handler(client: AsyncClient, path: str):
    """Authenticated staff passes the guard and reaches the handler (404 here)."""
    staff = User(
        id=1,
        email="staff.authz@example.com",
        first_name="Board",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: staff
    try:
        response = await client.get(path)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404, (
        f"{path} returned {response.status_code} for staff; expected 404 "
        "(record does not exist). A 401/403 means the guard wrongly blocked staff."
    )


@pytest.mark.parametrize("path", _GUARDED_PATHS)
async def test_patron_is_forbidden(client: AsyncClient, path: str):
    """A non-staff authenticated user is rejected with 403."""
    patron = User(
        id=2,
        email="patron.authz@example.com",
        first_name="Reg",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: patron
    try:
        response = await client.get(path)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403, (
        f"{path} returned {response.status_code} for a patron; expected 403."
    )


# ============ Part 2: board/meetings.py notice-status leak ============


async def _make_meeting(
    db_session: AsyncSession,
    *,
    notice_status: str,
    has_executive_session: bool = False,
    executive_session_reason: str | None = None,
    agenda_published: bool = False,
    title: str = "Regression Meeting",
) -> BoardMeeting:
    meeting = BoardMeeting(
        meeting_type="regular",
        title=title,
        scheduled_date=datetime.now(timezone.utc) + timedelta(days=7),
        is_cancelled=False,
        notice_status=notice_status,
        has_executive_session=has_executive_session,
        executive_session_reason=executive_session_reason,
        agenda_published_at=(datetime.now(timezone.utc) if agenda_published else None),
    )
    db_session.add(meeting)
    await db_session.commit()
    await db_session.refresh(meeting)

    agenda_item = AgendaItem(
        meeting_id=meeting.id,
        item_number="1",
        title="Draft internal discussion item",
        sort_order=0,
    )
    db_session.add(agenda_item)
    await db_session.commit()

    return meeting


async def test_unauthenticated_draft_meeting_detail_404s(client: AsyncClient, db_session: AsyncSession):
    """A draft/unposted meeting must not be readable by an unauthenticated caller."""
    meeting = await _make_meeting(
        db_session,
        notice_status="draft",
        has_executive_session=True,
        executive_session_reason="Personnel matter — pending litigation",
    )

    response = await client.get(f"/api/v1/board/meetings/{meeting.id}")

    assert response.status_code == 404, (
        f"Expected 404 for a draft meeting; got {response.status_code}: {response.text}"
    )


async def test_unauthenticated_draft_meeting_excluded_from_list(client: AsyncClient, db_session: AsyncSession):
    """The public meeting list must not include a draft/unposted meeting."""
    meeting = await _make_meeting(db_session, notice_status="draft")

    response = await client.get("/api/v1/board/meetings?limit=100")

    assert response.status_code == 200
    ids = {m["id"] for m in response.json()}
    assert meeting.id not in ids


async def test_unauthenticated_draft_meeting_agenda_404s(client: AsyncClient, db_session: AsyncSession):
    """Agenda items for a draft meeting must not be readable by an unauthenticated caller."""
    meeting = await _make_meeting(db_session, notice_status="draft")

    response = await client.get(f"/api/v1/board/meetings/{meeting.id}/agenda")

    assert response.status_code == 404, (
        f"Expected 404 for a draft meeting's agenda; got {response.status_code}: {response.text}"
    )


async def test_unauthenticated_posted_meeting_redacts_executive_session(
    client: AsyncClient, db_session: AsyncSession
):
    """A posted meeting is visible, but exec-session fields are always redacted for the public."""
    meeting = await _make_meeting(
        db_session,
        notice_status="posted",
        has_executive_session=True,
        executive_session_reason="Personnel matter — pending litigation",
    )

    response = await client.get(f"/api/v1/board/meetings/{meeting.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["has_executive_session"] is False, (
        "Unauthenticated caller must not learn a meeting has an executive session"
    )
    assert body["executive_session_reason"] is None, (
        "Unauthenticated caller must never see the executive-session reason"
    )


async def test_unauthenticated_posted_meeting_unpublished_agenda_is_empty(
    client: AsyncClient, db_session: AsyncSession
):
    """A posted meeting whose agenda isn't yet published returns no items publicly."""
    meeting = await _make_meeting(db_session, notice_status="posted", agenda_published=False)

    response = await client.get(f"/api/v1/board/meetings/{meeting.id}/agenda")

    assert response.status_code == 200
    assert response.json() == []


async def test_unauthenticated_posted_meeting_published_agenda_visible(
    client: AsyncClient, db_session: AsyncSession
):
    """Once the agenda is published on a posted meeting, its items are public."""
    meeting = await _make_meeting(db_session, notice_status="posted", agenda_published=True)

    response = await client.get(f"/api/v1/board/meetings/{meeting.id}/agenda")

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["title"] == "Draft internal discussion item"


async def test_staff_sees_draft_meeting_and_executive_session_unredacted(
    client: AsyncClient, db_session: AsyncSession
):
    """Board staff must not be locked out by the new gate: full detail, unredacted."""
    meeting = await _make_meeting(
        db_session,
        notice_status="draft",
        has_executive_session=True,
        executive_session_reason="Personnel matter — pending litigation",
    )

    staff = User(
        id=3,
        email="staff.meetings.authz@example.com",
        first_name="Board",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
    )
    # These endpoints depend on get_current_user_optional (they're public by
    # design, gated on notice status rather than auth), so the override target
    # differs from Part 1's get_current_user-gated endpoints.
    app.dependency_overrides[get_current_user_optional] = lambda: staff
    try:
        detail = await client.get(f"/api/v1/board/meetings/{meeting.id}")
        listing = await client.get("/api/v1/board/meetings?limit=100")
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)

    assert detail.status_code == 200
    body = detail.json()
    assert body["has_executive_session"] is True
    assert body["executive_session_reason"] == "Personnel matter — pending litigation"

    assert listing.status_code == 200
    ids = {m["id"] for m in listing.json()}
    assert meeting.id in ids


# ============ Part 2b: sealed-but-approved minutes leak (board/meetings.py list) ============


async def _make_meeting_with_minutes(
    db_session: AsyncSession,
    *,
    approved: bool,
    is_sealed: bool,
    recording_url: str = "https://zoom.example.com/rec/exec-session-recording",
    title: str = "Sealed Minutes Regression Meeting",
) -> BoardMeeting:
    meeting = BoardMeeting(
        meeting_type="regular",
        title=title,
        scheduled_date=datetime.now(timezone.utc) + timedelta(days=7),
        is_cancelled=False,
        notice_status="posted",
        has_executive_session=True,
        executive_session_reason="Personnel matter — pending litigation",
    )
    db_session.add(meeting)
    await db_session.commit()
    await db_session.refresh(meeting)

    minutes = BoardMinutes(
        meeting_id=meeting.id,
        status="approved" if approved else "under_review",
        approved=approved,
        is_sealed=is_sealed,
        recording_url=recording_url,
    )
    db_session.add(minutes)
    await db_session.commit()
    await db_session.refresh(meeting)

    return meeting


async def test_unauthenticated_sealed_approved_minutes_withheld_from_list(
    client: AsyncClient, db_session: AsyncSession
):
    """Approved + sealed minutes (e.g. covering executive session) must not
    leak recording_url/minutes_url to an unauthenticated caller via the list
    endpoint, even though `approved` is True."""
    meeting = await _make_meeting_with_minutes(db_session, approved=True, is_sealed=True)

    response = await client.get("/api/v1/board/meetings?limit=100")

    assert response.status_code == 200
    item = next(m for m in response.json() if m["id"] == meeting.id)
    assert item["recording_url"] is None, (
        "Unauthenticated caller must not receive recording_url for sealed minutes"
    )
    assert item["minutes_url"] is None, (
        "Unauthenticated caller must not receive minutes_url for sealed minutes"
    )


async def test_staff_sees_sealed_approved_minutes_in_list(
    client: AsyncClient, db_session: AsyncSession
):
    """Board staff (privileged) must still see recording_url/minutes_url for
    approved+sealed minutes -- this fix must not regress staff/board workflows."""
    meeting = await _make_meeting_with_minutes(db_session, approved=True, is_sealed=True)

    staff = User(
        id=4,
        email="staff.sealed-minutes.authz@example.com",
        first_name="Board",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
    )
    app.dependency_overrides[get_current_user_optional] = lambda: staff
    try:
        response = await client.get("/api/v1/board/meetings?limit=100")
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)

    assert response.status_code == 200
    item = next(m for m in response.json() if m["id"] == meeting.id)
    assert item["recording_url"] == "https://zoom.example.com/rec/exec-session-recording"
    assert item["minutes_url"] == f"/board/meetings/{meeting.id}#minutes"


async def test_unauthenticated_unsealed_approved_minutes_still_visible_in_list(
    client: AsyncClient, db_session: AsyncSession
):
    """Non-sealed approved minutes are unaffected by this fix -- still public."""
    meeting = await _make_meeting_with_minutes(db_session, approved=True, is_sealed=False)

    response = await client.get("/api/v1/board/meetings?limit=100")

    assert response.status_code == 200
    item = next(m for m in response.json() if m["id"] == meeting.id)
    assert item["recording_url"] == "https://zoom.example.com/rec/exec-session-recording"
    assert item["minutes_url"] == f"/board/meetings/{meeting.id}#minutes"


# ============ Part 3: board/public.py now mounted ============


async def test_public_board_api_is_mounted(client: AsyncClient):
    """board/public.py (previously dead code, dropped by merge drift) is now wired in."""
    response = await client.get("/api/v1/board/public/meetings")
    assert response.status_code == 200, (
        f"/api/v1/board/public/meetings returned {response.status_code}; "
        "expected 200 now that public.py is included in board/main.py."
    )
    body = response.json()
    assert "upcoming" in body and "past" in body
