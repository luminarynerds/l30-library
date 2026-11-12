# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.database import AsyncSessionLocal
from ..core.logging import get_logger
from ..models.tech_booking import TechAssistanceBooking
from . import tech_booking_service
from .unified_scheduler import ScheduleType, get_scheduling_service

settings = get_settings()
logger = get_logger(__name__)

scheduler: Optional[AsyncIOScheduler] = None


async def send_tech_booking_reminders() -> None:
    logger.info("Starting tech booking reminders job")

    try:
        async with AsyncSessionLocal() as db:
            # Get upcoming appointments that need reminders
            bookings = await tech_booking_service.get_upcoming_appointments_for_reminders(db)

            if not bookings:
                logger.debug("No bookings needing reminders at this time")
                return

            logger.info(f"Found {len(bookings)} bookings needing reminders")

            for booking in bookings:
                try:
                    success = await tech_booking_service.send_appointment_reminder(db, booking)
                    if success:
                        logger.info(f"Sent reminder for booking {booking.id}")
                    else:
                        logger.warning(f"Failed to send reminder for booking {booking.id}")
                except Exception as e:  # noqa: BLE001 — per-iteration boundary — must not crash loop
                    logger.error(f"Error sending reminder for booking {booking.id}: {e}")
                    continue

            logger.info("Completed tech booking reminders job")

    except Exception as e:  # noqa: BLE001 — scheduler-job boundary — must not propagate to apscheduler runtime
        logger.error(f"Fatal error in send_tech_booking_reminders: {e}")


async def check_tech_booking_no_shows() -> None:
    logger.info("Starting tech booking no-show check")

    try:
        async with AsyncSessionLocal() as db:
            no_show_count = await tech_booking_service.mark_no_shows(db)

            if no_show_count > 0:
                logger.info(f"Marked {no_show_count} bookings as no-show")
            else:
                logger.debug("No no-shows detected at this time")

    except Exception as e:  # noqa: BLE001 — scheduler-job boundary — must not propagate to apscheduler runtime
        logger.error(f"Fatal error in check_tech_booking_no_shows: {e}")


async def suggest_follow_ups() -> None:
    logger.info("Starting tech booking follow-up suggestion job")

    try:
        async with AsyncSessionLocal() as db:
            # Find completed bookings from last 3 days without follow-ups
            three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)

            stmt = select(TechAssistanceBooking).where(
                TechAssistanceBooking.status == "completed",
                TechAssistanceBooking.session_end_actual >= three_days_ago,
            )

            result = await db.execute(stmt)
            completed_bookings = result.scalars().all()

            follow_up_count = 0

            for booking in completed_bookings:
                try:
                    # Check if follow-up already exists
                    from ..models.tech_booking import TechFollowUpBooking

                    stmt = select(TechFollowUpBooking).where(
                        TechFollowUpBooking.original_booking_id == booking.id
                    )
                    result = await db.execute(stmt)
                    existing_follow_up = result.scalar_one_or_none()

                    if existing_follow_up:
                        continue

                    # Get session notes to assess comprehension
                    if booking.session_notes:
                        avg_comprehension = 0
                        if booking.session_notes:
                            comprehension_levels = [
                                n.patron_comprehension_level
                                for n in booking.session_notes
                                if n.patron_comprehension_level
                            ]
                            if comprehension_levels:
                                avg_comprehension = sum(comprehension_levels) / len(
                                    comprehension_levels
                                )

                        # Suggest follow-up if comprehension is below 4
                        if avg_comprehension < 4:
                            # Create follow-up record
                            await tech_booking_service.schedule_follow_up(
                                db,
                                original_booking_id=booking.id,
                                suggested_topics=[booking.topic],
                                reason="Patron would benefit from additional practice",
                                suggested_timing="1-2 weeks",
                            )
                            follow_up_count += 1
                            logger.info(
                                f"Suggested follow-up for booking {booking.id} "
                                f"(comprehension: {avg_comprehension})"
                            )

                except Exception as e:  # noqa: BLE001 — per-iteration boundary — must not crash loop
                    logger.error(f"Error processing follow-up for booking {booking.id}: {e}")
                    continue

            logger.info(f"Completed follow-up suggestions: {follow_up_count} suggested")

    except Exception as e:  # noqa: BLE001 — scheduler-job boundary — must not propagate to apscheduler runtime
        logger.error(f"Fatal error in suggest_follow_ups: {e}")


