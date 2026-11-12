# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, date, timezone
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas._base import MoneyDecimal, StrictInputSchema

from ..models.makerspace import (
    ResourceType, ResourceStatus, MakerspaceReservationStatus, JobStatus, JobPriority,
    CertificationStatus, MakerspaceIncidentSeverity, MaintenanceType, MaintenanceStatus,
    ConsumableUnit, PaymentStatus
)
from .common import PaginatedResponse


def ensure_timezone_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# =============================================================================
# Makerspace Resource Schemas
# =============================================================================

class MakerspaceResourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5000)
    resource_type: ResourceType
    location: str | None = Field(None, max_length=200)
    asset_tag: str | None = Field(None, max_length=50)
    serial_number: str | None = Field(None, max_length=100)
    manufacturer: str | None = Field(None, max_length=200)
    model: str | None = Field(None, max_length=200)
    status: ResourceStatus = ResourceStatus.available
    status_notes: str | None = None
    requires_certification: bool = True
    certification_type_id: int | None = None
    minimum_age: int = Field(default=0, ge=0)
    hourly_cost: MoneyDecimal = Field(default=Decimal("0.00"), ge=0)
    setup_fee: MoneyDecimal = Field(default=Decimal("0.00"), ge=0)
    max_reservation_hours: int = Field(default=4, ge=1, le=24)
    min_reservation_hours: int = Field(default=1, ge=1, le=24)
    advance_booking_days: int = Field(default=14, ge=1, le=90)
    buffer_minutes: int = Field(default=15, ge=0, le=120)
    available_from: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    available_until: str = Field(default="21:00", pattern=r"^\d{2}:\d{2}$")
    available_days: list[int] = Field(default=[0, 1, 2, 3, 4, 5])
    specifications: str | None = None
    build_volume_x: int | None = Field(None, ge=0)
    build_volume_y: int | None = Field(None, ge=0)
    build_volume_z: int | None = Field(None, ge=0)
    supported_materials: str | None = None
    supported_file_formats: str | None = None
    image_url: str | None = Field(None, max_length=500)
    manual_url: str | None = Field(None, max_length=500)
    safety_guidelines_url: str | None = Field(None, max_length=500)
    maintenance_interval_days: int = Field(default=30, ge=1)

    @field_validator("available_days", mode="before")
    @classmethod
    def validate_days(cls, v):
        if isinstance(v, str):
            import json
            v = json.loads(v)
        for day in v:
            if day < 0 or day > 6:
                raise ValueError("Days must be 0-6 (Monday=0, Sunday=6)")
        return v


class MakerspaceResourceCreate(StrictInputSchema, MakerspaceResourceBase):
    pass


class MakerspaceResourceUpdate(StrictInputSchema):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    resource_type: ResourceType | None = None
    location: str | None = None
    status: ResourceStatus | None = None
    status_notes: str | None = None
    requires_certification: bool | None = None
    certification_type_id: int | None = None
    minimum_age: int | None = Field(None, ge=0)
    hourly_cost: MoneyDecimal | None = Field(None, ge=0)
    setup_fee: MoneyDecimal | None = Field(None, ge=0)
    max_reservation_hours: int | None = Field(None, ge=1, le=24)
    min_reservation_hours: int | None = Field(None, ge=1, le=24)
    advance_booking_days: int | None = Field(None, ge=1, le=90)
    buffer_minutes: int | None = Field(None, ge=0, le=120)
    available_from: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    available_until: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    available_days: list[int] | None = None
    specifications: str | None = None
    build_volume_x: int | None = None
    build_volume_y: int | None = None
    build_volume_z: int | None = None
    supported_materials: str | None = None
    supported_file_formats: str | None = None
    image_url: str | None = None
    manual_url: str | None = None
    safety_guidelines_url: str | None = None
    maintenance_interval_days: int | None = Field(None, ge=1)
    is_active: bool | None = None


class MakerspaceResourceResponse(MakerspaceResourceBase):
    id: int
    is_active: bool
    total_reservations: int
    total_hours_used: MoneyDecimal
    total_revenue: MoneyDecimal
    last_maintenance_date: date | None
    next_maintenance_date: date | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class MakerspaceResourceSummary(BaseModel):
    id: int
    name: str
    resource_type: ResourceType
    status: ResourceStatus
    location: str | None
    hourly_cost: MoneyDecimal
    requires_certification: bool
    certification_type_id: int | None = None

    class Config:
        from_attributes = True


