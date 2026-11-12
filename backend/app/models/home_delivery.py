# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, Index, Integer, String, Text,
    UniqueConstraint, text
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


# ============================================================================
# Enums
# ============================================================================

class HomeDeliveryApplicationStatus(StrEnum):
    pending = "pending"
    under_review = "under_review"
    approved = "approved"
    denied = "denied"
    waitlisted = "waitlisted"
    withdrawn = "withdrawn"


class HomeDeliveryEnrollmentStatus(StrEnum):
    active = "active"
    paused = "paused"
    suspended = "suspended"
    terminated = "terminated"


class DeliveryFrequency(StrEnum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    on_demand = "on_demand"


class DeliveryVolunteerStatus(StrEnum):
    active = "active"
    inactive = "inactive"
    on_leave = "on_leave"
    pending_approval = "pending_approval"
    terminated = "terminated"


class DeliveryStatus(StrEnum):
    scheduled = "scheduled"
    items_selected = "items_selected"
    packed = "packed"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    delivery_failed = "delivery_failed"
    picked_up = "picked_up"
    cancelled = "cancelled"


class DeliveryItemStatus(StrEnum):
    pending = "pending"
    selected = "selected"
    packed = "packed"
    delivered = "delivered"
    returned = "returned"
    lost = "lost"
    damaged = "damaged"


class ReadingFormatPreference(StrEnum):
    standard_print = "standard_print"
    large_print = "large_print"
    audiobook = "audiobook"
    ebook = "ebook"
    braille = "braille"


class RouteStatus(StrEnum):
    draft = "draft"
    planned = "planned"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


# ============================================================================
# HomeDelivery Application and Enrollment
# ============================================================================

class HomeDeliveryApplication(Base):
    __tablename__ = "homebound_applications"

    id = Column(Integer, primary_key=True, index=True)
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
    )

    # Application details
    status = Column(
        SQLEnum(HomeDeliveryApplicationStatus, name="homeboundapplicationstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=HomeDeliveryApplicationStatus.pending,
        nullable=False
    )

    # Reason for service (medical, mobility, etc.)
    reason = Column(Text, nullable=False)
    medical_documentation = Column(Boolean, default=False)

    # Delivery address (may differ from main address)
    delivery_address = Column(Text, nullable=False)
    delivery_instructions = Column(Text, nullable=True)

    # Contact information
    contact_phone = Column(String(20), nullable=False)
    alternate_contact_name = Column(String(200), nullable=True)
    alternate_contact_phone = Column(String(20), nullable=True)

    # Preferred delivery options
    preferred_frequency = Column(
        SQLEnum(DeliveryFrequency, name="deliveryfrequency", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=DeliveryFrequency.biweekly,
        nullable=False
    )
    preferred_day = Column(String(20), nullable=True)  # Monday, Tuesday, etc.
    preferred_time_start = Column(String(10), nullable=True)  # "09:00"
    preferred_time_end = Column(String(10), nullable=True)  # "12:00"

    # Application processing
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    denial_reason = Column(Text, nullable=True)

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id], backref="home_delivery_applications")
    reviewer = relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        Index("ix_homebound_applications_status_submitted", "status", "submitted_at"),
    )


