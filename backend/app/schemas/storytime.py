# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from typing import ClassVar, List, Optional

from pydantic import BaseModel, Field, EmailStr, field_validator

from app.schemas._base import StrictInputSchema


# ============================================================================
# Storytime Series
# ============================================================================

class StorytimeSeriesCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    series_type: str = "weekly"
    primary_age_group: str
    secondary_age_groups: List[str] = []
    location: str = Field(..., min_length=1, max_length=255)
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    duration_minutes: int = Field(30, ge=15, le=180)
    max_capacity: Optional[int] = None
    primary_leader_id: Optional[int] = None
    secondary_leader_ids: List[int] = []
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool = True
    is_registration_required: bool = False
    is_virtual: bool = False
    virtual_link: Optional[str] = None
    image_url: Optional[str] = None


class StorytimeSeriesUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    series_type: Optional[str] = None
    primary_age_group: Optional[str] = None
    secondary_age_groups: Optional[List[str]] = None
    location: Optional[str] = None
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    max_capacity: Optional[int] = None
    primary_leader_id: Optional[int] = None
    secondary_leader_ids: Optional[List[int]] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
    is_registration_required: Optional[bool] = None
    is_virtual: Optional[bool] = None
    virtual_link: Optional[str] = None
    image_url: Optional[str] = None


class StorytimeSeriesResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    series_type: str
    primary_age_group: str
    secondary_age_groups: List[str]
    location: str
    day_of_week: Optional[str]
    start_time: Optional[str]
    duration_minutes: int
    max_capacity: Optional[int]
    primary_leader_id: Optional[int]
    secondary_leader_ids: List[int]
    start_date: Optional[date]
    end_date: Optional[date]
    is_active: bool
    is_registration_required: bool
    is_virtual: bool
    virtual_link: Optional[str]
    image_url: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Storytime Sessions
# ============================================================================

class StorytimeSessionCreate(StrictInputSchema):
    series_id: int
    session_date: date
    start_time: datetime
    end_time: Optional[datetime] = None
    theme_id: Optional[int] = None
    book_ids: List[int] = []
    assigned_leader_id: Optional[int] = None
    sub_leader_id: Optional[int] = None
    expected_attendance: int = 0
    weather_alert: Optional[str] = None


class StorytimeSessionUpdate(StrictInputSchema):
    session_date: Optional[date] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    theme_id: Optional[int] = None
    book_ids: Optional[List[int]] = None
    assigned_leader_id: Optional[int] = None
    sub_leader_id: Optional[int] = None
    status: Optional[str] = None
    is_cancelled: Optional[bool] = None
    cancellation_reason: Optional[str] = None
    expected_attendance: Optional[int] = None
    actual_attendance: Optional[int] = None
    weather_alert: Optional[str] = None


class StorytimeSessionResponse(BaseModel):
    id: int
    series_id: int
    session_date: date
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    theme_id: Optional[int]
    book_ids: List[int]
    assigned_leader_id: Optional[int]
    sub_leader_id: Optional[int]
    is_cancelled: bool
    cancellation_reason: Optional[str]
    expected_attendance: int
    actual_attendance: int
    weather_alert: Optional[str]
    reminder_sent_at: Optional[datetime]
    cancellation_notification_sent_at: Optional[datetime]
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # is_cancelled is nullable in the DB but declared non-null here; rows hold
    # NULL, which from_attributes hands pydantic as an explicit None and the
    # response 500s. Coerce None back to the default.
    _NULL_DEFAULTS: ClassVar[dict] = {"is_cancelled": False}

    @field_validator("is_cancelled", mode="before")
    @classmethod
    def _coerce_null_to_default(cls, v, info):
        if v is None:
            return cls._NULL_DEFAULTS.get(info.field_name)
        return v

    class Config:
        from_attributes = True


# ============================================================================
# Attendance
# ============================================================================

class StorytimeAttendanceCreate(StrictInputSchema):
    session_id: int
    user_id: Optional[int] = None
    child_name: Optional[str] = None
    caregiver_name: Optional[str] = None
    age_group: Optional[str] = None
    attendee_type: str
    is_first_time: bool = False
    caregiver_email: Optional[str] = None
    caregiver_phone: Optional[str] = None
    feedback: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)


