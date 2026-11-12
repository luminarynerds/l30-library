# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Inventory API routes.
Handles item copies, condition tracking, and inventory audits.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...core.branding import branding
from ...models.catalog import CatalogItem
from ...models.circulation import Checkout, CheckoutStatus
from ...models.inventory import (AcquisitionSource, AuditScan, ConditionChange,
                                 DamageType, InventoryAudit, ItemCondition,
                                 ItemCopy)
from ...models.lifecycle import ItemLifecycleEvent, LifecycleEventType
from ...models.shelf_reading import ShelfReadingSchedule
from ...models.user import User, UserRole
from ...schemas.inventory import (AuditCreate, AuditListResponse, AuditResponse,
                                  AuditScanCreate, AuditScanResponse,
                                  ConditionChangeCreate, ConditionChangeResponse,
                                  ItemCopyCreate, ItemCopyListResponse,
                                  ItemCopyResponse, ItemCopyUpdate,
                                  RepairRequest, WithdrawRequest)
from .auth import get_current_user
from .dependencies import require_staff
from .lifecycle import create_lifecycle_event

router = APIRouter(prefix="/inventory", tags=["inventory"])

# Valid condition transitions (from -> allowed to states)
# WITHDRAWN is a terminal state - items cannot be un-withdrawn
# Repairs (DAMAGED -> better condition) require the repair endpoint
VALID_CONDITION_TRANSITIONS: dict[ItemCondition, set[ItemCondition]] = {
    ItemCondition.NEW: {
        ItemCondition.GOOD,
        ItemCondition.FAIR,
        ItemCondition.POOR,
        ItemCondition.DAMAGED,
        ItemCondition.WITHDRAWN,
    },
    ItemCondition.GOOD: {
        ItemCondition.FAIR,
        ItemCondition.POOR,
        ItemCondition.DAMAGED,
        ItemCondition.WITHDRAWN,
    },
    ItemCondition.FAIR: {
        ItemCondition.POOR,
        ItemCondition.DAMAGED,
        ItemCondition.WITHDRAWN,
    },
    ItemCondition.POOR: {
        ItemCondition.DAMAGED,
        ItemCondition.WITHDRAWN,
    },
    ItemCondition.DAMAGED: {
        ItemCondition.WITHDRAWN,
    },
    ItemCondition.WITHDRAWN: set(),  # Terminal state - no transitions allowed
}

# Repair transitions (only via dedicated repair endpoint)
REPAIR_TRANSITIONS: dict[ItemCondition, set[ItemCondition]] = {
    ItemCondition.DAMAGED: {ItemCondition.GOOD, ItemCondition.FAIR, ItemCondition.POOR},
    ItemCondition.POOR: {ItemCondition.GOOD, ItemCondition.FAIR},
    ItemCondition.FAIR: {ItemCondition.GOOD},
}


def validate_condition_transition(
    current: ItemCondition, new: ItemCondition, allow_repair: bool = False
) -> None:
    # ItemCopy.condition is a String(50) column, so `current` arrives as a bare
    # str from the DB; coerce both ends to the enum so the .value formatting in
    # the error branches below does not blow up on an invalid transition.
    current = ItemCondition(current)
    new = ItemCondition(new)
    if current == new:
        return  # No change is always valid

    allowed = VALID_CONDITION_TRANSITIONS.get(current, set())

    # Check if this is a repair transition
    if new in REPAIR_TRANSITIONS.get(current, set()):
        if not allow_repair:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Condition improvement from {current.value} to {new.value} requires the repair endpoint",
            )
        return  # Repair transition is allowed

    if new not in allowed:
        if current == ItemCondition.WITHDRAWN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change condition of withdrawn items",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid condition transition from {current.value} to {new.value}",
        )


def generate_barcode() -> str:
    return f"{branding.CARD_PREFIX}-{uuid.uuid4().hex[:8].upper()}"


# ============ Dashboard ============


