# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Program Planning Tools API Routes.

Provides endpoints for:
- Program template library (CRUD, copy from past programs)
- Program plan management (create, update, with template/copy support)
- Budget tracking per program
- Supply checklist management
- Room and equipment auto-booking
- Marketing timeline reminders
- Volunteer assignment
- Post-program evaluation
- Success metrics comparison
"""

from app.core.logging import get_logger
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.user import User
from ...schemas.program_planning import (
    ProgramTemplateCreate, ProgramTemplateUpdate, ProgramTemplateResponse,
    ProgramTemplateListResponse,
    ProgramPlanCreate, ProgramPlanUpdate, ProgramPlanResponse,
    ProgramPlanDetailResponse,
    ProgramBudgetItemCreate, ProgramBudgetItemUpdate, ProgramBudgetItemResponse,
    ProgramSupplyItemCreate, ProgramSupplyItemUpdate, ProgramSupplyItemResponse,
    ProgramRoomBookingCreate, ProgramRoomBookingUpdate, ProgramRoomBookingResponse,
    ProgramEquipmentBookingCreate, ProgramEquipmentBookingUpdate,
    ProgramEquipmentBookingResponse,
    ProgramMarketingMilestoneCreate, ProgramMarketingMilestoneUpdate,
    ProgramMarketingMilestoneResponse,
    ProgramVolunteerAssignmentCreate, ProgramVolunteerAssignmentUpdate,
    ProgramVolunteerAssignmentResponse,
    ProgramEvaluationCreate, ProgramEvaluationUpdate, ProgramEvaluationResponse,
    CopyProgramRequest,
    SuccessMetricsComparisonResponse, SuccessMetricsComparison,
)
from ...services.program_planning_service import ProgramPlanningService
from .auth import get_current_user
from .dependencies import require_staff as require_staff_role

logger = get_logger(__name__)

router = APIRouter(prefix="/program-planning", tags=["program-planning"])




def get_service(db: AsyncSession = Depends(get_db)) -> ProgramPlanningService:
    return ProgramPlanningService(db)


# ============================================================================
# Template Endpoints
# ============================================================================

@router.get("/templates", response_model=list[ProgramTemplateListResponse])
@limiter.limit("60/minute")
async def list_templates(
    request: Request,
    category: str | None = None,
    active_only: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """List all program templates, optionally filtered by category."""
    return await service.list_templates(category=category, active_only=active_only, skip=skip, limit=limit)


@router.get("/templates/{template_id}", response_model=ProgramTemplateResponse)
@limiter.limit("60/minute")
async def get_template(
    request: Request,
    template_id: int,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Get a program template with all nested items."""
    template = await service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/templates", response_model=ProgramTemplateResponse, status_code=201)
