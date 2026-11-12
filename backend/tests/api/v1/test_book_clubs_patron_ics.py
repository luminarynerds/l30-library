# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the patron-facing book club iCalendar feed.

Endpoint: GET /api/v1/book-clubs/{club_id}/meetings.ics
- Public read (no auth required)
- Returns RFC 5545 VCALENDAR body (text/calendar)
- Empty meeting list still returns a valid empty VCALENDAR
- Missing club returns 404
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.api.v1.feature_guards import require_book_clubs_enabled
from app.main import app
from app.models.book_club import (
    BookClub,
    BookClubMeeting,
    BookClubStatus,
    DiscussionStatus,
)


@pytest.fixture
def book_clubs_enabled():
    """Override the book_clubs_enabled feature guard so the route is reachable."""
    app.dependency_overrides[require_book_clubs_enabled] = lambda: None
    yield
    app.dependency_overrides.pop(require_book_clubs_enabled, None)


@pytest.fixture
async def club_with_meetings(test_db):
    club = BookClub(
        name="Tuesday Tea, Talk; & Tomes\\",
        description="Weekly chat",
        is_public=True,
        status=BookClubStatus.active,
    )
    test_db.add(club)
    await test_db.commit()
    await test_db.refresh(club)

    future = datetime.now(timezone.utc) + timedelta(days=7)
    past = datetime.now(timezone.utc) - timedelta(days=7)
    cancelled = datetime.now(timezone.utc) + timedelta(days=14)

    meetings = [
        BookClubMeeting(
            book_club_id=club.id,
            title="Chapter 1, Part A",
            description="Bring snacks;\nand questions.",
            meeting_date=future,
            location="Branch 1, Room 2",
            status=DiscussionStatus.planned,
        ),
        BookClubMeeting(
            book_club_id=club.id,
            title="Past meeting (should be excluded)",
            meeting_date=past,
            status=DiscussionStatus.completed,
        ),
        BookClubMeeting(
            book_club_id=club.id,
            title="Cancelled (should be excluded)",
            meeting_date=cancelled,
            status=DiscussionStatus.cancelled,
        ),
    ]
    for m in meetings:
        test_db.add(m)
    await test_db.commit()
    for m in meetings:
        await test_db.refresh(m)
    return club


@pytest.fixture
async def empty_club(test_db):
    club = BookClub(
        name="Empty Club",
        is_public=True,
        status=BookClubStatus.active,
    )
    test_db.add(club)
    await test_db.commit()
    await test_db.refresh(club)
    return club


class TestBookClubMeetingsIcs:
    """GET /api/v1/book-clubs/{club_id}/meetings.ics"""

    @pytest.mark.asyncio
    async def test_ics_returns_200_and_calendar_mime(
        self, client, book_clubs_enabled, club_with_meetings
    ):
        response = await client.get(
            f"/api/v1/book-clubs/{club_with_meetings.id}/meetings.ics"
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith(
            "text/calendar"
        ), response.headers["content-type"]
        assert "charset=utf-8" in response.headers["content-type"].lower()
        # Inline disposition with filename
        assert "book-club-" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_ics_body_has_vcalendar_envelope_and_crlf(
        self, client, book_clubs_enabled, club_with_meetings
    ):
        response = await client.get(
            f"/api/v1/book-clubs/{club_with_meetings.id}/meetings.ics"
        )
        body = response.text
        assert body.startswith("BEGIN:VCALENDAR\r\n")
        assert body.endswith("END:VCALENDAR\r\n")
        # Every line in the body must end with CRLF (RFC 5545).
        # Splitting on \r\n should produce only empty trailing string.
        assert "\r\n" in body
        # No bare LF outside the CRLF pairs.
        assert body.replace("\r\n", "") .find("\n") == -1

    @pytest.mark.asyncio
    async def test_ics_only_includes_future_non_cancelled_meetings(
        self, client, book_clubs_enabled, club_with_meetings
    ):
        response = await client.get(
            f"/api/v1/book-clubs/{club_with_meetings.id}/meetings.ics"
        )
        body = response.text
        # Future planned meeting present
        assert "Chapter 1\\, Part A" in body  # comma escaped
        # Past and cancelled excluded
        assert "Past meeting" not in body
        assert "Cancelled" not in body
        # Required event headers
        assert "BEGIN:VEVENT\r\n" in body
        assert "END:VEVENT\r\n" in body
        assert "UID:book-club-meeting-" in body
        assert "DTSTAMP:" in body
        assert "DTSTART:" in body
        assert "DTEND:" in body
        # Location and description escapes
        assert "LOCATION:Branch 1\\, Room 2" in body
        assert "DESCRIPTION:Bring snacks\\;\\nand questions." in body

    @pytest.mark.asyncio
    async def test_ics_escapes_backslash_then_special_chars_in_summary(
        self, client, book_clubs_enabled, club_with_meetings
    ):
        response = await client.get(
            f"/api/v1/book-clubs/{club_with_meetings.id}/meetings.ics"
        )
        body = response.text
        # club name has trailing backslash and comma+semicolon; ensure
        # backslash was doubled first so we don't see lone backslashes
        # escaping the wrong characters.
        assert "SUMMARY:Tuesday Tea\\, Talk\\; & Tomes\\\\: Chapter 1\\, Part A" in body

    @pytest.mark.asyncio
    async def test_ics_empty_meetings_still_valid_vcalendar(
        self, client, book_clubs_enabled, empty_club
    ):
        response = await client.get(
            f"/api/v1/book-clubs/{empty_club.id}/meetings.ics"
        )
        assert response.status_code == 200
        body = response.text
        assert body.startswith("BEGIN:VCALENDAR\r\n")
        assert body.endswith("END:VCALENDAR\r\n")
        # No VEVENT blocks
        assert "BEGIN:VEVENT" not in body
        # Calendar metadata still present
        assert "VERSION:2.0\r\n" in body
        from app.core.config import get_settings

        library_name = get_settings().library_name
        assert f"PRODID:-//{library_name}//Book Club Meetings//EN\r\n" in body
        assert "X-WR-CALNAME:Empty Club Meetings\r\n" in body

    @pytest.mark.asyncio
    async def test_ics_404_when_club_missing(
        self, client, book_clubs_enabled
    ):
        response = await client.get("/api/v1/book-clubs/999999/meetings.ics")
        assert response.status_code == 404
