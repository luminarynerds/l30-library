# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Notification API endpoints for patron notification preferences and live notifications.
"""
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.notification import Notification, NotificationType
from ...models.user import User
from ...services.patron_notification_service import patron_notification_service
from .auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])
logger = get_logger(__name__)

# NOTE: GET/PUT /notifications/preferences are intentionally NOT defined here.
# This router and api/v1/notification_preferences.py both mount on the
# /notifications prefix; FastAPI is first-match-wins and notification_preferences
# is registered first (registry.py ~line 481, before this router at ~1140), so
# any /preferences route defined here would be dead code. Preference endpoints
# live solely in notification_preferences.py against the canonical
# UserNotificationPreference model. Do not re-add them here.


# ───────────────────────────────────────────────────────────
# Patron Live Notifications (in-app feed)
# ───────────────────────────────────────────────────────────


def _serialize_notification(notification) -> dict:
    category = str(notification.category) if notification.category else None
    # Strip enum prefix if str(enum) returns "EnumName.VALUE"
    if category and "." in category:
        category = category.split(".", 1)[1].lower()
    return {
        "id": notification.id,
        "type": category,
        "category": category,
        "title": notification.title,
        "message": notification.message,
        "source_event_type": notification.source_event_type,
        "related_loan_id": notification.related_loan_id,
        "related_hold_id": notification.related_hold_id,
        "related_fine_id": notification.related_fine_id,
        "related_item_title": notification.related_item_title,
        "is_read": notification.is_read,
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
        "action_url": notification.action_url,
        "action_label": notification.action_label,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


def _serialize_panic_alert(notification: Notification) -> dict:
    ctx = notification.context_data or {}
    return {
        "id": f"pa-{notification.id}",
        "type": "panic_alert",
        "category": "panic_alert",
        "title": notification.subject or "Panic alert",
        "message": notification.message or "",
        "source_event_type": "PanicAlert",
        "related_loan_id": None,
        "related_hold_id": None,
        "related_fine_id": None,
        "related_item_title": None,
        "is_read": notification.read_at is not None,
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
        "action_url": ctx.get("alert_url") if isinstance(ctx, dict) else None,
        "action_label": "View alert",
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


async def _fetch_panic_alert_notifications(
    user_id: int,
    db: AsyncSession,
    unread_only: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[Notification]:
    conditions = [
        Notification.user_id == user_id,
        Notification.notification_type == NotificationType.PANIC_ALERT,
    ]
    if unread_only:
        conditions.append(Notification.read_at.is_(None))

    result = await db.execute(
        select(Notification)
        .where(and_(*conditions))
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def _count_panic_alerts(
    user_id: int,
    db: AsyncSession,
    unread_only: bool = False,
) -> int:
    conditions = [
        Notification.user_id == user_id,
        Notification.notification_type == NotificationType.PANIC_ALERT,
    ]
    if unread_only:
        conditions.append(Notification.read_at.is_(None))
    result = await db.execute(
        select(func.count(Notification.id)).where(and_(*conditions))
    )
    return result.scalar() or 0


def _parse_panic_alert_id(notification_id: str) -> Optional[int]:
    if not isinstance(notification_id, str) or not notification_id.startswith("pa-"):
        return None
    try:
        return int(notification_id[3:])
    except ValueError:
        return None


@router.get("/live")
async def get_live_notifications(
    unread_only: bool = Query(False, description="Only return unread notifications"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get patron's live notification feed.

    Returns in-app notifications generated from domain events such as
    hold available, due date reminders, overdue notices, and fines.
    Also includes high-priority panic alerts dispatched to staff.
    """
    # Panic-alert-only filter: simple paginated query
    if category == "panic_alert":
        panic_total = await _count_panic_alerts(
            user_id=current_user.id, db=db, unread_only=unread_only
        )
        panic_alerts = await _fetch_panic_alert_notifications(
            user_id=current_user.id, db=db, unread_only=unread_only,
            limit=limit, offset=offset,
        )
        return {
            "items": [_serialize_panic_alert(n) for n in panic_alerts],
            "total": panic_total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < panic_total,
        }

    # Mixed feed: get totals from both sources, then fetch only what the
    # current page needs so pagination works correctly across the merge.
    panic_total = await _count_panic_alerts(
        user_id=current_user.id, db=db, unread_only=unread_only,
    ) if category is None else 0

    patron_items: list[dict] = []
    patron_total = 0
    if category != "panic_alert":
        patron_offset = max(0, offset - panic_total)
        notifications, patron_total = await patron_notification_service.get_notifications(
            patron_id=current_user.id,
            db=db,
            unread_only=unread_only,
            category=category,
            limit=limit,
            offset=patron_offset,
        )
        patron_items = [_serialize_notification(n) for n in notifications]

    total = patron_total + panic_total

    # Panic alerts come first in the feed. If offset falls within the panic
    # range, fetch the slice we need; otherwise skip them entirely.
    panic_items: list[dict] = []
    if panic_total > 0 and offset < panic_total:
        panic_slice = await _fetch_panic_alert_notifications(
            user_id=current_user.id, db=db, unread_only=unread_only,
            limit=min(limit, panic_total - offset), offset=offset,
        )
        panic_items = [_serialize_panic_alert(n) for n in panic_slice]

    # Fill remaining page slots with patron items
    remaining = limit - len(panic_items)
    merged = panic_items + patron_items[:remaining]

    return {
        "items": merged,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
    }