class HomeDeliveryEnrollment(Base):
    __tablename__ = "homebound_enrollments"

    id = Column(Integer, primary_key=True)
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
    )
    application_id = Column(
        Integer, ForeignKey("homebound_applications.id", ondelete="SET NULL"),
    )

    # Enrollment status
    status = Column(
        SQLEnum(HomeDeliveryEnrollmentStatus, name="homeboundenrollmentstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=HomeDeliveryEnrollmentStatus.active,
        nullable=False
    )

    # Delivery details (copied from application, can be updated)
    delivery_address = Column(Text, nullable=False)
    delivery_instructions = Column(Text, nullable=True)
    contact_phone = Column(String(20), nullable=False)
    alternate_contact_name = Column(String(200), nullable=True)
    alternate_contact_phone = Column(String(20), nullable=True)

    # Delivery schedule
    delivery_frequency = Column(
        SQLEnum(DeliveryFrequency, name="deliveryfrequency", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=DeliveryFrequency.biweekly,
        nullable=False
    )
    preferred_day = Column(String(20), nullable=True)
    preferred_time_start = Column(String(10), nullable=True)
    preferred_time_end = Column(String(10), nullable=True)
    next_scheduled_delivery = Column(Date, nullable=True)

    # Assigned volunteer (if any)
    assigned_volunteer_id = Column(
        Integer, ForeignKey("delivery_volunteers.id", ondelete="SET NULL"),
    )

    # Enrollment metadata
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    enrolled_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
    )
    paused_at = Column(DateTime(timezone=True), nullable=True)
    pause_reason = Column(Text, nullable=True)
    pause_until = Column(Date, nullable=True)
    terminated_at = Column(DateTime(timezone=True), nullable=True)
    termination_reason = Column(Text, nullable=True)

    # Statistics
    total_deliveries = Column(Integer, default=0, nullable=False)
    last_delivery_date = Column(Date, nullable=True)

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id], backref="home_delivery_enrollment")
    application = relationship("HomeDeliveryApplication", backref="enrollment")
    enrolled_by = relationship("User", foreign_keys=[enrolled_by_id])
    assigned_volunteer = relationship("DeliveryVolunteer", backref="assigned_patrons")
    reading_preferences = relationship(
        "ReadingPreferenceProfile",
        back_populates="enrollment",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_homebound_enrollments_status_next", "status", "next_scheduled_delivery"),
    )


# ============================================================================
# Reading Preferences
# ============================================================================

class ReadingPreferenceProfile(Base):
    __tablename__ = "reading_preference_profiles"

    id = Column(Integer, primary_key=True)
    enrollment_id = Column(
        Integer, ForeignKey("homebound_enrollments.id", ondelete="CASCADE"),
    )

    # Format preferences (ordered by preference)
    format_preferences = Column(
        ARRAY(String),
        default=["standard_print"],
        nullable=False
    )

    # Genre preferences (list of genre names)
    preferred_genres = Column(ARRAY(String), default=[], nullable=False)
    excluded_genres = Column(ARRAY(String), default=[], nullable=False)

    # Author preferences
    favorite_authors = Column(ARRAY(String), default=[], nullable=False)
    excluded_authors = Column(ARRAY(String), default=[], nullable=False)

    # Content preferences
    fiction_preference = Column(Float, default=0.5)  # 0 = nonfiction only, 1 = fiction only
    content_rating = Column(String(20), default="general")  # general, mature, any
    language_preference = Column(String(50), default="English")

    # Specific interests/topics
    interests = Column(ARRAY(String), default=[], nullable=False)

    # Reading level/accessibility
    prefers_large_print = Column(Boolean, default=False)
    prefers_audiobooks = Column(Boolean, default=False)
    prefers_short_books = Column(Boolean, default=False)
    max_pages_preference = Column(Integer, nullable=True)  # NULL = no limit

    # Additional notes from patron or staff
    notes = Column(Text, nullable=True)

    # Series tracking
    current_series = Column(JSONB, default=[])  # [{series_name, last_read_book, next_book}], server_default=func.now())

    # Relationships
    enrollment = relationship("HomeDeliveryEnrollment", back_populates="reading_preferences")


# ============================================================================
# Delivery Volunteers
# ============================================================================

class DeliveryVolunteer(Base):
    __tablename__ = "delivery_volunteers"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
    )

    # Volunteer status
    status = Column(
        SQLEnum(DeliveryVolunteerStatus, name="volunteerstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=DeliveryVolunteerStatus.pending_approval,
        nullable=False
    )

    # Contact information (may differ from user profile)
    phone = Column(String(20), nullable=False)
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)

    # Vehicle information
    has_vehicle = Column(Boolean, default=True)
    vehicle_type = Column(String(100), nullable=True)
    can_transport_large_items = Column(Boolean, default=True)

    # Background check
    background_check_completed = Column(Boolean, default=False)
    background_check_date = Column(Date, nullable=True)
    background_check_expiry = Column(Date, nullable=True)

    # Training
    training_completed = Column(Boolean, default=False)
    training_date = Column(Date, nullable=True)

    # Availability
    available_days = Column(ARRAY(String), default=[])  # ["Monday", "Wednesday", "Friday"]
    available_time_start = Column(String(10), nullable=True)
    available_time_end = Column(String(10), nullable=True)
    max_deliveries_per_day = Column(Integer, default=5)
    max_deliveries_per_week = Column(Integer, default=15)

    # Geographic preferences
    preferred_areas = Column(ARRAY(String), default=[])  # ZIP codes or area names
    max_driving_distance = Column(Integer, nullable=True)  # miles

    # Statistics
    total_deliveries = Column(Integer, default=0, nullable=False)
    total_volunteer_hours = Column(Float, default=0, nullable=False)

    # Recognition
    recognition_level = Column(String(50), default="bronze")  # bronze, silver, gold, platinum
    achievements = Column(JSONB, default=[])  # List of achievements earned

    # Dates
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
    )
    last_active_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="delivery_volunteer_profile")
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        Index("ix_delivery_volunteers_status_active", "status", "last_active_at"),
    )


