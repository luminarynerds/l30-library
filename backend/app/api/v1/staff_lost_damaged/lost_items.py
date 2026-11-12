# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Lost Item Endpoints

Handles marking items as lost, processing found items, writing off lost items,
auto-converting overdue items, bulk operations, and related info endpoints.
"""

from app.core.logging import get_logger
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.inventory import ItemCondition
from ....models.lost_damaged import LostItemStatus, LostItemType
from ....models.user import User
from ....schemas.lost_damaged import (
    MarkItemLostRequest,
    LostItemWorkflowResponse,
    LostItemRecordResponse,
    ProcessFoundItemRequest,
    FoundItemResponse,
    LostItemListResponse,
    AutoConvertOverdueRequest,
    AutoConvertOverdueResponse,
    ReplacementCostBreakdownResponse,
)
from ....services.lost_item_workflow_service import LostItemWorkflowService
from ..auth import get_current_user
from ..dependencies import require_staff
from .utils import convert_lost_record, handle_enum_validation, handle_service_error

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Inline Schemas for Bulk Operations
# ============================================================================

class BulkWriteOffRequest(BaseModel):
    lost_record_ids: List[int] = Field(..., min_length=1, max_length=100)
    notes: Optional[str] = Field(None, description="Notes for all write-offs")


class BulkWriteOffResponse(BaseModel):
    success_count: int
    failure_count: int
    results: List[dict]


class BulkMarkLostRequest(BaseModel):
    checkout_ids: List[int] = Field(..., min_length=1, max_length=100)
    lost_type: str = Field("lost_by_patron", description="Type of loss")
    notes: Optional[str] = Field(None, description="Notes for all lost items")
    send_notifications: bool = Field(False, description="Send notifications to patrons (opt-in for bulk)")
    dry_run: bool = Field(False, description="Preview impact without making changes")


class BulkMarkLostResponse(BaseModel):
    success_count: int
    failure_count: int
    total_charges: Decimal
    notifications_sent: int
    results: List[dict]


class LostItemClassification(BaseModel):
    value: str
    label: str
    description: str


# ============================================================================
# Lost Item Endpoints
# ============================================================================

@router.post("/lost/{checkout_id}/mark-lost", response_model=LostItemWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def mark_item_lost(
    checkout_id: int,
    request: MarkItemLostRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark an item as lost.

    Creates a lost item record, calculates replacement cost,
    creates fine for patron, and sends notification.
    """
    lost_type = handle_enum_validation(LostItemType, request.lost_type, "lost type")

    service = LostItemWorkflowService(db)
    result = await service.mark_item_lost(
        checkout_id=checkout_id,
        lost_type=lost_type,
        reported_by=staff_user,
        report_notes=request.report_notes,
        custom_replacement_cost=request.custom_replacement_cost,
        send_notification=request.send_notification,
    )

    handle_service_error(result)

    record_response = None
    if result.lost_item_record:
        record_response = convert_lost_record(result.lost_item_record)

    cost_response = None
    if result.replacement_cost:
        cost_response = ReplacementCostBreakdownResponse(
            item_price=result.replacement_cost.item_price,
            processing_fee=result.replacement_cost.processing_fee,
            total=result.replacement_cost.total,
            source=result.replacement_cost.source,
        )

    return LostItemWorkflowResponse(
        success=True,
        message=result.message,
        lost_item_record=record_response,
        replacement_cost=cost_response,
        fine_id=result.fine.id if result.fine else None,
        notification_sent=result.notification_sent,
    )


