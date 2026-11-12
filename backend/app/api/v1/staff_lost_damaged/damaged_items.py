# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Damaged Item Endpoints

Handles reporting damage, completing assessments, mending queue management,
repair completion, withdrawals, bulk operations, and related info endpoints.
"""

from app.core.logging import get_logger
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.inventory import ItemCondition, DamageType
from ....models.lost_damaged import DamagedItemStatus, DamageSeverity
from ....models.user import User
from ....schemas.lost_damaged import (
    ReportDamageRequest,
    DamagedItemWorkflowResponse,
    DamagedItemRecordResponse,
    CompleteAssessmentRequest,
    SendToMendingRequest,
    MendingQueueEntryResponse,
    CompleteRepairRequest,
    RepairCompletionResponse,
    WithdrawDamagedItemRequest,
    DamagedItemListResponse,
    MendingQueueListResponse,
    DamageAssessmentResponse,
)
from ....services.damaged_item_workflow_service import DamagedItemWorkflowService
from ..auth import get_current_user
from ..dependencies import require_staff
from .utils import convert_damaged_record, convert_mending_entry, handle_enum_validation, handle_service_error

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Inline Schemas for Bulk Operations
# ============================================================================

class BulkMendingAssignRequest(BaseModel):
    mending_entry_ids: List[int] = Field(..., min_length=1, max_length=100)
    assigned_to_id: int = Field(..., description="Staff member to assign")
    priority: Optional[int] = Field(None, ge=1, le=5, description="Optional priority override")


class BulkMendingAssignResponse(BaseModel):
    success_count: int
    failure_count: int
    results: List[dict]


# ============================================================================
# Damaged Item Endpoints
# ============================================================================

@router.post("/damaged/report", response_model=DamagedItemWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def report_damage(
    request: ReportDamageRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Report damage to an item.

    Creates a damage record, performs initial assessment,
    and updates item status.
    """
    severity = handle_enum_validation(DamageSeverity, request.severity, "severity")

    damage_types = []
    for dt in request.damage_types:
        damage_types.append(handle_enum_validation(DamageType, dt, "damage type"))

    service = DamagedItemWorkflowService(db)
    result = await service.report_damage(
        item_copy_id=request.item_copy_id,
        damage_types=damage_types,
        damage_description=request.damage_description,
        severity=severity,
        reported_by=staff_user,
        checkout_id=request.checkout_id,
        patron_id=request.patron_id,
        is_patron_responsible=request.is_patron_responsible,
        photo_urls=request.photo_urls,
        send_notification=request.send_notification,
    )

    handle_service_error(result)

    record_response = None
    if result.damaged_item_record:
        record_response = convert_damaged_record(result.damaged_item_record)

    assessment_response = None
    if result.assessment:
        assessment_response = DamageAssessmentResponse(
            is_repairable=result.assessment.is_repairable,
            severity=result.assessment.severity.value,
            estimated_repair_cost=result.assessment.estimated_repair_cost,
            recommended_action=result.assessment.recommended_action,
            patron_charge_amount=result.assessment.patron_charge_amount,
            charge_percentage=result.assessment.charge_percentage,
        )

    return DamagedItemWorkflowResponse(
        success=True,
        message=result.message,
        damaged_item_record=record_response,
        assessment=assessment_response,
        notification_sent=result.notification_sent,
    )


