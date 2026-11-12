# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import MoneyDecimal, StrictInputSchema

from ..models.book_drop import (
    BackdateMode, BookDropStatus, CheckInResultStatus,
    CheckInSessionStatus, ExceptionType, SIP2DeviceStatus,
    SortDestination
)


# =============================================================================
# Book Drop Schemas
# =============================================================================

class BookDropCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Z0-9_-]+$")
    description: Optional[str] = None

    branch_location: str = Field(..., min_length=1, max_length=100)
    physical_location: Optional[str] = Field(None, max_length=255)

    backdate_mode: BackdateMode = BackdateMode.FIXED_TIME
    backdate_fixed_time: Optional[time] = None
    backdate_hours: Optional[int] = Field(None, ge=1, le=48)
    backdate_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])

    processing_start_time: Optional[time] = None
    processing_end_time: Optional[time] = None

    exempt_overnight_fines: bool = True
    max_backdate_hours: int = Field(16, ge=1, le=48)

    sip2_device_id: Optional[int] = None

    @field_validator("backdate_days")
    @classmethod
    def validate_days(cls, v):
        for day in v:
            if day < 0 or day > 6:
                raise ValueError("Days must be 0-6 (Monday-Sunday)")
        return v


class BookDropUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    physical_location: Optional[str] = Field(None, max_length=255)
    status: Optional[BookDropStatus] = None

    backdate_mode: Optional[BackdateMode] = None
    backdate_fixed_time: Optional[time] = None
    backdate_hours: Optional[int] = Field(None, ge=1, le=48)
    backdate_days: Optional[list[int]] = None

    processing_start_time: Optional[time] = None
    processing_end_time: Optional[time] = None

    exempt_overnight_fines: Optional[bool] = None
    max_backdate_hours: Optional[int] = Field(None, ge=1, le=48)

    sip2_device_id: Optional[int] = None


class BookDropResponse(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str]

    branch_location: str
    physical_location: Optional[str]
    status: BookDropStatus

    backdate_mode: BackdateMode
    backdate_fixed_time: Optional[time]
    backdate_hours: Optional[int]
    backdate_days: Optional[list[int]] = None

    processing_start_time: Optional[time]
    processing_end_time: Optional[time]

    exempt_overnight_fines: bool
    max_backdate_hours: int

    sip2_device_id: Optional[int]

    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# SIP2 Device Schemas
# =============================================================================

class SIP2DeviceCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=100)
    device_id: str = Field(..., min_length=1, max_length=50)

    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(6001, ge=1, le=65535)
    institution_id: str = Field(..., min_length=1, max_length=100)
    terminal_password: Optional[str] = Field(None, max_length=100)

    timeout_seconds: int = Field(30, ge=5, le=300)
    retry_attempts: int = Field(3, ge=1, le=10)

    supports_checkin: bool = True
    supports_checkout: bool = True
    supports_sorting: bool = False

    sort_bin_mapping: dict[str, str] = Field(default_factory=dict)


class SIP2DeviceUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=100)

    host: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    institution_id: Optional[str] = Field(None, min_length=1, max_length=100)
    terminal_password: Optional[str] = Field(None, max_length=100)

    timeout_seconds: Optional[int] = Field(None, ge=5, le=300)
    retry_attempts: Optional[int] = Field(None, ge=1, le=10)

    supports_checkin: Optional[bool] = None
    supports_checkout: Optional[bool] = None
    supports_sorting: Optional[bool] = None

    sort_bin_mapping: Optional[dict[str, str]] = None

    status: Optional[SIP2DeviceStatus] = None


class SIP2DeviceResponse(BaseModel):
    id: int
    name: str
    device_id: str

    host: str
    port: int
    institution_id: str

    status: SIP2DeviceStatus
    last_communication: Optional[datetime]
    error_message: Optional[str]

    timeout_seconds: int
    retry_attempts: int

    supports_checkin: bool
    supports_checkout: bool
    supports_sorting: bool

    sort_bin_mapping: dict[str, str]

    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    # sort_bin_mapping is nullable in the DB (default {}, no NOT NULL); legacy
    # rows hold NULL, which from_attributes passes through as None and 500s the
    # response. Coerce None back to an empty dict at the boundary.
    @field_validator("sort_bin_mapping", mode="before")
    @classmethod
    def _coerce_null_sort_bin_mapping(cls, v):
        if v is None:
            return {}
        return v

    class Config:
        from_attributes = True


