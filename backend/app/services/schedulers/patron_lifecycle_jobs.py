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



async def process_expired_suspensions() -> None:
    async with JobExecutionContext(
        job_id="expired_suspension_processing",
        job_name="Expired Suspension Processing",
        severity=JobSeverity.MEDIUM,
    ) as ctx:
        logger.info("Starting expired suspension processing")

        async with AsyncSessionLocal() as db:
            from ..suspension_service import process_expired_suspensions as lift_expired

            suspensions_lifted = await lift_expired(db)
            await db.commit()

        ctx.add_metric("suspensions_lifted", suspensions_lifted)
        ctx.items_processed = suspensions_lifted
        ctx.items_succeeded = suspensions_lifted
        logger.info(
            "Expired suspension processing completed",
            extra={"suspensions_lifted": suspensions_lifted},
        )


async def send_home_delivery_reminders() -> None:
    logger.info("Starting home delivery reminder job")
    reminders_sent = 0
    errors = 0

    try:
        async with AsyncSessionLocal() as db:
            from ..delivery_notification_service import (
                DeliveryNotificationService,
                DeliveryNotificationScheduler,
                NotificationConfig,
            )

            # Initialize notification service with config from settings
            config = NotificationConfig(
                email_enabled=True,
                sms_enabled=settings.sms_enabled,
                email_from=settings.from_email,
                email_from_name="Library HomeDelivery Services",
                reminder_days_before=settings.home_delivery_reminder_days,
                feedback_delay_hours=settings.home_delivery_feedback_delay_hours,
            )

            notification_service = DeliveryNotificationService(config)
            scheduler_service = DeliveryNotificationScheduler(notification_service, db)

            results = await scheduler_service.send_delivery_reminders()

            for result in results:
                if result.success:
                    reminders_sent += 1
                else:
                    errors += 1
                    logger.warning(
                        "Failed to send delivery reminder",
                        extra={
                            "recipient_id": result.recipient_id,
                            "channel": str(result.channel),
                            "error": result.error_message,
                        },
                    )

        logger.info(
            "HomeDelivery delivery reminder job completed",
            extra={
                "reminders_sent": reminders_sent,
                "errors": errors,
            },
        )
    except Exception as e:
        logger.error(f"Error sending home delivery reminders: {e}", exc_info=True)
        raise


async def send_home_delivery_feedback_requests() -> None:
    logger.info("Starting home delivery feedback request job")
    requests_sent = 0
    errors = 0

    try:
        async with AsyncSessionLocal() as db:
            from ..delivery_notification_service import (
                DeliveryNotificationService,
                DeliveryNotificationScheduler,
                NotificationConfig,
            )

            # Initialize notification service with config from settings
            config = NotificationConfig(
                email_enabled=True,
                sms_enabled=settings.sms_enabled,
                email_from=settings.from_email,
                email_from_name="Library HomeDelivery Services",
                reminder_days_before=settings.home_delivery_reminder_days,
                feedback_delay_hours=settings.home_delivery_feedback_delay_hours,
            )

            notification_service = DeliveryNotificationService(config)
            scheduler_service = DeliveryNotificationScheduler(notification_service, db)

            results = await scheduler_service.send_feedback_requests()

            for result in results:
                if result.success:
                    requests_sent += 1
                else:
                    errors += 1
                    logger.warning(
                        "Failed to send feedback request",
                        extra={
                            "recipient_id": result.recipient_id,
                            "channel": str(result.channel),
                            "error": result.error_message,
                        },
                    )

        logger.info(
            "HomeDelivery feedback request job completed",
            extra={
                "requests_sent": requests_sent,
                "errors": errors,
            },
        )
    except Exception as e:
        logger.error(f"Error sending home delivery feedback requests: {e}", exc_info=True)
        raise


