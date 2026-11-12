# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas._base import MoneyDecimal, StrictInputSchema

from app.models.equipment import (
    AgreementStatus,
    EquipmentCondition,
    EquipmentStatus,
    EquipmentType,
    EquipmentMaintenanceStatus,
    EquipmentMaintenanceType,
    EquipmentReservationStatus,
)


# ============================================================================
# Equipment Schemas
# ============================================================================


class EquipmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    equipment_type: str
    serial_number: Optional[str] = Field(None, max_length=100)
    barcode: str = Field(..., min_length=1, max_length=50)
    asset_tag: Optional[str] = Field(None, max_length=50)
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    model_year: Optional[int] = None
    requires_agreement: bool = True
    max_checkout_days: int = Field(7, ge=0, le=365)
    fine_per_day: MoneyDecimal = Field(Decimal("5.00"), ge=0)
    max_renewals: int = Field(1, ge=0)
    deposit_required: bool = False
    deposit_amount: Optional[MoneyDecimal] = Field(None, ge=0)
    deposit_refundable: bool = True
    return_instructions: Optional[str] = None
    replacement_cost: Optional[MoneyDecimal] = Field(None, ge=0)
    purchase_price: Optional[MoneyDecimal] = Field(None, ge=0)
    purchase_date: Optional[date] = None
    warranty_expires: Optional[date] = None
    maintenance_schedule_days: Optional[int] = Field(90, ge=1)
    location: Optional[str] = Field(None, max_length=100)
    home_location: Optional[str] = Field(None, max_length=100)
    included_accessories: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)
    is_high_demand: bool = False


class EquipmentCreate(StrictInputSchema, EquipmentBase):
    pass


class EquipmentUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    equipment_type: Optional[str] = None
    serial_number: Optional[str] = Field(None, max_length=100)
    barcode: Optional[str] = Field(None, min_length=1, max_length=50)
    asset_tag: Optional[str] = Field(None, max_length=50)
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    model_year: Optional[int] = None
    status: Optional[EquipmentStatus] = None
    condition: Optional[EquipmentCondition] = None
    requires_agreement: Optional[bool] = None
    max_checkout_days: Optional[int] = Field(None, ge=0, le=365)
    fine_per_day: Optional[MoneyDecimal] = Field(None, ge=0)
    max_renewals: Optional[int] = Field(None, ge=0)
    deposit_required: Optional[bool] = None
    deposit_amount: Optional[MoneyDecimal] = Field(None, ge=0)
    deposit_refundable: Optional[bool] = None
    return_instructions: Optional[str] = None
    replacement_cost: Optional[MoneyDecimal] = Field(None, ge=0)
    purchase_price: Optional[MoneyDecimal] = Field(None, ge=0)
    purchase_date: Optional[date] = None
    warranty_expires: Optional[date] = None
    maintenance_schedule_days: Optional[int] = Field(None, ge=1)
    location: Optional[str] = Field(None, max_length=100)
    home_location: Optional[str] = Field(None, max_length=100)
    included_accessories: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)
    is_high_demand: Optional[bool] = None


class EquipmentResponse(EquipmentBase):
    id: int
    status: EquipmentStatus
    condition: EquipmentCondition
    last_maintenance_date: Optional[date] = None
    next_maintenance_date: Optional[date] = None
    total_checkouts: int
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None
    retired_at: Optional[datetime] = None
    is_available: bool
    needs_maintenance: bool

    class Config:
        from_attributes = True


class EquipmentListResponse(BaseModel):
    items: list[EquipmentResponse]
    total: int
    page: int
    per_page: int
    pages: int


class EquipmentBriefResponse(BaseModel):
    id: int
    name: str
    equipment_type: str
    barcode: str
    status: EquipmentStatus
    condition: EquipmentCondition
    location: Optional[str] = None
    is_available: bool

    class Config:
        from_attributes = True


# ============================================================================
# Equipment Checkout Schemas
# ============================================================================


class EquipmentCheckoutCreate(StrictInputSchema):
    equipment_id: int
    patron_id: Optional[int] = None  # For staff checking out for a patron
    checkout_notes: Optional[str] = None
    deposit_collected: bool = False  # Staff confirms deposit was collected


class EquipmentCheckoutReturn(BaseModel):
    condition_at_return: EquipmentCondition
    return_notes: Optional[str] = None
    refund_deposit: bool = True  # Whether to refund the deposit
    deposit_deduction_amount: Optional[MoneyDecimal] = Field(None, ge=0)  # Amount to deduct from deposit
    deposit_deduction_reason: Optional[str] = None  # Reason for deduction (damage, missing accessory, etc.)


class EquipmentCheckoutRenew(BaseModel):
    notes: Optional[str] = None