@router.post("/lost/{lost_record_id}/mark-found", response_model=FoundItemResponse)
async def process_found_item(
    lost_record_id: int,
    request: ProcessFoundItemRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Process a found item that was previously marked lost.

    Calculates credit for patron, restores item to circulation,
    and sends notification.
    """
    condition = handle_enum_validation(ItemCondition, request.found_condition, "condition")

    service = LostItemWorkflowService(db)
    result = await service.process_found_item(
        lost_record_id=lost_record_id,
        found_by=staff_user,
        found_condition=condition,
        resolution_notes=request.resolution_notes,
        send_notification=request.send_notification,
    )

    handle_service_error(result)

    record_response = None
    if result.lost_item_record:
        record_response = convert_lost_record(result.lost_item_record)

    return FoundItemResponse(
        success=True,
        message=result.message,
        lost_item_record=record_response,
        credit_amount=result.credit_amount,
        item_restored=result.item_restored,
        notification_sent=result.notification_sent,
    )


@router.post("/lost/{record_id}/write-off", response_model=LostItemWorkflowResponse)
async def write_off_lost_item(
    record_id: int,
    notes: Optional[str] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Write off a lost item that will not be recovered."""
    service = LostItemWorkflowService(db)
    result = await service.write_off_lost_item(
        lost_record_id=record_id,
        written_off_by=staff_user,
        notes=notes,
    )

    handle_service_error(result)

    record_response = None
    if result.lost_item_record:
        record_response = convert_lost_record(result.lost_item_record)

    return LostItemWorkflowResponse(
        success=True,
        message=result.message,
        lost_item_record=record_response,
        notification_sent=False,
    )


@router.get("/lost-items", response_model=LostItemListResponse)
async def list_lost_items(
    status: Optional[str] = Query(None, description="Filter by status"),
    lost_type: Optional[str] = Query(None, description="Filter by lost type"),
    patron_id: Optional[int] = Query(None, description="Filter by patron"),
    days_ago: Optional[int] = Query(None, ge=1, description="Items reported within X days"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List lost item records with filtering."""
    status_enum = None
    if status:
        status_enum = handle_enum_validation(LostItemStatus, status, "status")

    lost_type_enum = None
    if lost_type:
        lost_type_enum = handle_enum_validation(LostItemType, lost_type, "lost type")

    service = LostItemWorkflowService(db)
    items, total = await service.get_lost_items(
        status=status_enum,
        lost_type=lost_type_enum,
        patron_id=patron_id,
        days_ago=days_ago,
        limit=limit,
        offset=offset,
    )

    return LostItemListResponse(
        items=[convert_lost_record(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/lost/auto-convert", response_model=AutoConvertOverdueResponse)
async def auto_convert_overdue_to_lost(
    request: AutoConvertOverdueRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Automatically convert overdue items to lost.

    Use dry_run=True to preview what would be converted without making changes.
    """
    service = LostItemWorkflowService(db)
    results = await service.auto_convert_overdue_items(
        threshold_days=request.threshold_days,
        dry_run=request.dry_run,
    )

    return AutoConvertOverdueResponse(
        processed_count=len(results),
        dry_run=request.dry_run,
        results=[
            LostItemWorkflowResponse(
                success=r.success,
                message=r.message,
                lost_item_record=convert_lost_record(r.lost_item_record) if r.lost_item_record else None,
                replacement_cost=ReplacementCostBreakdownResponse(
                    item_price=r.replacement_cost.item_price,
                    processing_fee=r.replacement_cost.processing_fee,
                    total=r.replacement_cost.total,
                    source=r.replacement_cost.source,
                ) if r.replacement_cost else None,
                fine_id=r.fine.id if r.fine else None,
                notification_sent=r.notification_sent,
            )
            for r in results
        ],
    )


# ============================================================================
# Bulk Operations
# ============================================================================

@router.post("/bulk/write-off", response_model=BulkWriteOffResponse)
async def bulk_write_off_lost_items(
    request: BulkWriteOffRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk write off multiple lost items at once.

    Useful for periodic cleanup of long-lost items that will not be recovered.
    """
    service = LostItemWorkflowService(db)
    results = []
    success_count = 0
    failure_count = 0

    for record_id in request.lost_record_ids:
        try:
            result = await service.write_off_lost_item(
                lost_record_id=record_id,
                written_off_by=staff_user,
                notes=request.notes,
            )
            if result.success:
                success_count += 1
                results.append({
                    "record_id": record_id,
                    "success": True,
                    "message": "Written off successfully"
                })
            else:
                failure_count += 1
                results.append({
                    "record_id": record_id,
                    "success": False,
                    "message": result.message
                })
        except Exception as e:  # noqa: BLE001  # per-record batch — record failure and continue
            failure_count += 1
            results.append({
                "record_id": record_id,
                "success": False,
                "message": str(e)
            })

    return BulkWriteOffResponse(
        success_count=success_count,
        failure_count=failure_count,
        results=results
    )


@router.post("/bulk/mark-lost", response_model=BulkMarkLostResponse)
async def bulk_mark_items_lost(
    request: BulkMarkLostRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk mark multiple checkouts as lost.

    Useful for processing multiple lost items at once, such as after
    an inventory audit reveals missing items.

    Set dry_run=true to preview the impact (items affected, estimated charges)
    without making any changes. This is recommended before executing large batches.
    """
    lost_type = handle_enum_validation(LostItemType, request.lost_type, "lost type")

    service = LostItemWorkflowService(db)
    results = []
    success_count = 0
    failure_count = 0
    total_charges = Decimal("0.00")
    notifications_sent = 0

    if request.dry_run:
        # Preview mode: validate checkout IDs and estimate charges without changes
        from ....models.circulation import Checkout, CheckoutStatus
        from sqlalchemy import select

        for checkout_id in request.checkout_ids:
            try:
                result = await db.execute(
                    select(Checkout).where(Checkout.id == checkout_id)
                )
                checkout = result.scalar_one_or_none()
                if checkout and checkout.status in (CheckoutStatus.active, CheckoutStatus.overdue):
                    success_count += 1
                    results.append({
                        "checkout_id": checkout_id,
                        "success": True,
                        "message": "[DRY RUN] Would be marked as lost",
                        "charge_amount": "0.00"
                    })
                else:
                    failure_count += 1
                    msg = "Checkout not found" if not checkout else f"Invalid status: {checkout.status}"
                    results.append({
                        "checkout_id": checkout_id,
                        "success": False,
                        "message": f"[DRY RUN] Would fail: {msg}"
                    })
            except Exception as e:  # noqa: BLE001  # per-checkout dry-run — record failure and continue
                failure_count += 1
                results.append({
                    "checkout_id": checkout_id,
                    "success": False,
                    "message": f"[DRY RUN] Would fail: {str(e)}"
                })

        logger.info(
            f"Bulk mark-lost DRY RUN by staff {staff_user.id}: "
            f"{success_count} would succeed, {failure_count} would fail "
            f"out of {len(request.checkout_ids)} items"
        )
    else:
        # Live mode: actually mark items as lost
        for checkout_id in request.checkout_ids:
            try:
                result = await service.mark_item_lost(
                    checkout_id=checkout_id,
                    lost_type=lost_type,
                    reported_by=staff_user,
                    report_notes=request.notes,
                    send_notification=request.send_notifications,
                )
                if result.success:
                    success_count += 1
                    if result.replacement_cost:
                        total_charges += result.replacement_cost.total
                    if result.notification_sent:
                        notifications_sent += 1
                    results.append({
                        "checkout_id": checkout_id,
                        "success": True,
                        "message": "Marked as lost",
                        "charge_amount": str(result.replacement_cost.total) if result.replacement_cost else "0.00"
                    })
                else:
                    failure_count += 1
                    results.append({
                        "checkout_id": checkout_id,
                        "success": False,
                        "message": result.message
                    })
            except Exception as e:  # noqa: BLE001  # per-checkout batch — record failure and continue
                failure_count += 1
                results.append({
                    "checkout_id": checkout_id,
                    "success": False,
                    "message": str(e)
                })

    return BulkMarkLostResponse(
        success_count=success_count,
        failure_count=failure_count,
        total_charges=total_charges,
        notifications_sent=notifications_sent,
        results=results
    )


# ============================================================================
# Info Endpoints
# ============================================================================

@router.get("/bulk/mark-lost")
async def get_bulk_mark_lost_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about bulk mark lost operation.

    Returns endpoint metadata and guidance for marking multiple items as lost.
    """
    return {
        "endpoint": "POST /staff/lost-damaged/bulk/mark-lost",
        "description": "Bulk mark multiple checkouts as lost",
        "method": "POST",
        "required_fields": ["checkout_ids"],
        "optional_fields": ["lost_type", "notes", "send_notifications"],
        "lost_types": ["lost_by_patron", "lost_in_transit", "missing_from_shelf"],
        "default_lost_type": "lost_by_patron",
        "max_items_per_request": 100,
        "notes": [
            "Useful for processing multiple lost items at once",
            "Each checkout will be charged replacement cost + processing fee",
            "Notifications can be sent to patrons if send_notifications=true",
            "Operation returns detailed results for each item",
        ],
    }


@router.get("/bulk/write-off")
async def get_bulk_write_off_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about bulk write-off operation.

    Returns endpoint metadata for writing off multiple lost items.
    """
    return {
        "endpoint": "POST /staff/lost-damaged/bulk/write-off",
        "description": "Bulk write off multiple lost items that will not be recovered",
        "method": "POST",
        "required_fields": ["lost_record_ids"],
        "optional_fields": ["notes"],
        "max_items_per_request": 100,
        "notes": [
            "Use for periodic cleanup of long-lost items",
            "Write-off marks items as permanently lost",
            "Does not affect patron charges (charges remain)",
            "Updates item status and inventory records",
            "Useful after grace periods have expired",
        ],
    }


@router.get("/lost-items/auto-convert")
async def get_lost_items_auto_convert_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about auto-converting overdue items to lost.

    Returns endpoint metadata and conversion settings.
    """
    return {
        "endpoint": "POST /staff/lost-damaged/lost-items/auto-convert",
        "description": "Automatically convert overdue items to lost",
        "method": "POST",
        "required_fields": ["threshold_days"],
        "optional_fields": ["dry_run"],
        "threshold_guidelines": {
            "30_days": "Standard threshold for most libraries",
            "45_days": "Extended grace period",
            "60_days": "Long-term overdue",
        },
        "dry_run": "Set to true to preview conversions without making changes",
        "notes": [
            "Identifies checkouts overdue beyond threshold",
            "Automatically marks them as lost",
            "Calculates and applies replacement charges",
            "Sends notifications to patrons",
            "Use dry_run=true to preview before committing",
            "Returns detailed results for each conversion",
        ],
    }


@router.get("/lost-items/found")
async def get_lost_items_found_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about processing found items.

    Returns endpoint metadata and found item handling.
    """
    return {
        "endpoint": "POST /staff/lost-damaged/lost-items/found",
        "description": "Process a found item that was previously marked lost",
        "method": "POST",
        "required_fields": ["lost_record_id", "found_condition"],
        "optional_fields": ["resolution_notes", "send_notification"],
        "found_condition_options": ["new", "good", "fair", "poor", "damaged"],
        "workflow": [
            "1. Item previously marked as lost",
            "2. Item is found/returned",
            "3. Assess current condition",
            "4. Credit patron for charges (if paid)",
            "5. Return item to circulation or withdraw if damaged",
        ],
        "notes": [
            "Calculates appropriate credit for patron",
            "Credit based on condition and time elapsed",
            "Item restored to circulation if in good condition",
            "Damaged items may require repair or withdrawal",
            "Notification informs patron of credit",
        ],
    }


@router.get("/lost-items/mark")
async def get_lost_items_mark_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about marking items as lost.

    Returns endpoint metadata and loss type guidance.
    """
    return {
        "endpoint": "POST /staff/lost-damaged/lost-items/mark",
        "description": "Mark an item as lost",
        "method": "POST",
        "required_fields": ["checkout_id", "lost_type"],
        "optional_fields": [
            "report_notes",
            "custom_replacement_cost",
            "send_notification",
        ],
        "lost_types": {
            "lost_by_patron": "Patron reports item lost",
            "lost_in_transit": "Item lost during transfer/transit",
            "missing_from_shelf": "Item missing during inventory",
            "never_returned": "Long overdue, presumed lost",
        },
        "replacement_cost_calculation": [
            "1. Item price (from catalog or market value)",
            "2. Processing fee (library policy)",
            "3. Total = item price + processing fee",
        ],
        "notes": [
            "Creates lost item record",
            "Calculates replacement cost automatically",
            "Creates fine/charge for patron",
            "Sends notification to patron if requested",
            "Custom replacement cost overrides automatic calculation",
        ],
    }


@router.get("/lost-items/{record_id}/write-off")
async def get_lost_items_write_off_info(
    record_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about writing off a specific lost item.

    Returns lost item record details and write-off information.
    """
    from ....models.lost_damaged import LostItemRecord

    # Get the lost item record
    lost_record = await get_or_404(db, LostItemRecord, record_id, "Lost item record not found")

    can_write_off = lost_record.status in ["reported", "charged"]

    return {
        "endpoint": f"POST /staff/lost-damaged/lost-items/{record_id}/write-off",
        "description": "Write off a lost item that will not be recovered",
        "method": "POST",
        "lost_item": {
            "id": lost_record.id,
            "status": lost_record.status,
            "lost_type": lost_record.lost_type,
            "replacement_cost": str(lost_record.replacement_cost),
            "reported_at": lost_record.reported_at.isoformat() if lost_record.reported_at else None,
        },
        "can_write_off": can_write_off,
        "optional_fields": ["notes"],
        "notes": [
            "Write-off marks item as permanently lost",
            "Does not affect patron charges",
            "Updates item status for inventory tracking",
            "Use for items that will not be recovered",
            "Helpful after grace periods expire",
        ],
    }


# ============================================================================
# Configuration Endpoints
# ============================================================================

@router.get("/config/loss-classifications", response_model=list[LostItemClassification])
async def get_loss_classifications(
    current_user: User = Depends(require_staff),
):
    """Get all available lost item classifications for form population.

    Returns the classifications staff can use when marking items as lost.
    """
    classifications = [
        LostItemClassification(
            value="lost_by_patron",
            label="Lost by Patron",
            description="Patron lost the item and reported it lost"
        ),
        LostItemClassification(
            value="lost_in_transit",
            label="Lost in Transit",
            description="Item was lost during delivery or return"
        ),
        LostItemClassification(
            value="missing",
            label="Missing from Collection",
            description="Item is missing from library shelves or storage"
        ),
        LostItemClassification(
            value="long_overdue",
            label="Long Overdue",
            description="Item is significantly overdue and presumed lost"
        ),
    ]
    return classifications