class StorytimeAttendanceResponse(BaseModel):
    id: int
    session_id: int
    user_id: Optional[int]
    child_name: Optional[str]
    caregiver_name: Optional[str]
    age_group: Optional[str]
    attendee_type: str
    is_first_time: bool
    caregiver_email: Optional[str]
    caregiver_phone: Optional[str]
    feedback: Optional[str]
    rating: Optional[int]
    checked_in_at: datetime
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Repeat Attendees
# ============================================================================

class RepeatAttendeeResponse(BaseModel):
    id: int
    caregiver_identifier: str
    caregiver_name: Optional[str]
    caregiver_email: Optional[str]
    total_sessions_attended: int
    last_attended_date: date
    first_attended_date: date
    recognition_status: str
    recognition_badges: List[str]
    recognition_announcement_sent: bool
    prefers_contact: bool
    theme_preferences: List[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Theme Management
# ============================================================================

class StorytimeThemeCreate(StrictInputSchema):
    series_id: int
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    theme_color: Optional[str] = None
    learning_objectives: Optional[str] = None
    discussion_points: List[str] = []
    song_ids: List[int] = []
    rhyme_ids: List[int] = []
    craft_ids: List[int] = []
    image_url: Optional[str] = None


class StorytimeThemeUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    theme_color: Optional[str] = None
    learning_objectives: Optional[str] = None
    discussion_points: Optional[List[str]] = None
    song_ids: Optional[List[int]] = None
    rhyme_ids: Optional[List[int]] = None
    craft_ids: Optional[List[int]] = None
    image_url: Optional[str] = None


class StorytimeThemeResponse(BaseModel):
    id: int
    series_id: int
    title: str
    description: Optional[str]
    theme_color: Optional[str]
    learning_objectives: Optional[str]
    discussion_points: List[str]
    song_ids: List[int]
    rhyme_ids: List[int]
    craft_ids: List[int]
    image_url: Optional[str]
    times_used: int
    last_used_date: Optional[date]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Books
# ============================================================================

class StorytimeBookCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    illustrator: Optional[str] = None
    isbn: Optional[str] = None
    description: Optional[str] = None
    age_groups: List[str] = []
    word_count: Optional[int] = None
    page_count: Optional[int] = None
    library_call_number: Optional[str] = None
    is_in_collection: bool = True
    librarian_notes: Optional[str] = None
    image_url: Optional[str] = None


class StorytimeBookUpdate(StrictInputSchema):
    title: Optional[str] = None
    author: Optional[str] = None
    illustrator: Optional[str] = None
    description: Optional[str] = None
    age_groups: Optional[List[str]] = None
    word_count: Optional[int] = None
    page_count: Optional[int] = None
    library_call_number: Optional[str] = None
    is_in_collection: Optional[bool] = None
    librarian_notes: Optional[str] = None
    image_url: Optional[str] = None


class StorytimeBookResponse(BaseModel):
    id: int
    title: str
    author: str
    illustrator: Optional[str]
    isbn: Optional[str]
    description: Optional[str]
    age_groups: List[str]
    word_count: Optional[int]
    page_count: Optional[int]
    library_call_number: Optional[str]
    is_in_collection: bool
    times_read: int
    last_read_date: Optional[date]
    average_rating: Optional[float]
    librarian_notes: Optional[str]
    image_url: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Songs and Rhymes
# ============================================================================

class StorytimeSongCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=255)
    composer: Optional[str] = None
    lyricist: Optional[str] = None
    lyrics: Optional[str] = None
    melody_description: Optional[str] = None
    age_groups: List[str] = []
    themes: List[str] = []
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    image_url: Optional[str] = None
    librarian_notes: Optional[str] = None
    movement_suggestions: Optional[str] = None


class StorytimeSongResponse(BaseModel):
    id: int
    title: str
    composer: Optional[str]
    lyricist: Optional[str]
    lyrics: Optional[str]
    melody_description: Optional[str]
    age_groups: List[str]
    themes: List[str]
    audio_url: Optional[str]
    video_url: Optional[str]
    image_url: Optional[str]
    times_used: int
    last_used_date: Optional[date]
    librarian_notes: Optional[str]
    movement_suggestions: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class StorytimeRhymeCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=255)
    author: Optional[str] = None
    text: str
    hand_motions_description: Optional[str] = None
    age_groups: List[str] = []
    themes: List[str] = []
    motor_skill_level: Optional[str] = None
    video_url: Optional[str] = None
    image_url: Optional[str] = None
    librarian_notes: Optional[str] = None


