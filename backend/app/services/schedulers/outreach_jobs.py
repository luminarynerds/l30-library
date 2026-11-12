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



async def process_outreach_overdue_checkouts() -> None:
    logger.info("Starting outreach overdue checkout processing")

    try:
        async with AsyncSessionLocal() as db:
            from ..outreach_service import send_bulk_checkout_overdue_notifications

            notifications_sent = await send_bulk_checkout_overdue_notifications(db)

        logger.info(
            "Outreach overdue checkout processing completed",
            extra={"notifications_sent": notifications_sent},
        )
    except Exception as e:
        logger.error(f"Error processing outreach overdue checkouts: {e}", exc_info=True)
        raise


async def send_outreach_visit_reminders() -> None:
    logger.info("Starting outreach visit reminder job")

    try:
        async with AsyncSessionLocal() as db:
            from ..outreach_service import send_visit_reminders

            reminders_sent = await send_visit_reminders(db)

        logger.info(
            "Outreach visit reminder job completed",
            extra={"reminders_sent": reminders_sent},
        )
    except Exception as e:
        logger.error(f"Error sending outreach visit reminders: {e}", exc_info=True)
        raise


async def send_outreach_deposit_warnings() -> None:
    logger.info("Starting outreach deposit warning job")

    try:
        async with AsyncSessionLocal() as db:
            from ..outreach_service import send_deposit_expiry_warnings

            warnings_sent = await send_deposit_expiry_warnings(db)

        logger.info(
            "Outreach deposit warning job completed",
            extra={"warnings_sent": warnings_sent},
        )
    except Exception as e:
        logger.error(f"Error sending outreach deposit warnings: {e}", exc_info=True)
        raise


async def aggregate_outreach_statistics() -> None:
    logger.info("Starting outreach monthly statistics aggregation")

    try:
        async with AsyncSessionLocal() as db:
            from ..outreach_service import (
                generate_monthly_outreach_statistics,
                sync_outreach_to_program_statistics,
            )

            # Calculate previous month's date range
            today = date.today()
            first_of_month = today.replace(day=1)
            last_of_prev_month = first_of_month - timedelta(days=1)
            first_of_prev_month = last_of_prev_month.replace(day=1)

            # Generate outreach statistics
            stats = await generate_monthly_outreach_statistics(
                db, period_start=first_of_prev_month, period_end=last_of_prev_month
            )

            # Sync to ProgramStatistics for IMLS reporting
            await sync_outreach_to_program_statistics(
                db, period_start=first_of_prev_month, period_end=last_of_prev_month
            )

        logger.info(
            "Outreach monthly statistics aggregation completed",
            extra={
                "period_start": str(first_of_prev_month),
                "period_end": str(last_of_prev_month),
                "total_visits": stats.total_visits if stats else 0,
            },
        )
    except Exception as e:
        logger.error(f"Error aggregating outreach statistics: {e}", exc_info=True)
        raise