# =============================================================================
# Certification Type Schemas
# =============================================================================

class CertificationTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    training_duration_hours: MoneyDecimal = Field(default=Decimal("1.00"), ge=0)
    requires_safety_quiz: bool = True
    passing_score: int = Field(default=80, ge=0, le=100)
    validity_months: int = Field(default=12, ge=0)
    renewal_training_hours: MoneyDecimal = Field(default=Decimal("0.50"), ge=0)
    certification_fee: MoneyDecimal = Field(default=Decimal("0.00"), ge=0)
    renewal_fee: MoneyDecimal = Field(default=Decimal("0.00"), ge=0)
    prerequisites: str | None = None
    training_materials_url: str | None = Field(None, max_length=500)
    safety_video_url: str | None = Field(None, max_length=500)


class CertificationTypeCreate(StrictInputSchema, CertificationTypeBase):
    pass


class CertificationTypeUpdate(StrictInputSchema):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    training_duration_hours: MoneyDecimal | None = Field(None, ge=0)
    requires_safety_quiz: bool | None = None
    passing_score: int | None = Field(None, ge=0, le=100)
    validity_months: int | None = Field(None, ge=0)
    renewal_training_hours: MoneyDecimal | None = Field(None, ge=0)
    certification_fee: MoneyDecimal | None = Field(None, ge=0)
    renewal_fee: MoneyDecimal | None = Field(None, ge=0)
    prerequisites: str | None = None
    training_materials_url: str | None = None
    safety_video_url: str | None = None
    is_active: bool | None = None


class CertificationTypeResponse(CertificationTypeBase):
    id: int
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# =============================================================================
# Patron Certification Schemas
# =============================================================================

class CertificationBase(BaseModel):
    certification_type_id: int
    notes: str | None = None


class CertificationCreate(StrictInputSchema, CertificationBase):
    user_id: int


class CertificationUpdate(StrictInputSchema):
    status: CertificationStatus | None = None
    notes: str | None = None
    suspended_reason: str | None = None


class CertificationResponse(BaseModel):
    id: int
    user_id: int
    certification_type_id: int
    status: CertificationStatus
    training_completed_at: datetime | None
    quiz_score: int | None
    quiz_attempts: int
    certified_at: datetime | None
    expires_at: datetime | None
    certified_by_id: int | None
    suspended_at: datetime | None
    suspended_reason: str | None
    renewal_count: int
    notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class CertificationWithDetails(CertificationResponse):
    certification_type_name: str | None = None
    user_name: str | None = None
    certified_by_name: str | None = None


class QuizSubmission(BaseModel):
    answers: dict[str, str | int]  # question_id -> answer


class QuizResult(BaseModel):
    score: int
    passed: bool
    passing_score: int
    feedback: dict[str, str] | None = None


# =============================================================================
# Reservation Schemas
# =============================================================================

class ReservationBase(BaseModel):
    resource_id: int
    start_time: datetime
    end_time: datetime
    project_name: str | None = Field(None, max_length=200)
    project_description: str | None = None
    notes: str | None = None

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def validate_times(cls, v: datetime) -> datetime:
        return ensure_timezone_aware(v)

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class ReservationCreate(StrictInputSchema, ReservationBase):
    pass


class ReservationUpdate(StrictInputSchema):
    start_time: datetime | None = None
    end_time: datetime | None = None
    project_name: str | None = None
    project_description: str | None = None
    notes: str | None = None

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def validate_times(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            return ensure_timezone_aware(v)
        return v


class ReservationResponse(BaseModel):
    id: int
    user_id: int | None
    resource_id: int
    status: MakerspaceReservationStatus
    start_time: datetime
    end_time: datetime
    checked_in_at: datetime | None
    checked_out_at: datetime | None
    project_name: str | None
    project_description: str | None
    estimated_cost: MoneyDecimal
    actual_cost: MoneyDecimal | None
    consumables_cost: MoneyDecimal
    payment_status: PaymentStatus
    approved_by_id: int | None
    approved_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    notes: str | None
    staff_notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ReservationWithDetails(ReservationResponse):
    user_name: str | None = None
    user_email: str | None = None
    resource_name: str | None = None
    resource_type: ResourceType | None = None


class ReservationCheckIn(BaseModel):
    notes: str | None = None


class ReservationCheckOut(BaseModel):
    notes: str | None = None
    consumable_usage: list["ConsumableUsageCreate"] | None = None


class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    is_available: bool
    reservation_id: int | None = None


class AvailabilityResponse(BaseModel):
    resource_id: int
    date: date
    slots: list[TimeSlot]


# =============================================================================
# Job Queue Schemas
# =============================================================================

class JobBase(BaseModel):
    resource_id: int | None = None
    project_name: str = Field(..., min_length=1, max_length=200)
    project_description: str | None = None
    material_type: str | None = Field(None, max_length=50)
    material_color: str | None = Field(None, max_length=50)
    infill_percentage: int | None = Field(None, ge=0, le=100)
    layer_height: MoneyDecimal | None = Field(None, ge=Decimal("0.05"), le=Decimal("1.0"))
    supports_needed: bool = False
    contact_email: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=20)
    notes: str | None = None


