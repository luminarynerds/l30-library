# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas._base import StrictInputSchema

from ..models.room import RejectionReason


# ============================================================================
# Equipment Schemas
# ============================================================================

class EquipmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    equipment_code: str = Field(..., min_length=1, max_length=50)
    requires_staff_setup: bool = False
    setup_instructions: str | None = None


class EquipmentCreate(StrictInputSchema, EquipmentBase):
    total_quantity: int = Field(default=1, ge=1)


class EquipmentUpdate(StrictInputSchema):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    equipment_code: str | None = Field(None, min_length=1, max_length=50)
    total_quantity: int | None = Field(None, ge=1)
    requires_staff_setup: bool | None = None
    setup_instructions: str | None = None
    is_active: bool | None = None


class EquipmentResponse(EquipmentBase):
    id: int
    total_quantity: int
    is_active: bool
    created_at: datetime | None = None

    class Config:
        from_attributes = True


# ============================================================================
# Room Schemas
# ============================================================================

class EquipmentOption(BaseModel):
    id: str
    name: str
    requires_staff: bool = False


class OperatingHours(BaseModel):
    open: str = Field(..., pattern=r"^\d{2}:\d{2}$")  # HH:MM format
    close: str = Field(..., pattern=r"^\d{2}:\d{2}$")


class WeeklyOperatingHours(BaseModel):
    monday: OperatingHours | None = None
    tuesday: OperatingHours | None = None
    wednesday: OperatingHours | None = None
    thursday: OperatingHours | None = None
    friday: OperatingHours | None = None
    saturday: OperatingHours | None = None
    sunday: OperatingHours | None = None


class RoomBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    branch_id: int | None = None
    branch_name: str | None = Field(None, max_length=255)
    room_type: str = Field(default="study_room")
    capacity: int = Field(default=4, ge=1, le=500)
    floor: str | None = Field(None, max_length=50)
    room_number: str | None = Field(None, max_length=50)
    amenities: list[str] | None = None
    available_equipment: list[EquipmentOption] | None = None
    requires_approval: bool = False
    max_duration_minutes: int = Field(default=120, ge=15, le=480)
    min_duration_minutes: int = Field(default=30, ge=15, le=240)
    advance_booking_days: int = Field(default=14, ge=1, le=365)
    min_advance_hours: int = Field(default=1, ge=0, le=168)
    operating_hours: WeeklyOperatingHours | dict | None = None
    image_url: str | None = Field(None, max_length=500)

    # Accessibility metadata
    wheelchair_accessible: bool = False
    hearing_loop: bool = False
    accessible_restroom_nearby: bool = False
    accessibility_notes: str | None = None

    # Setup/teardown buffers (admin-configurable; minutes)
    setup_buffer_minutes: int = Field(default=0, ge=0, le=240)
    teardown_buffer_minutes: int = Field(default=0, ge=0, le=240)

    # Per-patron rolling 30-day cap (NULL = unlimited)
    max_bookings_per_patron_per_month: int | None = Field(default=None, ge=1, le=200)

    @field_validator("room_type", mode="before")
    @classmethod
    def validate_room_type(cls, v: object) -> str:
        from enum import Enum
        if isinstance(v, Enum):
            v = v.value
        s = str(v)
        valid_types = ["study_room", "meeting_room", "computer_lab", "event_space"]
        if s not in valid_types:
            raise ValueError(f"room_type must be one of: {', '.join(valid_types)}")
        return s

    @model_validator(mode="after")
    def validate_duration_range(self) -> "RoomBase":
        if self.min_duration_minutes > self.max_duration_minutes:
            raise ValueError("min_duration_minutes cannot exceed max_duration_minutes")
        return self


class RoomCreate(StrictInputSchema, RoomBase):
    pass


