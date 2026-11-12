# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import StrictInputSchema


# ============================================================================
# Tech Topic and Skill Level Enums
# ============================================================================

class TechTopicEnum(str):
    email = "email"
    smartphone = "smartphone"
    tablet = "tablet"
    computer_basics = "computer_basics"
    internet_browsing = "internet_browsing"
    social_media = "social_media"
    password_management = "password_management"
    online_safety = "online_safety"
    resume_building = "resume_building"
    job_search_online = "job_search_online"
    cloud_storage = "cloud_storage"
    video_conferencing = "video_conferencing"
    library_website = "library_website"
    digital_resources = "digital_resources"
    accessibility_features = "accessibility_features"
    other = "other"


# ============================================================================
# Staff Expertise Schemas
# ============================================================================

class TechAssistanceStaffBase(BaseModel):
    expertise_topics: list[str] = Field(..., min_items=1)
    max_concurrent_sessions: int = Field(default=3, ge=1, le=10)
    bio: Optional[str] = None
    languages: Optional[list[str]] = None
    is_volunteer_coordinator: bool = False


class TechAssistanceStaffCreate(StrictInputSchema, TechAssistanceStaffBase):
    pass


class TechAssistanceStaffUpdate(StrictInputSchema):
    expertise_topics: Optional[list[str]] = None
    max_concurrent_sessions: Optional[int] = Field(None, ge=1, le=10)
    bio: Optional[str] = None
    languages: Optional[list[str]] = None
    is_volunteer_coordinator: Optional[bool] = None
    is_active: Optional[bool] = None


class TechAssistanceStaffResponse(TechAssistanceStaffBase):
    id: int
    staff_id: int
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Booking Schemas
# ============================================================================

class TechAssistanceBookingBase(BaseModel):
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)
    topic: str = Field(..., min_length=1)
    skill_level: str = Field(default="beginner")
    description: Optional[str] = None
    preferred_staff_id: Optional[int] = None

    @field_validator("topic", mode="before")
    @classmethod
    def validate_topic(cls, v: object) -> str:
        from enum import Enum
        if isinstance(v, Enum):
            v = v.value
        s = str(v)
        valid_topics = [
            "email", "smartphone", "tablet", "computer_basics",
            "internet_browsing", "social_media", "password_management",
            "online_safety", "resume_building", "job_search_online",
            "cloud_storage", "video_conferencing", "library_website",
            "digital_resources", "accessibility_features", "other"
        ]
        if s not in valid_topics:
            raise ValueError(f"Topic must be one of: {', '.join(valid_topics)}")
        return s

    @field_validator("skill_level", mode="before")
    @classmethod
    def validate_skill_level(cls, v: object) -> str:
        from enum import Enum
        if isinstance(v, Enum):
            v = v.value
        s = str(v)
        valid_levels = ["beginner", "intermediate", "advanced"]
        if s not in valid_levels:
            raise ValueError(f"Skill level must be one of: {', '.join(valid_levels)}")
        return s

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: datetime, info) -> datetime:
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v


class TechAssistanceBookingCreate(StrictInputSchema, TechAssistanceBookingBase):
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)


class TechAssistanceBookingUpdate(StrictInputSchema):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    topic: Optional[str] = None
    skill_level: Optional[str] = None
    description: Optional[str] = None
    preferred_staff_id: Optional[int] = None
    status: Optional[str] = None


class TechAssistanceBookingResponse(TechAssistanceBookingBase):
    id: int
    patron_id: Optional[int] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    status: str
    assigned_staff_id: Optional[int] = None
    checked_in_at: Optional[datetime] = None
    session_start_actual: Optional[datetime] = None
    session_end_actual: Optional[datetime] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class TechAssistanceBookingListResponse(BaseModel):
    id: int
    start_time: datetime
    end_time: datetime
    topic: str
    skill_level: str
    status: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Session Notes Schemas
# ============================================================================

class TechSessionNoteBase(BaseModel):
    content: str = Field(..., min_length=1)
    topics_covered: Optional[list[str]] = None
    concepts_taught: Optional[list[str]] = None
    patron_comprehension_level: Optional[int] = Field(None, ge=1, le=5)
    recommendations: Optional[str] = None
    challenges: Optional[str] = None


class TechSessionNoteCreate(StrictInputSchema, TechSessionNoteBase):
    pass


class TechSessionNoteUpdate(StrictInputSchema):
    content: Optional[str] = Field(None, min_length=1)
    topics_covered: Optional[list[str]] = None
    concepts_taught: Optional[list[str]] = None
    patron_comprehension_level: Optional[int] = Field(None, ge=1, le=5)
    recommendations: Optional[str] = None
    challenges: Optional[str] = None


class TechSessionNoteResponse(TechSessionNoteBase):
    id: int
    booking_id: int
    created_by: Optional[int] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Follow-Up Booking Schemas
# ============================================================================

class TechFollowUpBookingBase(BaseModel):
    status: str = Field(default="not_needed")
    suggested_topics: Optional[list[str]] = None
    reason: Optional[str] = None
    suggested_timing: Optional[str] = None
    patron_agreed: bool = False


class TechFollowUpBookingCreate(StrictInputSchema, TechFollowUpBookingBase):
    pass


class TechFollowUpBookingUpdate(StrictInputSchema):
    status: Optional[str] = None
    suggested_topics: Optional[list[str]] = None
    reason: Optional[str] = None
    suggested_timing: Optional[str] = None
    patron_agreed: Optional[bool] = None