class StorytimeRhymeResponse(BaseModel):
    id: int
    title: str
    author: Optional[str]
    text: str
    hand_motions_description: Optional[str]
    age_groups: List[str]
    themes: List[str]
    motor_skill_level: Optional[str]
    video_url: Optional[str]
    image_url: Optional[str]
    times_used: int
    last_used_date: Optional[date]
    librarian_notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Crafts
# ============================================================================

class StorytimeCraftCreate(StrictInputSchema):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    age_groups: List[str] = []
    themes: List[str] = []
    complexity: str = "simple"
    step_by_step_instructions: Optional[str] = None
    estimated_time_minutes: Optional[int] = None
    required_supplies: List[str] = []
    optional_supplies: List[str] = []
    supplies_cost_estimate: Optional[float] = None
    image_url: Optional[str] = None
    tutorial_video_url: Optional[str] = None
    librarian_notes: Optional[str] = None
    success_tips: Optional[str] = None
    cleanup_notes: Optional[str] = None


class StorytimeCraftResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    age_groups: List[str]
    themes: List[str]
    complexity: str
    step_by_step_instructions: Optional[str]
    estimated_time_minutes: Optional[int]
    required_supplies: List[str]
    optional_supplies: List[str]
    supplies_cost_estimate: Optional[float]
    image_url: Optional[str]
    tutorial_video_url: Optional[str]
    times_used: int
    last_used_date: Optional[date]
    librarian_notes: Optional[str]
    success_tips: Optional[str]
    cleanup_notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Craft Supply Inventory
# ============================================================================

class CraftSupplyInventoryCreate(StrictInputSchema):
    supply_name: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = None
    quantity_on_hand: int = Field(0, ge=0)
    reorder_level: int = Field(10, ge=0)
    supplier_name: Optional[str] = None
    cost_per_unit: Optional[float] = None
    storage_location: Optional[str] = None
    notes: Optional[str] = None


class CraftSupplyInventoryResponse(BaseModel):
    id: int
    supply_name: str
    category: Optional[str]
    quantity_on_hand: int
    reorder_level: int
    last_restocked_date: Optional[date]
    supplier_name: Optional[str]
    cost_per_unit: Optional[float]
    storage_location: Optional[str]
    times_used: int
    average_usage_per_session: Optional[float]
    notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Caregiver Communication
# ============================================================================

class CaregiverContactCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    child_name: Optional[str] = None
    child_age_group: Optional[str] = None
    preferred_contact_method: str = "email"
    opt_in_reminders: bool = True
    opt_in_theme_previews: bool = True
    opt_in_feedback: bool = True
    opt_in_announcements: bool = True
    interested_themes: List[str] = []
    interested_age_groups: List[str] = []


class CaregiverContactUpdate(StrictInputSchema):
    name: Optional[str] = None
    phone: Optional[str] = None
    child_name: Optional[str] = None
    child_age_group: Optional[str] = None
    preferred_contact_method: Optional[str] = None
    opt_in_reminders: Optional[bool] = None
    opt_in_theme_previews: Optional[bool] = None
    opt_in_feedback: Optional[bool] = None
    opt_in_announcements: Optional[bool] = None
    interested_themes: Optional[List[str]] = None
    interested_age_groups: Optional[List[str]] = None


class CaregiverContactResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    child_name: Optional[str]
    child_age_group: Optional[str]
    preferred_contact_method: str
    opt_in_reminders: bool
    opt_in_theme_previews: bool
    opt_in_feedback: bool
    opt_in_announcements: bool
    interested_themes: List[str]
    interested_age_groups: List[str]
    sessions_attended: int
    last_contact_date: Optional[date]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class CaregiverCommunicationCreate(StrictInputSchema):
    caregiver_contact_id: int
    session_id: Optional[int] = None
    communication_type: str
    contact_method: str
    subject: Optional[str] = None
    message: str


