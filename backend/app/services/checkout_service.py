# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Circulation core: checkout, checkin, renewal.

Single source of truth for circulation semantics. The staff-desk entry
points in unified_circulation_service are thin adapters over this module.
"""

from app.core.logging import get_logger
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

# From circulation_config - uses time_config
from ..core.circulation_config import LOAN_PERIOD_DAYS
from ..models.catalog import CatalogItem, ItemStatus
from ..models.inventory import ItemCopy
from ..models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ..models.lifecycle import LifecycleEventType
from ..models.user import User
from ..core.authorization import (
    check_card_expiration,
    check_fine_block,
    get_checkout_limit,
    get_max_renewals,
    get_user_role_settings,
)
from .hold_service import process_expired_holds, recompute_title_availability
from .circulation_policy import get_loan_period_days
from .fine_service import check_and_create_overdue_fine
from .collection_alert_service import check_checkout_alerts
from .checkout_problem_resolution import CheckoutProblemResolver, problem_details_to_dict
from . import operations_audit_service as ops_audit
from ..core.exceptions import (
    BusinessLogicError,
    ConflictError,
    ForbiddenError,
    ResourceNotFoundError,
)
from ..core.error_codes import ErrorCode
from ..core.cache import get_redis, invalidate_catalog_cache, _acquire_lock, _release_lock
from app.core.datetime_utils import utc_now
from app.services.reports.cache_invalidator import invalidate_circulation_reports

logger = get_logger(__name__)

# Distributed lock timeout for item copy checkout (seconds)
_CHECKOUT_LOCK_TIMEOUT = 10


@dataclass
class PendingHoldNotification:

    to_email: str
    first_name: str
    book_title: str
    book_author: Optional[str]
    pickup_location: Optional[str]
    expires_at: str


@dataclass
class BumpedHoldNotification:

    to_email: str
    first_name: str
    book_title: str
    book_author: Optional[str]
    disposition: str  # "bump_to_front" | "cancel"


@dataclass
class ReturnResult:

    item: Optional[CatalogItem]
    pending_notification: Optional[PendingHoldNotification] = None
    promoted_hold: Optional[Hold] = None


@dataclass
class CheckoutResult:

    checkout: "Checkout"
    item: Optional[CatalogItem] = None
    _redis_client: Optional[object] = None
    _lock_key: Optional[str] = None
    _lock_token: Optional[str] = None

    async def release_lock(self) -> None:
        if self._redis_client and self._lock_key and self._lock_token:
            try:
                await _release_lock(self._redis_client, self._lock_key, self._lock_token)
            except Exception:  # noqa: BLE001 - cleanup boundary — lock release failure must not mask checkout result
                logger.warning(
                    "Failed to release checkout lock for key=%s", self._lock_key
                )


async def send_pending_hold_notification(
    notification: Optional[PendingHoldNotification],
) -> None:
    if notification is None:
        return
    try:
        from ..core.email import send_hold_ready_notification

        await send_hold_ready_notification(
            to_email=notification.to_email,
            first_name=notification.first_name,
            book_title=notification.book_title,
            book_author=notification.book_author,
            pickup_location=notification.pickup_location,
            expires_at=notification.expires_at,
        )
    except Exception as e:  # noqa: BLE001 - notification boundary — email failure must not crash checkout flow
        logger.error("Failed to send hold notification: %s", e)


async def send_bumped_hold_notification(notification: BumpedHoldNotification) -> None:
    from ..core.email import (
        send_hold_bumped_to_front_notification,
        send_hold_released_notification,
    )
    try:
        if notification.disposition == "bump_to_front":
            await send_hold_bumped_to_front_notification(
                notification.to_email, notification.first_name,
                notification.book_title, notification.book_author,
            )
        else:
            await send_hold_released_notification(
                notification.to_email, notification.first_name,
                notification.book_title, notification.book_author,
            )
    except Exception:  # noqa: BLE001 - notification boundary — email failure must not crash checkout flow
        logger.exception("Failed to send bumped-hold notification")

# Configuration constants (From circulation_config -> time_config.circulation)
# LOAN_PERIOD_DAYS imported from circulation_config


async def get_user_loan_period(user: User, db: AsyncSession) -> int:
    settings = await get_user_role_settings(user, db)
    return settings.checkout_duration_days if settings else LOAN_PERIOD_DAYS


async def check_patron_eligibility(
    patron: User,
    db: AsyncSession,
    *,
    is_staff_operation: bool = False,
    operation: str = "checkout",
) -> None:
    """Patron-status gate shared by checkout and renewal.

    Staff may override a suspension (desk judgment call) but never a
    deceased or blocked account. Card-expiry and fine/accountability
    blocks are waived for staff-driven operations.
    """
    from .suspension_service import check_patron_suspension_status

    can_circulate, reason, error_code = await check_patron_suspension_status(patron, db)
    if not can_circulate:
        if is_staff_operation and error_code == ErrorCode.PATRON_ACCOUNT_SUSPENDED:
            logger.info(
                "Staff override for suspended patron %s %s", patron.id, operation
            )
        else:
            raise ForbiddenError(
                code=error_code or ErrorCode.PATRON_BLOCKED,
                message=reason or "Patron account cannot perform circulation operations.",
            )

    if not patron.is_active:
        raise ForbiddenError(code=ErrorCode.PATRON_BLOCKED, message="Patron account is blocked")

    if is_staff_operation:
        return

    card_valid, days_remaining = await check_card_expiration(patron, db)
    if not card_valid:
        days_expired = abs(days_remaining) if days_remaining is not None else 0
        resolver = CheckoutProblemResolver(db)
        problem = await resolver.resolve_problem(
            ErrorCode.PATRON_CARD_EXPIRED,
            patron,
            context={"days_expired": days_expired},
        )
        raise ForbiddenError(
            code=ErrorCode.PATRON_CARD_EXPIRED,
            message=(
                f"Your library card has expired ({days_expired} days ago). "
                f"Please visit the circulation desk to renew your card."
            ),
            details=[{"problem": problem_details_to_dict(problem)}] if problem else None,
        )

    from .fine_service import FINE_FREE_MODE, OVERDUE_CHECKOUT_PAUSE_DAYS

    can_proceed, balance_or_count = await check_fine_block(patron, db)
    if not can_proceed:
        resolver = CheckoutProblemResolver(db)
        problem = await resolver.resolve_problem(
            ErrorCode.PATRON_HAS_OUTSTANDING_FINE,
            patron,
            context={
                "overdue_count": int(balance_or_count) if FINE_FREE_MODE else 0,
                "fine_balance": float(balance_or_count) if not FINE_FREE_MODE else 0,
            },
        )
        if FINE_FREE_MODE and balance_or_count > 0:
            # In fine-free mode, the "balance" is actually the count of long-overdue items
            count = int(balance_or_count)
            raise ForbiddenError(
                code=ErrorCode.PATRON_HAS_OUTSTANDING_FINE,
                message=(
                    f"You have {count} item(s) that have been overdue for more than "
                    f"{OVERDUE_CHECKOUT_PAUSE_DAYS} days. Please return them to resume "
                    f"checking out new items. We're happy to help if you need assistance!"
                ),
                details=[{"problem": problem_details_to_dict(problem)}] if problem else None,
            )
        raise ForbiddenError(
            code=ErrorCode.PATRON_HAS_OUTSTANDING_FINE,
            message=(
                f"Outstanding balance (${balance_or_count:.2f}) for lost or damaged "
                f"items. Please visit the circulation desk for assistance."
            ),
            details=[{"problem": problem_details_to_dict(problem)}] if problem else None,
        )


async def check_checkout_limit(user: User, db: AsyncSession) -> None:
    max_checkouts = await get_checkout_limit(user, db)

    # Lock the user's active checkouts to prevent race condition
    # where two concurrent checkouts could both pass the limit check
    result = await db.execute(
        select(Checkout.id)
        .where(
            Checkout.user_id == user.id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
        .with_for_update()
    )
    checkouts = result.scalars().all()
    current_count = len(checkouts)

    if current_count >= max_checkouts:
        resolver = CheckoutProblemResolver(db)
        problem = await resolver.resolve_problem(
            ErrorCode.QUOTA_EXCEEDED,
            user,
            context={"current_count": current_count, "max_checkouts": max_checkouts},
        )
        raise BusinessLogicError(
            code=ErrorCode.QUOTA_EXCEEDED,
            message=(
                f"You have reached your limit of {max_checkouts} borrowed items "
                f"({current_count}/{max_checkouts}). Return something before borrowing more."
            ),
            details=[{"problem": problem_details_to_dict(problem)}] if problem else None,
        )


async def _handle_held_copy_block(
    item: CatalogItem,
    patron: User,
    db: AsyncSession,
    *,
    is_staff_operation: bool,
    override_hold: bool,
    hold_disposition: Optional[str],
    staff_user: Optional[User],
    deferred_notifications: Optional[list],
) -> None:
    """Checkout is blocked because ready holds reserve the remaining copies.

    A ready hold belonging to another patron blocks checkout unless staff
    explicitly override it with a disposition (bump_to_front or cancel),
    which releases that reservation so the walk-in takes the copy.
    """
    other_hold_result = await db.execute(
        select(Hold)
        .where(
            Hold.item_id == item.id,
            Hold.status == HoldStatus.ready,
        )
        .order_by(Hold.position)
        .with_for_update()
    )
    other_hold = other_hold_result.scalars().first()

    if override_hold:
        if not is_staff_operation:
            raise ForbiddenError(
                code=ErrorCode.ITEM_ON_HOLD,
                message="Overriding a hold is a staff-only action.",
            )
        if hold_disposition not in ("bump_to_front", "cancel"):
            raise BusinessLogicError(
                code=ErrorCode.ITEM_ON_HOLD,
                message=(
                    "A hold disposition (bump_to_front or cancel) "
                    "is required to override a hold."
                ),
            )
        if other_hold is None:
            raise BusinessLogicError(
                code=ErrorCode.ITEM_ON_HOLD,
                message=(
                    "This item is marked on hold but has no active "
                    "hold to override. Ask a supervisor to check the "
                    "item's status."
                ),
            )

        bumped_user = await db.get(User, other_hold.user_id)
        bumped_title = item.title
        bumped_author = item.author

        if hold_disposition == "bump_to_front":
            # Keep the hold; send the patron to the front of
            # the queue as pending. The normal return flow
            # re-promotes them when the walk-in returns it.
            other_hold.status = HoldStatus.pending
            other_hold.notified_at = None
            other_hold.expires_at = None
            other_hold.shelf_slot = None
            other_hold.qr_pickup_code = None
        else:  # cancel
            other_hold.status = HoldStatus.cancelled
            other_hold.cancelled_at = utc_now()
            other_hold.cancelled_by = "staff"
            other_hold.cancellation_reason = (
                "Released by staff -- copy checked out in person."
            )
            remaining_result = await db.execute(
                select(Hold)
                .where(
                    Hold.item_id == item.id,
                    Hold.status.in_(
                        [HoldStatus.pending, HoldStatus.ready]
                    ),
                )
                .order_by(Hold.position)
                .with_for_update()
            )
            for idx, h in enumerate(
                remaining_result.scalars().all(), start=1
            ):
                h.position = idx

        await ops_audit.log_hold_overridden(
            db,
            staff=staff_user,
            bumped_patron=bumped_user,
            item=item,
            hold=other_hold,
            disposition=hold_disposition,
        )

        if (
            deferred_notifications is not None
            and bumped_user is not None
            and bumped_user.email
        ):
            deferred_notifications.append(
                BumpedHoldNotification(
                    to_email=bumped_user.email,
                    first_name=bumped_user.first_name,
                    book_title=bumped_title,
                    book_author=bumped_author,
                    disposition=hold_disposition,
                )
            )
        # Reservation released: checkout proceeds in create_checkout.
        return

    if is_staff_operation:
        resolver = CheckoutProblemResolver(db)
        problem = await resolver.resolve_problem(
            ErrorCode.ITEM_ON_HOLD, patron, item,
        )
        bumped_user = (
            await db.get(User, other_hold.user_id)
            if other_hold else None
        )
        queue_count = (await db.execute(
            select(func.count())
            .select_from(Hold)
            .where(
                Hold.item_id == item.id,
                Hold.status.in_(
                    [HoldStatus.pending, HoldStatus.ready]
                ),
            )
        )).scalar() or 0
        if bumped_user:
            _last = (bumped_user.last_name or "").strip()
            _suffix = f" {_last[0]}." if _last else ""
            held_patron_name = f"{bumped_user.first_name}{_suffix}"
        else:
            held_patron_name = "another patron"
        hold_override_block = {
            "hold_id": other_hold.id if other_hold else None,
            "held_patron_name": held_patron_name,
            "patron_on_way": bool(
                other_hold.patron_on_way if other_hold else False
            ),
            "queue_length": queue_count,
        }
        detail = {"hold_override": hold_override_block}
        if problem:
            detail["problem"] = problem_details_to_dict(problem)
        raise ConflictError(
            code=ErrorCode.ITEM_ON_HOLD,
            message="Item is on hold for another patron",
            details=[detail],
        )

    resolver = CheckoutProblemResolver(db)
    problem = await resolver.resolve_problem(
        ErrorCode.ITEM_ON_HOLD, patron, item,
    )
    raise ConflictError(
        code=ErrorCode.ITEM_ON_HOLD,
        message="Item is on hold for another patron",
        details=[{"problem": problem_details_to_dict(problem)}] if problem else None,
    )


async def create_checkout(
    user: User,
    item_id: int,
    db: AsyncSession,
    item_copy_id: Optional[int] = None,
    *,
    is_staff_operation: bool = False,
    override_hold: bool = False,
    hold_disposition: Optional[str] = None,
    staff_user: Optional[User] = None,
    deferred_notifications: Optional[list] = None,
) -> CheckoutResult:
    # Acquire distributed lock on item copy to prevent concurrent checkouts
    redis_client = None
    lock_key = None
    lock_token = None

    if item_copy_id is not None:
        redis_client = await get_redis()
        if redis_client is not None:
            lock_key = f"checkout:item_copy:{item_copy_id}"
            lock_token = await _acquire_lock(redis_client, lock_key, _CHECKOUT_LOCK_TIMEOUT)
            if lock_token is None:
                raise ConflictError(
                    code=ErrorCode.ITEM_CHECKED_OUT,
                    message="This item copy is currently being checked out by another request",
                )

    try:
        # Patron must be allowed to circulate (deceased/blocked/suspended,
        # card expiry, fines). Staff operations waive card/fine blocks and
        # may override a suspension.
        await check_patron_eligibility(
            user, db, is_staff_operation=is_staff_operation
        )

        # Check user checkout limit based on role settings
        await check_checkout_limit(user, db)

        # Use FOR UPDATE to lock the row and prevent race conditions
        result = await db.execute(
            select(CatalogItem)
            .where(CatalogItem.id == item_id)
            .with_for_update()
        )
        item = result.scalar_one_or_none()

        if not item:
            raise ResourceNotFoundError(
                code=ErrorCode.CATALOG_ITEM_NOT_FOUND,
                message="We could not find that item in our system.",
            )

        # Process any expired holds on this item first
        await process_expired_holds(db, item_id=item.id)

        if item.status not in (ItemStatus.available, ItemStatus.checked_out, ItemStatus.on_hold):
            # Hard non-circulating status (reference, lost, in_transit,
            # in_processing, withdrawn, ...) blocks unconditionally. The three
            # circulating statuses are NOT hard blocks: availability is decided
            # by the copy/loan/reservation counts below, not the title status.
            resolver = CheckoutProblemResolver(db)
            problem = await resolver.resolve_problem(
                ErrorCode.ITEM_NOT_AVAILABLE,
                user,
                item,
            )
            raise ConflictError(
                code=ErrorCode.ITEM_NOT_AVAILABLE,
                message=f"Item not available (status: {item.status})",
                details=[{"problem": problem_details_to_dict(problem)}] if problem else None,
            )

        # Fulfill the patron's own ready hold, if any: checking out the title
        # consumes their captured copy and releases its reservation, whatever
        # the title status currently says.
        own_hold_result = await db.execute(
            select(Hold).where(
                Hold.item_id == item.id,
                Hold.user_id == user.id,
                Hold.status == HoldStatus.ready,
            )
        )
        own_hold = own_hold_result.scalar_one_or_none()
        if own_hold is not None:
            own_hold.status = HoldStatus.fulfilled

        # Availability is per-COPY, not per-title: a multi-copy title can be out
        # to several patrons at once (one active loan per physical copy). Counting
        # active loans uses item_id (so legacy NULL-bound loans still count).
        active_statuses = [CheckoutStatus.active, CheckoutStatus.overdue]

        # A patron may not hold two copies of the same title.
        own_active = await db.execute(
            select(Checkout.id)
            .where(
                Checkout.item_id == item.id,
                Checkout.user_id == user.id,
                Checkout.status.in_(active_statuses),
            )
            .limit(1)
        )
        if own_active.first() is not None:
            raise ConflictError(
                code=ErrorCode.CHECKOUT_EXISTS,
                message="You already have this item checked out.",
            )

        # The specific physical copy must not already be out.
        if item_copy_id is not None:
            existing_copy = await db.execute(
                select(Checkout.id)
                .where(
                    Checkout.item_copy_id == item_copy_id,
                    Checkout.status.in_(active_statuses),
                )
                .with_for_update()
            )
            if existing_copy.first() is not None:
                raise ConflictError(
                    code=ErrorCode.ITEM_CHECKED_OUT,
                    message="This item copy is already checked out",
                )

        # Block when no copy is free. Each ready hold reserves one copy (it is
        # captured for the next patron), so free = copies - loans - reservations.
        # The patron's own ready hold was fulfilled above and no longer counts.
        # Titles with no copy records (legacy, never inventoried) circulate as
        # ONE virtual copy so they stay loan-gated.
        total_copies = (await db.execute(
            select(func.count(ItemCopy.id)).where(ItemCopy.catalog_item_id == item.id)
        )).scalar() or 0
        circulating_copies = total_copies or 1
        active_loans = (await db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.item_id == item.id,
                Checkout.status.in_(active_statuses),
            )
        )).scalar() or 0
        ready_holds = (await db.execute(
            select(func.count(Hold.id)).where(
                Hold.item_id == item.id,
                Hold.status == HoldStatus.ready,
            )
        )).scalar() or 0

        if active_loans >= circulating_copies:
            raise ConflictError(
                code=ErrorCode.ITEM_CHECKED_OUT,
                message="All copies are checked out",
            )
        if ready_holds > 0 and active_loans + ready_holds >= circulating_copies:
            # The remaining copies are reserved by other patrons' ready holds.
            # Staff may override one reservation for a walk-in; otherwise block.
            await _handle_held_copy_block(
                item,
                user,
                db,
                is_staff_operation=is_staff_operation,
                override_hold=override_hold,
                hold_disposition=hold_disposition,
                staff_user=staff_user,
                deferred_notifications=deferred_notifications,
            )

        # Resolve loan period via (collection x role x item_type x binding) policy matrix
        loan_period = await get_loan_period_days(user, item, db)
        due_date = utc_now() + timedelta(days=loan_period)

        checkout = Checkout(
            user_id=user.id,
            item_id=item.id,
            item_copy_id=item_copy_id,
            due_date=due_date,
            status=CheckoutStatus.active,
        )
        db.add(checkout)

        # Use atomic SQL increment to avoid lost updates on the counter
        await db.execute(
            update(CatalogItem)
            .where(CatalogItem.id == item.id)
            .values(total_checkouts=func.coalesce(CatalogItem.total_checkouts, 0) + 1)
        )

        await db.flush()

        # Rederive the title status now that the loan (and any fulfilled or
        # overridden hold) is flushed.
        await recompute_title_availability(item, db)

        # Audit: record the checkout for long-term forensic analysis
        await ops_audit.log_checkout_created(
            db, patron=user, item=item, checkout=checkout,
        )

        # Check for collection alerts after checkout is created
        await check_checkout_alerts(db, item.id, item.location)

        # Invalidate caches so reports and catalog views reflect this checkout
        await invalidate_circulation_reports()
        await invalidate_catalog_cache()

        return CheckoutResult(
            checkout=checkout,
            item=item,
            _redis_client=redis_client,
            _lock_key=lock_key,
            _lock_token=lock_token,
        )
    except Exception:
        # Release lock immediately on failure — no commit will happen
        if redis_client is not None and lock_key is not None and lock_token is not None:
            try:
                await _release_lock(redis_client, lock_key, lock_token)
            except Exception:  # noqa: BLE001 - cleanup boundary — lock release failure must not mask original checkout error
                logger.warning(
                    "Failed to release checkout lock for item_copy_id=%s",
                    item_copy_id,
                )
        raise


async def return_checkout(
    checkout: Checkout,
    db: AsyncSession,
    user: User,
    create_lifecycle_event_func=None,
    *,
    staff: Optional[User] = None,
) -> ReturnResult:
    # Lock the item to prevent concurrent status changes
    item_result = await db.execute(
        select(CatalogItem)
        .where(CatalogItem.id == checkout.item_id)
        .with_for_update()
    )
    item = item_result.scalar_one_or_none()

    # Check for overdue and create fine if needed
    await check_and_create_overdue_fine(checkout, db)

    was_overdue = checkout.status == CheckoutStatus.overdue
    checkout.status = CheckoutStatus.returned
    checkout.returned_at = utc_now()

    # Process any expired holds first
    await process_expired_holds(db, item_id=checkout.item_id)

    # Lock the hold record to prevent multiple concurrent returns from
    # promoting the same hold (race condition on hold promotion)
    hold_result = await db.execute(
        select(Hold)
        .where(Hold.item_id == checkout.item_id, Hold.status == HoldStatus.pending)
        .order_by(Hold.position)
        .with_for_update()
    )
    next_hold = hold_result.scalar_one_or_none()

    pending_notification: Optional[PendingHoldNotification] = None

    if next_hold:
        next_hold.status = HoldStatus.ready
        next_hold.notified_at = utc_now()
        # Get waiting patron's role settings for hold expiry (not the returning user's)
        waiting_patron_result = await db.execute(select(User).where(User.id == next_hold.user_id))
        waiting_patron = waiting_patron_result.scalar_one_or_none()
        waiting_settings = await get_user_role_settings(waiting_patron, db) if waiting_patron else None
        hold_expiry = waiting_settings.hold_duration_days if waiting_settings else 7
        next_hold.expires_at = utc_now() + timedelta(days=hold_expiry)

        # Stage the in-app feed row transactionally with the hold promotion.
        # Created even when the patron has no email on file.
        if waiting_patron:
            from .hold_service import record_hold_ready_in_app

            await record_hold_ready_in_app(next_hold, waiting_patron, item, db)

        # Collect notification info to send AFTER commit
        if waiting_patron and waiting_patron.email:
            expires_at_formatted = (
                next_hold.expires_at.strftime("%B %d, %Y")
                if next_hold.expires_at
                else "7 days"
            )
            pending_notification = PendingHoldNotification(
                to_email=waiting_patron.email,
                first_name=waiting_patron.first_name,
                book_title=item.title,
                book_author=item.author,
                pickup_location=item.location,
                expires_at=expires_at_formatted,
            )

    # Rederive the title status: the returned copy either went to the hold
    # shelf (promotion above reserves it) or back into circulation.
    await recompute_title_availability(item, db)

    # Audit: record the return for long-term forensic analysis.
    # `staff` is only set when staff drives the checkin (e.g. patron drops
    # an item at the desk); for patron self-return paths it stays None so
    # the row reads "patron returned themselves" not "staff handled it".
    await ops_audit.log_checkout_returned(
        db,
        patron=user,
        item=item,
        checkout=checkout,
        was_overdue=was_overdue,
        staff=staff,
    )

    # Log activity for the patron's reading shelf feed
    from .reading_activity_service import ReadingActivityService
    await ReadingActivityService.log_book_returned(
        db, user_id=user.id, catalog_item_id=item.id, title=item.title,
    )

    # Check if returning items should lift a suspension
    from .suspension_service import check_and_lift_on_return
    await check_and_lift_on_return(user.id, db)

    # Create lifecycle event if checkout has item_copy_id
    if checkout.item_copy_id and create_lifecycle_event_func:
        await create_lifecycle_event_func(
            db=db,
            item_copy_id=checkout.item_copy_id,
            event_type=LifecycleEventType.RETURNED,
            description="Returned by patron",
            metadata={
                "patron_id": user.id,
                "was_overdue": was_overdue,
            },
            performed_by_id=user.id,
            related_checkout_id=checkout.id,
        )

    # Invalidate caches so reports and catalog views reflect this return
    await invalidate_circulation_reports()
    await invalidate_catalog_cache()

    return ReturnResult(
        item=item,
        pending_notification=pending_notification,
        promoted_hold=next_hold,
    )


async def renew_checkout(
    checkout: Checkout,
    user: User,
    db: AsyncSession,
    create_lifecycle_event_func=None,
    *,
    is_staff_operation: bool = False,
    force: bool = False,
) -> None:
    if checkout.status not in [CheckoutStatus.active, CheckoutStatus.overdue]:
        raise ConflictError(
            code=ErrorCode.INVALID_STATE,
            message="This item cannot be renewed because it is not currently checked out.",
        )

    # Patron must be allowed to circulate (deceased/blocked/suspended,
    # card expiry, fines). Staff operations waive card/fine blocks.
    await check_patron_eligibility(
        user, db, is_staff_operation=is_staff_operation, operation="renewal"
    )

    # Check renewal limit based on role settings. A staff force-renew
    # (force=True) may push past the cap; the renewal is still recorded.
    max_renewals = await get_max_renewals(user, db)
    overrode_cap = False
    if checkout.renewal_count >= max_renewals:
        if not force:
            raise BusinessLogicError(
                code=ErrorCode.QUOTA_EXCEEDED,
                message=(
                    f"You have already renewed this item the maximum number of "
                    f"times ({max_renewals}). It needs to be returned."
                ),
            )
        overrode_cap = True
        logger.warning(
            "Staff force-renew past cap: checkout %s patron %s (%s/%s)",
            checkout.id, user.id, checkout.renewal_count, max_renewals,
        )

    # Lock holds to prevent race condition where a hold is placed between check and renewal
    holds_result = await db.execute(
        select(Hold)
        .where(
            Hold.item_id == checkout.item_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
        .with_for_update()
    )
    if holds_result.scalars().first() is not None:
        raise ConflictError(
            code=ErrorCode.ITEM_ON_HOLD,
            message=(
                "This item cannot be renewed because someone else is waiting "
                "for it. Please return it by your due date."
            ),
        )

    # Use policy-matrix loan period for renewals (per role x item_type x binding)
    item_for_policy = (await db.execute(
        select(CatalogItem).where(CatalogItem.id == checkout.item_id)
    )).scalar_one_or_none()
    if item_for_policy is None:
        loan_period = await get_user_loan_period(user, db)
    else:
        loan_period = await get_loan_period_days(user, item_for_policy, db)
    old_due_date = checkout.due_date

    # Calculate new due date from NOW (not old due date) to handle overdue renewals correctly
    now = utc_now()
    checkout.due_date = now + timedelta(days=loan_period)
    checkout.renewal_count += 1

    if checkout.status == CheckoutStatus.overdue:
        checkout.status = CheckoutStatus.active

    # Audit: record the renewal for long-term forensic analysis
    await ops_audit.log_checkout_renewed(
        db, patron=user, checkout=checkout,
        previous_due_date=old_due_date, new_due_date=checkout.due_date,
    )

    # Create lifecycle event if checkout has item_copy_id
    if checkout.item_copy_id and create_lifecycle_event_func:
        await create_lifecycle_event_func(
            db=db,
            item_copy_id=checkout.item_copy_id,
            event_type=LifecycleEventType.RENEWED,
            description=f"Checkout renewed ({checkout.renewal_count}/{max_renewals})" + (" [staff override]" if overrode_cap else ""),
            metadata={
                "patron_id": user.id,
                "old_due_date": old_due_date.isoformat(),
                "new_due_date": checkout.due_date.isoformat(),
                "renewal_count": checkout.renewal_count,
                "staff_override": overrode_cap,
            },
            performed_by_id=user.id,
            related_checkout_id=checkout.id,
        )

    # Invalidate circulation report cache so next report reflects this renewal
    await invalidate_circulation_reports()