class JobCreate(StrictInputSchema, JobBase):
    pass


class JobUpdate(StrictInputSchema):
    project_name: str | None = Field(None, min_length=1, max_length=200)
    project_description: str | None = None
    material_type: str | None = None
    material_color: str | None = None
    infill_percentage: int | None = Field(None, ge=0, le=100)
    layer_height: MoneyDecimal | None = None
    supports_needed: bool | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str | None = None


class JobResponse(BaseModel):
    id: int
    job_number: str
    user_id: int | None
    resource_id: int | None
    status: JobStatus
    priority: JobPriority
    queue_position: int | None
    project_name: str
    project_description: str | None
    file_name: str | None
    file_size_bytes: int | None
    file_format: str | None
    material_type: str | None
    material_color: str | None
    infill_percentage: int | None
    layer_height: MoneyDecimal | None
    supports_needed: bool
    estimated_print_time_minutes: int | None
    estimated_material_grams: MoneyDecimal | None
    actual_print_time_minutes: int | None
    actual_material_grams: MoneyDecimal | None
    estimated_cost: MoneyDecimal
    actual_cost: MoneyDecimal | None
    material_cost: MoneyDecimal
    machine_time_cost: MoneyDecimal
    payment_status: PaymentStatus
    reviewed_by_id: int | None
    reviewed_at: datetime | None
    review_notes: str | None
    rejection_reason: str | None
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    failure_reason: str | None
    ready_for_pickup_at: datetime | None
    pickup_notified_at: datetime | None
    picked_up_at: datetime | None
    contact_email: str | None
    contact_phone: str | None
    notes: str | None
    staff_notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class JobWithDetails(JobResponse):
    user_name: str | None = None
    user_email: str | None = None
    resource_name: str | None = None
    reviewed_by_name: str | None = None


class JobReview(BaseModel):
    approved: bool
    notes: str | None = None
    rejection_reason: str | None = None
    estimated_print_time_minutes: int | None = Field(None, ge=0)
    estimated_material_grams: MoneyDecimal | None = Field(None, ge=0)
    estimated_cost: MoneyDecimal | None = Field(None, ge=0)
    priority: JobPriority | None = None


class JobStatusUpdate(StrictInputSchema):
    status: JobStatus
    notes: str | None = None
    failure_reason: str | None = None
    actual_print_time_minutes: int | None = None
    actual_material_grams: MoneyDecimal | None = None


class JobComplete(BaseModel):
    actual_print_time_minutes: int
    actual_material_grams: MoneyDecimal
    notes: str | None = None
    consumable_usage: list["ConsumableUsageCreate"] | None = None


class JobPickup(BaseModel):
    notes: str | None = None


# =============================================================================
# Payment Schemas
# =============================================================================

class PaymentBase(BaseModel):
    amount: MoneyDecimal = Field(..., ge=0)
    payment_method: str = Field(..., max_length=50)
    notes: str | None = None


class PaymentCreate(StrictInputSchema, PaymentBase):
    user_id: int
    reservation_id: int | None = None
    job_id: int | None = None


class PaymentResponse(BaseModel):
    id: int
    user_id: int | None
    amount: MoneyDecimal
    payment_method: str
    status: PaymentStatus
    payment_reference: str | None
    receipt_number: str | None
    machine_time_fee: MoneyDecimal
    consumables_fee: MoneyDecimal
    setup_fee: MoneyDecimal
    refund_amount: MoneyDecimal
    refunded_at: datetime | None
    refund_reason: str | None
    processed_by_id: int | None
    notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class PaymentRefund(BaseModel):
    amount: MoneyDecimal = Field(..., gt=0)
    reason: str