@limiter.limit("30/minute")
async def create_template(
    request: Request,
    data: ProgramTemplateCreate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Create a new program template."""
    return await service.create_template(data.model_dump(), current_user.id)


@router.patch("/templates/{template_id}", response_model=ProgramTemplateResponse)
@limiter.limit("30/minute")
async def update_template(
    request: Request,
    template_id: int,
    data: ProgramTemplateUpdate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Update a program template."""
    template = await service.update_template(template_id, data.model_dump(exclude_unset=True))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.delete("/templates/{template_id}", status_code=204)
@limiter.limit("30/minute")
async def delete_template(
    request: Request,
    template_id: int,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Deactivate a program template."""
    if not await service.delete_template(template_id):
        raise HTTPException(status_code=404, detail="Template not found")


@router.post(
    "/templates/from-program/{program_id}",
    response_model=ProgramTemplateResponse,
    status_code=201,
)
@limiter.limit("10/minute")
async def create_template_from_program(
    request: Request,
    program_id: int,
    template_name: str = Query(..., min_length=1, max_length=255),
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Create a template from a successful past program."""
    template = await service.create_template_from_program(program_id, template_name, current_user.id)
    if not template:
        raise HTTPException(status_code=404, detail="Source program not found")
    return template


# ============================================================================
# Plan Endpoints
# ============================================================================

@router.post("/plans", response_model=ProgramPlanResponse, status_code=201)
@limiter.limit("30/minute")
async def create_plan(
    request: Request,
    data: ProgramPlanCreate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Create a program plan, optionally from a template or by copying a past program."""
    return await service.create_plan(data.model_dump(), current_user.id)


@router.get("/plans/{plan_id}", response_model=ProgramPlanDetailResponse)
@limiter.limit("60/minute")
async def get_plan(
    request: Request,
    plan_id: int,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Get a program plan with all nested details."""
    plan = await service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.get("/plans/by-program/{program_id}", response_model=ProgramPlanDetailResponse)
@limiter.limit("60/minute")
async def get_plan_by_program(
    request: Request,
    program_id: int,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Get the plan for a specific program."""
    plan = await service.get_plan_by_program(program_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No plan found for this program")
    return plan


@router.patch("/plans/{plan_id}", response_model=ProgramPlanResponse)
@limiter.limit("30/minute")
async def update_plan(
    request: Request,
    plan_id: int,
    data: ProgramPlanUpdate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Update a program plan."""
    plan = await service.update_plan(plan_id, data.model_dump(exclude_unset=True))
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


# ============================================================================
# Copy Program Endpoint
# ============================================================================

@router.post("/copy-program")
@limiter.limit("10/minute")
async def copy_program(
    request: Request,
    data: CopyProgramRequest,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Copy a successful program from a previous year, creating a new program + plan."""
    result = await service.copy_program(data.model_dump(), current_user.id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ============================================================================
# Budget Item Endpoints
# ============================================================================

@router.post("/budget-items", response_model=ProgramBudgetItemResponse, status_code=201)
@limiter.limit("60/minute")
async def add_budget_item(
    request: Request,
    data: ProgramBudgetItemCreate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Add a budget item to a program plan."""
    return await service.add_budget_item(data.model_dump())


@router.patch("/budget-items/{item_id}", response_model=ProgramBudgetItemResponse)
@limiter.limit("60/minute")
async def update_budget_item(
    request: Request,
    item_id: int,
    data: ProgramBudgetItemUpdate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Update a budget item."""
    item = await service.update_budget_item(item_id, data.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")
    return item


@router.delete("/budget-items/{item_id}", status_code=204)
@limiter.limit("60/minute")
async def delete_budget_item(
    request: Request,
    item_id: int,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Delete a budget item."""
    if not await service.delete_budget_item(item_id):
        raise HTTPException(status_code=404, detail="Budget item not found")


# ============================================================================
# Supply Checklist Endpoints
# ============================================================================

@router.get("/supply-items/{plan_id}", response_model=list[ProgramSupplyItemResponse])
@limiter.limit("60/minute")
async def get_supply_checklist(
    request: Request,
    plan_id: int,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Get the supply checklist for a program plan."""
    return await service.get_supply_checklist(plan_id)


@router.post("/supply-items", response_model=ProgramSupplyItemResponse, status_code=201)
@limiter.limit("60/minute")
async def add_supply_item(
    request: Request,
    data: ProgramSupplyItemCreate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Add a supply item to the checklist."""
    return await service.add_supply_item(data.model_dump())


@router.patch("/supply-items/{item_id}", response_model=ProgramSupplyItemResponse)
@limiter.limit("60/minute")
async def update_supply_item(
    request: Request,
    item_id: int,
    data: ProgramSupplyItemUpdate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Update a supply item."""
    item = await service.update_supply_item(item_id, data.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="Supply item not found")
    return item


@router.delete("/supply-items/{item_id}", status_code=204)
@limiter.limit("60/minute")
async def delete_supply_item(
    request: Request,
    item_id: int,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Delete a supply item."""
    if not await service.delete_supply_item(item_id):
        raise HTTPException(status_code=404, detail="Supply item not found")


# ============================================================================
# Room & Equipment Booking Endpoints
# ============================================================================

@router.post("/room-bookings", response_model=ProgramRoomBookingResponse, status_code=201)
@limiter.limit("30/minute")
async def create_room_booking(
    request: Request,
    data: ProgramRoomBookingCreate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Book a room for a program (auto-selects if room_id not provided)."""
    booking = await service.auto_book_room(data.plan_id, data.room_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Plan not found")
    return booking


@router.post(
    "/equipment-bookings",
    response_model=ProgramEquipmentBookingResponse,
    status_code=201,
)
@limiter.limit("30/minute")
async def create_equipment_booking(
    request: Request,
    data: ProgramEquipmentBookingCreate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Request equipment for a program."""
    return await service.add_equipment_booking(data.model_dump())


@router.patch(
    "/equipment-bookings/{booking_id}",
    response_model=ProgramEquipmentBookingResponse,
)
@limiter.limit("30/minute")
async def update_equipment_booking(
    request: Request,
    booking_id: int,
    data: ProgramEquipmentBookingUpdate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Update an equipment booking."""
    booking = await service.update_equipment_booking(booking_id, data.model_dump(exclude_unset=True))
    if not booking:
        raise HTTPException(status_code=404, detail="Equipment booking not found")
    return booking


# ============================================================================
# Marketing Timeline Endpoints
# ============================================================================

@router.post(
    "/marketing-milestones",
    response_model=ProgramMarketingMilestoneResponse,
    status_code=201,
)
@limiter.limit("60/minute")
async def add_marketing_milestone(
    request: Request,
    data: ProgramMarketingMilestoneCreate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Add a marketing milestone to a program plan."""
    return await service.add_marketing_milestone(data.model_dump())


@router.patch(
    "/marketing-milestones/{milestone_id}",
    response_model=ProgramMarketingMilestoneResponse,
)
@limiter.limit("60/minute")
async def update_marketing_milestone(
    request: Request,
    milestone_id: int,
    data: ProgramMarketingMilestoneUpdate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Update a marketing milestone (including marking it complete)."""
    milestone = await service.update_marketing_milestone(
        milestone_id, data.model_dump(exclude_unset=True), current_user.id
    )
    if not milestone:
        raise HTTPException(status_code=404, detail="Marketing milestone not found")
    return milestone


@router.get(
    "/marketing-reminders",
    response_model=list[ProgramMarketingMilestoneResponse],
)
@limiter.limit("60/minute")
async def get_marketing_reminders(
    request: Request,
    days_ahead: int = Query(7, ge=1, le=90),
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Get upcoming marketing milestones that need attention."""
    return await service.get_upcoming_marketing_reminders(days_ahead)


# ============================================================================
# Volunteer Assignment Endpoints
# ============================================================================

@router.post(
    "/volunteer-assignments",
    response_model=ProgramVolunteerAssignmentResponse,
    status_code=201,
)
@limiter.limit("60/minute")
async def assign_volunteer(
    request: Request,
    data: ProgramVolunteerAssignmentCreate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Assign a volunteer to a program."""
    return await service.assign_volunteer(data.model_dump())


@router.patch(
    "/volunteer-assignments/{assignment_id}",
    response_model=ProgramVolunteerAssignmentResponse,
)
@limiter.limit("60/minute")
async def update_volunteer_assignment(
    request: Request,
    assignment_id: int,
    data: ProgramVolunteerAssignmentUpdate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Update a volunteer assignment."""
    assignment = await service.update_volunteer_assignment(
        assignment_id, data.model_dump(exclude_unset=True)
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Volunteer assignment not found")
    return assignment


@router.delete("/volunteer-assignments/{assignment_id}", status_code=204)
@limiter.limit("60/minute")
async def delete_volunteer_assignment(
    request: Request,
    assignment_id: int,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Remove a volunteer assignment."""
    if not await service.delete_volunteer_assignment(assignment_id):
        raise HTTPException(status_code=404, detail="Volunteer assignment not found")


# ============================================================================
# Evaluation Endpoints
# ============================================================================

@router.post("/evaluations", response_model=ProgramEvaluationResponse, status_code=201)
@limiter.limit("30/minute")
async def create_evaluation(
    request: Request,
    data: ProgramEvaluationCreate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Create a post-program evaluation."""
    return await service.create_evaluation(data.model_dump(), current_user.id)


@router.patch("/evaluations/{eval_id}", response_model=ProgramEvaluationResponse)
@limiter.limit("30/minute")
async def update_evaluation(
    request: Request,
    eval_id: int,
    data: ProgramEvaluationUpdate,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Update a post-program evaluation."""
    evaluation = await service.update_evaluation(
        eval_id, data.model_dump(exclude_unset=True), current_user.id
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation


@router.get("/evaluations/by-plan/{plan_id}", response_model=ProgramEvaluationResponse)
@limiter.limit("60/minute")
async def get_evaluation(
    request: Request,
    plan_id: int,
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Get the evaluation for a program plan."""
    evaluation = await service.get_evaluation(plan_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="No evaluation found for this plan")
    return evaluation


# ============================================================================
# Success Metrics Comparison
# ============================================================================

@router.get("/success-metrics", response_model=SuccessMetricsComparisonResponse)
@limiter.limit("30/minute")
async def compare_success_metrics(
    request: Request,
    program_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    program_ids: str | None = Query(None, description="Comma-separated program IDs"),
    limit: int = Query(20, ge=1, le=100),
    service: ProgramPlanningService = Depends(get_service),
    current_user: User = Depends(require_staff_role),
):
    """Compare success metrics across completed programs."""
    ids = [int(x.strip()) for x in program_ids.split(",")] if program_ids else None
    comparisons = await service.compare_success_metrics(
        program_ids=ids,
        program_type=program_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )

    programs = [SuccessMetricsComparison(**c) for c in comparisons]

    # Build summary
    if programs:
        avg_attendance = sum(
            p.attendance for p in programs if p.attendance
        ) / max(1, sum(1 for p in programs if p.attendance))
        summary = {
            "total_programs": len(programs),
            "average_attendance": round(avg_attendance, 1),
            "programs_recommended_repeat": sum(
                1 for p in programs if p.recommend_repeat
            ),
        }
    else:
        summary = {"total_programs": 0}

    return SuccessMetricsComparisonResponse(programs=programs, summary=summary)