# =============================================================================
# Check-in Session Schemas
# =============================================================================

class CheckInSessionCreate(StrictInputSchema):
    book_drop_id: Optional[int] = None
    branch_location: str = Field(..., min_length=1, max_length=100)
    workstation_id: Optional[str] = Field(None, max_length=50)

    use_backdating: bool = False
    backdate_to: Optional[datetime] = None


class CheckInSessionResponse(BaseModel):
    id: int
    session_code: str

    book_drop_id: Optional[int]
    branch_id: Optional[int] = None
    branch_location: str
    workstation_id: Optional[str]

    staff_id: int
    status: CheckInSessionStatus

    started_at: datetime
    ended_at: Optional[datetime]

    use_backdating: bool
    backdate_to: Optional[datetime]

    total_items: int
    successful_checkins: int
    holds_trapped: int
    transits_created: int
    exceptions_count: int

    # Calculated fields
    success_rate: Optional[float] = None

    class Config:
        from_attributes = True


class CheckInSessionSummary(BaseModel):
    id: int
    session_code: str
    branch_id: Optional[int] = None
    branch_location: str
    status: CheckInSessionStatus
    started_at: datetime
    ended_at: Optional[datetime]
    total_items: int
    staff_name: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# Batch Check-in Schemas
# =============================================================================

class BatchCheckInItem(BaseModel):
    barcode: str = Field(..., min_length=1, max_length=50)
    condition_status: Optional[str] = Field(None, max_length=50)
    condition_notes: Optional[str] = None


class BatchCheckInRequest(StrictInputSchema):
    session_id: int
    items: list[BatchCheckInItem] = Field(..., min_length=1, max_length=100)

    # Optional overrides
    skip_condition_check: bool = False
    override_backdate: Optional[datetime] = None


class SingleCheckInRequest(StrictInputSchema):
    session_id: int
    barcode: str = Field(..., min_length=1, max_length=50)

    condition_status: Optional[str] = Field(None, max_length=50)
    condition_notes: Optional[str] = None

    override_backdate: Optional[datetime] = None


class CheckInResultResponse(BaseModel):
    id: int
    barcode: str
    status: CheckInResultStatus

    item_copy_id: Optional[int]
    checkout_id: Optional[int]

    # Item details
    item_title: Optional[str] = None
    item_author: Optional[str] = None

    # Sorting
    sort_destination: Optional[SortDestination]
    sort_bin: Optional[str]

    # Hold info
    hold_id: Optional[int]
    hold_patron_name: Optional[str] = None
    hold_pickup_location: Optional[str] = None

    # Transit info
    destination_branch_id: Optional[int] = None
    destination_branch: Optional[str]

    # Timing
    checked_in_at: datetime
    effective_checkin_time: Optional[datetime]

    # Overdue/fine
    was_overdue: bool
    overdue_days: int
    fine_amount: MoneyDecimal
    fine_waived_by_backdate: bool

    # Condition
    condition_checked: bool
    condition_status: Optional[str]

    # Exception
    exception_type: Optional[ExceptionType]
    exception_message: Optional[str]

    class Config:
        from_attributes = True


class BatchCheckInResponse(BaseModel):
    session_id: int
    processed_count: int
    successful_count: int
    holds_trapped: int
    transits_created: int
    exceptions_count: int

    results: list[CheckInResultResponse]

    # Items requiring attention
    items_with_holds: list[CheckInResultResponse] = []
    items_for_transit: list[CheckInResultResponse] = []
    items_with_exceptions: list[CheckInResultResponse] = []


# =============================================================================
# Exception Handling Schemas
# =============================================================================

class CheckInExceptionResponse(BaseModel):
    id: int
    check_in_result_id: int
    exception_type: ExceptionType
    severity: str

    item_copy_id: Optional[int]
    patron_id: Optional[int]

    title: str
    description: Optional[str]
    exception_data: dict

    requires_action: bool
    action_taken: Optional[str]
    resolved: bool
    resolved_by_id: Optional[int]
    resolved_at: Optional[datetime]

    created_at: datetime | None = None
    # Additional context
    item_title: Optional[str] = None
    patron_name: Optional[str] = None

    class Config:
        from_attributes = True


