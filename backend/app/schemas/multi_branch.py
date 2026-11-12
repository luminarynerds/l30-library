# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas._base import MoneyDecimal, StrictInputSchema


# =============================================================================
# ENUMS (for schema validation)
# =============================================================================

from app.models.multi_branch import (
    BranchType,
    BranchStatus,
    DayOfWeek,
    TransitStatus,
    TransitPriority,
    TransitReason,
    ConsortiumMemberType,
    ConsortiumMemberStatus,
    BillingCycleType,
    BillingItemType,
    BillingStatus,
    SettingScopeLevel,
    FloatingCollectionType,
)


# =============================================================================
# LIBRARY SYSTEM SCHEMAS
# =============================================================================

class LibrarySystemBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    legal_name: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    fax: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = Field(None, max_length=2)
    zip_code: str | None = None
    country: str | None = "USA"
    tax_id: str | None = None
    state_library_id: str | None = None
    governance_type: str | None = None
    fiscal_year_start_month: int | None = 7
    timezone: str | None = "America/New_York"

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            ZoneInfo(v)
        except (KeyError, ValueError, TypeError):
            raise ValueError(f"Invalid IANA timezone: '{v}'. Use a valid timezone like 'America/New_York' or 'Europe/London'.") from None
        return v


class LibrarySystemCreate(StrictInputSchema, LibrarySystemBase):
    pass


class LibrarySystemUpdate(StrictInputSchema):
    name: str | None = None
    legal_name: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    fax: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = None
    tax_id: str | None = None
    state_library_id: str | None = None
    governance_type: str | None = None
    fiscal_year_start_month: int | None = None
    timezone: str | None = None
    is_active: bool | None = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            ZoneInfo(v)
        except (KeyError, ValueError, TypeError):
            raise ValueError(f"Invalid IANA timezone: '{v}'. Use a valid timezone like 'America/New_York' or 'Europe/London'.") from None
        return v


