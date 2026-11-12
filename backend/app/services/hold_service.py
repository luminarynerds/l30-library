# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

# From circulation_config - uses time_config
from ..core.circulation_config import HOLD_EXPIRY_DAYS
from ..models.catalog import CatalogItem, ItemStatus
from ..models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ..models.inventory import ItemCopy
from ..models.user import User
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)

# Title statuses derived from circulation state. Anything else (reference,
# lost, withdrawn, in_processing, ...) is set by other workflows and must
# never be overwritten by hold/checkout bookkeeping.
_CIRCULATING_STATUSES = (
    ItemStatus.available,
    ItemStatus.checked_out,
    ItemStatus.on_hold,
)


async def free_copy_count(item: CatalogItem, db: AsyncSession) -> int:
    """Copies neither on loan nor reserved by a ready hold.

    Each ready hold reserves one copy (it is captured on the hold shelf or
    owed to the next patron). Titles with no copy records (legacy items
    that were never inventoried) circulate as ONE virtual copy, so they
    are still loan-gated like the single physical thing they are.
    """
    total_copies = (await db.execute(
        select(func.count(ItemCopy.id)).where(ItemCopy.catalog_item_id == item.id)
    )).scalar() or 0
    circulating_copies = total_copies or 1
    active_loans = (await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.item_id == item.id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
    )).scalar() or 0
    ready_holds = (await db.execute(
        select(func.count(Hold.id)).where(
            Hold.item_id == item.id,
            Hold.status == HoldStatus.ready,
        )
    )).scalar() or 0
    return circulating_copies - active_loans - ready_holds


async def recompute_title_availability(item: CatalogItem | None, db: AsyncSession) -> None:
    """Derive the title-level status from copy, loan, and ready-hold counts.

    Replaces the scattered `item.status = on_hold/available` writes that
    assumed one copy per title: a multi-copy title stays `available` while
    any copy is free, regardless of loans or holds on the other copies.
    """
    if item is None or item.status not in _CIRCULATING_STATUSES:
        return

    total_copies = (await db.execute(
        select(func.count(ItemCopy.id)).where(ItemCopy.catalog_item_id == item.id)
    )).scalar() or 0
    # Titles with no copy records circulate as one virtual copy.
    circulating_copies = total_copies or 1
    ready_holds = (await db.execute(
        select(func.count(Hold.id)).where(
            Hold.item_id == item.id,
            Hold.status == HoldStatus.ready,
        )
    )).scalar() or 0
    active_loans = (await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.item_id == item.id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
    )).scalar() or 0

    if circulating_copies - active_loans - ready_holds > 0:
        item.status = ItemStatus.available
    elif ready_holds > 0:
        item.status = ItemStatus.on_hold
    else:
        item.status = ItemStatus.checked_out


async def ready_hold_if_copy_free(
    hold: Hold, user: User | None, item: CatalogItem, db: AsyncSession
) -> bool:
    """Capture a free copy for a just-placed hold (ready immediately).

    Returns True when the hold was readied.
    """
    if await free_copy_count(item, db) <= 0:
        return False

    hold.status = HoldStatus.ready
    hold.notified_at = utc_now()
    if user is not None:
        from ..core.authorization import get_user_role_settings

        settings = await get_user_role_settings(user, db)
        hold_expiry = settings.hold_duration_days if settings else HOLD_EXPIRY_DAYS
    else:
        hold_expiry = HOLD_EXPIRY_DAYS
    hold.expires_at = utc_now() + timedelta(days=hold_expiry)
    return True


async def _build_pending_notification(next_hold: Hold, db: AsyncSession):
    # Lazy import to avoid circular dependency at module load time.
    from .checkout_service import PendingHoldNotification

    user = await db.get(User, next_hold.user_id)
    if not user:
        return None
    item = await db.get(CatalogItem, next_hold.item_id)
    if not item:
        return None

    await record_hold_ready_in_app(next_hold, user, item, db)

    if not user.email:
        return None
    expires_at_formatted = (
        next_hold.expires_at.strftime("%B %d, %Y")
        if next_hold.expires_at
        else "7 days"
    )
    return PendingHoldNotification(
        to_email=user.email,
        first_name=user.first_name,
        book_title=item.title,
        book_author=item.author,
        pickup_location=item.location,
        expires_at=expires_at_formatted,
    )