class VolunteerSchedule(Base):
    __tablename__ = "volunteer_schedules"

    id = Column(Integer, primary_key=True)
    volunteer_id = Column(
        Integer, ForeignKey("delivery_volunteers.id", ondelete="CASCADE"),
    )

    # Specific date availability
    date = Column(Date, nullable=False)
    is_available = Column(Boolean, default=True)
    time_start = Column(String(10), nullable=True)
    time_end = Column(String(10), nullable=True)

    # Notes (e.g., "only morning" or "leaving early")
    notes = Column(Text, nullable=True)

    # Relationships
    volunteer = relationship("DeliveryVolunteer", backref="schedules")

    __table_args__ = (
        UniqueConstraint("volunteer_id", "date", name="uq_volunteer_schedule_date"),
        Index("ix_volunteer_schedules_date", "date"),
    )


class VolunteerHourLog(Base):
    __tablename__ = "volunteer_hour_logs"

    id = Column(Integer, primary_key=True)
    volunteer_id = Column(
        Integer, ForeignKey("delivery_volunteers.id", ondelete="CASCADE"),
    )

    # Date and hours
    date = Column(Date, nullable=False)
    hours = Column(Float, nullable=False)

    # Activity type
    activity_type = Column(String(50), nullable=False)  # delivery, training, meeting, other

    # Related delivery (if applicable)
    delivery_route_id = Column(
        Integer, ForeignKey("delivery_routes.id", ondelete="SET NULL"),
    )

    # Notes/description
    notes = Column(Text, nullable=True)

    # Verification
    verified = Column(Boolean, default=False)
    verified_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
    )
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    volunteer = relationship("DeliveryVolunteer", backref="hour_logs")
    delivery_route = relationship("DeliveryRoute")
    verified_by = relationship("User")

    __table_args__ = (
        Index("ix_volunteer_hour_logs_volunteer_date", "volunteer_id", "date"),
    )


# ============================================================================
# Delivery Routes
# ============================================================================

class DeliveryRoute(Base):
    __tablename__ = "delivery_routes"

    id = Column(Integer, primary_key=True, index=True)

    # Route identification
    name = Column(String(100), nullable=False)
    date = Column(Date, nullable=False)

    # Route status
    status = Column(
        SQLEnum(RouteStatus, name="routestatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=RouteStatus.draft,
        nullable=False
    )

    # Assigned volunteer
    volunteer_id = Column(
        Integer, ForeignKey("delivery_volunteers.id", ondelete="SET NULL"),
    )

    # Route planning
    estimated_duration_minutes = Column(Integer, nullable=True)
    estimated_distance_miles = Column(Float, nullable=True)

    # Route optimization data
    optimized_order = Column(JSONB, default=[])  # List of delivery IDs in optimal order
    route_geometry = Column(JSONB, nullable=True)  # GeoJSON or waypoints

    # Time windows
    planned_start_time = Column(String(10), nullable=True)
    planned_end_time = Column(String(10), nullable=True)
    actual_start_time = Column(DateTime(timezone=True), nullable=True)
    actual_end_time = Column(DateTime(timezone=True), nullable=True)

    # Statistics
    total_stops = Column(Integer, default=0)
    completed_stops = Column(Integer, default=0)
    total_items = Column(Integer, default=0)

    # Staff who created/planned the route
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
    )

    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    volunteer = relationship("DeliveryVolunteer", backref="routes")
    created_by = relationship("User")
    deliveries = relationship("Delivery", back_populates="route", order_by="Delivery.route_order")

    __table_args__ = (
        Index("ix_delivery_routes_date_status", "date", "status"),
    )


