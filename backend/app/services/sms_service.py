# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.sms import (
    SMS_MAX_SEGMENTS,
    SMS_VERIFICATION_CODE_LENGTH,
    SMS_VERIFICATION_EXPIRY_MINUTES,
    SMSConfigurationError,
    SMSDeliveryError,
    SMSOptedOutError,
    SMSValidationError,
    calculate_segments,
    generate_verification_code,
    get_next_available_time,
    hash_verification_code,
    is_within_dnd_hours,
    normalize_phone_number,
    send_sms,
    send_verification_sms,
    truncate_message,
    verify_code,
)
from ..models.notification import NotificationPreferences
from ..models.sms import (
    DoNotDisturbHours,
    PhoneVerification,
    SMSCostRecord,
    SMSDeliveryLog,
    SMSDeliveryStatus,
    SMSNotificationType,
    SMSOptOut,
    SMSQueue,
    SMSTemplate,
)
from ..models.user import User

settings = get_settings()
logger = get_logger(__name__)


# Default SMS templates for each notification type
DEFAULT_TEMPLATES = {
    SMSNotificationType.HOLD_READY: (
        "{library_name}: Your hold '{title}' is ready! "
        "Pick up by {expires_date}. Questions? {phone}"
    ),
    SMSNotificationType.HOLD_EXPIRED: (
        "{library_name}: Your hold for '{title}' has expired. "
        "You can place a new hold on this item if still interested."
    ),
    SMSNotificationType.DUE_DATE_REMINDER: (
        "{library_name}: Reminder - '{title}' is due {due_date}. "
        "Renew online or return to avoid fines."
    ),
    SMSNotificationType.OVERDUE_NOTICE: (
        "{library_name}: '{title}' is {days_overdue} day(s) overdue. "
        "Please return ASAP to avoid additional fines."
    ),
    SMSNotificationType.CHECKOUT_RECEIPT: (
        "{library_name}: Checked out '{title}'. Due: {due_date}. "
        "Manage your account online."
    ),
    SMSNotificationType.EVENT_REMINDER: (
        "{library_name}: Reminder - '{event_name}' is {time_until}. "
        "Location: {location}"
    ),
    SMSNotificationType.EVENT_CANCELLED: (
        "{library_name}: '{event_name}' on {event_date} has been cancelled. "
        "Sorry for any inconvenience."
    ),
    SMSNotificationType.EVENT_UPDATED: (
        "{library_name}: '{event_name}' has been updated. "
        "Check your account for details."
    ),
    SMSNotificationType.PHONE_VERIFICATION: (
        "{library_name}: Your verification code is {code}. "
        "Valid for {expiry_minutes} minutes."
    ),
    SMSNotificationType.ACCOUNT_ALERT: (
        "{library_name}: {message}"
    ),
    SMSNotificationType.AD_HOC: (
        "{library_name}: {message}"
    ),
}