@router.post("/damaged/assess", response_model=DamagedItemWorkflowResponse)
async def complete_assessment(
    request: CompleteAssessmentRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Complete the assessment of a damaged item.

    Determines if item is repairable, applies charges if appropriate.
    """
    service = DamagedItemWorkflowService(db)
    result = await service.complete_assessment(
        damage_record_id=request.damage_record_id,
        assessed_by=staff_user,
        is_repairable=request.is_repairable,
        charge_patron=request.charge_patron,
        charge_amount=request.charge_amount,
        assessment_notes=request.assessment_notes,
        patron_responsibility_reason=request.patron_responsibility_reason,
        send_notification=request.send_notification,
    )

    handle_service_error(result)

    record_response = None
    if result.damaged_item_record:
        record_response = convert_damaged_record(result.damaged_item_record)

    return DamagedItemWorkflowResponse(
        success=True,
        message=result.message,
        damaged_item_record=record_response,
        fine_id=result.fine.id if result.fine else None,
        notification_sent=result.notification_sent,
    )


@router.post("/damaged/{damage_record_id}/send-to-mending", response_model=DamagedItemWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def send_to_mending(
    damage_record_id: int,
    request: SendToMendingRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Add a damaged item to the mending queue."""
    service = DamagedItemWorkflowService(db)
    result = await service.send_to_mending(
        damage_record_id=damage_record_id,
        added_by=staff_user,
        priority=request.priority,
        repair_type=request.repair_type,
        repair_instructions=request.repair_instructions,
        materials_needed=request.materials_needed,
        estimated_time_hours=request.estimated_time_hours,
        estimated_cost=request.estimated_cost,
        assigned_to_id=request.assigned_to_id,
    )

    handle_service_error(result)

    record_response = None
    if result.damaged_item_record:
        record_response = convert_damaged_record(result.damaged_item_record)

    return DamagedItemWorkflowResponse(
        success=True,
        message=result.message,
        damaged_item_record=record_response,
        mending_entry_id=result.mending_entry.id if result.mending_entry else None,
    )


@router.post("/damaged/{mending_entry_id}/repair-complete", response_model=RepairCompletionResponse)
async def complete_repair(
    mending_entry_id: int,
    request: CompleteRepairRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Complete a repair and return item to circulation."""
    condition = handle_enum_validation(ItemCondition, request.new_condition, "condition")

    service = DamagedItemWorkflowService(db)
    result = await service.complete_repair(
        mending_entry_id=mending_entry_id,
        completed_by=staff_user,
        actual_cost=request.actual_cost,
        completion_notes=request.completion_notes,
        new_condition=condition,
    )

    handle_service_error(result)

    record_response = None
    if result.damaged_item_record:
        record_response = convert_damaged_record(result.damaged_item_record)

    return RepairCompletionResponse(
        success=True,
        message=result.message,
        damaged_item_record=record_response,
        item_restored=result.item_restored,
        actual_cost=result.actual_cost,
    )


@router.post("/damaged/{damage_record_id}/withdraw", response_model=DamagedItemWorkflowResponse)
async def withdraw_damaged_item(
    damage_record_id: int,
    request: WithdrawDamagedItemRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw a damaged item that cannot be repaired."""
    service = DamagedItemWorkflowService(db)
    result = await service.withdraw_damaged_item(
        damage_record_id=damage_record_id,
        withdrawn_by=staff_user,
        withdrawal_reason=request.withdrawal_reason,
        charge_patron=request.charge_patron,
        charge_amount=request.charge_amount,
        send_notification=request.send_notification,
    )

    handle_service_error(result)

    record_response = None
    if result.damaged_item_record:
        record_response = convert_damaged_record(result.damaged_item_record)

    return DamagedItemWorkflowResponse(
        success=True,
        message=result.message,
        damaged_item_record=record_response,
        fine_id=result.fine.id if result.fine else None,
        notification_sent=result.notification_sent,
    )


@router.get("/damaged-items", response_model=DamagedItemListResponse)
async def list_damaged_items(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    patron_id: Optional[int] = Query(None, description="Filter by patron"),
    is_patron_responsible: Optional[bool] = Query(None, description="Filter by patron responsibility"),
    days_ago: Optional[int] = Query(None, ge=1, description="Items reported within X days"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List damaged item records with filtering."""
    status_enum = None
    if status:
        status_enum = handle_enum_validation(DamagedItemStatus, status, "status")

    severity_enum = None
    if severity:
        severity_enum = handle_enum_validation(DamageSeverity, severity, "severity")

    service = DamagedItemWorkflowService(db)
    items, total = await service.get_damaged_items(
        status=status_enum,
        severity=severity_enum,
        patron_id=patron_id,
        is_patron_responsible=is_patron_responsible,
        days_ago=days_ago,
        limit=limit,
        offset=offset,
    )

    return DamagedItemListResponse(
        items=[convert_damaged_record(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/mending-queue", response_model=MendingQueueListResponse)
async def list_mending_queue(
    include_completed: bool = Query(False, description="Include completed repairs"),
    assigned_to_id: Optional[int] = Query(None, description="Filter by assigned staff"),
    priority: Optional[int] = Query(None, ge=1, le=5, description="Filter by priority"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List mending queue entries."""
    service = DamagedItemWorkflowService(db)
    items, total = await service.get_mending_queue(
        include_completed=include_completed,
        assigned_to_id=assigned_to_id,
        priority=priority,
        limit=limit,
        offset=offset,
    )

    return MendingQueueListResponse(
        items=[convert_mending_entry(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# ============================================================================
# Bulk Operations
# ============================================================================

@router.post("/bulk/mending-assign", response_model=BulkMendingAssignResponse)
async def bulk_assign_mending(
    request: BulkMendingAssignRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk assign mending queue items to a staff member.

    Useful for distributing repair work among staff.
    """
    from ....models.lost_damaged import MendingQueue

    results = []
    success_count = 0
    failure_count = 0

    for entry_id in request.mending_entry_ids:
        try:
            # Get and update the entry
            result = await db.execute(
                select(MendingQueue).where(
                    MendingQueue.id == entry_id,
                    MendingQueue.is_completed == False
                )
            )
            entry = result.scalar_one_or_none()

            if not entry:
                failure_count += 1
                results.append({
                    "entry_id": entry_id,
                    "success": False,
                    "message": "Entry not found or already completed"
                })
                continue

            entry.assigned_to_id = request.assigned_to_id
            if request.priority:
                entry.priority = request.priority

            success_count += 1
            results.append({
                "entry_id": entry_id,
                "success": True,
                "message": "Assignment updated"
            })
        except Exception as e:  # noqa: BLE001  # per-entry batch — record failure and continue
            failure_count += 1
            results.append({
                "entry_id": entry_id,
                "success": False,
                "message": str(e)
            })

    await db.commit()

    return BulkMendingAssignResponse(
        success_count=success_count,
        failure_count=failure_count,
        results=results
    )


@router.post("/bulk/mending-priority")
async def bulk_update_mending_priority(
    entry_ids: List[int] = Query(..., description="Mending entry IDs to update"),
    priority: int = Query(..., ge=1, le=5, description="New priority level"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Bulk update priority for mending queue items."""
    from ....models.lost_damaged import MendingQueue

    updated_count = 0
    for entry_id in entry_ids:
        result = await db.execute(
            select(MendingQueue).where(
                MendingQueue.id == entry_id,
                MendingQueue.is_completed == False
            )
        )
        entry = result.scalar_one_or_none()
        if entry:
            entry.priority = priority
            updated_count += 1

    await db.commit()

    return {
        "updated_count": updated_count,
        "requested_count": len(entry_ids),
        "priority": priority
    }


# ============================================================================
# Info Endpoints
# ============================================================================

@router.get("/bulk/mending-assign")
async def get_bulk_mending_assign_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about bulk mending assignment operation.

    Returns endpoint metadata and available staff for assignment.
    """
    from ....models.user import UserRole

    # Get available staff for assignment
    staff_result = await db.execute(
        select(User).where(
            User.role.in_([UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN]),
            User.is_active == True,
        ).order_by(User.last_name, User.first_name)
    )
    available_staff = staff_result.scalars().all()

    return {
        "endpoint": "POST /staff/lost-damaged/bulk/mending-assign",
        "description": "Bulk assign mending queue items to a staff member",
        "method": "POST",
        "required_fields": ["mending_entry_ids", "assigned_to_id"],
        "optional_fields": ["priority"],
        "max_items_per_request": 100,
        "available_staff": [
            {
                "id": s.id,
                "name": f"{s.first_name} {s.last_name}",
                "role": str(s.role),
            }
            for s in available_staff
        ],
        "notes": [
            "Useful for distributing repair work among staff",
            "Only incomplete mending entries can be reassigned",
            "Optional priority override (1-5, 1=highest)",
        ],
    }


@router.get("/bulk/mending-priority")
async def get_bulk_mending_priority_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about bulk mending priority update operation.

    Returns endpoint metadata for updating priorities.
    """
    return {
        "endpoint": "POST /staff/lost-damaged/bulk/mending-priority",
        "description": "Bulk update priority for mending queue items",
        "method": "POST",
        "required_query_params": ["entry_ids", "priority"],
        "priority_scale": {
            "1": "Highest - Urgent repairs",
            "2": "High - Important items",
            "3": "Normal - Standard repairs",
            "4": "Low - Can wait",
            "5": "Lowest - Defer if needed",
        },
        "notes": [
            "Only incomplete mending entries can have priority updated",
            "Priority affects queue position",
            "Returns count of successfully updated entries",
        ],
    }


@router.get("/damaged-items/assess")
async def get_damaged_items_assess_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about completing damage assessment.

    Returns endpoint metadata and assessment guidelines.
    """
    return {
        "endpoint": "POST /staff/lost-damaged/damaged-items/assess",
        "description": "Complete the assessment of a damaged item",
        "method": "POST",
        "required_fields": ["damage_record_id", "is_repairable"],
        "optional_fields": [
            "charge_patron",
            "charge_amount",
            "assessment_notes",
            "patron_responsibility_reason",
            "send_notification",
        ],
        "assessment_workflow": [
            "1. Item damage is reported",
            "2. Initial severity assessment is made",
            "3. Detailed assessment determines if repairable",
            "4. If patron responsible, charge may be applied",
            "5. Item moves to repair or withdrawal",
        ],
        "charge_guidelines": {
            "minor_damage": "Usually no patron charge",
            "moderate_damage": "Partial replacement cost (25-50%)",
            "severe_damage": "Full replacement cost",
            "patron_caused": "Consider patron responsibility",
        },
        "notes": [
            "Assessment determines repair vs. withdrawal path",
            "Patron charges are based on responsibility and severity",
            "Notification informs patron of assessment outcome",
        ],
    }


@router.get("/damaged-items/mending")
async def get_damaged_items_mending_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about sending items to mending queue.

    Returns endpoint metadata and queue information.
    """
    from sqlalchemy import func
    from ....models.lost_damaged import MendingQueue

    # Get current queue stats
    queue_count_result = await db.execute(
        select(func.count(MendingQueue.id)).where(
            MendingQueue.is_completed == False
        )
    )
    queue_count = queue_count_result.scalar() or 0

    return {
        "endpoint": "POST /staff/lost-damaged/damaged-items/mending",
        "description": "Add a damaged item to the mending queue",
        "method": "POST",
        "required_fields": ["damage_record_id"],
        "optional_fields": [
            "priority",
            "repair_type",
            "repair_instructions",
            "materials_needed",
            "estimated_time_hours",
            "estimated_cost",
            "assigned_to_id",
        ],
        "current_queue_size": queue_count,
        "priority_scale": "1 (highest) to 5 (lowest)",
        "repair_types": [
            "binding_repair",
            "page_repair",
            "cover_repair",
            "spine_repair",
            "cleaning",
            "other",
        ],
        "notes": [
            "Item enters mending queue for repair",
            "Priority determines position in queue",
            "Can be assigned to specific staff member",
            "Repair instructions guide the mending work",
        ],
    }


@router.get("/damaged-items/repair-complete")
async def get_damaged_items_repair_complete_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about completing repairs.

    Returns endpoint metadata and completion guidance.
    """
    return {
        "endpoint": "POST /staff/lost-damaged/damaged-items/repair-complete",
        "description": "Complete a repair and return item to circulation",
        "method": "POST",
        "required_fields": ["mending_entry_id", "new_condition"],
        "optional_fields": ["actual_cost", "completion_notes"],
        "valid_conditions": ["good", "fair", "poor"],
        "notes": [
            "Marks mending queue entry as completed",
            "Updates item condition in inventory",
            "Records actual repair cost if different from estimate",
            "Item becomes available for circulation again",
            "Completion notes document repair outcome",
        ],
    }


@router.get("/damaged-items/report")
async def get_damaged_items_report_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about reporting damaged items.

    Returns endpoint metadata and damage reporting guidance.
    """
    return {
        "endpoint": "POST /staff/lost-damaged/damaged-items/report",
        "description": "Report damage to an item",
        "method": "POST",
        "required_fields": ["item_copy_id", "damage_types", "severity", "damage_description"],
        "optional_fields": [
            "checkout_id",
            "patron_id",
            "is_patron_responsible",
            "photo_urls",
            "send_notification",
        ],
        "damage_types": [
            "torn_pages",
            "water_damage",
            "cover_damage",
            "binding_damage",
            "writing_marks",
            "missing_pages",
            "stains",
            "mold",
            "other",
        ],
        "severity_levels": {
            "minor": "Small issue, easily repairable",
            "moderate": "Noticeable damage, may require professional repair",
            "severe": "Major damage, repair questionable",
            "total_loss": "Cannot be repaired, must be replaced",
        },
        "notes": [
            "Creates damage record and performs initial assessment",
            "Severity determines repair vs. withdrawal path",
            "Photos can be attached for documentation",
            "If patron responsible, they may be charged",
            "Notification informs patron of damage claim",
        ],
    }


@router.get("/damaged-items/withdraw")
async def get_damaged_items_withdraw_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about withdrawing damaged items.

    Returns endpoint metadata and withdrawal guidance.
    """
    return {
        "endpoint": "POST /staff/lost-damaged/damaged-items/withdraw",
        "description": "Withdraw a damaged item that cannot be repaired",
        "method": "POST",
        "required_fields": ["damage_record_id", "withdrawal_reason"],
        "optional_fields": ["charge_patron", "charge_amount", "send_notification"],
        "withdrawal_reasons": [
            "Beyond economical repair",
            "Damage too severe",
            "Not worth repair cost",
            "Outdated/superseded",
            "Health/safety concern (mold, etc.)",
        ],
        "notes": [
            "Use when item cannot or should not be repaired",
            "Item is permanently removed from circulation",
            "Patron may be charged if responsible for damage",
            "Withdrawal is tracked in inventory system",
            "Notification informs patron if charges apply",
        ],
    }
