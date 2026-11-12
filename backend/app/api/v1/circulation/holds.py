# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hold placement, cancellation, listing, aging report, and renewal endpoints."""

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import utc_now

from ....core.authorization import check_fine_block, get_max_renewals, get_user_role_settings
from ....core.cache import invalidate_catalog_cache
from ....core.database import get_db
from ....core.error_codes import ErrorCode
from ....core.exceptions import BusinessLogicError
from ....core.pagination import PaginationParams, calculate_total_pages
from ....core.service_error_handler import handle_service_errors
from ....core.shortcuts import get_or_404
from ....models.catalog import CatalogItem, ItemStatus
from ....models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ....models.inventory import ItemCopy
from ....models.multi_branch import Branch
from ....models.user import PatronStatus, User, UserRole
from ....schemas.catalog import NON_HOLDABLE_STATUSES
from ....schemas.circulation import (
    CheckoutCreate,
    CheckoutResponse,
    HoldAgingBracket,
    HoldAgingReport,
    HoldCancel,
    HoldCreate,
    HoldResponse,
)
from ....schemas.common import PaginatedResponse, PaginationInfo
from ....services.checkout_service import (
    check_patron_eligibility,
    renew_checkout,
    send_pending_hold_notification,
)
from ....services.collection_alert_service import check_hold_alerts
from ....services.hold_service import (
    check_and_expire_hold_collecting_notifications,
    process_expired_holds_collecting_notifications,
    promote_next_hold_collecting_notification,
    ready_hold_if_copy_free,
    recompute_title_availability,
)
from ....services.hold_wait_estimate import compute_hold_wait_estimate
from ....services import circulation_policy as circ_policy
from ....services.smart_hold_shelf_service import auto_assign_slot_and_qr
from ..auth import get_current_user
from ..dependencies import is_staff_or_admin, require_staff
from ..lifecycle import create_lifecycle_event
from .helpers import check_hold_limit, get_user_hold_expiry, validate_pickup_location

logger = get_logger(__name__)

router = APIRouter()


def _build_hold_response(
    hold: Hold,
    item: CatalogItem,
    branch: Branch | None,
    *,
    copy_count: int = 0,
    loan_period_days: int = 21,
) -> HoldResponse:
    is_ready = hold.status == HoldStatus.ready
    wait = compute_hold_wait_estimate(
        position=hold.position,
        copies=copy_count,
        loan_period_days=loan_period_days,
        is_ready=is_ready,
    )
    return HoldResponse(
        id=hold.id,
        user_id=hold.user_id,
        item_id=hold.item_id,
        status=hold.status,
        position=hold.position,
        queue_position=hold.position if hold.status == HoldStatus.pending else None,
        pickup_location_id=hold.pickup_location_id,
        pickup_branch_name=branch.name if branch else None,
        created_at=hold.created_at,
        notified_at=hold.notified_at,
        expires_at=hold.expires_at,
        item_title=item.title,
        item_author=item.author,
        estimated_wait_days=wait["estimated_wait_days"] if wait else None,
        estimated_wait_weeks=wait["estimated_wait_weeks"] if wait else None,
    )


async def _fetch_wait_context(
    rows: list,
    user: "User",
    db: AsyncSession,
) -> dict[int, dict]:
    """Return {item_id: {copy_count, loan_period_days}} for each row's item.

    Single copy-count batch query + per-item policy resolve. Falls back to
    0 copies (→ treated as 1 by compute_hold_wait_estimate) and 21-day default.
    """
    if not rows:
        return {}

    item_ids = list({item.id for _, item, _ in rows})
    count_result = await db.execute(
        select(ItemCopy.catalog_item_id, func.count(ItemCopy.id).label("cnt"))
        .where(ItemCopy.catalog_item_id.in_(item_ids))
        .group_by(ItemCopy.catalog_item_id)
    )
    copy_counts: dict[int, int] = {row.catalog_item_id: row.cnt for row in count_result}

    context: dict[int, dict] = {}
    for _, item, _ in rows:
        if item.id in context:
            continue
        try:
            policy = await circ_policy.resolve(user=user, item=item, db=db)
            loan_days = policy.loan_period_days
        except Exception:  # noqa: BLE001
            loan_days = 21  # safe fallback; policy resolution shouldn't normally fail
        context[item.id] = {
            "copy_count": copy_counts.get(item.id, 0),
            "loan_period_days": loan_days,
        }
    return context