async def process_child_to_adult_transitions() -> None:
    async with JobExecutionContext(
        job_id="child_to_adult_transitions",
        job_name="Child to Adult Account Transitions",
        severity=JobSeverity.MEDIUM,
    ) as ctx:
        logger.info("Starting child-to-adult account transition job")
        transitions_completed = 0
        notifications_sent = 0
        parent_notifications_sent = 0
        errors = 0

        async with AsyncSessionLocal() as db:
            from datetime import date

            today = date.today()

            # Get system settings for transition age threshold
            # Default to 18 if no settings configured
            settings_result = await db.execute(select(SystemSettings).limit(1))
            system_settings = settings_result.scalar_one_or_none()

            transition_age = 18  # Default
            auto_transition_enabled = True
            forgive_reading_minutes = True

            if system_settings:
                transition_age = system_settings.age_transition_threshold or 18
                auto_transition_enabled = system_settings.auto_transition_enabled
                forgive_reading_minutes = (
                    system_settings.forgive_reading_minutes_on_transition
                )

            if not auto_transition_enabled:
                logger.info("Automatic child-to-adult transitions are disabled")
                return

            # Calculate the cutoff birth date - users born on or before this date are eligible
            # They must have turned `transition_age` today or earlier
            cutoff_birth_date = date(
                today.year - transition_age, today.month, today.day
            )

            # Find all CHILD users who have reached the transition age.
            # date_of_birth is encrypted at rest, so the "born on/before cutoff"
            # comparison can't run in SQL -- fetch active CHILD users with a DOB
            # and filter app-side (the CHILD cohort is small).
            stmt = (
                select(User)
                .where(
                    and_(
                        User.role == UserRole.CHILD,
                        User.is_active == True,
                        User.date_of_birth.isnot(None),
                    )
                )
                .with_for_update(skip_locked=True)
            )

            result = await db.execute(stmt)
            users_to_transition = [
                u for u in result.scalars().all()
                if u.date_of_birth is not None and u.date_of_birth <= cutoff_birth_date
            ]

            logger.info(
                f"Found {len(users_to_transition)} child accounts eligible for transition",
                extra={"transition_age": transition_age},
            )

            # Get PATRON role settings for reference
            patron_settings_result = await db.execute(
                select(RoleSettings).where(RoleSettings.role == UserRole.PATRON)
            )
            patron_settings_result.scalar_one_or_none()

            for user in users_to_transition:
                try:
                    # Store previous state for audit
                    previous_role = str(user.role)
                    previous_reading_minutes_owed = user.reading_minutes_owed
                    parent_guardian_id = user.parent_guardian_id
                    parent_guardian_email = None

                    # Get parent/guardian email for notification
                    if parent_guardian_id:
                        parent_result = await db.execute(
                            select(User).where(User.id == parent_guardian_id)
                        )
                        parent = parent_result.scalar_one_or_none()
                        if parent:
                            parent_guardian_email = parent.email

                    # Transition the user
                    user.role = UserRole.PATRON

                    # Clear parental consent requirements (no longer needed for adults)
                    user.parental_consent_given = False
                    user.parental_consent_date = None
                    user.parental_consent_email = None
                    user.parental_consent_token = None
                    user.parental_consent_token_expires = None
                    # Keep parent_guardian_id for historical reference but clear dependency

                    # Handle reading minutes
                    reading_minutes_forgiven = 0
                    if forgive_reading_minutes and user.reading_minutes_owed > 0:
                        reading_minutes_forgiven = user.reading_minutes_owed
                        user.reading_minutes_owed = 0
                        user.reading_minutes_logged = 0

                    # Update patron type if exists
                    if user.patron_type == "child":
                        user.patron_type = "adult"

                    # Create audit log entry
                    audit_entry = AuditLog(
                        admin_id=None,  # System automated
                        target_user_id=user.id,
                        action=AuditAction.CHILD_TO_ADULT_TRANSITION,
                        details={
                            "previous_role": previous_role,
                            "new_role": UserRole.PATRON.value,
                            "transition_age": transition_age,
                            "date_of_birth": str(user.date_of_birth),
                            "age_at_transition": user.age,
                            "reading_minutes_forgiven": reading_minutes_forgiven,
                            "previous_reading_minutes_owed": previous_reading_minutes_owed,
                            "parent_guardian_id": parent_guardian_id,
                            "parental_consent_cleared": True,
                        },
                        ip_address=None,
                        user_agent="ChildToAdultTransitionScheduler/1.0",
                    )
                    db.add(audit_entry)

                    transitions_completed += 1

                    # Send notification to the transitioned user
                    if user.email:
                        try:
                            notification_sent = (
                                await _send_account_transition_notification(
                                    user=user,
                                    reading_minutes_forgiven=reading_minutes_forgiven,
                                )
                            )
                            if notification_sent:
                                notifications_sent += 1
                        except Exception as e:  # noqa: BLE001  # per-user iteration - must continue with remaining users
                            logger.warning(
                                f"Failed to send transition notification to user {user.id}: {e}"
                            )

                    # Send notification to parent/guardian
                    if parent_guardian_email:
                        try:
                            parent_notification_sent = (
                                await _send_parent_transition_notification(
                                    parent_email=parent_guardian_email,
                                    child_name=user.full_name,
                                    child_age=user.age or transition_age,
                                )
                            )
                            if parent_notification_sent:
                                parent_notifications_sent += 1
                        except Exception as e:  # noqa: BLE001  # per-user iteration - must continue with remaining users
                            logger.warning(
                                f"Failed to send parent notification for user {user.id}: {e}"
                            )

                    logger.info(
                        f"Transitioned user {user.id} from CHILD to PATRON",
                        extra={
                            "user_id": user.id,
                            "age": user.age,
                            "reading_minutes_forgiven": reading_minutes_forgiven,
                        },
                    )

                except Exception as e:
                    logger.error(
                        f"Error transitioning user {user.id}: {e}",
                        exc_info=True,
                    )
                    errors += 1
                    continue

            await db.commit()

        ctx.add_metric("transitions_completed", transitions_completed)
        ctx.add_metric("notifications_sent", notifications_sent)
        ctx.add_metric("parent_notifications_sent", parent_notifications_sent)
        ctx.add_metric("errors", errors)
        ctx.items_processed = transitions_completed + errors
        ctx.items_succeeded = transitions_completed
        ctx.items_failed = errors
        logger.info(
            "Child-to-adult transition job completed",
            extra={
                "transitions_completed": transitions_completed,
                "notifications_sent": notifications_sent,
                "parent_notifications_sent": parent_notifications_sent,
                "errors": errors,
            },
        )


