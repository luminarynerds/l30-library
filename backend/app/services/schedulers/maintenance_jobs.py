# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ...core.config import get_settings
from ...core.database import AsyncSessionLocal, engine
from ...core.email import send_email, COLORS
from ...core.logging import get_logger
from ...models.audit_log import AuditAction, AuditLog
from ...models.catalog import CatalogItem
from ...models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ...models.event import Event
from ...models.event_registration import EventRegistration, EventRegistrationStatus
from ...models.event_review import EventReview
from ...models.fine import Fine, FineStatus, FineType
from ...models.job_failure import JobSeverity
from ...models.multi_branch import BranchClosure, SystemSettings
from ...models.notification import NotificationPreferences, NotificationType
from ...models.permission import RoleSettings
from ...models.reading import ReadingAchievement
from ...models.sms import SMSNotificationType
from ...models.room import Room, RoomReservation, ReservationStatus
from ...models.user import User, UserRole
from ..job_failure_service import (
    JobExecutionContext,
    cleanup_old_job_logs,
    process_retry_queue,
)

settings = get_settings()
logger = get_logger(__name__)


def get_overdue_fine_per_day() -> Decimal:
    return Decimal(settings.overdue_fine_per_day)



async def process_failed_job_retries() -> None:
    async with JobExecutionContext(
        job_id="failed_job_retries",
        job_name="Failed Job Retry Processing",
        severity=JobSeverity.MEDIUM,
    ) as ctx:
        try:
            stats = await process_retry_queue()
            ctx.add_metric("processed", stats["processed"])
            ctx.add_metric("retried", stats["retried"])
            ctx.add_metric("abandoned", stats["abandoned"])
            ctx.items_processed = stats["processed"]
            ctx.items_succeeded = stats["retried"]
            ctx.items_failed = stats["errors"]
        except Exception as e:
            logger.error(f"Error processing retry queue: {e}", exc_info=True)
            raise


async def cleanup_job_logs() -> None:
    async with JobExecutionContext(
        job_id="job_log_cleanup",
        job_name="Job Log Cleanup",
        severity=JobSeverity.LOW,
    ) as ctx:
        try:
            stats = await cleanup_old_job_logs(days=settings.job_log_retention_days)
            ctx.add_metric("execution_logs_deleted", stats["execution_logs_deleted"])
            ctx.add_metric("failed_records_deleted", stats["failed_records_deleted"])
            ctx.items_processed = (
                stats["execution_logs_deleted"] + stats["failed_records_deleted"]
            )
            ctx.items_succeeded = ctx.items_processed
        except Exception as e:
            logger.error(f"Error cleaning up job logs: {e}", exc_info=True)
            raise


async def refresh_caches() -> None:
    logger.info("Starting scheduled cache refresh")
    try:
        from .cache_warming_service import refresh_caches as do_refresh

        status = await do_refresh()
        success_count = len([r for r in status.results if r.success])
        logger.info(
            f"Cache refresh completed: {success_count}/{len(status.results)} caches refreshed "
            f"in {status.total_duration_ms:.2f}ms"
        )
    except Exception as e:  # noqa: BLE001  # per-iteration scheduler job - must not crash scheduler loop
        # Cache refresh failures should not crash the scheduler
        logger.warning(f"Cache refresh failed (non-fatal): {e}")