# ============================================================================
# Deliveries and Items
# ============================================================================

class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True)

    # Patron and enrollment
    enrollment_id = Column(
        Integer, ForeignKey("homebound_enrollments.id", ondelete="CASCADE"),
    )

    # Route assignment
    route_id = Column(
        Integer, ForeignKey("delivery_routes.id", ondelete="SET NULL"),
    )
    route_order = Column(Integer, nullable=True)  # Order within the route

    # Delivery status
    status = Column(
        SQLEnum(DeliveryStatus, name="deliverystatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=DeliveryStatus.scheduled,
        nullable=False
    )

    # Scheduling
    scheduled_date = Column(Date, nullable=False)
    scheduled_time_start = Column(String(10), nullable=True)
    scheduled_time_end = Column(String(10), nullable=True)

    # Delivery address (snapshot at time of delivery)
    delivery_address = Column(Text, nullable=False)
    delivery_instructions = Column(Text, nullable=True)

    # Actual delivery times
    packed_at = Column(DateTime(timezone=True), nullable=True)
    packed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
    )
    out_for_delivery_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    delivery_signature = Column(Text, nullable=True)  # Base64 signature image or text
    delivery_photo = Column(Text, nullable=True)  # Photo of delivered items

    # Failed delivery
    delivery_failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    reschedule_date = Column(Date, nullable=True)

    # Pickup of previously delivered items
    pickup_requested = Column(Boolean, default=False)
    picked_up_at = Column(DateTime(timezone=True), nullable=True)

    # Item counts
    items_count = Column(Integer, default=0)
    items_delivered = Column(Integer, default=0)
    items_picked_up = Column(Integer, default=0)

    # Notes
    staff_notes = Column(Text, nullable=True)
    patron_notes = Column(Text, nullable=True)  # Patron requests/comments
    volunteer_notes = Column(Text, nullable=True)  # Notes from volunteer

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    enrollment = relationship("HomeDeliveryEnrollment", backref="deliveries")
    route = relationship("DeliveryRoute", back_populates="deliveries")
    packed_by = relationship("User", foreign_keys=[packed_by_id])
    items = relationship("DeliveryItem", back_populates="delivery", cascade="all, delete-orphan")
    feedback = relationship(
        "DeliveryFeedback",
        back_populates="delivery",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_deliveries_status_scheduled", "status", "scheduled_date"),
        Index("ix_deliveries_enrollment_status", "enrollment_id", "status"),
    )


class DeliveryItem(Base):
    __tablename__ = "delivery_items"

    id = Column(Integer, primary_key=True)
    delivery_id = Column(
        Integer, ForeignKey("deliveries.id", ondelete="CASCADE"),
    )

    # Item reference
    item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"),
    )
    item_copy_id = Column(
        Integer, ForeignKey("item_copies.id", ondelete="SET NULL"),
    )

    # Item details snapshot (in case item is deleted)
    item_title = Column(String(500), nullable=False)
    item_author = Column(String(500), nullable=True)
    item_format = Column(String(50), nullable=True)  # book, large_print, audiobook, etc.
    item_barcode = Column(String(100), nullable=True)

    # Item status within delivery
    status = Column(
        SQLEnum(DeliveryItemStatus, name="deliveryitemstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=DeliveryItemStatus.pending,
        nullable=False
    )

    # Checkout integration
    checkout_id = Column(
        Integer, ForeignKey("checkouts.id", ondelete="SET NULL"),
    )
    checked_out_at = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(Date, nullable=True)

    # Return tracking
    returned_at = Column(DateTime(timezone=True), nullable=True)
    return_condition = Column(String(50), nullable=True)  # good, damaged, lost

    # Selection metadata
    selected_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
    )
    selection_reason = Column(Text, nullable=True)  # Why this item was selected
    patron_requested = Column(Boolean, default=False)  # Patron specifically requested this item, server_default=func.now())

    # Relationships
    delivery = relationship("Delivery", back_populates="items")
    item = relationship("CatalogItem")
    item_copy = relationship("ItemCopy")
    checkout = relationship("Checkout")
    selected_by = relationship("User")

    __table_args__ = (
        Index("ix_delivery_items_delivery_status", "delivery_id", "status"),
    )


