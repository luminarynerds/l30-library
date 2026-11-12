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
from ...models.multi_branch import BranchClosure, Consortium, ConsortiumBilling, SystemSettings
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




async def generate_monthly_consortium_billing() -> None:
    logger.info("Starting monthly consortium billing generation")

    try:
        async with AsyncSessionLocal() as db:
            from ..consortium_billing_service import ConsortiumBillingService

            # For monthly, we bill for the previous month
            today = date.today()
            month_start = date(today.year, today.month, 1)
            period_end = month_start - timedelta(days=1)
            period_start = date(period_end.year, period_end.month, 1)

            # Get all active consortiums
            result = await db.execute(select(Consortium))
            consortiums = result.scalars().all()

            billing_service = ConsortiumBillingService(db)

            for consortium in consortiums:
                try:
                    # Generate billing
                    billing_records = await billing_service.generate_billing_for_period(
                        consortium.id,
                        period_start,
                        period_end,
                    )

                    if billing_records:
                        # Create invoice
                        await billing_service.create_invoice(
                            [r.id for r in billing_records],
                            due_days=30,
                        )
                        logger.info(
                            f"Generated {len(billing_records)} billing records for consortium {consortium.id}"
                        )
                except Exception as e:
                    logger.error(
                        f"Error generating billing for consortium {consortium.id}: {e}",
                        exc_info=True,
                    )

    except Exception as e:
        logger.error(
            f"Error in monthly consortium billing generation: {e}", exc_info=True
        )


async def generate_quarterly_consortium_billing() -> None:
    logger.info("Starting quarterly consortium billing generation")

    try:
        async with AsyncSessionLocal() as db:
            from ..consortium_billing_service import ConsortiumBillingService

            # For quarterly, we bill for the previous quarter
            today = date.today()
            month = today.month

            # Determine previous quarter
            if month in [1, 2, 3]:
                quarter_start_month = 10
                quarter_start_year = today.year - 1
            elif month in [4, 5, 6]:
                quarter_start_month = 1
                quarter_start_year = today.year
            elif month in [7, 8, 9]:
                quarter_start_month = 4
                quarter_start_year = today.year
            else:  # 10, 11, 12
                quarter_start_month = 7
                quarter_start_year = today.year

            period_start = date(quarter_start_year, quarter_start_month, 1)
            period_end = date(today.year, today.month, 1) - timedelta(days=1)

            # Get all active consortiums
            result = await db.execute(select(Consortium))
            consortiums = result.scalars().all()

            billing_service = ConsortiumBillingService(db)

            for consortium in consortiums:
                try:
                    # Generate billing
                    billing_records = await billing_service.generate_billing_for_period(
                        consortium.id,
                        period_start,
                        period_end,
                    )

                    if billing_records:
                        # Create invoice
                        await billing_service.create_invoice(
                            [r.id for r in billing_records],
                            due_days=45,
                        )
                        logger.info(
                            f"Generated {len(billing_records)} quarterly billing records for consortium {consortium.id}"
                        )
                except Exception as e:
                    logger.error(
                        f"Error generating quarterly billing for consortium {consortium.id}: {e}",
                        exc_info=True,
                    )

    except Exception as e:
        logger.error(
            f"Error in quarterly consortium billing generation: {e}", exc_info=True
        )


async def mark_overdue_consortium_invoices() -> None:
    try:
        async with AsyncSessionLocal() as db:
            from ..consortium_billing_service import ConsortiumBillingService

            billing_service = ConsortiumBillingService(db)
            count = await billing_service.mark_overdue()

            if count > 0:
                logger.info(
                    f"Marked {count} consortium invoices as overdue",
                    extra={"overdue_count": count},
                )

    except Exception as e:
        logger.error(f"Error marking overdue consortium invoices: {e}", exc_info=True)


async def send_consortium_payment_reminders() -> None:
    try:
        async with AsyncSessionLocal() as db:
            from ...models.multi_branch import BillingStatus

            today = date.today()
            due_soon_date = today + timedelta(days=7)

            # Find invoices due within 7 days
            result = await db.execute(
                select(ConsortiumBilling).where(
                    and_(
                        ConsortiumBilling.status == BillingStatus.INVOICED,
                        ConsortiumBilling.due_date >= today,
                        ConsortiumBilling.due_date <= due_soon_date,
                    )
                )
            )
            invoices = result.scalars().all()

            if invoices:
                logger.info(
                    f"Found {len(invoices)} consortium invoices due within 7 days",
                    extra={"invoice_count": len(invoices), "period_end": due_soon_date},
                )
                # Email notifications would be sent here
                # Example: await send_reminder_emails(invoices)
            else:
                logger.debug("No consortium invoices due within 7 days")

    except Exception as e:
        logger.error(f"Error sending consortium payment reminders: {e}", exc_info=True)