@router.get("/live/unread-count")
async def get_unread_notification_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the count of unread notifications for the UI badge."""
    patron_count = await patron_notification_service.get_unread_count(
        patron_id=current_user.id, db=db
    )
    panic_count_result = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.notification_type == NotificationType.PANIC_ALERT,
                Notification.read_at.is_(None),
            )
        )
    )
    panic_count = panic_count_result.scalar() or 0
    return {"unread_count": patron_count + panic_count}


@router.post("/live/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read.

    Accepts either a numeric PatronNotification id or a 'pa-<n>'
    panic-alert id.
    """
    panic_id = _parse_panic_alert_id(notification_id)
    if panic_id is not None:
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == panic_id,
                    Notification.user_id == current_user.id,
                    Notification.notification_type == NotificationType.PANIC_ALERT,
                )
            )
        )
        notif = result.scalar_one_or_none()
        if notif is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )
        if notif.read_at is None:
            notif.read_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(notif)
        return _serialize_panic_alert(notif)

    try:
        numeric_id = int(notification_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid notification id",
        ) from None

    notification = await patron_notification_service.mark_as_read(
        notification_id=numeric_id,
        patron_id=current_user.id,
        db=db,
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return _serialize_notification(notification)


@router.post("/live/read-all")
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read (patron + panic alerts)."""
    count = await patron_notification_service.mark_all_as_read(
        patron_id=current_user.id, db=db
    )
    panic_result = await db.execute(
        update(Notification)
        .where(
            and_(
                Notification.user_id == current_user.id,
                Notification.notification_type == NotificationType.PANIC_ALERT,
                Notification.read_at.is_(None),
            )
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"ok": True, "marked_read": count + (panic_result.rowcount or 0)}


@router.delete("/live/{notification_id}")
async def dismiss_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss a notification from the patron's feed.

    Panic alerts have no dismissed flag; we mark them read instead so they
    drop out of the unread badge but remain queryable in audit views.
    """
    panic_id = _parse_panic_alert_id(notification_id)
    if panic_id is not None:
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == panic_id,
                    Notification.user_id == current_user.id,
                    Notification.notification_type == NotificationType.PANIC_ALERT,
                )
            )
        )
        notif = result.scalar_one_or_none()
        if notif is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )
        if notif.read_at is None:
            notif.read_at = datetime.now(timezone.utc)
            await db.commit()
        return {"ok": True, "message": "Notification dismissed"}

    try:
        numeric_id = int(notification_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid notification id",
        ) from None

    notification = await patron_notification_service.dismiss_notification(
        notification_id=numeric_id,
        patron_id=current_user.id,
        db=db,
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return {"ok": True, "message": "Notification dismissed"}


# ============================================================================
# Dynamic Configuration Endpoints
# ============================================================================

from pydantic import BaseModel

class NotificationTemplate(BaseModel):
    id: str
    name: str
    subject: str
    message: str
    notification_types: list[str]


@router.get("/templates", response_model=list[NotificationTemplate])
async def get_notification_templates(
    current_user: User = Depends(get_current_user),
):
    """Get all available notification templates for staff use.

    Returns a list of pre-configured notification templates that staff
    can use to send standardized messages to patrons.
    """
    templates = [
        NotificationTemplate(
            id="overdue_reminder",
            name="Overdue Reminder",
            subject="Your library items are overdue",
            message="Dear {patron_name}, your library items are overdue. Please return them to the library as soon as possible.",
            notification_types=["email", "sms"]
        ),
        NotificationTemplate(
            id="hold_ready",
            name="Hold Ready for Pickup",
            subject="Your hold is ready",
            message="Dear {patron_name}, your hold is ready for pickup at the circulation desk.",
            notification_types=["email", "sms"]
        ),
        NotificationTemplate(
            id="account_update",
            name="Account Update",
            subject="Your library account has been updated",
            message="Dear {patron_name}, your library account has been updated. Please log in to verify your information.",
            notification_types=["email"]
        ),
        NotificationTemplate(
            id="fine_notice",
            name="Fine Notice",
            subject="You have outstanding fines",
            message="Dear {patron_name}, you have outstanding fines on your library account. Please visit the library to pay them.",
            notification_types=["email", "sms"]
        ),
        NotificationTemplate(
            id="custom",
            name="Custom Message",
            subject="Message from the library",
            message="Enter your custom message here",
            notification_types=["email", "sms"]
        ),
    ]
    return templates