async def recompute_under_18_flags() -> None:
    """Recompute the maintained ``users.under_18`` age-gate flag.

    ``date_of_birth`` is Fernet-encrypted, so SQL can't compare it. ``under_18``
    is written at insert/update time (see ``User._recompute_under_18``), but a
    patron who is not written on their 18th birthday would keep a stale
    ``under_18 = True`` forever. COPPA data-retention (``_get_minor_patron_ids``)
    now filters on this flag, so a stale True would keep an adult mis-classified
    as a minor (and a never-set NULL would silently exclude a real minor). This
    daily job decrypts each DOB app-side and rewrites the flag when it drifted.

    Boundary semantics (must match ``User.age`` / ``_recompute_under_18``):
    standard age calculation -- a patron is ``under_18`` while strictly younger
    than 18. On the morning of the exact 18th birthday, age becomes 18 and the
    flag flips to False. DOB-less patrons get ``under_18 = NULL`` (unknown).
    """
    async with JobExecutionContext(
        job_id="recompute_under_18_flags",
        job_name="Recompute under_18 Age-Gate Flags",
        severity=JobSeverity.HIGH,
    ) as ctx:
        from ...models.user import TEEN_AGE_THRESHOLD

        logger.info("Starting under_18 age-gate recompute")
        today = date.today()
        scanned = 0
        updated = 0

        async with AsyncSessionLocal() as db:
            # date_of_birth is encrypted, so the age comparison can't run in
            # SQL -- stream users that have a DOB and recompute app-side. The
            # cohort with a DOB is bounded by registered patrons; process in
            # primary-key batches to keep memory flat and avoid a long-held
            # snapshot. Only the flag column is touched, never the DOB.
            last_id = 0
            batch_size = 1000
            while True:
                result = await db.execute(
                    select(User.id, User.date_of_birth, User.under_18)
                    .where(
                        and_(
                            User.id > last_id,
                            User.date_of_birth.isnot(None),
                        )
                    )
                    .order_by(User.id)
                    .limit(batch_size)
                )
                rows = result.all()
                if not rows:
                    break

                for user_id, dob, current_flag in rows:
                    last_id = user_id
                    scanned += 1
                    if dob is None:
                        # Encrypted DOB that failed to decrypt -> leave the flag
                        # untouched rather than guessing an age.
                        continue
                    age = today.year - dob.year - (
                        (today.month, today.day) < (dob.month, dob.day)
                    )
                    desired = age < TEEN_AGE_THRESHOLD
                    if current_flag is desired:
                        continue
                    await db.execute(
                        update(User)
                        .where(User.id == user_id)
                        .values(under_18=desired)
                    )
                    updated += 1

                await db.commit()

        ctx.add_metric("users_scanned", scanned)
        ctx.add_metric("flags_updated", updated)
        ctx.items_processed = scanned
        ctx.items_succeeded = scanned
        logger.info(
            "under_18 age-gate recompute completed",
            extra={"users_scanned": scanned, "flags_updated": updated},
        )