@router.get("/dashboard")
async def inventory_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Inventory dashboard with summary stats."""
    total_copies = (await db.execute(select(func.count(ItemCopy.id)))).scalar() or 0
    good_condition = (await db.execute(
        select(func.count(ItemCopy.id)).where(ItemCopy.condition == ItemCondition.GOOD)
    )).scalar() or 0
    withdrawn = (await db.execute(
        select(func.count(ItemCopy.id)).where(ItemCopy.condition == ItemCondition.WITHDRAWN)
    )).scalar() or 0
    return {
        "total_copies": total_copies,
        "good_condition": good_condition,
        "withdrawn": withdrawn,
    }


@router.get("/collection-intelligence")
async def collection_intelligence_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Aggregated collection intelligence dashboard.

    Returns condition breakdown, circulation stats, and recent lifecycle events
    for the collection dashboard overview.
    """
    # Condition breakdown (excluding withdrawn)
    condition_counts: dict[str, int] = {}
    for cond in [ItemCondition.NEW, ItemCondition.GOOD, ItemCondition.FAIR,
                 ItemCondition.POOR, ItemCondition.DAMAGED]:
        count = (await db.execute(
            select(func.count(ItemCopy.id)).where(ItemCopy.condition == cond)
        )).scalar() or 0
        condition_counts[cond.value] = count

    total_active = sum(condition_counts.values())

    # Items currently checked out
    in_circulation = (await db.execute(
        select(func.count(Checkout.id)).where(Checkout.status == CheckoutStatus.active)
    )).scalar() or 0

    circulation_pct = round((in_circulation / total_active * 100), 1) if total_active > 0 else 0

    # Poor + damaged count
    poor_damaged = condition_counts.get("poor", 0) + condition_counts.get("damaged", 0)

    # Shelf reading schedules overdue
    now = datetime.now(timezone.utc)
    overdue_reads = (await db.execute(
        select(func.count(ShelfReadingSchedule.id)).where(
            ShelfReadingSchedule.is_active == True,  # noqa: E712
            ShelfReadingSchedule.next_due_at <= now,
        )
    )).scalar() or 0

    # Recent lifecycle events (last 5)
    recent_result = await db.execute(
        select(
            ItemLifecycleEvent.id,
            ItemLifecycleEvent.event_type,
            ItemLifecycleEvent.description,
            ItemLifecycleEvent.created_at,
            ItemLifecycleEvent.item_copy_id,
            ItemCopy.barcode,
            CatalogItem.title,
        )
        .join(ItemCopy, ItemLifecycleEvent.item_copy_id == ItemCopy.id)
        .join(CatalogItem, ItemCopy.catalog_item_id == CatalogItem.id)
        .order_by(ItemLifecycleEvent.created_at.desc())
        .limit(5)
    )
    recent_events = [
        {
            "id": row.id,
            "event_type": row.event_type,
            "description": row.description,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "item_copy_id": row.item_copy_id,
            "barcode": row.barcode,
            "title": row.title,
        }
        for row in recent_result.all()
    ]

    return {
        "total_items": total_active,
        "circulation_pct": circulation_pct,
        "in_circulation": in_circulation,
        "poor_damaged": poor_damaged,
        "condition_breakdown": condition_counts,
        "overdue_shelf_reads": overdue_reads,
        "recent_events": recent_events,
    }


# ============ Item Copies ============


