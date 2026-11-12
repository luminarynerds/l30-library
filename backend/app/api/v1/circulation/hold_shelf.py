# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hold shelf management endpoints: shelf slots, expiring holds, patron-on-way,
QR pickup, slip printing, pull list, shelf capacity."""

from datetime import timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.datetime_utils import utc_now

from ....core.cache import invalidate_catalog_cache
from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.catalog import CatalogItem, ItemStatus
from ....models.circulation import Hold, HoldStatus
from ....models.user import User, UserRole
from ....schemas.circulation import (
    ExpiringHoldItem,
    ExpiringHoldsResponse,
    FulfillHoldResponse,
    HoldCheckoutResponse,
    HoldShelfSlipData,
    LocationGroup,
    OnWayCancelResponse,
    PatronOnWayRequest,
    PatronOnWayResponse,
    PatronOnWayStatusItem,
    PatronOnWayStatusResponse,
    PullListItem,
    PullListResponse,
    ReQueueResult,
    ShelfSlotUpdateRequest,
    ShelfSlotUpdateResponse,
    StaffPatronOnWayToggleResponse,
)
from ....services.hold_jobs import _send_hold_ready_notification
from ....services.smart_hold_shelf_service import (
    auto_assign_slot_and_qr,
    generate_hold_shelf_slip_data,
    get_expiring_holds_sorted,
    get_shelf_capacity_with_expiring,
    mark_patron_on_way,
    record_no_show,
    requeue_hold_after_no_show,
)
from ....services.unified_circulation_service import (
    checkout_item as unified_checkout_item,
)
from ..auth import get_current_user
from ..dependencies import require_staff
from .helpers import HOLD_EXPIRY_DAYS

router = APIRouter()


# =============================================================================
# Staff Pull List Endpoint
# =============================================================================


@router.get("/holds/pull-list", response_model=PullListResponse)
async def get_holds_pull_list(
    location: str | None = Query(None, description="Filter by shelf location/branch"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a pull list of items to retrieve from shelves for ready holds.

    Staff/Admin only endpoint.

    Returns all holds with status='ready' grouped by pickup location,
    sorted by pickup deadline (most urgent first) for efficient processing.

    Args:
        location: Optional filter by shelf location/branch

    Returns:
        Pull list with items grouped by location, sorted by expiration date
    """
    # Build query for ready holds with item and user info
    query = (
        select(Hold, CatalogItem)
        .options(selectinload(Hold.user))
        .join(CatalogItem, Hold.item_id == CatalogItem.id)
        .where(Hold.status == HoldStatus.ready)
    )

    # Apply location filter if provided
    if location:
        query = query.where(CatalogItem.location == location)

    # Sort by location, then by expiration date (most urgent first)
    query = query.order_by(
        CatalogItem.location.nulls_last(),
        Hold.expires_at.nulls_last(),  # Sort by deadline to prioritize urgent holds
        Hold.created_at,
    )

    result = await db.execute(query)
    rows = result.all()

    # Calculate days until expiry for each hold
    now = utc_now()

    # Group items by location
    location_groups: dict[str, list[PullListItem]] = {}

    for hold, item in rows:
        patron = hold.user
        # Use location or "Unassigned" for items without location
        loc = item.location or "Unassigned"

        # Calculate patron initials from first and last name
        patron_initials = ""
        if patron.first_name:
            patron_initials += patron.first_name[0].upper()
        if patron.last_name:
            patron_initials += patron.last_name[0].upper()
        patron_initials = patron_initials or "?"

        # Calculate days until expiry
        days_until_expiry = None
        if hold.expires_at:
            if hold.expires_at.tzinfo is None:
                expires_at = hold.expires_at.replace(tzinfo=timezone.utc)
            else:
                expires_at = hold.expires_at
            delta = expires_at - now
            days_until_expiry = delta.days

        pull_item = PullListItem(
            hold_id=hold.id,
            item_id=item.id,
            item_title=item.title,
            item_author=item.author,
            call_number=item.call_number,
            shelf_location=item.location,
            barcode=item.barcode,
            patron_name=patron.full_name,
            patron_initials=patron_initials,
            patron_library_card=patron.library_card,
            hold_expires_at=hold.expires_at,
            hold_created_at=hold.created_at,
            days_until_expiry=days_until_expiry,
            shelf_slot=hold.shelf_slot,
            patron_on_way=hold.patron_on_way,
            qr_pickup_code=hold.qr_pickup_code,
            no_show_count=hold.no_show_count,
        )

        if loc not in location_groups:
            location_groups[loc] = []
        location_groups[loc].append(pull_item)

    # Convert to response format
    locations = [
        LocationGroup(
            location=loc,
            items=items,
            item_count=len(items),
        )
        for loc, items in sorted(location_groups.items())
    ]

    return PullListResponse(
        locations=locations,
        total_items=len(rows),
        generated_at=utc_now(),
    )