async def _send_account_transition_notification(
    user: User,
    reading_minutes_forgiven: int = 0,
) -> bool:
    subject = "Welcome to Your Adult Library Account!"

    reading_minutes_message = ""
    if reading_minutes_forgiven > 0:
        reading_minutes_message = f"""
        <div style="background-color: #E8F5E9; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0; color: {COLORS['heading']};">
                <strong>Good news!</strong> As part of your transition, we've cleared
                {reading_minutes_forgiven} reading minutes from your account.
                You're starting fresh!
            </p>
        </div>
        """

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Congratulations, {user.first_name}!</h2>
        <p>Happy Birthday! Now that you've turned 18, your library account has been
           automatically upgraded to a full adult patron account.</p>

        <div style="background-color: {COLORS['border']}; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">What's Changed?</h3>
            <ul style="color: {COLORS['body']}; padding-left: 20px;">
                <li>Full access to our entire collection, including adult materials</li>
                <li>Extended checkout limits and loan periods</li>
                <li>Ability to book meeting rooms</li>
                <li>Access to additional digital resources</li>
                <li>No more parental consent requirements</li>
            </ul>
        </div>

        {reading_minutes_message}

        <p style="color: {COLORS['body']};">
            Your library card number and login credentials remain the same.
            If you have any questions about your new account privileges,
            please don't hesitate to ask any staff member.
        </p>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{routes.url(settings.frontend_url, routes.account)}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                View My Account
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name} - {settings.library_name}
        </p>
    </div>
    """

    try:
        return await send_email(user.email, subject, html_content)
    except Exception as e:
        logger.error(
            "Failed to send account transition notification email",
            extra={
                "user_id": user.id,
                "error": str(e),
            },
            exc_info=True,
        )
        return False


async def _send_parent_transition_notification(
    parent_email: str,
    child_name: str,
    child_age: int,
) -> bool:
    subject = f"Library Account Update: {child_name}'s Account Has Transitioned"

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Account Transition Notice</h2>
        <p>Hello,</p>

        <p>We wanted to let you know that <strong>{child_name}</strong>'s library account
           has been automatically upgraded to an adult patron account now that they have
           turned {child_age}.</p>

        <div style="background-color: {COLORS['border']}; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">What This Means:</h3>
            <ul style="color: {COLORS['body']}; padding-left: 20px;">
                <li>Their account is now managed independently</li>
                <li>Parental consent is no longer required for their library activities</li>
                <li>They now have full access to adult library services</li>
                <li>Any outstanding reading minutes have been cleared</li>
            </ul>
        </div>

        <p style="color: {COLORS['body']};">
            Thank you for being part of our library family and for supporting
            {child_name}'s reading journey throughout their childhood.
            We hope they continue to be an active library patron!
        </p>

        <p style="color: {COLORS['text_light']};">
            If you have any questions about this transition, please contact the library.
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name} - {settings.library_name}
        </p>
    </div>
    """

    try:
        return await send_email(parent_email, subject, html_content)
    except Exception as e:
        logger.error(
            "Failed to send parent transition notification email",
            extra={
                "parent_email": parent_email,
                "child_name": child_name,
                "error": str(e),
            },
            exc_info=True,
        )
        return False


# =============================================================================
# Outreach Program Scheduled Jobs
# =============================================================================