class EquipmentReportLost(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    assess_replacement_fee: bool = True
    notes: Optional[str] = None


class EquipmentReportDamaged(BaseModel):
    damage_description: str = Field(..., min_length=1, max_length=1000)
    fee_amount: Optional[MoneyDecimal] = Field(None, ge=0)
    notes: Optional[str] = None


class EquipmentCheckoutResponse(BaseModel):
    id: int
    equipment_id: int
    user_id: Optional[int] = None
    status: str
    checked_out_at: datetime
    due_date: datetime
    returned_at: Optional[datetime] = None
    renewal_count: int
    condition_at_checkout: Optional[EquipmentCondition] = None
    condition_at_return: Optional[EquipmentCondition] = None
    checkout_notes: Optional[str] = None
    return_notes: Optional[str] = None
    fine_amount: MoneyDecimal
    fine_paid: bool

    # Deposit tracking
    deposit_amount: MoneyDecimal = Decimal("0.00")
    deposit_collected: bool = False
    deposit_refunded: bool = False
    deposit_refund_amount: Optional[MoneyDecimal] = None
    deposit_deduction_reason: Optional[str] = None

    # Equipment details
    equipment_name: Optional[str] = None
    equipment_type: Optional[str] = None
    equipment_barcode: Optional[str] = None
    return_instructions: Optional[str] = None
    included_accessories: Optional[str] = None

    # Patron details
    patron_name: Optional[str] = None
    patron_email: Optional[str] = None

    class Config:
        from_attributes = True


class EquipmentCheckoutListResponse(BaseModel):
    items: list[EquipmentCheckoutResponse]
    total: int
    page: int
    per_page: int
    pages: int


# ============================================================================
# Equipment Agreement Schemas
# ============================================================================


class AgreementCreate(StrictInputSchema):
    patron_id: Optional[int] = None  # For staff creating for patron
    equipment_types_covered: Optional[list[EquipmentType]] = None
    notes: Optional[str] = None


class AgreementSign(BaseModel):
    signature: str = Field(..., min_length=1, max_length=255)

    @field_validator('signature')
    @classmethod
    def validate_signature(cls, v):
        if not v or not v.strip():
            raise ValueError('Signature cannot be empty')
        return v.strip()


class AgreementResponse(BaseModel):
    id: int
    user_id: int
    agreement_version: str
    status: AgreementStatus
    agreement_text: str
    signature: Optional[str] = None
    signed_at: Optional[datetime] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    equipment_types_covered: Optional[str] = None
    is_valid: bool
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    # Patron details
    patron_name: Optional[str] = None
    patron_email: Optional[str] = None

    class Config:
        from_attributes = True


class AgreementListResponse(BaseModel):
    items: list[AgreementResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AgreementStatusResponse(BaseModel):
    has_valid_agreement: bool
    agreement_id: Optional[int] = None
    signed_at: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    equipment_types_covered: Optional[list[str]] = None


# ============================================================================
# Equipment Maintenance Schemas
# ============================================================================


class MaintenanceCreate(StrictInputSchema):
    equipment_id: int
    maintenance_type: EquipmentMaintenanceType
    description: Optional[str] = None
    scheduled_date: Optional[date] = None


class MaintenanceUpdate(StrictInputSchema):
    maintenance_type: Optional[EquipmentMaintenanceType] = None
    status: Optional[EquipmentMaintenanceStatus] = None
    description: Optional[str] = None
    issues_found: Optional[str] = None
    work_performed: Optional[str] = None
    scheduled_date: Optional[date] = None
    condition_before: Optional[EquipmentCondition] = None
    condition_after: Optional[EquipmentCondition] = None
    parts_cost: Optional[MoneyDecimal] = Field(None, ge=0)
    labor_cost: Optional[MoneyDecimal] = Field(None, ge=0)
    external_vendor: Optional[str] = Field(None, max_length=255)
    vendor_invoice: Optional[str] = Field(None, max_length=100)
    requires_followup: Optional[bool] = None
    followup_notes: Optional[str] = None
    followup_date: Optional[date] = None


class MaintenanceComplete(BaseModel):
    work_performed: str
    condition_after: EquipmentCondition
    issues_found: Optional[str] = None
    parts_cost: MoneyDecimal = Field(Decimal("0.00"), ge=0)
    labor_cost: MoneyDecimal = Field(Decimal("0.00"), ge=0)
    external_vendor: Optional[str] = None
    vendor_invoice: Optional[str] = None
    requires_followup: bool = False
    followup_notes: Optional[str] = None
    followup_date: Optional[date] = None


class MaintenanceResponse(BaseModel):
    id: int
    equipment_id: int
    maintenance_type: EquipmentMaintenanceType
    status: EquipmentMaintenanceStatus
    description: Optional[str] = None
    issues_found: Optional[str] = None
    work_performed: Optional[str] = None
    scheduled_date: Optional[date] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    condition_before: Optional[EquipmentCondition] = None
    condition_after: Optional[EquipmentCondition] = None
    parts_cost: MoneyDecimal
    labor_cost: MoneyDecimal
    total_cost: MoneyDecimal
    external_vendor: Optional[str] = None
    vendor_invoice: Optional[str] = None
    performed_by_id: Optional[int] = None
    requires_followup: bool
    followup_notes: Optional[str] = None
    followup_date: Optional[date] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    # Equipment details
    equipment_name: Optional[str] = None
    equipment_barcode: Optional[str] = None

    class Config:
        from_attributes = True


class MaintenanceListResponse(BaseModel):
    items: list[MaintenanceResponse]
    total: int
    page: int
    per_page: int
    pages: int


# ============================================================================
# Equipment Reservation Schemas
# ============================================================================


class ReservationCreate(StrictInputSchema):
    equipment_id: int
    start_date: date
    end_date: date
    purpose: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v, info):
        start = info.data.get('start_date')
        if start and v < start:
            raise ValueError('End date must be after start date')
        return v


class ReservationUpdate(StrictInputSchema):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None


class ReservationResponse(BaseModel):
    id: int
    equipment_id: int
    user_id: int
    status: EquipmentReservationStatus
    start_date: date
    end_date: date
    position: int
    notified_at: Optional[datetime] = None
    pickup_deadline: Optional[datetime] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    # Equipment details
    equipment_name: Optional[str] = None
    equipment_type: Optional[str] = None
    equipment_barcode: Optional[str] = None

    # Patron details
    patron_name: Optional[str] = None
    patron_email: Optional[str] = None

    class Config:
        from_attributes = True


class ReservationListResponse(BaseModel):
    items: list[ReservationResponse]
    total: int
    page: int
    per_page: int
    pages: int


class EquipmentAvailabilityResponse(BaseModel):
    equipment_id: int
    is_available: bool
    current_status: EquipmentStatus
    next_available_date: Optional[date] = None
    pending_reservations: int
    queue_position: Optional[int] = None


# ============================================================================
# Equipment Alert Schemas
# ============================================================================


class AlertResponse(BaseModel):
    id: int
    alert_type: str
    priority: str
    status: str
    equipment_id: Optional[int] = None
    checkout_id: Optional[int] = None
    reservation_id: Optional[int] = None
    user_id: Optional[int] = None
    title: str
    message: Optional[str] = None
    days_overdue: Optional[int] = None
    escalation_level: int
    created_at: datetime | None = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # Equipment details
    equipment_name: Optional[str] = None
    equipment_barcode: Optional[str] = None

    # Patron details
    patron_name: Optional[str] = None
    patron_email: Optional[str] = None
    patron_phone: Optional[str] = None

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AlertAcknowledge(BaseModel):
    notes: Optional[str] = None


class AlertResolve(BaseModel):
    resolution_notes: str


# ============================================================================
# Equipment Reports Schemas
# ============================================================================


class EquipmentUtilizationReport(BaseModel):
    equipment_id: int
    equipment_name: str
    equipment_type: str
    total_checkouts: int
    total_days_checked_out: int
    average_checkout_duration: float
    utilization_rate: float  # Percentage of time checked out
    last_checkout_date: Optional[date] = None


class EquipmentConditionTrend(BaseModel):
    equipment_id: int
    equipment_name: str
    current_condition: EquipmentCondition
    condition_history: list[dict]  # List of {date, condition} entries
    degradation_rate: Optional[float] = None  # Percentage per month


class PopularEquipmentReport(BaseModel):
    equipment_id: int
    equipment_name: str
    equipment_type: str
    checkout_count: int
    unique_patrons: int
    average_wait_time_days: Optional[float] = None
    reservation_count: int


class EquipmentDemandAnalytics(BaseModel):

    equipment_type: str
    inventory_count: int
    checked_out_now: int
    active_reservations: int
    overdue_checkouts: int
    period_checkouts: int
    unique_patrons: int
    avg_checkout_days: float
    demand_score: float
    recommended_additional_units: int


class EquipmentReportSummary(BaseModel):
    total_equipment: int
    available_equipment: int
    checked_out_equipment: int
    in_maintenance: int
    damaged_or_lost: int
    overdue_checkouts: int
    pending_reservations: int
    maintenance_due_count: int
    total_replacement_value: MoneyDecimal
    average_utilization_rate: float


class PatronEquipmentHistory(BaseModel):
    patron_id: int
    patron_name: str
    total_checkouts: int
    current_checkouts: int
    overdue_count: int
    lost_count: int
    has_valid_agreement: bool
    agreement_signed_at: Optional[datetime] = None
    checkouts: list[EquipmentCheckoutResponse]


# ============================================================================
# Patron-Facing Schemas
# ============================================================================


class EquipmentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    equipment_type: str
    status: EquipmentStatus
    condition: EquipmentCondition
    barcode: str
    location: Optional[str] = None
    image_url: Optional[str] = None
    max_checkout_days: int
    requires_agreement: bool


class PatronEquipmentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[EquipmentItemResponse]
    total: int


class PatronCheckoutRequest(StrictInputSchema):
    model_config = ConfigDict(from_attributes=True)

    equipment_id: int


class PatronCheckoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    equipment_name: Optional[str] = None
    checked_out_at: datetime
    due_date: datetime
    status: str


class PatronLoanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    equipment_name: Optional[str] = None
    checked_out_at: datetime
    due_date: datetime
    returned_at: Optional[datetime] = None
    status: str
    is_overdue: bool = False


class PatronLoanListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[PatronLoanResponse]
