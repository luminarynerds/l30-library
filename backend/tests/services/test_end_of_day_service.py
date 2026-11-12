# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for EndOfDayService.

Tests the core functionality of end-of-day automation including:
- Session creation and management
- Task execution
- Auto-logout scheduling
- Statistics generation
"""

import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.end_of_day import (
    EODTemplate, EODSession, EODTask, EODSecurityCheck, EODStatistics,
    EODTaskType, EODTaskStatus, EODSessionStatus, SecurityCheckType
)
from app.models.user import User, UserRole
from app.services.end_of_day_service import EndOfDayService
from app.core.database import AsyncSessionLocal


@pytest.fixture
async def mock_db():
    """Create a mock database session"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
async def test_user(mock_db):
    """Create a test user"""
    user = User(
        id=1,
        email="staff@example.com",
        first_name="Test",
        last_name="Staff",
        role=UserRole.STAFF,
    )
    return user


class TestEODSessionCreation:
    """Tests for creating EOD sessions"""

    @pytest.mark.asyncio
    async def test_create_closing_session(self, mock_db, test_user):
        """Test creating a new closing session"""
        # Mock the template lookup
        mock_db.execute = AsyncMock()
        mock_db.flush = AsyncMock()

        # Mock template query result
        template = EODTemplate(
            id=1,
            name="Main Branch Default",
            branch_location="Main Branch",
            is_active=True,
            estimated_duration_minutes=5,
            task_configs=[
                {"task_type": "close_registers", "required": True},
                {"task_type": "process_holds", "required": True},
            ],
        )

        # db.execute() is async but the Result object it returns is sync
        # (scalars()/first()/all() are plain methods) -- must be MagicMock,
        # not AsyncMock, or those calls return unawaited coroutines.
        session_result = MagicMock()
        session_result.scalars.return_value.first.return_value = template
        mock_db.execute.return_value = session_result

        # Create session
        session = await EndOfDayService.create_closing_session(
            db=mock_db,
            branch_location="Main Branch",
            staff_id=test_user.id,
        )

        # Assertions
        assert session is not None
        assert session.branch_location == "Main Branch"
        assert session.staff_id == test_user.id
        assert session.status == EODSessionStatus.STARTED
        assert "EOD-" in session.session_code

    @pytest.mark.asyncio
    async def test_create_session_with_assisted_staff(self, mock_db, test_user):
        """Test creating session with assisted staff"""
        assisted_ids = [2, 3, 4]

        session = EODSession(
            session_code="EOD-ABC12345",
            template_id=1,
            branch_location="Main Branch",
            closing_date=date.today(),
            staff_id=test_user.id,
            assisted_by_ids=assisted_ids,
            status=EODSessionStatus.STARTED,
        )

        assert session.assisted_by_ids == assisted_ids
        assert len(session.assisted_by_ids) == 3


class TestEODTaskExecution:
    """Tests for executing EOD tasks"""

    @pytest.mark.asyncio
    async def test_close_registers_task(self, mock_db):
        """Test close registers task"""
        result = await EndOfDayService._close_registers(db=mock_db, session_id=1)

        assert result is not None
        assert "message" in result
        assert result["status"] == "manual_completion"

    @pytest.mark.asyncio
    async def test_process_holds_task(self, mock_db):
        """Test process holds task"""
        mock_db.get = AsyncMock()
        mock_db.execute = AsyncMock()

        # Mock session
        session = EODSession(
            id=1,
            branch_location="Main Branch",
            staff_id=1,
            closing_date=date.today(),
            template_id=1,
            session_code="EOD-TEST"
        )
        mock_db.get.return_value = session

        # Mock count result
        count_result = MagicMock()
        count_result.scalar.return_value = 5
        mock_db.execute.return_value = count_result

        result = await EndOfDayService._process_holds(db=mock_db, session_id=1)

        assert "holds_ready" in result
        assert result["holds_ready"] == 5

    @pytest.mark.asyncio
    async def test_statistics_summary_generation(self, mock_db):
        """Test statistics summary generation"""
        mock_db.get = AsyncMock()
        mock_db.execute = AsyncMock()

        # Mock session
        session = EODSession(
            id=1,
            branch_location="Main Branch",
            staff_id=1,
            closing_date=date.today(),
            template_id=1,
            session_code="EOD-TEST"
        )
        mock_db.get.return_value = session

        # Mock count results
        count_result = MagicMock()
        count_result.scalar.side_effect = [150, 148, Decimal("45.50")]
        mock_db.execute.return_value = count_result

        result = await EndOfDayService._statistics_summary(db=mock_db, session_id=1)

        assert "message" in result
        assert result["total_checkouts"] == 150
        assert result["total_checkins"] == 148

    @pytest.mark.asyncio
    async def test_security_check_prompts(self, mock_db):
        """Test security check prompts generation"""
        mock_db.get = AsyncMock()
        mock_db.add = AsyncMock()
        mock_db.flush = AsyncMock()

        # Mock session
        session = EODSession(
            id=1,
            branch_location="Main Branch",
            staff_id=1,
            closing_date=date.today(),
            template_id=1,
            session_code="EOD-TEST"
        )
        mock_db.get.return_value = session

        result = await EndOfDayService._security_check_prompts(
            db=mock_db,
            session_id=1,
            completed_by_id=1
        )

        assert result is not None
        assert "checks_passed" in result
        assert result["checks_passed"] > 0

    @pytest.mark.asyncio
    async def test_tomorrow_events_reminder(self, mock_db):
        """Test tomorrow's events reminder generation"""
        mock_db.get = AsyncMock()
        mock_db.execute = AsyncMock()

        # Mock session
        session = EODSession(
            id=1,
            branch_location="Main Branch",
            staff_id=1,
            closing_date=date.today(),
            template_id=1,
            session_code="EOD-TEST"
        )
        mock_db.get.return_value = session

        # Mock events query
        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = events_result

        result = await EndOfDayService._tomorrow_events(db=mock_db, session_id=1)

        assert "event_count" in result
        assert result["event_count"] == 0


