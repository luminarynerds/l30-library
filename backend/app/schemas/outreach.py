# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from typing import ClassVar, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas._base import StrictInputSchema

from ..models.outreach import (
    BulkCheckoutStatus, DepositStatus, DepositType, InstitutionalCardStatus,
    OutreachPartnerStatus, PartnerType, SchoolLevel, VisitStatus, VisitType
)


# =============================================================================
# Outreach Partner Schemas
# =============================================================================

class OutreachPartnerContactCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=200)
    title: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=30)
    role: Optional[str] = Field(None, max_length=100)
    is_primary: bool = False
    receives_notifications: bool = True
    preferred_contact_method: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class OutreachPartnerContactResponse(BaseModel):
    id: int
    partner_id: int
    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_primary: bool
    receives_notifications: bool
    preferred_contact_method: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OutreachPartnerCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=300)
    partner_type: PartnerType = PartnerType.SCHOOL
    status: OutreachPartnerStatus = OutreachPartnerStatus.ACTIVE

    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)

    # Primary contact
    primary_contact_name: Optional[str] = Field(None, max_length=200)
    primary_contact_title: Optional[str] = Field(None, max_length=100)
    primary_contact_email: Optional[str] = Field(None, max_length=255)
    primary_contact_phone: Optional[str] = Field(None, max_length=30)
    secondary_contact_name: Optional[str] = Field(None, max_length=200)
    secondary_contact_email: Optional[str] = Field(None, max_length=255)
    secondary_contact_phone: Optional[str] = Field(None, max_length=30)

    # School-specific
    school_level: Optional[SchoolLevel] = None
    school_district: Optional[str] = Field(None, max_length=200)
    student_count: Optional[int] = Field(None, ge=0)
    teacher_count: Optional[int] = Field(None, ge=0)

    # Partnership details
    partnership_start_date: Optional[date] = None
    partnership_end_date: Optional[date] = None
    agreement_document_url: Optional[str] = Field(None, max_length=500)
    service_area: Optional[str] = Field(None, max_length=200)

    # Service configuration
    allows_bulk_checkout: bool = True
    allows_institutional_card: bool = True
    requires_deposit: bool = False
    default_deposit_amount: float = Field(default=0.0, ge=0)
    checkout_limit: int = Field(default=100, ge=1)
    loan_period_days: int = Field(default=28, ge=1)

    # Metadata
    notes: Optional[str] = None
    tags: list[str] = []
    custom_fields: dict = {}


class OutreachPartnerUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=300)
    partner_type: Optional[PartnerType] = None
    status: Optional[OutreachPartnerStatus] = None

    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)

    primary_contact_name: Optional[str] = Field(None, max_length=200)
    primary_contact_title: Optional[str] = Field(None, max_length=100)
    primary_contact_email: Optional[str] = Field(None, max_length=255)
    primary_contact_phone: Optional[str] = Field(None, max_length=30)
    secondary_contact_name: Optional[str] = Field(None, max_length=200)
    secondary_contact_email: Optional[str] = Field(None, max_length=255)
    secondary_contact_phone: Optional[str] = Field(None, max_length=30)

    school_level: Optional[SchoolLevel] = None
    school_district: Optional[str] = Field(None, max_length=200)
    student_count: Optional[int] = Field(None, ge=0)
    teacher_count: Optional[int] = Field(None, ge=0)

    partnership_start_date: Optional[date] = None
    partnership_end_date: Optional[date] = None
    agreement_document_url: Optional[str] = Field(None, max_length=500)
    service_area: Optional[str] = Field(None, max_length=200)

    allows_bulk_checkout: Optional[bool] = None
    allows_institutional_card: Optional[bool] = None
    requires_deposit: Optional[bool] = None
    default_deposit_amount: Optional[float] = Field(None, ge=0)
    checkout_limit: Optional[int] = Field(None, ge=1)
    loan_period_days: Optional[int] = Field(None, ge=1)

    notes: Optional[str] = None
    tags: Optional[list[str]] = None
    custom_fields: Optional[dict] = None


