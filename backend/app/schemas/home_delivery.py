# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import StrictInputSchema

from ..models.home_delivery import (
    DeliveryFrequency, DeliveryItemStatus, DeliveryStatus,
    HomeDeliveryApplicationStatus, HomeDeliveryEnrollmentStatus,
    RouteStatus, DeliveryVolunteerStatus
)


# ============================================================================
# HomeDelivery Application Schemas
# ============================================================================

class HomeDeliveryApplicationCreate(StrictInputSchema):
    reason: str = Field(..., min_length=10, max_length=2000)
    medical_documentation: bool = False
    delivery_address: str = Field(..., min_length=10, max_length=500)
    delivery_instructions: Optional[str] = Field(None, max_length=1000)
    contact_phone: str = Field(..., min_length=10, max_length=20)
    alternate_contact_name: Optional[str] = Field(None, max_length=200)
    alternate_contact_phone: Optional[str] = Field(None, max_length=20)
    preferred_frequency: DeliveryFrequency = DeliveryFrequency.biweekly
    preferred_day: Optional[str] = Field(None, max_length=20)
    preferred_time_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    preferred_time_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")


class HomeDeliveryApplicationReview(BaseModel):
    status: HomeDeliveryApplicationStatus
    review_notes: Optional[str] = Field(None, max_length=2000)
    denial_reason: Optional[str] = Field(None, max_length=1000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: HomeDeliveryApplicationStatus) -> HomeDeliveryApplicationStatus:
        if v == HomeDeliveryApplicationStatus.pending:
            raise ValueError("Cannot set status to pending during review")
        return v


class HomeDeliveryApplicationResponse(BaseModel):
    id: int
    patron_id: int
    patron_name: Optional[str] = None
    patron_library_card: Optional[str] = None
    status: HomeDeliveryApplicationStatus
    reason: str
    medical_documentation: bool
    delivery_address: str
    delivery_instructions: Optional[str] = None
    contact_phone: str
    alternate_contact_name: Optional[str] = None
    alternate_contact_phone: Optional[str] = None
    preferred_frequency: DeliveryFrequency
    preferred_day: Optional[str] = None
    preferred_time_start: Optional[str] = None
    preferred_time_end: Optional[str] = None
    submitted_at: datetime
    reviewed_by_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    denial_reason: Optional[str] = None

    class Config:
        from_attributes = True