class CaregiverCommunicationResponse(BaseModel):
    id: int
    caregiver_contact_id: int
    session_id: Optional[int]
    communication_type: str
    contact_method: str
    subject: Optional[str]
    message: str
    is_sent: bool
    sent_at: Optional[datetime]
    opened_at: Optional[datetime]
    clicked_at: Optional[datetime]
    responded: bool
    response_received_at: Optional[datetime]
    response_text: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Sub Leader Management
# ============================================================================

class StorytimeSubLeaderCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    experience_level: Optional[str] = None
    certifications: List[str] = []
    background_check_date: Optional[date] = None
    available_days: List[str] = []
    available_times: List[str] = []
    max_assignments_per_month: Optional[int] = None
    specializes_in: List[str] = []
    prefers_contact_method: str = "email"


class StorytimeSubLeaderUpdate(StrictInputSchema):
    name: Optional[str] = None
    phone: Optional[str] = None
    experience_level: Optional[str] = None
    certifications: Optional[List[str]] = None
    background_check_date: Optional[date] = None
    status: Optional[str] = None
    available_days: Optional[List[str]] = None
    available_times: Optional[List[str]] = None
    max_assignments_per_month: Optional[int] = None
    specializes_in: Optional[List[str]] = None
    prefers_contact_method: Optional[str] = None


class StorytimeSubLeaderResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    experience_level: Optional[str]
    certifications: List[str]
    background_check_date: Optional[date]
    status: str
    available_days: List[str]
    available_times: List[str]
    max_assignments_per_month: Optional[int]
    specializes_in: List[str]
    total_sessions_led: int
    last_assigned_date: Optional[date]
    assignments_this_month: int
    average_rating: Optional[float]
    feedback_notes: Optional[str]
    prefers_contact_method: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class SubLeaderAssignmentCreate(StrictInputSchema):
    session_id: int
    sub_leader_id: int
    special_instructions: Optional[str] = None


class SubLeaderAssignmentResponse(BaseModel):
    id: int
    session_id: int
    sub_leader_id: int
    confirmed: bool
    confirmed_at: Optional[datetime]
    completed: bool
    completed_at: Optional[datetime]
    rating: Optional[int]
    feedback: Optional[str]
    special_instructions: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Annual Planning
# ============================================================================

class StorytimeAnnualPlanCreate(StrictInputSchema):
    year: int
    annual_theme: Optional[str] = None
    goals: List[str] = []
    special_events: List[str] = []
    total_sessions_planned: int = 0
    expected_total_attendance: int = 0
    estimated_budget: Optional[float] = None
    notes: Optional[str] = None


class StorytimeAnnualPlanResponse(BaseModel):
    id: int
    year: int
    annual_theme: Optional[str]
    goals: List[str]
    special_events: List[str]
    total_sessions_planned: int
    expected_total_attendance: int
    estimated_budget: Optional[float]
    notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class StorytimeMonthlyPlanCreate(StrictInputSchema):
    year: int
    month: int = Field(..., ge=1, le=12)
    monthly_theme: Optional[str] = None
    learning_focus: Optional[str] = None
    sessions_planned: int = 0
    expected_attendance: int = 0
    special_dates: List[str] = []
    craft_supply_needs: List[str] = []
    notes: Optional[str] = None


class StorytimeMonthlyPlanResponse(BaseModel):
    id: int
    year: int
    month: int
    monthly_theme: Optional[str]
    learning_focus: Optional[str]
    sessions_planned: int
    expected_attendance: int
    special_dates: List[str]
    craft_supply_needs: List[str]
    notes: Optional[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Weather Alerts
# ============================================================================

class WeatherAlertCreate(StrictInputSchema):
    alert_type: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    severity: Optional[str] = None
    affected_locations: List[str] = []
    effective_from: datetime
    effective_until: Optional[datetime] = None
    should_cancel_programs: bool = False
    recommended_action: Optional[str] = None


class WeatherAlertResponse(BaseModel):
    id: int
    alert_type: str
    description: Optional[str]
    severity: Optional[str]
    affected_locations: List[str]
    effective_from: datetime
    effective_until: Optional[datetime]
    should_cancel_programs: bool
    recommended_action: Optional[str]
    sessions_cancelled: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class WeatherCancellationApplyRequest(StrictInputSchema):
    include_only_scheduled: bool = True
    cancellation_reason: Optional[str] = "Cancelled due to weather alert"