class OutreachPartnerResponse(BaseModel):
    id: int
    name: str
    partner_type: str
    status: str

    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    primary_contact_name: Optional[str] = None
    primary_contact_title: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None
    secondary_contact_name: Optional[str] = None
    secondary_contact_email: Optional[str] = None
    secondary_contact_phone: Optional[str] = None

    school_level: Optional[str] = None
    school_district: Optional[str] = None
    student_count: Optional[int] = None
    teacher_count: Optional[int] = None

    partnership_start_date: Optional[date] = None
    partnership_end_date: Optional[date] = None
    agreement_document_url: Optional[str] = None
    service_area: Optional[str] = None

    allows_bulk_checkout: bool
    allows_institutional_card: bool
    requires_deposit: bool
    default_deposit_amount: float
    checkout_limit: int
    loan_period_days: int

    notes: Optional[str] = None
    tags: list[str] = []
    custom_fields: dict = {}

    created_by_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    # Related counts (populated by API)
    active_bulk_checkouts: int = 0
    active_institutional_cards: int = 0
    total_visits: int = 0
    pending_deposits: float = 0.0

    # These columns are nullable in the DB but declared non-null here; seeded
    # rows hold NULL, which from_attributes hands pydantic as an explicit None
    # and the response 500s. Coerce None back to each field's intended default.
    _NULL_DEFAULTS: ClassVar[dict] = {
        "default_deposit_amount": 0.0,
        "checkout_limit": 0,
        "loan_period_days": 0,
        "tags": [],
        "custom_fields": {},
    }

    @field_validator(
        "default_deposit_amount", "checkout_limit", "loan_period_days",
        "tags", "custom_fields",
        mode="before",
    )
    @classmethod
    def _coerce_null_to_default(cls, v, info):
        if v is None:
            return cls._NULL_DEFAULTS.get(info.field_name)
        return v

    class Config:
        from_attributes = True


class OutreachPartnerListResponse(BaseModel):
    partners: list[OutreachPartnerResponse]
    total: int
    limit: int
    offset: int


class OutreachPartnerSummary(BaseModel):
    id: int
    name: str
    partner_type: str
    status: str
    city: Optional[str] = None
    primary_contact_name: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# Deposit Schemas
# =============================================================================

class OutreachDepositCreate(StrictInputSchema):
    partner_id: int
    deposit_type: DepositType = DepositType.CLASSROOM_CHECKOUT
    amount: float = Field(..., gt=0)
    payment_method: Optional[str] = Field(None, max_length=50)
    payment_reference: Optional[str] = Field(None, max_length=100)
    collected_date: date
    expiry_date: Optional[date] = None
    institutional_card_id: Optional[int] = None
    bulk_checkout_id: Optional[int] = None
    notes: Optional[str] = None


class OutreachDepositRefund(BaseModel):
    refund_amount: float = Field(..., gt=0)
    refund_reason: str = Field(..., min_length=1, max_length=500)

    @field_validator("refund_amount")
    @classmethod
    def validate_refund_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Refund amount must be positive")
        return v


class DepositApplicationCreate(StrictInputSchema):
    amount: float = Field(..., gt=0)
    reason: str = Field(..., min_length=1, max_length=500)
    fine_id: Optional[int] = None
    bulk_checkout_id: Optional[int] = None
    notes: Optional[str] = None


class OutreachDepositResponse(BaseModel):
    id: int
    partner_id: int
    partner_name: Optional[str] = None
    deposit_type: str
    status: str
    amount: float
    amount_applied: float
    amount_refunded: float
    amount_remaining: float = 0.0  # Computed: amount - applied - refunded

    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    receipt_number: Optional[str] = None

    institutional_card_id: Optional[int] = None
    bulk_checkout_id: Optional[int] = None

    collected_date: date
    refund_date: Optional[date] = None
    expiry_date: Optional[date] = None

    notes: Optional[str] = None
    refund_reason: Optional[str] = None

    collected_by_id: Optional[int] = None
    collected_by_name: Optional[str] = None
    refunded_by_id: Optional[int] = None
    refunded_by_name: Optional[str] = None

    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OutreachDepositListResponse(BaseModel):
    deposits: list[OutreachDepositResponse]
    total: int
    limit: int
    offset: int