# =============================================================================
# Consumable Schemas
# =============================================================================

class ConsumableBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    sku: str | None = Field(None, max_length=50)
    category: str | None = Field(None, max_length=100)
    material_type: str | None = Field(None, max_length=50)
    color: str | None = Field(None, max_length=50)
    diameter_mm: MoneyDecimal | None = Field(None, ge=0)
    unit: ConsumableUnit = ConsumableUnit.grams
    quantity_in_stock: MoneyDecimal = Field(default=Decimal("0.00"), ge=0)
    reorder_threshold: MoneyDecimal = Field(default=Decimal("100.00"), ge=0)
    reorder_quantity: MoneyDecimal = Field(default=Decimal("1000.00"), ge=0)
    cost_per_unit: MoneyDecimal = Field(default=Decimal("0.00"), ge=0)
    price_per_unit: MoneyDecimal = Field(default=Decimal("0.00"), ge=0)
    supplier_name: str | None = Field(None, max_length=200)
    supplier_sku: str | None = Field(None, max_length=100)
    compatible_resources: str | None = None


class ConsumableCreate(StrictInputSchema, ConsumableBase):
    pass


class ConsumableUpdate(StrictInputSchema):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    sku: str | None = None
    category: str | None = None
    material_type: str | None = None
    color: str | None = None
    diameter_mm: MoneyDecimal | None = None
    unit: ConsumableUnit | None = None
    quantity_in_stock: MoneyDecimal | None = Field(None, ge=0)
    reorder_threshold: MoneyDecimal | None = Field(None, ge=0)
    reorder_quantity: MoneyDecimal | None = Field(None, ge=0)
    cost_per_unit: MoneyDecimal | None = Field(None, ge=0)
    price_per_unit: MoneyDecimal | None = Field(None, ge=0)
    supplier_name: str | None = None
    supplier_sku: str | None = None
    compatible_resources: str | None = None
    is_active: bool | None = None


class ConsumableResponse(ConsumableBase):
    id: int
    is_active: bool
    last_order_date: date | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ConsumableStockAdjustment(BaseModel):
    quantity: MoneyDecimal = Field(...)  # Positive = add, negative = subtract
    reason: str = Field(..., max_length=500)


class ConsumableUsageCreate(StrictInputSchema):
    consumable_id: int
    quantity_used: MoneyDecimal = Field(..., gt=0)


class ConsumableUsageResponse(BaseModel):
    id: int
    consumable_id: int
    job_id: int | None
    reservation_id: int | None
    resource_id: int | None
    quantity_used: MoneyDecimal
    cost: MoneyDecimal
    recorded_by_id: int | None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class ConsumableUsageWithDetails(ConsumableUsageResponse):
    consumable_name: str | None = None
    resource_name: str | None = None


# =============================================================================
# Safety Incident Schemas
# =============================================================================

class SafetyIncidentBase(BaseModel):
    resource_id: int | None = None
    incident_date: datetime
    severity: MakerspaceIncidentSeverity = MakerspaceIncidentSeverity.minor
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(..., min_length=1)
    location: str | None = Field(None, max_length=200)
    injuries_reported: bool = False
    injury_description: str | None = None
    equipment_damage: bool = False
    damage_description: str | None = None
    immediate_action_taken: str | None = None
    first_aid_administered: bool = False
    emergency_services_called: bool = False

    @field_validator("incident_date", mode="after")
    @classmethod
    def validate_incident_date(cls, v: datetime) -> datetime:
        return ensure_timezone_aware(v)


class SafetyIncidentCreate(StrictInputSchema, SafetyIncidentBase):
    involved_user_id: int | None = None


class SafetyIncidentUpdate(StrictInputSchema):
    severity: MakerspaceIncidentSeverity | None = None
    title: str | None = Field(None, max_length=300)
    description: str | None = None
    location: str | None = None
    injuries_reported: bool | None = None
    injury_description: str | None = None
    equipment_damage: bool | None = None
    damage_description: str | None = None
    immediate_action_taken: str | None = None
    first_aid_administered: bool | None = None
    emergency_services_called: bool | None = None
    investigation_notes: str | None = None
    root_cause: str | None = None
    corrective_actions: str | None = None
    corrective_action_deadline: date | None = None
    follow_up_required: bool | None = None
    follow_up_notes: str | None = None