async def process_expired_institutional_cards_job() -> None:
    logger.info("Starting expired institutional cards processing")
    cards_expired = 0
    notifications_sent = 0
    errors = 0

    try:
        async with AsyncSessionLocal() as db:
            from ...models.outreach import InstitutionalCard, InstitutionalCardStatus, OutreachPartner
            from datetime import date

            today = date.today()

            # Find all active institutional cards that have expired
            # Note: cannot use joinedload with FOR UPDATE (PostgreSQL rejects
            # FOR UPDATE on the nullable side of an outer join), so we load
            # the partner relationship after the locked select.
            stmt = (
                select(InstitutionalCard)
                .where(
                    and_(
                        InstitutionalCard.status == InstitutionalCardStatus.ACTIVE.value,
                        InstitutionalCard.expiry_date.isnot(None),
                        InstitutionalCard.expiry_date < today,
                    )
                )
                .with_for_update(skip_locked=True)
            )

            result = await db.execute(stmt)
            expired_cards = result.scalars().all()

            # Eagerly load partner for each card (avoids lazy load inside loop)
            for card in expired_cards:
                await db.refresh(card, attribute_names=["partner"])

            logger.info(
                f"Found {len(expired_cards)} institutional cards to expire"
            )

            for card in expired_cards:
                try:
                    # Store previous status for audit
                    previous_status = card.status

                    # Update card status to EXPIRED
                    card.status = InstitutionalCardStatus.EXPIRED.value

                    # Create audit log entry
                    audit_entry = AuditLog(
                        admin_id=None,  # System automated
                        target_user_id=None,
                        action=AuditAction.UPDATE,
                        details={
                            "resource_type": "InstitutionalCard",
                            "resource_id": card.id,
                            "card_number": card.card_number,
                            "partner_id": card.partner_id,
                            "partner_name": card.partner.name if card.partner else None,
                            "previous_status": previous_status,
                            "new_status": InstitutionalCardStatus.EXPIRED.value,
                            "expiry_date": str(card.expiry_date),
                            "reason": "Automatic expiration - expiry date passed",
                        },
                        ip_address=None,
                        user_agent="InstitutionalCardExpirationScheduler/1.0",
                    )
                    db.add(audit_entry)

                    cards_expired += 1

                    # Send notification to partner organization
                    if card.partner and card.partner.primary_contact_email:
                        try:
                            notification_sent = await _send_institutional_card_expired_notification(
                                card=card,
                                partner=card.partner,
                            )
                            if notification_sent:
                                notifications_sent += 1
                        except Exception as e:  # noqa: BLE001  # per-card iteration - must continue with remaining cards
                            logger.warning(
                                f"Failed to send expiration notification for card {card.id}: {e}"
                            )

                    logger.info(
                        f"Expired institutional card {card.id} (card number: {card.card_number})",
                        extra={
                            "card_id": card.id,
                            "card_number": card.card_number,
                            "partner_id": card.partner_id,
                            "expiry_date": str(card.expiry_date),
                        },
                    )

                except Exception as e:
                    logger.error(
                        f"Error expiring institutional card {card.id}: {e}",
                        exc_info=True,
                    )
                    errors += 1
                    continue

            await db.commit()

        logger.info(
            "Expired institutional cards processing completed",
            extra={
                "cards_expired": cards_expired,
                "notifications_sent": notifications_sent,
                "errors": errors,
            },
        )

    except Exception as e:
        logger.error(
            f"Fatal error in institutional card expiration job: {e}", exc_info=True
        )
        raise


