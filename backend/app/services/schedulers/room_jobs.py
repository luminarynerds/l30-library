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




async def process_room_no_shows() -> None:
    async with JobExecutionContext(
        job_id="room_no_show_processing",
        job_name="Room No-Show Processing",
        severity=JobSeverity.LOW,
    ) as ctx:
        logger.info("Starting room no-show processing")

        async with AsyncSessionLocal() as db:
            from ..room_service import process_no_shows

            no_shows_processed = await process_no_shows(db)
            await db.commit()

        ctx.add_metric("no_shows_processed", no_shows_processed)
        ctx.items_processed = no_shows_processed
        ctx.items_succeeded = no_shows_processed
        logger.info(
            "Room no-show processing completed",
            extra={"no_shows_processed": no_shows_processed},
        )


async def complete_room_reservations() -> None:
    logger.info("Starting room reservation completion check")
    reservations_completed = 0

    try:
        async with AsyncSessionLocal() as db:
            from ..room_service import complete_finished_reservations

            reservations_completed = await complete_finished_reservations(db)
            await db.commit()

        logger.info(
            "Room reservation completion check completed",
            extra={"reservations_completed": reservations_completed},
        )
    except Exception as e:
        logger.error(f"Error completing room reservations: {e}", exc_info=True)
        raise


async def send_room_reservation_reminders() -> None:
    logger.info("Starting room reservation reminder job")
    reminders_sent = 0

    try:
        async with AsyncSessionLocal() as db:
            from ..room_service import get_upcoming_reminders, send_reservation_reminder
            from sqlalchemy.orm import joinedload

            reminders = await get_upcoming_reminders(db, hours_ahead=24)

            for reservation in reminders:
                try:
                    # Get room info
                    room_result = await db.execute(
                        select(Room).where(Room.id == reservation.room_id)
                    )
                    room = room_result.scalar_one_or_none()
                    if not room:
                        continue

                    # Get patron info
                    patron = None
                    if reservation.patron_id:
                        patron_result = await db.execute(
                            select(User).where(User.id == reservation.patron_id)
                        )
                        patron = patron_result.scalar_one_or_none()

                    # Send reminder
                    success = await send_reservation_reminder(reservation, room, patron)

                    if success:
                        reservation.reminder_sent_at = datetime.now(timezone.utc)
                        reminders_sent += 1

                except Exception as e:
                    logger.error(
                        f"Error sending room reminder: {e}",
                        extra={"reservation_id": reservation.id},
                        exc_info=True,
                    )
                    continue

            await db.commit()

        logger.info(
            "Room reservation reminder job completed",
            extra={"reminders_sent": reminders_sent},
        )
    except Exception as e:
        logger.error(f"Error sending room reminders: {e}", exc_info=True)
        raise