class DepositApplicationResponse(BaseModel):
    id: int
    deposit_id: int
    amount: float
    reason: str
    fine_id: Optional[int] = None
    bulk_checkout_id: Optional[int] = None
    applied_by_id: Optional[int] = None
    applied_by_name: Optional[str] = None
    applied_at: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# Outreach Visit Schemas
# =============================================================================

class OutreachVisitCreate(StrictInputSchema):
    partner_id: int
    visit_type: VisitType = VisitType.CLASSROOM_VISIT
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None

    scheduled_date: date
    scheduled_start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    scheduled_end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")

    location_name: Optional[str] = Field(None, max_length=200)
    location_room: Optional[str] = Field(None, max_length=100)
    location_address: Optional[str] = Field(None, max_length=500)

    expected_attendees: Optional[int] = Field(None, ge=0)
    age_group: Optional[str] = Field(None, max_length=50)
    grade_levels: list[str] = []

    lead_staff_id: Optional[int] = None
    additional_staff_ids: list[int] = []

    materials_needed: list[str] = []
    items_to_deliver: int = Field(default=0, ge=0)
    items_to_pickup: int = Field(default=0, ge=0)

    is_recurring: bool = False
    recurrence_pattern: Optional[str] = Field(None, max_length=50)


class OutreachVisitUpdate(StrictInputSchema):
    visit_type: Optional[VisitType] = None
    status: Optional[VisitStatus] = None
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None

    scheduled_date: Optional[date] = None
    scheduled_start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    scheduled_end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")

    location_name: Optional[str] = Field(None, max_length=200)
    location_room: Optional[str] = Field(None, max_length=100)
    location_address: Optional[str] = Field(None, max_length=500)

    expected_attendees: Optional[int] = Field(None, ge=0)
    age_group: Optional[str] = Field(None, max_length=50)
    grade_levels: Optional[list[str]] = None

    lead_staff_id: Optional[int] = None
    additional_staff_ids: Optional[list[int]] = None

    materials_needed: Optional[list[str]] = None
    items_to_deliver: Optional[int] = Field(None, ge=0)
    items_to_pickup: Optional[int] = Field(None, ge=0)


class OutreachVisitComplete(BaseModel):
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    actual_attendees: Optional[int] = Field(None, ge=0)

    items_delivered: int = Field(default=0, ge=0)
    items_picked_up: int = Field(default=0, ge=0)

    outcome_notes: Optional[str] = None
    new_cards_issued: int = Field(default=0, ge=0)
    books_checked_out: int = Field(default=0, ge=0)

    follow_up_needed: bool = False
    follow_up_notes: Optional[str] = None
    next_visit_date: Optional[date] = None

    partner_feedback: Optional[str] = None
    partner_rating: Optional[int] = Field(None, ge=1, le=5)
    staff_notes: Optional[str] = None


class OutreachVisitCancel(BaseModel):
    cancellation_reason: str = Field(..., min_length=1, max_length=500)
    reschedule_date: Optional[date] = None


