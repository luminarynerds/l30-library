# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..core.config import get_settings
from ..core.database import AsyncSessionLocal
from ..core.email import send_email, COLORS, get_can_spam_footer
from ..core.frontend_routes import routes
from ..core.logging import get_logger
from ..models.catalog import CatalogItem
from ..models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ..models.notification import NotificationHistory, NotificationType
from ..models.user import User
from .notifications.preference_gate import should_send_email

settings = get_settings()
logger = get_logger(__name__)


def _get_overdue_fine_per_day() -> Decimal:
    return Decimal(settings.overdue_fine_per_day)


async def _was_recently_notified(
    db: AsyncSession,
    user_id: int,
    notification_type: NotificationType,
    hours: int = 24,
) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = select(NotificationHistory.id).where(
        and_(
            NotificationHistory.user_id == user_id,
            NotificationHistory.notification_type == notification_type,
            NotificationHistory.sent_at >= cutoff,
            NotificationHistory.success == True,
        )
    ).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _record_notification(
    db: AsyncSession,
    user_id: int,
    notification_type: NotificationType,
    email: str,
    subject: str,
    success: bool,
) -> None:
    record = NotificationHistory(
        user_id=user_id,
        notification_type=notification_type,
        recipient_email=email,
        subject=subject,
        context_data={"source": "patron_notification_sweep"},
        sent_at=datetime.now(timezone.utc),
        success=success,
    )
    db.add(record)


# ---------------------------------------------------------------------------
# Hold Available Sweep
# ---------------------------------------------------------------------------

async def _sweep_hold_available(db: AsyncSession) -> int:
    stmt = (
        select(Hold)
        .options(
            joinedload(Hold.user),
            joinedload(Hold.item),
            joinedload(Hold.pickup_location),
        )
        .where(
            and_(
                Hold.status == HoldStatus.ready,
                Hold.notified_at.is_(None),
            )
        )
        .limit(200)
    )
    result = await db.execute(stmt)
    holds = result.unique().scalars().all()

    sent = 0
    for hold in holds:
        user = hold.user
        item = hold.item
        if not user or not user.email or not item:
            continue

        # hold_ready is a REQUIRED type: the gate always allows it. Routed
        # through the gate anyway so all sweep sends share one decision path.
        if not await should_send_email(user.id, "hold_ready", db):
            continue

        pickup = hold.pickup_location.name if hold.pickup_location else None
        expires_str = (
            hold.expires_at.strftime("%B %d, %Y") if hold.expires_at else "7 days"
        )

        subject = f"Your hold is ready: {item.title}"
        html = _build_hold_ready_email(user, item, pickup, expires_str)

        try:
            success = await send_email(
                user.email,
                subject,
                html,
                patron_id=user.id,
                notification_type="hold_ready",
            )
            if success:
                hold.notified_at = datetime.now(timezone.utc)
                sent += 1
                await _record_notification(
                    db, user.id, NotificationType.HOLD_READY,
                    user.email, subject, True,
                )
        except Exception as e:  # noqa: BLE001 — per-iteration boundary: one patron's send failure must not crash sweep loop
            logger.error(
                "Failed to send hold-ready sweep email",
                extra={"hold_id": hold.id, "user_id": user.id, "error": str(e)},
            )

    return sent


