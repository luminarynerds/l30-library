# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from ._base import MoneyDecimal, StrictInputSchema


# ============================================================================
# Program Template Schemas
# ============================================================================

class TemplateBudgetItemBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=255)
    category: str
    estimated_amount: MoneyDecimal = Field(..., ge=0)
    notes: str | None = None


class TemplateBudgetItemCreate(StrictInputSchema, TemplateBudgetItemBase):
    pass


class TemplateBudgetItemResponse(TemplateBudgetItemBase):
    id: int

    class Config:
        from_attributes = True


class TemplateSupplyItemBase(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(default=1, ge=1)
    unit: str | None = Field(None, max_length=50)
    estimated_cost: MoneyDecimal | None = Field(None, ge=0)
    vendor_suggestion: str | None = Field(None, max_length=255)
    notes: str | None = None


class TemplateSupplyItemCreate(StrictInputSchema, TemplateSupplyItemBase):
    pass


class TemplateSupplyItemResponse(TemplateSupplyItemBase):
    id: int

    class Config:
        from_attributes = True


class TemplateMarketingMilestoneBase(BaseModel):
    milestone_type: str
    description: str = Field(..., min_length=1, max_length=500)
    days_before_program: int = Field(..., ge=0)
    notes: str | None = None


class TemplateMarketingMilestoneCreate(StrictInputSchema, TemplateMarketingMilestoneBase):
    pass


class TemplateMarketingMilestoneResponse(TemplateMarketingMilestoneBase):
    id: int

    class Config:
        from_attributes = True


class ProgramTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str
    target_audience: str = Field(..., max_length=50)
    program_type: str = Field(..., max_length=50)
    default_duration_minutes: int = Field(default=60, ge=15, le=480)
    recommended_capacity: int | None = Field(None, ge=1)
    registration_required: bool = False
    room_type_needed: str | None = Field(None, max_length=50)
    equipment_needed: list[str] | None = None
    estimated_budget: MoneyDecimal | None = Field(None, ge=0)
    marketing_lead_days: int | None = Field(default=14, ge=0)
    volunteers_needed: int = Field(default=0, ge=0)
    volunteer_roles_needed: list[str] | None = None
    target_attendance: int | None = Field(None, ge=1)
    success_metrics: dict | None = None


class ProgramTemplateCreate(StrictInputSchema, ProgramTemplateBase):
    budget_items: list[TemplateBudgetItemCreate] | None = None
    supply_items: list[TemplateSupplyItemCreate] | None = None
    marketing_milestones: list[TemplateMarketingMilestoneCreate] | None = None


class ProgramTemplateUpdate(StrictInputSchema):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = None
    target_audience: str | None = Field(None, max_length=50)
    program_type: str | None = Field(None, max_length=50)
    default_duration_minutes: int | None = Field(None, ge=15, le=480)
    recommended_capacity: int | None = Field(None, ge=1)
    registration_required: bool | None = None
    room_type_needed: str | None = Field(None, max_length=50)
    equipment_needed: list[str] | None = None
    estimated_budget: MoneyDecimal | None = Field(None, ge=0)
    marketing_lead_days: int | None = Field(None, ge=0)
    volunteers_needed: int | None = Field(None, ge=0)
    volunteer_roles_needed: list[str] | None = None
    target_attendance: int | None = Field(None, ge=1)
    success_metrics: dict | None = None
    is_active: bool | None = None


class ProgramTemplateResponse(ProgramTemplateBase):
    id: int
    is_active: bool
    times_used: int
    source_program_id: int | None = None
    created_by_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    template_budget_items: list[TemplateBudgetItemResponse] = []
    template_supply_items: list[TemplateSupplyItemResponse] = []
    template_marketing_milestones: list[TemplateMarketingMilestoneResponse] = []

    class Config:
        from_attributes = True


class ProgramTemplateListResponse(ProgramTemplateBase):
    id: int
    is_active: bool
    times_used: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Program Plan Schemas
# ============================================================================

class ProgramPlanCreate(StrictInputSchema):
    program_id: int
    template_id: int | None = None
    copied_from_program_id: int | None = None
    planning_notes: str | None = None


class ProgramPlanUpdate(StrictInputSchema):
    planning_notes: str | None = None
    planning_complete: bool | None = None


class ProgramPlanResponse(BaseModel):
    id: int
    program_id: int
    template_id: int | None = None
    copied_from_program_id: int | None = None
    planning_notes: str | None = None
    planning_complete: bool
    planning_completed_at: datetime | None = None
    total_budget: MoneyDecimal
    total_spent: MoneyDecimal
    created_by_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class ProgramPlanDetailResponse(ProgramPlanResponse):
    budget_items: list["ProgramBudgetItemResponse"] = []
    supply_items: list["ProgramSupplyItemResponse"] = []
    room_bookings: list["ProgramRoomBookingResponse"] = []
    equipment_bookings: list["ProgramEquipmentBookingResponse"] = []
    marketing_milestones: list["ProgramMarketingMilestoneResponse"] = []
    volunteer_assignments: list["ProgramVolunteerAssignmentResponse"] = []
    evaluation: Optional["ProgramEvaluationResponse"] = None

    class Config:
        from_attributes = True


# ============================================================================
# Budget Item Schemas
# ============================================================================

class ProgramBudgetItemCreate(StrictInputSchema):
    plan_id: int
    description: str = Field(..., min_length=1, max_length=255)
    category: str
    estimated_amount: MoneyDecimal = Field(..., ge=0)
    actual_amount: MoneyDecimal | None = Field(None, ge=0)
    vendor: str | None = Field(None, max_length=255)
    notes: str | None = None


class ProgramBudgetItemUpdate(StrictInputSchema):
    description: str | None = Field(None, min_length=1, max_length=255)
    category: str | None = None
    estimated_amount: MoneyDecimal | None = Field(None, ge=0)
    actual_amount: MoneyDecimal | None = Field(None, ge=0)
    is_paid: bool | None = None
    paid_date: date | None = None
    receipt_reference: str | None = Field(None, max_length=255)
    vendor: str | None = Field(None, max_length=255)
    notes: str | None = None


class ProgramBudgetItemResponse(BaseModel):
    id: int
    plan_id: int
    description: str
    category: str
    estimated_amount: MoneyDecimal
    actual_amount: MoneyDecimal | None = None
    is_paid: bool
    paid_date: date | None = None
    receipt_reference: str | None = None
    vendor: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Supply Item Schemas
# ============================================================================

class ProgramSupplyItemCreate(StrictInputSchema):
    plan_id: int
    item_name: str = Field(..., min_length=1, max_length=255)
    quantity_needed: int = Field(default=1, ge=1)
    quantity_on_hand: int = Field(default=0, ge=0)
    unit: str | None = Field(None, max_length=50)
    estimated_cost: MoneyDecimal | None = Field(None, ge=0)
    vendor: str | None = Field(None, max_length=255)
    notes: str | None = None


class ProgramSupplyItemUpdate(StrictInputSchema):
    item_name: str | None = Field(None, min_length=1, max_length=255)
    quantity_needed: int | None = Field(None, ge=1)
    quantity_on_hand: int | None = Field(None, ge=0)
    unit: str | None = Field(None, max_length=50)
    estimated_cost: MoneyDecimal | None = Field(None, ge=0)
    actual_cost: MoneyDecimal | None = Field(None, ge=0)
    status: str | None = None
    vendor: str | None = Field(None, max_length=255)
    order_date: date | None = None
    expected_delivery: date | None = None
    assigned_to_id: int | None = None
    notes: str | None = None


class ProgramSupplyItemResponse(BaseModel):
    id: int
    plan_id: int
    item_name: str
    quantity_needed: int
    quantity_on_hand: int
    unit: str | None = None
    estimated_cost: MoneyDecimal | None = None
    actual_cost: MoneyDecimal | None = None
    status: str
    vendor: str | None = None
    order_date: date | None = None
    expected_delivery: date | None = None
    assigned_to_id: int | None = None
    notes: str | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Room & Equipment Booking Schemas
# ============================================================================

class ProgramRoomBookingCreate(StrictInputSchema):
    plan_id: int
    room_id: int | None = None
    setup_notes: str | None = None
    setup_time_minutes: int | None = Field(default=15, ge=0)
    teardown_time_minutes: int | None = Field(default=15, ge=0)


class ProgramRoomBookingUpdate(StrictInputSchema):
    room_id: int | None = None
    status: str | None = None
    setup_notes: str | None = None
    setup_time_minutes: int | None = Field(None, ge=0)
    teardown_time_minutes: int | None = Field(None, ge=0)


class ProgramRoomBookingResponse(BaseModel):
    id: int
    plan_id: int
    room_id: int | None = None
    reservation_id: int | None = None
    status: str
    setup_notes: str | None = None
    setup_time_minutes: int | None = None
    teardown_time_minutes: int | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ProgramEquipmentBookingCreate(StrictInputSchema):
    plan_id: int
    equipment_id: int | None = None
    equipment_type_requested: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(default=1, ge=1)
    notes: str | None = None


class ProgramEquipmentBookingUpdate(StrictInputSchema):
    equipment_id: int | None = None
    equipment_type_requested: str | None = Field(None, min_length=1, max_length=100)
    quantity: int | None = Field(None, ge=1)
    status: str | None = None
    notes: str | None = None


class ProgramEquipmentBookingResponse(BaseModel):
    id: int
    plan_id: int
    equipment_id: int | None = None
    equipment_type_requested: str
    quantity: int
    status: str
    notes: str | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Marketing Milestone Schemas
# ============================================================================

class ProgramMarketingMilestoneCreate(StrictInputSchema):
    plan_id: int
    milestone_type: str
    description: str = Field(..., min_length=1, max_length=500)
    due_date: date
    assigned_to_id: int | None = None
    notes: str | None = None


class ProgramMarketingMilestoneUpdate(StrictInputSchema):
    milestone_type: str | None = None
    description: str | None = Field(None, min_length=1, max_length=500)
    due_date: date | None = None
    completed: bool | None = None
    assigned_to_id: int | None = None
    notes: str | None = None


class ProgramMarketingMilestoneResponse(BaseModel):
    id: int
    plan_id: int
    milestone_type: str
    description: str
    due_date: date
    completed: bool
    completed_at: datetime | None = None
    completed_by_id: int | None = None
    assigned_to_id: int | None = None
    notes: str | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Volunteer Assignment Schemas
# ============================================================================

class ProgramVolunteerAssignmentCreate(StrictInputSchema):
    plan_id: int
    volunteer_id: int | None = None
    user_id: int | None = None
    role: str = Field(..., min_length=1, max_length=100)
    notes: str | None = None


class ProgramVolunteerAssignmentUpdate(StrictInputSchema):
    volunteer_id: int | None = None
    user_id: int | None = None
    role: str | None = Field(None, min_length=1, max_length=100)
    status: str | None = None
    hours_worked: float | None = Field(None, ge=0)
    notes: str | None = None


class ProgramVolunteerAssignmentResponse(BaseModel):
    id: int
    plan_id: int
    volunteer_id: int | None = None
    user_id: int | None = None
    role: str
    status: str
    confirmed_at: datetime | None = None
    hours_worked: float | None = None
    notes: str | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Evaluation Schemas
# ============================================================================

class ProgramEvaluationCreate(StrictInputSchema):
    plan_id: int
    overall_rating: str | None = None
    content_quality_rating: str | None = None
    logistics_rating: str | None = None
    engagement_rating: str | None = None
    expected_attendance: int | None = Field(None, ge=0)
    actual_attendance: int | None = Field(None, ge=0)
    new_patron_count: int | None = Field(None, ge=0)
    repeat_attendee_count: int | None = Field(None, ge=0)
    budget_variance: MoneyDecimal | None = None
    cost_per_attendee: MoneyDecimal | None = Field(None, ge=0)
    staff_notes: str | None = None
    what_went_well: str | None = None
    what_to_improve: str | None = None
    attendee_feedback_summary: str | None = None
    recommend_repeat: bool | None = None
    recommended_changes: str | None = None
    comparison_metrics: dict | None = None


class ProgramEvaluationUpdate(ProgramEvaluationCreate, StrictInputSchema):
    plan_id: int | None = None  # type: ignore


class ProgramEvaluationResponse(BaseModel):
    id: int
    plan_id: int
    overall_rating: str | None = None
    content_quality_rating: str | None = None
    logistics_rating: str | None = None
    engagement_rating: str | None = None
    expected_attendance: int | None = None
    actual_attendance: int | None = None
    new_patron_count: int | None = None
    repeat_attendee_count: int | None = None
    budget_variance: MoneyDecimal | None = None
    cost_per_attendee: MoneyDecimal | None = None
    staff_notes: str | None = None
    what_went_well: str | None = None
    what_to_improve: str | None = None
    attendee_feedback_summary: str | None = None
    recommend_repeat: bool | None = None
    recommended_changes: str | None = None
    comparison_metrics: dict | None = None
    evaluated_by_id: int | None = None
    evaluated_at: datetime | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Copy Program Schema
# ============================================================================

class CopyProgramRequest(StrictInputSchema):
    source_program_id: int
    new_title: str = Field(..., min_length=1, max_length=255)
    new_program_date: date
    new_start_time: str = Field(..., max_length=10)  # HH:MM format
    new_end_time: str | None = Field(None, max_length=10)
    branch_id: int | None = None
    copy_budget: bool = True
    copy_supplies: bool = True
    copy_marketing_timeline: bool = True
    copy_volunteer_roles: bool = True
    notes: str | None = None


# ============================================================================
# Success Metrics Comparison
# ============================================================================

class SuccessMetricsComparison(BaseModel):
    program_id: int
    program_title: str
    program_date: date
    attendance: int | None = None
    target_attendance: int | None = None
    attendance_rate: float | None = None
    total_budget: MoneyDecimal | None = None
    total_spent: MoneyDecimal | None = None
    cost_per_attendee: MoneyDecimal | None = None
    overall_rating: str | None = None
    recommend_repeat: bool | None = None


class SuccessMetricsComparisonResponse(BaseModel):
    programs: list[SuccessMetricsComparison]
    summary: dict | None = None  # aggregate stats


# Rebuild forward refs for nested models
ProgramPlanDetailResponse.model_rebuild()
