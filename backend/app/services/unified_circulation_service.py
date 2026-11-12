# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff-desk adapters over the circulation core.

Checkout/checkin/renewal semantics live in checkout_service (the single
circulation core). This module keeps the CheckoutResponse-shaped staff
entry points and hold placement.
"""

from app.core.logging import get_logger
from datetime import timedelta
from typing import Optional, Tuple

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.authorization import (
    check_card_expiration,
    check_fine_block,
    get_hold_limit,
    get_user_role_settings,
)
from ..core.error_codes import ErrorCode
from ..core.exceptions import (
    BusinessLogicError,
    ConflictError,
    ForbiddenError,
    ResourceNotFoundError,
)
from ..models.catalog import CatalogItem, ItemStatus
from ..models.inventory import ItemCopy
from ..models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ..models.multi_branch import Branch
from ..models.user import User
from ..schemas.circulation import CheckoutResponse, HoldResponse, NextHoldInfo
from .checkout_service import (
    BumpedHoldNotification,  # noqa: F401 - re-export for existing importers
    PendingHoldNotification,
    create_checkout,
    return_checkout,
    send_bumped_hold_notification,  # noqa: F401 - re-export for existing importers
)
from .hold_service import ready_hold_if_copy_free, recompute_title_availability
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)

HOLD_EXPIRY_DAYS = 7


# =============================================================================
# HELPERS
# =============================================================================


async def get_user_hold_expiry(user: User, db: AsyncSession) -> int:
    settings = await get_user_role_settings(user, db)
    return settings.hold_duration_days if settings else HOLD_EXPIRY_DAYS


def build_checkout_response(checkout: Checkout, item: CatalogItem) -> CheckoutResponse:
    return CheckoutResponse(
        id=checkout.id,
        user_id=checkout.user_id,
        item_id=checkout.item_id,
        status=checkout.status,
        checked_out_at=checkout.checked_out_at,
        due_date=checkout.due_date,
        returned_at=checkout.returned_at,
        renewal_count=checkout.renewal_count,
        item_title=item.title if item else None,
        item_author=item.author if item else None,
    )


# =============================================================================
# CHECKOUT OPERATIONS
# =============================================================================


async def checkout_item(
    patron: User,
    item_id: int,
    db: AsyncSession,
    is_staff_operation: bool = False,
    item_copy_id: Optional[int] = None,
    override_hold: bool = False,
    hold_disposition: Optional[str] = None,
    staff_user: Optional[User] = None,
    deferred_notifications: Optional[list] = None,
) -> Tuple[CheckoutResponse, CatalogItem]:
    result = await create_checkout(
        patron,
        item_id,
        db,
        item_copy_id,
        is_staff_operation=is_staff_operation,
        override_hold=override_hold,
        hold_disposition=hold_disposition,
        staff_user=staff_user,
        deferred_notifications=deferred_notifications,
    )
    checkout = result.checkout
    item = result.item
    await db.refresh(checkout)
    # Release the distributed copy lock once the loan row exists; the
    # caller commits afterwards (same window as the previous in-module
    # implementation released in its finally block).
    await result.release_lock()

    return build_checkout_response(checkout, item), item


# =============================================================================
# CHECKIN OPERATIONS
# =============================================================================


async def checkin_by_barcode(
    barcode: str,
    db: AsyncSession,
    staff: Optional[User] = None,
    create_lifecycle_event_func=None,
) -> Tuple[
    CheckoutResponse,
    CatalogItem,
    Optional[NextHoldInfo],
    Optional[PendingHoldNotification],
]:
    normalized = barcode.replace("-", "")
    # Look up item copy by barcode first, then fall back to catalog item
    copy_result = await db.execute(
        select(ItemCopy).where(
            (ItemCopy.barcode == barcode) | (ItemCopy.barcode == normalized)
        )
    )
    copy = copy_result.scalar_one_or_none()
    if copy:
        item_result = await db.execute(select(CatalogItem).where(CatalogItem.id == copy.catalog_item_id))
        item = item_result.scalar_one_or_none()
    else:
        item_result = await db.execute(
            select(CatalogItem).where(
                (CatalogItem.barcode == barcode) | (CatalogItem.barcode == normalized)
            )
        )
        item = item_result.scalar_one_or_none()
    if not item:
        raise ResourceNotFoundError(code=ErrorCode.CATALOG_ITEM_NOT_FOUND, message="Item not found")

    # Find the active checkout for THIS specific copy. Filtering by item_id
    # (the title) alone returns multiple rows for a multi-copy title with more
    # than one copy out, which crashes scalar_one_or_none() with
    # MultipleResultsFound. Prefer the exact copy; fall back to legacy checkouts
    # that never recorded a copy (item_copy_id IS NULL, from before quick-checkout
    # bound the copy). Order so the copy-bound match wins, then the oldest, and
    # take the first so resolution is deterministic and never raises.
    active_statuses = [CheckoutStatus.active, CheckoutStatus.overdue]
    if copy is not None:
        checkout_stmt = (
            select(Checkout)
            .where(
                Checkout.status.in_(active_statuses),
                or_(
                    Checkout.item_copy_id == copy.id,
                    and_(
                        Checkout.item_id == item.id,
                        Checkout.item_copy_id.is_(None),
                    ),
                ),
            )
            .order_by(
                (Checkout.item_copy_id == copy.id).desc(),
                Checkout.checked_out_at.asc(),
            )
        )
    else:
        checkout_stmt = (
            select(Checkout)
            .where(
                Checkout.item_id == item.id,
                Checkout.status.in_(active_statuses),
            )
            .order_by(Checkout.checked_out_at.asc())
        )
    checkout_result = await db.execute(checkout_stmt)
    checkout = checkout_result.scalars().first()
    if not checkout:
        raise ResourceNotFoundError(code=ErrorCode.CHECKOUT_NOT_FOUND, message="No active checkout")

    # The loan owner is whoever the checkout was issued to, so audit,
    # reading-shelf, and suspension lift attribute to the patron; the
    # scanning staff member lands in the audit staff_id.
    loan_owner = await db.get(User, checkout.user_id)
    if loan_owner is None:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Checkout references a missing patron",
        )

    # Delegate checkin semantics (fine, hold promotion, in-app feed row,
    # audit, lifecycle, cache invalidation) to the circulation core.
    ret = await return_checkout(
        checkout,
        db,
        loan_owner,
        create_lifecycle_event_func,
        staff=staff,
    )
    next_hold = ret.promoted_hold

    # Build a small projection of the next-up hold for the staff response.
    # Done here (not in the route) because the route would otherwise need to
    # access next_hold.user — a lazy relationship that 500s with MissingGreenlet
    # outside a sync greenlet context. Loading the user explicitly via db.get
    # keeps Pydantic away from the ORM relationship entirely.
    next_hold_info: Optional[NextHoldInfo] = None
    if next_hold:
        hold_user = await db.get(User, next_hold.user_id)
        if hold_user:
            last_initial = (hold_user.last_name or "").strip()
            last_initial = (last_initial[0] + ".") if last_initial else ""
            next_hold_info = NextHoldInfo(
                hold_id=next_hold.id,
                patron_first_name=hold_user.first_name or "",
                patron_last_initial=last_initial,
                shelf_slot=next_hold.shelf_slot,
                expires_at=next_hold.expires_at,
                item_title=item.title,
            )

    await db.flush()
    await db.refresh(checkout)
    # refresh item too: build_checkout_response reads item.title/.author, which
    # can trigger MissingGreenlet outside a request context if item state was
    # expired by upstream refresh/commit operations.
    await db.refresh(item)

    return build_checkout_response(checkout, item), item, next_hold_info, ret.pending_notification


# =============================================================================
# HOLD PLACEMENT OPERATIONS
# =============================================================================


async def place_hold(
    patron: User,
    item_id: int,
    db: AsyncSession,
) -> Tuple[Optional["HoldResponse"], CatalogItem]:
    from ..schemas.circulation import HoldResponse

    # CRITICAL: Check patron status (deceased, blocked, suspended)
    from ..services.suspension_service import check_patron_suspension_status

    can_circulate, reason, error_code = await check_patron_suspension_status(patron, db)
    if not can_circulate:
        raise ForbiddenError(
            code=error_code or ErrorCode.PATRON_BLOCKED,
            message=reason or "Patron account cannot place holds."
        )

    # Check hold limit (age-group aware)
    max_holds = await get_hold_limit(patron, db)

    result = await db.execute(
        select(Hold)
        .where(
            Hold.user_id == patron.id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
        .with_for_update()
    )
    active_holds = result.scalars().all()

    if len(active_holds) >= max_holds:
        raise BusinessLogicError(
            code=ErrorCode.QUOTA_EXCEEDED,
            message=f"Hold limit reached ({len(active_holds)}/{max_holds}). Cancel existing holds first.",
        )

    # Check card expiration for placing holds
    card_valid, days_remaining = await check_card_expiration(patron, db)
    if not card_valid:
        days_expired = abs(days_remaining) if days_remaining is not None else 0
        raise ForbiddenError(
            code=ErrorCode.PATRON_CARD_EXPIRED,
            message=(
                f"Your library card has expired ({days_expired} days ago). "
                f"Please visit the circulation desk to renew your card before placing holds."
            ),
        )

    # Check for accountability block
    from ..services.fine_service import FINE_FREE_MODE, OVERDUE_CHECKOUT_PAUSE_DAYS

    can_proceed, balance_or_count = await check_fine_block(patron, db)
    if not can_proceed:
        if FINE_FREE_MODE and balance_or_count > 0:
            count = int(balance_or_count)
            raise ForbiddenError(
                code=ErrorCode.PATRON_HAS_OUTSTANDING_FINE,
                message=(
                    f"You have {count} item(s) overdue for more than {OVERDUE_CHECKOUT_PAUSE_DAYS} days. "
                    f"Please return them to place new holds."
                ),
            )
        else:
            raise ForbiddenError(
                code=ErrorCode.PATRON_HAS_OUTSTANDING_FINE,
                message=f"Outstanding balance (${balance_or_count:.2f}) for lost or damaged items blocks hold placement.",
            )

    # Lock item and check status
    item_result = await db.execute(
        select(CatalogItem).where(CatalogItem.id == item_id).with_for_update()
    )
    item = item_result.scalar_one_or_none()

    if not item:
        raise ResourceNotFoundError(code=ErrorCode.CATALOG_ITEM_NOT_FOUND, message="Item not found")

    # Check for duplicate active hold
    existing_hold = await db.execute(
        select(Hold).where(
            Hold.user_id == patron.id,
            Hold.item_id == item_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
    )
    if existing_hold.scalar_one_or_none():
        raise ConflictError(code=ErrorCode.HOLD_EXISTS, message="Already have active hold on this item")

    # Check for existing active checkout
    existing_checkout = await db.execute(
        select(Checkout).where(
            Checkout.user_id == patron.id,
            Checkout.item_id == item_id,
            Checkout.status == CheckoutStatus.active,
        )
    )
    if existing_checkout.scalar_one_or_none():
        raise ConflictError(code=ErrorCode.CHECKOUT_EXISTS, message="Already have this item checked out")

    # Get next position
    position_result = await db.execute(
        select(Hold)
        .where(
            Hold.item_id == item_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
        .with_for_update()
    )
    existing_holds = position_result.scalars().all()
    next_position = max((h.position for h in existing_holds), default=0) + 1

    pickup_location_id = patron.home_branch_id
    if pickup_location_id is not None:
        branch = await db.scalar(select(Branch.id).where(Branch.id == pickup_location_id))
        if branch is None:
            raise BusinessLogicError(
                code=ErrorCode.INVALID_INPUT,
                message=f"Invalid pickup_location_id: {pickup_location_id}",
            )

    # Create hold
    hold = Hold(
        user_id=patron.id,
        item_id=item_id,
        pickup_location_id=pickup_location_id,
        position=next_position,
        status=HoldStatus.pending,
    )

    # Capture a free copy for immediate pickup when one exists; the title
    # status is rederived from copy/loan/reservation counts either way.
    await ready_hold_if_copy_free(hold, patron, item, db)

    db.add(hold)
    await recompute_title_availability(item, db)
    await db.flush()
    await db.refresh(hold)

    hold_response = HoldResponse(
        id=hold.id,
        user_id=hold.user_id,
        item_id=hold.item_id,
        status=hold.status,
        position=hold.position,
        pickup_location_id=hold.pickup_location_id,
        created_at=hold.created_at,
        notified_at=hold.notified_at,
        expires_at=hold.expires_at,
        item_title=item.title,
        item_author=item.author,
    )

    return hold_response, item
