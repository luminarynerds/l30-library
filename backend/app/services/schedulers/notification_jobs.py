# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import contextlib
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ...core.cache import get_redis
from ...core.config import get_settings
from ...core.database import AsyncSessionLocal, engine
from ...core.email import send_email, COLORS
from ...core.frontend_routes import routes
from ...core.i18n import get_patron_language, get_translator
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
from ..notifications.preference_gate import (
    should_send_email,
    should_send_email_by_email,
)
from ..notifications.templates import render_hold_expiring_email, render_hold_ready_email

settings = get_settings()
logger = get_logger(__name__)


def get_overdue_fine_per_day() -> Decimal:
    return Decimal(settings.overdue_fine_per_day)

async def _send_hold_expired_notification(
    user: User, item: CatalogItem, db: Optional[AsyncSession] = None
) -> bool:
    from ..sms_service import SMSService

    subject = f"Your hold has expired: {item.title}"

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Hold Expired</h2>
        <p>Hi {user.first_name},</p>
        <p>Unfortunately, your hold has expired because it was not picked up within the allowed timeframe.</p>
        <div style="background-color: {COLORS['border']}; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <strong style="color: {COLORS['heading']};">{item.title}</strong>
            {f'<br><span style="color: {COLORS["body"]};">by {item.author}</span>' if item.author else ''}
        </div>
        <p>The item is now available to other patrons. If you would like to request this item again,
           you can place a new hold from your account.</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{routes.url(settings.frontend_url, routes.account_holds_alt)}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Place a New Hold
            </a>
        </p>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name} - {settings.library_name}
        </p>
    </div>
    """

    try:
        email_sent = await send_email(user.email, subject, html_content)
    except Exception as e:
        logger.error(
            "Failed to send hold expired notification email",
            extra={
                "user_id": user.id,
                "item_id": item.id,
                "error": str(e),
            },
            exc_info=True,
        )
        email_sent = False

    # Send SMS notification if db session provided and user has SMS enabled
    if db is not None:
        try:
            prefs = await SMSService.get_sms_preferences(user.id, db)
            if (
                prefs
                and prefs.sms_notifications_enabled
                and prefs.sms_hold_expired
                and prefs.sms_phone_number
                and prefs.sms_phone_verified
            ):
                # Get or render the SMS template
                template = await SMSService.get_or_create_template(
                    SMSNotificationType.HOLD_EXPIRED, db
                )
                message = SMSService.render_template(
                    template.template_body,
                    {
                        "title": item.title[:50],  # Truncate long titles
                    },
                )

                # Queue the SMS
                await SMSService.queue_sms(
                    user_id=user.id,
                    phone_number=prefs.sms_phone_number,
                    notification_type=SMSNotificationType.HOLD_EXPIRED,
                    message=message,
                    context_data={"item_id": item.id, "item_title": item.title},
                    db=db,
                )
                logger.info(
                    "SMS queued for hold expired notification",
                    extra={
                        "user_id": user.id,
                        "item_id": item.id,
                    },
                )
        except Exception as e:  # noqa: BLE001  # SMS dispatch boundary - must not fail email-side success
            # SMS failure should not affect email notification success
            logger.warning(
                "Failed to queue SMS for hold expired notification",
                extra={
                    "user_id": user.id,
                    "item_id": item.id,
                    "error": str(e),
                },
            )

    return email_sent


async def _send_hold_ready_notification(
    user: User,
    item: CatalogItem,
    db: Optional[AsyncSession] = None,
    hold: Optional[Hold] = None,
) -> bool:
    from ..sms_service import SMSService

    lang = await get_patron_language(user, db)
    subject, html_content = render_hold_ready_email(user, item, hold, lang)

    email_sent = await send_email(user.email, subject, html_content)

    # Send SMS notification if db session provided and user has SMS enabled
    if db is not None:
        try:
            prefs = await SMSService.get_sms_preferences(user.id, db)
            if (
                prefs
                and prefs.sms_notifications_enabled
                and prefs.sms_hold_ready
                and prefs.sms_phone_number
                and prefs.sms_phone_verified
            ):
                # Calculate expiry date for the SMS message
                expires_date = (
                    datetime.now(timezone.utc)
                    + timedelta(days=settings.hold_expiry_days)
                ).strftime("%B %d")

                # Get or render the SMS template
                template = await SMSService.get_or_create_template(
                    SMSNotificationType.HOLD_READY, db
                )
                message = SMSService.render_template(
                    template.template_body,
                    {
                        "title": item.title[:50],  # Truncate long titles
                        "expires_date": expires_date,
                        "phone": getattr(settings, "library_phone", ""),
                    },
                )

                # Queue the SMS
                await SMSService.queue_sms(
                    user_id=user.id,
                    phone_number=prefs.sms_phone_number,
                    notification_type=SMSNotificationType.HOLD_READY,
                    message=message,
                    context_data={"item_id": item.id, "item_title": item.title},
                    db=db,
                )
                logger.info(
                    "SMS queued for hold ready notification",
                    extra={
                        "user_id": user.id,
                        "item_id": item.id,
                    },
                )
        except Exception as e:  # noqa: BLE001  # SMS dispatch boundary - must not fail email-side success
            # SMS failure should not affect email notification success
            logger.warning(
                "Failed to queue SMS for hold ready notification",
                extra={
                    "user_id": user.id,
                    "item_id": item.id,
                    "error": str(e),
                },
            )

    return email_sent


async def send_hold_expiration_reminders() -> None:
    logger.info("Starting hold expiration reminder job")
    reminders_sent = 0
    holds_checked = 0

    try:
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            # Find holds expiring within 2 days (48 hours from now)
            reminder_threshold = now + timedelta(days=2)

            # Find ready holds that:
            # 1. Have an expires_at date within 2 days
            # 2. Have NOT already received a reminder (reminder_sent_at is NULL)
            stmt = (
                select(Hold)
                .options(
                    joinedload(Hold.item),
                    joinedload(Hold.user),
                )
                .where(
                    and_(
                        Hold.status == HoldStatus.ready,
                        Hold.expires_at.isnot(None),
                        Hold.expires_at <= reminder_threshold,
                        Hold.expires_at > now,  # Not already expired
                        Hold.reminder_sent_at.is_(None),  # No reminder sent yet
                    )
                )
                .with_for_update(skip_locked=True, of=Hold)
            )

            result = await db.execute(stmt)
            holds_to_remind = result.unique().scalars().all()

            logger.info(
                f"Found {len(holds_to_remind)} holds needing expiration reminders"
            )

            for hold in holds_to_remind:
                holds_checked += 1
                try:
                    if not hold.user or not hold.item:
                        logger.warning(
                            f"Skipping hold {hold.id}: missing user or item",
                            extra={"hold_id": hold.id},
                        )
                        continue

                    if not hold.user.email:
                        logger.warning(
                            f"Skipping hold {hold.id}: user has no email",
                            extra={"hold_id": hold.id, "user_id": hold.user_id},
                        )
                        continue

                    # Send reminder notification
                    notification_sent = (
                        await _send_hold_expiration_reminder_notification(
                            user=hold.user,
                            item=hold.item,
                            expires_at=hold.expires_at,
                            hold=hold,
                            db=db,
                        )
                    )

                    if notification_sent:
                        # Mark reminder as sent
                        hold.reminder_sent_at = now
                        reminders_sent += 1
                        logger.debug(
                            f"Sent hold expiration reminder for hold {hold.id}",
                            extra={
                                "hold_id": hold.id,
                                "user_id": hold.user_id,
                                "item_id": hold.item_id,
                                "expires_at": hold.expires_at.isoformat(),
                            },
                        )
                    else:
                        logger.warning(
                            "Failed to send hold expiration reminder",
                            extra={
                                "hold_id": hold.id,
                                "user_id": hold.user_id,
                            },
                        )

                except Exception as e:
                    logger.error(
                        f"Error processing hold expiration reminder: {e}",
                        extra={"hold_id": hold.id},
                        exc_info=True,
                    )
                    continue

            await db.commit()

        logger.info(
            "Hold expiration reminder job completed",
            extra={
                "holds_checked": holds_checked,
                "reminders_sent": reminders_sent,
            },
        )
    except Exception as e:
        logger.error(f"Error in hold expiration reminder job: {e}", exc_info=True)
        raise


async def send_smart_automated_communications() -> None:
    logger.info("Starting smart automated communications job")
    notifications_sent = 0

    try:
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            today = now.date()

            notifications_sent += await _send_due_date_communications(db, now)
            notifications_sent += await _send_hold_expiring_tomorrow_communications(
                db, now
            )
            notifications_sent += await _send_card_expiry_next_month_communications(
                db, today
            )
            notifications_sent += await _send_inactive_patron_winback_communications(
                db, now
            )
            notifications_sent += await _send_post_event_feedback_communications(
                db, now
            )
            notifications_sent += await _send_reading_milestone_communications(db, now)

        logger.info(
            "Smart automated communications job completed",
            extra={"notifications_sent": notifications_sent},
        )
    except Exception as e:
        logger.error(f"Error in smart automated communications job: {e}", exc_info=True)
        raise


async def _send_due_date_communications(db: AsyncSession, now: datetime) -> int:
    sent = 0
    # Only fetch checkouts in the actionable window: due within 3 days or overdue within 30 days
    date_window_start = now - timedelta(days=30)
    date_window_end = now + timedelta(days=3)
    stmt = (
        select(Checkout)
        .options(
            joinedload(Checkout.user),
            joinedload(Checkout.item),
            joinedload(Checkout.item_copy),
        )
        .where(
            and_(
                Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
                Checkout.returned_at.is_(None),
                Checkout.due_date >= date_window_start,
                Checkout.due_date <= date_window_end,
            )
        )
        .limit(1000)
    )
    checkouts = (await db.execute(stmt)).scalars().all()

    grouped: dict[tuple[int, str], list[Checkout]] = {}
    for checkout in checkouts:
        if not checkout.user or not checkout.user.email or not checkout.due_date:
            continue

        days_delta = (checkout.due_date.date() - now.date()).days
        template = None
        if checkout.status == CheckoutStatus.active and days_delta == 3:
            template = "predue_3_days"
        elif checkout.status == CheckoutStatus.active and days_delta == 0:
            template = "due_today"
        elif checkout.status == CheckoutStatus.overdue:
            overdue_days = max((now.date() - checkout.due_date.date()).days, 0)
            if overdue_days in {1, 7, 14, 30}:
                template = f"overdue_day_{overdue_days}"

        if template:
            grouped.setdefault((checkout.user_id, template), []).append(checkout)

    for (user_id, template), patron_checkouts in grouped.items():
        # predue/due-today map to the patron-toggleable due_date_reminder type;
        # overdue_day_* maps to overdue_notice (a REQUIRED type the gate always
        # allows). Routed through the gate either way so channel toggles, Quiet
        # Hours, and Digest Mode apply consistently with the nightly sweep.
        is_overdue = template.startswith("overdue_day_")
        ntype = "overdue_notice" if is_overdue else "due_date_reminder"
        count = len(patron_checkouts)
        plural = "s" if count != 1 else ""
        # overdue_notice is REQUIRED so summary is ignored (never digested);
        # due_date_reminder gets a digest line for Digest Mode patrons.
        summary = None if is_overdue else f"{count} item{plural} due soon"
        if not await should_send_email(
            user_id,
            ntype,
            db,
            summary=summary,
            context_data={"item_count": count, "template": template},
            dedup_key=f"smartcomm:{template}:{now.date().isoformat()}",
        ):
            continue
        lang = await get_patron_language(patron_checkouts[0].user, db)
        if await _send_due_date_email(
            patron_checkouts[0].user, patron_checkouts, template, now, lang=lang
        ):
            sent += 1
            # Escalation tiers (day 1/7/14/30) also stage an in-app
            # OVERDUE_NOTICE row, sharing the same key namespace as
            # _sweep_overdue_notices so the two paths together emit at
            # most one in-app row per patron per UTC day. Pre-due and
            # due-today templates remain email-only here; they are
            # covered by the courtesy-reminder sweep's separate key.
            if template.startswith("overdue_day_"):
                from ..patron_notifications import (
                    _record_overdue_notice_in_app,
                )

                fine_per_day = get_overdue_fine_per_day()
                await _record_overdue_notice_in_app(
                    db, user_id, patron_checkouts, fine_per_day, now
                )

    await db.commit()
    return sent


async def _send_due_date_email(
    user: User,
    checkouts: list[Checkout],
    template: str,
    now: datetime,
    lang: str = "en",
) -> bool:
    tr = get_translator(lang)
    if template == "predue_3_days":
        subject = tr("email.due_group.subject_predue")
        intro = tr("email.due_group.intro_predue")
    elif template == "due_today":
        subject = tr("email.due_group.subject_due_today")
        intro = tr("email.due_group.intro_due_today")
    else:
        day = template.split("_")[-1]
        subject = tr("email.due_group.subject_overdue", day=day)
        intro = tr("email.due_group.intro_overdue", day=day)

    rows = ""
    for checkout in checkouts:
        title = checkout.item.title if checkout.item else "Library item"
        due_str = checkout.due_date.strftime("%B %d, %Y")
        due_label = tr("email.due_group.item_due_label", due_date=due_str)
        rows += f"<li><strong>{title}</strong> {due_label}</li>"

    html = f"""
    <div style=\"font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;\">
        <h2 style=\"color: {COLORS['heading']};\">{settings.app_name} Reminder</h2>
        <p>{tr('email.due_group.greeting', user_name=user.first_name)}</p>
        <p>{intro}</p>
        <ul>{rows}</ul>
        <p style=\"text-align: center; margin: 24px 0;\">
            <a href=\"{routes.url(settings.frontend_url, routes.account_checkouts_alt)}\"
               style=\"background-color: {COLORS['button']}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;\">{tr('email.due_group.manage_items_button')}</a>
        </p>
        <p style=\"color: {COLORS['text_light']}; font-size: 12px;\">{tr('email.due_group.sent_footer', date=now.strftime('%B %d, %Y'), app_name=settings.app_name)}</p>
    </div>
    """
    return await send_email(user.email, subject, html)


async def _send_hold_expiring_tomorrow_communications(
    db: AsyncSession, now: datetime
) -> int:
    sent = 0
    tomorrow_start = datetime.combine(
        now.date() + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
    )
    tomorrow_end = tomorrow_start + timedelta(days=1)

    stmt = (
        select(Hold)
        .options(joinedload(Hold.user), joinedload(Hold.item))
        .where(
            and_(
                Hold.status == HoldStatus.ready,
                Hold.expires_at.isnot(None),
                Hold.expires_at >= tomorrow_start,
                Hold.expires_at < tomorrow_end,
                Hold.reminder_sent_at.is_(None),
            )
        )
        .with_for_update(skip_locked=True, of=Hold)
    )
    holds = (await db.execute(stmt)).unique().scalars().all()

    for hold in holds:
        if not hold.user or not hold.user.email or not hold.item:
            continue
        if await _send_hold_expiration_reminder_notification(
            hold.user, hold.item, hold.expires_at, hold=hold, db=db
        ):
            hold.reminder_sent_at = now
            sent += 1

    await db.commit()
    return sent


async def _send_card_expiry_next_month_communications(
    db: AsyncSession, today: date
) -> int:
    # Send monthly on the first day to avoid duplicate notices.
    if today.day != 1:
        return 0

    first_day_next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    second_month = (first_day_next_month.replace(day=28) + timedelta(days=4)).replace(
        day=1
    )

    stmt = (
        select(User).where(
            and_(
                User.is_active == True,
                User.email.isnot(None),
                User.card_expires_at.isnot(None),
                User.card_expires_at >= first_day_next_month,
                User.card_expires_at < second_month,
                User.role.in_([UserRole.PATRON, UserRole.CHILD]),
            )
        )
        .limit(500)
    )
    users = (await db.execute(stmt)).scalars().all()

    sent = 0
    for user in users:
        expires = user.card_expires_at.strftime("%B %d, %Y")
        html = f"""
        <div style=\"font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;\">
            <h2 style=\"color: {COLORS['heading']};\">Library Card Renewal Reminder</h2>
            <p>Hi {user.first_name},</p>
            <p>Your library card expires next month on <strong>{expires}</strong>.</p>
            <p>Renew now so your borrowing, holds, and digital access stay uninterrupted.</p>
        </div>
        """
        if await send_email(user.email, "Your library card expires next month", html):
            sent += 1
    return sent


async def _send_inactive_patron_winback_communications(
    db: AsyncSession, now: datetime
) -> int:
    # Send monthly to long-inactive patrons to avoid fatigue.
    if now.day != 1:
        return 0

    inactivity_threshold = now - timedelta(days=180)
    stmt = (
        select(User).where(
            and_(
                User.is_active == True,
                User.role.in_([UserRole.PATRON, UserRole.CHILD]),
                User.email.isnot(None),
                or_(User.last_login.is_(None), User.last_login <= inactivity_threshold),
            )
        )
        .limit(500)
    )
    users = (await db.execute(stmt)).scalars().all()
    sent = 0
    for user in users:
        html = f"""
        <div style=\"font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;\">
            <h2 style=\"color: {COLORS['heading']};\">We miss you at {settings.app_name}</h2>
            <p>Hi {user.first_name},</p>
            <p>It has been a while since your last visit. We’d love to welcome you back!</p>
            <p>Check out new arrivals, upcoming programs, and fresh recommendations picked just for you.</p>
        </div>
        """
        if await send_email(
            user.email, "We miss you! Come back and see what's new", html
        ):
            sent += 1
    return sent


async def _send_post_event_feedback_communications(
    db: AsyncSession, now: datetime
) -> int:
    yesterday_start = datetime.combine(
        now.date() - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
    )
    today_start = datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc)

    stmt = (
        select(EventRegistration, Event)
        .join(Event, Event.id == EventRegistration.event_id)
        .where(
            and_(
                EventRegistration.status == EventRegistrationStatus.CONFIRMED.value,
                Event.end_time.isnot(None),
                Event.end_time >= yesterday_start,
                Event.end_time < today_start,
            )
        )
    )
    rows = (await db.execute(stmt)).all()

    sent = 0
    for reg, event in rows:
        existing_review = await db.execute(
            select(EventReview.id).where(
                and_(
                    EventReview.event_id == event.id,
                    EventReview.patron_email == reg.patron_email,
                )
            )
        )
        if existing_review.scalar_one_or_none() is not None:
            continue

        html = f"""
        <div style=\"font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;\">
            <h2 style=\"color: {COLORS['heading']};\">How was {event.title}?</h2>
            <p>Hi {reg.patron_name},</p>
            <p>Thanks for attending! We’d love your feedback to make future events even better.</p>
            <p>Please share a quick rating and comment when you have a moment.</p>
        </div>
        """
        if await send_email(reg.patron_email, f"How was '{event.title}'?", html):
            sent += 1

    return sent


async def _send_reading_milestone_communications(
    db: AsyncSession, now: datetime
) -> int:
    window_start = now - timedelta(days=1)
    stmt = (
        select(ReadingAchievement, User)
        .join(User, User.id == ReadingAchievement.user_id)
        .where(
            and_(
                ReadingAchievement.unlocked_at >= window_start,
                User.email.isnot(None),
            )
        )
    )
    rows = (await db.execute(stmt)).all()

    sent = 0
    for achievement, user in rows:
        html = f"""
        <div style=\"font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;\">
            <h2 style=\"color: {COLORS['heading']};\">🎉 Reading Milestone Unlocked!</h2>
            <p>Hi {user.first_name},</p>
            <p>You just earned <strong>{achievement.badge_name}</strong>.</p>
            <p>{achievement.badge_description or 'Great work-keep reading!'}</p>
        </div>
        """
        if await send_email(
            user.email, f"🎉 You earned: {achievement.badge_name}", html
        ):
            sent += 1
    return sent


async def _send_hold_expiration_reminder_notification(
    user: User,
    item: CatalogItem,
    expires_at: datetime,
    hold: Optional[Hold] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    days_until_expiry = max((expires_at - datetime.now(timezone.utc)).days, 0)
    lang = await get_patron_language(user, db)
    effective_hold = hold if hold is not None else SimpleNamespace(expires_at=expires_at)
    subject, html_content = render_hold_expiring_email(
        user, item, effective_hold, days_until_expiry, lang
    )

    try:
        return await send_email(user.email, subject, html_content)
    except Exception as e:
        logger.error(
            "Failed to send hold expiration reminder email",
            extra={
                "user_id": user.id,
                "item_id": item.id,
                "error": str(e),
            },
            exc_info=True,
        )
        return False


async def send_event_reminders() -> None:
    from sqlalchemy.orm import selectinload
    from ..notifications.email_sender import EmailSenderService
    from ..notifications.types import NotificationType as _SenderNotificationType

    async with JobExecutionContext(
        "event_reminders_24h",
        "Event Reminders (24h)",
        severity=JobSeverity.LOW,
    ) as ctx:
        sender = EmailSenderService()
        now = datetime.now(timezone.utc)
        window_start = now + timedelta(hours=23)
        window_end = now + timedelta(hours=25)

        async with AsyncSessionLocal() as db:
            stmt = (
                select(EventRegistration)
                .options(selectinload(EventRegistration.event))
                .join(Event, Event.id == EventRegistration.event_id)
                .where(
                    and_(
                        Event.is_published == True,  # noqa: E712
                        Event.start_time >= window_start,
                        Event.start_time <= window_end,
                        EventRegistration.status
                        == EventRegistrationStatus.CONFIRMED.value,
                        EventRegistration.reminder_requested == True,  # noqa: E712
                        EventRegistration.reminder_sent_at.is_(None),
                    )
                )
            )
            registrations = (await db.execute(stmt)).scalars().all()

            logger.info(
                "Event reminder scan complete",
                extra={"candidates": len(registrations)},
            )

            for reg in registrations:
                event = reg.event
                try:
                    if not reg.patron_email or event is None:
                        continue

                    event_date_str = event.start_time.strftime("%B %d, %Y")
                    event_time_str = event.start_time.strftime("%I:%M %p").lstrip("0")
                    location_str = (
                        event.virtual_link
                        if event.is_virtual and event.virtual_link
                        else (event.location or "TBD")
                    )

                    context = {
                        "patron_name": reg.patron_name or "Patron",
                        "event_title": event.title,
                        "event_date": event_date_str,
                        "event_time": event_time_str,
                        "event_location": location_str,
                    }

                    # Honor channel toggle / Quiet Hours / Digest Mode when
                    # the registration email resolves to a known user. True
                    # guest registrations (no matching account) send freely.
                    # On gate-block do NOT set reminder_sent_at -- the 23-25h
                    # scan window naturally retries on the next hourly tick,
                    # so a Quiet-Hours suppression can still resolve before
                    # the window closes. event_reminder is NOT in
                    # REQUIRED_NOTIFICATION_TYPES, so the bypass for critical
                    # types does not apply here.
                    if not await should_send_email_by_email(
                        reg.patron_email,
                        "event_reminder",
                        db,
                    ):
                        continue

                    sent = await sender.send_templated(
                        notification_type=_SenderNotificationType.EVENT_REMINDER,
                        recipient_email=reg.patron_email,
                        context_data=context,
                    )

                    if sent:
                        # Mark sent BEFORE commit so a concurrent run of the
                        # same job (overlapping cron tick) does not double-send.
                        reg.reminder_sent_at = datetime.now(timezone.utc)
                        await db.commit()
                        ctx.record_success()
                        logger.info(
                            "Sent event reminder",
                            extra={
                                "registration_id": reg.id,
                                "event_id": event.id,
                            },
                        )
                    else:
                        # Do NOT set reminder_sent_at -- next hourly run retries.
                        ctx.record_failure(
                            Exception("send_templated returned False"),
                            entity_type="event_registration",
                            entity_id=reg.id,
                            context={"event_id": event.id},
                        )
                except Exception as e:
                    # Roll back any pending mutations on this session so a
                    # later row can still commit its own reminder_sent_at.
                    with contextlib.suppress(SQLAlchemyError):
                        await db.rollback()
                    logger.error(
                        "Failed to send event reminder",
                        extra={
                            "registration_id": reg.id,
                            "event_id": getattr(event, "id", None),
                            "error": str(e),
                        },
                        exc_info=True,
                    )
                    ctx.record_failure(
                        e,
                        entity_type="event_registration",
                        entity_id=reg.id,
                        context={"event_id": getattr(event, "id", None)},
                    )
                    continue