class OutreachVisitResponse(BaseModel):
    id: int
    partner_id: int
    partner_name: Optional[str] = None

    visit_type: str
    status: str
    title: str
    description: Optional[str] = None

    scheduled_date: date
    scheduled_start_time: Optional[str] = None
    scheduled_end_time: Optional[str] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None

    location_name: Optional[str] = None
    location_room: Optional[str] = None
    location_address: Optional[str] = None

    expected_attendees: Optional[int] = None
    actual_attendees: Optional[int] = None
    age_group: Optional[str] = None
    grade_levels: Optional[list[str]] = []

    lead_staff_id: Optional[int] = None
    lead_staff_name: Optional[str] = None
    additional_staff_ids: Optional[list[int]] = []

    materials_needed: Optional[list[str]] = []
    items_to_deliver: Optional[int] = 0
    items_delivered: Optional[int] = 0
    items_to_pickup: Optional[int] = 0
    items_picked_up: Optional[int] = 0

    outcome_notes: Optional[str] = None
    new_cards_issued: Optional[int] = 0
    books_checked_out: Optional[int] = 0
    follow_up_needed: Optional[bool] = False
    follow_up_notes: Optional[str] = None
    next_visit_date: Optional[date] = None

    partner_feedback: Optional[str] = None
    partner_rating: Optional[int] = None
    staff_notes: Optional[str] = None

    cancellation_reason: Optional[str] = None
    cancelled_by_id: Optional[int] = None
    cancelled_at: Optional[datetime] = None

    is_recurring: Optional[bool] = False
    recurrence_pattern: Optional[str] = None
    parent_visit_id: Optional[int] = None

    created_by_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OutreachVisitListResponse(BaseModel):
    visits: list[OutreachVisitResponse]
    total: int
    limit: int
    offset: int


# =============================================================================
# Institutional Card Schemas
# =============================================================================

class InstitutionalCardCreate(StrictInputSchema):
    partner_id: int
    card_name: str = Field(..., min_length=1, max_length=200)

    authorized_users: list[str] = []
    requires_pin: bool = False
    pin: Optional[str] = Field(None, min_length=4, max_length=10)

    checkout_limit: int = Field(default=100, ge=1)
    hold_limit: int = Field(default=25, ge=0)
    loan_period_days: int = Field(default=28, ge=1)
    renewal_limit: int = Field(default=2, ge=0)

    exempt_from_fines: bool = False
    fine_cap: Optional[float] = Field(None, ge=0)

    deposit_required: bool = False
    deposit_amount: float = Field(default=0.0, ge=0)

    expiry_date: Optional[date] = None
    notes: Optional[str] = None


class InstitutionalCardUpdate(StrictInputSchema):
    card_name: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[InstitutionalCardStatus] = None

    authorized_users: Optional[list[str]] = None
    requires_pin: Optional[bool] = None
    new_pin: Optional[str] = Field(None, min_length=4, max_length=10)

    checkout_limit: Optional[int] = Field(None, ge=1)
    hold_limit: Optional[int] = Field(None, ge=0)
    loan_period_days: Optional[int] = Field(None, ge=1)
    renewal_limit: Optional[int] = Field(None, ge=0)

    exempt_from_fines: Optional[bool] = None
    fine_cap: Optional[float] = Field(None, ge=0)

    expiry_date: Optional[date] = None
    notes: Optional[str] = None


class InstitutionalCardResponse(BaseModel):
    id: int
    partner_id: int
    partner_name: Optional[str] = None

    card_number: str
    card_name: str
    status: str

    authorized_users: list[str]
    requires_pin: bool

    checkout_limit: int
    hold_limit: int
    loan_period_days: int
    renewal_limit: int

    exempt_from_fines: bool
    fine_cap: Optional[float] = None

    deposit_required: bool
    deposit_amount: float
    current_deposit_id: Optional[int] = None

    issued_date: date
    expiry_date: Optional[date] = None
    last_renewal_date: Optional[date] = None

    total_checkouts: int
    current_checkouts: int
    current_holds: int
    current_fines: float

    notes: Optional[str] = None

    issued_by_id: Optional[int] = None
    issued_by_name: Optional[str] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InstitutionalCardListResponse(BaseModel):
    cards: list[InstitutionalCardResponse]
    total: int
    limit: int
    offset: int


class InstitutionalCheckoutCreate(StrictInputSchema):
    card_id: int
    barcode: str = Field(..., min_length=1, max_length=50)
    checked_out_by_name: Optional[str] = Field(None, max_length=200)
    pin: Optional[str] = None  # Required if card requires_pin


