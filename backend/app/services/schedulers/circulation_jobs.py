# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ...core.config import get_settings
from ...core.database import AsyncSessionLocal, engine
from ...core.email import send_email, COLORS
from ...core.frontend_routes import routes
from ...core.i18n import get_patron_language
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
from ..notifications.preference_gate import should_send_email
from ..notifications.templates import render_hold_ready_email
from .retention_jobs import _send_overdue_notification_email

settings = get_settings()
logger = get_logger(__name__)


def get_overdue_fine_per_day() -> Decimal:
    return Decimal(settings.overdue_fine_per_day)




async def calculate_daily_overdue_fines() -> None:
    async with JobExecutionContext(
        job_id="daily_fine_calculation",
        job_name="Daily Overdue Fine Calculation",
        severity=JobSeverity.HIGH,
    ) as ctx:
        async with AsyncSessionLocal() as db:
            from ...services.fine_policy_service import apply_fine_policy

            now = datetime.now(timezone.utc)

            # Find all checkouts that are past due and not returned/lost
            # Use FOR UPDATE SKIP LOCKED to prevent duplicate processing
            # by concurrent scheduler instances
            # Use selectinload instead of joinedload to avoid
            # "FOR UPDATE cannot be applied to nullable side of outer join"
            stmt = (
                select(Checkout)
                .options(
                    selectinload(Checkout.user),
                    selectinload(Checkout.item),
                    selectinload(Checkout.item_copy),
                )
                .where(
                    and_(
                        Checkout.due_date < now,
                        Checkout.status.in_(
                            [CheckoutStatus.active, CheckoutStatus.overdue]
                        ),
                        Checkout.returned_at.is_(None),
                    )
                )
                .with_for_update(skip_locked=True)
            )

            result = await db.execute(stmt)
            overdue_checkouts = result.unique().scalars().all()

            logger.info(f"Found {len(overdue_checkouts)} overdue checkouts to process")

            fines_created = 0
            fines_updated = 0
            checkouts_marked_overdue = 0

            for checkout in overdue_checkouts:
                try:
                    # Get user and item info
                    user = checkout.user
                    item = checkout.item

                    if not user:
                        logger.warning(
                            f"Skipping checkout {checkout.id}: user not found"
                        )
                        continue

                    # Apply fine policy
                    fine, was_modified = await apply_fine_policy(
                        checkout, user, item, db
                    )

                    # Track results
                    if fine:
                        if was_modified and fine.id:
                            # Existing fine that was updated
                            fines_updated += 1
                        else:
                            # New fine
                            fines_created += 1

                    if checkout.status == CheckoutStatus.overdue:
                        checkouts_marked_overdue += 1

                    ctx.record_success()

                except Exception as e:
                    logger.error(
                        f"Error processing overdue checkout {checkout.id}: {e}",
                        exc_info=True,
                    )
                    ctx.record_failure(
                        error=e,
                        entity_type="checkout",
                        entity_id=checkout.id,
                        context={
                            "user_id": checkout.user_id,
                            "item_id": checkout.item_id,
                            "due_date": (
                                checkout.due_date.isoformat()
                                if checkout.due_date
                                else None
                            ),
                        },
                    )
                    continue

            await db.commit()

            # Add custom metrics
            ctx.add_metric("fines_created", fines_created)
            ctx.add_metric("fines_updated", fines_updated)
            ctx.add_metric("checkouts_marked_overdue", checkouts_marked_overdue)


