# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


# Computer Schemas

class ComputerResponse(BaseModel):
    id: int
    name: str
    computer_number: str
    description: Optional[str] = None
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    location: Optional[str] = None
    computer_type: str
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    processor: Optional[str] = None
    ram_gb: Optional[int] = None
    storage_gb: Optional[int] = None
    installed_software: Optional[List[str]] = []
    has_internet: bool
    internet_type: Optional[str] = None
    has_screen_reader: bool
    has_magnifier: bool
    has_keyboard_options: bool
    accessibility_features: Optional[List[str]] = []
    has_print_release: bool
    max_session_minutes: int
    is_extendable: bool
    max_extension_minutes: int
    status: str
    is_active: bool
    image_url: Optional[str] = None
    map_x: Optional[float] = None
    map_y: Optional[float] = None
    map_floor: Optional[str] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class ComputerListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[ComputerResponse]


# Reservation Schemas

class ReservationCreateRequest(StrictInputSchema):
    computer_id: int | None = None
    start_time: datetime
    duration_minutes: int = Field(..., gt=0, le=480)  # Max 8 hours
    is_guest_pass: bool = False
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None
    guest_phone: Optional[str] = None


class ReservationResponse(BaseModel):
    id: int
    computer_id: int | None = None
    patron_id: Optional[int] = None
    reserved_start_time: datetime
    reserved_end_time: datetime
    status: str
    session_duration_minutes: int
    is_guest_pass: bool
    guest_pass_code: Optional[str] = None
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None
    guest_phone: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    extension_requested: bool
    extended_until: Optional[datetime] = None
    extensions_used: int
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    five_min_warning_sent_at: Optional[datetime] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# Session Schemas

class SessionResponse(BaseModel):
    id: int
    reservation_id: int | None = None
    computer_id: int | None = None
    patron_id: Optional[int] = None
    session_start_time: datetime | None = None
    session_end_time: datetime | None = None
    actual_end_time: Optional[datetime] = None
    is_active: bool
    was_extended: bool
    extension_count: int
    warning_sent_at: Optional[datetime] = None
    auto_logout_at: Optional[datetime] = None
    user_initiated_logout: bool
    auto_logout_executed: bool
    logoff_reason: Optional[str] = None
    print_jobs_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# Staff Session Termination

class StaffEndSessionRequest(StrictInputSchema):
    reason_category: str = Field(
        ...,
        description="One of: time_up, patron_left, policy_violation, technical_issue, other",
    )
    notes: Optional[str] = Field(default=None, max_length=500)


class StaffBulkActionRequest(StrictInputSchema):
    computer_ids: List[int] = Field(..., min_length=1, max_length=100)
    action: str = Field(
        ...,
        description="One of: end_sessions, mark_available, mark_maintenance, mark_offline",
    )
    reason_category: Optional[str] = Field(
        default=None,
        description="Required for end_sessions; one of the StaffEndSessionRequest categories",
    )
    notes: Optional[str] = Field(default=None, max_length=500)


class StaffBulkActionResultItem(BaseModel):
    computer_id: int
    success: bool
    detail: Optional[str] = None


class StaffBulkActionResponse(BaseModel):
    action: str
    succeeded: int
    failed: int
    results: List[StaffBulkActionResultItem]


# Guest Pass Schemas

class GuestPassCreateRequest(StrictInputSchema):
    guest_name: str
    guest_email: Optional[str] = None
    guest_phone: Optional[str] = None
    max_sessions: int = 1
    max_duration_minutes_per_session: int = 60
    allowed_computer_types: Optional[List[str]] = None


class GuestPassResponse(BaseModel):
    id: int
    guest_name: str
    guest_email: Optional[str] = None
    guest_phone: Optional[str] = None
    pass_code: str
    max_sessions: int
    sessions_used: int
    max_duration_minutes_per_session: int
    issued_at: datetime
    valid_until: datetime
    is_active: bool
    allowed_computer_types: Optional[List[str]] = []
    first_used_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class GuestPassPublicResponse(BaseModel):
    pass_code: str
    is_active: bool
    max_sessions: int
    sessions_used: int
    max_duration_minutes_per_session: int
    valid_until: datetime
    allowed_computer_types: Optional[List[str]] = []
    guest_name_short: str = Field(description="First name only (or initial) for identity confirmation")

    class Config:
        from_attributes = True

    @classmethod
    def from_guest_pass(cls, gp) -> "GuestPassPublicResponse":
        name = (gp.guest_name or "").strip()
        parts = name.split()
        short = parts[0] if len(parts) >= 2 else (name[:1] + "." if name else "Guest")
        return cls(
            pass_code=gp.pass_code,
            is_active=gp.is_active,
            max_sessions=gp.max_sessions,
            sessions_used=gp.sessions_used,
            max_duration_minutes_per_session=gp.max_duration_minutes_per_session,
            valid_until=gp.valid_until,
            allowed_computer_types=gp.allowed_computer_types or [],
            guest_name_short=short,
        )


# Waitlist Schemas

class WaitlistResponse(BaseModel):
    id: int
    computer_id: int | None = None
    patron_id: Optional[int] = None
    is_guest: bool
    guest_phone: Optional[str] = None
    desired_start_time: datetime
    desired_duration_minutes: int
    status: str
    queue_position: int
    notified_at: Optional[datetime] = None
    notification_method: Optional[str] = None
    created_at: datetime | None = None
    expires_at: datetime

    class Config:
        from_attributes = True


# Extension Request Schemas

class ExtensionRequestResponse(BaseModel):
    id: int
    reservation_id: int | None = None
    session_id: int
    extension_minutes: int
    status: str
    requested_at: datetime
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    denial_reason: Optional[str] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# Usage Statistics Schemas

class UsageStatsResponse(BaseModel):
    id: int
    computer_id: int | None = None
    date: datetime
    total_reservations: int
    completed_sessions: int
    cancelled_reservations: int
    no_show_count: int
    total_minutes_used: int
    total_extension_minutes: int
    guest_sessions: int
    cardholders_sessions: int
    extension_requests: int
    extension_requests_granted: int
    extension_requests_denied: int
    hourly_usage: Optional[dict] = None
    downtime_minutes: int
    maintenance_events: int
    print_jobs_count: int

    class Config:
        from_attributes = True


class LabMapStation(BaseModel):
    id: int
    name: str
    computer_number: str
    location: Optional[str] = None
    computer_type: str
    status: str
    map_x: Optional[float] = None
    map_y: Optional[float] = None
    map_floor: Optional[str] = None
    available_at: Optional[datetime] = None  # When this station will be free; null = free now or not in normal-use state

    class Config:
        from_attributes = True


class LabMapResponse(BaseModel):
    stations: List[LabMapStation]
    generated_at: datetime