class InstitutionalCheckoutResponse(BaseModel):
    id: int
    card_id: int
    card_number: Optional[str] = None
    checkout_id: Optional[int] = None

    item_copy_id: Optional[int] = None
    barcode: str
    title: Optional[str] = None

    checked_out_by_name: Optional[str] = None
    checked_out_by_id: Optional[int] = None

    checked_out_at: datetime
    due_date: datetime
    returned_at: Optional[datetime] = None

    status: str

    class Config:
        from_attributes = True


# =============================================================================
# Bulk Checkout Schemas
# =============================================================================

class BulkCheckoutCreate(StrictInputSchema):
    partner_id: int
    checkout_name: str = Field(..., min_length=1, max_length=300)

    requestor_name: str = Field(..., min_length=1, max_length=200)
    requestor_email: Optional[str] = Field(None, max_length=255)
    requestor_phone: Optional[str] = Field(None, max_length=30)
    classroom_name: Optional[str] = Field(None, max_length=200)
    grade_level: Optional[str] = Field(None, max_length=50)

    checkout_date: date
    due_date: date

    deposit_required: bool = False
    deposit_amount: float = Field(default=0.0, ge=0)

    topic_requests: list[str] = []
    reading_level_min: Optional[str] = Field(None, max_length=20)
    reading_level_max: Optional[str] = Field(None, max_length=20)
    format_preferences: list[str] = []

    delivery_method: Optional[str] = Field(None, max_length=50)
    delivery_address: Optional[str] = Field(None, max_length=500)
    pickup_location: Optional[str] = Field(None, max_length=200)
    outreach_visit_id: Optional[int] = None

    notes: Optional[str] = None


class BulkCheckoutUpdate(StrictInputSchema):
    checkout_name: Optional[str] = Field(None, min_length=1, max_length=300)
    status: Optional[BulkCheckoutStatus] = None

    requestor_name: Optional[str] = Field(None, min_length=1, max_length=200)
    requestor_email: Optional[str] = Field(None, max_length=255)
    requestor_phone: Optional[str] = Field(None, max_length=30)
    classroom_name: Optional[str] = Field(None, max_length=200)
    grade_level: Optional[str] = Field(None, max_length=50)

    due_date: Optional[date] = None

    topic_requests: Optional[list[str]] = None
    reading_level_min: Optional[str] = Field(None, max_length=20)
    reading_level_max: Optional[str] = Field(None, max_length=20)
    format_preferences: Optional[list[str]] = None

    delivery_method: Optional[str] = Field(None, max_length=50)
    delivery_address: Optional[str] = Field(None, max_length=500)
    pickup_location: Optional[str] = Field(None, max_length=200)

    notes: Optional[str] = None


class BulkCheckoutItemAddEntry(BaseModel):
    barcode: str = Field(..., min_length=1, max_length=50)
    condition_out: Optional[str] = Field(None, max_length=50)


class BulkCheckoutItemAdd(BaseModel):
    barcodes: list[str] = Field(default=None, min_length=1)
    items: Optional[list[BulkCheckoutItemAddEntry]] = None

    @model_validator(mode="after")
    def validate_has_entries(self) -> "BulkCheckoutItemAdd":
        if not self.barcodes and not self.items:
            raise ValueError("Either barcodes or items must be provided")
        return self

    def get_entries(self) -> list["BulkCheckoutItemAddEntry"]:
        if self.items:
            return self.items
        if self.barcodes:
            return [BulkCheckoutItemAddEntry(barcode=b) for b in self.barcodes]
        return []


class BulkCheckoutItemReturn(BaseModel):
    barcode: str = Field(..., min_length=1, max_length=50)
    condition: Optional[str] = Field(None, max_length=50)
    damage_notes: Optional[str] = None


