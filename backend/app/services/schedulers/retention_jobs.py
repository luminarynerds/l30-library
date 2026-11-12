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
from ...core.frontend_routes import routes
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



async def run_data_retention_jobs() -> None:
    async with JobExecutionContext(
        job_id="daily_data_retention",
        job_name="Daily Data Retention Cleanup",
        severity=JobSeverity.MEDIUM,
    ) as ctx:
        logger.info("Starting daily data retention jobs")

        async with AsyncSessionLocal() as db:
            from .data_retention_service import run_all_retention_jobs

            results = await run_all_retention_jobs(db)

        for key, value in results.items():
            if isinstance(value, int):
                ctx.add_metric(key, value)
        total = sum(v for v in results.values() if isinstance(v, int))
        ctx.items_processed = total
        ctx.items_succeeded = total
        logger.info(
            "Data retention jobs completed",
            extra=results,
        )


async def _send_overdue_notification_email(
    user: User, checkouts: list[Checkout]
) -> bool:
    item_count = len(checkouts)
    subject = (
        f"Overdue Notice: {item_count} item{'s' if item_count > 1 else ''} overdue"
    )

    # Build item list
    items_html = ""
    total_fine = Decimal("0.00")
    fine_per_day = get_overdue_fine_per_day()
    now = datetime.now(timezone.utc)

    for checkout in checkouts:
        item_title = "Unknown Item"
        item_author = ""

        if checkout.item:
            item_title = checkout.item.title
            item_author = checkout.item.author or ""
        elif checkout.item_copy and checkout.item_copy.catalog_item:
            item_title = checkout.item_copy.catalog_item.title
            item_author = checkout.item_copy.catalog_item.author or ""

        days_overdue = (now - checkout.due_date).days
        if days_overdue < 1:
            days_overdue = 1
        item_fine = fine_per_day * days_overdue
        total_fine += item_fine

        due_date_str = checkout.due_date.strftime("%B %d, %Y")

        items_html += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid {COLORS['divider']};">
                <strong>{item_title}</strong>
                {f'<br><span style="color: {COLORS["body"]};">{item_author}</span>' if item_author else ''}
            </td>
            <td style="padding: 10px; border-bottom: 1px solid {COLORS['divider']}; text-align: center;">
                {due_date_str}
            </td>
            <td style="padding: 10px; border-bottom: 1px solid {COLORS['divider']}; text-align: right;">
                ${item_fine:.2f}
            </td>
        </tr>
        """

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Overdue Notice</h2>
        <p>Hi {user.first_name},</p>
        <p>This is a friendly reminder that you have <strong>{item_count} overdue item{'s' if item_count > 1 else ''}</strong>
           from {settings.app_name}. Please return them as soon as possible to avoid additional fines.</p>

        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background-color: {COLORS['border']};">
                    <th style="padding: 10px; text-align: left;">Item</th>
                    <th style="padding: 10px; text-align: center;">Due Date</th>
                    <th style="padding: 10px; text-align: right;">Fine</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
            <tfoot>
                <tr style="background-color: {COLORS['border']};">
                    <td colspan="2" style="padding: 10px; text-align: right; font-weight: bold;">
                        Total Fines:
                    </td>
                    <td style="padding: 10px; text-align: right; font-weight: bold;">
                        ${total_fine:.2f}
                    </td>
                </tr>
            </tfoot>
        </table>

        <p style="color: {COLORS['text_light']}; font-size: 14px;">
            Fines accrue at ${fine_per_day:.2f} per day per item.
            Return items promptly to minimize charges.
        </p>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{routes.url(settings.frontend_url, routes.account_checkouts_alt)}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                View My Account
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            If you've already returned these items, please disregard this notice
            and allow a few days for our records to update.
        </p>
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name} - {settings.library_name}
        </p>
    </div>
    """

    return await send_email(user.email, subject, html_content)