async def _send_institutional_card_expired_notification(
    card,
    partner,
) -> bool:
    subject = f"Library Institutional Card Expired - {card.card_name}"

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Institutional Card Expired</h2>
        <p>Dear {partner.primary_contact_name or 'Library Partner'},</p>

        <p>This is to notify you that your institutional library card has expired:</p>

        <div style="background-color: {COLORS['border']}; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">Card Details</h3>
            <p style="margin: 5px 0;"><strong>Card Name:</strong> {card.card_name}</p>
            <p style="margin: 5px 0;"><strong>Card Number:</strong> {card.card_number}</p>
            <p style="margin: 5px 0;"><strong>Expiry Date:</strong> {card.expiry_date.strftime('%B %d, %Y')}</p>
            <p style="margin: 5px 0;"><strong>Organization:</strong> {partner.name}</p>
        </div>

        <div style="background-color: #FFF3CD; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0; color: {COLORS['heading']};">
                <strong>Action Required:</strong> Please contact the library to renew your
                institutional card and restore access to library services for your organization.
            </p>
        </div>

        <p style="color: {COLORS['body']};">
            To renew your card, please contact us at:
        </p>
        <ul style="color: {COLORS['body']};">
            <li>Email: {settings.from_email}</li>
            <li>Phone: Contact your library branch</li>
        </ul>

        <p style="color: {COLORS['body']};">
            Thank you for your continued partnership with {settings.app_name}.
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name} - {settings.library_name}
        </p>
    </div>
    """

    try:
        return await send_email(partner.primary_contact_email, subject, html_content)
    except Exception as e:
        logger.error(
            "Failed to send institutional card expiration notification",
            extra={
                "card_id": card.id,
                "partner_id": partner.id,
                "error": str(e),
            },
            exc_info=True,
        )
        return False


async def send_database_renewal_notifications() -> None:
    logger.info("Starting database renewal notification job")
    notifications_sent = 0
    errors = 0

    try:
        async with AsyncSessionLocal() as db:
            from ...models.database_subscription import (
                DatabaseSubscription,
                DatabaseRenewalNotification,
                SubscriptionStatus,
            )
            from datetime import date, timedelta

            today = date.today()

            # Find all subscriptions that are expiring soon and active/expiring_soon
            stmt = (
                select(DatabaseSubscription)
                .options(joinedload(DatabaseSubscription.vendor))
                .where(
                    and_(
                        DatabaseSubscription.is_active == True,
                        DatabaseSubscription.status.in_([
                            SubscriptionStatus.ACTIVE.value,
                            SubscriptionStatus.EXPIRING_SOON.value,
                        ]),
                        DatabaseSubscription.subscription_end >= today,
                    )
                )
            )

            result = await db.execute(stmt)
            subscriptions = result.scalars().all()

            logger.info(
                f"Checking {len(subscriptions)} active subscriptions for renewal notifications"
            )

            for sub in subscriptions:
                try:
                    days_until_expiry = (sub.subscription_end - today).days

                    # Determine notification type based on days until expiry
                    notification_type = None
                    if days_until_expiry <= 7:
                        notification_type = "7_day"
                    elif days_until_expiry <= 14:
                        notification_type = "14_day"
                    elif days_until_expiry <= 30:
                        notification_type = "30_day"
                    elif days_until_expiry <= sub.renewal_reminder_days:
                        notification_type = "60_day"
                    else:
                        # Not yet in renewal window
                        continue

                    # Check if we already sent this notification type recently (within last 7 days)
                    recent_notification_stmt = (
                        select(DatabaseRenewalNotification)
                        .where(
                            and_(
                                DatabaseRenewalNotification.subscription_id == sub.id,
                                DatabaseRenewalNotification.notification_type == notification_type,
                                DatabaseRenewalNotification.sent_at >= datetime.now(timezone.utc) - timedelta(days=7),
                            )
                        )
                        .limit(1)
                    )
                    recent_result = await db.execute(recent_notification_stmt)
                    recent_notification = recent_result.scalar_one_or_none()

                    if recent_notification:
                        logger.debug(
                            f"Skipping notification for subscription {sub.id} - "
                            f"{notification_type} already sent recently"
                        )
                        continue

                    # Determine recipient email
                    recipient_email = sub.renewal_contact_email
                    if not recipient_email and sub.vendor:
                        recipient_email = sub.vendor.account_rep_email
                    if not recipient_email:
                        logger.warning(
                            f"No renewal contact email for subscription {sub.id}, skipping"
                        )
                        continue

                    # Send renewal notification email
                    notification_sent = await _send_database_renewal_email(
                        subscription=sub,
                        recipient_email=recipient_email,
                        days_until_expiry=days_until_expiry,
                        notification_type=notification_type,
                    )

                    if notification_sent:
                        # Log the notification
                        notification_log = DatabaseRenewalNotification(
                            subscription_id=sub.id,
                            sent_at=datetime.now(timezone.utc),
                            notification_type=notification_type,
                            sent_to=recipient_email,
                            delivered=True,
                        )
                        db.add(notification_log)

                        # Update last_renewal_reminder timestamp on subscription
                        sub.last_renewal_reminder = datetime.now(timezone.utc)

                        notifications_sent += 1

                        logger.info(
                            f"Sent {notification_type} renewal notification for subscription {sub.id}",
                            extra={
                                "subscription_id": sub.id,
                                "subscription_name": sub.name,
                                "days_until_expiry": days_until_expiry,
                                "notification_type": notification_type,
                                "recipient": recipient_email,
                            },
                        )
                    else:
                        # Log failed notification
                        notification_log = DatabaseRenewalNotification(
                            subscription_id=sub.id,
                            sent_at=datetime.now(timezone.utc),
                            notification_type=notification_type,
                            sent_to=recipient_email,
                            delivered=False,
                            error_message="Email delivery failed",
                        )
                        db.add(notification_log)
                        errors += 1

                except Exception as e:
                    logger.error(
                        f"Error processing renewal notification for subscription {sub.id}: {e}",
                        exc_info=True,
                    )
                    errors += 1
                    continue

            await db.commit()

        logger.info(
            "Database renewal notification job completed",
            extra={
                "notifications_sent": notifications_sent,
                "errors": errors,
            },
        )

    except Exception as e:
        logger.error(
            f"Fatal error in database renewal notification job: {e}", exc_info=True
        )
        raise


async def _send_database_renewal_email(
    subscription,
    recipient_email: str,
    days_until_expiry: int,
    notification_type: str,
) -> bool:
    urgency_map = {
        "60_day": ("Renewal Notice", "#3498DB"),
        "30_day": ("Renewal Reminder", "#F39C12"),
        "14_day": ("Urgent: Renewal Required", "#E67E22"),
        "7_day": ("URGENT: Expiring Soon", "#C0392B"),
    }

    subject_prefix, urgency_color = urgency_map.get(notification_type, ("Renewal Notice", "#3498DB"))
    subject = f"{subject_prefix}: {subscription.name} - Expires in {days_until_expiry} days"

    vendor_info = ""
    if subscription.vendor:
        vendor_info = f"""
        <div style="background-color: {COLORS['border']}; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">Vendor Contact</h3>
            <p style="margin: 5px 0;"><strong>Vendor:</strong> {subscription.vendor.name}</p>
            {f'<p style="margin: 5px 0;"><strong>Account Rep:</strong> {subscription.vendor.account_rep_name}</p>' if subscription.vendor.account_rep_name else ''}
            {f'<p style="margin: 5px 0;"><strong>Email:</strong> {subscription.vendor.account_rep_email}</p>' if subscription.vendor.account_rep_email else ''}
            {f'<p style="margin: 5px 0;"><strong>Phone:</strong> {subscription.vendor.account_rep_phone}</p>' if subscription.vendor.account_rep_phone else ''}
        </div>
        """

    cost_info = ""
    if subscription.annual_cost:
        cost_info = f'<p style="margin: 5px 0;"><strong>Annual Cost:</strong> ${subscription.annual_cost:,.2f}</p>'

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: {urgency_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
            <h2 style="margin: 0; color: white;">{subject_prefix}</h2>
        </div>

        <div style="padding: 20px; border: 2px solid {urgency_color}; border-top: none; border-radius: 0 0 8px 8px;">
            <p>This is a reminder that the following database subscription is expiring soon:</p>

            <div style="background-color: #FFF3CD; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid {urgency_color};">
                <h3 style="color: {COLORS['heading']}; margin-top: 0;">Subscription Details</h3>
                <p style="margin: 5px 0;"><strong>Database:</strong> {subscription.name}</p>
                <p style="margin: 5px 0;"><strong>Expiration Date:</strong> {subscription.subscription_end.strftime('%B %d, %Y')}</p>
                <p style="margin: 5px 0; color: {urgency_color}; font-size: 18px;">
                    <strong>Days Remaining: {days_until_expiry}</strong>
                </p>
                {cost_info}
                {f'<p style="margin: 5px 0;"><strong>Contract #:</strong> {subscription.contract_number}</p>' if subscription.contract_number else ''}
            </div>

            {vendor_info}

            <div style="background-color: {COLORS['border']}; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: {COLORS['heading']}; margin-top: 0;">Action Required</h3>
                <p style="margin: 0; color: {COLORS['body']};">
                    Please review this subscription and take appropriate action:
                </p>
                <ul style="color: {COLORS['body']};">
                    <li>Contact the vendor to negotiate renewal terms</li>
                    <li>Review usage statistics to justify renewal</li>
                    <li>Prepare budget approval if needed</li>
                    <li>Update subscription details in the system</li>
                </ul>
            </div>

            {f'<p style="color: {COLORS["body"]};">Renewal notes: {subscription.renewal_notes}</p>' if subscription.renewal_notes else ''}

            <p style="text-align: center; margin: 30px 0;">
                <a href="{routes.url(settings.frontend_url, routes.admin_databases, id=subscription.id)}"
                   style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    View Subscription Details
                </a>
            </p>
        </div>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            This is an automated reminder from {settings.app_name}. If you have already renewed
            this subscription, please update the expiration date in the system.
        </p>
    </div>
    """

    try:
        return await send_email(recipient_email, subject, html_content)
    except Exception as e:
        logger.error(
            "Failed to send database renewal notification email",
            extra={
                "subscription_id": subscription.id,
                "recipient_email": recipient_email,
                "error": str(e),
            },
            exc_info=True,
        )
        return False