async def record_hold_ready_in_app(
    hold: Hold, user: User, item: CatalogItem, db: AsyncSession
) -> None:
    try:
        from app.models.notification import PatronNotificationCategory
        from .patron_notification_service import record_in_app_notification
        from app.core.frontend_routes import routes

        title = item.title or "Your hold"
        await record_in_app_notification(
            db,
            patron_id=hold.user_id,
            category=PatronNotificationCategory.HOLD_AVAILABLE,
            title="Your hold is ready for pickup",
            message=f'"{title}" is ready. Please pick it up before it expires.',
            source_event_type="HoldReady",
            source_event_id=f"hold_ready:{hold.id}",
            related_hold_id=str(hold.id),
            related_item_title=item.title,
            action_url=routes.account_holds,
            action_label="View hold",
        )
    except Exception as e:  # noqa: BLE001 -- in-app notification staging must not block hold-ready commit
        logger.error(
            "Failed to stage in-app hold-ready notification",
            extra={"hold_id": hold.id, "user_id": hold.user_id, "error": str(e)},
        )

# Configuration constants (From circulation_config -> time_config.circulation)
# HOLD_EXPIRY_DAYS imported from circulation_config


def get_effective_expiration(hold: Hold) -> datetime | None:
    if hold.expires_at is not None:
        return hold.expires_at

    # Fallback: use notified_at + HOLD_EXPIRY_DAYS for ready holds with NULL expires_at
    if hold.notified_at is not None:
        return hold.notified_at + timedelta(days=HOLD_EXPIRY_DAYS)

    return None


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_hold_expired(hold: Hold, now: datetime | None = None) -> bool:
    if hold.status != HoldStatus.ready:
        return False

    current_time = now if now is not None else utc_now()

    effective_expiration = get_effective_expiration(hold)
    if effective_expiration is None:
        return False

    return _ensure_utc(effective_expiration) < _ensure_utc(current_time)


async def check_and_expire_hold_collecting_notifications(
    hold: Hold, db: AsyncSession
):
    now = datetime.now(timezone.utc)

    # Use is_hold_expired to handle NULL expires_at with notified_at fallback
    if not is_hold_expired(hold, now):
        return False, None

    # Process this expired hold
    hold.status = HoldStatus.expired

    # Get the item with lock to prevent concurrent status changes
    item_result = await db.execute(
        select(CatalogItem)
        .where(CatalogItem.id == hold.item_id)
        .with_for_update()
    )
    item = item_result.scalar_one_or_none()

    # Bulk update positions for remaining holds
    # PostgreSQL acquires row-level locks during UPDATE, providing
    # equivalent concurrency safety to SELECT FOR UPDATE + individual decrements
    await db.execute(
        update(Hold)
        .where(
            Hold.item_id == hold.item_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
            Hold.position > hold.position,
        )
        .values(position=Hold.position - 1)
    )

    # Advance next hold in queue with lock to prevent duplicate promotions
    next_hold_result = await db.execute(
        select(Hold)
        .where(Hold.item_id == hold.item_id, Hold.status == HoldStatus.pending)
        .order_by(Hold.position)
        .with_for_update()
    )
    next_hold = next_hold_result.scalar_one_or_none()

    notification = None
    if next_hold:
        next_hold.status = HoldStatus.ready
        next_hold.notified_at = now
        next_hold.expires_at = now + timedelta(days=HOLD_EXPIRY_DAYS)
        notification = await _build_pending_notification(next_hold, db)
    await recompute_title_availability(item, db)

    return True, notification


async def check_and_expire_hold(hold: Hold, db: AsyncSession) -> bool:
    expired, _ = await check_and_expire_hold_collecting_notifications(hold, db)
    return expired


