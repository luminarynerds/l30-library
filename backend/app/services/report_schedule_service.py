# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import contextlib
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.database import AsyncSessionLocal
from ..models.report_schedule import UnifiedReportSchedule
from .reports.base import OutputFormat, ReportFilters
from .reports.factory import ReportFactory, ReportType
from .unified_scheduler import ScheduleType, get_scheduling_service

logger = get_logger(__name__)
settings = get_settings()

# Day-of-week labels for cron (0 = Monday in Python, but cron uses 0 = Sunday).
# APScheduler CronTrigger uses 0=Mon consistent with Python weekday().
_WEEKDAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class UnifiedReportScheduler:

    def __init__(self) -> None:
        self.scheduler: Optional[AsyncIOScheduler] = None

    async def init(self) -> None:
        self.scheduler = AsyncIOScheduler()
        await self._load_schedules()
        if not self.scheduler.running:
            self.scheduler.start()
        logger.info("Unified Report Scheduler started")

    async def shutdown(self) -> None:
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Unified Report Scheduler stopped")

    # ------------------------------------------------------------------
    # Schedule lifecycle
    # ------------------------------------------------------------------

    async def _load_schedules(self) -> None:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(UnifiedReportSchedule).where(UnifiedReportSchedule.is_active == True)
                )
                schedules = result.scalars().all()
                for sched in schedules:
                    self._register(sched)
                logger.info("Loaded %d active report schedules", len(schedules))
        except Exception:  # noqa: BLE001 -- scheduler bootstrap boundary: missing schedules must not crash app startup
            logger.exception("Failed to load report schedules")

    def _register(self, sched: UnifiedReportSchedule) -> None:
        job_id = f"report_schedule_{sched.id}"
        with contextlib.suppress(Exception):  # noqa: BLE001 - idempotent re-register: missing job is the desired end-state
            self.scheduler.remove_job(job_id)

        trigger = self._build_trigger(sched)
        if trigger is None:
            return

        self.scheduler.add_job(
            self._execute,
            trigger=trigger,
            id=job_id,
            args=(sched.id,),
            name=f"Report: {sched.name}",
            replace_existing=True,
        )

    def _build_trigger(self, sched: UnifiedReportSchedule) -> Optional[CronTrigger]:
        hour, minute = _parse_time(sched.time_of_day)

        if sched.frequency == "daily":
            return CronTrigger(hour=hour, minute=minute)
        elif sched.frequency == "weekly":
            dow = sched.day_of_week if sched.day_of_week is not None else 0
            return CronTrigger(day_of_week=dow, hour=hour, minute=minute)
        elif sched.frequency == "monthly":
            day = sched.day_of_month or 1
            return CronTrigger(day=day, hour=hour, minute=minute)
        else:
            logger.warning("Unknown frequency %s for schedule %d", sched.frequency, sched.id)
            return None

    async def add_schedule(self, sched: UnifiedReportSchedule) -> None:
        self._register(sched)

    async def update_schedule(self, sched: UnifiedReportSchedule) -> None:
        self._register(sched)

    async def remove_schedule(self, schedule_id: int) -> None:
        with contextlib.suppress(Exception):  # noqa: BLE001 - idempotent removal: missing job is the desired end-state
            self.scheduler.remove_job(f"report_schedule_{schedule_id}")

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def _execute(self, schedule_id: int) -> None:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(UnifiedReportSchedule).where(UnifiedReportSchedule.id == schedule_id)
                )
                sched = result.scalars().first()
                if not sched:
                    logger.warning("Schedule %d not found", schedule_id)
                    return

                logger.info("Executing report schedule: %s", sched.name)

                try:
                    report_type = ReportType(sched.report_type)
                    output_format = OutputFormat(sched.output_format)
                except ValueError as exc:
                    sched.last_status = "failed"
                    sched.last_error = f"Invalid type/format: {exc}"
                    sched.last_run_at = datetime.now(timezone.utc)
                    await db.commit()
                    return

                # Build date range: previous full period
                now = datetime.now(timezone.utc)
                filters = _period_filters(sched.frequency, now, sched.branch_id)

                try:
                    factory = ReportFactory(db, None)
                    report_bytes = await factory.generate(report_type, filters, output_format)

                    # Email delivery
                    if sched.recipient_emails:
                        await _send_report_email(
                            recipients=sched.recipient_emails,
                            report_bytes=report_bytes,
                            report_type=report_type,
                            output_format=output_format,
                            schedule_name=sched.name,
                        )

                    sched.last_run_at = now
                    sched.last_status = "success"
                    sched.last_error = None

                except Exception as exc:
                    logger.exception("Report generation failed for schedule %d", schedule_id)
                    sched.last_run_at = now
                    sched.last_status = "failed"
                    sched.last_error = str(exc)[:500]

                # Update next_run_at
                job = self.scheduler.get_job(f"report_schedule_{sched.id}")
                if job and job.next_run_time:
                    sched.next_run_at = job.next_run_time

                await db.commit()

        except Exception:
            logger.exception("Error in report schedule execution for %d", schedule_id)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_time(time_str: Optional[str]) -> tuple[int, int]:
    if not time_str:
        return 8, 0
    try:
        parts = time_str.split(":")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return 8, 0


def _period_filters(frequency: str, now: datetime, branch_id: Optional[int]) -> ReportFilters:
    from datetime import timedelta

    if frequency == "daily":
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=1)
    elif frequency == "weekly":
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=7)
    else:  # monthly
        end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start = (end - timedelta(days=1)).replace(day=1)

    return ReportFilters(start_date=start, end_date=end, branch_id=branch_id)


async def _send_report_email(
    recipients: list[str],
    report_bytes: bytes,
    report_type: ReportType,
    output_format: OutputFormat,
    schedule_name: str,
) -> None:
    from ..core.email import send_email

    ext_map = {OutputFormat.CSV: "csv", OutputFormat.EXCEL: "xlsx", OutputFormat.PDF: "pdf"}
    mime_map = {
        OutputFormat.CSV: "text/csv",
        OutputFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        OutputFormat.PDF: "application/pdf",
    }

    ext = ext_map.get(output_format, "pdf")
    mime = mime_map.get(output_format, "application/octet-stream")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{report_type.value}_report_{timestamp}.{ext}"

    subject = f"Scheduled Report: {schedule_name}"
    body = (
        f"Your scheduled {report_type.value} report is attached.\n\n"
        f"Report: {schedule_name}\n"
        f"Format: {ext.upper()}\n"
        f"Generated: {timestamp}"
    )

    for email in recipients:
        try:
            await send_email(
                to=email,
                subject=subject,
                body=body,
                attachments=[{"filename": filename, "content": report_bytes, "mime_type": mime}],
            )
        except Exception:
            logger.exception("Failed to email report to %s", email)


# ------------------------------------------------------------------
# Global instance
# ------------------------------------------------------------------

_report_scheduler: Optional[UnifiedReportScheduler] = None


def get_report_scheduler() -> UnifiedReportScheduler:
    global _report_scheduler
    if _report_scheduler is None:
        _report_scheduler = UnifiedReportScheduler()
    return _report_scheduler