def _build_hold_ready_email(
    user: User, item: CatalogItem, pickup: str | None, expires_str: str
) -> str:
    holds_url = routes.url(settings.frontend_url, routes.account_holds_alt)
    author_line = (
        f'<br><span style="color: {COLORS["body"]};">by {item.author}</span>'
        if item.author else ""
    )
    pickup_line = (
        f'<p><strong>Pickup location:</strong> {pickup}</p>' if pickup else ""
    )

    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Your Hold is Ready!</h2>
        <p>Hi {user.first_name},</p>
        <p>The item you placed on hold is now available for pickup.</p>
        <div style="background-color: {COLORS['border']}; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <strong style="color: {COLORS['heading']};">{item.title}</strong>
            {author_line}
        </div>
        {pickup_line}
        <p>Please pick up your item by <strong>{expires_str}</strong>
           or your hold will expire.</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{holds_url}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                View My Holds
            </a>
        </p>
        {get_can_spam_footer(is_transactional=True)}
    </div>
    """


# ---------------------------------------------------------------------------
# Courtesy Reminder (3 days before due)
# ---------------------------------------------------------------------------

async def _sweep_courtesy_reminders(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    target_date = now + timedelta(days=3)
    day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    stmt = (
        select(Checkout)
        .options(
            joinedload(Checkout.user),
            joinedload(Checkout.item),
        )
        .where(
            and_(
                Checkout.status == CheckoutStatus.active,
                Checkout.returned_at.is_(None),
                Checkout.due_date >= day_start,
                Checkout.due_date < day_end,
            )
        )
        .limit(1000)
    )
    result = await db.execute(stmt)
    checkouts = result.scalars().all()

    # Group by user
    user_checkouts: dict[int, list[Checkout]] = {}
    for co in checkouts:
        if not co.user or not co.user.email:
            continue
        user_checkouts.setdefault(co.user_id, []).append(co)

    sent = 0
    for user_id, cos in user_checkouts.items():
        user = cos[0].user

        # Dedup: check if we already sent a due-date reminder for this user
        # today. Done before the gate so a digest-mode patron is not enqueued
        # twice for the same day.
        already = await _was_recently_notified(
            db, user_id, NotificationType.DUE_DATE_REMINDER, hours=20,
        )
        if already:
            continue

        item_count = len(cos)
        plural = "s" if item_count > 1 else ""
        subject = f"Friendly reminder: {item_count} item{plural} due in 3 days"

        # due_date_reminder is non-required: honor the patron's email toggle,
        # Quiet Hours, and Digest Mode. For digest-mode patrons the gate
        # enqueues this summary line instead of sending now; the date-keyed
        # dedup_key collapses repeat sweep runs within the same day.
        if not await should_send_email(
            user_id,
            "due_date_reminder",
            db,
            summary=f"{item_count} item{plural} due in 3 days",
            context_data={"item_count": item_count},
            dedup_key=f"courtesy:{datetime.now(timezone.utc).date().isoformat()}",
        ):
            continue

        html = _build_courtesy_email(user, cos)

        try:
            success = await send_email(
                user.email,
                subject,
                html,
                patron_id=user.id,
                notification_type="due_date_reminder",
            )
            if success:
                sent += 1
                await _record_notification(
                    db, user_id, NotificationType.DUE_DATE_REMINDER,
                    user.email, subject, True,
                )
                await _record_due_date_reminder_in_app(db, user_id, cos)
        except Exception as e:  # noqa: BLE001 — per-iteration boundary: one patron's send failure must not crash sweep loop
            logger.error(
                "Failed to send courtesy reminder",
                extra={"user_id": user_id, "error": str(e)},
            )

    return sent


async def _record_due_date_reminder_in_app(
    db: AsyncSession, user_id: int, checkouts: list[Checkout]
) -> None:
    try:
        from ..models.notification import PatronNotificationCategory
        from .patron_notification_service import record_in_app_notification

        count = len(checkouts)
        first = checkouts[0]
        title = first.item.title if first.item else "a library item"
        due_str = first.due_date.strftime("%B %d, %Y")
        if count > 1:
            message = f"{count} items are due on {due_str}, including \"{title}\"."
        else:
            message = f'"{title}" is due on {due_str}. Renew it online if no one is waiting.'

        await record_in_app_notification(
            db,
            patron_id=user_id,
            category=PatronNotificationCategory.DUE_DATE_REMINDER,
            title=f"{count} item{'s' if count > 1 else ''} due soon",
            message=message,
            source_event_type="DueDateReminder",
            source_event_id=f"due_date_reminder:{user_id}:{first.due_date.date().isoformat()}",
            related_loan_id=str(first.id),
            related_item_title=first.item.title if first.item else None,
            action_url=routes.account_checkouts,
            action_label="View checkouts",
        )
    except Exception as e:  # noqa: BLE001 — per-item boundary: in-app reminder is best-effort, must not crash email sweep
        logger.error(
            "Failed to stage in-app due-date reminder",
            extra={"user_id": user_id, "error": str(e)},
        )


def _build_courtesy_email(user: User, checkouts: list[Checkout]) -> str:
    checkouts_url = routes.url(settings.frontend_url, routes.account_checkouts_alt)
    items_html = ""
    for co in checkouts:
        title = co.item.title if co.item else "Library item"
        due_str = co.due_date.strftime("%B %d, %Y")
        items_html += f"<li><strong>{title}</strong> -- due {due_str}</li>"

    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Items Due Soon</h2>
        <p>Hi {user.first_name},</p>
        <p>This is a friendly reminder that the following items are due in 3 days:</p>
        <ul>{items_html}</ul>
        <p>You can renew items online if no one else has placed a hold on them.</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{checkouts_url}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Manage My Items
            </a>
        </p>
        {get_can_spam_footer(is_transactional=True)}
    </div>
    """