async def process_expired_holds_collecting_notifications(
    db: AsyncSession, item_id: int | None = None
):
    now = utc_now()
    notified_at_expiry_threshold = now - timedelta(days=HOLD_EXPIRY_DAYS)

    # Find expired ready holds
    # Use skip_locked to prevent duplicate processing by concurrent workers
    # Include holds where:
    #   1. expires_at is set and has passed, OR
    #   2. expires_at is NULL but notified_at + HOLD_EXPIRY_DAYS has passed
    #      (handles legacy data with missing expires_at)
    query = (
        select(Hold)
        .where(
            Hold.status == HoldStatus.ready,
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
        .with_for_update(skip_locked=True)
    )
    if item_id:
        query = query.where(Hold.item_id == item_id)

    result = await db.execute(query)
    expired_holds = result.scalars().all()

    processed_count = 0
    notifications = []
    for expired_hold in expired_holds:
        expired_hold.status = HoldStatus.expired

        # Reposition remaining holds for this item with lock
        remaining_result = await db.execute(
            select(Hold)
            .where(
                Hold.item_id == expired_hold.item_id,
                Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
                Hold.position > expired_hold.position,
            )
            .order_by(Hold.position)
            .with_for_update()
        )
        for remaining_hold in remaining_result.scalars().all():
            remaining_hold.position -= 1

        # Promote next pending hold to ready with lock
        next_hold_result = await db.execute(
            select(Hold)
            .where(
                Hold.item_id == expired_hold.item_id,
                Hold.status == HoldStatus.pending,
            )
            .order_by(Hold.position)
            .limit(1)
            .with_for_update()
        )
        next_hold = next_hold_result.scalar_one_or_none()

        if next_hold:
            next_hold.status = HoldStatus.ready
            next_hold.notified_at = utc_now()
            hold_expiry_days = HOLD_EXPIRY_DAYS  # Could fetch user-specific expiry
            next_hold.expires_at = utc_now() + timedelta(days=hold_expiry_days)
            notification = await _build_pending_notification(next_hold, db)
            if notification is not None:
                notifications.append(notification)
        else:
            # No promotion happened: the expired reservation is released, so
            # rederive the title status (with lock).
            item_result = await db.execute(
                select(CatalogItem)
                .where(CatalogItem.id == expired_hold.item_id)
                .with_for_update()
            )
            item = item_result.scalar_one_or_none()
            await recompute_title_availability(item, db)

        processed_count += 1

    return processed_count, notifications


async def process_expired_holds(db: AsyncSession, item_id: int | None = None) -> int:
    count, _ = await process_expired_holds_collecting_notifications(db, item_id=item_id)
    return count


async def promote_next_hold_collecting_notification(
    item_id: int, db: AsyncSession, hold_expiry_days: int = HOLD_EXPIRY_DAYS
):
    # Lock next pending hold
    next_hold_result = await db.execute(
        select(Hold)
        .where(Hold.item_id == item_id, Hold.status == HoldStatus.pending)
        .order_by(Hold.position)
        .with_for_update()
    )
    next_hold = next_hold_result.scalar_one_or_none()

    item_result = await db.execute(
        select(CatalogItem)
        .where(CatalogItem.id == item_id)
        .with_for_update()
    )
    item = item_result.scalar_one_or_none()

    if next_hold:
        next_hold.status = HoldStatus.ready
        next_hold.notified_at = utc_now()
        next_hold.expires_at = utc_now() + timedelta(days=hold_expiry_days)
        notification = await _build_pending_notification(next_hold, db)
        await recompute_title_availability(item, db)
        return True, notification

    # No more holds: rederive status from loans/copies instead of blindly
    # marking available (other copies may still be out).
    await recompute_title_availability(item, db)

    return False, None


async def promote_next_hold(
    item_id: int, db: AsyncSession, hold_expiry_days: int = HOLD_EXPIRY_DAYS
) -> bool:
    promoted, _ = await promote_next_hold_collecting_notification(
        item_id, db, hold_expiry_days=hold_expiry_days
    )
    return promoted


async def get_next_hold_position(item_id: int, db: AsyncSession) -> int:
    # Advisory lock serializes concurrent hold placement for the same item
    await db.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": item_id})

    existing_holds_result = await db.execute(
        select(func.coalesce(func.max(Hold.position), 0))
        .where(
            Hold.item_id == item_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
    )
    max_position = existing_holds_result.scalar() or 0
    return max_position + 1


async def fix_null_expires_at_holds(db: AsyncSession) -> int:
    now = utc_now()

    # Find ready holds with NULL expires_at
    result = await db.execute(
        select(Hold)
        .where(
            Hold.status == HoldStatus.ready,
            Hold.expires_at.is_(None),
        )
        .with_for_update()
    )
    null_expires_holds = result.scalars().all()

    fixed_count = 0
    for hold in null_expires_holds:
        if hold.notified_at is not None:
            # Use notified_at as the base for expiration
            hold.expires_at = hold.notified_at + timedelta(days=HOLD_EXPIRY_DAYS)
        else:
            # Fallback: if notified_at is also NULL, set both to current time
            # This shouldn't happen in normal operation but handles edge cases
            hold.notified_at = now
            hold.expires_at = now + timedelta(days=HOLD_EXPIRY_DAYS)
            logger.warning(
                f"Hold {hold.id} had NULL notified_at and expires_at, "
                f"setting both to current time"
            )
        fixed_count += 1

    if fixed_count > 0:
        logger.info(f"Fixed {fixed_count} holds with NULL expires_at")

    return fixed_count
