# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.email import send_email
from ...models.user import User
from .base import BaseNotificationService

logger = get_logger(__name__)


class MakerspaceNotificationService(BaseNotificationService):

    # =========================================================================
    # Reservation notifications
    # =========================================================================

    @staticmethod
    async def notify_reservation_created(db: AsyncSession, reservation) -> bool:
        from ...models.makerspace import MakerspaceResource

        user = reservation.user or await db.get(User, reservation.user_id)
        if not user or not user.email:
            return False

        resource = reservation.resource or await db.get(MakerspaceResource, reservation.resource_id)
        resource_name = resource.name if resource else "Equipment"
        start_time = reservation.start_time.strftime("%A, %B %d, %Y at %I:%M %p")

        subject = f"Makerspace Reservation Confirmed - {resource_name}"
        body = f"Your reservation for {resource_name} is confirmed for {start_time}."

        return await send_email(user.email, subject, body)

    @staticmethod
    async def notify_reservation_reminder(db: AsyncSession, reservation) -> bool:
        from ...models.makerspace import MakerspaceResource

        user = reservation.user or await db.get(User, reservation.user_id)
        if not user or not user.email:
            return False

        resource = reservation.resource or await db.get(MakerspaceResource, reservation.resource_id)
        resource_name = resource.name if resource else "Equipment"
        start_time = reservation.start_time.strftime("%A, %B %d, %Y at %I:%M %p")

        subject = f"Reminder: Makerspace Reservation Tomorrow - {resource_name}"
        body = f"Your reservation for {resource_name} is tomorrow at {start_time}."

        success = await send_email(user.email, subject, body)

        if success:
            reservation.reminder_sent_at = datetime.now(timezone.utc)
            await db.commit()

        return success

    # =========================================================================
    # Job notifications
    # =========================================================================

    @staticmethod
    async def notify_job_submitted(db: AsyncSession, job) -> bool:
        email = job.contact_email or (job.user.email if job.user else None)
        if not email:
            return False

        subject = f"Job Submitted: {job.job_number}"
        body = f"Your job {job.job_number} has been submitted and is awaiting review."

        return await send_email(email, subject, body)

    @staticmethod
    async def notify_job_approved(db: AsyncSession, job) -> bool:
        email = job.contact_email or (job.user.email if job.user else None)
        if not email:
            return False

        subject = f"Job Approved: {job.job_number}"
        body = f"Great news! Your job {job.job_number} has been approved and added to the queue."

        return await send_email(email, subject, body)

    @staticmethod
    async def notify_job_rejected(db: AsyncSession, job) -> bool:
        email = job.contact_email or (job.user.email if job.user else None)
        if not email:
            return False

        subject = f"Job Review Update: {job.job_number}"
        reason = job.rejection_reason or "Please contact staff for details."
        body = f"Your job {job.job_number} could not be approved. Reason: {reason}"

        return await send_email(email, subject, body)

    @staticmethod
    async def notify_job_ready_pickup(db: AsyncSession, job) -> bool:
        email = job.contact_email or (job.user.email if job.user else None)
        if not email:
            return False

        subject = f"Ready for Pickup: {job.job_number}"
        body = f"Your print job {job.job_number} is ready for pickup. Please pick up within 7 days."

        success = await send_email(email, subject, body)

        if success:
            job.pickup_notified_at = datetime.now(timezone.utc)
            await db.commit()

        return success

    # =========================================================================
    # Waitlist notifications
    # =========================================================================

    @staticmethod
    async def notify_waitlist_joined(db: AsyncSession, waitlist_entry) -> bool:
        from ...models.makerspace import MakerspaceResource

        user = waitlist_entry.user or await db.get(User, waitlist_entry.user_id)
        if not user or not user.email:
            return False

        resource = waitlist_entry.resource or await db.get(MakerspaceResource, waitlist_entry.resource_id)
        resource_name = resource.name if resource else "Equipment"

        subject = f"Waitlist Confirmation - {resource_name}"
        body = f"You've been added to the waitlist for {resource_name}. We'll notify you when a slot becomes available."

        return await send_email(user.email, subject, body)

    @staticmethod
    async def notify_waitlist_slot_available(
        db: AsyncSession, waitlist_entry, expires_in_hours: int = 24
    ) -> bool:
        from ...models.makerspace import MakerspaceResource, MakerspaceWaitlistStatus

        user = waitlist_entry.user or await db.get(User, waitlist_entry.user_id)
        if not user or not user.email:
            return False

        resource = waitlist_entry.resource or await db.get(MakerspaceResource, waitlist_entry.resource_id)
        resource_name = resource.name if resource else "Equipment"

        subject = f"A Slot is Available! - {resource_name}"
        body = f"Great news! A slot has opened up for {resource_name}. Please book within {expires_in_hours} hours to secure your spot."

        success = await send_email(user.email, subject, body)

        if success:
            waitlist_entry.status = MakerspaceWaitlistStatus.notified
            waitlist_entry.notified_at = datetime.now(timezone.utc)
            waitlist_entry.notification_expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
            await db.commit()

        return success

    # =========================================================================
    # Workshop notifications
    # =========================================================================

    @staticmethod
    async def notify_workshop_registration(
        db: AsyncSession, registration, is_waitlisted: bool = False
    ) -> bool:
        from ...models.makerspace import MakerspaceWorkshop

        user = registration.user or await db.get(User, registration.user_id)
        workshop = registration.workshop or await db.get(MakerspaceWorkshop, registration.workshop_id)

        if not user or not user.email or not workshop:
            return False

        if is_waitlisted:
            subject = f"Waitlisted: {workshop.title}"
            body = f"The workshop {workshop.title} is currently full, but you've been added to the waitlist."
        else:
            subject = f"Registration Confirmed: {workshop.title}"
            body = f"You're registered for {workshop.title}! It's scheduled for {workshop.start_time.strftime('%A, %B %d, %Y at %I:%M %p')}."

        success = await send_email(user.email, subject, body)

        if success:
            registration.confirmation_sent_at = datetime.now(timezone.utc)
            await db.commit()

        return success

    @staticmethod
    async def notify_workshop_reminder(db: AsyncSession, registration) -> bool:
        from ...models.makerspace import MakerspaceWorkshop

        user = registration.user or await db.get(User, registration.user_id)
        workshop = registration.workshop or await db.get(MakerspaceWorkshop, registration.workshop_id)

        if not user or not user.email or not workshop:
            return False

        subject = f"Reminder: {workshop.title} is Tomorrow!"
        body = f"This is a reminder that {workshop.title} is tomorrow at {workshop.start_time.strftime('%I:%M %p')}."

        success = await send_email(user.email, subject, body)

        if success:
            registration.reminder_sent_at = datetime.now(timezone.utc)
            await db.commit()

        return success

    # =========================================================================
    # Certification notifications
    # =========================================================================

    @staticmethod
    async def notify_certification_expiring(
        db: AsyncSession, certification, days_until_expiry: int
    ) -> bool:
        user = certification.user or await db.get(User, certification.user_id)
        if not user or not user.email:
            return False

        cert_name = certification.certification_type.name if certification.certification_type else "Equipment"

        subject = f"Certification Expiring Soon: {cert_name}"
        body = f"Your {cert_name} certification expires in {days_until_expiry} days. Please renew before expiration."

        return await send_email(user.email, subject, body)

    @staticmethod
    async def notify_certification_completed(db: AsyncSession, certification) -> bool:
        user = certification.user or await db.get(User, certification.user_id)
        if not user or not user.email:
            return False

        cert_name = certification.certification_type.name if certification.certification_type else "Equipment"

        subject = f"Congratulations! Certification Complete: {cert_name}"
        body = f"You've successfully completed your {cert_name} certification! You can now use this equipment."

        return await send_email(user.email, subject, body)

    # =========================================================================
    # Batch reminder methods
    # =========================================================================

    @staticmethod
    async def send_reservation_reminders(db: AsyncSession) -> int:
        from ...models.makerspace import MakerspaceReservation, MakerspaceResource, MakerspaceReservationStatus

        tomorrow_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        tomorrow_end = tomorrow_start + timedelta(days=1)

        result = await db.execute(
            select(MakerspaceReservation)
            .options(
                selectinload(MakerspaceReservation.user),
                selectinload(MakerspaceReservation.resource)
            )
            .where(MakerspaceReservation.status.in_([
                MakerspaceReservationStatus.pending,
                MakerspaceReservationStatus.confirmed
            ]))
            .where(MakerspaceReservation.start_time >= tomorrow_start)
            .where(MakerspaceReservation.start_time < tomorrow_end)
            .where(MakerspaceReservation.reminder_sent_at.is_(None))
        )
        reservations = result.scalars().all()

        count = 0
        for reservation in reservations:
            if await MakerspaceNotificationService.notify_reservation_reminder(db, reservation):
                count += 1

        logger.info(f"Sent {count} makerspace reservation reminders")
        return count

    @staticmethod
    async def send_workshop_reminders(db: AsyncSession) -> int:
        from ...models.makerspace import (
            MakerspaceWorkshop, WorkshopRegistration,
            WorkshopStatus, RegistrationStatus,
        )

        tomorrow_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        tomorrow_end = tomorrow_start + timedelta(days=1)

        workshops_result = await db.execute(
            select(MakerspaceWorkshop)
            .where(MakerspaceWorkshop.status == WorkshopStatus.published)
            .where(MakerspaceWorkshop.start_time >= tomorrow_start)
            .where(MakerspaceWorkshop.start_time < tomorrow_end)
        )
        workshops = workshops_result.scalars().all()

        count = 0
        for workshop in workshops:
            reg_result = await db.execute(
                select(WorkshopRegistration)
                .options(selectinload(WorkshopRegistration.user))
                .where(WorkshopRegistration.workshop_id == workshop.id)
                .where(WorkshopRegistration.status.in_([
                    RegistrationStatus.registered,
                    RegistrationStatus.confirmed
                ]))
                .where(WorkshopRegistration.reminder_sent_at.is_(None))
            )
            registrations = reg_result.scalars().all()

            for registration in registrations:
                registration.workshop = workshop
                if await MakerspaceNotificationService.notify_workshop_reminder(db, registration):
                    count += 1

        logger.info(f"Sent {count} workshop reminders")
        return count

    @staticmethod
    async def send_certification_expiry_warnings(
        db: AsyncSession, days_before: int = 30
    ) -> int:
        from ...models.makerspace import MakerspaceCertification, CertificationStatus

        warning_date = datetime.now(timezone.utc) + timedelta(days=days_before)

        result = await db.execute(
            select(MakerspaceCertification)
            .options(
                selectinload(MakerspaceCertification.user),
                selectinload(MakerspaceCertification.certification_type)
            )
            .where(MakerspaceCertification.status == CertificationStatus.active)
            .where(MakerspaceCertification.expires_at.isnot(None))
            .where(MakerspaceCertification.expires_at <= warning_date)
            .where(MakerspaceCertification.expires_at > datetime.now(timezone.utc))
        )
        certifications = result.scalars().all()

        count = 0
        for cert in certifications:
            days_until = (cert.expires_at - datetime.now(timezone.utc)).days
            if await MakerspaceNotificationService.notify_certification_expiring(db, cert, days_until):
                count += 1

        logger.info(f"Sent {count} certification expiry warnings")
        return count
