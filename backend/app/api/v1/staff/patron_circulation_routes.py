# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff circulation operations performed from a patron record."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.cache import invalidate_catalog_cache
from ....core.database import get_db
from ....core.rate_limit import limiter
from ....core.shortcuts import get_or_404
from ....models.catalog import CatalogItem
from ....models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ....models.inventory import ItemCopy
from ....models.multi_branch import Branch
from ....models.user import User
from ....schemas.circulation import CheckoutResponse, HoldResponse
from ....services.unified_circulation_service import checkout_item
from ..dependencies import require_staff
from .patrons_schemas import (
    PlaceHoldForPatronRequest,
    PlaceHoldForPatronResponse,
    QuickCheckoutRequest,
    QuickCheckoutResponse,
    RenewAllResponse,
    ReturnAllResponse,
)

router = APIRouter()

@router.post(
    "/{patron_id}/quick-checkout",
    response_model=QuickCheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("60/minute")
async def quick_checkout_for_patron(
    request: Request,
    patron_id: int,
    checkout_data: QuickCheckoutRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Quick checkout an item for a patron by barcode."""
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    normalized = checkout_data.barcode.replace("-", "")
    result = await db.execute(
        select(ItemCopy).where(
            (ItemCopy.barcode == checkout_data.barcode) | (ItemCopy.barcode == normalized)
        )
    )
    copy = result.scalar_one_or_none()
    if copy:
        item_result = await db.execute(
            select(CatalogItem).where(CatalogItem.id == copy.catalog_item_id)
        )
        item = item_result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(CatalogItem).where(
                (CatalogItem.barcode == checkout_data.barcode) | (CatalogItem.barcode == normalized)
            )
        )
        item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found with that barcode"
        )

    deferred_notifications: list = []
    checkout_response, checked_out_item = await checkout_item(
        patron=patron,
        item_id=item.id,
        item_copy_id=copy.id if copy else None,
        db=db,
        is_staff_operation=True,
        override_hold=checkout_data.override_hold,
        hold_disposition=checkout_data.hold_disposition,
        staff_user=staff_user,
        deferred_notifications=deferred_notifications,
    )

    # Capture ORM attributes before commit -- commit expires the objects, and
    # a post-commit attribute access would trigger an async lazy load.
    item_title = checked_out_item.title
    patron_name = f"{patron.first_name} {patron.last_name}"

    # Commit before sending email so we never notify for a bump that rolls back.
    await db.commit()

    from ....services.checkout_service import send_bumped_hold_notification

    for notification in deferred_notifications:
        await send_bumped_hold_notification(notification)

    return QuickCheckoutResponse(
        checkout=checkout_response,
        message=f"Checked out '{item_title}' to {patron_name}",
    )


@router.post("/{patron_id}/renew-all", response_model=RenewAllResponse)
@limiter.limit("10/minute")
async def renew_all_eligible_for_patron(
    request: Request,
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Renew all eligible checkouts for a patron."""
    from ....services.checkout_service import renew_checkout
    from ..lifecycle import create_lifecycle_event

    patron = await get_or_404(db, User, patron_id, "Patron not found")

    checkouts_result = await db.execute(
        select(Checkout, CatalogItem)
        .outerjoin(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(
            Checkout.user_id == patron_id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
    )

    renewals: list[CheckoutResponse] = []
    failures: list[dict] = []

    for checkout, item in checkouts_result.all():
        try:
            # The circulation core handles renewal limits, hold blocks,
            # policy-matrix loan periods, audit, and lifecycle events.
            # Eligibility checks all run before any mutation, so a failed
            # item leaves the shared transaction clean for the next one.
            await renew_checkout(
                checkout,
                patron,
                db,
                create_lifecycle_event,
                is_staff_operation=True,
            )
        except Exception as e:  # noqa: BLE001  # per-item boundary — record failure and continue
            reason = getattr(e, "detail", None) or getattr(e, "message", None) or str(e)
            failures.append(
                {
                    "item_id": checkout.item_id,
                    "item_title": item.title if item else "Unknown",
                    "reason": str(reason),
                }
            )
            continue

        renewals.append(
            CheckoutResponse(
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
        )

    await db.commit()

    return RenewAllResponse(
        renewed_count=len(renewals),
        failed_count=len(failures),
        renewals=renewals,
        failures=failures,
        message=f"Renewed {len(renewals)} items, {len(failures)} failed",
    )


@router.post("/{patron_id}/return-all", response_model=ReturnAllResponse)
@limiter.limit("10/minute")
async def return_all_for_patron(
    request: Request,
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return all checked out items for a patron."""
    from ....services.checkout_service import return_checkout, send_pending_hold_notification
    from ....services.suspension_service import check_and_lift_on_return
    from ..lifecycle import create_lifecycle_event

    patron = await get_or_404(db, User, patron_id, "Patron not found")

    checkouts_result = await db.execute(
        select(Checkout, CatalogItem)
        .outerjoin(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(
            Checkout.user_id == patron_id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
    )

    returns: list[CheckoutResponse] = []
    pending_notifications = []

    for checkout, item in checkouts_result.all():
        ret_result = await return_checkout(checkout, db, patron, create_lifecycle_event)
        if ret_result.pending_notification:
            pending_notifications.append(ret_result.pending_notification)
        display_item = ret_result.item or item
        returns.append(
            CheckoutResponse(
                id=checkout.id,
                user_id=checkout.user_id,
                item_id=checkout.item_id,
                status=checkout.status,
                checked_out_at=checkout.checked_out_at,
                due_date=checkout.due_date,
                returned_at=checkout.returned_at,
                renewal_count=checkout.renewal_count,
                item_title=display_item.title if display_item else None,
                item_author=display_item.author if display_item else None,
            )
        )

    await check_and_lift_on_return(patron_id, db)
    await db.commit()

    for notification in pending_notifications:
        await send_pending_hold_notification(notification)

    await invalidate_catalog_cache()

    return ReturnAllResponse(
        returned_count=len(returns),
        returns=returns,
        message=f"Returned {len(returns)} items for {patron.first_name} {patron.last_name}",
    )


@router.post(
    "/{patron_id}/place-hold",
    response_model=PlaceHoldForPatronResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def place_hold_for_patron(
    request: Request,
    patron_id: int,
    hold_data: PlaceHoldForPatronRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Place a hold on an item for a patron."""
    patron = await get_or_404(db, User, patron_id, "Patron not found")
    if not patron.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Patron account is blocked"
        )

    item = await get_or_404(db, CatalogItem, hold_data.item_id, "Item not found")

    existing_hold = await db.execute(
        select(Hold).where(
            Hold.user_id == patron_id,
            Hold.item_id == hold_data.item_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
    )
    if existing_hold.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Patron already has a hold on this item"
        )

    position_result = await db.execute(
        select(func.count(Hold.id)).where(
            Hold.item_id == hold_data.item_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
    )
    position = (position_result.scalar() or 0) + 1

    pickup_location_id = patron.home_branch_id
    if pickup_location_id is not None:
        branch = await db.scalar(select(Branch.id).where(Branch.id == pickup_location_id))
        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid pickup_location_id: {pickup_location_id}",
            )

    hold = Hold(
        user_id=patron_id,
        item_id=hold_data.item_id,
        pickup_location_id=pickup_location_id,
        status=HoldStatus.pending,
        position=position,
    )
    db.add(hold)

    # Capture a free copy for immediate pickup when one exists (previously a
    # staff-placed hold on an on-shelf item sat pending until some other
    # circulation event promoted it).
    from ....services.hold_service import (
        ready_hold_if_copy_free,
        recompute_title_availability,
    )

    readied = await ready_hold_if_copy_free(hold, patron, item, db)
    await recompute_title_availability(item, db)

    await db.commit()
    await db.refresh(hold)

    if readied:
        message = f"Hold placed for '{item.title}' - ready for pickup now"
    else:
        message = f"Hold placed for '{item.title}' - Position {position} in queue"

    return PlaceHoldForPatronResponse(
        hold=HoldResponse(
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
        ),
        message=message,
    )


@router.get("/{patron_id}/checkouts", response_model=List[CheckoutResponse])
async def get_patron_checkouts(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all active checkouts for a patron."""
    patron = await get_or_404(db, User, patron_id, "Patron not found")
    result = await db.execute(
        select(Checkout)
        .where(
            Checkout.user_id == patron_id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
        .order_by(Checkout.due_date.asc())
    )
    checkouts = result.scalars().all()
    items_map = {}
    if checkouts:
        item_ids = [c.item_id for c in checkouts]
        items_result = await db.execute(select(CatalogItem).where(CatalogItem.id.in_(item_ids)))
        items_map = {i.id: i for i in items_result.scalars().all()}
    return [
        CheckoutResponse(
            id=c.id,
            user_id=c.user_id,
            item_id=c.item_id,
            status=c.status,
            checked_out_at=c.checked_out_at,
            due_date=c.due_date,
            returned_at=c.returned_at,
            renewal_count=c.renewal_count,
            item_title=items_map.get(c.item_id, None) and items_map[c.item_id].title,
            item_author=items_map.get(c.item_id, None) and items_map[c.item_id].author,
        )
        for c in checkouts
    ]


@router.get("/{patron_id}/holds", response_model=List[HoldResponse])
async def get_patron_holds(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all active holds for a patron."""
    patron = await get_or_404(db, User, patron_id, "Patron not found")
    result = await db.execute(
        select(Hold)
        .where(
            Hold.user_id == patron_id,
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
        )
        .order_by(Hold.created_at.desc())
    )
    holds = result.scalars().all()
    items_map = {}
    if holds:
        item_ids = [h.item_id for h in holds]
        items_result = await db.execute(select(CatalogItem).where(CatalogItem.id.in_(item_ids)))
        items_map = {i.id: i for i in items_result.scalars().all()}
    return [
        HoldResponse(
            id=h.id,
            user_id=h.user_id,
            item_id=h.item_id,
            status=h.status,
            created_at=h.created_at,
            expires_at=h.expires_at,
            position=h.position,
            item_title=items_map.get(h.item_id, None) and items_map[h.item_id].title,
            item_author=items_map.get(h.item_id, None) and items_map[h.item_id].author,
        )
        for h in holds
    ]

