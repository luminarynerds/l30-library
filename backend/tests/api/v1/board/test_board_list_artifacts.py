# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for artifact URLs (minutes/recording/agenda-packet) on the public
board meetings LIST endpoint.

Covers the additions in `BoardMeetingListItem` so the frontend can render
artifact badges without a follow-up fetch per meeting.
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.board import BoardMeeting
from app.models.board.minutes import BoardMinutes


def _find_meeting(payload, meeting_id):
    for m in payload:
        if m["id"] == meeting_id:
            return m
    raise AssertionError(f"meeting {meeting_id} not in list response")


@pytest.mark.asyncio
class TestPublicMeetingsListArtifactUrls:
    """`/api/v1/board/meetings` should surface artifact URLs per meeting."""

    async def test_approved_minutes_surfaces_minutes_and_recording_urls(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        meeting = BoardMeeting(
            meeting_type="regular",
            title="Approved-minutes meeting",
            scheduled_date=datetime.now(timezone.utc) - timedelta(days=14),
            notice_status="posted",
        )
        test_db.add(meeting)
        await test_db.commit()
        await test_db.refresh(meeting)

        test_db.add(
            BoardMinutes(
                meeting_id=meeting.id,
                status="approved",
                approved=True,
                recording_url="https://zoom.us/rec/approved-meeting",
            )
        )
        await test_db.commit()

        resp = await client.get("/api/v1/board/meetings")
        assert resp.status_code == 200
        m = _find_meeting(resp.json(), meeting.id)
        assert m["minutes_url"] == f"/board/meetings/{meeting.id}#minutes"
        assert m["recording_url"] == "https://zoom.us/rec/approved-meeting"
        assert m["agenda_packet_url"] is None

    async def test_draft_minutes_returns_null_for_both(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        meeting = BoardMeeting(
            meeting_type="regular",
            title="Draft-minutes meeting",
            scheduled_date=datetime.now(timezone.utc) - timedelta(days=7),
            notice_status="posted",
        )
        test_db.add(meeting)
        await test_db.commit()
        await test_db.refresh(meeting)

        test_db.add(
            BoardMinutes(
                meeting_id=meeting.id,
                status="draft",
                approved=False,
                recording_url="https://zoom.us/rec/draft-not-yet-public",
            )
        )
        await test_db.commit()

        resp = await client.get("/api/v1/board/meetings")
        assert resp.status_code == 200
        m = _find_meeting(resp.json(), meeting.id)
        assert m["minutes_url"] is None
        assert m["recording_url"] is None
        assert m["agenda_packet_url"] is None

    async def test_no_minutes_row_returns_nulls_without_greenlet_500(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        """Meeting with NO BoardMinutes attached must not 500 with MissingGreenlet
        when the response serializer touches the relationship.
        """
        meeting = BoardMeeting(
            meeting_type="regular",
            title="No-minutes meeting",
            scheduled_date=datetime.now(timezone.utc) + timedelta(days=3),
            notice_status="posted",
        )
        test_db.add(meeting)
        await test_db.commit()
        await test_db.refresh(meeting)

        resp = await client.get("/api/v1/board/meetings")
        assert resp.status_code == 200
        m = _find_meeting(resp.json(), meeting.id)
        assert m["minutes_url"] is None
        assert m["recording_url"] is None
        assert m["agenda_packet_url"] is None

    async def test_approved_minutes_with_empty_recording_url(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        """Approved minutes but empty string recording_url -> recording_url null
        (truthy check, not just `is not None`).
        """
        meeting = BoardMeeting(
            meeting_type="regular",
            title="Approved no-recording meeting",
            scheduled_date=datetime.now(timezone.utc) - timedelta(days=21),
            notice_status="posted",
        )
        test_db.add(meeting)
        await test_db.commit()
        await test_db.refresh(meeting)

        test_db.add(
            BoardMinutes(
                meeting_id=meeting.id,
                status="approved",
                approved=True,
                recording_url="",
            )
        )
        await test_db.commit()

        resp = await client.get("/api/v1/board/meetings")
        assert resp.status_code == 200
        m = _find_meeting(resp.json(), meeting.id)
        assert m["minutes_url"] == f"/board/meetings/{meeting.id}#minutes"
        assert m["recording_url"] is None