@router.get("/holds/shelf-capacity/{branch_id}")
async def get_hold_shelf_capacity(
    branch_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get hold shelf capacity status for a specific branch.

    Staff/Admin only endpoint.

    Returns:
    - Current ready holds count
    - Hold shelf capacity limit
    - Capacity percentage
    - Warning status if near capacity
    """
    from ....models.multi_branch import Branch, BranchSettings

    # Get branch and its settings
    branch = await get_or_404(db, Branch, branch_id, "We couldn't find that library branch. Please check and try again.")

    # Get branch settings or use defaults
    settings_result = await db.execute(
        select(BranchSettings).where(BranchSettings.branch_id == branch_id)
    )
    settings = settings_result.scalar_one_or_none()

    # Get count of ready holds for this branch
    count_result = await db.execute(
        select(func.count(Hold.id))
        .join(CatalogItem, Hold.item_id == CatalogItem.id)
        .where(
            and_(
                Hold.status == HoldStatus.ready,
                CatalogItem.location == branch.code,  # Match by branch code
            )
        )
    )
    ready_holds_count = count_result.scalar() or 0

    # Calculate capacity metrics
    capacity_limit = settings.hold_shelf_capacity if settings else 500
    warning_threshold = settings.hold_shelf_warning_threshold if settings else 80
    capacity_percentage = (ready_holds_count / capacity_limit * 100) if capacity_limit > 0 else 0
    is_at_capacity = ready_holds_count >= capacity_limit
    is_over_warning = capacity_percentage >= warning_threshold

    return {
        "branch_id": branch_id,
        "branch_name": branch.name,
        "ready_holds_count": ready_holds_count,
        "capacity_limit": capacity_limit,
        "capacity_percentage": round(capacity_percentage, 2),
        "is_at_capacity": is_at_capacity,
        "is_over_warning": is_over_warning,
        "warning_threshold_percentage": warning_threshold,
        "available_slots": max(0, capacity_limit - ready_holds_count),
    }


# =============================================================================
# Smart Hold Shelf Management Endpoints
# =============================================================================


@router.get("/holds/expiring", response_model=ExpiringHoldsResponse)
async def get_expiring_holds(
    branch_id: int | None = Query(None, description="Filter by branch"),
    hours: int = Query(48, ge=1, le=168, description="Hours threshold for expiring"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get holds expiring within the given timeframe, sorted soonest-first.

    Staff only. This is the daily "holds expiring" pull list.
    Holds are sorted by expiration time so staff can prioritize
    the most urgent ones.
    """
    now = utc_now()
    holds = await get_expiring_holds_sorted(db, branch_id=branch_id, hours_threshold=hours)

    items = []
    for hold in holds:
        patron = hold.user
        patron_initials = ""
        if patron and patron.first_name:
            patron_initials += patron.first_name[0].upper()
        if patron and patron.last_name:
            patron_initials += patron.last_name[0].upper()

        hours_left = None
        if hold.expires_at:
            exp = hold.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            hours_left = round((exp - now).total_seconds() / 3600, 1)

        items.append(ExpiringHoldItem(
            hold_id=hold.id,
            item_id=hold.item_id,
            item_title=hold.item.title if hold.item else "Unknown",
            item_author=hold.item.author if hold.item else None,
            patron_name=patron.full_name if patron else "Unknown",
            patron_initials=patron_initials or "?",
            shelf_slot=hold.shelf_slot,
            expires_at=hold.expires_at,
            hours_until_expiry=hours_left,
            patron_on_way=hold.patron_on_way,
            patron_library_card=patron.library_card if patron else None,
        ))

    return ExpiringHoldsResponse(
        holds=items,
        total_expiring=len(items),
        generated_at=now,
    )


@router.post("/holds/{hold_id}/patron-on-way", response_model=PatronOnWayResponse)
async def patron_on_way(
    hold_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Patron indicates they are on their way to pick up a hold.

    If the hold is expiring soon, the expiration is extended by a few hours
    to give the patron time to arrive. Available to the hold's patron or staff.
    """
    hold = await get_or_404(db, Hold, hold_id, "We couldn't find that hold. It may have been cancelled or fulfilled.")

    if hold.status != HoldStatus.ready:
        raise HTTPException(status_code=400, detail="This hold isn't ready for pickup yet. You'll get a notification when it's available.")

    # Only the patron or staff can mark on-way
    if hold.user_id != current_user.id and current_user.role == UserRole.PATRON:
        raise HTTPException(status_code=403, detail="This hold belongs to a different account.")

    extended = await mark_patron_on_way(hold, db)
    await db.commit()

    if extended:
        msg = f"Hold extended until {extended.strftime('%I:%M %p')}. See you soon!"
    else:
        msg = "Got it! We'll keep your hold ready."

    return PatronOnWayResponse(
        hold_id=hold.id,
        patron_on_way=True,
        extended_expires_at=extended,
        message=msg,
    )


@router.post("/patron-on-way", response_model=PatronOnWayResponse)
async def signal_patron_on_way(
    request: PatronOnWayRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unified endpoint for patron to signal they are on their way to pick up a hold.

    Accepts a hold_id in the request body and marks the hold as on-way.
    Returns PatronOnWayResponse with estimated arrival information.
    """
    hold = await get_or_404(db, Hold, request.hold_id, "We couldn't find that hold. It may have been cancelled or fulfilled.")

    if hold.status != HoldStatus.ready:
        raise HTTPException(status_code=400, detail="This hold isn't ready for pickup yet. You'll get a notification when it's available.")

    # Only the patron or staff can mark on-way
    if hold.user_id != current_user.id and current_user.role == UserRole.PATRON:
        raise HTTPException(status_code=403, detail="This hold belongs to a different account.")

    extended = await mark_patron_on_way(hold, db)
    await db.commit()

    if extended:
        msg = f"Hold extended until {extended.strftime('%I:%M %p')}. See you soon!"
    else:
        msg = "Got it! We'll keep your hold ready."

    return PatronOnWayResponse(
        hold_id=hold.id,
        patron_on_way=True,
        extended_expires_at=extended,
        message=msg,
    )


@router.get("/patron-on-way/status", response_model=PatronOnWayStatusResponse)
async def get_patron_on_way_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get real-time shelf readiness status for all patron's on-way holds.

    Returns information about all holds the patron has signaled they are coming for,
    including shelf readiness, item location, and estimated wait times.
    """
    # Get all on-way holds for the current user
    result = await db.execute(
        select(Hold)
        .options(selectinload(Hold.item), selectinload(Hold.pickup_location))
        .where(
            and_(
                Hold.user_id == current_user.id,
                Hold.patron_on_way == True,
                Hold.status == HoldStatus.ready,
            )
        )
    )
    holds = result.unique().scalars().all()

    on_way_items = []
    now = utc_now()

    for hold in holds:
        # Calculate if hold is ready (has shelf slot assigned)
        is_ready = hold.shelf_slot is not None

        # Calculate estimated wait time (conservative estimate: 5 minutes for shelf lookup)
        estimated_wait_time_minutes = 5 if is_ready else 15

        # Check if hold is expiring soon
        if hold.expires_at:
            expires_utc = hold.expires_at
            if expires_utc.tzinfo is None:
                expires_utc = expires_utc.replace(tzinfo=timezone.utc)
            time_until_expiration = (expires_utc - now).total_seconds() / 60
            # If expiring in less than 15 minutes, increase estimated wait
            if time_until_expiration < 15:
                estimated_wait_time_minutes = min(int(time_until_expiration), 5)

        on_way_items.append(
            PatronOnWayStatusItem(
                hold_id=hold.id,
                item_title=hold.item.title if hold.item else None,
                item_author=hold.item.author if hold.item else None,
                shelf_slot=hold.shelf_slot,
                expires_at=hold.expires_at,
                qr_pickup_code=hold.qr_pickup_code,
                is_ready=is_ready,
                estimated_wait_time_minutes=estimated_wait_time_minutes,
            )
        )

    all_items_ready = all(item.is_ready for item in on_way_items)

    return PatronOnWayStatusResponse(
        on_way_holds=on_way_items,
        total_on_way_count=len(on_way_items),
        all_items_ready=all_items_ready,
    )


@router.post("/patron-on-way/{hold_id}/cancel", response_model=OnWayCancelResponse)
async def cancel_patron_on_way(
    hold_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a patron's on-way signal for a specific hold.

    Removes the on-way signal, allowing the hold to be returned to the queue
    if not picked up. Only the patron or staff can cancel the signal.
    """
    hold = await get_or_404(db, Hold, hold_id, "We couldn't find that hold. It may have been cancelled or fulfilled.")

    # Only the patron or staff can cancel on-way
    if hold.user_id != current_user.id and current_user.role == UserRole.PATRON:
        raise HTTPException(status_code=403, detail="This hold belongs to a different account.")

    if not hold.patron_on_way:
        raise HTTPException(
            status_code=400, detail="This hold doesn't have an on-my-way signal to cancel."
        )

    # Cancel the on-way signal
    hold.patron_on_way = False
    hold.patron_on_way_at = None
    await db.commit()

    return OnWayCancelResponse(
        hold_id=hold.id,
        patron_on_way=False,
        message="On-way signal cancelled. Hold will be returned to the queue if not picked up soon.",
    )


@router.post("/holds/{hold_id}/requeue", response_model=ReQueueResult)
async def requeue_hold(
    hold_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Re-queue a hold after the pickup window expires (staff action).

    Moves the hold back to the end of the queue, records a no-show,
    clears the shelf slot, and promotes the next patron in line.
    """
    hold_result = await db.execute(
        select(Hold).where(Hold.id == hold_id).with_for_update()
    )
    hold = hold_result.scalar_one_or_none()
    if not hold:
        raise HTTPException(status_code=404, detail="We couldn't find that hold. It may have already been cancelled or picked up.")

    if hold.status != HoldStatus.ready:
        raise HTTPException(status_code=400, detail="This hold can only be re-queued if it's currently ready for pickup.")

    new_position = await requeue_hold_after_no_show(hold, db)
    await db.commit()

    await invalidate_catalog_cache()

    return ReQueueResult(
        hold_id=hold.id,
        new_position=new_position,
        no_show_count=hold.no_show_count,
        message=f"Hold re-queued at position {new_position}. No-show count: {hold.no_show_count}",
    )


@router.post("/holds/{hold_id}/mark-not-picked-up")
async def mark_hold_not_picked_up(
    hold_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark a hold as not picked up. Expires the hold and advances the queue.

    Records a no-show for the patron and promotes the next hold in line.
    """
    hold_result = await db.execute(
        select(Hold)
        .options(selectinload(Hold.user), selectinload(Hold.item))
        .where(Hold.id == hold_id)
        .with_for_update()
    )
    hold = hold_result.unique().scalar_one_or_none()
    if not hold:
        raise HTTPException(status_code=404, detail="We couldn't find that hold. It may have already been cancelled or picked up.")

    if hold.status != HoldStatus.ready:
        raise HTTPException(status_code=400, detail="This hold is no longer ready for pickup, so it can't be marked as not picked up.")

    # Record no-show
    await record_no_show(hold, db)

    # Expire the hold
    hold.status = HoldStatus.expired
    hold.shelf_slot = None

    # Advance queue
    next_hold_result = await db.execute(
        select(Hold)
        .where(
            Hold.item_id == hold.item_id,
            Hold.status == HoldStatus.pending,
        )
        .order_by(Hold.position)
        .limit(1)
        .with_for_update()
    )
    next_hold = next_hold_result.scalar_one_or_none()

    response_data = {
        "hold_id": hold.id,
        "status": "expired",
        "no_show_count": hold.no_show_count,
        "next_hold_promoted": False,
    }

    if next_hold:
        next_hold.status = HoldStatus.ready
        next_hold.notified_at = utc_now()
        next_hold.expires_at = utc_now() + timedelta(days=HOLD_EXPIRY_DAYS)

        # Auto-assign slot and QR for promoted hold
        await auto_assign_slot_and_qr(next_hold, db)

        # Load next hold's user for notification
        if next_hold.user_id:
            user_result = await db.execute(
                select(User).where(User.id == next_hold.user_id)
            )
            next_user = user_result.scalar_one_or_none()
            if next_user and hold.item:
                await _send_hold_ready_notification(next_user, hold.item, db, hold=next_hold)

        response_data["next_hold_promoted"] = True
        response_data["next_hold"] = {
            "hold_id": next_hold.id,
            "patron_name": next_user.full_name if next_user else "Unknown",
            "shelf_slot": next_hold.shelf_slot,
        }
    else:
        # No more holds - release item
        if hold.item_id:
            item_result = await db.execute(
                select(CatalogItem)
                .where(CatalogItem.id == hold.item_id)
                .with_for_update()
            )
            item = item_result.scalar_one_or_none()
            if item and item.status == ItemStatus.on_hold:
                item.status = ItemStatus.available

    await db.commit()
    await invalidate_catalog_cache()

    return response_data


@router.get("/holds/{hold_id}/slip", response_model=HoldShelfSlipData)
async def get_hold_shelf_slip(
    hold_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get data for printing a one-scan hold shelf slip.

    Returns all info needed for the slip: patron initials, item details,
    shelf slot, QR code, and expiration date.
    """
    hold = await get_or_404(db, Hold, hold_id, "We couldn't find that hold. It may have been cancelled or fulfilled.")

    if hold.status != HoldStatus.ready:
        raise HTTPException(status_code=400, detail="A shelf slip can only be printed for holds that are ready for pickup.")

    # Auto-assign slot and QR if not already done
    if not hold.shelf_slot or not hold.qr_pickup_code:
        await auto_assign_slot_and_qr(hold, db)
        await db.commit()

    slip_data = await generate_hold_shelf_slip_data(hold, db)
    return HoldShelfSlipData(**slip_data)


@router.post("/holds/batch-assign-slots")
async def batch_assign_shelf_slots(
    branch_id: int = Query(..., description="Branch to assign slots for"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Batch-assign shelf slots and QR codes to all ready holds at a branch.

    Staff only. Useful after processing a batch of holds or at start of day.
    Only assigns to holds that don't already have a shelf slot.
    """
    result = await db.execute(
        select(Hold)
        .where(
            Hold.status == HoldStatus.ready,
            Hold.pickup_location_id == branch_id,
            Hold.shelf_slot.is_(None),
        )
        .order_by(Hold.expires_at.nulls_last(), Hold.created_at)
    )
    holds = result.scalars().all()

    assigned = []
    for hold in holds:
        slot, qr = await auto_assign_slot_and_qr(hold, db)
        assigned.append({
            "hold_id": hold.id,
            "shelf_slot": slot,
            "qr_pickup_code": qr,
        })

    await db.commit()

    return {
        "assigned_count": len(assigned),
        "holds": assigned,
    }



# =============================================================================
# Manual Shelf Slot Update
# =============================================================================


@router.patch("/holds/{hold_id}/shelf-slot", response_model=ShelfSlotUpdateResponse)
async def update_hold_shelf_slot(
    hold_id: int,
    body: ShelfSlotUpdateRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Manually update the shelf slot for a ready hold.

    Staff only. Allows inline editing of slot assignments from the
    holds shelf dashboard (e.g. changing "A-03" to "B-12").
    Setting shelf_slot to None clears the assignment.
    """
    hold = await get_or_404(db, Hold, hold_id, "We couldn't find that hold. It may have been cancelled or fulfilled.")

    if hold.status != HoldStatus.ready:
        raise HTTPException(
            status_code=400,
            detail="This hold isn't ready yet, so it can't be assigned a shelf slot.",
        )

    hold.shelf_slot = body.shelf_slot
    await db.commit()

    slot_display = body.shelf_slot or "unassigned"
    return ShelfSlotUpdateResponse(
        hold_id=hold.id,
        shelf_slot=hold.shelf_slot,
        message=f"Shelf slot updated to {slot_display}",
    )


# =============================================================================
# Fulfill Hold (Mark as Picked Up)
# =============================================================================


@router.post("/holds/{hold_id}/fulfill", response_model=FulfillHoldResponse)
async def fulfill_hold(
    hold_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark a ready hold as picked up (fulfilled) by the patron.

    Staff only. Sets the hold status to fulfilled, clears the shelf slot,
    and releases the item back to available if no other holds are pending.
    """
    hold_result = await db.execute(
        select(Hold)
        .options(selectinload(Hold.item))
        .where(Hold.id == hold_id)
        .with_for_update()
    )
    hold = hold_result.unique().scalar_one_or_none()
    if not hold:
        raise HTTPException(status_code=404, detail="We couldn't find that hold. It may have been cancelled or fulfilled.")

    if hold.status != HoldStatus.ready:
        raise HTTPException(
            status_code=400,
            detail="This hold isn't ready for pickup yet, so it can't be marked as fulfilled.",
        )

    # Mark fulfilled
    hold.status = HoldStatus.fulfilled
    hold.shelf_slot = None
    hold.patron_on_way = False
    hold.patron_on_way_at = None

    # Check if there are more pending holds for this item
    next_result = await db.execute(
        select(Hold)
        .where(
            Hold.item_id == hold.item_id,
            Hold.status == HoldStatus.pending,
        )
        .order_by(Hold.position)
        .limit(1)
        .with_for_update()
    )
    next_hold = next_result.scalar_one_or_none()

    if next_hold:
        # Promote next hold in queue
        from datetime import timedelta
        next_hold.status = HoldStatus.ready
        next_hold.notified_at = utc_now()
        next_hold.expires_at = utc_now() + timedelta(days=HOLD_EXPIRY_DAYS)
        await auto_assign_slot_and_qr(next_hold, db)

        # Notify next patron
        if next_hold.user_id:
            user_result = await db.execute(
                select(User).where(User.id == next_hold.user_id)
            )
            next_user = user_result.scalar_one_or_none()
            if next_user and hold.item:
                await _send_hold_ready_notification(next_user, hold.item, db, hold=next_hold)
    else:
        # No more holds -- release item back to available
        if hold.item_id:
            item_result = await db.execute(
                select(CatalogItem)
                .where(CatalogItem.id == hold.item_id)
                .with_for_update()
            )
            item = item_result.scalar_one_or_none()
            if item and item.status == ItemStatus.on_hold:
                item.status = ItemStatus.available

    await db.commit()
    await invalidate_catalog_cache()

    return FulfillHoldResponse(
        hold_id=hold.id,
        status="fulfilled",
        message="Hold marked as picked up",
    )


# =============================================================================
# One-Click Checkout of a Ready Hold (staff patron record)
# =============================================================================


@router.post("/holds/{hold_id}/checkout", response_model=HoldCheckoutResponse)
async def checkout_ready_hold(
    hold_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """One-click checkout of a ready hold to its patron (staff only).

    Loads and locks the hold, validates it is ready, then delegates to the
    unified circulation checkout which fulfills the patron's own ready hold
    and creates the loan in the same transaction. The endpoint commits on
    success; any failure propagates without a commit, leaving the hold
    ready and no loan created.
    """
    hold_result = await db.execute(
        select(Hold)
        .options(selectinload(Hold.user))
        .where(Hold.id == hold_id)
        .with_for_update()
    )
    hold = hold_result.unique().scalar_one_or_none()
    if not hold:
        raise HTTPException(
            status_code=404,
            detail="We couldn't find that hold. It may have been cancelled or fulfilled.",
        )

    if hold.status != HoldStatus.ready:
        raise HTTPException(
            status_code=400,
            detail="This hold isn't ready for pickup yet, so it can't be checked out.",
        )

    patron = hold.user
    if patron is None:
        patron = await get_or_404(
            db, User, hold.user_id, "We couldn't find the patron for this hold."
        )

    # Delegates fulfillment + copy selection + loan creation. Does NOT commit;
    # raises a domain error (surfaced as 4xx) if no copy is available, in
    # which case nothing below runs and the transaction is never committed.
    checkout_response, item = await unified_checkout_item(
        patron=patron,
        item_id=hold.item_id,
        db=db,
        is_staff_operation=True,
    )

    await db.commit()
    await invalidate_catalog_cache()

    return HoldCheckoutResponse(
        checkout=checkout_response,
        hold_id=hold.id,
        message=(
            f"Checked out '{item.title}' to "
            f"{patron.first_name} {patron.last_name}"
        ),
    )


# =============================================================================
# Staff Toggle Patron On Way
# =============================================================================


@router.patch(
    "/holds/{hold_id}/patron-on-way",
    response_model=StaffPatronOnWayToggleResponse,
)
async def toggle_patron_on_way(
    hold_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Toggle the patron-on-way flag for a hold (staff action).

    Staff only. Flips the current patron_on_way state. When toggling ON,
    records the timestamp. When toggling OFF, clears it.
    """
    hold = await get_or_404(db, Hold, hold_id, "We couldn't find that hold. It may have been cancelled or fulfilled.")

    if hold.status != HoldStatus.ready:
        raise HTTPException(
            status_code=400,
            detail="This hold isn't ready for pickup yet, so it can't be marked as on the way.",
        )

    # Toggle
    hold.patron_on_way = not hold.patron_on_way
    hold.patron_on_way_at = utc_now() if hold.patron_on_way else None
    await db.commit()

    state = "on way" if hold.patron_on_way else "not on way"
    return StaffPatronOnWayToggleResponse(
        hold_id=hold.id,
        patron_on_way=hold.patron_on_way,
        message=f"Patron marked as {state}",
    )