async def send_auto_handouts() -> None:
    logger.info("Starting tech booking auto-handout job")

    try:
        async with AsyncSessionLocal() as db:
            from ..models.tech_booking import TechResourceHandout

            # Find completed bookings with unsent resources
            stmt = (
                select(TechAssistanceBooking)
                .where(TechAssistanceBooking.status == "completed")
                .where(TechAssistanceBooking.session_end_actual.isnot(None))
            )

            result = await db.execute(stmt)
            completed_bookings = result.scalars().all()

            handout_count = 0

            for booking in completed_bookings:
                try:
                    # Get unsent resources
                    stmt = select(TechResourceHandout).where(
                        TechResourceHandout.booking_id == booking.id,
                        TechResourceHandout.sent_to_patron == False,
                    )

                    result = await db.execute(stmt)
                    unsent_resources = list(result.scalars().all())

                    if not unsent_resources:
                        continue

                    # Send handouts
                    success = await tech_booking_service.send_handout_materials(
                        db, booking, unsent_resources
                    )

                    if success:
                        handout_count += 1
                        logger.info(f"Sent handout materials for booking {booking.id}")
                    else:
                        logger.warning(f"Failed to send handouts for booking {booking.id}")

                except Exception as e:  # noqa: BLE001 — per-iteration boundary — must not crash loop
                    logger.error(f"Error sending handouts for booking {booking.id}: {e}")
                    continue

            logger.info(f"Completed auto-handout job: {handout_count} sent")

    except Exception as e:  # noqa: BLE001 — scheduler-job boundary — must not propagate to apscheduler runtime
        logger.error(f"Fatal error in send_auto_handouts: {e}")


def initialize_tech_booking_jobs(scheduler_instance: AsyncIOScheduler) -> None:
    global scheduler
    scheduler = scheduler_instance
    unified_scheduler = get_scheduling_service()

    def _add_job(func, trigger, job_id, job_type, name, max_instances=1):
        scheduler.add_job(
            func,
            trigger,
            id=job_id,
            name=name,
            replace_existing=True,
            max_instances=max_instances,
        )
        try:
            if unified_scheduler:
                from .unified_scheduler import ScheduleConfig
                unified_scheduler.register_job(ScheduleConfig(
                    job_id=job_id,
                    job_type=job_type,
                    name=name,
                    handler=func,
                    trigger=trigger,
                    max_instances=max_instances,
                ))
        except Exception as e:  # noqa: BLE001 — secondary-registry boundary — failed registration must not block primary apscheduler.add_job
            logger.warning(f"Failed to register job {job_id} with unified scheduler: {e}")

    # Send reminders every hour
    _add_job(
        send_tech_booking_reminders,
        CronTrigger(minute=0),
        "tech-booking-reminders",
        ScheduleType.TECH_BOOKING_REMINDERS,
        "Send Tech Booking Reminders",
    )

    # Check for no-shows every 30 minutes
    _add_job(
        check_tech_booking_no_shows,
        CronTrigger(minute="*/30"),
        "tech-booking-no-shows",
        ScheduleType.TECH_BOOKING_NO_SHOWS,
        "Check Tech Booking No-Shows",
    )

    # Suggest follow-ups daily at 9am
    _add_job(
        suggest_follow_ups,
        CronTrigger(hour=9, minute=0),
        "tech-booking-follow-ups",
        ScheduleType.TECH_BOOKING_FOLLOW_UPS,
        "Suggest Tech Booking Follow-ups",
    )

    # Send auto handouts every 2 hours
    _add_job(
        send_auto_handouts,
        CronTrigger(hour="*/2", minute=0),
        "tech-booking-auto-handouts",
        ScheduleType.TECH_BOOKING,
        "Send Tech Booking Auto Handouts",
    )

    logger.info("Initialized tech booking scheduled jobs")