class RoomUpdate(StrictInputSchema):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    branch_id: int | None = None
    branch_name: str | None = Field(None, max_length=255)
    room_type: str | None = None
    capacity: int | None = Field(None, ge=1, le=500)
    floor: str | None = Field(None, max_length=50)
    room_number: str | None = Field(None, max_length=50)
    amenities: list[str] | None = None
    available_equipment: list[EquipmentOption] | None = None
    requires_approval: bool | None = None
    max_duration_minutes: int | None = Field(None, ge=15, le=480)
    min_duration_minutes: int | None = Field(None, ge=15, le=240)
    advance_booking_days: int | None = Field(None, ge=1, le=365)
    min_advance_hours: int | None = Field(None, ge=0, le=168)
    operating_hours: WeeklyOperatingHours | dict | None = None
    image_url: str | None = Field(None, max_length=500)
    is_active: bool | None = None
    # Accessibility metadata (optional updates)
    wheelchair_accessible: bool | None = None
    hearing_loop: bool | None = None
    accessible_restroom_nearby: bool | None = None
    accessibility_notes: str | None = None
    # Setup/teardown buffers
    setup_buffer_minutes: int | None = Field(None, ge=0, le=240)
    teardown_buffer_minutes: int | None = Field(None, ge=0, le=240)
    # Per-patron rolling 30-day cap
    max_bookings_per_patron_per_month: int | None = Field(None, ge=1, le=200)

    @field_validator("room_type", mode="before")
    @classmethod
    def validate_room_type(cls, v: object) -> str | None:
        if v is None:
            return v
        from enum import Enum
        if isinstance(v, Enum):
            v = v.value
        s = str(v)
        valid_types = ["study_room", "meeting_room", "computer_lab", "event_space"]
        if s not in valid_types:
            raise ValueError(f"room_type must be one of: {', '.join(valid_types)}")
        return s


class RoomResponse(BaseModel):
    id: int
    name: str
    description: str | None
    branch_id: int | None
    branch_name: str | None
    room_type: str
    capacity: int
    floor: str | None
    room_number: str | None
    amenities: list[str] | None
    available_equipment: list[dict] | None
    requires_approval: bool
    max_duration_minutes: int
    min_duration_minutes: int
    advance_booking_days: int
    min_advance_hours: int = 0
    operating_hours: dict | None
    image_url: str | None
    is_active: bool
    # Accessibility metadata
    wheelchair_accessible: bool = False
    hearing_loop: bool = False
    accessible_restroom_nearby: bool = False
    accessibility_notes: str | None = None
    # Setup/teardown buffers (admin-only operational fields, exposed in response)
    setup_buffer_minutes: int = 0
    teardown_buffer_minutes: int = 0
    # Per-patron rolling 30-day cap (NULL = unlimited)
    max_bookings_per_patron_per_month: int | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class RoomListResponse(BaseModel):
    items: list[RoomResponse]
    total: int
    page: int
    per_page: int


class RoomAvailabilitySlot(BaseModel):
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    max_available_minutes: int | None = None


class RoomAvailabilityResponse(BaseModel):
    room_id: int
    room_name: str
    date: str  # YYYY-MM-DD
    available_slots: list[RoomAvailabilitySlot]
    reservations: list["ReservationBriefResponse"]


# ============================================================================
# Reservation Schemas
# ============================================================================

class ReservationBase(BaseModel):
    room_id: int
    start_time: datetime
    end_time: datetime
    purpose: str | None = Field(None, max_length=500)
    attendee_count: int = Field(default=1, ge=1)
    equipment_requested: list[str] | None = None
    contact_name: str | None = Field(None, max_length=255)
    contact_email: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=50)

    @model_validator(mode="after")
    def validate_time_range(self) -> "ReservationBase":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class ReservationCreate(StrictInputSchema, ReservationBase):
    # Recurring reservation fields (optional)
    is_recurring: bool | None = False
    recurrence_pattern: str | None = None  # daily, weekly, biweekly, monthly
    recurrence_end_date: datetime | None = None
    # Accommodation request (accessibility / special needs)
    accommodation_requested: bool | None = False
    accommodation_details: str | None = None
    # Meeting-room policy acknowledgement (required when room.requires_approval)
    policy_acknowledged: bool | None = False

    @model_validator(mode="after")
    def validate_recurring(self) -> "ReservationCreate":
        if self.is_recurring:
            if not self.recurrence_pattern:
                raise ValueError("recurrence_pattern is required for recurring reservations")
            if not self.recurrence_end_date:
                raise ValueError("recurrence_end_date is required for recurring reservations")
            valid_patterns = ["daily", "weekly", "biweekly", "monthly"]
            if self.recurrence_pattern not in valid_patterns:
                raise ValueError(f"recurrence_pattern must be one of: {', '.join(valid_patterns)}")
        return self


