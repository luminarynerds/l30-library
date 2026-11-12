# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import html
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Optional

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..core.config import get_settings
from ..core.frontend_routes import routes
from ..core.database import AsyncSessionLocal
from ..core.email import send_email, COLORS
from ..core.i18n import get_patron_language
from ..core.logging import get_logger
from ..models.catalog import CatalogItem
from ..models.circulation import Hold, HoldStatus
from ..models.sms import SMSNotificationType
from ..models.user import User
from .notifications.templates import render_hold_expiring_email, render_hold_ready_email

settings = get_settings()
logger = get_logger(__name__)


async def expire_old_holds() -> None:
    logger.info("Starting hold expiration check")
    holds_expired = 0
    notifications_sent = 0
    queue_advances = 0
    items_released = 0

    try:
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            # Threshold for notified_at fallback (for legacy NULL expires_at)
            notified_at_expiry_threshold = now - timedelta(days=settings.hold_expiry_days)

            # Find expired holds with FOR UPDATE SKIP LOCKED to prevent
            # duplicate processing by concurrent scheduler instances
            # Include holds where:
            #   1. expires_at is set and has passed, OR
            #   2. expires_at is NULL but notified_at + hold_expiry_days has passed
            #      (handles legacy data with missing expires_at)
            stmt = (
                select(Hold)
                .options(
                    joinedload(Hold.item),
                    joinedload(Hold.user),
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
                        if hold.item:
                            from ..models.catalog import CatalogItem
                            item_stmt = (
                                update(CatalogItem)
                                .where(CatalogItem.id == hold.item_id)
                                .values(status="available")
                            )
                            await db.execute(item_stmt)
                            items_released += 1

                except Exception as e:
                    logger.error(
                        f"Error processing expired hold: {e}",
                        extra={"hold_id": hold.id},
                        exc_info=True,
                    )
                    # Continue processing other holds despite this error
                    continue

            await db.commit()

        logger.info(
            "Hold expiration check completed",
            extra={
                "holds_expired": holds_expired,
                "queue_advances": queue_advances,
                "items_released": items_released,
                "notifications_sent": notifications_sent,
            },
        )
    except Exception as e:
        logger.error(f"Error expiring holds: {e}", exc_info=True)
        raise


async def _send_hold_expired_notification(
    user: User,
    item: CatalogItem,
    db: Optional[AsyncSession] = None
) -> bool:
    from .sms_service import SMSService

    subject = f"Your hold has expired: {item.title}"

    # User and item fields are HTML-escaped because they originate from
    # patron and catalog input and would otherwise allow HTML/script
    # injection in mail clients that render the body.
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Hold Expired</h2>
        <p>Hi {html.escape(user.first_name or "")},</p>
        <p>Unfortunately, your hold has expired because it was not picked up within the allowed timeframe.</p>
        <div style="background-color: {COLORS['border']}; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <strong style="color: {COLORS['heading']};">{html.escape(item.title or "")}</strong>
            {f'<br><span style="color: {COLORS["body"]};">by {html.escape(item.author)}</span>' if item.author else ''}
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
                    }
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
        except Exception as e:  # noqa: BLE001 -- channel failure must not block other channels: SMS failure won't fail email
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
    from .sms_service import SMSService

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
                    datetime.now(timezone.utc) + timedelta(days=settings.hold_expiry_days)
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
                        "phone": getattr(settings, 'library_phone', ""),
                    }
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
        except Exception as e:  # noqa: BLE001 -- channel failure must not block other channels: SMS failure won't fail email
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
                .with_for_update(skip_locked=True)
            )

            result = await db.execute(stmt)
            holds_to_remind = result.unique().scalars().all()

            logger.info(f"Found {len(holds_to_remind)} holds needing expiration reminders")

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
                    notification_sent = await _send_hold_expiration_reminder_notification(
                        user=hold.user,
                        item=hold.item,
                        expires_at=hold.expires_at,
                        hold=hold,
                        db=db,
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


async def auto_requeue_expired_ready_holds() -> None:
    from .smart_hold_shelf_service import (
        requeue_hold_after_no_show,
        ON_WAY_STALE_HOURS,
    )

    logger.info("Starting auto re-queue for expired ready holds")
    requeued = 0
    skipped_on_way = 0

    try:
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            stale_on_way_threshold = now - timedelta(hours=ON_WAY_STALE_HOURS)

            # Find expired ready holds, excluding recent patron-on-way
            stmt = (
                select(Hold)
                .options(joinedload(Hold.user), joinedload(Hold.item))
                .where(
                    and_(
                        Hold.status == HoldStatus.ready,
                        Hold.expires_at.isnot(None),
                        Hold.expires_at < now,
                        or_(
                            Hold.patron_on_way == False,  # noqa: E712
                            and_(
                                Hold.patron_on_way == True,  # noqa: E712
                                Hold.patron_on_way_at.isnot(None),
                                Hold.patron_on_way_at < stale_on_way_threshold,
                            ),
                        ),
                    )
                )
                .with_for_update(skip_locked=True)
            )
            result = await db.execute(stmt)
            expired_holds = result.unique().scalars().all()

            for hold in expired_holds:
                try:
                    await requeue_hold_after_no_show(hold, db)
                    requeued += 1
                except Exception as e:
                    logger.error(
                        f"Error re-queuing hold {hold.id}: {e}",
                        exc_info=True,
                    )

            await db.commit()

        logger.info(
            "Auto re-queue completed",
            extra={
                "requeued": requeued,
                "skipped_on_way": skipped_on_way,
            },
        )
    except Exception as e:
        logger.error(f"Error in auto re-queue job: {e}", exc_info=True)
        raise


async def send_daily_expiring_holds_report() -> None:
    from .smart_hold_shelf_service import get_expiring_holds_sorted

    logger.info("Generating daily expiring holds report")

    try:
        async with AsyncSessionLocal() as db:
            # Get holds expiring in the next 24 hours
            holds = await get_expiring_holds_sorted(db, hours_threshold=24)

            if not holds:
                logger.info("No holds expiring today")
                return

            # Build report email
            items_html = ""
            for hold in holds:
                # Patron + item + slot fields are HTML-escaped before
                # interpolation -- staff-only audience but the same XSS
                # vector applies to any HTML mail client.
                patron_name = html.escape(hold.user.full_name) if hold.user else "Unknown"
                item_title = html.escape(hold.item.title) if hold.item else "Unknown"
                slot = html.escape(hold.shelf_slot) if hold.shelf_slot else "Unassigned"
                on_way = " (ON WAY)" if hold.patron_on_way else ""

                items_html += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{slot}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{item_title}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{patron_name}{on_way}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">
                        {hold.expires_at.strftime('%I:%M %p') if hold.expires_at else 'N/A'}
                    </td>
                </tr>
                """

            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
                <h2 style="color: {COLORS['heading']};">Daily Holds Expiring Report</h2>
                <p><strong>{len(holds)} hold(s)</strong> expire today and need attention.</p>
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <thead>
                        <tr style="background-color: #5C4F3D; color: white;">
                            <th style="padding: 8px; text-align: left;">Shelf Slot</th>
                            <th style="padding: 8px; text-align: left;">Title</th>
                            <th style="padding: 8px; text-align: left;">Patron</th>
                            <th style="padding: 8px; text-align: left;">Expires</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
                <p style="color: {COLORS['text_light']}; font-size: 12px;">
                    {settings.app_name} - Automated Hold Shelf Report
                </p>
            </div>
            """

            # Send to configured alert email or fallback to from_email
            alert_email = settings.job_alert_email or settings.from_email
            if alert_email:
                await send_email(
                    alert_email,
                    f"Holds Expiring Today: {len(holds)} items",
                    html_content,
                )

        logger.info(
            "Daily expiring holds report sent",
            extra={"holds_count": len(holds)},
        )
    except Exception as e:
        logger.error(f"Error generating expiring holds report: {e}", exc_info=True)
        raise