class SMSService:

    @staticmethod
    async def get_sms_preferences(
        user_id: int, db: AsyncSession
    ) -> Optional[NotificationPreferences]:
        result = await db.execute(
            select(NotificationPreferences).where(
                NotificationPreferences.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def is_phone_opted_out(
        phone_number: str, db: AsyncSession
    ) -> bool:
        try:
            normalized = normalize_phone_number(phone_number)
        except SMSValidationError:
            return True  # Invalid numbers are effectively opted out

        result = await db.execute(
            select(SMSOptOut).where(
                and_(
                    SMSOptOut.phone_number == normalized,
                    SMSOptOut.is_active == True
                )
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_dnd_config(
        user_id: Optional[int], db: AsyncSession
    ) -> Optional[DoNotDisturbHours]:
        if user_id:
            # Try user-specific config first
            result = await db.execute(
                select(DoNotDisturbHours).where(
                    DoNotDisturbHours.user_id == user_id,
                    DoNotDisturbHours.is_enabled == True
                )
            )
            user_config = result.scalar_one_or_none()
            if user_config:
                return user_config

        # Fall back to global config
        result = await db.execute(
            select(DoNotDisturbHours).where(
                DoNotDisturbHours.user_id.is_(None),
                DoNotDisturbHours.is_enabled == True
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_or_create_template(
        notification_type: SMSNotificationType, db: AsyncSession
    ) -> SMSTemplate:
        result = await db.execute(
            select(SMSTemplate).where(
                SMSTemplate.notification_type == notification_type
            )
        )
        template = result.scalar_one_or_none()

        if not template:
            # Create default template
            default_body = DEFAULT_TEMPLATES.get(
                notification_type,
                "{library_name}: {message}"
            )
            template = SMSTemplate(
                notification_type=notification_type,
                template_body=default_body,
                description=f"Default template for {notification_type.value}"
            )
            db.add(template)
            await db.flush()

        return template

    @staticmethod
    def render_template(template_body: str, context: dict) -> str:
        # Add default library name if not in context
        if "library_name" not in context:
            context["library_name"] = settings.app_name

        try:
            return template_body.format(**context)
        except KeyError as e:
            logger.warning(f"Missing template placeholder: {e}")
            # Return template with missing placeholders shown
            return template_body.format_map(
                {k: context.get(k, f"[{k}]") for k in context}
            )

    @staticmethod
    async def queue_sms(
        user_id: int,
        phone_number: str,
        notification_type: SMSNotificationType,
        message: str,
        context_data: Optional[dict] = None,
        scheduled_for: Optional[datetime] = None,
        initiated_by_user_id: Optional[int] = None,
        db: AsyncSession = None,
        check_opt_out: bool = True,
        check_dnd: bool = True,
    ) -> SMSQueue:
        # Normalize phone number
        normalized_phone = normalize_phone_number(phone_number)

        # Check opt-out status
        if check_opt_out:
            if await SMSService.is_phone_opted_out(normalized_phone, db):
                raise SMSOptedOutError(f"Phone {normalized_phone[-4:]} has opted out")

        # Get user info for recipient name
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        recipient_name = user.full_name if user else None

        # Calculate segments and truncate if needed
        segments = calculate_segments(message)
        max_segments = SMS_MAX_SEGMENTS
        if segments > max_segments:
            message = truncate_message(message, max_segments)
            segments = calculate_segments(message)

        # Determine scheduled time
        if scheduled_for is None:
            scheduled_for = datetime.now(timezone.utc)

        # Check DND hours
        status = SMSDeliveryStatus.PENDING
        if check_dnd:
            dnd_config = await SMSService.get_dnd_config(user_id, db)
            if dnd_config and is_within_dnd_hours(
                dnd_config.start_time,
                dnd_config.end_time,
                dnd_config.timezone,
                scheduled_for
            ):
                # Queue for after DND hours
                next_available = get_next_available_time(
                    dnd_config.start_time,
                    dnd_config.end_time,
                    dnd_config.timezone
                )
                scheduled_for = next_available
                status = SMSDeliveryStatus.QUEUED_DND

        # Create queue record
        sms_queue = SMSQueue(
            user_id=user_id,
            notification_type=notification_type,
            status=status,
            recipient_phone=normalized_phone,
            recipient_name=recipient_name,
            message_body=message,
            message_segments=segments,
            context_data=context_data,
            scheduled_for=scheduled_for,
            initiated_by_user_id=initiated_by_user_id,
        )

        db.add(sms_queue)
        await db.flush()

        logger.info(
            "SMS queued",
            extra={
                "sms_queue_id": sms_queue.id,
                "user_id": user_id,
                "phone": normalized_phone[-4:],
                "type": notification_type.value,
                "segments": segments,
                "status": status.value,
                "scheduled_for": scheduled_for.isoformat()
            }
        )

        return sms_queue

    @staticmethod
    async def send_queued_sms(
        sms_queue_id: int, db: AsyncSession
    ) -> tuple[bool, Optional[str]]:
        result = await db.execute(
            select(SMSQueue).where(SMSQueue.id == sms_queue_id)
        )
        sms = result.scalar_one_or_none()

        if not sms:
            return False, "SMS queue record not found"

        if sms.status not in (SMSDeliveryStatus.PENDING, SMSDeliveryStatus.QUEUED_DND):
            return False, f"SMS already processed: {sms.status}"

        try:
            # Check opt-out again before sending
            if await SMSService.is_phone_opted_out(sms.recipient_phone, db):
                sms.status = SMSDeliveryStatus.CANCELLED
                sms.failure_reason = "Recipient opted out"
                await db.commit()
                return False, "Recipient opted out"

            # Send via SMS provider (none wired; raises SMSConfigurationError)
            response = await send_sms(
                to_phone=sms.recipient_phone,
                message=sms.message_body,
            )

            # Update queue record
            sms.twilio_sid = response.get("sid")
            sms.twilio_status = response.get("status")
            sms.cost_cents = response.get("cost_cents")
            sms.sent_at = datetime.now(timezone.utc)

            if response.get("status") == "disabled":
                sms.status = SMSDeliveryStatus.CANCELLED
                sms.failure_reason = "SMS disabled"
            else:
                sms.status = SMSDeliveryStatus.SENT

            # Create delivery log
            log = SMSDeliveryLog(
                sms_queue_id=sms.id,
                previous_status=SMSDeliveryStatus.PENDING.value,
                new_status=str(sms.status),
                twilio_sid=sms.twilio_sid,
                twilio_status=sms.twilio_status,
            )
            db.add(log)

            # Update cost tracking
            await SMSService._update_cost_record(
                user_id=sms.user_id,
                notification_type=sms.notification_type,
                segments=sms.message_segments,
                cost_cents=sms.cost_cents or 0,
                success=True,
                db=db
            )

            await db.commit()

            logger.info(
                "SMS sent",
                extra={
                    "sms_queue_id": sms.id,
                    "twilio_sid": sms.twilio_sid,
                    "status": str(sms.status)
                }
            )

            return True, None

        except (SMSDeliveryError, SMSConfigurationError) as e:
            sms.retry_count += 1

            if sms.retry_count >= sms.max_retries:
                sms.status = SMSDeliveryStatus.FAILED
                sms.failed_at = datetime.now(timezone.utc)
                sms.failure_reason = str(e)

                # Update cost tracking for failure
                await SMSService._update_cost_record(
                    user_id=sms.user_id,
                    notification_type=sms.notification_type,
                    segments=sms.message_segments,
                    cost_cents=0,
                    success=False,
                    db=db
                )
            else:
                # Schedule retry with exponential backoff
                backoff_minutes = 2 ** sms.retry_count  # 2, 4, 8 minutes
                sms.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)
                sms.failure_reason = str(e)

            # Create delivery log
            log = SMSDeliveryLog(
                sms_queue_id=sms.id,
                previous_status=SMSDeliveryStatus.PENDING.value,
                new_status=str(sms.status),
                twilio_error_message=str(e),
            )
            db.add(log)

            await db.commit()

            logger.error(
                "SMS send failed",
                extra={
                    "sms_queue_id": sms.id,
                    "retry_count": sms.retry_count,
                    "error": str(e)
                }
            )

            return False, str(e)

    @staticmethod
    async def initiate_phone_verification(
        user_id: int,
        phone_number: str,
        db: AsyncSession,
    ) -> PhoneVerification:
        normalized_phone = normalize_phone_number(phone_number)

        # Generate verification code
        code = generate_verification_code(SMS_VERIFICATION_CODE_LENGTH)
        code_hash = hash_verification_code(code)

        # Create verification record
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=SMS_VERIFICATION_EXPIRY_MINUTES
        )

        verification = PhoneVerification(
            user_id=user_id,
            phone_number=normalized_phone,
            verification_code_hash=code_hash,
            expires_at=expires_at,
        )
        db.add(verification)
        await db.flush()

        # Send verification SMS
        try:
            response = await send_verification_sms(
                to_phone=normalized_phone,
                verification_code=code,
                library_name=settings.app_name
            )
            verification.twilio_sid = response.get("sid")
        except (SMSDeliveryError, SMSConfigurationError) as e:
            logger.error(
                "Failed to send verification SMS",
                extra={
                    "user_id": user_id,
                    "phone": normalized_phone[-4:],
                    "error": str(e)
                }
            )
            # Still save the verification record for retry
            verification.twilio_sid = None

        await db.commit()

        logger.info(
            "Phone verification initiated",
            extra={
                "user_id": user_id,
                "phone": normalized_phone[-4:],
                "verification_id": verification.id
            }
        )

        return verification

    @staticmethod
    async def verify_phone(
        user_id: int,
        phone_number: str,
        code: str,
        db: AsyncSession,
    ) -> bool:
        normalized_phone = normalize_phone_number(phone_number)

        # Find latest verification for this user/phone
        result = await db.execute(
            select(PhoneVerification)
            .where(
                and_(
                    PhoneVerification.user_id == user_id,
                    PhoneVerification.phone_number == normalized_phone,
                    PhoneVerification.is_verified == False,
                    PhoneVerification.expires_at > datetime.now(timezone.utc)
                )
            )
            .order_by(PhoneVerification.created_at.desc())
            .limit(1)
        )
        verification = result.scalar_one_or_none()

        if not verification:
            logger.warning(
                "No valid verification found",
                extra={"user_id": user_id, "phone": normalized_phone[-4:]}
            )
            return False

        # Check attempts
        verification.attempts += 1
        if verification.attempts > verification.max_attempts:
            logger.warning(
                "Verification max attempts exceeded",
                extra={
                    "user_id": user_id,
                    "phone": normalized_phone[-4:],
                    "attempts": verification.attempts
                }
            )
            await db.commit()
            return False

        # Verify code
        if not verify_code(code, verification.verification_code_hash):
            logger.info(
                "Verification code mismatch",
                extra={
                    "user_id": user_id,
                    "phone": normalized_phone[-4:],
                    "attempt": verification.attempts
                }
            )
            await db.commit()
            return False

        # Mark as verified
        verification.is_verified = True
        verification.verified_at = datetime.now(timezone.utc)

        # Update notification preferences
        prefs_result = await db.execute(
            select(NotificationPreferences).where(
                NotificationPreferences.user_id == user_id
            )
        )
        prefs = prefs_result.scalar_one_or_none()

        if prefs:
            prefs.sms_phone_number = normalized_phone
            prefs.sms_phone_verified = True
            prefs.sms_phone_verified_at = datetime.now(timezone.utc)
            prefs.sms_notifications_enabled = True

        await db.commit()

        logger.info(
            "Phone verified successfully",
            extra={"user_id": user_id, "phone": normalized_phone[-4:]}
        )

        return True

    @staticmethod
    async def _update_cost_record(
        user_id: int,
        notification_type: SMSNotificationType,
        segments: int,
        cost_cents: int,
        success: bool,
        db: AsyncSession,
    ) -> SMSCostRecord:
        now = datetime.now(timezone.utc)
        year = now.year
        month = now.month

        result = await db.execute(
            select(SMSCostRecord).where(
                and_(
                    SMSCostRecord.user_id == user_id,
                    SMSCostRecord.year == year,
                    SMSCostRecord.month == month,
                    SMSCostRecord.notification_type == notification_type,
                )
            )
        )
        record = result.scalar_one_or_none()

        if not record:
            record = SMSCostRecord(
                user_id=user_id,
                year=year,
                month=month,
                notification_type=notification_type,
            )
            db.add(record)

        record.messages_sent += 1
        record.total_segments += segments
        record.total_cost_cents += cost_cents

        if success:
            record.messages_delivered += 1
        else:
            record.messages_failed += 1

        await db.flush()
        return record

    @staticmethod
    async def send_pending_sms(db: AsyncSession, batch_size: int = 50) -> dict:
        now = datetime.now(timezone.utc)

        # Get pending messages that are due
        result = await db.execute(
            select(SMSQueue)
            .where(
                and_(
                    SMSQueue.status.in_([
                        SMSDeliveryStatus.PENDING,
                        SMSDeliveryStatus.QUEUED_DND
                    ]),
                    SMSQueue.scheduled_for <= now,
                )
            )
            .order_by(SMSQueue.scheduled_for)
            .limit(batch_size)
        )
        messages = result.scalars().all()

        sent = 0
        failed = 0
        skipped = 0

        for sms in messages:
            success, error = await SMSService.send_queued_sms(sms.id, db)
            if success:
                sent += 1
            elif error and "opted out" in error.lower():
                skipped += 1
            else:
                failed += 1

        # Also process retries
        retry_result = await db.execute(
            select(SMSQueue)
            .where(
                and_(
                    SMSQueue.status == SMSDeliveryStatus.PENDING,
                    SMSQueue.retry_count > 0,
                    SMSQueue.next_retry_at <= now,
                )
            )
            .limit(batch_size)
        )
        retries = retry_result.scalars().all()

        retried = 0
        for sms in retries:
            success, _ = await SMSService.send_queued_sms(sms.id, db)
            if success:
                retried += 1

        logger.info(
            "SMS batch processing complete",
            extra={
                "sent": sent,
                "failed": failed,
                "skipped": skipped,
                "retried": retried,
            }
        )

        return {
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
            "retried": retried,
            "processed": len(messages) + len(retries),
        }

    @staticmethod
    async def get_user_sms_stats(
        user_id: int,
        db: AsyncSession,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> dict:
        query = select(SMSCostRecord).where(SMSCostRecord.user_id == user_id)

        if year:
            query = query.where(SMSCostRecord.year == year)
        if month:
            query = query.where(SMSCostRecord.month == month)

        result = await db.execute(query)
        records = result.scalars().all()

        total_sent = sum(r.messages_sent for r in records)
        total_delivered = sum(r.messages_delivered for r in records)
        total_failed = sum(r.messages_failed for r in records)
        total_segments = sum(r.total_segments for r in records)
        total_cost_cents = sum(r.total_cost_cents for r in records)

        # Group by notification type
        by_type = {}
        for r in records:
            type_name = str(r.notification_type)
            if type_name not in by_type:
                by_type[type_name] = {
                    "sent": 0,
                    "delivered": 0,
                    "failed": 0,
                    "segments": 0,
                    "cost_cents": 0,
                }
            by_type[type_name]["sent"] += r.messages_sent
            by_type[type_name]["delivered"] += r.messages_delivered
            by_type[type_name]["failed"] += r.messages_failed
            by_type[type_name]["segments"] += r.total_segments
            by_type[type_name]["cost_cents"] += r.total_cost_cents

        return {
            "total_sent": total_sent,
            "total_delivered": total_delivered,
            "total_failed": total_failed,
            "total_segments": total_segments,
            "total_cost_cents": total_cost_cents,
            "total_cost_dollars": total_cost_cents / 100,
            "by_notification_type": by_type,
        }


# Singleton instance
sms_service = SMSService()