@router.get("/copies", response_model=ItemCopyListResponse)
async def list_copies(
    catalog_item_id: int | None = Query(None),
    condition: ItemCondition | None = Query(None),
    location: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List item copies with optional filters"""
    await require_staff(current_user)

    query = select(ItemCopy).options(selectinload(ItemCopy.catalog_item))
    count_query = select(func.count(ItemCopy.id))

    if catalog_item_id:
        query = query.where(ItemCopy.catalog_item_id == catalog_item_id)
        count_query = count_query.where(ItemCopy.catalog_item_id == catalog_item_id)

    if condition:
        query = query.where(ItemCopy.condition == condition)
        count_query = count_query.where(ItemCopy.condition == condition)

    if location:
        safe_location = location.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(ItemCopy.location.ilike(f"%{safe_location}%"))
        count_query = count_query.where(ItemCopy.location.ilike(f"%{safe_location}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(ItemCopy.created_at.desc())

    result = await db.execute(query)
    copies = result.scalars().all()

    items = []
    for copy in copies:
        item_dict = ItemCopyResponse.model_validate(copy).model_dump()
        item_dict["catalog_title"] = (
            copy.catalog_item.title if copy.catalog_item else None
        )
        item_dict["catalog_author"] = (
            copy.catalog_item.author if copy.catalog_item else None
        )
        items.append(item_dict)

    return ItemCopyListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/copies/{copy_id}", response_model=ItemCopyResponse)
async def get_copy(
    copy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get item copy details"""
    await require_staff(current_user)

    result = await db.execute(
        select(ItemCopy)
        .where(ItemCopy.id == copy_id)
        .options(selectinload(ItemCopy.catalog_item))
    )
    copy = result.scalar_one_or_none()
    if not copy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Copy not found")

    response = ItemCopyResponse.model_validate(copy)
    response.catalog_title = copy.catalog_item.title if copy.catalog_item else None
    response.catalog_author = copy.catalog_item.author if copy.catalog_item else None
    return response


@router.post("/copies", response_model=ItemCopyResponse, status_code=status.HTTP_201_CREATED)
async def create_copy(
    copy_in: ItemCopyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new item copy"""
    await require_staff(current_user)

    # Verify catalog item exists
    cat_result = await db.execute(
        select(CatalogItem).where(CatalogItem.id == copy_in.catalog_item_id)
    )
    if not cat_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")

    # Auto-generate barcode if not provided
    barcode = copy_in.barcode or generate_barcode()

    # Check barcode uniqueness
    existing = await db.execute(select(ItemCopy).where(ItemCopy.barcode == barcode))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Barcode already exists")

    # Determine copy number - lock existing copies to prevent duplicate copy numbers
    # from concurrent creates. We lock the actual rows, not just query an aggregate.
    existing_copies_result = await db.execute(
        select(ItemCopy)
        .where(ItemCopy.catalog_item_id == copy_in.catalog_item_id)
        .with_for_update()
    )
    existing_copies = existing_copies_result.scalars().all()
    copy_number = len(existing_copies) + 1

    copy = ItemCopy(
        **copy_in.model_dump(exclude={"barcode", "copy_number"}),
        barcode=barcode,
        copy_number=copy_number,
    )
    db.add(copy)
    await db.flush()  # Flush to get the copy ID

    # Create lifecycle event
    await create_lifecycle_event(
        db=db,
        item_copy_id=copy.id,
        event_type=LifecycleEventType.COPY_CREATED,
        description=f"Item copy created with barcode {barcode}",
        performed_by_id=current_user.id,
    )

    await db.commit()
    await db.refresh(copy, attribute_names=["catalog_item"])
    response = ItemCopyResponse.model_validate(copy)
    response.catalog_title = copy.catalog_item.title if copy.catalog_item else None
    response.catalog_author = copy.catalog_item.author if copy.catalog_item else None
    return response


@router.patch("/copies/{copy_id}", response_model=ItemCopyResponse)
async def update_copy(
    copy_id: int,
    copy_in: ItemCopyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an item copy"""
    await require_staff(current_user)

    copy = await get_or_404(db, ItemCopy, copy_id, "Copy not found")

    # Track if condition is being changed for audit trail
    update_data = copy_in.model_dump(exclude_unset=True)
    previous_condition = copy.condition
    new_condition = update_data.get("condition")
    condition_changed = new_condition is not None and new_condition != previous_condition

    # Validate condition transition if changing
    if condition_changed:
        validate_condition_transition(previous_condition, new_condition, allow_repair=False)

    # Apply updates
    for field, value in update_data.items():
        setattr(copy, field, value)

    # Create audit trail if condition changed
    if condition_changed:

        # Log the condition change
        change = ConditionChange(
            item_copy_id=copy_id,
            previous_condition=previous_condition,
            new_condition=new_condition,
            damage_description="Condition updated via item edit",
            reported_by_id=current_user.id,
        )
        db.add(change)

        # Create lifecycle event
        event_type = (
            LifecycleEventType.DAMAGED
            if new_condition == ItemCondition.DAMAGED
            else LifecycleEventType.CONDITION_CHANGED
        )
        await create_lifecycle_event(
            db=db,
            item_copy_id=copy_id,
            event_type=event_type,
            description=f"Condition changed from {str(previous_condition)} to {str(new_condition)}",
            metadata={
                "from": str(previous_condition),
                "to": str(new_condition),
                "source": "item_update",
            },
            performed_by_id=current_user.id,
        )

    await db.commit()
    await db.refresh(copy)
    return copy


@router.post("/copies/{copy_id}/withdraw", response_model=ItemCopyResponse)
async def withdraw_copy(
    copy_id: int,
    request: WithdrawRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Withdraw an item copy from circulation"""
    await require_staff(current_user)

    copy = await get_or_404(db, ItemCopy, copy_id, "Copy not found")

    # Capture previous condition before modifying
    previous_condition = copy.condition

    # Reject if already withdrawn
    if previous_condition == ItemCondition.WITHDRAWN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item is already withdrawn",
        )

    # Validate that item can be withdrawn
    validate_condition_transition(
        previous_condition, ItemCondition.WITHDRAWN, allow_repair=False
    )

    # Log the condition change
    change = ConditionChange(
        item_copy_id=copy_id,
        previous_condition=previous_condition,
        new_condition=ItemCondition.WITHDRAWN,
        damage_description=request.reason,
        reported_by_id=current_user.id,
    )
    db.add(change)

    copy.condition = ItemCondition.WITHDRAWN
    copy.notes = (copy.notes or "") + f"\nWithdrawn: {request.reason}"

    # Create lifecycle event
    await create_lifecycle_event(
        db=db,
        item_copy_id=copy_id,
        event_type=LifecycleEventType.CONDITION_CHANGED,
        description=f"Item withdrawn from circulation: {request.reason}",
        metadata={"reason": request.reason, "previous_condition": str(previous_condition)},
        performed_by_id=current_user.id,
    )

    await db.commit()
    await db.refresh(copy)
    return copy


@router.post("/copies/{copy_id}/repair", response_model=ItemCopyResponse)
async def repair_copy(
    copy_id: int,
    request: RepairRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Repair an item copy, improving its condition.
    This is the only way to transition an item to a better condition state.
    """
    await require_staff(current_user)

    copy = await get_or_404(db, ItemCopy, copy_id, "Copy not found")

    # Capture previous condition
    previous_condition = copy.condition

    # Validate this is a valid repair transition
    validate_condition_transition(
        previous_condition, request.new_condition, allow_repair=True
    )

    # Ensure this is actually a repair (improvement in condition)
    if request.new_condition not in REPAIR_TRANSITIONS.get(previous_condition, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repair endpoint is only for condition improvements. "
            f"Cannot repair from {str(previous_condition)} to {request.new_condition}",
        )

    # Log the condition change with repair details
    change = ConditionChange(
        item_copy_id=copy_id,
        previous_condition=previous_condition,
        new_condition=request.new_condition,
        repair_notes=request.repair_notes,
        repair_cost=request.repair_cost,
        repaired_at=datetime.now(timezone.utc),
        reported_by_id=current_user.id,
    )
    db.add(change)

    # Update the copy condition
    copy.condition = request.new_condition

    # Create lifecycle event
    await create_lifecycle_event(
        db=db,
        item_copy_id=copy_id,
        event_type=LifecycleEventType.REPAIRED,
        description=f"Item repaired from {str(previous_condition)} to {request.new_condition}",
        metadata={
            "from": str(previous_condition),
            "to": str(request.new_condition),
            "repair_notes": request.repair_notes,
            "repair_cost": str(request.repair_cost) if request.repair_cost else None,
        },
        performed_by_id=current_user.id,
    )

    await db.commit()
    await db.refresh(copy)
    return copy


# ============ Condition Changes ============


@router.get(
    "/copies/{copy_id}/condition-history", response_model=list[ConditionChangeResponse]
)
async def get_condition_history(
    copy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get condition change history for an item copy"""
    await require_staff(current_user)

    result = await db.execute(
        select(ConditionChange)
        .where(ConditionChange.item_copy_id == copy_id)
        .options(selectinload(ConditionChange.reported_by))
        .order_by(ConditionChange.created_at.desc())
    )
    changes = result.scalars().all()

    items = []
    for change in changes:
        item_dict = ConditionChangeResponse.model_validate(change).model_dump()
        item_dict["reported_by_name"] = (
            change.reported_by.full_name if change.reported_by else None
        )
        items.append(item_dict)
    return items


@router.post("/copies/{copy_id}/condition", response_model=ConditionChangeResponse, status_code=status.HTTP_201_CREATED)
async def log_condition_change(
    copy_id: int,
    change_in: ConditionChangeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log a condition change for an item copy"""
    await require_staff(current_user)

    copy = await get_or_404(db, ItemCopy, copy_id, "Copy not found")

    # Capture previous condition before modifying
    previous_condition = copy.condition

    # Validate the condition transition
    validate_condition_transition(
        previous_condition, change_in.new_condition, allow_repair=False
    )

    change = ConditionChange(
        item_copy_id=copy_id,
        previous_condition=previous_condition,
        **change_in.model_dump(),
        reported_by_id=current_user.id,
    )
    db.add(change)

    # Update copy condition
    copy.condition = change_in.new_condition

    # Create lifecycle event
    event_type = (
        LifecycleEventType.DAMAGED
        if change_in.new_condition == ItemCondition.DAMAGED
        else LifecycleEventType.CONDITION_CHANGED
    )
    await create_lifecycle_event(
        db=db,
        item_copy_id=copy_id,
        event_type=event_type,
        description=f"Condition changed from {str(previous_condition)} to {str(change_in.new_condition)}",
        metadata={
            "from": str(previous_condition),
            "to": str(change_in.new_condition),
            "damage_type": (
                str(change_in.damage_type) if change_in.damage_type else None
            ),
            "description": change_in.damage_description,
        },
        performed_by_id=current_user.id,
    )

    await db.commit()
    await db.refresh(change)
    return change


# ============ Inventory Audits ============


@router.get("/audits", response_model=AuditListResponse)
async def list_audits(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, pattern="^(in_progress|completed)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List inventory audits"""
    await require_staff(current_user)

    query = select(InventoryAudit).options(selectinload(InventoryAudit.created_by))
    count_query = select(func.count(InventoryAudit.id))

    if status == "in_progress":
        query = query.where(InventoryAudit.completed_at.is_(None))
        count_query = count_query.where(InventoryAudit.completed_at.is_(None))
    elif status == "completed":
        query = query.where(InventoryAudit.completed_at.is_not(None))
        count_query = count_query.where(InventoryAudit.completed_at.is_not(None))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = (
        query.offset(offset).limit(per_page).order_by(InventoryAudit.started_at.desc())
    )

    result = await db.execute(query)
    audits = result.scalars().all()

    items = []
    for audit in audits:
        item_dict = AuditResponse.model_validate(audit).model_dump()
        item_dict["created_by_name"] = (
            audit.created_by.full_name if audit.created_by else None
        )
        items.append(item_dict)

    return AuditListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/audits", response_model=AuditResponse, status_code=status.HTTP_201_CREATED)
async def create_audit(
    audit_in: AuditCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a new inventory audit"""
    await require_staff(current_user)

    # Check for an active (uncompleted) audit
    active_query = select(InventoryAudit).where(InventoryAudit.completed_at.is_(None))
    if audit_in.location_filter:
        active_query = active_query.where(
            InventoryAudit.location_filter == audit_in.location_filter
        )
    active_result = await db.execute(active_query)
    if active_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active inventory audit is already in progress",
        )

    # Count expected items (exclude withdrawn and currently checked-out copies)
    checked_out_ids = (
        select(Checkout.item_copy_id)
        .where(Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
            Checkout.item_copy_id.is_not(None),)
        .correlate(None)
        .scalar_subquery()
    )
    count_query = select(func.count(ItemCopy.id)).where(
        ItemCopy.condition != ItemCondition.WITHDRAWN,
        ItemCopy.id.not_in(checked_out_ids),
    )
    if audit_in.location_filter:
        safe_loc = audit_in.location_filter.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        count_query = count_query.where(
            ItemCopy.location.ilike(f"%{safe_loc}%")
        )

    count_result = await db.execute(count_query)
    expected = count_result.scalar() or 0

    audit = InventoryAudit(
        **audit_in.model_dump(),
        items_expected=expected,
        created_by_id=current_user.id,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)
    return audit


@router.get("/audits/{audit_id}", response_model=AuditResponse)
async def get_audit(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get audit details"""
    await require_staff(current_user)

    result = await db.execute(
        select(InventoryAudit)
        .where(InventoryAudit.id == audit_id)
        .options(selectinload(InventoryAudit.created_by))
    )
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")

    response = AuditResponse.model_validate(audit)
    response.created_by_name = audit.created_by.full_name if audit.created_by else None
    return response


@router.get("/audits/{audit_id}/scan", response_model=dict)
async def get_scan_status(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current scan status for an audit."""
    await require_staff(current_user)

    result = await db.execute(
        select(InventoryAudit)
        .where(InventoryAudit.id == audit_id)
    )
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")

    return {
        "audit_id": audit.id,
        "items_expected": audit.items_expected,
        "items_found": audit.items_found,
        "items_missing": audit.items_expected - audit.items_found,
        "is_completed": audit.completed_at is not None,
        "completed_at": audit.completed_at,
    }


@router.post("/audits/{audit_id}/scan", response_model=AuditScanResponse, status_code=status.HTTP_201_CREATED)
async def scan_item(
    audit_id: int,
    scan_in: AuditScanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Scan an item during an audit"""
    await require_staff(current_user)

    # Verify audit exists and is active - lock to prevent concurrent stat updates
    audit_result = await db.execute(
        select(InventoryAudit)
        .where(InventoryAudit.id == audit_id)
        .with_for_update()
    )
    audit = audit_result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    if audit.completed_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audit is already completed")

    # Find item by barcode
    copy_result = await db.execute(
        select(ItemCopy)
        .where(ItemCopy.barcode == scan_in.barcode)
        .options(selectinload(ItemCopy.catalog_item))
    )
    copy = copy_result.scalar_one_or_none()
    if not copy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found with this barcode")

    # Check if already scanned - use FOR UPDATE to prevent duplicate scans
    # from concurrent requests scanning the same item
    existing = await db.execute(
        select(AuditScan)
        .where(AuditScan.audit_id == audit_id, AuditScan.item_copy_id == copy.id)
        .with_for_update()
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Item already scanned in this audit"
        )

    # Check if misplaced
    is_misplaced = False
    if scan_in.found_at_location and copy.location:
        is_misplaced = scan_in.found_at_location.lower() != copy.location.lower()

    scan = AuditScan(
        audit_id=audit_id,
        item_copy_id=copy.id,
        found_at_location=scan_in.found_at_location,
        is_misplaced=is_misplaced,
        scanned_by_id=current_user.id,
    )
    db.add(scan)

    # Update audit stats
    audit.items_found += 1
    if is_misplaced:
        audit.items_misplaced += 1

    # Create lifecycle event
    event_description = "Scanned during inventory audit"
    if is_misplaced:
        event_description += (
            f" - found at {scan_in.found_at_location} (expected: {copy.location})"
        )

    await create_lifecycle_event(
        db=db,
        item_copy_id=copy.id,
        event_type=LifecycleEventType.INVENTORIED,
        description=event_description,
        metadata={
            "audit_id": audit_id,
            "found_at": scan_in.found_at_location,
            "expected_at": copy.location,
            "is_misplaced": is_misplaced,
        },
        performed_by_id=current_user.id,
        related_audit_id=audit_id,
    )

    await db.commit()
    await db.refresh(scan)

    response = AuditScanResponse.model_validate(scan)
    response.barcode = copy.barcode
    response.catalog_title = copy.catalog_item.title if copy.catalog_item else None
    return response


@router.get("/audits/{audit_id}/complete", response_model=dict)
async def get_completion_status(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if an audit can be completed."""
    await require_staff(current_user)

    result = await db.execute(
        select(InventoryAudit)
        .where(InventoryAudit.id == audit_id)
    )
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")

    return {
        "audit_id": audit.id,
        "is_completed": audit.completed_at is not None,
        "completed_at": audit.completed_at,
        "items_expected": audit.items_expected,
        "items_found": audit.items_found,
        "can_complete": audit.completed_at is None,
    }


@router.post("/audits/{audit_id}/complete", response_model=AuditResponse)
async def complete_audit(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete an inventory audit"""
    await require_staff(current_user)

    result = await db.execute(
        select(InventoryAudit)
        .where(InventoryAudit.id == audit_id)
        .with_for_update()
        .options(selectinload(InventoryAudit.created_by))
    )
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    if audit.completed_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audit already completed")

    audit.completed_at = datetime.now(timezone.utc)
    audit.items_missing = max(0, audit.items_expected - audit.items_found)

    await db.commit()
    await db.refresh(audit)

    response = AuditResponse.model_validate(audit)
    response.created_by_name = audit.created_by.full_name if audit.created_by else None
    return response


# ============ Barcode Lookup ============


@router.get("/lookup/{barcode}", response_model=ItemCopyResponse)
async def lookup_barcode(
    barcode: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Look up an item by barcode"""
    await require_staff(current_user)

    result = await db.execute(
        select(ItemCopy)
        .where(ItemCopy.barcode == barcode)
        .options(selectinload(ItemCopy.catalog_item))
    )
    copy = result.scalar_one_or_none()
    if not copy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    response = ItemCopyResponse.model_validate(copy)
    response.catalog_title = copy.catalog_item.title if copy.catalog_item else None
    response.catalog_author = copy.catalog_item.author if copy.catalog_item else None
    return response


@router.get("/copies/{copy_id}/condition")
async def get_copies_condition_info(
    copy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get information about logging condition changes for an item copy.

    Returns current condition, valid transitions, and endpoint metadata.
    """
    await require_staff(current_user)

    # Get the copy
    result = await db.execute(
        select(ItemCopy)
        .where(ItemCopy.id == copy_id)
        .options(selectinload(ItemCopy.catalog_item))
    )
    copy = result.scalar_one_or_none()

    if not copy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Copy not found")

    # Get condition history count
    history_count_result = await db.execute(
        select(func.count(ConditionChange.id)).where(ConditionChange.item_copy_id == copy_id)
    )
    history_count = history_count_result.scalar() or 0

    # Determine valid transitions from current condition
    valid_transitions = list(VALID_CONDITION_TRANSITIONS.get(copy.condition, set()))

    return {
        "endpoint": f"POST /inventory/copies/{copy_id}/condition",
        "description": "Log a condition change for this item copy",
        "method": "POST",
        "item_copy": {
            "id": copy.id,
            "barcode": copy.barcode,
            "current_condition": str(copy.condition),
            "location": copy.location,
            "catalog_title": copy.catalog_item.title if copy.catalog_item else None,
        },
        "valid_transitions": [c.value for c in valid_transitions],
        "condition_history_count": history_count,
        "required_fields": ["new_condition"],
        "optional_fields": ["damage_type", "damage_description", "repair_notes", "repair_cost"],
        "notes": [
            "Repairs (condition improvements) must use POST /copies/{copy_id}/repair",
            "Withdrawn items cannot be changed to other conditions",
            "Condition changes create an audit trail",
        ],
        "all_conditions": [c.value for c in ItemCondition],
    }



@router.get("/copies/{copy_id}/repair")
async def get_copies_repair_info(
    copy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get information about repairing an item copy.

    Returns current condition, valid repair transitions, and repair endpoint metadata.
    """
    await require_staff(current_user)

    # Get the copy
    result = await db.execute(
        select(ItemCopy)
        .where(ItemCopy.id == copy_id)
        .options(selectinload(ItemCopy.catalog_item))
    )
    copy = result.scalar_one_or_none()

    if not copy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Copy not found")

    # Determine valid repair transitions from current condition
    repair_options = list(REPAIR_TRANSITIONS.get(copy.condition, set()))
    can_repair = len(repair_options) > 0

    # Get recent condition changes
    recent_changes_result = await db.execute(
        select(ConditionChange)
        .where(ConditionChange.item_copy_id == copy_id)
        .order_by(ConditionChange.created_at.desc())
        .limit(5)
    )
    recent_changes = recent_changes_result.scalars().all()

    return {
        "endpoint": f"POST /inventory/copies/{copy_id}/repair",
        "description": "Repair an item copy, improving its condition",
        "method": "POST",
        "item_copy": {
            "id": copy.id,
            "barcode": copy.barcode,
            "current_condition": str(copy.condition),
            "location": copy.location,
            "catalog_title": copy.catalog_item.title if copy.catalog_item else None,
        },
        "can_repair": can_repair,
        "valid_repair_transitions": [c.value for c in repair_options],
        "required_fields": ["new_condition", "repair_notes"],
        "optional_fields": ["repair_cost"],
        "recent_condition_changes": [
            {
                "from": str(change.previous_condition),
                "to": str(change.new_condition),
                "date": change.created_at.isoformat(),
                "is_repair": change.repair_notes is not None,
            }
            for change in recent_changes
        ],
        "notes": [
            "Repairs can only improve condition (e.g., DAMAGED -> GOOD)",
            "This is the only way to improve item condition",
            "Regular condition changes use POST /copies/{copy_id}/condition",
        ],
    }



# ============ Mobile Scanning Endpoints ============


@router.get("/sections")
async def list_sections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all inventory sections (distinct locations) with item counts."""
    await require_staff(current_user)

    result = await db.execute(
        select(
            ItemCopy.location,
            func.count(ItemCopy.id).label("item_count"),
        )
        .where(
            ItemCopy.condition != ItemCondition.WITHDRAWN,
            ItemCopy.location.isnot(None),
            ItemCopy.location != "",
        )
        .group_by(ItemCopy.location)
        .order_by(ItemCopy.location)
    )
    rows = result.all()

    sections = []
    for row in rows:
        sections.append({
            "location": row.location,
            "item_count": row.item_count,
        })

    return {"sections": sections, "total_sections": len(sections)}


@router.get("/sections/{location}/items")
async def get_section_items(
    location: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all items in a section, ordered by call number for shelf-walking.
    Returns items in the order they should appear on shelves.
    """
    await require_staff(current_user)

    safe_location = location.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    result = await db.execute(
        select(ItemCopy)
        .where(
            ItemCopy.location.ilike(f"%{safe_location}%"),
            ItemCopy.condition != ItemCondition.WITHDRAWN,
        )
        .options(selectinload(ItemCopy.catalog_item))
        .order_by(ItemCopy.barcode)
    )
    copies = result.scalars().all()

    items = []
    for copy in copies:
        items.append({
            "id": copy.id,
            "barcode": copy.barcode,
            "copy_number": copy.copy_number,
            "location": copy.location,
            "condition": str(copy.condition),
            "catalog_title": copy.catalog_item.title if copy.catalog_item else None,
            "catalog_author": copy.catalog_item.author if copy.catalog_item else None,
            "call_number": getattr(copy.catalog_item, "call_number", None) if copy.catalog_item else None,
        })

    return {"items": items, "total": len(items), "location": location}


@router.post("/audits/{audit_id}/scan/batch", response_model=dict)
async def batch_scan_items(
    audit_id: int,
    scans: list[AuditScanCreate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Batch scan items for an audit - used by mobile scanner to sync offline scans.
    Returns results for each scan attempt.
    """
    await require_staff(current_user)

    # Verify audit
    audit_result = await db.execute(
        select(InventoryAudit)
        .where(InventoryAudit.id == audit_id)
        .with_for_update()
    )
    audit = audit_result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    if audit.completed_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audit is already completed")

    results = []
    for scan_in in scans:
        # Find item by barcode
        copy_result = await db.execute(
            select(ItemCopy)
            .where(ItemCopy.barcode == scan_in.barcode)
            .options(selectinload(ItemCopy.catalog_item))
        )
        copy = copy_result.scalar_one_or_none()
        if not copy:
            results.append({
                "barcode": scan_in.barcode,
                "status": "not_found",
                "message": "Item not found",
            })
            continue

        # Check if already scanned - use FOR UPDATE to prevent duplicate scans
        existing = await db.execute(
            select(AuditScan)
            .where(AuditScan.audit_id == audit_id, AuditScan.item_copy_id == copy.id)
            .with_for_update()
        )
        if existing.scalar_one_or_none():
            results.append({
                "barcode": scan_in.barcode,
                "status": "already_scanned",
                "title": copy.catalog_item.title if copy.catalog_item else None,
                "message": "Already scanned",
            })
            continue

        # Check if misplaced
        is_misplaced = False
        if scan_in.found_at_location and copy.location:
            is_misplaced = scan_in.found_at_location.lower() != copy.location.lower()

        scan = AuditScan(
            audit_id=audit_id,
            item_copy_id=copy.id,
            found_at_location=scan_in.found_at_location,
            is_misplaced=is_misplaced,
            scanned_by_id=current_user.id,
        )
        db.add(scan)

        audit.items_found += 1
        if is_misplaced:
            audit.items_misplaced += 1

        results.append({
            "barcode": scan_in.barcode,
            "status": "found",
            "title": copy.catalog_item.title if copy.catalog_item else None,
            "is_misplaced": is_misplaced,
            "expected_location": copy.location,
            "message": "Scanned successfully",
        })

    await db.commit()

    return {
        "audit_id": audit_id,
        "results": results,
        "total_processed": len(results),
        "total_found": sum(1 for r in results if r["status"] == "found"),
        "total_errors": sum(1 for r in results if r["status"] == "not_found"),
        "total_duplicates": sum(1 for r in results if r["status"] == "already_scanned"),
        "audit_progress": {
            "items_expected": audit.items_expected,
            "items_found": audit.items_found,
            "items_missing": audit.items_expected - audit.items_found,
            "items_misplaced": audit.items_misplaced,
            "completion_pct": round((audit.items_found / max(audit.items_expected, 1)) * 100, 1),
        },
    }


@router.get("/copies/{copy_id}/withdraw")
async def get_copies_withdraw_info(
    copy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get information about withdrawing an item copy from circulation.

    Returns item details and withdrawal endpoint metadata.
    """
    await require_staff(current_user)

    # Get the copy
    result = await db.execute(
        select(ItemCopy)
        .where(ItemCopy.id == copy_id)
        .options(selectinload(ItemCopy.catalog_item))
    )
    copy = result.scalar_one_or_none()

    if not copy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Copy not found")

    # Check if already withdrawn
    is_withdrawn = copy.condition == ItemCondition.WITHDRAWN
    can_withdraw = not is_withdrawn

    # Get catalog item info
    catalog_info = None
    if copy.catalog_item:
        # Count other copies
        other_copies_result = await db.execute(
            select(func.count(ItemCopy.id)).where(
                ItemCopy.catalog_item_id == copy.catalog_item_id,
                ItemCopy.id != copy_id,
                ItemCopy.condition != ItemCondition.WITHDRAWN,
            )
        )
        other_copies = other_copies_result.scalar() or 0

        catalog_info = {
            "title": copy.catalog_item.title,
            "author": copy.catalog_item.author,
            "other_active_copies": other_copies,
        }

    return {
        "endpoint": f"POST /inventory/copies/{copy_id}/withdraw",
        "description": "Withdraw an item copy from circulation permanently",
        "method": "POST",
        "item_copy": {
            "id": copy.id,
            "barcode": copy.barcode,
            "current_condition": str(copy.condition),
            "location": copy.location,
            "replacement_cost": str(copy.replacement_cost) if copy.replacement_cost else None,
        },
        "catalog_item": catalog_info,
        "is_withdrawn": is_withdrawn,
        "can_withdraw": can_withdraw,
        "required_fields": ["reason"],
        "notes": [
            "Withdrawal is permanent - items cannot be un-withdrawn",
            "Use this for lost, severely damaged, or outdated items",
            "The item will be removed from circulation and marked for disposal",
        ],
        "common_reasons": [
            "Lost or missing",
            "Damaged beyond repair",
            "Outdated or superseded",
            "Poor condition",
            "Low circulation",
            "Part of weeding project",
        ],
    }