async def expire_old_holds() -> None:
    async with JobExecutionContext(
        job_id="hourly_hold_expiration",
        job_name="Hourly Hold Expiration Check",
        severity=JobSeverity.HIGH,
    ) as ctx:
        logger.info("Starting hold expiration check")
        holds_expired = 0
        notifications_sent = 0
        queue_advances = 0
        items_released = 0

        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            # Threshold for notified_at fallback (for legacy NULL expires_at)
            notified_at_expiry_threshold = now - timedelta(
                days=settings.hold_expiry_days
            )

            # Find expired holds with FOR UPDATE SKIP LOCKED to prevent
            # duplicate processing by concurrent scheduler instances
            # Include holds where:
            #   1. expires_at is set and has passed, OR
            #   2. expires_at is NULL but notified_at + hold_expiry_days has passed
            #      (handles legacy data with missing expires_at)
            # Use selectinload instead of joinedload to avoid
            # "FOR UPDATE cannot be applied to nullable side of outer join"
            stmt = (
                select(Hold)
                .options(
                    selectinload(Hold.item),
                    selectinload(Hold.user),
                )
                .where(
                    and_(
                        Hold.status.in_([HoldStatus.ready, HoldStatus.pending]),
                        or_(
                            # Case 1: Normal expiration (expires_at is set)
                            and_(
                                Hold.expires_at.isnot(None),
                                Hold.expires_at < now,
                            ),
                            # Case 2: Legacy holds with NULL expires_at but valid notified_at
                            and_(
                                Hold.expires_at.is_(None),
                                Hold.notified_at.isnot(None),
                                Hold.notified_at < notified_at_expiry_threshold,
                            ),
                        ),
                    )
                )
                .order_by(Hold.item_id, Hold.position)
                .with_for_update(skip_locked=True)
            )
            result = await db.execute(stmt)
            expired_holds = result.unique().scalars().all()

            for hold in expired_holds:
                try:
                    # Double-check status after acquiring lock
                    if hold.status == HoldStatus.expired:
                        continue

                    # Mark hold as expired
                    hold.status = HoldStatus.expired
                    holds_expired += 1

                    # Send expiration notification to patron (email + SMS if enabled)
                    if hold.user and hold.item:
                        notification_sent = await _send_hold_expired_notification(
                            hold.user, hold.item, db
                        )
                        if notification_sent:
                            notifications_sent += 1
                        else:
                            logger.warning(
                                "Failed to send hold expiration notification",
                                extra={
                                    "user_id": hold.user_id,
                                    "hold_id": hold.id,
                                    "item_id": hold.item_id,
                                },
                            )

                    # Try to advance the next hold in queue with lock
                    next_hold_stmt = (
                        select(Hold)
                        .options(
                            selectinload(Hold.user),
                            selectinload(Hold.item),
                        )
                        .where(
                            and_(
                                Hold.item_id == hold.item_id,
                                Hold.status == HoldStatus.pending,
                            )
                        )
                        .order_by(Hold.position)
                        .limit(1)
                        .with_for_update()
                    )
                    next_hold_result = await db.execute(next_hold_stmt)
                    next_hold = next_hold_result.scalar_one_or_none()

                    if next_hold:
                        # Promote next pending hold to ready
                        next_hold.status = HoldStatus.ready
                        next_hold.notified_at = now
                        next_hold.expires_at = now + timedelta(
                            days=settings.hold_expiry_days
                        )
                        queue_advances += 1

                        # Send notification to next patron in queue (email + SMS if enabled)
                        if next_hold.user and next_hold.item:
                            notification_sent = await _send_hold_ready_notification(
                                next_hold.user, next_hold.item, db, hold=next_hold
                            )
                            if notification_sent:
                                notifications_sent += 1
                            else:
                                logger.warning(
                                    "Failed to send hold ready notification",
                                    extra={
                                        "user_id": next_hold.user_id,
                                        "hold_id": next_hold.id,
                                        "item_id": next_hold.item_id,
                                    },
                                )
                    else:
                        # No more holds in queue - release item back to available
                        # Only update if item is still on_hold to prevent overwriting
                        # a concurrent checkout or other status change
                        if hold.item:
                            item_stmt = (
                                update(CatalogItem)
                                .where(
                                    CatalogItem.id == hold.item_id,
                                    CatalogItem.status == "on_hold",
                                )
                                .values(status="available")
                            )
                            result = await db.execute(item_stmt)
                            if result.rowcount > 0:
                                items_released += 1

                    ctx.record_success()

                except Exception as e:
                    logger.error(
                        f"Error processing expired hold: {e}",
                        extra={"hold_id": hold.id},
                        exc_info=True,
                    )
                    ctx.record_failure(
                        error=e,
                        entity_type="hold",
                        entity_id=hold.id,
                    )
                    continue

            await db.commit()

        ctx.add_metric("holds_expired", holds_expired)
        ctx.add_metric("queue_advances", queue_advances)
        ctx.add_metric("items_released", items_released)
        ctx.add_metric("notifications_sent", notifications_sent)
        ctx.items_processed = holds_expired
        ctx.items_succeeded = holds_expired - ctx.items_failed
        logger.info(
            "Hold expiration check completed",
            extra={
                "holds_expired": holds_expired,
                "queue_advances": queue_advances,
                "items_released": items_released,
                "notifications_sent": notifications_sent,
            },
        )


async def send_overdue_notifications() -> None:
    async with JobExecutionContext(
        job_id="daily_overdue_notifications",
        job_name="Daily Overdue Notifications",
        severity=JobSeverity.MEDIUM,
    ) as ctx:
        logger.info("Starting overdue notification job")
        notifications_sent = 0

        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            notification_interval = timedelta(
                days=settings.overdue_notice_interval_days
            )

            # Find overdue checkouts eligible for notification (past the interval)
            stmt = (
                select(Checkout)
                .options(
                    joinedload(Checkout.user),
                    joinedload(Checkout.item),
                    joinedload(Checkout.item_copy),
                )
                .where(
                    and_(
                        Checkout.status == CheckoutStatus.overdue,
                        Checkout.returned_at.is_(None),
                        Checkout.due_date + notification_interval < now,
                    )
                )
                .limit(1000)
            )
            result = await db.execute(stmt)
            overdue_checkouts = result.scalars().all()

            # Group checkouts by user
            user_checkouts: dict[int, list[Checkout]] = {}
            for checkout in overdue_checkouts:
                if checkout.user_id not in user_checkouts:
                    user_checkouts[checkout.user_id] = []
                user_checkouts[checkout.user_id].append(checkout)

            # Process each user's overdue items
            for user_id, checkouts in user_checkouts.items():
                user = checkouts[0].user
                if not user or not user.email:
                    continue

                # Notification interval already filtered in SQL query
                # Build and send notification email
                success = await _send_overdue_notification_email(user, checkouts)
                if success:
                    notifications_sent += 1

        ctx.add_metric("notifications_sent", notifications_sent)
        ctx.items_processed = notifications_sent
        ctx.items_succeeded = notifications_sent
        logger.info(
            "Overdue notification job completed",
            extra={"notifications_sent": notifications_sent},
        )


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
        # hold_cancelled is patron-toggleable: honor the email channel toggle,
        # Quiet Hours, and Digest Mode. For digest-mode patrons the gate
        # enqueues this summary; for non-digest blocks a gate-block is a
        # preference, not a failure, so report success -- otherwise the caller
        # logs a false alarm. The gate needs a session; without one (db is
        # None) fall through and send, matching prior behavior.
        if db is not None and not await should_send_email(
            user.id,
            "hold_cancelled",
            db,
            summary=f"Your hold on \"{item.title}\" expired before pickup",
            context_data={"item_id": item.id, "item_title": item.title},
            dedup_key=f"hold_expired:{item.id}",
        ):
            email_sent = True
        else:
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