class BulkCheckoutItemResponse(BaseModel):
    id: int
    bulk_checkout_id: int
    item_copy_id: Optional[int] = None
    checkout_id: Optional[int] = None

    barcode: str
    title: Optional[str] = None
    call_number: Optional[str] = None

    status: str
    returned_at: Optional[datetime] = None

    condition_out: Optional[str] = None
    condition_in: Optional[str] = None
    condition_changed: bool = False
    damage_notes: Optional[str] = None

    replacement_cost: Optional[float] = None
    fine_amount: float

    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    # fine_amount is nullable in the DB but declared non-null here; rows hold
    # NULL, which from_attributes hands pydantic as an explicit None and the
    # response 500s. Coerce None back to the default.
    _NULL_DEFAULTS: ClassVar[dict] = {"fine_amount": 0.0}

    @field_validator("fine_amount", mode="before")
    @classmethod
    def _coerce_null_to_default(cls, v, info):
        if v is None:
            return cls._NULL_DEFAULTS.get(info.field_name)
        return v

    class Config:
        from_attributes = True


class BulkCheckoutResponse(BaseModel):
    id: int
    partner_id: int
    partner_name: Optional[str] = None

    checkout_name: str
    status: str

    requestor_name: str
    requestor_email: Optional[str] = None
    requestor_phone: Optional[str] = None
    classroom_name: Optional[str] = None
    grade_level: Optional[str] = None

    checkout_date: date
    due_date: date
    returned_date: Optional[date] = None

    total_items: int
    items_returned: int
    items_lost: int
    items_damaged: int
    items_outstanding: int = 0  # Computed

    deposit_required: bool
    deposit_amount: float
    deposit_collected: bool

    topic_requests: list[str]
    reading_level_min: Optional[str] = None
    reading_level_max: Optional[str] = None
    format_preferences: list[str]

    delivery_method: Optional[str] = None
    delivery_address: Optional[str] = None
    pickup_location: Optional[str] = None
    outreach_visit_id: Optional[int] = None

    notes: Optional[str] = None
    return_notes: Optional[str] = None

    processed_by_id: Optional[int] = None
    processed_by_name: Optional[str] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    items: list[BulkCheckoutItemResponse] = []

    # These columns are nullable in the DB but declared non-null here; rows hold
    # NULL, which from_attributes hands pydantic as an explicit None and the
    # response 500s. Coerce None back to each field's intended default.
    _NULL_DEFAULTS: ClassVar[dict] = {
        "deposit_amount": 0.0,
        "format_preferences": [],
    }

    @field_validator("deposit_amount", "format_preferences", mode="before")
    @classmethod
    def _coerce_null_to_default(cls, v, info):
        if v is None:
            return cls._NULL_DEFAULTS.get(info.field_name)
        return v

    class Config:
        from_attributes = True


class BulkCheckoutListResponse(BaseModel):
    checkouts: list[BulkCheckoutResponse]
    total: int
    limit: int
    offset: int


# =============================================================================
# Outreach Statistics Schemas
# =============================================================================

class OutreachStatisticsResponse(BaseModel):
    id: int
    period_start: date
    period_end: date
    branch_id: Optional[int] = None

    # Partner stats
    total_partners: int
    active_partners: int
    new_partners: int
    partners_by_type: dict

    # Visit stats
    total_visits: int
    visits_completed: int
    visits_cancelled: int
    total_attendees: int
    visits_by_type: dict

    # Checkout stats
    bulk_checkouts_created: int
    bulk_checkouts_returned: int
    bulk_items_checked_out: int
    bulk_items_returned: int
    bulk_items_lost: int

    # Institutional card stats
    institutional_cards_active: int
    institutional_cards_issued: int
    institutional_checkouts: int

    # Deposit stats
    deposits_collected: float
    deposits_refunded: float
    deposits_applied_to_fines: float

    # Impact metrics
    new_cards_from_outreach: int
    reading_program_signups: int

    generated_at: datetime

    class Config:
        from_attributes = True


class OutreachDashboardResponse(BaseModel):
    # Current period stats
    active_partners: int
    pending_visits: int
    overdue_bulk_checkouts: int
    deposits_held: float

    # Recent activity
    recent_visits: list[OutreachVisitResponse]
    upcoming_visits: list[OutreachVisitResponse]

    # Quick stats
    visits_this_month: int
    attendees_this_month: int
    items_circulated_this_month: int
    new_cards_this_month: int

    # Top partners
    top_partners_by_checkouts: list[OutreachPartnerSummary]
    top_partners_by_visits: list[OutreachPartnerSummary]


