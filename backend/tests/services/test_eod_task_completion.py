# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for EOD task completion workflow.

Verifies the full lifecycle for each EOD task:
1. Mark task as in-progress
2. Complete the task with task_data (e.g., drawer count, discrepancy notes)
3. Verify task status changes to COMPLETED with duration_seconds tracked
4. Verify completed_by_id is set to the staff member
"""

import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.end_of_day import (
    EODTemplate, EODSession, EODTask, EODSecurityCheck,
    EODTaskType, EODTaskStatus, EODSessionStatus, SecurityCheckType,
)
from app.models.user import User
from app.services.end_of_day_service import EndOfDayService


STAFF_ID = 42


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    session = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def eod_session():
    """Create an EOD session for testing."""
    return EODSession(
        id=1,
        session_code="EOD-TEST1234",
        template_id=1,
        branch_location="Main Branch",
        closing_date=date.today(),
        staff_id=STAFF_ID,
        status=EODSessionStatus.IN_PROGRESS,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )


def _make_task(task_type: EODTaskType, display_name: str) -> EODTask:
    """Helper to create a pending EOD task."""
    return EODTask(
        id=1,
        session_id=1,
        task_type=task_type,
        display_name=display_name,
        status=EODTaskStatus.PENDING,
        task_data={},
        duration_seconds=0,
    )


# =============================================================================
# Close Registers Task
# =============================================================================


class TestCloseRegistersCompletion:
    """Tests for the close registers task completion workflow."""

    @pytest.mark.asyncio
    async def test_close_registers_transitions_to_in_progress(self, mock_db):
        """Verify task is marked IN_PROGRESS before execution."""
        task = _make_task(EODTaskType.CLOSE_REGISTERS, "Close Registers")
        assert task.status == EODTaskStatus.PENDING

        original_close = EndOfDayService._close_registers

        async def capture_in_progress(db, session_id, task_data=None):
            # At this point the task should be IN_PROGRESS
            assert task.status == EODTaskStatus.IN_PROGRESS
            assert task.started_at is not None
            return await original_close(db, session_id, task_data=task_data)

        with patch.object(EndOfDayService, "_close_registers", side_effect=capture_in_progress):
            await EndOfDayService.execute_task(
                db=mock_db, task=task, completed_by_id=STAFF_ID
            )

    @pytest.mark.asyncio
    async def test_close_registers_completes_with_task_data(self, mock_db):
        """Verify close registers stores drawer count and discrepancy notes."""
        task = _make_task(EODTaskType.CLOSE_REGISTERS, "Close Registers")

        staff_data = {
            "drawer_count": 3,
            "total_cash": 542.75,
            "discrepancy_notes": "Register 2 was $1.25 short",
        }

        await EndOfDayService.execute_task(
            db=mock_db,
            task=task,
            completed_by_id=STAFF_ID,
            task_data=staff_data,
        )

        assert task.status == EODTaskStatus.COMPLETED
        assert task.task_data["drawer_count"] == 3
        assert task.task_data["total_cash"] == 542.75
        assert task.task_data["discrepancy_notes"] == "Register 2 was $1.25 short"
        assert task.task_data["status"] == "manual_completion"

    @pytest.mark.asyncio
    async def test_close_registers_sets_completed_by_id(self, mock_db):
        """Verify completed_by_id is set to the staff member."""
        task = _make_task(EODTaskType.CLOSE_REGISTERS, "Close Registers")

        await EndOfDayService.execute_task(
            db=mock_db, task=task, completed_by_id=STAFF_ID
        )

        assert task.completed_by_id == STAFF_ID

    @pytest.mark.asyncio
    async def test_close_registers_tracks_duration(self, mock_db):
        """Verify duration_seconds is computed from started_at to completed_at."""
        task = _make_task(EODTaskType.CLOSE_REGISTERS, "Close Registers")

        await EndOfDayService.execute_task(
            db=mock_db, task=task, completed_by_id=STAFF_ID
        )

        assert task.completed_at is not None
        assert task.started_at is not None
        assert task.duration_seconds >= 0
        expected = int((task.completed_at - task.started_at).total_seconds())
        assert task.duration_seconds == expected

    @pytest.mark.asyncio
    async def test_close_registers_without_task_data(self, mock_db):
        """Verify close registers works with no staff-provided data."""
        task = _make_task(EODTaskType.CLOSE_REGISTERS, "Close Registers")

        await EndOfDayService.execute_task(
            db=mock_db, task=task, completed_by_id=STAFF_ID
        )

        assert task.status == EODTaskStatus.COMPLETED
        assert task.task_data["message"] == "Registers closed by staff"
        assert task.task_data["status"] == "manual_completion"


# =============================================================================
# Process Holds Task
# =============================================================================


class TestProcessHoldsCompletion:
    """Tests for the process holds task completion workflow."""

    @pytest.mark.asyncio
    async def test_process_holds_full_workflow(self, mock_db):
        """Verify full lifecycle: PENDING -> IN_PROGRESS -> COMPLETED."""
        task = _make_task(EODTaskType.PROCESS_HOLDS, "Process Holds")

        holds_data = {"holds_ready": 12, "message": "Identified 12 holds ready for tomorrow's processing"}

        with patch.object(EndOfDayService, "_process_holds", return_value=holds_data):
            await EndOfDayService.execute_task(
                db=mock_db, task=task, completed_by_id=STAFF_ID
            )

        assert task.status == EODTaskStatus.COMPLETED
        assert task.task_data["holds_ready"] == 12
        assert task.completed_by_id == STAFF_ID
        assert task.duration_seconds >= 0
        assert task.completed_at is not None


# =============================================================================
# Send Overdue Notices Task
# =============================================================================


class TestSendOverdueNoticesCompletion:
    """Tests for the send overdue notices task completion workflow."""

    @pytest.mark.asyncio
    async def test_overdue_notices_full_workflow(self, mock_db):
        """Verify overdue notices task completes with correct data."""
        task = _make_task(EODTaskType.SEND_OVERDUE_NOTICES, "Send Overdue Notices")

        notices_data = {
            "overdue_items": 7,
            "notices_queued": 7,
            "failed_sends": 0,
            "message": "Queued 7 overdue notices",
        }

        with patch.object(EndOfDayService, "_send_overdue_notices", return_value=notices_data):
            await EndOfDayService.execute_task(
                db=mock_db, task=task, completed_by_id=STAFF_ID
            )

        assert task.status == EODTaskStatus.COMPLETED
        assert task.task_data["overdue_items"] == 7
        assert task.task_data["notices_queued"] == 7
        assert task.completed_by_id == STAFF_ID
        assert task.duration_seconds >= 0


# =============================================================================
# Backup Confirmation Task
# =============================================================================


class TestBackupConfirmationCompletion:
    """Tests for the backup confirmation task completion workflow."""

    @pytest.mark.asyncio
    async def test_backup_confirmation_full_workflow(self, mock_db, eod_session):
        """Verify backup confirmation completes and tracks staff member."""
        task = _make_task(EODTaskType.BACKUP_CONFIRMATION, "Backup Confirmation")

        mock_db.get = AsyncMock(return_value=eod_session)

        await EndOfDayService.execute_task(
            db=mock_db, task=task, completed_by_id=STAFF_ID
        )

        assert task.status == EODTaskStatus.COMPLETED
        assert task.task_data["backup_status"] == "verified"
        assert task.completed_by_id == STAFF_ID
        assert task.duration_seconds >= 0
        assert task.completed_at is not None


# =============================================================================
# Security Check Task
# =============================================================================


class TestSecurityCheckCompletion:
    """Tests for the security check task completion workflow."""

    @pytest.mark.asyncio
    async def test_security_check_full_workflow(self, mock_db, eod_session):
        """Verify security checks complete with all checks passed."""
        task = _make_task(EODTaskType.SECURITY_CHECK, "Security Checks")

        mock_db.get = AsyncMock(return_value=eod_session)

        await EndOfDayService.execute_task(
            db=mock_db, task=task, completed_by_id=STAFF_ID
        )

        assert task.status == EODTaskStatus.COMPLETED
        assert task.task_data["checks_passed"] == 6
        assert task.task_data["checks_failed"] == 0
        assert task.completed_by_id == STAFF_ID
        assert task.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_security_check_creates_check_records(self, mock_db, eod_session):
        """Verify individual security check records are created."""
        task = _make_task(EODTaskType.SECURITY_CHECK, "Security Checks")

        mock_db.get = AsyncMock(return_value=eod_session)

        await EndOfDayService.execute_task(
            db=mock_db, task=task, completed_by_id=STAFF_ID
        )

        # Should create 6 EODSecurityCheck records (one per check type)
        add_calls = [
            call for call in mock_db.add.call_args_list
            if isinstance(call[0][0], EODSecurityCheck)
        ]
        assert len(add_calls) == 6


# =============================================================================
# Statistics Summary Task
# =============================================================================


class TestStatisticsSummaryCompletion:
    """Tests for the statistics summary task completion workflow."""

    @pytest.mark.asyncio
    async def test_statistics_summary_full_workflow(self, mock_db):
        """Verify statistics summary task populates all metrics."""
        task = _make_task(EODTaskType.STATISTICS_SUMMARY, "Statistics Summary")

        summary_data = {
            "total_checkouts": 150,
            "total_checkins": 148,
            "total_fines": 45.50,
            "message": "Daily summary: 150 checkouts, 148 check-ins, $45.50 in fines",
        }

        with patch.object(EndOfDayService, "_statistics_summary", return_value=summary_data):
            await EndOfDayService.execute_task(
                db=mock_db, task=task, completed_by_id=STAFF_ID
            )

        assert task.status == EODTaskStatus.COMPLETED
        assert task.task_data["total_checkouts"] == 150
        assert task.task_data["total_checkins"] == 148
        assert task.task_data["total_fines"] == 45.50
        assert task.completed_by_id == STAFF_ID
        assert task.duration_seconds >= 0


# =============================================================================
# Tomorrow Events Task
# =============================================================================


class TestTomorrowEventsCompletion:
    """Tests for the tomorrow events task completion workflow."""

    @pytest.mark.asyncio
    async def test_tomorrow_events_full_workflow(self, mock_db):
        """Verify tomorrow events task completes with event list."""
        task = _make_task(EODTaskType.TOMORROW_EVENTS, "Tomorrow's Events Reminder")

        events_data = {
            "event_count": 3,
            "events": [
                {"title": "Story Time", "start_time": "2026-02-27T10:00:00", "location": "Main Branch"},
                {"title": "Book Club", "start_time": "2026-02-27T14:00:00", "location": "Main Branch"},
                {"title": "Tech Help", "start_time": "2026-02-27T16:00:00", "location": "Main Branch"},
            ],
            "message": "3 events scheduled for tomorrow",
        }

        with patch.object(EndOfDayService, "_tomorrow_events", return_value=events_data):
            await EndOfDayService.execute_task(
                db=mock_db, task=task, completed_by_id=STAFF_ID
            )

        assert task.status == EODTaskStatus.COMPLETED
        assert task.task_data["event_count"] == 3
        assert len(task.task_data["events"]) == 3
        assert task.completed_by_id == STAFF_ID
        assert task.duration_seconds >= 0


# =============================================================================
# Holds Pull List Task
# =============================================================================


class TestHoldsPullListCompletion:
    """Tests for the holds pull list task completion workflow."""

    @pytest.mark.asyncio
    async def test_holds_pull_list_full_workflow(self, mock_db):
        """Verify holds pull list task generates list and tracks completion."""
        task = _make_task(EODTaskType.HOLDS_PULL_LIST, "Print Holds Pull List")

        pull_data = {
            "pull_list_generated": True,
            "holds_count": 15,
            "pdf_generated": True,
            "message": "Generated pull list for 15 holds",
        }

        with patch.object(EndOfDayService, "_holds_pull_list", return_value=pull_data):
            await EndOfDayService.execute_task(
                db=mock_db, task=task, completed_by_id=STAFF_ID
            )

        assert task.status == EODTaskStatus.COMPLETED
        assert task.task_data["pull_list_generated"] is True
        assert task.task_data["holds_count"] == 15
        assert task.completed_by_id == STAFF_ID
        assert task.duration_seconds >= 0


# =============================================================================
# Cross-Cutting Concerns: Full Session Task Completion
# =============================================================================


class TestFullSessionTaskCompletion:
    """Integration-style tests verifying multiple tasks in a session."""

    @pytest.mark.asyncio
    async def test_all_tasks_track_duration_seconds(self, mock_db, eod_session):
        """Verify every task type records duration_seconds on completion."""
        mock_results = {
            EODTaskType.CLOSE_REGISTERS: {"message": "Registers closed", "status": "manual_completion"},
            EODTaskType.PROCESS_HOLDS: {"holds_ready": 5, "message": "5 holds"},
            EODTaskType.SEND_OVERDUE_NOTICES: {"overdue_items": 3, "notices_queued": 3, "failed_sends": 0, "message": "3 notices"},
            EODTaskType.BACKUP_CONFIRMATION: {"backup_status": "verified", "message": "Backup OK"},
            EODTaskType.SECURITY_CHECK: {"total_checks": 6, "checks_passed": 6, "checks_failed": 0, "message": "All passed"},
            EODTaskType.STATISTICS_SUMMARY: {"total_checkouts": 10, "total_checkins": 8, "total_fines": 0, "message": "Summary"},
            EODTaskType.TOMORROW_EVENTS: {"event_count": 0, "events": [], "message": "No events"},
            EODTaskType.HOLDS_PULL_LIST: {"pull_list_generated": True, "holds_count": 0, "message": "No holds"},
        }

        method_names = {
            EODTaskType.CLOSE_REGISTERS: "_close_registers",
            EODTaskType.PROCESS_HOLDS: "_process_holds",
            EODTaskType.SEND_OVERDUE_NOTICES: "_send_overdue_notices",
            EODTaskType.BACKUP_CONFIRMATION: "_backup_confirmation",
            EODTaskType.SECURITY_CHECK: "_security_check_prompts",
            EODTaskType.STATISTICS_SUMMARY: "_statistics_summary",
            EODTaskType.TOMORROW_EVENTS: "_tomorrow_events",
            EODTaskType.HOLDS_PULL_LIST: "_holds_pull_list",
        }

        for task_type, result_data in mock_results.items():
            task = _make_task(task_type, task_type.value)
            method = method_names[task_type]

            with patch.object(EndOfDayService, method, return_value=result_data):
                await EndOfDayService.execute_task(
                    db=mock_db, task=task, completed_by_id=STAFF_ID
                )

            assert task.status == EODTaskStatus.COMPLETED, (
                f"{task_type.value} did not complete"
            )
            assert task.duration_seconds >= 0, (
                f"{task_type.value} did not track duration_seconds"
            )
            assert task.completed_by_id == STAFF_ID, (
                f"{task_type.value} did not set completed_by_id"
            )

    @pytest.mark.asyncio
    async def test_all_tasks_set_completed_by_id(self, mock_db):
        """Verify completed_by_id is always set regardless of task type."""
        different_staff = 99
        task = _make_task(EODTaskType.CLOSE_REGISTERS, "Close Registers")

        await EndOfDayService.execute_task(
            db=mock_db, task=task, completed_by_id=different_staff
        )

        assert task.completed_by_id == different_staff

    @pytest.mark.asyncio
    async def test_failed_task_also_sets_completed_by_id(self, mock_db):
        """Verify completed_by_id is set even when a task fails."""
        task = _make_task(EODTaskType.CLOSE_REGISTERS, "Close Registers")

        with patch.object(
            EndOfDayService, "_close_registers",
            side_effect=Exception("Hardware failure"),
        ):
            await EndOfDayService.execute_task(
                db=mock_db, task=task, completed_by_id=STAFF_ID
            )

        assert task.status == EODTaskStatus.FAILED
        assert task.completed_by_id == STAFF_ID
        assert "Hardware failure" in task.error_message

    @pytest.mark.asyncio
    async def test_task_completed_at_is_set(self, mock_db):
        """Verify completed_at timestamp is set on completion."""
        task = _make_task(EODTaskType.CLOSE_REGISTERS, "Close Registers")
        before = datetime.now(timezone.utc)

        await EndOfDayService.execute_task(
            db=mock_db, task=task, completed_by_id=STAFF_ID
        )

        after = datetime.now(timezone.utc)
        assert task.completed_at is not None
        assert before <= task.completed_at <= after

    @pytest.mark.asyncio
    async def test_task_data_populated_on_completion(self, mock_db):
        """Verify task_data is non-empty after successful completion."""
        task = _make_task(EODTaskType.CLOSE_REGISTERS, "Close Registers")

        await EndOfDayService.execute_task(
            db=mock_db, task=task, completed_by_id=STAFF_ID
        )

        assert task.task_data is not None
        assert isinstance(task.task_data, dict)
        assert len(task.task_data) > 0

    @pytest.mark.asyncio
    async def test_session_complete_after_all_tasks(self, mock_db, eod_session):
        """Verify session can be completed after all tasks are done."""
        mock_db.get = AsyncMock(return_value=eod_session)

        # Use MagicMock for results since scalar() is a sync call
        total_r = MagicMock()
        total_r.scalar.return_value = 2
        completed_r = MagicMock()
        completed_r.scalar.return_value = 2
        failed_r = MagicMock()
        failed_r.scalar.return_value = 0
        skipped_r = MagicMock()
        skipped_r.scalar.return_value = 0

        mock_db.execute = AsyncMock(
            side_effect=[total_r, completed_r, failed_r, skipped_r]
        )

        session = await EndOfDayService.complete_session(db=mock_db, session_id=1)

        assert session.status == EODSessionStatus.COMPLETED
        assert session.completed_at is not None
        assert session.total_duration_seconds > 0
        assert session.completed_tasks == 2
        assert session.failed_tasks == 0