class HomeDeliveryApplicationListResponse(BaseModel):
    applications: list[HomeDeliveryApplicationResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# HomeDelivery Enrollment Schemas
# ============================================================================

class HomeDeliveryEnrollmentCreate(StrictInputSchema):
    application_id: int
    delivery_address: Optional[str] = None  # Override from application if needed
    delivery_instructions: Optional[str] = None
    contact_phone: Optional[str] = None
    delivery_frequency: Optional[DeliveryFrequency] = None
    preferred_day: Optional[str] = None
    preferred_time_start: Optional[str] = None
    preferred_time_end: Optional[str] = None
    assigned_volunteer_id: Optional[int] = None
    next_scheduled_delivery: Optional[date] = None


class HomeDeliveryEnrollmentUpdate(StrictInputSchema):
    delivery_address: Optional[str] = Field(None, max_length=500)
    delivery_instructions: Optional[str] = Field(None, max_length=1000)
    contact_phone: Optional[str] = Field(None, max_length=20)
    alternate_contact_name: Optional[str] = Field(None, max_length=200)
    alternate_contact_phone: Optional[str] = Field(None, max_length=20)
    delivery_frequency: Optional[DeliveryFrequency] = None
    preferred_day: Optional[str] = None
    preferred_time_start: Optional[str] = None
    preferred_time_end: Optional[str] = None
    assigned_volunteer_id: Optional[int] = None
    next_scheduled_delivery: Optional[date] = None


class HomeDeliveryEnrollmentStatusUpdate(StrictInputSchema):
    status: HomeDeliveryEnrollmentStatus
    pause_reason: Optional[str] = Field(None, max_length=500)
    pause_until: Optional[date] = None
    termination_reason: Optional[str] = Field(None, max_length=500)


class ReadingPreferenceProfileUpdate(StrictInputSchema):
    format_preferences: Optional[list[str]] = None
    preferred_genres: Optional[list[str]] = None
    excluded_genres: Optional[list[str]] = None
    favorite_authors: Optional[list[str]] = None
    excluded_authors: Optional[list[str]] = None
    fiction_preference: Optional[float] = Field(None, ge=0, le=1)
    content_rating: Optional[str] = None
    language_preference: Optional[str] = None
    interests: Optional[list[str]] = None
    prefers_large_print: Optional[bool] = None
    prefers_audiobooks: Optional[bool] = None
    prefers_short_books: Optional[bool] = None
    max_pages_preference: Optional[int] = Field(None, ge=50, le=2000)
    notes: Optional[str] = Field(None, max_length=2000)
    current_series: Optional[list[dict]] = None


class ReadingPreferenceProfileResponse(BaseModel):
    id: int
    enrollment_id: int
    format_preferences: list[str]
    preferred_genres: list[str]
    excluded_genres: list[str]
    favorite_authors: list[str]
    excluded_authors: list[str]
    fiction_preference: float
    content_rating: str
    language_preference: str
    interests: list[str]
    prefers_large_print: bool
    prefers_audiobooks: bool
    prefers_short_books: bool
    max_pages_preference: Optional[int] = None
    notes: Optional[str] = None
    current_series: list[dict]

    class Config:
        from_attributes = True


class HomeDeliveryEnrollmentResponse(BaseModel):
    id: int
    patron_id: int
    patron_name: Optional[str] = None
    patron_library_card: Optional[str] = None
    application_id: Optional[int] = None
    status: HomeDeliveryEnrollmentStatus
    delivery_address: str
    delivery_instructions: Optional[str] = None
    contact_phone: str
    alternate_contact_name: Optional[str] = None
    alternate_contact_phone: Optional[str] = None
    delivery_frequency: DeliveryFrequency
    preferred_day: Optional[str] = None
    preferred_time_start: Optional[str] = None
    preferred_time_end: Optional[str] = None
    next_scheduled_delivery: Optional[date] = None
    assigned_volunteer_id: Optional[int] = None
    assigned_volunteer_name: Optional[str] = None
    enrolled_at: datetime
    paused_at: Optional[datetime] = None
    pause_reason: Optional[str] = None
    pause_until: Optional[date] = None
    total_deliveries: int
    last_delivery_date: Optional[date] = None
    reading_preferences: Optional[ReadingPreferenceProfileResponse] = None

    class Config:
        from_attributes = True


class HomeDeliveryEnrollmentListResponse(BaseModel):
    enrollments: list[HomeDeliveryEnrollmentResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Delivery Volunteer Schemas
# ============================================================================

class DeliveryVolunteerCreate(StrictInputSchema):
    user_id: int
    phone: str = Field(..., min_length=10, max_length=20)
    emergency_contact_name: Optional[str] = Field(None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    has_vehicle: bool = True
    vehicle_type: Optional[str] = Field(None, max_length=100)
    can_transport_large_items: bool = True
    available_days: list[str] = []
    available_time_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    available_time_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    max_deliveries_per_day: int = Field(5, ge=1, le=20)
    max_deliveries_per_week: int = Field(15, ge=1, le=50)
    preferred_areas: list[str] = []
    max_driving_distance: Optional[int] = Field(None, ge=1, le=100)


class DeliveryVolunteerUpdate(StrictInputSchema):
    phone: Optional[str] = Field(None, max_length=20)
    emergency_contact_name: Optional[str] = Field(None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    has_vehicle: Optional[bool] = None
    vehicle_type: Optional[str] = Field(None, max_length=100)
    can_transport_large_items: Optional[bool] = None
    available_days: Optional[list[str]] = None
    available_time_start: Optional[str] = None
    available_time_end: Optional[str] = None
    max_deliveries_per_day: Optional[int] = Field(None, ge=1, le=20)
    max_deliveries_per_week: Optional[int] = Field(None, ge=1, le=50)
    preferred_areas: Optional[list[str]] = None
    max_driving_distance: Optional[int] = Field(None, ge=1, le=100)


class DeliveryVolunteerStatusUpdate(StrictInputSchema):
    status: DeliveryVolunteerStatus
    background_check_completed: Optional[bool] = None
    background_check_date: Optional[date] = None
    background_check_expiry: Optional[date] = None
    training_completed: Optional[bool] = None
    training_date: Optional[date] = None


class DeliveryVolunteerResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    status: DeliveryVolunteerStatus
    phone: str
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    has_vehicle: bool = False
    vehicle_type: Optional[str] = None
    can_transport_large_items: bool = False
    background_check_completed: bool = False
    background_check_date: Optional[date] = None
    background_check_expiry: Optional[date] = None
    training_completed: bool = False
    training_date: Optional[date] = None
    available_days: list[str] = []
    available_time_start: Optional[str] = None
    available_time_end: Optional[str] = None
    max_deliveries_per_day: int = 0
    max_deliveries_per_week: int = 0
    preferred_areas: list[str] = []
    max_driving_distance: Optional[int] = None
    total_deliveries: int = 0
    total_volunteer_hours: float = 0.0
    recognition_level: str = "new"
    achievements: list[dict] = []
    approved_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None
    assigned_patrons_count: Optional[int] = None

    class Config:
        from_attributes = True


class DeliveryVolunteerListResponse(BaseModel):
    volunteers: list[DeliveryVolunteerResponse]
    total: int
    limit: int
    offset: int


class VolunteerScheduleCreate(StrictInputSchema):
    date: date
    is_available: bool = True
    time_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    time_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    notes: Optional[str] = Field(None, max_length=500)


class VolunteerScheduleResponse(BaseModel):
    id: int
    volunteer_id: int
    date: date
    is_available: bool
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class VolunteerHourLogCreate(StrictInputSchema):
    date: date
    hours: float = Field(..., gt=0, le=24)
    activity_type: str = Field(..., max_length=50)
    delivery_route_id: Optional[int] = None
    notes: Optional[str] = Field(None, max_length=500)


class VolunteerHourLogResponse(BaseModel):
    id: int
    volunteer_id: int
    volunteer_name: Optional[str] = None
    date: date
    hours: float
    activity_type: str
    delivery_route_id: Optional[int] = None
    notes: Optional[str] = None
    verified: bool
    verified_by_id: Optional[int] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VolunteerHourLogListResponse(BaseModel):
    logs: list[VolunteerHourLogResponse]
    total: int
    total_hours: float
    limit: int
    offset: int


# ============================================================================
# Delivery Route Schemas
# ============================================================================

class DeliveryRouteCreate(StrictInputSchema):
    name: str = Field(..., min_length=1, max_length=100)
    date: date
    volunteer_id: Optional[int] = None
    planned_start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    planned_end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    notes: Optional[str] = Field(None, max_length=1000)


class DeliveryRouteUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, max_length=100)
    date: Optional[date] = None
    volunteer_id: Optional[int] = None
    planned_start_time: Optional[str] = None
    planned_end_time: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)


class DeliveryRouteStatusUpdate(StrictInputSchema):
    status: RouteStatus
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None


class DeliveryRouteReorderRequest(StrictInputSchema):
    optimized_order: list[int] = Field(..., min_length=1)


class DeliveryRouteOptimizeRequest(StrictInputSchema):
    delivery_ids: list[int]
    start_location: Optional[str] = None  # Optional start address


class DeliveryRouteResponse(BaseModel):
    id: int
    name: str
    date: date
    status: RouteStatus
    volunteer_id: Optional[int] = None
    volunteer_name: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    estimated_distance_miles: Optional[float] = None
    optimized_order: list[int]
    planned_start_time: Optional[str] = None
    planned_end_time: Optional[str] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    total_stops: int
    completed_stops: int
    total_items: int
    notes: Optional[str] = None
    created_by_id: Optional[int] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class DeliveryRouteDetailResponse(DeliveryRouteResponse):
    deliveries: list["DeliveryResponse"] = []


class DeliveryRouteListResponse(BaseModel):
    routes: list[DeliveryRouteResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Delivery Schemas
# ============================================================================

class DeliveryCreate(StrictInputSchema):
    enrollment_id: int
    scheduled_date: date
    scheduled_time_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    scheduled_time_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    route_id: Optional[int] = None
    staff_notes: Optional[str] = Field(None, max_length=1000)


class DeliveryUpdate(StrictInputSchema):
    scheduled_date: Optional[date] = None
    scheduled_time_start: Optional[str] = None
    scheduled_time_end: Optional[str] = None
    route_id: Optional[int] = None
    route_order: Optional[int] = None
    delivery_address: Optional[str] = Field(None, max_length=500)
    delivery_instructions: Optional[str] = Field(None, max_length=1000)
    staff_notes: Optional[str] = Field(None, max_length=1000)
    patron_notes: Optional[str] = Field(None, max_length=1000)


class DeliveryStatusUpdate(StrictInputSchema):
    status: DeliveryStatus
    volunteer_notes: Optional[str] = Field(None, max_length=1000)
    delivery_signature: Optional[str] = None
    delivery_photo: Optional[str] = None
    failure_reason: Optional[str] = Field(None, max_length=500)
    reschedule_date: Optional[date] = None


class DeliveryItemAdd(BaseModel):
    item_id: int
    item_copy_id: Optional[int] = None
    selection_reason: Optional[str] = Field(None, max_length=500)
    patron_requested: bool = False


class DeliveryItemUpdate(StrictInputSchema):
    status: Optional[DeliveryItemStatus] = None
    return_condition: Optional[str] = Field(None, max_length=50)


class DeliveryItemResponse(BaseModel):
    id: int
    delivery_id: int
    item_id: Optional[int] = None
    item_copy_id: Optional[int] = None
    item_title: str
    item_author: Optional[str] = None
    item_format: Optional[str] = None
    item_barcode: Optional[str] = None
    status: DeliveryItemStatus
    checkout_id: Optional[int] = None
    checked_out_at: Optional[datetime] = None
    due_date: Optional[date] = None
    returned_at: Optional[datetime] = None
    return_condition: Optional[str] = None
    selection_reason: Optional[str] = None
    patron_requested: bool

    class Config:
        from_attributes = True


class DeliveryResponse(BaseModel):
    id: int
    enrollment_id: int
    patron_id: Optional[int] = None
    patron_name: Optional[str] = None
    patron_library_card: Optional[str] = None
    route_id: Optional[int] = None
    route_name: Optional[str] = None
    route_order: Optional[int] = None
    status: DeliveryStatus
    scheduled_date: date
    scheduled_time_start: Optional[str] = None
    scheduled_time_end: Optional[str] = None
    delivery_address: str
    delivery_instructions: Optional[str] = None
    packed_at: Optional[datetime] = None
    out_for_delivery_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    delivery_failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    reschedule_date: Optional[date] = None
    pickup_requested: bool
    picked_up_at: Optional[datetime] = None
    items_count: int
    items_delivered: int
    items_picked_up: int
    staff_notes: Optional[str] = None
    patron_notes: Optional[str] = None
    volunteer_notes: Optional[str] = None
    has_feedback: Optional[bool] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class DeliveryDetailResponse(DeliveryResponse):
    items: list[DeliveryItemResponse] = []
    feedback: Optional["DeliveryFeedbackResponse"] = None


class DeliveryListResponse(BaseModel):
    deliveries: list[DeliveryResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Delivery Feedback Schemas
# ============================================================================

class DeliveryFeedbackCreate(StrictInputSchema):
    overall_rating: int = Field(..., ge=1, le=5)
    item_satisfaction: Optional[int] = Field(None, ge=1, le=5)
    volunteer_rating: Optional[int] = Field(None, ge=1, le=5)
    timeliness_rating: Optional[int] = Field(None, ge=1, le=5)
    comments: Optional[str] = Field(None, max_length=2000)
    item_feedback: Optional[str] = Field(None, max_length=2000)
    suggestions_for_next_delivery: Optional[str] = Field(None, max_length=1000)
    would_recommend: Optional[bool] = None


class DeliveryFeedbackResponse(BaseModel):
    id: int
    delivery_id: int
    overall_rating: int
    item_satisfaction: Optional[int] = None
    volunteer_rating: Optional[int] = None
    timeliness_rating: Optional[int] = None
    comments: Optional[str] = None
    item_feedback: Optional[str] = None
    suggestions_for_next_delivery: Optional[str] = None
    would_recommend: Optional[bool] = None
    requires_follow_up: bool
    follow_up_completed: bool
    follow_up_notes: Optional[str] = None
    follow_up_by_name: Optional[str] = None
    follow_up_at: Optional[datetime] = None
    submitted_at: datetime

    class Config:
        from_attributes = True


class DeliveryFeedbackFollowUp(BaseModel):
    follow_up_notes: str = Field(..., max_length=2000)


# ============================================================================
# Item Request Schemas
# ============================================================================

class HomeDeliveryItemRequestCreate(StrictInputSchema):
    request_type: str = Field(..., max_length=50)  # specific_item, author, genre, topic
    title: Optional[str] = Field(None, max_length=500)
    author: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=1000)
    item_id: Optional[int] = None


class HomeDeliveryItemRequestResponse(BaseModel):
    id: int
    enrollment_id: int
    request_type: str
    title: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    item_id: Optional[int] = None
    item_title: Optional[str] = None
    fulfilled: bool
    fulfilled_in_delivery_id: Optional[int] = None
    staff_notes: Optional[str] = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class HomeDeliveryItemRequestListResponse(BaseModel):
    requests: list[HomeDeliveryItemRequestResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Report Schemas
# ============================================================================

class HomeDeliveryReportSummary(BaseModel):
    total_enrolled_patrons: int
    active_enrolled_patrons: int
    pending_applications: int
    active_volunteers: int
    total_deliveries_this_month: int
    total_items_delivered_this_month: int
    average_delivery_rating: Optional[float] = None
    total_volunteer_hours_this_month: float


class HomeDeliveryPatronReport(BaseModel):
    patron_id: int
    patron_name: str
    enrolled_since: date
    total_deliveries: int
    total_items_received: int
    average_rating_given: Optional[float] = None
    last_delivery_date: Optional[date] = None
    assigned_volunteer: Optional[str] = None


class HomeDeliveryVolunteerReport(BaseModel):
    volunteer_id: int
    volunteer_name: str
    status: DeliveryVolunteerStatus
    total_deliveries: int
    total_hours: float
    recognition_level: str
    assigned_patrons: int
    average_rating: Optional[float] = None
    joined_date: date


class HomeDeliveryDeliveryReport(BaseModel):
    period: str  # "2024-01" or "2024-W01"
    total_deliveries: int
    completed_deliveries: int
    failed_deliveries: int
    total_items_delivered: int
    total_items_picked_up: int
    average_items_per_delivery: float
    average_rating: Optional[float] = None


class HomeDeliveryReportResponse(BaseModel):
    summary: HomeDeliveryReportSummary
    patron_reports: list[HomeDeliveryPatronReport]
    volunteer_reports: list[HomeDeliveryVolunteerReport]
    delivery_reports: list[HomeDeliveryDeliveryReport]
    generated_at: datetime


# ============================================================================
# Patron Self-Service Schemas
# ============================================================================

class PatronDeliveryRescheduleRequest(StrictInputSchema):
    new_date: date
    reason: Optional[str] = Field(None, max_length=500)


class PatronEnrollmentPauseRequest(StrictInputSchema):
    pause_until: Optional[date] = None
    reason: Optional[str] = Field(None, max_length=500)


class PatronDeliveryTrackingResponse(BaseModel):
    delivery_id: int
    status: DeliveryStatus
    status_display: str
    scheduled_date: date
    time_window: Optional[str] = None
    delivery_address: str
    items_count: int
    estimated_arrival: Optional[str] = None
    volunteer_name: Optional[str] = None
    is_out_for_delivery: bool = False
    can_reschedule: bool = True
    timeline: list[dict] = []


class DeliveryTimelineEvent(BaseModel):
    event: str
    timestamp: Optional[datetime] = None
    description: str
    completed: bool = False


# ============================================================================
# Enhanced Report Schemas
# ============================================================================

class DeliveryAnalytics(BaseModel):
    period_start: date
    period_end: date
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    success_rate: float
    average_items_per_delivery: float
    average_rating: Optional[float] = None
    total_items_delivered: int
    total_items_picked_up: int
    unique_patrons_served: int
    deliveries_by_day: dict[str, int] = {}
    deliveries_by_status: dict[str, int] = {}
    ratings_distribution: dict[int, int] = {}


class VolunteerAnalytics(BaseModel):
    period_start: date
    period_end: date
    total_active_volunteers: int
    total_hours_logged: float
    average_hours_per_volunteer: float
    total_deliveries_made: int
    average_deliveries_per_volunteer: float
    top_volunteers: list[dict] = []
    volunteers_by_status: dict[str, int] = {}
    hours_by_activity_type: dict[str, float] = {}


class ServiceAnalytics(BaseModel):
    period_start: date
    period_end: date
    delivery_analytics: DeliveryAnalytics
    volunteer_analytics: VolunteerAnalytics
    patron_metrics: dict
    trends: dict


class ExportRequest(StrictInputSchema):
    report_type: str  # "deliveries", "volunteers", "patrons", "summary"
    format: str = "csv"  # "csv", "json", "xlsx"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    filters: Optional[dict] = None


class ExportResponse(BaseModel):
    export_id: str
    status: str  # "pending", "processing", "completed", "failed"
    download_url: Optional[str] = None
    file_name: Optional[str] = None
    record_count: Optional[int] = None
    created_at: datetime | None = None
    expires_at: Optional[datetime] = None


# ============================================================================
# Route Suggestion Schemas
# ============================================================================

class RouteSuggestion(BaseModel):
    suggested_name: str
    delivery_ids: list[int]
    delivery_count: int
    addresses: list[str]
    estimated_distance_miles: Optional[float] = None
    estimated_duration_minutes: Optional[int] = None


class RouteSuggestionsResponse(BaseModel):
    date: date
    suggestions: list[RouteSuggestion]
    unassigned_delivery_count: int


# Forward reference resolution
DeliveryRouteDetailResponse.model_rebuild()
DeliveryDetailResponse.model_rebuild()
