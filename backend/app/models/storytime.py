# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, Index, Integer, String, Text,
    UniqueConstraint, text, ForeignKey
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


# ============================================================================
# Enums
# ============================================================================

class AgeGroup(StrEnum):
    babies = "babies"  # 0-12 months
    toddlers = "toddlers"  # 12-24 months
    twos = "twos"  # 2-3 years
    threes = "threes"  # 3-4 years
    fours = "fours"  # 4-5 years
    fives_and_up = "fives_and_up"  # 5+ years
    preschool = "preschool"  # General preschool
    school_age = "school_age"  # K-3rd grade
    families = "families"  # Mixed ages


class StorytimeSeriesType(StrEnum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    drop_in = "drop_in"
    special_event = "special_event"
    workshop = "workshop"


class StorytimeSessionStatus(StrEnum):
    scheduled = "scheduled"
    cancelled_weather = "cancelled_weather"
    cancelled_other = "cancelled_other"
    completed = "completed"
    in_progress = "in_progress"


class AttendeeType(StrEnum):
    child = "child"
    caregiver = "caregiver"


class CommunicationType(StrEnum):
    email = "email"
    sms = "sms"
    phone = "phone"
    in_app = "in_app"
    social_media = "social_media"


class CommunicationTemplate(StrEnum):
    session_reminder = "session_reminder"
    weather_cancellation = "weather_cancellation"
    theme_preview = "theme_preview"
    activity_follow_up = "activity_follow_up"
    feedback_request = "feedback_request"
    special_announcement = "special_announcement"


class RepeatAttendeeStatus(StrEnum):
    regular = "regular"  # 5+ sessions
    frequent = "frequent"  # 10+ sessions
    devoted = "devoted"  # 25+ sessions
    super_fan = "super_fan"  # 50+ sessions


class SubLeaderStatus(StrEnum):
    available = "available"
    on_assignment = "on_assignment"
    unavailable = "unavailable"
    inactive = "inactive"


class CraftComplexity(StrEnum):
    simple = "simple"
    moderate = "moderate"
    complex = "complex"


class StorytimeResourceType(StrEnum):
    book = "book"
    song = "song"
    rhyme = "rhyme"
    craft_activity = "craft_activity"
    game = "game"
    prop = "prop"


# ============================================================================
# Core Storytime Series
# ============================================================================

class StorytimeSeries(Base):
    __tablename__ = "storytime_series"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    series_type = Column(
        SQLEnum(StorytimeSeriesType, name="storytimeseriestype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=StorytimeSeriesType.weekly,
        nullable=False
    )

    # Age targeting
    primary_age_group = Column(
        SQLEnum(AgeGroup, name="agegroup", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    secondary_age_groups = Column(ARRAY(String), default=[], nullable=False)

    # Location and timing
    location = Column(String(255), nullable=False)
    day_of_week = Column(String(20), nullable=True)  # e.g., "Monday", "Wednesday"
    start_time = Column(String(5), nullable=True)  # e.g., "10:00"
    duration_minutes = Column(Integer, default=30, nullable=False)

    # Capacity
    max_capacity = Column(Integer, nullable=True)

    # Leaders
    primary_leader_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    secondary_leader_ids = Column(ARRAY(Integer), default=[], nullable=False)

    # Schedule
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    # Metadata
    is_registration_required = Column(Boolean, default=False)
    is_virtual = Column(Boolean, default=False)
    virtual_link = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)

    # Relationships
    primary_leader = relationship("User", foreign_keys=[primary_leader_id], backref="led_storytime_series")
    sessions = relationship("StorytimeSession", backref="series", cascade="all, delete-orphan")
    themes = relationship("StorytimeTheme", backref="series", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_storytime_series_active", "is_active"),
        Index("ix_storytime_series_age_group", "primary_age_group"),
    )


# ============================================================================
# Storytime Sessions
# ============================================================================

class StorytimeSession(Base):
    __tablename__ = "storytime_sessions"

    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(
        Integer, ForeignKey("storytime_series.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Session details
    session_date = Column(Date, nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(
        SQLEnum(StorytimeSessionStatus, name="storytimesessionstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=StorytimeSessionStatus.scheduled,
        nullable=False, index=True
    )

    # Theme for this session
    theme_id = Column(
        Integer, ForeignKey("storytime_themes.id", ondelete="SET NULL"),
        nullable=True
    )

    # Books for this session
    book_ids = Column(ARRAY(Integer), default=[], nullable=False)

    # Leader assignment
    assigned_leader_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    sub_leader_id = Column(
        Integer, ForeignKey("storytime_sub_leaders.id", ondelete="SET NULL"),
        nullable=True
    )

    # Weather and cancellation
    weather_alert = Column(String(500), nullable=True)
    is_cancelled = Column(Boolean, default=False, index=True)
    cancellation_reason = Column(String(255), nullable=True)

    # Attendance
    expected_attendance = Column(Integer, default=0)
    actual_attendance = Column(Integer, default=0, nullable=False)

    # Communications sent
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_notification_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    theme = relationship("StorytimeTheme", backref="sessions")
    assigned_leader = relationship("User", foreign_keys=[assigned_leader_id])
    sub_leader = relationship("StorytimeSubLeader", backref="assigned_sessions")
    attendances = relationship("StorytimeAttendance", backref="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_storytime_sessions_date", "session_date"),
        Index("ix_storytime_sessions_status", "status"),
    )


# ============================================================================
# Attendance Tracking (No Registration)
# ============================================================================

class StorytimeAttendance(Base):
    __tablename__ = "storytime_attendance"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("storytime_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # For walk-ins, we may not have user_id
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True, index=True
    )

    # Walk-in info (captured when user not in system)
    child_name = Column(String(255), nullable=True)
    caregiver_name = Column(String(255), nullable=True)
    age_group = Column(
        SQLEnum(AgeGroup, name="agegroup", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )

    # Attendance type
    attendee_type = Column(
        SQLEnum(AttendeeType, name="attendeetype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # First time?
    is_first_time = Column(Boolean, default=False)

    # Email for follow-up
    caregiver_email = Column(String(255), nullable=True)
    caregiver_phone = Column(String(20), nullable=True)

    # Feedback
    feedback = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 stars

    checked_in_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="storytime_attendances")

    __table_args__ = (
        Index("ix_storytime_attendance_session", "session_id"),
        Index("ix_storytime_attendance_user", "user_id"),
    )


# ============================================================================
# Repeat Attendee Recognition
# ============================================================================

class RepeatAttendee(Base):
    __tablename__ = "repeat_attendees"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("storytime_sessions.id", ondelete="CASCADE"),
        nullable=False
    )

    # Anonymous tracking by caregiver name + email
    caregiver_identifier = Column(String(255), nullable=False, unique=True, index=True)
    caregiver_name = Column(String(255), nullable=True)
    caregiver_email = Column(String(255), nullable=True)

    # Statistics
    total_sessions_attended = Column(Integer, default=1, nullable=False)
    last_attended_date = Column(Date, nullable=False)
    first_attended_date = Column(Date, nullable=False)

    # Recognition
    recognition_status = Column(
        SQLEnum(RepeatAttendeeStatus, name="repeatattendeestatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=RepeatAttendeeStatus.regular,
        nullable=False, index=True
    )
    recognition_badges = Column(ARRAY(String), default=[], nullable=False)
    recognition_announcement_sent = Column(Boolean, default=False)

    # Preferences
    prefers_contact = Column(Boolean, default=False)
    theme_preferences = Column(ARRAY(String), default=[], nullable=False)

    __table_args__ = (
        Index("ix_repeat_attendees_status", "recognition_status"),
    )


# ============================================================================
# Theme and Book Management
# ============================================================================

class StorytimeTheme(Base):
    __tablename__ = "storytime_themes"

    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(
        Integer, ForeignKey("storytime_series.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Theme info
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    theme_color = Column(String(7), nullable=True)  # Hex color

    # Content
    learning_objectives = Column(Text, nullable=True)
    discussion_points = Column(ARRAY(String), default=[], nullable=False)

    # Associated resources
    song_ids = Column(ARRAY(Integer), default=[], nullable=False)
    rhyme_ids = Column(ARRAY(Integer), default=[], nullable=False)
    craft_ids = Column(ARRAY(Integer), default=[], nullable=False)

    # Image/media
    image_url = Column(String(500), nullable=True)

    # Usage tracking
    times_used = Column(Integer, default=0, nullable=False)
    last_used_date = Column(Date, nullable=True)

    __table_args__ = (
        Index("ix_storytime_themes_series", "series_id"),
    )


class StorytimeBook(Base):
    __tablename__ = "storytime_books"

    id = Column(Integer, primary_key=True, index=True)

    # Book info
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    illustrator = Column(String(255), nullable=True)
    isbn = Column(String(20), nullable=True, unique=True)

    # Content details
    description = Column(Text, nullable=True)
    age_groups = Column(ARRAY(String), default=[], nullable=False)
    word_count = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)

    # Library info
    library_call_number = Column(String(50), nullable=True)
    is_in_collection = Column(Boolean, default=True)

    # Session usage
    times_read = Column(Integer, default=0, nullable=False)
    last_read_date = Column(Date, nullable=True)

    # Rating and feedback
    average_rating = Column(Float, nullable=True)
    librarian_notes = Column(Text, nullable=True)

    image_url = Column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_storytime_books_title", "title"),
        Index("ix_storytime_books_author", "author"),
    )


# ============================================================================
# Songs and Rhymes Library
# ============================================================================

class StorytimeSong(Base):
    __tablename__ = "storytime_songs"

    id = Column(Integer, primary_key=True, index=True)

    # Song info
    title = Column(String(255), nullable=False)
    composer = Column(String(255), nullable=True)
    lyricist = Column(String(255), nullable=True)

    # Content
    lyrics = Column(Text, nullable=True)
    melody_description = Column(Text, nullable=True)

    # Classification
    age_groups = Column(ARRAY(String), default=[], nullable=False)
    themes = Column(ARRAY(String), default=[], nullable=False)

    # Media
    audio_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)

    # Usage
    times_used = Column(Integer, default=0, nullable=False)
    last_used_date = Column(Date, nullable=True)

    # Notes
    librarian_notes = Column(Text, nullable=True)
    movement_suggestions = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_storytime_songs_title", "title"),
    )


class StorytimeRhyme(Base):
    __tablename__ = "storytime_rhymes"

    id = Column(Integer, primary_key=True, index=True)

    # Rhyme info
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=True)

    # Content
    text = Column(Text, nullable=False)
    hand_motions_description = Column(Text, nullable=True)

    # Classification
    age_groups = Column(ARRAY(String), default=[], nullable=False)
    themes = Column(ARRAY(String), default=[], nullable=False)

    # Complexity
    motor_skill_level = Column(String(50), nullable=True)  # fine, gross, both

    # Media
    video_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)

    # Usage
    times_used = Column(Integer, default=0, nullable=False)
    last_used_date = Column(Date, nullable=True)

    # Notes
    librarian_notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_storytime_rhymes_title", "title"),
    )


# ============================================================================
# Craft Supply Planning
# ============================================================================

class StorytimeCraft(Base):
    __tablename__ = "storytime_crafts"

    id = Column(Integer, primary_key=True, index=True)

    # Craft info
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Content
    age_groups = Column(ARRAY(String), default=[], nullable=False)
    themes = Column(ARRAY(String), default=[], nullable=False)
    complexity = Column(
        SQLEnum(CraftComplexity, name="craftcomplexity", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=CraftComplexity.simple,
        nullable=False
    )

    # Instructions
    step_by_step_instructions = Column(Text, nullable=True)
    estimated_time_minutes = Column(Integer, nullable=True)

    # Supplies
    required_supplies = Column(ARRAY(String), default=[], nullable=False)
    optional_supplies = Column(ARRAY(String), default=[], nullable=False)
    supplies_cost_estimate = Column(Float, nullable=True)

    # Media
    image_url = Column(String(500), nullable=True)
    tutorial_video_url = Column(String(500), nullable=True)

    # Usage
    times_used = Column(Integer, default=0, nullable=False)
    last_used_date = Column(Date, nullable=True)

    # Notes
    librarian_notes = Column(Text, nullable=True)
    success_tips = Column(Text, nullable=True)
    cleanup_notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_storytime_crafts_title", "title"),
    )


class CraftSupplyInventory(Base):
    __tablename__ = "craft_supply_inventory"

    id = Column(Integer, primary_key=True, index=True)

    # Supply info
    supply_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)  # e.g., "Paper", "Markers", "Glue"

    # Inventory
    quantity_on_hand = Column(Integer, default=0, nullable=False)
    reorder_level = Column(Integer, default=10, nullable=False)
    last_restocked_date = Column(Date, nullable=True)

    # Sourcing
    supplier_name = Column(String(255), nullable=True)
    cost_per_unit = Column(Float, nullable=True)
    storage_location = Column(String(255), nullable=True)

    # Usage tracking
    times_used = Column(Integer, default=0, nullable=False)
    average_usage_per_session = Column(Float, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_craft_supplies_reorder", "quantity_on_hand", "reorder_level"),
    )


# ============================================================================
# Caregiver Communication
# ============================================================================

class CaregiverContact(Base):
    __tablename__ = "caregiver_contacts"

    id = Column(Integer, primary_key=True, index=True)

    # Contact info
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=True)

    # Child info
    child_name = Column(String(255), nullable=True)
    child_age_group = Column(
        SQLEnum(AgeGroup, name="agegroup", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )

    # Communication preferences
    preferred_contact_method = Column(
        SQLEnum(CommunicationType, name="communicationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=CommunicationType.email,
        nullable=False
    )
    opt_in_reminders = Column(Boolean, default=True)
    opt_in_theme_previews = Column(Boolean, default=True)
    opt_in_feedback = Column(Boolean, default=True)
    opt_in_announcements = Column(Boolean, default=True)

    # Interests
    interested_themes = Column(ARRAY(String), default=[], nullable=False)
    interested_age_groups = Column(ARRAY(String), default=[], nullable=False)

    # Tracking
    sessions_attended = Column(Integer, default=0, nullable=False)
    last_contact_date = Column(Date, nullable=True)

    __table_args__ = (
        # Note: email column already has unique=True, index=True
        # which creates an implicit unique index
    )


class CaregiverCommunication(Base):
    __tablename__ = "caregiver_communications"

    id = Column(Integer, primary_key=True, index=True)

    # Communication details
    caregiver_contact_id = Column(
        Integer, ForeignKey("caregiver_contacts.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    session_id = Column(
        Integer, ForeignKey("storytime_sessions.id", ondelete="SET NULL"),
        nullable=True
    )

    # Content
    communication_type = Column(
        SQLEnum(CommunicationTemplate, name="communicationtemplate", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    contact_method = Column(
        SQLEnum(CommunicationType, name="communicationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    subject = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)

    # Status
    is_sent = Column(Boolean, default=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)

    # Response
    responded = Column(Boolean, default=False)
    response_received_at = Column(DateTime(timezone=True), nullable=True)
    response_text = Column(Text, nullable=True)

    # Relationships
    caregiver_contact = relationship("CaregiverContact", backref="communications")
    session = relationship("StorytimeSession")

    __table_args__ = (
        Index("ix_caregiver_communications_type", "communication_type"),
        Index("ix_caregiver_communications_sent", "is_sent"),
    )


# ============================================================================
# Sub Storytime Leader Scheduling
# ============================================================================

class StorytimeSubLeader(Base):
    __tablename__ = "storytime_sub_leaders"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=True)

    # Qualifications
    experience_level = Column(String(50), nullable=True)  # beginner, intermediate, advanced
    certifications = Column(ARRAY(String), default=[], nullable=False)
    background_check_date = Column(Date, nullable=True)

    # Availability
    status = Column(
        SQLEnum(SubLeaderStatus, name="subleaderstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=SubLeaderStatus.available,
        nullable=False, index=True
    )
    available_days = Column(ARRAY(String), default=[], nullable=False)
    available_times = Column(ARRAY(String), default=[], nullable=False)
    max_assignments_per_month = Column(Integer, nullable=True)

    # Age group specialties
    specializes_in = Column(ARRAY(String), default=[], nullable=False)

    # Tracking
    total_sessions_led = Column(Integer, default=0, nullable=False)
    last_assigned_date = Column(Date, nullable=True)
    assignments_this_month = Column(Integer, default=0, nullable=False)

    # Performance
    average_rating = Column(Float, nullable=True)
    feedback_notes = Column(Text, nullable=True)

    # Contact preferences
    prefers_contact_method = Column(
        SQLEnum(CommunicationType, name="communicationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=CommunicationType.email,
        nullable=False
    )

    __table_args__ = (
        Index("ix_sub_leaders_status", "status"),
    )


class SubLeaderAssignment(Base):
    __tablename__ = "sub_leader_assignments"

    id = Column(Integer, primary_key=True, index=True)

    # Assignment details
    session_id = Column(
        Integer, ForeignKey("storytime_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    sub_leader_id = Column(
        Integer, ForeignKey("storytime_sub_leaders.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Status
    confirmed = Column(Boolean, default=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    # Performance
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 stars
    feedback = Column(Text, nullable=True)

    # Notes
    special_instructions = Column(Text, nullable=True)

    # Relationships
    session = relationship("StorytimeSession")
    sub_leader = relationship("StorytimeSubLeader")

    __table_args__ = (
        Index("ix_sub_assignments_confirmed", "confirmed"),
    )


# ============================================================================
# Annual Planning Calendar
# ============================================================================

class StorytimeAnnualPlan(Base):
    __tablename__ = "storytime_annual_plans"

    id = Column(Integer, primary_key=True, index=True)

    # Plan year
    year = Column(Integer, nullable=False, unique=True, index=True)

    # Overall goals and themes
    annual_theme = Column(String(255), nullable=True)
    goals = Column(ARRAY(String), default=[], nullable=False)
    special_events = Column(ARRAY(String), default=[], nullable=False)

    # Planning details
    total_sessions_planned = Column(Integer, default=0)
    expected_total_attendance = Column(Integer, default=0)

    # Budget
    estimated_budget = Column(Float, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)


class StorytimeMonthlyPlan(Base):
    __tablename__ = "storytime_monthly_plans"

    id = Column(Integer, primary_key=True, index=True)

    # Year and month
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)

    # Monthly focus
    monthly_theme = Column(String(255), nullable=True)
    learning_focus = Column(Text, nullable=True)

    # Planning details
    sessions_planned = Column(Integer, default=0)
    expected_attendance = Column(Integer, default=0)

    # Upcoming holidays/events
    special_dates = Column(ARRAY(String), default=[], nullable=False)

    # Craft supply needs
    craft_supply_needs = Column(ARRAY(String), default=[], nullable=False)

    # Notes
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_monthly_plans_year_month", "year", "month"),
    )


# ============================================================================
# Weather Cancellation
# ============================================================================

class WeatherAlert(Base):
    __tablename__ = "weather_alerts"

    id = Column(Integer, primary_key=True, index=True)

    # Alert details
    alert_type = Column(String(100), nullable=False)  # "winter_weather", "heat_advisory", etc.
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=True)  # "minor", "moderate", "severe"

    # Geography
    affected_locations = Column(ARRAY(String), default=[], nullable=False)

    # Time
    effective_from = Column(DateTime(timezone=True), nullable=False)
    effective_until = Column(DateTime(timezone=True), nullable=True)

    # Action
    should_cancel_programs = Column(Boolean, default=False)
    recommended_action = Column(Text, nullable=True)

    # Tracking
    sessions_cancelled = Column(Integer, default=0)

    __table_args__ = (
        Index("ix_weather_alerts_effective", "effective_from", "effective_until"),
    )
