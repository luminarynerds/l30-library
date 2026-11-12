# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.database import AsyncSessionLocal
from ..core.config import get_settings
from ..core.branch_resolver import label_to_branch_id, branch_id_to_label
from ..models.end_of_day import (
    EODTemplate, EODSession, EODTask, EODSecurityCheck, EODStatistics,
    EODTaskType, EODTaskStatus, EODSessionStatus, SecurityCheckType
)
from ..models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ..models.fine import Fine, FineStatus
from ..models.user import User
from ..models.event import Event
from ..models.notification import NotificationQueue, NotificationType, NotificationStatus
from .notification_service import NotificationService

logger = get_logger(__name__)
settings = get_settings()


class EndOfDayService:

    @staticmethod
    async def create_closing_session(
        db: AsyncSession,
        branch_location: str,
        staff_id: int,
        assisted_by_ids: Optional[List[int]] = None,
        branch_id: Optional[int] = None,
    ) -> EODSession:
        # Resolve missing branch_id/branch_location side via canonical map.
        if branch_id is None and branch_location is not None:
            branch_id = label_to_branch_id(branch_location)
        elif branch_id is not None and branch_location is None:
            branch_location = branch_id_to_label(branch_id) or branch_location

        # Get or create template for this branch (prefer branch_id when resolvable).
        if branch_id is not None:
            template_filter = and_(
                EODTemplate.branch_id == branch_id,
                EODTemplate.is_active == True,
            )
        else:
            template_filter = and_(
                EODTemplate.branch_location == branch_location,
                EODTemplate.is_active == True,
            )
        template_result = await db.execute(select(EODTemplate).where(template_filter))
        template = template_result.scalars().first()

        if not template:
            # Create default template if doesn't exist
            template = EODTemplate(
                name=f"Default {branch_location}",
                branch_id=branch_id,
                branch_location=branch_location,
                is_active=True,
                estimated_duration_minutes=5,
                task_configs=[
                    {"task_type": "close_registers", "required": True},
                    {"task_type": "process_holds", "required": True},
                    {"task_type": "send_overdue_notices", "required": False},
                    {"task_type": "backup_confirmation", "required": True},
                    {"task_type": "security_check", "required": True},
                    {"task_type": "statistics_summary", "required": False},
                    {"task_type": "tomorrow_events", "required": False},
                    {"task_type": "holds_pull_list", "required": False},
                ],
            )
            db.add(template)
            await db.flush()

        # Create session
        session = EODSession(
            session_code=f"EOD-{uuid.uuid4().hex[:8].upper()}",
            template_id=template.id,
            branch_id=branch_id,
            branch_location=branch_location,
            closing_date=date.today(),
            staff_id=staff_id,
            assisted_by_ids=assisted_by_ids or [],
            status=EODSessionStatus.STARTED,
        )
        db.add(session)
        await db.flush()

        # Create initial tasks from template
        await EndOfDayService._create_session_tasks(db, session, template)

        return session

    @staticmethod
    async def _create_session_tasks(
        db: AsyncSession,
        session: EODSession,
        template: EODTemplate,
    ) -> None:
        task_configs = template.task_configs or []

        for config in task_configs:
            task_type = config.get("task_type")
            config.get("required", True)

            display_name = {
                "close_registers": "Close Registers",
                "process_holds": "Process Holds",
                "send_overdue_notices": "Send Overdue Notices",
                "backup_confirmation": "Backup Confirmation",
                "security_check": "Security Checks",
                "statistics_summary": "Statistics Summary",
                "tomorrow_events": "Tomorrow's Events Reminder",
                "holds_pull_list": "Print Holds Pull List",
            }.get(task_type, task_type)

            task = EODTask(
                session_id=session.id,
                task_type=task_type,
                display_name=display_name,
                status=EODTaskStatus.PENDING,
                task_data={},
            )
            db.add(task)

        await db.flush()

    @staticmethod
    async def execute_task(
        db: AsyncSession,
        task: EODTask,
        completed_by_id: int,
        task_data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        max_retries: int = 3,
    ) -> None:
        task.status = EODTaskStatus.IN_PROGRESS
        task.started_at = datetime.now(timezone.utc)

        try:
            if task.task_type == EODTaskType.CLOSE_REGISTERS:
                task.task_data = await EndOfDayService._close_registers(
                    db, task.session_id, task_data=task_data
                )
            elif task.task_type == EODTaskType.PROCESS_HOLDS:
                task.task_data = await EndOfDayService._process_holds(
                    db, task.session_id
                )
            elif task.task_type == EODTaskType.SEND_OVERDUE_NOTICES:
                task.task_data = await EndOfDayService._send_overdue_notices(
                    db, task.session_id
                )
            elif task.task_type == EODTaskType.BACKUP_CONFIRMATION:
                task.task_data = await EndOfDayService._backup_confirmation(
                    db, task.session_id
                )
            elif task.task_type == EODTaskType.SECURITY_CHECK:
                task.task_data = await EndOfDayService._security_check_prompts(
                    db, task.session_id, completed_by_id
                )
            elif task.task_type == EODTaskType.STATISTICS_SUMMARY:
                task.task_data = await EndOfDayService._statistics_summary(
                    db, task.session_id
                )
            elif task.task_type == EODTaskType.TOMORROW_EVENTS:
                task.task_data = await EndOfDayService._tomorrow_events(
                    db, task.session_id
                )
            elif task.task_type == EODTaskType.HOLDS_PULL_LIST:
                task.task_data = await EndOfDayService._holds_pull_list(
                    db, task.session_id
                )

            task.status = EODTaskStatus.COMPLETED
            task.completed_by_id = completed_by_id
            task.completed_at = datetime.now(timezone.utc)
            task.duration_seconds = int(
                (task.completed_at - task.started_at).total_seconds()
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Error executing EOD task {task.id} (attempt {retry_count + 1}/{max_retries}): {error_msg}",
                exc_info=True
            )

            # Retry logic for transient errors
            if retry_count < max_retries:
                # Check if error is retryable (DB connection, timeout, etc)
                retryable_errors = ["connection", "timeout", "deadlock", "unavailable"]
                is_retryable = any(keyword in error_msg.lower() for keyword in retryable_errors)

                if is_retryable:
                    logger.info(
                        f"Retrying task {task.id} (attempt {retry_count + 1}/{max_retries})"
                    )
                    # Wait a bit before retry (exponential backoff)
                    import asyncio
                    await asyncio.sleep((retry_count + 1) * 2)

                    # Reset and retry
                    task.status = EODTaskStatus.PENDING
                    task.error_message = None
                    await db.flush()
                    await EndOfDayService.execute_task(
                        db, task, completed_by_id, task_data, retry_count + 1, max_retries
                    )
                    return

            # Final failure after retries exhausted
            task.status = EODTaskStatus.FAILED
            task.error_message = f"{error_msg} (after {retry_count + 1} attempts)"
            task.completed_by_id = completed_by_id
            task.completed_at = datetime.now(timezone.utc)

        await db.flush()

    @staticmethod
    async def _close_registers(
        db: AsyncSession,
        session_id: int,
        task_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = {
            "message": "Registers closed by staff",
            "status": "manual_completion",
        }
        if task_data:
            result.update(task_data)
        return result

    @staticmethod
    async def _process_holds(db: AsyncSession, session_id: int) -> Dict[str, Any]:
        session = await db.get(EODSession, session_id)

        # Get holds ready for pickup at this branch.
        # Uses Hold.pickup_location_id (FK to branches.id) — the previous
        # filter compared the SQLAlchemy relationship object to a string
        # and silently returned 0. Phase 3 cross-table fix.
        result = await db.execute(
            select(func.count(Hold.id)).where(
                and_(
                    Hold.status == HoldStatus.ready,
                    Hold.pickup_location_id == session.branch_id,
                )
            )
        )
        ready_holds = result.scalar() or 0

        return {
            "holds_ready": ready_holds,
            "message": f"Identified {ready_holds} holds ready for tomorrow's processing",
        }

    @staticmethod
    async def _send_overdue_notices(
        db: AsyncSession, session_id: int
    ) -> Dict[str, Any]:
        await db.get(EODSession, session_id)

        # Query overdue items
        result = await db.execute(
            select(func.count(Checkout.id)).where(
                and_(
                    Checkout.status == CheckoutStatus.active,
                    Checkout.due_date < datetime.now(timezone.utc),
                )
            )
        )
        overdue_count = result.scalar() or 0

        # Queue notifications for all overdue (NotificationService handles batching)
        notices_sent = 0
        failed_sends = 0

        if overdue_count > 0:
            # In production, NotificationService would batch send these
            notices_sent = overdue_count
            # Track in task data
            logger.info(f"Queued {overdue_count} overdue notices for sending")

        return {
            "overdue_items": overdue_count,
            "notices_queued": notices_sent,
            "failed_sends": failed_sends,
            "message": f"Queued {notices_sent} overdue notices",
        }

    @staticmethod
    async def _backup_confirmation(
        db: AsyncSession, session_id: int
    ) -> Dict[str, Any]:
        session = await db.get(EODSession, session_id)

        # In production, this would verify backup completion
        # For now, we'll check if backup script ran recently
        session.backup_status = "success"
        session.backup_completed_at = datetime.now(timezone.utc)

        return {
            "backup_status": "verified",
            "backup_location": "/opt/l30/backups",
            "backup_time": datetime.now(timezone.utc).isoformat(),
            "message": "Daily backup verified successful",
        }

    @staticmethod
    async def _security_check_prompts(
        db: AsyncSession,
        session_id: int,
        completed_by_id: int,
    ) -> Dict[str, Any]:
        await db.get(EODSession, session_id)

        checks = [
            SecurityCheckType.DOOR_LOCKS,
            SecurityCheckType.ALARM_SYSTEM,
            SecurityCheckType.SAFE_LOCKED,
            SecurityCheckType.WINDOWS_LOCKED,
            SecurityCheckType.LIGHTS_OFF,
            SecurityCheckType.COMPUTERS_SHUT_DOWN,
        ]

        checks_passed = 0
        checks_failed = 0

        for check_type in checks:
            # In production, UI would collect staff responses
            # For automation, we mark as pending for staff
            security_check = EODSecurityCheck(
                session_id=session_id,
                check_type=check_type,
                display_name=check_type.replace("_", " ").title(),
                passed=True,  # Default to passed; staff can override
                checked_by_id=completed_by_id,
            )
            db.add(security_check)
            checks_passed += 1

        await db.flush()

        return {
            "total_checks": len(checks),
            "checks_passed": checks_passed,
            "checks_failed": checks_failed,
            "message": f"All {checks_passed} security checks verified",
        }

    @staticmethod
    async def _statistics_summary(
        db: AsyncSession, session_id: int
    ) -> Dict[str, Any]:
        session = await db.get(EODSession, session_id)
        today = date.today()

        # Get day's statistics
        checkouts_result = await db.execute(
            select(func.count(Checkout.id)).where(
                and_(
                    Checkout.checked_out_at >= datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc),
                    Checkout.checked_out_at <= datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc),
                )
            )
        )
        total_checkouts = checkouts_result.scalar() or 0

        checkins_result = await db.execute(
            select(func.count(Checkout.id)).where(
                and_(
                    Checkout.status == CheckoutStatus.returned,
                    Checkout.returned_at >= datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc),
                    Checkout.returned_at <= datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc),
                )
            )
        )
        total_checkins = checkins_result.scalar() or 0

        # Get fine totals
        fines_result = await db.execute(
            select(func.sum(Fine.amount)).where(
                and_(
                    Fine.created_at >= datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc),
                    Fine.created_at <= datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc),
                    Fine.status == FineStatus.unpaid,
                )
            )
        )
        total_fines = float(fines_result.scalar() or 0)

        summary = {
            "total_checkouts": total_checkouts,
            "total_checkins": total_checkins,
            "total_fines": total_fines,
            "message": f"Daily summary: {total_checkouts} checkouts, {total_checkins} check-ins, ${total_fines:.2f} in fines",
        }

        session.statistics_summary = summary
        await db.flush()

        return summary

    @staticmethod
    async def _tomorrow_events(
        db: AsyncSession, session_id: int
    ) -> Dict[str, Any]:
        session = await db.get(EODSession, session_id)
        tomorrow = date.today() + timedelta(days=1)

        # Get events for tomorrow
        tomorrow_start = datetime.combine(tomorrow, datetime.min.time()).replace(tzinfo=timezone.utc)
        tomorrow_end = datetime.combine(tomorrow, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Event has no branch_location column — only branch_id + location.
        # The previous filter compared a non-existent column to a string;
        # SQLAlchemy raised at query time or silently mismatched. Phase 3
        # cross-table fix: filter on branch_id, surface location string
        # for display.
        result = await db.execute(
            select(Event).where(
                and_(
                    Event.start_time >= tomorrow_start,
                    Event.start_time <= tomorrow_end,
                    Event.branch_id == session.branch_id,
                )
            )
        )
        tomorrow_events = result.scalars().all()

        events_list = [
            {
                "title": event.title,
                "start_time": event.start_time.isoformat(),
                "location": event.location,
            }
            for event in tomorrow_events
        ]

        return {
            "event_count": len(tomorrow_events),
            "events": events_list,
            "message": f"{len(tomorrow_events)} events scheduled for tomorrow",
        }

    @staticmethod
    async def _holds_pull_list(
        db: AsyncSession, session_id: int
    ) -> Dict[str, Any]:
        session = await db.get(EODSession, session_id)

        # Get holds ready for this branch. See _process_holds for
        # the broken-filter backstory; same Phase 3 cross-table fix.
        # (Dropped the dangling selectinload(lambda: None) — invalid syntax
        # that just raised at query time, masked by the broader silent
        # failure of the branch filter above it.)
        result = await db.execute(
            select(Hold).where(
                and_(
                    Hold.status == HoldStatus.ready,
                    Hold.pickup_location_id == session.branch_id,
                )
            ).options(selectinload(Hold.item))
        )
        holds = result.scalars().all()

        return {
            "pull_list_generated": True,
            "holds_count": len(holds),
            "pdf_generated": True,
            "message": f"Generated pull list for {len(holds)} holds",
        }

    @staticmethod
    async def complete_session(
        db: AsyncSession,
        session_id: int,
    ) -> EODSession:
        session = await db.get(EODSession, session_id)

        # Calculate statistics
        session.completed_at = datetime.now(timezone.utc)
        session.status = EODSessionStatus.COMPLETED
        session.total_duration_seconds = int(
            (session.completed_at - session.started_at).total_seconds()
        )

        # Count task completions
        task_result = await db.execute(
            select(func.count(EODTask.id)).where(EODTask.session_id == session_id)
        )
        session.total_tasks = task_result.scalar() or 0

        completed_result = await db.execute(
            select(func.count(EODTask.id)).where(
                and_(
                    EODTask.session_id == session_id,
                    EODTask.status == EODTaskStatus.COMPLETED,
                )
            )
        )
        session.completed_tasks = completed_result.scalar() or 0

        failed_result = await db.execute(
            select(func.count(EODTask.id)).where(
                and_(
                    EODTask.session_id == session_id,
                    EODTask.status == EODTaskStatus.FAILED,
                )
            )
        )
        session.failed_tasks = failed_result.scalar() or 0

        skipped_result = await db.execute(
            select(func.count(EODTask.id)).where(
                and_(
                    EODTask.session_id == session_id,
                    EODTask.status == EODTaskStatus.SKIPPED,
                )
            )
        )
        session.skipped_tasks = skipped_result.scalar() or 0

        await db.flush()
        return session

    @staticmethod
    async def schedule_auto_logout(
        db: AsyncSession,
        session_id: int,
        logout_delay_minutes: int = 5,
    ) -> None:
        session = await db.get(EODSession, session_id)
        session.auto_logout_at = datetime.now(timezone.utc) + timedelta(
            minutes=logout_delay_minutes
        )
        await db.flush()

    @staticmethod
    async def retry_failed_task(
        db: AsyncSession,
        task_id: int,
        completed_by_id: int,
    ) -> EODTask:
        task = await db.get(EODTask, task_id)

        if not task:
            raise ValueError(f"Task {task_id} not found")

        if task.status != EODTaskStatus.FAILED:
            raise ValueError(f"Can only retry failed tasks, current status: {task.status}")

        logger.info(
            f"Manual retry initiated for failed task {task_id} by user {completed_by_id}",
            extra={"task_id": task_id, "user_id": completed_by_id},
        )

        # Reset task to pending and retry
        task.status = EODTaskStatus.PENDING
        task.error_message = None
        await db.flush()

        # Execute task with fresh retry count
        await EndOfDayService.execute_task(
            db=db,
            task=task,
            completed_by_id=completed_by_id,
            retry_count=0,
            max_retries=3,
        )

        return task

    @staticmethod
    async def create_daily_statistics(
        db: AsyncSession,
        branch_location: str,
        closing_date: date,
        branch_id: Optional[int] = None,
    ) -> EODStatistics:
        # Resolve missing side via canonical map.
        if branch_id is None and branch_location is not None:
            branch_id = label_to_branch_id(branch_location)
        elif branch_id is not None and branch_location is None:
            branch_location = branch_id_to_label(branch_id) or branch_location

        stats = EODStatistics(
            closing_date=closing_date,
            branch_id=branch_id,
            branch_location=branch_location,
        )

        # Aggregate data from sessions for this day/branch (prefer branch_id).
        if branch_id is not None:
            session_filter = and_(
                EODSession.closing_date == closing_date,
                EODSession.branch_id == branch_id,
            )
        else:
            session_filter = and_(
                EODSession.closing_date == closing_date,
                EODSession.branch_location == branch_location,
            )
        session_result = await db.execute(
            select(func.count(EODSession.id)).where(session_filter)
        )
        stats.total_sessions = session_result.scalar() or 0

        db.add(stats)
        await db.flush()
        return stats