class SafetyIncidentResponse(BaseModel):
    id: int
    incident_number: str
    resource_id: int | None
    reported_by_id: int | None
    involved_user_id: int | None
    incident_date: datetime
    severity: MakerspaceIncidentSeverity
    title: str
    description: str
    location: str | None
    injuries_reported: bool
    injury_description: str | None
    equipment_damage: bool
    damage_description: str | None
    immediate_action_taken: str | None
    first_aid_administered: bool
    emergency_services_called: bool
    investigated_by_id: int | None
    investigation_notes: str | None
    root_cause: str | None
    corrective_actions: str | None
    corrective_action_deadline: date | None
    corrective_action_completed_at: datetime | None
    follow_up_required: bool
    follow_up_notes: str | None
    is_resolved: bool
    resolved_at: datetime | None
    resolved_by_id: int | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class SafetyIncidentWithDetails(SafetyIncidentResponse):
    resource_name: str | None = None
    reported_by_name: str | None = None
    involved_user_name: str | None = None
    investigated_by_name: str | None = None
    resolved_by_name: str | None = None


class SafetyIncidentResolve(BaseModel):
    resolution_notes: str | None = None


# =============================================================================
# Equipment Maintenance Schemas
# =============================================================================

class MaintenanceBase(BaseModel):
    resource_id: int
    maintenance_type: MaintenanceType = MaintenanceType.preventive
    scheduled_date: date
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    checklist: str | None = None


class MaintenanceCreate(StrictInputSchema, MaintenanceBase):
    pass


class MaintenanceUpdate(StrictInputSchema):
    maintenance_type: MaintenanceType | None = None
    scheduled_date: date | None = None
    title: str | None = Field(None, max_length=300)
    description: str | None = None
    checklist: str | None = None
    status: MaintenanceStatus | None = None


class MaintenanceResponse(BaseModel):
    id: int
    resource_id: int
    maintenance_type: MaintenanceType
    status: MaintenanceStatus
    scheduled_date: date
    scheduled_by_id: int | None
    title: str
    description: str | None
    checklist: str | None
    started_at: datetime | None
    completed_at: datetime | None
    performed_by_id: int | None
    findings: str | None
    parts_replaced: str | None
    parts_cost: MoneyDecimal
    labor_hours: MoneyDecimal
    next_maintenance_date: date | None
    notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class MaintenanceWithDetails(MaintenanceResponse):
    resource_name: str | None = None
    scheduled_by_name: str | None = None
    performed_by_name: str | None = None


class MaintenanceComplete(BaseModel):
    findings: str | None = None
    parts_replaced: str | None = None
    parts_cost: MoneyDecimal = Field(default=Decimal("0.00"), ge=0)
    labor_hours: MoneyDecimal = Field(default=Decimal("0.00"), ge=0)
    notes: str | None = None
    next_maintenance_date: date | None = None


# =============================================================================
# Reports & Analytics Schemas
# =============================================================================

class ResourceUtilizationReport(BaseModel):
    resource_id: int
    resource_name: str
    resource_type: ResourceType
    total_reservations: int
    total_hours_reserved: MoneyDecimal
    total_hours_used: MoneyDecimal
    utilization_percentage: MoneyDecimal
    total_revenue: MoneyDecimal
    period_start: date
    period_end: date


class RevenueReport(BaseModel):
    period_start: date
    period_end: date
    total_revenue: MoneyDecimal
    machine_time_revenue: MoneyDecimal
    consumables_revenue: MoneyDecimal
    setup_fees_revenue: MoneyDecimal
    certification_fees_revenue: MoneyDecimal
    by_resource_type: dict[str, MoneyDecimal]
    by_resource: list[dict]


class PopularEquipmentReport(BaseModel):
    period_start: date
    period_end: date
    items: list[dict]  # resource_id, name, type, reservation_count, hours_used, revenue


class PatronUsageReport(BaseModel):
    user_id: int
    user_name: str
    total_reservations: int
    total_hours: MoneyDecimal
    total_jobs: int
    total_spent: MoneyDecimal
    certifications: list[str]
    most_used_resources: list[str]


class IncidentSummaryReport(BaseModel):
    period_start: date
    period_end: date
    total_incidents: int
    by_severity: dict[str, int]
    by_resource: list[dict]
    unresolved_count: int


