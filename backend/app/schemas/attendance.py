# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ._base import MoneyDecimal, StrictInputSchema


# ============================================================================
# Enums as string literals for schema validation
# ============================================================================

CHECK_IN_METHODS = ["qr_code", "library_card", "walk_in", "head_count", "pre_registered"]
AGE_RANGES = ["0-5", "6-12", "13-17", "18-34", "35-54", "55-64", "65+", "unknown"]
SESSION_STATUSES = ["open", "closed", "finalized"]


# ============================================================================
# Attendance Session Schemas
# ============================================================================


class AttendanceSessionCreate(StrictInputSchema):
    event_id: Optional[int] = Field(None, description="Link to an event")
    program_id: Optional[int] = Field(None, description="Link to a program")
    session_name: str = Field(..., min_length=1, max_length=255)
    session_date: date
    head_count_mode: bool = Field(default=False, description="Enable head count mode for large events")
    event_cost: Optional[MoneyDecimal] = Field(None, ge=0, description="Total event cost for ROI calculation")
    cost_notes: Optional[str] = None
    survey_enabled: bool = Field(default=True)
    survey_link: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


class AttendanceSessionUpdate(StrictInputSchema):
    session_name: Optional[str] = Field(None, min_length=1, max_length=255)
    head_count_mode: Optional[bool] = None
    head_count_total: Optional[int] = Field(None, ge=0)
    head_count_by_age: Optional[dict] = None
    event_cost: Optional[MoneyDecimal] = Field(None, ge=0)
    cost_notes: Optional[str] = None
    survey_enabled: Optional[bool] = None
    survey_link: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


class AttendanceSessionResponse(BaseModel):
    id: int
    event_id: Optional[int] = None
    program_id: Optional[int] = None
    session_name: str
    session_date: date
    status: str
    qr_code_token: str
    head_count_mode: bool
    head_count_total: int
    head_count_by_age: Optional[dict] = None
    total_checked_in: int
    total_walk_ins: int
    total_pre_registered: int
    total_card_scans: int
    total_qr_scans: int
    event_cost: Optional[MoneyDecimal] = None
    cost_notes: Optional[str] = None
    survey_enabled: bool
    survey_link: Optional[str] = None
    survey_sent_at: Optional[datetime] = None
    opened_by_id: Optional[int] = None
    closed_by_id: Optional[int] = None
    closed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Computed fields
    effective_total: Optional[int] = Field(None, description="Total attendance including head count")
    cost_per_attendee: Optional[MoneyDecimal] = Field(None, description="ROI: cost per attendee")

    class Config:
        from_attributes = True


class AttendanceSessionSummary(BaseModel):
    id: int
    session_name: str
    session_date: date
    status: str
    event_id: Optional[int] = None
    program_id: Optional[int] = None
    event_title: Optional[str] = None
    program_title: Optional[str] = None
    head_count_mode: bool
    total_checked_in: int
    head_count_total: int
    effective_total: int
    cost_per_attendee: Optional[MoneyDecimal] = None

    class Config:
        from_attributes = True


# ============================================================================
# Check-In Schemas
# ============================================================================


class QRCodeCheckIn(StrictInputSchema):
    qr_token: str = Field(..., description="QR code token from the session")
    patron_id: Optional[int] = Field(None, description="Patron ID if logged in")
    guest_name: Optional[str] = Field(None, max_length=255)
    guest_email: Optional[str] = Field(None, max_length=255)
    age_range: Optional[str] = Field(default="unknown")

    @field_validator("age_range")
    @classmethod
    def validate_age_range(cls, v: str) -> str:
        if v not in AGE_RANGES:
            raise ValueError(f"age_range must be one of: {AGE_RANGES}")
        return v


class LibraryCardCheckIn(StrictInputSchema):
    session_id: int
    library_card_number: str = Field(..., min_length=1, max_length=50)
    age_range: Optional[str] = Field(default=None, description="Override age range if known")


class WalkInCheckIn(StrictInputSchema):
    session_id: int
    guest_name: Optional[str] = Field(None, max_length=255, description="Optional name")
    guest_email: Optional[str] = Field(None, max_length=255, description="Optional email for survey")
    guest_phone: Optional[str] = Field(None, max_length=50)
    age_range: str = Field(default="unknown")
    notes: Optional[str] = None

    @field_validator("age_range")
    @classmethod
    def validate_age_range(cls, v: str) -> str:
        if v not in AGE_RANGES:
            raise ValueError(f"age_range must be one of: {AGE_RANGES}")
        return v


class HeadCountUpdate(StrictInputSchema):
    session_id: int
    total: int = Field(..., ge=0, description="Total head count")
    by_age: Optional[dict] = Field(
        None,
        description="Breakdown by age range, e.g. {'0-5': 10, '6-12': 15}",
    )


class CheckInResponse(BaseModel):
    id: int
    session_id: int
    patron_id: Optional[int] = None
    registration_id: Optional[int] = Field(
        None,
        description="EventRegistration this check-in satisfies, when "
        "check_in_method='pre_registered'. NULL for all other paths.",
    )
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None
    check_in_method: str
    checked_in_at: datetime
    library_card_number: Optional[str] = None
    age_range: str
    is_repeat_attendee: bool
    previous_visit_count: int
    first_visit_date: Optional[date] = None
    patron_name: Optional[str] = Field(None, description="Patron full name if linked")
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# Survey Schemas
# ============================================================================


class SurveySendRequest(StrictInputSchema):
    session_id: int
    survey_link: Optional[str] = Field(None, max_length=500, description="Override survey link")
    send_to_all: bool = Field(default=True, description="Send to all attendees with email")


class SurveySendResponse(BaseModel):
    session_id: int
    total_eligible: int
    total_sent: int
    total_failed: int
    total_opted_out: int


# ============================================================================
# Trends & Analytics Schemas
# ============================================================================


class AttendanceTrendFilter(StrictInputSchema):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    program_type: Optional[str] = None
    audience: Optional[str] = None
    branch_id: Optional[int] = None
    period_type: str = Field(default="monthly", description="daily, weekly, or monthly")


class AttendanceTrendResponse(BaseModel):
    period_start: date
    period_end: date
    period_type: str
    program_type: Optional[str] = None
    audience: Optional[str] = None
    total_sessions: int
    total_attendance: int
    avg_attendance_per_session: float
    total_walk_ins: int
    total_repeat_attendees: int
    total_new_attendees: int
    total_cost: MoneyDecimal
    cost_per_attendee: MoneyDecimal
    age_distribution: Optional[dict] = None
    method_distribution: Optional[dict] = None

    class Config:
        from_attributes = True


class ROIReport(BaseModel):
    period_label: str
    total_events: int
    total_attendance: int
    total_cost: MoneyDecimal
    cost_per_attendee: MoneyDecimal
    repeat_rate: float = Field(description="Percentage of repeat attendees")
    top_programs: list[dict] = Field(description="Top programs by attendance")
    cost_breakdown: Optional[dict] = None


class AttendanceDashboard(BaseModel):
    today_sessions: int
    today_total_attendance: int
    week_total_attendance: int
    month_total_attendance: int
    avg_attendance_per_event: float
    repeat_attendee_rate: float
    top_check_in_method: str
    recent_sessions: list[AttendanceSessionSummary]
    age_distribution: dict
    method_distribution: dict