# ---------------------------------------------------------------------------
# Overdue Notice
# ---------------------------------------------------------------------------

async def _sweep_overdue_notices(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    fine_per_day = _get_overdue_fine_per_day()

    stmt = (
        select(Checkout)
        .options(
            joinedload(Checkout.user),
            joinedload(Checkout.item),
        )
        .where(
            and_(
                Checkout.status == CheckoutStatus.overdue,
                Checkout.returned_at.is_(None),
            )
        )
        .limit(1000)
    )
    result = await db.execute(stmt)
    checkouts = result.scalars().all()

    # Group by user
    user_checkouts: dict[int, list[Checkout]] = {}
    for co in checkouts:
        if not co.user or not co.user.email:
            continue
        user_checkouts.setdefault(co.user_id, []).append(co)

    sent = 0
    for user_id, cos in user_checkouts.items():
        user = cos[0].user

        # overdue_notice is a REQUIRED type: the gate always allows it. Routed
        # through the gate anyway so all sweep sends share one decision path.
        if not await should_send_email(user_id, "overdue_notice", db):
            continue

        # Dedup: skip if we already sent an overdue notice today
        already = await _was_recently_notified(
            db, user_id, NotificationType.OVERDUE_NOTICE, hours=20,
        )
        if already:
            continue

        subject = f"Overdue notice: {len(cos)} item{'s' if len(cos) > 1 else ''} past due"
        html = _build_overdue_email(user, cos, fine_per_day, now)

        try:
            success = await send_email(
                user.email,
                subject,
                html,
                patron_id=user.id,
                notification_type="overdue_notice",
            )
            if success:
                sent += 1
                await _record_notification(
                    db, user_id, NotificationType.OVERDUE_NOTICE,
                    user.email, subject, True,
                )
                await _record_overdue_notice_in_app(db, user_id, cos, fine_per_day, now)
        except Exception as e:  # noqa: BLE001 — per-iteration boundary: one patron's send failure must not crash sweep loop
            logger.error(
                "Failed to send overdue notice",
                extra={"user_id": user_id, "error": str(e)},
            )

    return sent


async def _record_overdue_notice_in_app(
    db: AsyncSession,
    user_id: int,
    checkouts: list[Checkout],
    fine_per_day: Decimal,
    now: datetime,
) -> None:
    try:
        from ..models.notification import PatronNotificationCategory
        from .patron_notification_service import record_in_app_notification

        count = len(checkouts)
        first = checkouts[0]
        title = first.item.title if first.item else "a library item"
        total_fine = Decimal("0.00")
        for co in checkouts:
            # SQLite returns naive datetimes; normalize before subtracting.
            due = co.due_date
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            days_overdue = max((now - due).days, 1)
            total_fine += fine_per_day * days_overdue
        if count > 1:
            message = (
                f"{count} items are overdue, including \"{title}\". "
                f"Accrued fines so far: ${total_fine:.2f}."
            )
        else:
            message = (
                f'"{title}" is overdue. Accrued fines so far: ${total_fine:.2f}. '
                "Please return it as soon as you can."
            )

        await record_in_app_notification(
            db,
            patron_id=user_id,
            category=PatronNotificationCategory.OVERDUE_NOTICE,
            title=f"{count} overdue item{'s' if count > 1 else ''}",
            message=message,
            source_event_type="OverdueNotice",
            source_event_id=f"overdue_notice:{user_id}:{now.date().isoformat()}",
            related_loan_id=str(first.id),
            related_item_title=first.item.title if first.item else None,
            action_url=routes.account_checkouts,
            action_label="View checkouts",
        )
    except Exception as e:  # noqa: BLE001 — per-item boundary: in-app reminder is best-effort, must not crash email sweep
        logger.error(
            "Failed to stage in-app overdue notice",
            extra={"user_id": user_id, "error": str(e)},
        )


def _build_overdue_email(
    user: User, checkouts: list[Checkout], fine_per_day: Decimal, now: datetime
) -> str:
    checkouts_url = routes.url(settings.frontend_url, routes.account_checkouts_alt)
    total_fine = Decimal("0.00")
    rows = ""

    for co in checkouts:
        title = co.item.title if co.item else "Library item"
        author = (co.item.author or "") if co.item else ""
        days_overdue = max((now - co.due_date).days, 1)
        item_fine = fine_per_day * days_overdue
        total_fine += item_fine
        due_str = co.due_date.strftime("%B %d, %Y")

        rows += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid {COLORS['divider']};">
                <strong>{title}</strong>
                {f'<br><span style="color: {COLORS["body"]};">{author}</span>' if author else ''}
            </td>
            <td style="padding: 10px; border-bottom: 1px solid {COLORS['divider']}; text-align: center;">
                {due_str}
            </td>
            <td style="padding: 10px; border-bottom: 1px solid {COLORS['divider']}; text-align: right;">
                ${item_fine:.2f}
            </td>
        </tr>
        """

    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Overdue Notice</h2>
        <p>Hi {user.first_name},</p>
        <p>You have <strong>{len(checkouts)} overdue item{'s' if len(checkouts) > 1 else ''}</strong>
           from {settings.app_name}. Please return them as soon as possible to avoid additional fines.</p>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background-color: {COLORS['border']};">
                    <th style="padding: 10px; text-align: left;">Item</th>
                    <th style="padding: 10px; text-align: center;">Due Date</th>
                    <th style="padding: 10px; text-align: right;">Fine</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
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
        <p style="text-align: center; margin: 30px 0;">
            <a href="{checkouts_url}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Manage My Items
            </a>
        </p>
        {get_can_spam_footer(is_transactional=True)}
    </div>
    """


# ---------------------------------------------------------------------------
# Main entry point (called by scheduler)
# ---------------------------------------------------------------------------

async def send_patron_notifications() -> None:
    logger.info("Starting patron notification sweep")

    async with AsyncSessionLocal() as db:
        try:
            holds_sent = await _sweep_hold_available(db)
            courtesy_sent = await _sweep_courtesy_reminders(db)
            overdue_sent = await _sweep_overdue_notices(db)

            await db.commit()

            logger.info(
                "Patron notification sweep completed",
                extra={
                    "holds_notified": holds_sent,
                    "courtesy_reminders": courtesy_sent,
                    "overdue_notices": overdue_sent,
                },
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Patron notification sweep failed: {e}", exc_info=True)
            raise