class ConsumableInventoryReport(BaseModel):
    low_stock_items: list[ConsumableResponse]
    out_of_stock_items: list[ConsumableResponse]
    total_inventory_value: MoneyDecimal
    usage_summary: list[dict]  # consumable_id, name, quantity_used, cost


# =============================================================================
# Cost Calculation Schemas
# =============================================================================

class CostEstimate(BaseModel):
    machine_time_hours: MoneyDecimal
    machine_time_cost: MoneyDecimal
    consumables_cost: MoneyDecimal
    setup_fee: MoneyDecimal
    total_cost: MoneyDecimal
    breakdown: list[dict]


class CostCalculationRequest(StrictInputSchema):
    resource_id: int
    duration_hours: MoneyDecimal = Field(..., gt=0)
    consumables: list[ConsumableUsageCreate] | None = None


# =============================================================================
# Paginated Response Types
# =============================================================================

# Type aliases for paginated responses
PaginatedMakerspaceResourceSummaryResponse = PaginatedResponse[MakerspaceResourceSummary]
PaginatedReservationWithDetailsResponse = PaginatedResponse[ReservationWithDetails]
PaginatedJobWithDetailsResponse = PaginatedResponse[JobWithDetails]


# =============================================================================
# Staff Endpoint List Response Schemas
# =============================================================================

class StaffResourceListResponse(BaseModel):
    items: list[MakerspaceResourceResponse]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")


class StaffCertificationListItem(CertificationResponse):
    certification_type_name: str | None = None
    user_name: str | None = None


class StaffCertificationListResponse(BaseModel):
    items: list[StaffCertificationListItem]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")


class StaffReservationListResponse(BaseModel):
    items: list[ReservationWithDetails]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")


class StaffJobListResponse(BaseModel):
    items: list[JobWithDetails]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")


class StaffConsumableListResponse(BaseModel):
    items: list[ConsumableResponse]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")


class StaffIncidentListItem(SafetyIncidentResponse):
    resource_name: str | None = None


class StaffIncidentListResponse(BaseModel):
    items: list[StaffIncidentListItem]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")


class StaffMaintenanceListItem(MaintenanceResponse):
    resource_name: str | None = None


class StaffMaintenanceListResponse(BaseModel):
    items: list[StaffMaintenanceListItem]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")


# =============================================================================
# Staff Report Response Schemas
# =============================================================================

class ResourceRevenueItem(BaseModel):
    resource_id: int
    resource_name: str
    resource_type: str
    revenue: MoneyDecimal


class StaffRevenueReportResponse(BaseModel):
    period_start: date
    period_end: date
    total_revenue: MoneyDecimal
    machine_time_revenue: MoneyDecimal
    consumables_revenue: MoneyDecimal
    setup_fees_revenue: MoneyDecimal
    certification_fees_revenue: MoneyDecimal
    by_resource_type: dict[str, MoneyDecimal]
    by_resource: list[ResourceRevenueItem]


class ResourceIncidentItem(BaseModel):
    resource_id: int
    resource_name: str
    incident_count: int


class StaffIncidentSummaryReportResponse(BaseModel):
    period_start: date
    period_end: date
    total_incidents: int
    by_severity: dict[str, int]
    by_resource: list[ResourceIncidentItem]
    unresolved_count: int


# =============================================================================
# Queue Status Schemas
# =============================================================================

class QueueJobItem(BaseModel):
    position: int = Field(..., ge=1, description="Position in the queue (1-indexed)")
    job_number: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    estimated_time_minutes: int | None = Field(None, description="Estimated print/processing time")
    resource_name: str | None = Field(None, description="Name of the assigned resource")
    submitted_at: str | None = Field(None, description="ISO timestamp when job was submitted")


class QueueStatusResponse(BaseModel):
    queue: list[QueueJobItem] = Field(..., description="List of jobs in the queue")
    total_jobs: int = Field(..., ge=0, description="Total number of jobs in the queue")


# =============================================================================
# Operating Hours & Dynamic Time Slots
# =============================================================================

class OperatingHoursDay(BaseModel):
    open: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    close: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    is_closed: bool = False


class ResourceOperatingHours(BaseModel):
    resource_id: int
    resource_name: str
    available_from: str
    available_until: str
    available_days: list[int]
    buffer_minutes: int
    min_reservation_hours: int
    max_reservation_hours: int


class DynamicTimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    is_available: bool
    is_past: bool = False
    reservation_id: int | None = None