class OutreachReportRequest(StrictInputSchema):
    start_date: date
    end_date: date
    partner_ids: Optional[list[int]] = None
    partner_types: Optional[list[PartnerType]] = None
    visit_types: Optional[list[VisitType]] = None
    include_details: bool = False
    branch_id: Optional[int] = None


class OutreachReportResponse(BaseModel):
    report_period: str
    generated_at: datetime

    # Summary statistics
    statistics: OutreachStatisticsResponse

    # Detailed breakdowns (if include_details=True)
    partner_details: Optional[list[OutreachPartnerResponse]] = None
    visit_details: Optional[list[OutreachVisitResponse]] = None
    bulk_checkout_details: Optional[list[BulkCheckoutResponse]] = None


# =============================================================================
# Notification Template Schemas
# =============================================================================

class OutreachNotificationTemplateCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=200)
    notification_type: str = Field(..., max_length=50)
    channel: str = Field(..., max_length=20)

    subject: Optional[str] = Field(None, max_length=500)
    body: str = Field(..., min_length=1)
    html_body: Optional[str] = None

    available_variables: list[str] = []

    days_before_event: Optional[int] = Field(None, ge=0)
    send_time: Optional[str] = Field(None, max_length=10)

    is_active: bool = True
    is_default: bool = False


class OutreachNotificationTemplateUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    subject: Optional[str] = Field(None, max_length=500)
    body: Optional[str] = Field(None, min_length=1)
    html_body: Optional[str] = None

    available_variables: Optional[list[str]] = None

    days_before_event: Optional[int] = Field(None, ge=0)
    send_time: Optional[str] = Field(None, max_length=10)

    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class OutreachNotificationTemplateResponse(BaseModel):
    id: int
    name: str
    notification_type: str
    channel: str

    subject: Optional[str] = None
    body: str
    html_body: Optional[str] = None

    available_variables: list[str]

    days_before_event: Optional[int] = None
    send_time: Optional[str] = None

    is_active: bool
    is_default: bool

    created_by_id: Optional[int] = None
    updated_by_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OutreachNotificationTemplateListResponse(BaseModel):
    templates: list[OutreachNotificationTemplateResponse]
    total: int
    limit: int
    offset: int


class OutreachNotificationLogResponse(BaseModel):
    id: int
    template_id: Optional[int] = None
    notification_type: str
    channel: str

    recipient_type: Optional[str] = None
    recipient_id: Optional[int] = None
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    recipient_name: Optional[str] = None

    partner_id: Optional[int] = None
    visit_id: Optional[int] = None
    bulk_checkout_id: Optional[int] = None
    deposit_id: Optional[int] = None
    institutional_card_id: Optional[int] = None

    subject: Optional[str] = None
    body: Optional[str] = None

    status: str
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None

    external_message_id: Optional[str] = None

    triggered_by: Optional[str] = None
    triggered_by_user_id: Optional[int] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class OutreachNotificationLogListResponse(BaseModel):
    logs: list[OutreachNotificationLogResponse]
    total: int
    limit: int
    offset: int


class OutreachNotificationSendRequest(StrictInputSchema):
    template_id: int
    recipient_emails: Optional[list[str]] = None
    recipient_phones: Optional[list[str]] = None
    partner_id: Optional[int] = None
    visit_id: Optional[int] = None
    bulk_checkout_id: Optional[int] = None
    deposit_id: Optional[int] = None
    institutional_card_id: Optional[int] = None
    custom_variables: Optional[dict] = None


class OutreachNotificationPreviewRequest(StrictInputSchema):
    template_id: int
    partner_id: Optional[int] = None
    visit_id: Optional[int] = None
    bulk_checkout_id: Optional[int] = None
    deposit_id: Optional[int] = None
    institutional_card_id: Optional[int] = None
    custom_variables: Optional[dict] = None


class OutreachNotificationPreviewResponse(BaseModel):
    subject: Optional[str] = None
    body: str
    html_body: Optional[str] = None
    variables_used: dict
