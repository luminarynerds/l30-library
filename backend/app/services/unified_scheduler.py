# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.base import BaseTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logging import get_logger

logger = get_logger(__name__)


class ScheduleType(StrEnum):

    # Fine and circulation management
    FINE_CALCULATION = "fine_calculation"
    HOLD_EXPIRATION = "hold_expiration"
    OVERDUE_NOTIFICATIONS = "overdue_notifications"

    # Tech bookings
    TECH_BOOKING = "tech_booking"
    TECH_BOOKING_REMINDERS = "tech_booking_reminders"
    TECH_BOOKING_NO_SHOWS = "tech_booking_no_shows"
    TECH_BOOKING_FOLLOW_UPS = "tech_booking_follow_ups"

    # Staff scheduling
    STAFF_SCHEDULING = "staff_scheduling"
    STAFF_FAIRNESS_CHECK = "staff_fairness_check"

    # Compliance
    COMPLIANCE_DEADLINE = "compliance_deadline"
    COMPLIANCE_ESCALATION = "compliance_escalation"

    # Board reporting
    BOARD_REPORTING = "board_reporting"
    BOARD_REPORT_GENERATION = "board_report_generation"

    # Consortium billing
    CONSORTIUM_BILLING = "consortium_billing"
    CONSORTIUM_BILLING_MONTHLY = "consortium_billing_monthly"
    CONSORTIUM_BILLING_QUARTERLY = "consortium_billing_quarterly"

    # Room and event management
    ROOM_MANAGEMENT = "room_management"
    EVENT_MANAGEMENT = "event_management"

    # Release tracking
    RELEASE_INGESTION = "release_ingestion"

    # Misc system jobs
    SYSTEM_MAINTENANCE = "system_maintenance"
    DATA_RETENTION = "data_retention"
    CACHE_REFRESH = "cache_refresh"
    OPERATIONAL_ALERTS = "operational_alerts"
    COMMUNITY_METRICS = "community_metrics"
    COMMUNITY_METRICS_SNAPSHOT = "community_metrics_snapshot"

    # Indie ebook lending
    INDIE_LENDING = "indie_lending"

    # EDI (Electronic Data Interchange)
    EDI_POLLING = "edi_polling"
    EDI_RETRY = "edi_retry"

    # Collection weeding
    WEEDING_ANALYSIS = "weeding_analysis"


@dataclass
class ScheduleConfig:

    job_id: str
    job_type: ScheduleType
    name: str
    description: str = ""
    handler: Optional[Callable] = None
    trigger: Optional[BaseTrigger] = None
    cron_expression: Optional[str] = None
    enabled: bool = True
    max_instances: int = 1
    misfire_grace_time: int = 3600
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobExecutionResult:

    job_id: str
    job_type: ScheduleType
    success: bool
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    error_message: Optional[str] = None
    context_data: dict[str, Any] = field(default_factory=dict)


class SchedulingService:

    def __init__(self, scheduler: Optional[AsyncIOScheduler] = None):
        self.scheduler = scheduler
        self.job_registry: dict[str, ScheduleConfig] = {}
        self.execution_history: dict[str, list[JobExecutionResult]] = {}

    def register_job(self, config: ScheduleConfig) -> None:
        self.job_registry[config.job_id] = config
        logger.debug(f"Registered job {config.job_id}: {config.name}")

    def add_job(
        self,
        func: Callable,
        trigger: BaseTrigger,
        job_id: str,
        job_type: ScheduleType,
        name: str,
        misfire_grace_time: int = 3600,
        max_instances: int = 1,
        replace_existing: bool = True,
    ) -> None:
        if not self.scheduler:
            logger.error("Scheduler not initialized. Call init_scheduler() first.")
            return

        try:
            config = ScheduleConfig(
                job_id=job_id,
                job_type=job_type,
                name=name,
                handler=func,
                trigger=trigger,
                misfire_grace_time=misfire_grace_time,
                max_instances=max_instances,
            )
            self.register_job(config)

            self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                name=name,
                replace_existing=replace_existing,
                max_instances=max_instances,
                misfire_grace_time=misfire_grace_time,
            )
            logger.info(f"Added job {job_id} ({job_type.value}): {name}")
        except Exception as e:
            logger.error(f"Failed to add job {job_id}: {e}", exc_info=True)

    def remove_job(self, job_id: str) -> bool:
        if not self.scheduler:
            return False

        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.job_registry:
                del self.job_registry[job_id]
            logger.info(f"Removed job {job_id}")
            return True
        except Exception as e:  # noqa: BLE001 - scheduler job boundary — must not crash scheduler
            logger.warning(f"Failed to remove job {job_id}: {e}")
            return False

    def pause_job(self, job_id: str) -> bool:
        if not self.scheduler:
            return False

        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.pause()
                logger.info(f"Paused job {job_id}")
                return True
            return False
        except Exception as e:  # noqa: BLE001 - scheduler job boundary — must not crash scheduler
            logger.warning(f"Failed to pause job {job_id}: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        if not self.scheduler:
            return False

        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.resume()
                logger.info(f"Resumed job {job_id}")
                return True
            return False
        except Exception as e:  # noqa: BLE001 - scheduler job boundary — must not crash scheduler
            logger.warning(f"Failed to resume job {job_id}: {e}")
            return False

    def get_job_status(self, job_id: str) -> Optional[dict[str, Any]]:
        if not self.scheduler:
            return None

        job = self.scheduler.get_job(job_id)
        if not job:
            return None

        return {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time,
            "func": str(job.func),
            "trigger": str(job.trigger),
            "paused": False,  # APScheduler doesn't expose pause state directly
        }

    def list_jobs(self, job_type: Optional[ScheduleType] = None) -> list[dict[str, Any]]:
        jobs = []
        for job_id, config in self.job_registry.items():
            if job_type and config.job_type != job_type:
                continue

            status = self.get_job_status(job_id) or {}
            jobs.append({
                **config.__dict__,
                "status": status,
            })
        return jobs

    def record_execution(self, result: JobExecutionResult) -> None:
        job_id = result.job_id
        if job_id not in self.execution_history:
            self.execution_history[job_id] = []

        self.execution_history[job_id].append(result)

        # Keep only last 100 executions per job to avoid memory bloat
        if len(self.execution_history[job_id]) > 100:
            self.execution_history[job_id] = self.execution_history[job_id][-100:]

    def get_execution_history(
        self,
        job_id: str,
        limit: int = 50,
    ) -> list[JobExecutionResult]:
        history = self.execution_history.get(job_id, [])
        return history[-limit:]


# Global scheduling service instance
_scheduling_service: Optional[SchedulingService] = None


def get_scheduling_service() -> SchedulingService:
    global _scheduling_service
    if _scheduling_service is None:
        _scheduling_service = SchedulingService()
    return _scheduling_service


def set_scheduling_service(service: SchedulingService) -> None:
    global _scheduling_service
    _scheduling_service = service