class ReservationUpdate(StrictInputSchema):
    start_time: datetime | None = None
    end_time: datetime | None = None
    purpose: str | None = Field(None, max_length=500)
    attendee_count: int | None = Field(None, ge=1)
    equipment_requested: list[str] | None = None
    contact_name: str | None = Field(None, max_length=255)
    contact_email: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=50)


class ReservationApproval(BaseModel):
    approved: bool
    rejection_reason: str | None = Field(None, max_length=500)
    rejection_reason_code: str | None = None  # RejectionReason value, structured category
    internal_notes: str | None = None

    @field_validator("rejection_reason_code", mode="before")
    @classmethod
    def validate_rejection_reason_code(cls, v: object) -> str | None:
        if v is None or v == "":
            return None
        from enum import Enum
        if isinstance(v, Enum):
            v = v.value
        s = str(v)
        valid = {e.value for e in RejectionReason}
        if s not in valid:
            raise ValueError(f"rejection_reason_code must be one of: {', '.join(sorted(valid))}")
        return s


class ReservationDeny(BaseModel):
    rejection_reason_code: str = Field(...)
    rejection_reason: str | None = Field(None, max_length=500)
    internal_notes: str | None = None

    @field_validator("rejection_reason_code", mode="before")
    @classmethod
    def validate_rejection_reason_code(cls, v: object) -> str:
        from enum import Enum
        if isinstance(v, Enum):
            v = v.value
        s = str(v)
        valid = {e.value for e in RejectionReason}
        if s not in valid:
            raise ValueError(f"rejection_reason_code must be one of: {', '.join(sorted(valid))}")
        return s


class AccommodationAcknowledge(BaseModel):
    notes: str | None = Field(None, max_length=1000)


class ReservationCancellation(BaseModel):
    reason: str | None = Field(None, max_length=500)


class StaffOverrideCreate(StrictInputSchema):
    room_id: int
    start_time: datetime
    end_time: datetime
    purpose: str | None = Field(None, max_length=500)
    override_reason: str = Field(..., min_length=1, max_length=500)
    patron_id: int | None = None
    contact_name: str | None = Field(None, max_length=255)
    contact_email: str | None = Field(None, max_length=255)
    internal_notes: str | None = None


class ReservationBriefResponse(BaseModel):
    id: int
    start_time: datetime
    end_time: datetime
    status: str

    class Config:
        from_attributes = True


class ReservationResponse(BaseModel):
    id: int
    room_id: int
    patron_id: int | None
    start_time: datetime
    end_time: datetime
    status: str
    purpose: str | None
    attendee_count: int
    equipment_requested: list[str] | None
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    is_recurring: bool | None = False
    recurrence_pattern: str | None
    recurrence_end_date: datetime | None
    parent_reservation_id: int | None
    approved_by: int | None
    approved_at: datetime | None
    rejection_reason: str | None
    checked_in_at: datetime | None
    cancelled_at: datetime | None
    cancelled_by: int | None
    cancellation_reason: str | None
    is_staff_override: bool | None = False
    rejection_reason_code: str | None = None
    accommodation_requested: bool = False
    accommodation_details: str | None = None
    accommodation_acknowledged_at: datetime | None = None
    accommodation_acknowledged_by: int | None = None
    policy_acknowledged: bool = False
    policy_acknowledged_at: datetime | None = None

    @field_validator("is_recurring", "is_staff_override", mode="before")
    @classmethod
    def coerce_none_to_false(cls, v: Any) -> bool:
        return bool(v) if v is not None else False
    confirmation_sent_at: datetime | None
    reminder_sent_at: datetime | None
    created_at: datetime | None = None
    updated_at: datetime | None

    # Joined data
    room_name: str | None = None
    patron_name: str | None = None
    approver_name: str | None = None

    class Config:
        from_attributes = True