class TestEODSessionManagement:
    """Tests for managing EOD sessions"""

    @pytest.mark.asyncio
    async def test_complete_session(self, mock_db):
        """Test completing an EOD session"""
        # Create a session
        session = EODSession(
            id=1,
            session_code="EOD-TEST",
            template_id=1,
            branch_location="Main Branch",
            closing_date=date.today(),
            staff_id=1,
            status=EODSessionStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            total_tasks=8,
        )

        mock_db.get = AsyncMock(return_value=session)
        mock_db.execute = AsyncMock()

        # Mock task counts
        count_result = MagicMock()
        count_result.scalar.side_effect = [8, 7, 1, 0]  # total, completed, failed, skipped
        mock_db.execute.return_value = count_result
        mock_db.flush = AsyncMock()

        completed_session = await EndOfDayService.complete_session(db=mock_db, session_id=1)

        assert completed_session.status == EODSessionStatus.COMPLETED
        assert completed_session.completed_at is not None
        assert completed_session.total_duration_seconds > 0

    @pytest.mark.asyncio
    async def test_schedule_auto_logout(self, mock_db):
        """Test scheduling auto-logout"""
        session = EODSession(
            id=1,
            session_code="EOD-TEST",
            template_id=1,
            branch_location="Main Branch",
            closing_date=date.today(),
            staff_id=1,
            status=EODSessionStatus.COMPLETED,
        )

        mock_db.get = AsyncMock(return_value=session)
        mock_db.flush = AsyncMock()

        await EndOfDayService.schedule_auto_logout(
            db=mock_db,
            session_id=1,
            logout_delay_minutes=5
        )

        assert session.auto_logout_at is not None
        assert session.auto_logout_at > datetime.now(timezone.utc)


class TestEODStatistics:
    """Tests for EOD statistics"""

    @pytest.mark.asyncio
    async def test_create_daily_statistics(self, mock_db):
        """Test creating daily statistics"""
        mock_db.execute = AsyncMock()
        mock_db.add = AsyncMock()
        mock_db.flush = AsyncMock()

        # Mock session count
        count_result = MagicMock()
        count_result.scalar.return_value = 3
        mock_db.execute.return_value = count_result

        stats = await EndOfDayService.create_daily_statistics(
            db=mock_db,
            branch_location="Main Branch",
            closing_date=date.today()
        )

        assert stats is not None
        assert stats.closing_date == date.today()
        assert stats.branch_location == "Main Branch"
        assert stats.total_sessions == 3


class TestEODErrorHandling:
    """Tests for error handling"""

    @pytest.mark.asyncio
    async def test_task_execution_error_handling(self, mock_db):
        """Test error handling during task execution"""
        task = EODTask(
            id=1,
            session_id=1,
            task_type=EODTaskType.CLOSE_REGISTERS,
            display_name="Close Registers",
            status=EODTaskStatus.PENDING,
        )

        # Mock a task that will fail
        with patch.object(EndOfDayService, '_close_registers', side_effect=Exception("Test error")):
            await EndOfDayService.execute_task(
                db=mock_db,
                task=task,
                completed_by_id=1
            )

        assert task.status == EODTaskStatus.FAILED
        assert task.error_message is not None
        assert "Test error" in task.error_message

    @pytest.mark.asyncio
    async def test_session_creation_with_missing_template(self, mock_db):
        """Test session creation when no template exists"""
        # Mock no template found, then successful creation
        template_result = MagicMock()
        template_result.scalars.return_value.first.return_value = None

        mock_db.execute = AsyncMock(return_value=template_result)
        mock_db.flush = AsyncMock()
        mock_db.add = AsyncMock()

        session = await EndOfDayService.create_closing_session(
            db=mock_db,
            branch_location="Main Branch",
            staff_id=1,
        )

        # Should create default template
        assert session is not None
        assert session.branch_location == "Main Branch"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