@router.get("/holds/active", response_model=PaginatedResponse[HoldResponse])
async def get_active_holds(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's active holds with pagination.

    Returns only pending and ready holds (actively waiting or ready for pickup).
    """
    base_filters = [
        Hold.user_id == current_user.id,
        Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
    ]

    result = await db.execute(
        select(Hold, CatalogItem, Branch)
        .join(CatalogItem, Hold.item_id == CatalogItem.id)
        .outerjoin(Branch, Hold.pickup_location_id == Branch.id)
        .where(*base_filters)
        .order_by(Hold.created_at)
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    rows = result.all()

    # Check for and process any expired holds inline. Each expiration may
    # promote the next pending hold to ready -- collect the resulting
    # PendingHoldNotifications and flush them after commit (mirrors
    # return_checkout pattern; never email before the DB write persists).
    modified = False
    pending_notifications = []
    for hold, item, branch in rows:
        expired, notification = await check_and_expire_hold_collecting_notifications(hold, db)
        if expired:
            modified = True
            if notification is not None:
                pending_notifications.append(notification)

    if modified:
        await db.commit()
        for notification in pending_notifications:
            try:
                await send_pending_hold_notification(notification)
            except Exception:
                logger.exception(
                    "Failed to send hold-ready notification from active-holds listing"
                )
        # Re-fetch after processing expired holds
        result = await db.execute(
            select(Hold, CatalogItem, Branch)
            .join(CatalogItem, Hold.item_id == CatalogItem.id)
            .outerjoin(Branch, Hold.pickup_location_id == Branch.id)
            .where(*base_filters)
            .order_by(Hold.created_at)
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        rows = result.all()

    # Count query (after expiration processing for accurate count)
    count_result = await db.execute(
        select(func.count(Hold.id)).where(*base_filters)
    )
    total = count_result.scalar() or 0

    wait_ctx = await _fetch_wait_context(rows, current_user, db)
    items = [
        _build_hold_response(
            hold, item, branch,
            copy_count=wait_ctx.get(item.id, {}).get("copy_count", 0),
            loan_period_days=wait_ctx.get(item.id, {}).get("loan_period_days", 21),
        )
        for hold, item, branch in rows
    ]

    total_pages = calculate_total_pages(total, pagination.page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationInfo(
            page=pagination.page,
            per_page=pagination.page_size,
            total=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        ),
    )


@router.post("/holds", response_model=HoldResponse, status_code=status.HTTP_201_CREATED)
async def place_hold(
    hold_in: HoldCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Place a hold on an item."""
    # Check user hold limit based on role settings
    await check_hold_limit(current_user, db)

    # Check fine balance
    can_proceed, balance = await check_fine_block(current_user, db)
    if not can_proceed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your account has ${balance:.2f} in unpaid fines, which needs to be resolved before placing a hold. Please visit the front desk or pay online.",
        )

    # Suspension / card-expiry gate (the fine check above already ran, so its
    # friendlier message wins for the fine case).
    await check_patron_eligibility(current_user, db, operation="hold")

    # Lock the item row to prevent race conditions on hold position
    result = await db.execute(
        select(CatalogItem)
        .where(CatalogItem.id == hold_in.item_id)
        .with_for_update()
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="We couldn't find that item in the catalog. It may have been removed.")

    # Reject holds on items whose status makes a patron-placed hold meaningless
    # (lost/withdrawn/missing/reference/restricted variants). The same frozenset
    # powers the available_for_hold UX hint and the catalog rail filter (PR #573).
    if item.status in NON_HOLDABLE_STATUSES:
        raise BusinessLogicError(
            code=ErrorCode.ITEM_NOT_HOLDABLE,
            message=(
                f"This item is not currently available for hold (status: {item.status.value}). "
                "Please ask staff if you need help finding another copy."
            ),
        )

    # Process any expired holds on this item first. Any newly promoted hold
    # gets a deferred PendingHoldNotification we must send after commit.
    _expired_count, expired_promotion_notifications = await process_expired_holds_collecting_notifications(
        db, item_id=item.id
    )

    existing = await db.execute(
        select(Hold).where(
            Hold.user_id == current_user.id,
            Hold.item_id == hold_in.item_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You already have a hold on this item. Check My Account > Holds to see your place in line."
        )

    checkout_existing = await db.execute(
        select(Checkout).where(
            Checkout.user_id == current_user.id,
            Checkout.item_id == hold_in.item_id,
            Checkout.status == CheckoutStatus.active,
        )
    )
    if checkout_existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You already have this item checked out. No need to place a hold."
        )

    # Lock all existing holds for this item to prevent race condition on position assignment
    # We must lock the actual rows, not just query an aggregate (which doesn't lock rows)
    existing_holds_result = await db.execute(
        select(Hold)
        .where(
            Hold.item_id == hold_in.item_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
        .with_for_update()
    )
    existing_holds = existing_holds_result.scalars().all()
    max_position = max((h.position for h in existing_holds), default=0)

    # Default pickup location to user's home branch if not specified
    pickup_location_id = hold_in.pickup_location_id or current_user.home_branch_id
    await validate_pickup_location(db, pickup_location_id)

    hold = Hold(
        user_id=current_user.id,
        item_id=hold_in.item_id,
        pickup_location_id=pickup_location_id,
        position=max_position + 1,
        status=HoldStatus.pending,
    )
    db.add(hold)

    # Capture a free copy for immediate pickup when one exists; the title
    # status is rederived from copy/loan/reservation counts either way.
    if await ready_hold_if_copy_free(hold, current_user, item, db):
        # Auto-assign shelf slot and QR code for immediate pickup
        await auto_assign_slot_and_qr(hold, db)
    await recompute_title_availability(item, db)

    await db.commit()
    await db.refresh(hold)

    # Send any deferred hold-ready notifications produced by the expired-hold
    # sweep above (a stale ready hold may have expired and promoted the next
    # patron silently before this fix).
    for notification in expired_promotion_notifications:
        try:
            await send_pending_hold_notification(notification)
        except Exception:
            logger.exception(
                "Failed to send hold-ready notification triggered by place_hold sweep"
            )

    # Check for collection alerts after hold is created
    await check_hold_alerts(db, hold.item_id)

    # Invalidate catalog cache since item status may have changed
    await invalidate_catalog_cache()

    # Fetch branch name for the response
    branch_result = await db.execute(
        select(Branch).where(Branch.id == hold.pickup_location_id)
    )
    branch = branch_result.scalar_one_or_none()

    return HoldResponse(
        id=hold.id,
        user_id=hold.user_id,
        item_id=hold.item_id,
        status=hold.status,
        position=hold.position,
        queue_position=hold.position if hold.status == HoldStatus.pending else None,
        pickup_location_id=hold.pickup_location_id,
        pickup_branch_name=branch.name if branch else None,
        created_at=hold.created_at,
        notified_at=hold.notified_at,
        expires_at=hold.expires_at,
        shelf_slot=hold.shelf_slot,
        patron_on_way=hold.patron_on_way,
        qr_pickup_code=hold.qr_pickup_code,
        no_show_count=hold.no_show_count,
        item_title=item.title,
        item_author=item.author,
    )


@router.get("/holds", response_model=PaginatedResponse[HoldResponse])
@handle_service_errors("Failed to retrieve holds")
async def get_user_holds(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's active holds with pagination."""
    base_filters = [
        Hold.user_id == current_user.id,
        Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
    ]

    result = await db.execute(
        select(Hold, CatalogItem, Branch)
        .join(CatalogItem, Hold.item_id == CatalogItem.id)
        .outerjoin(Branch, Hold.pickup_location_id == Branch.id)
        .where(*base_filters)
        .order_by(Hold.created_at)
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    rows = result.all()

    # Check for and process any expired holds inline. Each expiration may
    # silently promote the next patron -- capture PendingHoldNotifications
    # and flush them after commit (same pattern as get_active_holds above).
    modified = False
    pending_notifications = []
    for hold, item, branch in rows:
        expired, notification = await check_and_expire_hold_collecting_notifications(hold, db)
        if expired:
            modified = True
            if notification is not None:
                pending_notifications.append(notification)

    if modified:
        await db.commit()
        for notification in pending_notifications:
            try:
                await send_pending_hold_notification(notification)
            except Exception:
                logger.exception(
                    "Failed to send hold-ready notification from get_user_holds"
                )
        # Re-fetch after processing expired holds
        result = await db.execute(
            select(Hold, CatalogItem, Branch)
            .join(CatalogItem, Hold.item_id == CatalogItem.id)
            .outerjoin(Branch, Hold.pickup_location_id == Branch.id)
            .where(*base_filters)
            .order_by(Hold.created_at)
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        rows = result.all()

    # Count query (after expiration processing for accurate count)
    count_result = await db.execute(
        select(func.count(Hold.id)).where(*base_filters)
    )
    total = count_result.scalar() or 0

    wait_ctx = await _fetch_wait_context(rows, current_user, db)
    items = [
        _build_hold_response(
            hold, item, branch,
            copy_count=wait_ctx.get(item.id, {}).get("copy_count", 0),
            loan_period_days=wait_ctx.get(item.id, {}).get("loan_period_days", 21),
        )
        for hold, item, branch in rows
    ]

    total_pages = calculate_total_pages(total, pagination.page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationInfo(
            page=pagination.page,
            per_page=pagination.page_size,
            total=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        ),
    )


@router.delete("/holds/{hold_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_hold(
    hold_id: int,
    cancel_in: HoldCancel | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a hold.

    Patrons can cancel their own holds. Staff/admins can cancel any hold.
    Only pending or ready holds can be cancelled.
    """
    # Lock the hold row to prevent concurrent modifications
    result = await db.execute(
        select(Hold)
        .where(Hold.id == hold_id)
        .with_for_update()
    )
    hold = result.scalar_one_or_none()

    if not hold:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="We couldn't find that hold. It may have already been cancelled or picked up.",
        )

    # Authorization: patrons can only cancel their own holds
    is_staff = is_staff_or_admin(current_user)
    if hold.user_id != current_user.id and not is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This hold belongs to a different account.",
        )

    # Only pending or ready holds can be cancelled
    if hold.status not in (HoldStatus.pending, HoldStatus.ready):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This hold can't be cancelled because it has already been {hold.status}.",
        )

    # Determine who is cancelling
    if is_staff and hold.user_id != current_user.id:
        cancelled_by = "staff"
    else:
        cancelled_by = "patron"

    reason = cancel_in.reason if cancel_in else ""

    # Update hold status and cancellation metadata
    was_ready = hold.status == HoldStatus.ready
    item_id = hold.item_id

    hold.status = HoldStatus.cancelled
    hold.cancelled_at = utc_now()
    hold.cancelled_by = cancelled_by
    hold.cancellation_reason = reason

    # If the cancelled hold was ready, promote the next hold in queue.
    # Capture the PendingHoldNotification so the newly-readied patron actually
    # learns their hold is ready (previously this promotion was silent).
    cancellation_notification = None
    if was_ready:
        _promoted, cancellation_notification = await promote_next_hold_collecting_notification(item_id, db)

    # Reposition remaining holds in the queue
    remaining_holds_result = await db.execute(
        select(Hold)
        .where(
            Hold.item_id == item_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
        .order_by(Hold.position)
        .with_for_update()
    )
    remaining_holds = remaining_holds_result.scalars().all()
    for idx, h in enumerate(remaining_holds, start=1):
        h.position = idx

    await db.commit()

    # Send hold-ready notification AFTER commit (mirrors return_checkout).
    if cancellation_notification is not None:
        try:
            await send_pending_hold_notification(cancellation_notification)
        except Exception:
            logger.exception(
                "Failed to send hold-ready notification from cancel_hold promotion"
            )

    # Invalidate catalog cache since item status may have changed
    await invalidate_catalog_cache()


@router.get("/holds/aging-report", response_model=HoldAgingReport)
async def get_hold_aging_report(
    item_id: int | None = Query(None, description="Filter by item ID"),
    location: str | None = Query(None, description="Filter by item location"),
    date_from: datetime | None = Query(None, description="Filter holds created on or after this date"),
    date_to: datetime | None = Query(None, description="Filter holds created on or before this date"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aging report for pending holds - staff/admin only.

    Returns metrics about how long patrons have been waiting for holds:
    - Total count of pending holds
    - Average wait time in days
    - Longest wait time in days
    - Breakdown by age brackets (0-7, 7-14, 14-30, 30+ days)

    Supports filtering by:
    - item_id: Only holds for a specific item
    - location: Only holds for items at a specific location
    - date_from/date_to: Only holds created within a date range
    """
    now = utc_now()

    # Build base query for pending holds
    query = select(Hold).where(Hold.status == HoldStatus.pending)

    # Apply filters
    if item_id is not None:
        query = query.where(Hold.item_id == item_id)

    if location is not None:
        # Join with CatalogItem to filter by location
        query = query.join(CatalogItem, Hold.item_id == CatalogItem.id).where(
            CatalogItem.location == location
        )

    if date_from is not None:
        query = query.where(Hold.created_at >= date_from)

    if date_to is not None:
        query = query.where(Hold.created_at <= date_to)

    result = await db.execute(query)
    holds = result.scalars().all()

    # Calculate wait times in days for each hold
    wait_days_list = []
    for hold in holds:
        if hold.created_at:
            # Handle timezone-aware vs naive datetime
            created_at = hold.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            delta = now - created_at
            wait_days_list.append(delta.days)

    total_pending = len(wait_days_list)

    # Calculate metrics
    if total_pending > 0:
        average_wait = sum(wait_days_list) / total_pending
        longest_wait = max(wait_days_list)
    else:
        average_wait = 0.0
        longest_wait = 0

    # Calculate brackets
    brackets_config = [
        ("0-7 days", 0, 7),
        ("7-14 days", 7, 14),
        ("14-30 days", 14, 30),
        ("30+ days", 30, None),
    ]

    brackets = []
    for label, min_days, max_days in brackets_config:
        if max_days is None:
            count = sum(1 for d in wait_days_list if d >= min_days)
        else:
            count = sum(1 for d in wait_days_list if min_days <= d < max_days)

        brackets.append(
            HoldAgingBracket(
                bracket_label=label,
                min_days=min_days,
                max_days=max_days,
                count=count,
            )
        )

    return HoldAgingReport(
        total_pending_holds=total_pending,
        average_wait_days=round(average_wait, 2),
        longest_wait_days=longest_wait,
        brackets=brackets,
        filtered_by_item_id=item_id,
        filtered_by_location=location,
        filtered_by_date_from=date_from,
        filtered_by_date_to=date_to,
    )


@router.post("/renew/{checkout_id}", response_model=CheckoutResponse)
async def renew_item(
    checkout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Renew a checkout, extending the due date."""
    # 1. Patron account status check
    if current_user.patron_status != PatronStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is currently on hold. Please contact the library at the front desk or by phone to get this resolved.",
        )

    # Lock the checkout to prevent concurrent modifications
    result = await db.execute(
        select(Checkout)
        .where(Checkout.id == checkout_id, Checkout.user_id == current_user.id)
        .with_for_update()
    )
    checkout = result.scalar_one_or_none()

    if not checkout:
        raise HTTPException(status_code=404, detail="We couldn't find that checkout. It may have already been returned.")

    # 2. Renewal limit check
    max_renewals = await get_max_renewals(current_user, db)
    if checkout.renewal_count >= max_renewals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This item has been renewed the maximum {max_renewals} times. Please return it so others can enjoy it too.",
        )

    # 3. Hold queue check - block renewal if other patrons are waiting
    holds_result = await db.execute(
        select(Hold.id).where(
            Hold.item_id == checkout.item_id,
            Hold.user_id != current_user.id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
    )
    if holds_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Someone else is waiting for this item, so it can't be renewed. Please return it by the due date.",
        )

    # 4. Overdue grace check - block renewal if item is too far overdue
    if checkout.due_date:
        now = utc_now()
        due_dt = checkout.due_date
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=timezone.utc)
        overdue_days = (now - due_dt).days
        if overdue_days > 14:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This item is {overdue_days} days overdue and can no longer be renewed. Please return it as soon as possible.",
            )

    # 5. Check fine balance
    can_proceed, balance = await check_fine_block(current_user, db)
    if not can_proceed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your account has ${balance:.2f} in unpaid fines, which needs to be resolved before renewing. Please visit the front desk or pay online.",
        )

    # Delegate to service layer (handles status validation and due date extension)
    await renew_checkout(checkout, current_user, db, create_lifecycle_event)

    # Get item for response
    item_result = await db.execute(
        select(CatalogItem).where(CatalogItem.id == checkout.item_id)
    )
    item = item_result.scalar_one_or_none()

    await db.commit()
    await db.refresh(checkout)

    # Calculate renewals remaining
    renewals_remaining = max(0, max_renewals - checkout.renewal_count)

    return CheckoutResponse(
        id=checkout.id,
        user_id=checkout.user_id,
        item_id=checkout.item_id,
        status=checkout.status,
        checked_out_at=checkout.checked_out_at,
        due_date=checkout.due_date,
        returned_at=checkout.returned_at,
        renewal_count=checkout.renewal_count,
        renewals_remaining=renewals_remaining,
        item_title=item.title if item else None,
        item_author=item.author if item else None,
    )