class DynamicAvailabilityResponse(BaseModel):
    resource_id: int
    resource_name: str
    date: date
    operating_hours: ResourceOperatingHours
    slots: list[DynamicTimeSlot]
    waitlist_count: int = 0


# =============================================================================
# Waitlist Schemas
# =============================================================================

class WaitlistStatus(StrEnum):
    waiting = "waiting"
    notified = "notified"
    expired = "expired"
    cancelled = "cancelled"
    fulfilled = "fulfilled"


class WaitlistBase(BaseModel):
    resource_id: int
    preferred_date: date
    preferred_start_time: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    preferred_end_time: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    flexible_dates: bool = False
    notify_email: bool = True
    notify_sms: bool = False
    contact_phone: str | None = Field(None, max_length=20)
    notes: str | None = None


class WaitlistCreate(StrictInputSchema, WaitlistBase):
    pass


class WaitlistResponse(BaseModel):
    id: int
    user_id: int
    resource_id: int
    preferred_date: date
    preferred_start_time: str | None
    preferred_end_time: str | None
    flexible_dates: bool
    status: WaitlistStatus
    position: int | None
    notified_at: datetime | None
    notification_expires_at: datetime | None
    notify_email: bool
    notify_sms: bool
    contact_phone: str | None
    notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class WaitlistWithDetails(WaitlistResponse):
    user_name: str | None = None
    user_email: str | None = None
    resource_name: str | None = None
    resource_type: str | None = None


class WaitlistPositionResponse(BaseModel):
    waitlist_id: int
    position: int
    total_waiting: int
    estimated_wait: str | None = None  # e.g., "~2-3 days"


# =============================================================================
# Workshop Schemas
# =============================================================================

class WorkshopStatus(StrEnum):
    draft = "draft"
    published = "published"
    cancelled = "cancelled"
    completed = "completed"


