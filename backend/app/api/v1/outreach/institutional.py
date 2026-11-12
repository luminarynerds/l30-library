# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Institutional card management and checkout endpoints, plus bulk checkout endpoints."""

from datetime import date, datetime, timedelta
import hashlib
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.logging import get_logger
from ....models.outreach import (
    OutreachPartner, InstitutionalCard, InstitutionalCheckout,
    BulkCheckout, BulkCheckoutItem,
    InstitutionalCardStatus, BulkCheckoutStatus
)
from ....models.user import User
from ....models.inventory import ItemCopy
from ....schemas.outreach import (
    InstitutionalCardCreate, InstitutionalCardUpdate, InstitutionalCardResponse,
    InstitutionalCardListResponse, InstitutionalCheckoutCreate, InstitutionalCheckoutResponse,
    BulkCheckoutCreate, BulkCheckoutUpdate, BulkCheckoutResponse,
    BulkCheckoutListResponse, BulkCheckoutItemAdd, BulkCheckoutItemReturn,
    BulkCheckoutItemResponse,
)
from .helpers import require_staff

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Institutional Card Endpoints
# =============================================================================

@router.post("/institutional-cards", response_model=InstitutionalCardResponse, status_code=201)
async def create_institutional_card(
    card_data: InstitutionalCardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Create a new institutional library card."""
    # Verify partner exists
    partner_query = select(OutreachPartner).where(OutreachPartner.id == card_data.partner_id)
    partner = (await db.execute(partner_query)).scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    # Generate unique card number
    card_number = f"INST-{secrets.token_hex(6).upper()}"

    # Hash PIN if provided
    pin_hash = None
    if card_data.requires_pin and card_data.pin:
        pin_hash = hashlib.sha256(card_data.pin.encode()).hexdigest()

    card = InstitutionalCard(
        partner_id=card_data.partner_id,
        card_number=card_number,
        card_name=card_data.card_name,
        authorized_users=card_data.authorized_users,
        requires_pin=card_data.requires_pin,
        pin_hash=pin_hash,
        checkout_limit=card_data.checkout_limit,
        hold_limit=card_data.hold_limit,
        loan_period_days=card_data.loan_period_days,
        renewal_limit=card_data.renewal_limit,
        exempt_from_fines=card_data.exempt_from_fines,
        fine_cap=card_data.fine_cap,
        deposit_required=card_data.deposit_required,
        deposit_amount=card_data.deposit_amount,
        issued_date=date.today(),
        expiry_date=card_data.expiry_date,
        notes=card_data.notes,
        issued_by_id=current_user.id,
        status=InstitutionalCardStatus.ACTIVE.value
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)

    logger.info(f"Created institutional card: {card.card_number}",
                extra={"card_id": card.id, "partner_id": card_data.partner_id})

    response = InstitutionalCardResponse.model_validate(card)
    response.partner_name = partner.name
    return response


@router.get("/institutional-cards", response_model=InstitutionalCardListResponse)
async def list_institutional_cards(
    partner_id: Optional[int] = None,
    status: Optional[InstitutionalCardStatus] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """List institutional cards with filtering."""
    query = select(InstitutionalCard).options(
        selectinload(InstitutionalCard.partner)
    )

    if partner_id:
        query = query.where(InstitutionalCard.partner_id == partner_id)
    if status:
        query = query.where(InstitutionalCard.status == status.value)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(InstitutionalCard.card_name).offset(offset).limit(limit)
    result = await db.execute(query)
    cards = result.scalars().all()

    card_responses = []
    for c in cards:
        response = InstitutionalCardResponse.model_validate(c)
        response.partner_name = c.partner.name if c.partner else None
        card_responses.append(response)

    return InstitutionalCardListResponse(
        cards=card_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/institutional-cards/{card_id}", response_model=InstitutionalCardResponse)
async def get_institutional_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Get details of an institutional card."""
    query = select(InstitutionalCard).options(
        selectinload(InstitutionalCard.partner)
    ).where(InstitutionalCard.id == card_id)

    result = await db.execute(query)
    card = result.scalar_one_or_none()

    if not card:
        raise HTTPException(status_code=404, detail="Institutional card not found")

    response = InstitutionalCardResponse.model_validate(card)
    response.partner_name = card.partner.name if card.partner else None
    return response


@router.patch("/institutional-cards/{card_id}", response_model=InstitutionalCardResponse)
async def update_institutional_card(
    card_id: int,
    update_data: InstitutionalCardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Update an institutional card."""
    query = select(InstitutionalCard).options(
        selectinload(InstitutionalCard.partner)
    ).where(InstitutionalCard.id == card_id)
    result = await db.execute(query)
    card = result.scalar_one_or_none()

    if not card:
        raise HTTPException(status_code=404, detail="Institutional card not found")

    update_dict = update_data.model_dump(exclude_unset=True, exclude={"new_pin"})

    # Handle PIN update
    if update_data.new_pin:
        update_dict["pin_hash"] = hashlib.sha256(update_data.new_pin.encode()).hexdigest()

    # Handle status enum
    if "status" in update_dict and update_dict["status"]:
        update_dict["status"] = update_dict["status"].value

    for field, value in update_dict.items():
        setattr(card, field, value)

    await db.commit()
    await db.refresh(card)

    response = InstitutionalCardResponse.model_validate(card)
    response.partner_name = card.partner.name if card.partner else None
    return response


@router.post("/institutional-cards/{card_id}/checkout", response_model=InstitutionalCheckoutResponse)
async def institutional_checkout(
    card_id: int,
    checkout_data: InstitutionalCheckoutCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Check out an item using an institutional card."""
    # Get the card
    card_query = select(InstitutionalCard).where(InstitutionalCard.id == card_id)
    card = (await db.execute(card_query)).scalar_one_or_none()

    if not card:
        raise HTTPException(status_code=404, detail="Institutional card not found")

    if card.status != InstitutionalCardStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="Card is not active")

    # Verify PIN if required
    if card.requires_pin:
        if not checkout_data.pin:
            raise HTTPException(status_code=400, detail="PIN is required")
        if hashlib.sha256(checkout_data.pin.encode()).hexdigest() != card.pin_hash:
            raise HTTPException(status_code=400, detail="Invalid PIN")

    # Check checkout limit
    if card.current_checkouts >= card.checkout_limit:
        raise HTTPException(status_code=400, detail="Checkout limit reached")

    # Find the item by barcode
    item_query = select(ItemCopy).options(
        selectinload(ItemCopy.catalog_item)
    ).where(ItemCopy.barcode == checkout_data.barcode)
    item_copy = (await db.execute(item_query)).scalar_one_or_none()

    if not item_copy:
        raise HTTPException(status_code=404, detail="Item not found")

    # Calculate due date
    due_date = datetime.now() + timedelta(days=card.loan_period_days)

    # Create institutional checkout record
    inst_checkout = InstitutionalCheckout(
        card_id=card_id,
        item_copy_id=item_copy.id,
        barcode=checkout_data.barcode,
        title=item_copy.catalog_item.title if item_copy.catalog_item else None,
        checked_out_by_name=checkout_data.checked_out_by_name,
        checked_out_by_id=current_user.id,
        due_date=due_date,
        status="active"
    )
    db.add(inst_checkout)

    # Update card statistics
    card.current_checkouts += 1
    card.total_checkouts += 1

    await db.commit()
    await db.refresh(inst_checkout)

    logger.info(f"Institutional checkout: {checkout_data.barcode} on card {card.card_number}",
                extra={"card_id": card_id, "barcode": checkout_data.barcode})

    response = InstitutionalCheckoutResponse.model_validate(inst_checkout)
    response.card_number = card.card_number
    return response


@router.get("/institutional-cards/{card_id}/checkouts", response_model=list[InstitutionalCheckoutResponse])
async def list_institutional_checkouts(
    card_id: int,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """List checkouts for an institutional card."""
    query = select(InstitutionalCheckout).where(InstitutionalCheckout.card_id == card_id)

    if status:
        query = query.where(InstitutionalCheckout.status == status)

    query = query.order_by(InstitutionalCheckout.checked_out_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)

    return result.scalars().all()


# =============================================================================
# Bulk Checkout Endpoints
# =============================================================================

@router.post("/bulk-checkouts", response_model=BulkCheckoutResponse, status_code=201)
async def create_bulk_checkout(
    checkout_data: BulkCheckoutCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Create a new bulk/classroom checkout."""
    # Verify partner exists
    partner_query = select(OutreachPartner).where(OutreachPartner.id == checkout_data.partner_id)
    partner = (await db.execute(partner_query)).scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    bulk_checkout = BulkCheckout(
        **checkout_data.model_dump(),
        status=BulkCheckoutStatus.ACTIVE.value,
        processed_by_id=current_user.id
    )
    db.add(bulk_checkout)
    await db.commit()
    await db.refresh(bulk_checkout)

    logger.info(f"Created bulk checkout: {bulk_checkout.checkout_name}",
                extra={"bulk_checkout_id": bulk_checkout.id, "partner_id": checkout_data.partner_id})

    response = BulkCheckoutResponse.model_validate(bulk_checkout)
    response.partner_name = partner.name
    response.items_outstanding = bulk_checkout.total_items - bulk_checkout.items_returned - bulk_checkout.items_lost
    return response


@router.get("/bulk-checkouts", response_model=BulkCheckoutListResponse)
async def list_bulk_checkouts(
    partner_id: Optional[int] = None,
    status: Optional[BulkCheckoutStatus] = None,
    overdue_only: bool = False,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """List bulk checkouts with filtering."""
    query = select(BulkCheckout).options(
        selectinload(BulkCheckout.partner),
        selectinload(BulkCheckout.items)
    )

    if partner_id:
        query = query.where(BulkCheckout.partner_id == partner_id)
    if status:
        query = query.where(BulkCheckout.status == status.value)
    if overdue_only:
        query = query.where(
            BulkCheckout.due_date < date.today(),
            BulkCheckout.status == BulkCheckoutStatus.ACTIVE.value
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(BulkCheckout.due_date.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    checkouts = result.scalars().all()

    checkout_responses = []
    for c in checkouts:
        response = BulkCheckoutResponse.model_validate(c)
        response.partner_name = c.partner.name if c.partner else None
        response.items_outstanding = c.total_items - c.items_returned - c.items_lost
        response.items = [BulkCheckoutItemResponse.model_validate(i) for i in c.items]
        checkout_responses.append(response)

    return BulkCheckoutListResponse(
        checkouts=checkout_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/bulk-checkouts/{checkout_id}", response_model=BulkCheckoutResponse)
async def get_bulk_checkout(
    checkout_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Get details of a bulk checkout."""
    query = select(BulkCheckout).options(
        selectinload(BulkCheckout.partner),
        selectinload(BulkCheckout.items)
    ).where(BulkCheckout.id == checkout_id)

    result = await db.execute(query)
    checkout = result.scalar_one_or_none()

    if not checkout:
        raise HTTPException(status_code=404, detail="Bulk checkout not found")

    response = BulkCheckoutResponse.model_validate(checkout)
    response.partner_name = checkout.partner.name if checkout.partner else None
    response.items_outstanding = checkout.total_items - checkout.items_returned - checkout.items_lost
    response.items = [BulkCheckoutItemResponse.model_validate(i) for i in checkout.items]
    return response


@router.post("/bulk-checkouts/{checkout_id}/items", response_model=list[BulkCheckoutItemResponse])
async def add_items_to_bulk_checkout(
    checkout_id: int,
    items_data: BulkCheckoutItemAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Add items to a bulk checkout by barcode."""
    # Get the bulk checkout
    checkout_query = select(BulkCheckout).where(BulkCheckout.id == checkout_id)
    checkout = (await db.execute(checkout_query)).scalar_one_or_none()

    if not checkout:
        raise HTTPException(status_code=404, detail="Bulk checkout not found")

    if checkout.status != BulkCheckoutStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="Cannot add items to a non-active checkout")

    added_items = []
    errors = []

    entries = items_data.get_entries()

    for entry in entries:
        # Find the item
        item_query = select(ItemCopy).options(
            selectinload(ItemCopy.catalog_item)
        ).where(ItemCopy.barcode == entry.barcode)
        item_copy = (await db.execute(item_query)).scalar_one_or_none()

        if not item_copy:
            errors.append(f"Item not found: {entry.barcode}")
            continue

        # Create bulk checkout item with condition assessment
        item = BulkCheckoutItem(
            bulk_checkout_id=checkout_id,
            item_copy_id=item_copy.id,
            barcode=entry.barcode,
            title=item_copy.catalog_item.title if item_copy.catalog_item else None,
            call_number=item_copy.catalog_item.call_number if item_copy.catalog_item else None,
            condition_out=entry.condition_out,
            replacement_cost=float(item_copy.replacement_cost) if item_copy.replacement_cost else None,
            status="checked_out"
        )
        db.add(item)
        added_items.append(item)

    # Update total count
    checkout.total_items += len(added_items)

    await db.commit()

    # Refresh all items
    for item in added_items:
        await db.refresh(item)

    if errors:
        logger.warning(f"Some items could not be added to bulk checkout {checkout_id}: {errors}")

    logger.info(f"Added {len(added_items)} items to bulk checkout {checkout_id}",
                extra={"checkout_id": checkout_id, "items_added": len(added_items)})

    return [BulkCheckoutItemResponse.model_validate(i) for i in added_items]


@router.post("/bulk-checkouts/{checkout_id}/return", response_model=BulkCheckoutItemResponse)
async def return_bulk_checkout_item(
    checkout_id: int,
    return_data: BulkCheckoutItemReturn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Return a single item from a bulk checkout."""
    # Find the item
    item_query = select(BulkCheckoutItem).where(
        BulkCheckoutItem.bulk_checkout_id == checkout_id,
        BulkCheckoutItem.barcode == return_data.barcode
    )
    item = (await db.execute(item_query)).scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found in this bulk checkout")

    if item.status != "checked_out":
        raise HTTPException(status_code=400, detail="Item is not currently checked out")

    # Update item
    item.status = "returned"
    item.returned_at = datetime.now()
    item.condition_in = return_data.condition
    item.damage_notes = return_data.damage_notes

    # Update bulk checkout counts
    checkout_query = select(BulkCheckout).where(BulkCheckout.id == checkout_id)
    checkout = (await db.execute(checkout_query)).scalar_one_or_none()

    if checkout:
        checkout.items_returned += 1
        if return_data.damage_notes:
            checkout.items_damaged += 1

        # Check if all items are returned
        if checkout.items_returned + checkout.items_lost >= checkout.total_items:
            checkout.status = BulkCheckoutStatus.RETURNED.value
            checkout.returned_date = date.today()
        elif checkout.items_returned > 0:
            checkout.status = BulkCheckoutStatus.PARTIALLY_RETURNED.value

    await db.commit()
    await db.refresh(item)

    logger.info(f"Returned item {return_data.barcode} from bulk checkout {checkout_id}",
                extra={"checkout_id": checkout_id, "barcode": return_data.barcode})

    response = BulkCheckoutItemResponse.model_validate(item)
    # Flag condition change when both condition_out and condition_in are recorded and differ
    if item.condition_out and item.condition_in and item.condition_out != item.condition_in:
        response.condition_changed = True
    return response


@router.post("/bulk-checkouts/{checkout_id}/return-all", response_model=BulkCheckoutResponse)
async def return_all_bulk_checkout_items(
    checkout_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Return all outstanding items from a bulk checkout."""
    # Get checkout with items
    checkout_query = select(BulkCheckout).options(
        selectinload(BulkCheckout.partner),
        selectinload(BulkCheckout.items)
    ).where(BulkCheckout.id == checkout_id)

    checkout = (await db.execute(checkout_query)).scalar_one_or_none()

    if not checkout:
        raise HTTPException(status_code=404, detail="Bulk checkout not found")

    # Return all checked out items
    items_returned = 0
    for item in checkout.items:
        if item.status == "checked_out":
            item.status = "returned"
            item.returned_at = datetime.now()
            items_returned += 1

    checkout.items_returned = items_returned + (checkout.items_returned or 0)
    checkout.status = BulkCheckoutStatus.RETURNED.value
    checkout.returned_date = date.today()

    await db.commit()
    await db.refresh(checkout)

    logger.info(f"Returned all items from bulk checkout {checkout_id}",
                extra={"checkout_id": checkout_id, "items_returned": items_returned})

    response = BulkCheckoutResponse.model_validate(checkout)
    response.partner_name = checkout.partner.name if checkout.partner else None
    response.items_outstanding = 0
    return response