class LibrarySystemResponse(LibrarySystemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SystemSettingsBase(BaseModel):
    default_loan_period_days: int | None = 21
    default_renewal_limit: int | None = 2
    default_hold_limit: int | None = 10
    default_checkout_limit: int | None = 50
    default_overdue_fine_per_day: MoneyDecimal | None = Decimal("0.25")
    default_max_fine: MoneyDecimal | None = Decimal("10.00")
    grace_period_days: int | None = 0
    fine_free_juvenile: bool | None = False
    lost_item_threshold_days: int | None = 30
    default_replacement_cost: MoneyDecimal | None = Decimal("25.00")
    processing_fee: MoneyDecimal | None = Decimal("5.00")
    hold_pickup_days: int | None = 7
    allow_hold_on_available: bool | None = True
    transit_time_estimate_days: int | None = 2
    auto_approve_transit: bool | None = True
    require_address_verification: bool | None = True
    allow_self_registration: bool | None = True
    card_expiry_years: int | None = 3
    # Age-based account transition settings
    age_transition_threshold: int | None = 18  # Age at which CHILD accounts auto-transition to PATRON
    auto_transition_enabled: bool | None = True  # Enable/disable automatic child-to-adult transitions
    forgive_reading_minutes_on_transition: bool | None = True  # Forgive outstanding reading minutes on transition
    overdue_notice_days: list[int] | None = None
    courtesy_notice_days: int | None = 3
    enable_floating_collections: bool | None = False
    enable_reciprocal_borrowing: bool | None = False
    enable_self_checkout: bool | None = True
    # Reporting basis (state annual report FTE divisor + board monthly volunteer value)
    fte_annual_hours: int | None = 2080
    volunteer_hour_value: MoneyDecimal | None = Decimal("33.49")


class SystemSettingsUpdate(StrictInputSchema, SystemSettingsBase):
    pass


class SystemSettingsResponse(SystemSettingsBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    library_system_id: int
    updated_at: datetime | None = None


# =============================================================================
# REGION SCHEMAS
# =============================================================================

class RegionBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    manager_user_id: int | None = None


class RegionCreate(StrictInputSchema, RegionBase):
    library_system_id: int


class RegionUpdate(StrictInputSchema):
    name: str | None = None
    description: str | None = None
    manager_user_id: int | None = None
    is_active: bool | None = None


class RegionResponse(RegionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    library_system_id: int
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


# =============================================================================
# BRANCH SCHEMAS
# =============================================================================

class BranchBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    short_name: str | None = None
    branch_type: BranchType = BranchType.BRANCH
    phone: str | None = None
    fax: str | None = None
    email: str | None = None
    website: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = "USA"
    latitude: float | None = None
    longitude: float | None = None
    square_footage: int | None = None
    parking_spaces: int | None = None
    is_ada_accessible: bool | None = True
    has_meeting_rooms: bool | None = False
    has_computer_lab: bool | None = True
    has_makerspace: bool | None = False
    has_drive_through: bool | None = False
    has_book_drop: bool | None = True
    has_self_checkout: bool | None = True
    ils_location_code: str | None = None
    display_order: int | None = 0


class BranchCreate(StrictInputSchema, BranchBase):
    library_system_id: int
    region_id: int | None = None
    branch_manager_id: int | None = None
    opened_date: date | None = None


class BranchUpdate(StrictInputSchema):
    name: str | None = None
    short_name: str | None = None
    branch_type: BranchType | None = None
    status: BranchStatus | None = None
    region_id: int | None = None
    phone: str | None = None
    fax: str | None = None
    email: str | None = None
    website: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    square_footage: int | None = None
    parking_spaces: int | None = None
    is_ada_accessible: bool | None = None
    has_meeting_rooms: bool | None = None
    has_computer_lab: bool | None = None
    has_makerspace: bool | None = None
    has_drive_through: bool | None = None
    has_book_drop: bool | None = None
    has_self_checkout: bool | None = None
    branch_manager_id: int | None = None
    ils_location_code: str | None = None
    display_order: int | None = None
    opened_date: date | None = None
    closed_date: date | None = None


class BranchResponse(BranchBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    library_system_id: int
    region_id: int | None = None
    status: BranchStatus
    branch_manager_id: int | None = None
    opened_date: date | None = None
    closed_date: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BranchDetailResponse(BranchResponse):
    hours: list["BranchHoursResponse"] = []
    closures: list["BranchClosureResponse"] = []
    settings: "BranchSettingsResponse | None" = None


# =============================================================================
# BRANCH HOURS SCHEMAS
# =============================================================================

class BranchHoursBase(BaseModel):
    day_of_week: DayOfWeek
    is_closed: bool = False
    open_time: time | None = None
    close_time: time | None = None
    open_time_2: time | None = None
    close_time_2: time | None = None
    effective_from: date | None = None
    effective_until: date | None = None
    notes: str | None = None


class BranchHoursCreate(StrictInputSchema, BranchHoursBase):
    branch_id: int


class BranchHoursUpdate(StrictInputSchema):
    is_closed: bool | None = None
    open_time: time | None = None
    close_time: time | None = None
    open_time_2: time | None = None
    close_time_2: time | None = None
    effective_from: date | None = None
    effective_until: date | None = None
    notes: str | None = None


class BranchHoursResponse(BranchHoursBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# =============================================================================
# BRANCH CLOSURE SCHEMAS
# =============================================================================

class BranchClosureBase(BaseModel):
    start_date: date
    end_date: date
    start_time: time | None = None
    end_time: time | None = None
    reason: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    is_system_wide: bool = False
    is_annual: bool = False


class BranchClosureCreate(StrictInputSchema, BranchClosureBase):
    branch_id: int


class BranchClosureResponse(BranchClosureBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    created_by_id: int | None = None
    created_at: datetime | None = None
    updated_by_id: int | None = None
    updated_at: datetime | None = None

    # Closure management status
    patrons_with_holds_notified: bool = False
    staff_notified: bool = False
    partner_organizations_notified: bool = False
    website_updated: bool = False
    phone_message_updated: bool = False
    social_media_updated: bool = False
    google_maps_updated: bool = False
    apple_maps_updated: bool = False
    events_canceled: bool = False
    programs_rescheduled: bool = False
    closure_documentation: str | None = None
    reopening_announcement: str | None = None

    @field_validator(
        "patrons_with_holds_notified", "staff_notified",
        "partner_organizations_notified", "website_updated",
        "phone_message_updated", "social_media_updated",
        "google_maps_updated", "apple_maps_updated",
        "events_canceled", "programs_rescheduled",
        mode="before",
    )
    @classmethod
    def coerce_none_to_false(cls, v):
        return v if v is not None else False


class CloseTodayRequest(StrictInputSchema):
    reason: str = Field(..., min_length=1, max_length=255, description="Brief reason for closure")
    closure_documentation: str | None = Field(None, description="Detailed documentation")
    send_notifications: bool = True
    cancel_events: bool = True
    reschedule_programs: bool = True
    update_external_services: bool = True
    notify_partner_organizations: bool = True
    partner_list: list[str] | None = None


class ClosureStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    closure: BranchClosureResponse
    notifications: dict[str, bool]
    external_services: dict[str, bool]
    event_management: dict[str, bool | None]


class ClosureCompletionStatus(BaseModel):
    patrons_notified: bool
    staff_notified: bool
    partners_notified: bool
    website_updated: bool
    phone_updated: bool
    social_media_updated: bool
    maps_updated: bool
    events_handled: bool
    all_complete: bool


class UpdateExternalServicesRequest(StrictInputSchema):
    website: bool = False
    phone_message: bool = False
    social_media: bool = False
    google_maps: bool = False
    apple_maps: bool = False


class NotifyPartnersRequest(StrictInputSchema):
    partner_list: list[str] | None = None


class ScheduleReopeningRequest(StrictInputSchema):
    reopening_announcement: str = Field(..., min_length=1, description="Reopening message")


class PatronWithHolds(BaseModel):
    patron_id: int
    patron_name: str
    patron_email: str | None = None
    item_title: str
    hold_placed_at: str | None = None


class AffectedEvent(BaseModel):
    event_id: int
    title: str
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    category: str | None = None
    audience: str | None = None


class StaffMember(BaseModel):
    staff_id: int
    name: str
    email: str | None = None
    role: str | None = None


# =============================================================================
# BRANCH SETTINGS SCHEMAS
# =============================================================================

class BranchSettingsBase(BaseModel):
    loan_period_days: int | None = None
    renewal_limit: int | None = None
    hold_limit: int | None = None
    checkout_limit: int | None = None
    overdue_fine_per_day: MoneyDecimal | None = None
    max_fine: MoneyDecimal | None = None
    fine_free: bool | None = None
    allow_ill_pickup: bool | None = True
    allow_hold_pickup: bool | None = True
    allow_returns: bool | None = True
    floating_type: FloatingCollectionType | None = FloatingCollectionType.NO_FLOAT
    default_pickup_branch: bool | None = True
    checkout_message: str | None = None
    hold_pickup_message: str | None = None
    print_receipt_header: str | None = None
    print_receipt_footer: str | None = None


class BranchSettingsUpdate(StrictInputSchema, BranchSettingsBase):
    pass


class BranchSettingsResponse(BranchSettingsBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    updated_at: datetime | None = None


# =============================================================================
# TRANSIT REQUEST SCHEMAS
# =============================================================================

class TransitRequestBase(BaseModel):
    reason: str
    priority: TransitPriority = TransitPriority.NORMAL
    notes: str | None = None


class TransitRequestCreate(StrictInputSchema, TransitRequestBase):
    item_copy_id: int
    from_branch_id: int
    to_branch_id: int
    hold_id: int | None = None


class TransitRequestResponse(TransitRequestBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_copy_id: int
    from_branch_id: int
    to_branch_id: int
    status: TransitStatus
    hold_id: int | None = None
    requested_at: datetime
    requested_by_id: int
    approved_at: datetime | None = None
    approved_by_id: int | None = None
    picked_up_at: datetime | None = None
    picked_up_by_id: int | None = None
    shipped_at: datetime | None = None
    received_at: datetime | None = None
    received_by_id: int | None = None
    cancelled_at: datetime | None = None
    cancelled_by_id: int | None = None
    cancellation_reason: str | None = None
    expected_arrival_date: date | None = None


class TransitRequestDetailResponse(TransitRequestResponse):
    from_branch: BranchResponse | None = None
    to_branch: BranchResponse | None = None


# =============================================================================
# TRANSIT SHIPMENT SCHEMAS
# =============================================================================

class TransitShipmentBase(BaseModel):
    container_count: int = 1
    carrier: str | None = None
    tracking_number: str | None = None
    notes: str | None = None


class TransitShipmentCreate(StrictInputSchema, TransitShipmentBase):
    from_branch_id: int
    to_branch_id: int


class TransitShipmentResponse(TransitShipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_number: str
    from_branch_id: int
    to_branch_id: int
    item_count: int
    created_at: datetime | None = None
    created_by_id: int
    shipped_at: datetime | None = None
    shipped_by_id: int | None = None
    received_at: datetime | None = None
    received_by_id: int | None = None


class TransitShipmentDetailResponse(TransitShipmentResponse):
    from_branch: BranchResponse | None = None
    to_branch: BranchResponse | None = None
    items: list["TransitShipmentItemResponse"] = []


class TransitShipmentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    transit_request_id: int
    scanned_in_at: datetime
    scanned_in_by_id: int | None = None
    received_at: datetime | None = None
    received_by_id: int | None = None
    notes: str | None = None


# =============================================================================
# CONSORTIUM SCHEMAS
# =============================================================================

class ConsortiumBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    legal_name: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = "USA"
    established_date: date | None = None
    governing_document_url: str | None = None


class ConsortiumCreate(StrictInputSchema, ConsortiumBase):
    pass


class ConsortiumUpdate(StrictInputSchema):
    name: str | None = None
    legal_name: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = None
    established_date: date | None = None
    governing_document_url: str | None = None
    is_active: bool | None = None


class ConsortiumResponse(ConsortiumBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConsortiumDetailResponse(ConsortiumResponse):
    members: list["ConsortiumMemberResponse"] = []
    settings: "ConsortiumSettingsResponse | None" = None


# =============================================================================
# CONSORTIUM MEMBER SCHEMAS
# =============================================================================

class ConsortiumMemberBase(BaseModel):
    member_type: ConsortiumMemberType = ConsortiumMemberType.FULL
    voting_member: bool = True
    vote_weight: int = 1
    annual_fee: MoneyDecimal | None = None


class ConsortiumMemberCreate(StrictInputSchema, ConsortiumMemberBase):
    consortium_id: int
    library_system_id: int
    joined_date: date | None = None
    liaison_user_id: int | None = None


class ConsortiumMemberUpdate(StrictInputSchema):
    member_type: ConsortiumMemberType | None = None
    status: ConsortiumMemberStatus | None = None
    voting_member: bool | None = None
    vote_weight: int | None = None
    annual_fee: MoneyDecimal | None = None
    fee_paid_through: date | None = None
    liaison_user_id: int | None = None
    expiry_date: date | None = None


class ConsortiumMemberResponse(ConsortiumMemberBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    consortium_id: int
    library_system_id: int
    status: ConsortiumMemberStatus
    joined_date: date
    expiry_date: date | None = None
    fee_paid_through: date | None = None
    liaison_user_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConsortiumMemberDetailResponse(ConsortiumMemberResponse):
    library_system: LibrarySystemResponse | None = None
    reciprocal_settings: "ReciprocalBorrowingSettingsResponse | None" = None
    white_label: "ConsortiumWhiteLabelResponse | None" = None


# =============================================================================
# CONSORTIUM SETTINGS SCHEMAS
# =============================================================================

class ConsortiumSettingsBase(BaseModel):
    enable_shared_catalog: bool | None = True
    catalog_search_all_members: bool | None = True
    enable_reciprocal_borrowing: bool | None = True
    reciprocal_checkout_limit: int | None = 5
    reciprocal_hold_limit: int | None = 3
    enable_ill: bool | None = True
    ill_request_limit: int | None = 10
    ill_loan_period_days: int | None = 21
    enable_consortium_transit: bool | None = True
    default_transit_time_days: int | None = 3
    enable_single_sign_on: bool | None = False
    sso_provider: str | None = None
    sso_config: dict[str, Any] | None = None
    cost_sharing_model: str | None = None
    ill_fee_per_item: MoneyDecimal | None = Decimal("0.00")
    transit_fee_per_item: MoneyDecimal | None = Decimal("0.00")
    billing_cycle: BillingCycleType | None = BillingCycleType.QUARTERLY
    enable_consortium_float: bool | None = False


class ConsortiumSettingsUpdate(StrictInputSchema, ConsortiumSettingsBase):
    pass


class ConsortiumSettingsResponse(ConsortiumSettingsBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    consortium_id: int
    updated_at: datetime | None = None


# =============================================================================
# RECIPROCAL BORROWING SCHEMAS
# =============================================================================

class ReciprocalBorrowingSettingsBase(BaseModel):
    allow_incoming_borrowers: bool | None = True
    incoming_checkout_limit: int | None = 5
    incoming_hold_limit: int | None = 3
    allow_outgoing_borrowers: bool | None = True
    require_registration: bool | None = True
    registration_valid_days: int | None = 365
    blocked_item_types: list[str] | None = None
    restricted_collections: list[str] | None = None


class ReciprocalBorrowingSettingsUpdate(StrictInputSchema, ReciprocalBorrowingSettingsBase):
    pass


class ReciprocalBorrowingSettingsResponse(ReciprocalBorrowingSettingsBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    updated_at: datetime | None = None


# =============================================================================
# BILLING SCHEMAS
# =============================================================================

class ConsortiumBillingBase(BaseModel):
    item_type: BillingItemType
    quantity: int = 1
    unit_amount: MoneyDecimal
    total_amount: MoneyDecimal
    description: str | None = None


class ConsortiumBillingCreate(StrictInputSchema, ConsortiumBillingBase):
    consortium_id: int
    billing_member_id: int
    billed_member_id: int
    billing_period_start: date
    billing_period_end: date


class ConsortiumBillingResponse(ConsortiumBillingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    consortium_id: int
    billing_member_id: int
    billed_member_id: int
    billing_period_start: date
    billing_period_end: date
    status: BillingStatus
    invoice_number: str | None = None
    invoiced_at: datetime | None = None
    due_date: date | None = None
    paid_at: datetime | None = None
    payment_reference: str | None = None
    disputed_at: datetime | None = None
    dispute_reason: str | None = None
    dispute_resolved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# =============================================================================
# WHITE LABEL SCHEMAS
# =============================================================================

class ConsortiumWhiteLabelBase(BaseModel):
    logo_url: str | None = None
    logo_small_url: str | None = None
    banner_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    text_color: str | None = None
    background_color: str | None = None
    heading_font: str | None = None
    body_font: str | None = None
    custom_css: str | None = None
    custom_domain: str | None = None
    subdomain: str | None = None
    welcome_message: str | None = None
    footer_text: str | None = None
    contact_info: dict[str, Any] | None = None
    facebook_url: str | None = None
    twitter_url: str | None = None
    instagram_url: str | None = None
    youtube_url: str | None = None
    show_consortium_branding: bool | None = True
    show_member_list: bool | None = True
    show_consortium_events: bool | None = True


class ConsortiumWhiteLabelUpdate(StrictInputSchema, ConsortiumWhiteLabelBase):
    pass


class ConsortiumWhiteLabelResponse(ConsortiumWhiteLabelBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    updated_at: datetime | None = None


# =============================================================================
# PATRON LINK SCHEMAS
# =============================================================================

class ConsortiumPatronLinkBase(BaseModel):
    linked_card_number: str | None = None


class ConsortiumPatronLinkCreate(StrictInputSchema, ConsortiumPatronLinkBase):
    home_user_id: int
    home_member_id: int
    linked_member_id: int
    expires_at: datetime | None = None


class ConsortiumPatronLinkResponse(ConsortiumPatronLinkBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    home_user_id: int
    home_member_id: int
    linked_member_id: int
    registered_at: datetime
    expires_at: datetime | None = None
    is_active: bool
    blocked: bool
    blocked_reason: str | None = None
    last_used_at: datetime | None = None
    total_checkouts: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# =============================================================================
# BRANCH STATISTICS SCHEMAS
# =============================================================================

class BranchStatisticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    period_start: date
    period_end: date
    total_checkouts: int
    total_renewals: int
    total_checkins: int
    total_holds_placed: int
    total_holds_filled: int
    items_owned: int
    items_added: int
    items_withdrawn: int
    items_sent_to_other_branches: int
    items_received_from_other_branches: int
    active_patrons: int
    new_registrations: int
    fines_assessed: MoneyDecimal
    fines_collected: MoneyDecimal
    fines_waived: MoneyDecimal
    door_count: int | None = None
    generated_at: datetime


# =============================================================================
# BRANCH ITEM COPY SCHEMAS
# =============================================================================

class BranchItemCopyBase(BaseModel):
    is_floating: bool = False
    float_scope: FloatingCollectionType = FloatingCollectionType.NO_FLOAT
    shelving_location: str | None = None


class BranchItemCopyCreate(StrictInputSchema, BranchItemCopyBase):
    item_copy_id: int
    home_branch_id: int | None = None
    current_branch_id: int


class BranchItemCopyResponse(BranchItemCopyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_copy_id: int
    home_branch_id: int | None = None
    current_branch_id: int
    last_seen_at: datetime | None = None
    last_circulated_branch_id: int | None = None
    assigned_at: datetime
    updated_at: datetime | None = None


# =============================================================================
# REPORTING SCHEMAS
# =============================================================================

class SystemStatisticsResponse(BaseModel):
    library_system_id: int
    period: dict[str, str]
    branch_count: int
    circulation: dict[str, int]
    collection: dict[str, int]
    transit: dict[str, int]
    patrons: dict[str, int]
    financial: dict[str, float]


class BranchComparisonResponse(BaseModel):
    branch_id: int
    branch_code: str
    branch_name: str
    checkouts: int
    checkins: int
    holds_placed: int
    holds_filled: int
    items_owned: int
    active_patrons: int
    new_registrations: int
    fines_collected: float
    items_sent: int
    items_received: int


class TransitStatisticsResponse(BaseModel):
    total_requests: int
    by_status: dict[str, int]
    by_reason: dict[str, int]
    average_transit_hours: float | None
    period: dict[str, str | None]


class MemberBalanceResponse(BaseModel):
    owed_to_member: MoneyDecimal
    member_owes: MoneyDecimal
    net_balance: MoneyDecimal


# Update forward references
BranchDetailResponse.model_rebuild()
TransitShipmentDetailResponse.model_rebuild()
ConsortiumDetailResponse.model_rebuild()
ConsortiumMemberDetailResponse.model_rebuild()
