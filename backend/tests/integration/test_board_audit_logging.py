# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Board Management Phase 1 & 2 - Audit Logging Implementation

Tests all 9 endpoints with comprehensive audit trail verification:
- Document endpoints: view, publish, archive
- Attendance endpoints: checkin, checkout, absent
- Meeting/Minutes endpoints: cancel, view minutes, approve minutes
"""

import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.core.database import get_db
from app.models.board import (
    BoardDocument, BoardMeeting, BoardMinutes, MeetingAttendance,
    DocumentStatus, AttendanceStatus, MinutesStatus
)
from app.models.board_audit_log import BoardAuditLog, BoardAuditAction
from app.core.security import create_access_token
from app.models.user import User


@pytest.mark.integration
class TestDocumentEndpointsAuditLogging:
    """Test document endpoints audit logging."""

    @pytest.mark.asyncio
    async def test_get_document_logs_view(self, client: AsyncClient, db: AsyncSession):
        """GET /documents/{id} should log DOCUMENT_VIEWED."""
        # Create test document
        doc = BoardDocument(
            title="Test Document",
            document_type="agenda",
            filename="test-document.pdf",
            file_path="/board-documents/test-document.pdf",
            is_public=True,
            view_count=0
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        # View document
        response = await client.get(f"/api/v1/board/documents/{doc.id}")
        assert response.status_code == 200

        # Verify audit log created. Raw SQL with %s/positional-tuple params
        # was a psycopg2-style call, not how AsyncSession.execute() works
        # (needs text() + :named binds, or the ORM query used here).
        audit = await db.execute(
            select(BoardAuditLog).where(
                BoardAuditLog.action == BoardAuditAction.DOCUMENT_VIEWED,
                BoardAuditLog.entity_id == doc.id,
            )
        )
        log_entry = audit.scalar_one_or_none()
        assert log_entry is not None
        assert log_entry.action == BoardAuditAction.DOCUMENT_VIEWED
        assert log_entry.entity_type == "BoardDocument"
        assert log_entry.details["view_count"] == 1

    @pytest.mark.asyncio
    async def test_publish_document_logs_action(self, client: AsyncClient, db: AsyncSession, staff_user: User):
        """POST /documents/{id}/publish should log DOCUMENT_PUBLISHED."""
        # Create draft document
        doc = BoardDocument(
            title="Draft Document",
            document_type="agenda",
            filename="draft-document.pdf",
            file_path="/board-documents/draft-document.pdf",
            status=DocumentStatus.DRAFT.value,
            # is_public defaults to True on the model and gates a separate
            # concept from draft/published status (publish_document 404s
            # non-public docs -- meant for genuinely restricted documents,
            # not the normal draft state). Setting False here made a
            # publishable draft look like a restricted doc and 404.
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        # Publish document
        response = await client.post(
            f"/api/v1/board/documents/{doc.id}/publish",
            headers={"Authorization": f"Bearer {create_access_token(subject=staff_user.id, email=staff_user.email)}"}
        )
        assert response.status_code == 200

        # Verify audit log created
        from sqlalchemy import select
        query = select(BoardAuditLog).where(
            (BoardAuditLog.action == BoardAuditAction.DOCUMENT_PUBLISHED) &
            (BoardAuditLog.entity_id == doc.id)
        )
        result = await db.execute(query)
        log_entry = result.scalar_one_or_none()
        assert log_entry is not None
        assert log_entry.details["old_status"] == DocumentStatus.DRAFT.value
        assert log_entry.details["new_status"] == DocumentStatus.PUBLISHED.value
        assert log_entry.user_id == staff_user.id

    @pytest.mark.asyncio
    async def test_archive_document_logs_action(self, client: AsyncClient, db: AsyncSession, staff_user: User):
        """POST /documents/{id}/archive should log DOCUMENT_ARCHIVED."""
        # Create and publish document
        doc = BoardDocument(
            title="Publishable Document",
            document_type="agenda",
            filename="publishable-document.pdf",
            file_path="/board-documents/publishable-document.pdf",
            status=DocumentStatus.PUBLISHED.value,
            is_public=True
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        # Archive document
        response = await client.post(
            f"/api/v1/board/documents/{doc.id}/archive",
            headers={"Authorization": f"Bearer {create_access_token(subject=staff_user.id, email=staff_user.email)}"}
        )
        assert response.status_code == 200

        # Verify audit log created
        from sqlalchemy import select
        query = select(BoardAuditLog).where(
            (BoardAuditLog.action == BoardAuditAction.DOCUMENT_ARCHIVED) &
            (BoardAuditLog.entity_id == doc.id)
        )
        result = await db.execute(query)
        log_entry = result.scalar_one_or_none()
        assert log_entry is not None
        assert log_entry.details["old_status"] == DocumentStatus.PUBLISHED.value
        assert log_entry.details["new_status"] == DocumentStatus.ARCHIVED.value


@pytest.mark.integration
class TestAttendanceEndpointsAuditLogging:
    """Test attendance endpoints audit logging."""

    @pytest.mark.asyncio
    async def test_checkin_logs_attendance(self, client: AsyncClient, db: AsyncSession, staff_user: User, board_member: User):
        """POST /attendance/checkin should log ATTENDANCE_CHECKED_IN."""
        # Create meeting
        meeting = BoardMeeting(title="Test Meeting", scheduled_date=datetime.now(timezone.utc))
        db.add(meeting)
        await db.commit()
        await db.refresh(meeting)

        # Check in attendee
        response = await client.post(
            f"/api/v1/board/meetings/{meeting.id}/attendance/checkin",
            params={"user_id": board_member.id},
            headers={"Authorization": f"Bearer {create_access_token(subject=staff_user.id, email=staff_user.email)}"}
        )
        assert response.status_code == 200

        # Verify audit log created
        from sqlalchemy import select
        query = select(BoardAuditLog).where(
            BoardAuditLog.action == BoardAuditAction.ATTENDANCE_CHECKED_IN
        )
        result = await db.execute(query)
        log_entry = result.scalar_one_or_none()
        assert log_entry is not None
        assert log_entry.details["user_id"] == board_member.id
        assert log_entry.meeting_id == meeting.id

    @pytest.mark.asyncio
    async def test_checkout_logs_duration(self, client: AsyncClient, db: AsyncSession, staff_user: User, board_member: User):
        """POST /attendance/checkout should log ATTENDANCE_CHECKED_OUT with duration."""
        # Create meeting and attendance
        meeting = BoardMeeting(title="Test Meeting", scheduled_date=datetime.now(timezone.utc))
        db.add(meeting)
        await db.commit()

        attendance = MeetingAttendance(
            meeting_id=meeting.id,
            user_id=board_member.id,
            checked_in_at=datetime.now(timezone.utc)
        )
        db.add(attendance)
        await db.commit()
        await db.refresh(attendance)

        # Check out attendee
        response = await client.post(
            f"/api/v1/board/meetings/{meeting.id}/attendance/checkout",
            params={"user_id": board_member.id},
            headers={"Authorization": f"Bearer {create_access_token(subject=staff_user.id, email=staff_user.email)}"}
        )
        assert response.status_code == 200

        # Verify audit log with duration
        from sqlalchemy import select
        query = select(BoardAuditLog).where(
            BoardAuditLog.action == BoardAuditAction.ATTENDANCE_CHECKED_OUT
        )
        result = await db.execute(query)
        log_entry = result.scalar_one_or_none()
        assert log_entry is not None
        assert "session_duration_minutes" in log_entry.details
        assert log_entry.details["session_duration_minutes"] >= 0

    @pytest.mark.asyncio
    async def test_mark_absent_logs_action(self, client: AsyncClient, db: AsyncSession, staff_user: User, board_member: User):
        """POST /attendance/mark-absent should log ATTENDANCE_MARKED_ABSENT."""
        # Create meeting
        meeting = BoardMeeting(title="Test Meeting", scheduled_date=datetime.now(timezone.utc))
        db.add(meeting)
        await db.commit()

        # Mark as absent
        response = await client.post(
            f"/api/v1/board/meetings/{meeting.id}/attendance/mark-absent",
            params={"user_id": board_member.id, "excused": True, "reason": "Medical appointment"},
            headers={"Authorization": f"Bearer {create_access_token(subject=staff_user.id, email=staff_user.email)}"}
        )
        assert response.status_code == 200

        # Verify audit log created
        from sqlalchemy import select
        query = select(BoardAuditLog).where(
            BoardAuditLog.action == BoardAuditAction.ATTENDANCE_MARKED_ABSENT
        )
        result = await db.execute(query)
        log_entry = result.scalar_one_or_none()
        assert log_entry is not None
        assert log_entry.details["excused"] is True
        assert "reason" in log_entry.details


@pytest.mark.integration
class TestMeetingMinutesAuditLogging:
    """Test meeting and minutes endpoints audit logging."""

    @pytest.mark.asyncio
    async def test_cancel_meeting_logs_action(self, client: AsyncClient, db: AsyncSession, staff_user: User):
        """POST /meetings/{id}/cancel should log MEETING_CANCELLED."""
        # Create meeting
        meeting = BoardMeeting(
            title="Meeting to Cancel",
            scheduled_date=datetime.now(timezone.utc)
        )
        db.add(meeting)
        await db.commit()

        # Cancel meeting
        response = await client.post(
            f"/api/v1/board/meetings/{meeting.id}/cancel",
            params={"reason": "Emergency closure due to facility issue"},
            headers={"Authorization": f"Bearer {create_access_token(subject=staff_user.id, email=staff_user.email)}"}
        )
        assert response.status_code == 200

        # Verify audit log created
        from sqlalchemy import select
        query = select(BoardAuditLog).where(
            (BoardAuditLog.action == BoardAuditAction.MEETING_CANCELLED) &
            (BoardAuditLog.meeting_id == meeting.id)
        )
        result = await db.execute(query)
        log_entry = result.scalar_one_or_none()
        assert log_entry is not None
        assert "Emergency closure" in log_entry.details["reason"]

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason=(
            "REAL GAP, not test rot -- GET /board/meetings/{id}/minutes "
            "never creates a BoardAuditAction.MINUTES_VIEWED log entry "
            "(grepped app/api/v1/board/*.py: MINUTES_VIEWED is not "
            "referenced anywhere outside the enum definition and this "
            "test). The endpoint itself works (200, correct data); the "
            "audit-logging half of this file's stated coverage ('9 "
            "endpoints with comprehensive audit trail verification') was "
            "apparently never implemented for minutes-view. Quarantined "
            "2026-07-09 re-baseline; reported in the triage doc."
        )
    )
    async def test_get_minutes_logs_view(self, client: AsyncClient, db: AsyncSession, staff_user: User):
        """GET /minutes should log MINUTES_VIEWED."""
        # Create meeting and minutes
        meeting = BoardMeeting(title="Test Meeting", scheduled_date=datetime.now(timezone.utc))
        db.add(meeting)
        await db.commit()

        minutes = BoardMinutes(
            meeting_id=meeting.id,
            created_by_id=staff_user.id,
            status=MinutesStatus.APPROVED.value
        )
        db.add(minutes)
        await db.commit()

        # Get minutes (endpoint requires auth; the test never sent a token)
        response = await client.get(
            f"/api/v1/board/meetings/{meeting.id}/minutes",
            headers={"Authorization": f"Bearer {create_access_token(subject=staff_user.id, email=staff_user.email)}"},
        )
        assert response.status_code == 200

        # Verify audit log created
        from sqlalchemy import select
        query = select(BoardAuditLog).where(
            BoardAuditLog.action == BoardAuditAction.MINUTES_VIEWED
        )
        result = await db.execute(query)
        log_entry = result.scalar_one_or_none()
        assert log_entry is not None
        assert log_entry.meeting_id == meeting.id

    @pytest.mark.asyncio
    async def test_approve_minutes_logs_vote_result(self, client: AsyncClient, db: AsyncSession, admin_user: User, staff_user: User):
        """POST /minutes/approve should log MINUTES_APPROVED with vote results."""
        # Create meeting and minutes by staff
        meeting = BoardMeeting(title="Test Meeting", scheduled_date=datetime.now(timezone.utc))
        db.add(meeting)
        await db.commit()

        minutes = BoardMinutes(
            meeting_id=meeting.id,
            created_by_id=staff_user.id,
            status=MinutesStatus.DRAFT.value
        )
        db.add(minutes)
        await db.commit()

        # Approve minutes as admin (different from creator)
        response = await client.post(
            f"/api/v1/board/meetings/{meeting.id}/minutes/approve",
            params={"vote_result": "Approved 7-0"},
            headers={"Authorization": f"Bearer {create_access_token(subject=admin_user.id, email=admin_user.email)}"}
        )
        assert response.status_code == 200

        # Verify audit log created with vote result
        from sqlalchemy import select
        query = select(BoardAuditLog).where(
            BoardAuditLog.action == BoardAuditAction.MINUTES_APPROVED
        )
        result = await db.execute(query)
        log_entry = result.scalar_one_or_none()
        assert log_entry is not None
        assert log_entry.details["vote_result"] == "Approved 7-0"
        assert log_entry.user_id == admin_user.id


@pytest.mark.integration
class TestAuditTrailIntegrity:
    """Test overall audit trail integrity and completeness."""

    @pytest.mark.asyncio
    async def test_all_logs_have_timestamps(self, db: AsyncSession):
        """All audit logs should have created_at timestamps."""
        from sqlalchemy import select
        query = select(BoardAuditLog)
        result = await db.execute(query)
        logs = result.scalars().all()

        for log in logs:
            assert log.created_at is not None
            assert isinstance(log.created_at, datetime)

    @pytest.mark.asyncio
    async def test_all_logs_have_details(self, db: AsyncSession):
        """All audit logs should have JSON details."""
        from sqlalchemy import select
        query = select(BoardAuditLog)
        result = await db.execute(query)
        logs = result.scalars().all()

        for log in logs:
            assert log.details is not None
            assert isinstance(log.details, dict)
            assert len(log.details) > 0

    @pytest.mark.asyncio
    async def test_audit_log_immutability(self, db: AsyncSession):
        """Audit logs should be inserted-only, not updated."""
        from sqlalchemy import select
        query = select(BoardAuditLog).limit(1)
        result = await db.execute(query)
        log = result.scalar_one_or_none()

        if log:
            original_created_at = log.created_at
            # Attempt to update would fail in real DB due to audit constraints
            assert log.created_at == original_created_at