# ============================================================================
# Patron Feedback
# ============================================================================

class DeliveryFeedback(Base):
    __tablename__ = "delivery_feedback"

    id = Column(Integer, primary_key=True)
    delivery_id = Column(
        Integer, ForeignKey("deliveries.id", ondelete="CASCADE"),
    )

    # Overall rating
    overall_rating = Column(Integer, nullable=False)  # 1-5 stars

    # Specific ratings
    item_satisfaction = Column(Integer, nullable=True)  # 1-5
    volunteer_rating = Column(Integer, nullable=True)  # 1-5
    timeliness_rating = Column(Integer, nullable=True)  # 1-5

    # Written feedback
    comments = Column(Text, nullable=True)
    item_feedback = Column(Text, nullable=True)  # Feedback on specific items

    # Suggestions
    suggestions_for_next_delivery = Column(Text, nullable=True)

    # Would recommend
    would_recommend = Column(Boolean, nullable=True)

    # Staff follow-up
    requires_follow_up = Column(Boolean, default=False)
    follow_up_completed = Column(Boolean, default=False)
    follow_up_notes = Column(Text, nullable=True)
    follow_up_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
    )
    follow_up_at = Column(DateTime(timezone=True), nullable=True)

    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    delivery = relationship("Delivery", back_populates="feedback")
    follow_up_by = relationship("User")


# ============================================================================
# Patron Item Requests
# ============================================================================

class HomeDeliveryItemRequest(Base):
    __tablename__ = "homebound_item_requests"

    id = Column(Integer, primary_key=True)
    enrollment_id = Column(
        Integer, ForeignKey("homebound_enrollments.id", ondelete="CASCADE"),
    )

    # Request details
    request_type = Column(String(50), nullable=False)  # specific_item, author, genre, topic
    title = Column(String(500), nullable=True)
    author = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)  # Description of what they want

    # Linked catalog item (if specific item requested)
    item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"),
    )

    # Status
    fulfilled = Column(Boolean, default=False)
    fulfilled_in_delivery_id = Column(
        Integer, ForeignKey("deliveries.id", ondelete="SET NULL"),
    )

    # Notes
    staff_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    enrollment = relationship("HomeDeliveryEnrollment", backref="item_requests")
    item = relationship("CatalogItem")
    fulfilled_in_delivery = relationship("Delivery")

    __table_args__ = (
        Index("ix_homebound_item_requests_enrollment_fulfilled", "enrollment_id", "fulfilled"),
    )


# ============================================================================
# One-Click Delivery Requests (for any patron, not just enrollees)
# ============================================================================

class DeliveryRequestStatus(StrEnum):
    pending = "pending"  # Awaiting staff approval
    approved = "approved"  # Staff approved
    declined = "declined"  # Staff declined
    in_delivery = "in_delivery"  # Item picked up for delivery
    completed = "completed"  # Delivered to patron
    cancelled = "cancelled"  # Patron cancelled request


class DeliveryRequest(Base):
    __tablename__ = "delivery_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    approved_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Status tracking
    status = Column(
        SQLEnum(DeliveryRequestStatus, name="deliveryrequeststatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=DeliveryRequestStatus.pending,
        nullable=False,
        index=True,
    )

    # Delivery options
    frequency = Column(
        SQLEnum(DeliveryFrequency, name="deliveryfrequency", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=DeliveryFrequency.on_demand,
        nullable=False,
    )

    # Patron preferences
    delivery_address = Column(String(500), nullable=True)
    delivery_notes = Column(Text, nullable=True)
    preferred_window = Column(
        String(100),
        nullable=True,
    )

    # Workflow timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    declined_at = Column(DateTime(timezone=True), nullable=True)
    decline_reason = Column(Text, nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Scheduling
    requested_by_date = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_delivery_date = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], lazy="selectin")
    item = relationship("CatalogItem", foreign_keys=[item_id], lazy="selectin")
    approved_by = relationship("User", foreign_keys=[approved_by_id], lazy="selectin")

    # Performance optimization indexes
    __table_args__ = (
        Index("ix_delivery_requests_user_status", "user_id", "status"),
        Index("ix_delivery_requests_status_approved_at", "status", "approved_at"),
        Index("ix_delivery_requests_next_delivery_date", "next_delivery_date"),
    )