class ReservationDetailResponse(ReservationResponse):
    room: RoomResponse | None = None
    internal_notes: str | None = None  # Only included for staff
    child_reservations: list["ReservationBriefResponse"] | None = None


class ReservationListResponse(BaseModel):
    items: list[ReservationResponse]
    total: int
    page: int
    per_page: int


# ============================================================================
# Report Schemas
# ============================================================================

class RoomUtilizationReport(BaseModel):
    room_id: int
    room_name: str
    period_start: datetime
    period_end: datetime
    total_reservations: int
    completed_reservations: int
    cancelled_reservations: int
    no_show_count: int
    no_show_rate: float  # Percentage
    total_hours_available: float
    total_hours_booked: float
    utilization_rate: float  # Percentage
    average_booking_duration_minutes: float
    total_attendees: int
    average_attendees_per_booking: float


class PopularTimesReport(BaseModel):
    room_id: int | None  # None for aggregate across all rooms
    room_name: str | None
    day_of_week: dict[str, int]  # Day name -> booking count
    hourly_distribution: dict[str, int]  # Hour (00-23) -> booking count
    peak_hour: str
    peak_day: str


class NoShowReport(BaseModel):
    period_start: datetime
    period_end: datetime
    total_reservations: int
    no_show_count: int
    no_show_rate: float
    by_room: list[dict[str, Any]]  # Room-level breakdown
    by_day_of_week: dict[str, int]
    repeat_no_show_patrons: list[dict[str, Any]]  # Patrons with multiple no-shows


class UsageReportResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    room_utilization: list[RoomUtilizationReport]
    popular_times: PopularTimesReport
    no_show_summary: NoShowReport
    equipment_usage: dict[str, int]  # Equipment code -> usage count


# ============================================================================
# Waitlist Schemas
# ============================================================================

class WaitlistCreate(StrictInputSchema):
    room_id: int
    desired_start_time: datetime
    desired_end_time: datetime

    @model_validator(mode="after")
    def validate_time_range(self) -> "WaitlistCreate":
        if self.desired_end_time <= self.desired_start_time:
            raise ValueError("desired_end_time must be after desired_start_time")
        return self


class WaitlistResponse(BaseModel):
    id: int
    room_id: int
    patron_id: int
    desired_start_time: datetime
    desired_end_time: datetime
    status: str
    position: int | None = None  # Position in queue (1-indexed), None if not pending
    notified_at: datetime | None
    created_at: datetime | None = None
    expires_at: datetime

    class Config:
        from_attributes = True


class WaitlistListResponse(BaseModel):
    items: list[WaitlistResponse]
    total: int
    page: int
    per_page: int


# ============================================================================
# Prep Notes Schemas
# ============================================================================

class PrepNoteCreate(StrictInputSchema):
    setup_instructions: str | None = None
    equipment_to_setup: list[str] | None = None
    special_requirements: str | None = None


class PrepNoteUpdate(StrictInputSchema):
    setup_instructions: str | None = None
    equipment_to_setup: list[str] | None = None
    special_requirements: str | None = None
    is_completed: bool | None = None


class PrepNoteResponse(BaseModel):
    id: int
    reservation_id: int
    setup_instructions: str | None
    equipment_to_setup: list[str] | None
    special_requirements: str | None
    is_completed: bool
    completed_by: int | None
    completed_at: datetime | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class PrepNoteListResponse(BaseModel):
    items: list[PrepNoteResponse]
    total: int
    page: int
    per_page: int


# Forward reference resolution
RoomAvailabilityResponse.model_rebuild()
ReservationDetailResponse.model_rebuild()