class TechFollowUpBookingResponse(TechFollowUpBookingBase):
    id: int
    original_booking_id: int
    follow_up_booking_id: Optional[int] = None
    patron_agreed_at: Optional[datetime] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Resource Handout Schemas
# ============================================================================

class TechResourceHandoutBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    resource_url: Optional[str] = Field(None, max_length=500)
    file_path: Optional[str] = Field(None, max_length=500)
    resource_type: Optional[str] = Field(None, max_length=100)
    topics: Optional[list[str]] = None


class TechResourceHandoutCreate(StrictInputSchema, TechResourceHandoutBase):
    pass


class TechResourceHandoutUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    resource_url: Optional[str] = Field(None, max_length=500)
    file_path: Optional[str] = Field(None, max_length=500)
    resource_type: Optional[str] = Field(None, max_length=100)
    topics: Optional[list[str]] = None
    sent_to_patron: Optional[bool] = None


class TechResourceHandoutResponse(TechResourceHandoutBase):
    id: int
    booking_id: int
    sent_to_patron: bool
    sent_at: Optional[datetime] = None
    sent_method: Optional[str] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Skill Impact Schemas
# ============================================================================

class TechSkillImpactBase(BaseModel):
    skills_learned: Optional[list[str]] = None
    confidence_before: Optional[int] = Field(None, ge=1, le=5)
    confidence_after: Optional[int] = Field(None, ge=1, le=5)
    independence_level: Optional[int] = Field(None, ge=1, le=5)
    goal_achieved: bool = False
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)
    patron_feedback: Optional[str] = None
    interested_in_future_sessions: bool = False
    staff_recommendation: Optional[str] = None


class TechSkillImpactCreate(StrictInputSchema, TechSkillImpactBase):
    pass


class TechSkillImpactUpdate(StrictInputSchema):
    skills_learned: Optional[list[str]] = None
    confidence_before: Optional[int] = Field(None, ge=1, le=5)
    confidence_after: Optional[int] = Field(None, ge=1, le=5)
    independence_level: Optional[int] = Field(None, ge=1, le=5)
    goal_achieved: Optional[bool] = None
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)
    patron_feedback: Optional[str] = None
    interested_in_future_sessions: Optional[bool] = None
    staff_recommendation: Optional[str] = None


class TechSkillImpactResponse(TechSkillImpactBase):
    id: int
    booking_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Volunteer Tutor Schemas
# ============================================================================

class TechVolunteerTutorBase(BaseModel):
    expertise_topics: list[str] = Field(..., min_items=1)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    background: Optional[str] = None
    has_background_check: bool = False
    training_completed: bool = False


class TechVolunteerTutorCreate(StrictInputSchema, TechVolunteerTutorBase):
    pass


class TechVolunteerTutorUpdate(StrictInputSchema):
    expertise_topics: Optional[list[str]] = None
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    background: Optional[str] = None
    has_background_check: Optional[bool] = None
    training_completed: Optional[bool] = None
    is_active: Optional[bool] = None


class TechVolunteerTutorResponse(TechVolunteerTutorBase):
    id: int
    volunteer_id: int
    is_active: bool
    approval_status: str
    approved_at: Optional[datetime] = None
    total_sessions: int
    average_rating: float
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Complex Response Schemas
# ============================================================================

class BookingDetailResponse(TechAssistanceBookingResponse):
    assigned_staff: Optional[TechAssistanceStaffResponse] = None
    session_notes: list[TechSessionNoteResponse] = []
    resources: list[TechResourceHandoutResponse] = []
    follow_ups: list[TechFollowUpBookingResponse] = []
    impact_tracking: Optional[TechSkillImpactResponse] = None

    class Config:
        from_attributes = True


# ============================================================================
# Availability Schemas
# ============================================================================

class AvailabilitySlot(BaseModel):
    date: str
    start_time: str
    end_time: str
    staff_id: Optional[int] = None
    staff_name: Optional[str] = None
    topics: list[str] = []


class AvailabilityResponse(BaseModel):
    slots: list[AvailabilitySlot] = []
    topic: Optional[str] = None
    date_range_start: str
    date_range_end: str


# ============================================================================
# Cancel Booking Schema
# ============================================================================

class CancelBookingRequest(StrictInputSchema):
    reason: Optional[str] = Field(None, max_length=500)


# ============================================================================
# Complete Session Schema
# ============================================================================

class CompleteSessionRequest(StrictInputSchema):
    notes: Optional[TechSessionNoteCreate] = None
    impact: Optional[TechSkillImpactCreate] = None
    follow_up_needed: bool = False
    follow_up_topics: Optional[list[str]] = None
    follow_up_reason: Optional[str] = None
    follow_up_timing: Optional[str] = None
    resource_ids_to_send: Optional[list[int]] = None


# ============================================================================
# Impact Summary Schema
# ============================================================================

class ImpactSummaryResponse(BaseModel):
    total_sessions: int = 0
    average_confidence_improvement: float = 0.0
    goal_achievement_rate: float = 0.0
    average_satisfaction: float = 0.0
    skills_learned: list[str] = []


# ============================================================================
# Patron History Schema
# ============================================================================

class PatronBookingHistoryResponse(BaseModel):
    bookings: list[BookingDetailResponse] = []
    total_sessions: int = 0
    topics_covered: list[str] = []
    impact_summary: Optional[ImpactSummaryResponse] = None