class ResolveExceptionRequest(StrictInputSchema):
    action_taken: str = Field(..., min_length=1, max_length=500)


# =============================================================================
# Statistics Schemas
# =============================================================================

class CheckInStatisticResponse(BaseModel):
    id: int
    date: date
    hour: int
    day_of_week: int
    branch_id: Optional[int] = None
    branch_location: str
    book_drop_id: Optional[int]

    total_checkins: int
    staff_checkins: int
    book_drop_checkins: int
    self_service_checkins: int

    successful_count: int
    holds_trapped_count: int
    transits_count: int
    exceptions_count: int

    overdue_items_count: int
    total_fines_amount: MoneyDecimal
    fines_waived_amount: MoneyDecimal

    avg_processing_time: float

    class Config:
        from_attributes = True


class StatisticsQuery(BaseModel):
    start_date: date
    end_date: date
    branch_location: Optional[str] = None
    book_drop_id: Optional[int] = None
    group_by: str = Field("day", pattern=r"^(hour|day|week|month)$")


class StatisticsSummary(BaseModel):
    period_start: date
    period_end: date
    branch_location: Optional[str]

    total_checkins: int
    avg_daily_checkins: float
    peak_hour: int
    peak_day_of_week: int

    holds_trapped_total: int
    transits_total: int
    exceptions_total: int

    total_fines: MoneyDecimal
    total_fines_waived: MoneyDecimal

    # Breakdown by source
    staff_checkins_pct: float
    book_drop_checkins_pct: float
    self_service_checkins_pct: float


class HourlyVolume(BaseModel):
    hour: int
    count: int
    avg_count: float


class DailyVolume(BaseModel):
    date: date
    day_of_week: int
    total_checkins: int
    holds_trapped: int
    transits: int
    exceptions: int


# =============================================================================
# Book Drop Check-in Schemas
# =============================================================================

class BookDropCheckInRequest(StrictInputSchema):
    book_drop_id: int
    items: list[BatchCheckInItem]

    # Processing options
    apply_backdating: bool = True
    calculate_backdate_from: Optional[datetime] = None  # Default: now


class BookDropCheckInResponse(BaseModel):
    book_drop_id: int
    book_drop_name: str
    session_id: int

    backdated_to: Optional[datetime]
    fines_waived_count: int
    fines_waived_amount: MoneyDecimal

    processed_count: int
    successful_count: int
    holds_trapped: int
    transits_created: int
    exceptions_count: int

    results: list[CheckInResultResponse]


# =============================================================================
# Condition Check Schemas
# =============================================================================

class ConditionCheckRequest(StrictInputSchema):
    check_in_result_id: int
    condition_status: str = Field(..., pattern=r"^(new|good|fair|poor|damaged)$")
    condition_notes: Optional[str] = None
    damage_type: Optional[str] = None
    requires_repair: bool = False


class ConditionCheckResponse(BaseModel):
    check_in_result_id: int
    condition_status: str
    condition_notes: Optional[str]
    condition_changed: bool
    previous_condition: Optional[str]
    exception_created: bool


# =============================================================================
# Fast Processing Schemas
# =============================================================================

class DestinationSummary(BaseModel):
    total: int
    shelve: int
    holds: int
    transit: int
    exceptions: int


class DamageCheckRequirement(BaseModel):
    check_in_result_id: int
    barcode: str
    requires_check: bool
    reason: Optional[str]
    item_title: Optional[str]


class ClaimsReturnedResolution(BaseModel):
    check_in_result_id: int
    resolution_notes: str = Field(..., min_length=1, max_length=500)


class FastProcessingScanRequest(StrictInputSchema):
    session_id: int
    barcode: str
    check_damage: Optional[bool] = False  # Only if flagged items
    damage_status: Optional[str] = None  # Only if check_damage=True


class FastProcessingResponse(BaseModel):
    check_in_result_id: int
    barcode: str
    status: CheckInResultStatus
    sort_destination: Optional[SortDestination]
    sort_color: str  # "green", "yellow", "blue", "red"
    sort_sound: str  # "shelve", "holds", "transit", "exception"
    hold_patron_name: Optional[str]
    destination_branch_id: Optional[int] = None
    destination_branch: Optional[str]
    requires_damage_check: bool
    exception_message: Optional[str]
    destination_summary: DestinationSummary
