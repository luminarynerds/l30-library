# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Circulation Checkin Endpoints

Barcode-driven staff-desk checkin operations and post-checkin
condition reports (damaged, lost, claims-returned).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.rate_limit import limiter
from ....models.catalog import CatalogItem
from ....models.circulation import Checkout
from ....models.inventory import ItemCopy
from ....models.user import User
from ....schemas.circulation import CheckoutResponse
from ..dependencies import require_staff

router = APIRouter(prefix="/staff", tags=["staff-circulation-checkin"])


@router.post("/override-renew/{checkout_id}", response_model=CheckoutResponse)
@limiter.limit("30/minute")
async def staff_override_renew(
    request: Request,
    checkout_id: int,
    override: bool = Query(
        False,
        description="When true, renew past the per-patron renewal cap. The "
                    "overdue-grace cutoff is always waived for staff; the "
                    "hold queue still blocks when another patron is waiting.",
    ),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff renew a single checkout on behalf of any patron (desk override).

    Not scoped to the caller's own checkouts and skips the overdue cutoff.
    With override=True staff may also renew past the renewal cap (audit-
    logged). The hold queue still applies, so a waiting patron is never
    bumped.
    """
    from ....services.checkout_service import renew_checkout
    from ..lifecycle import create_lifecycle_event

    result = await db.execute(
        select(Checkout).where(Checkout.id == checkout_id).with_for_update()
    )
    checkout = result.scalar_one_or_none()
    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout not found")

    patron_result = await db.execute(
        select(User).where(User.id == checkout.user_id)
    )
    patron = patron_result.scalar_one_or_none()
    if not patron:
        raise HTTPException(status_code=404, detail="Patron not found")

    await renew_checkout(
        checkout, patron, db, create_lifecycle_event,
        is_staff_operation=True, force=override,
    )

    item_result = await db.execute(
        select(CatalogItem).where(CatalogItem.id == checkout.item_id)
    )
    item = item_result.scalar_one_or_none()

    await db.commit()

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


@router.post("/checkin-barcode")
@limiter.limit("60/minute")
async def staff_checkin_by_barcode(
    request: Request,
    barcode: str = Query(..., description="Item barcode to check in"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Check in an item by scanning its barcode."""
    from ....services.checkout_service import send_pending_hold_notification
    from ....services.unified_circulation_service import checkin_by_barcode
    from ..lifecycle import create_lifecycle_event

    try:
        checkout_response, item, next_hold, pending_notification = await checkin_by_barcode(
            barcode=barcode,
            db=db,
            staff=staff_user,
            create_lifecycle_event_func=create_lifecycle_event,
        )
        item_title = item.title
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Send hold-ready notification AFTER commit so we never notify for
    # a hold promotion that gets rolled back.
    await send_pending_hold_notification(pending_notification)

    return {
        "message": f"Checked in {item_title}",
        "checkout": checkout_response,
        "next_hold": next_hold,
    }


@router.post("/checkin-condition-report")
@limiter.limit("30/minute")
async def staff_checkin_condition_report(
    request: Request,
    checkout_id: int = Query(..., description="Checkout ID from the checkin"),
    condition_type: str = Query(..., description="One of: damaged, lost_by_patron, claims_returned, returned_damaged"),
    notes: str = Query("", description="Staff notes about the condition"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Report a condition issue for an item that was just checked in.

    Called after staff checkin when the returned item has damage,
    was previously reported lost by the patron, or is a claims-returned situation.
    """
    valid_types = {"damaged", "lost_by_patron", "claims_returned", "returned_damaged"}
    if condition_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid condition_type. Must be one of: {sorted(valid_types)}",
        )

    result = await db.execute(
        select(Checkout).where(Checkout.id == checkout_id)
    )
    checkout = result.scalar_one_or_none()
    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout not found")

    if condition_type == "claims_returned":
        from ....services.claims_returned_service import ClaimsReturnedService
        service = ClaimsReturnedService(db)
        claim_result = await service.file_claim(
            checkout_id=checkout_id,
            patron_statement=notes or "Reported at checkin",
            filed_by=staff_user,
            send_notification=False,
        )
        if not claim_result.success:
            raise HTTPException(status_code=400, detail=claim_result.message)
        await db.commit()
        return {"success": True, "message": "Claims returned dispute filed", "condition_type": condition_type}

    if condition_type in ("damaged", "returned_damaged"):
        item_copy_id = checkout.item_copy_id
        if not item_copy_id:
            copy_result = await db.execute(
                select(ItemCopy).where(ItemCopy.catalog_item_id == checkout.item_id).limit(1)
            )
            copy = copy_result.scalar_one_or_none()
            if copy:
                item_copy_id = copy.id
        if not item_copy_id:
            raise HTTPException(status_code=400, detail="No item copy found for this checkout")

        from ....services.damaged_item_workflow_service import DamagedItemWorkflowService
        from ....models.lost_damaged import DamageSeverity
        from ....models.inventory import DamageType
        service = DamagedItemWorkflowService(db)
        damage_result = await service.report_damage(
            item_copy_id=item_copy_id,
            damage_types=[DamageType.other],
            damage_description=notes or "Damage noted at checkin",
            severity=DamageSeverity.moderate,
            reported_by=staff_user,
            checkout_id=checkout_id,
            patron_id=checkout.user_id,
            is_patron_responsible=True,
            send_notification=False,
        )
        if not damage_result.success:
            raise HTTPException(status_code=400, detail=damage_result.message)
        await db.commit()
        return {"success": True, "message": "Damage report filed", "condition_type": condition_type}

    if condition_type == "lost_by_patron":
        from ....services.lost_item_workflow_service import LostItemWorkflowService
        from ....models.lost_damaged import LostItemType
        service = LostItemWorkflowService(db)
        lost_result = await service.mark_item_lost(
            checkout_id=checkout_id,
            lost_type=LostItemType.lost_by_patron,
            reported_by=staff_user,
            report_notes=notes or "Reported at checkin",
            send_notification=False,
            commit=False,
        )
        if not lost_result.success:
            raise HTTPException(status_code=400, detail=lost_result.message)
        await db.commit()
        return {"success": True, "message": "Lost item report filed", "condition_type": condition_type}