class WorkshopLevel(StrEnum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    all_levels = "all_levels"


class MakerspaceRegistrationStatus(StrEnum):
    registered = "registered"
    waitlisted = "waitlisted"
    confirmed = "confirmed"
    attended = "attended"
    no_show = "no_show"
    cancelled = "cancelled"


class WorkshopBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    short_description: str | None = Field(None, max_length=500)
    is_certification_training: bool = False
    certification_type_id: int | None = None
    start_time: datetime
    end_time: datetime
    duration_minutes: int = Field(..., ge=15)
    location: str | None = Field(None, max_length=200)
    room_id: int | None = None
    is_virtual: bool = False
    virtual_meeting_url: str | None = Field(None, max_length=500)
    max_participants: int = Field(default=10, ge=1)
    min_participants: int = Field(default=1, ge=1)
    instructor_id: int | None = None
    instructor_name: str | None = Field(None, max_length=200)
    instructor_bio: str | None = None
    skill_level: WorkshopLevel = WorkshopLevel.beginner
    prerequisites: str | None = None
    age_requirement: int = Field(default=0, ge=0)
    required_materials: str | None = None
    fee: MoneyDecimal = Field(default=Decimal("0.00"), ge=0)
    materials_fee: MoneyDecimal = Field(default=Decimal("0.00"), ge=0)
    materials_included: bool = True
    registration_opens_at: datetime | None = None
    registration_closes_at: datetime | None = None
    registration_required: bool = True
    cancellation_deadline_hours: int = Field(default=24, ge=0)
    allow_waitlist: bool = True
    resources_used: str | None = None
    image_url: str | None = Field(None, max_length=500)
    syllabus_url: str | None = Field(None, max_length=500)
    materials_list_url: str | None = Field(None, max_length=500)
    tags: list[str] | None = None

    @field_validator("start_time", "end_time", "registration_opens_at", "registration_closes_at", mode="after")
    @classmethod
    def validate_times(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            return ensure_timezone_aware(v)
        return v

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class WorkshopCreate(StrictInputSchema, WorkshopBase):
    pass


class WorkshopUpdate(StrictInputSchema):
    title: str | None = Field(None, max_length=300)
    description: str | None = None
    short_description: str | None = None
    is_certification_training: bool | None = None
    certification_type_id: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_minutes: int | None = Field(None, ge=15)
    location: str | None = None
    room_id: int | None = None
    is_virtual: bool | None = None
    virtual_meeting_url: str | None = None
    max_participants: int | None = Field(None, ge=1)
    min_participants: int | None = Field(None, ge=1)
    instructor_id: int | None = None
    instructor_name: str | None = None
    instructor_bio: str | None = None
    skill_level: WorkshopLevel | None = None
    prerequisites: str | None = None
    age_requirement: int | None = Field(None, ge=0)
    required_materials: str | None = None
    fee: MoneyDecimal | None = Field(None, ge=0)
    materials_fee: MoneyDecimal | None = Field(None, ge=0)
    materials_included: bool | None = None
    registration_opens_at: datetime | None = None
    registration_closes_at: datetime | None = None
    registration_required: bool | None = None
    cancellation_deadline_hours: int | None = Field(None, ge=0)
    allow_waitlist: bool | None = None
    status: WorkshopStatus | None = None
    resources_used: str | None = None
    image_url: str | None = None
    syllabus_url: str | None = None
    materials_list_url: str | None = None
    tags: list[str] | None = None


class WorkshopResponse(BaseModel):
    id: int
    title: str
    description: str | None
    short_description: str | None
    is_certification_training: bool
    certification_type_id: int | None
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    location: str | None
    room_id: int | None
    is_virtual: bool
    virtual_meeting_url: str | None
    max_participants: int
    min_participants: int
    current_participants: int
    allow_waitlist: bool
    waitlist_count: int
    instructor_id: int | None
    instructor_name: str | None
    instructor_bio: str | None
    skill_level: WorkshopLevel
    prerequisites: str | None
    age_requirement: int
    required_materials: str | None
    fee: MoneyDecimal
    materials_fee: MoneyDecimal
    materials_included: bool
    registration_opens_at: datetime | None
    registration_closes_at: datetime | None
    registration_required: bool
    cancellation_deadline_hours: int
    status: WorkshopStatus
    resources_used: str | None
    image_url: str | None
    syllabus_url: str | None
    materials_list_url: str | None
    tags: list[str] | None
    created_by_id: int | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class WorkshopSummary(BaseModel):
    id: int
    title: str
    short_description: str | None
    start_time: datetime
    end_time: datetime
    location: str | None
    is_virtual: bool
    skill_level: WorkshopLevel
    fee: MoneyDecimal
    max_participants: int
    current_participants: int
    spots_remaining: int
    is_full: bool
    has_waitlist: bool
    waitlist_count: int
    is_certification_training: bool
    certification_type_id: int | None
    instructor_name: str | None
    image_url: str | None
    tags: list[str] | None
    status: WorkshopStatus

    class Config:
        from_attributes = True


class WorkshopWithDetails(WorkshopResponse):
    certification_type_name: str | None = None
    instructor_user_name: str | None = None
    room_name: str | None = None
    spots_remaining: int = 0
    is_full: bool = False
    is_registration_open: bool = False


# =============================================================================
# Workshop Registration Schemas
# =============================================================================

class WorkshopRegistrationCreate(StrictInputSchema):
    workshop_id: int
    contact_email: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=20)
    notes: str | None = None


class WorkshopRegistrationResponse(BaseModel):
    id: int
    workshop_id: int
    user_id: int
    status: MakerspaceRegistrationStatus
    waitlist_position: int | None
    contact_email: str | None
    contact_phone: str | None
    payment_status: PaymentStatus
    amount_paid: MoneyDecimal
    checked_in_at: datetime | None
    certification_awarded_id: int | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    refund_issued: bool
    confirmation_sent_at: datetime | None
    reminder_sent_at: datetime | None
    notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class WorkshopRegistrationWithDetails(WorkshopRegistrationResponse):
    workshop_title: str | None = None
    workshop_start_time: datetime | None = None
    workshop_location: str | None = None
    user_name: str | None = None
    user_email: str | None = None


class MyWorkshopRegistration(BaseModel):
    registration_id: int
    workshop_id: int
    workshop_title: str
    workshop_start_time: datetime
    workshop_end_time: datetime
    workshop_location: str | None
    is_virtual: bool
    virtual_meeting_url: str | None
    status: MakerspaceRegistrationStatus
    waitlist_position: int | None
    is_waitlisted: bool
    confirmation_sent: bool
    reminder_sent: bool


# =============================================================================
# Paginated Workshop Responses
# =============================================================================

class PaginatedWorkshopSummaryResponse(BaseModel):
    items: list[WorkshopSummary]
    total: int
    page: int
    per_page: int


class PaginatedWaitlistResponse(BaseModel):
    items: list[WaitlistWithDetails]
    total: int
    page: int
    per_page: int
