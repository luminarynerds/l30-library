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

class VolunteerApplicationStatus(StrEnum):
    draft = "draft"
    submitted = "submitted"
    under_review = "under_review"
    approved = "approved"
    denied = "denied"
    withdrawn = "withdrawn"


class VolunteerRoleCategory(StrEnum):
    delivery = "delivery"
    programming = "programming"
    tech_support = "tech_support"
    shelving = "shelving"
    reader_advisory = "reader_advisory"
    administrative = "administrative"
    patron_services = "patron_services"
    community_outreach = "community_outreach"
    cataloging = "cataloging"
    makerspace = "makerspace"
    other = "other"


class VolunteerStatus(StrEnum):
    pending_background = "pending_background"
    pending_training = "pending_training"
    active = "active"
    inactive = "inactive"
    on_leave = "on_leave"
    suspended = "suspended"
    terminated = "terminated"
    pending_approval = "pending_approval"


class BackgroundCheckStatus(StrEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    clear = "clear"
    issues = "issues"
    expired = "expired"
    denied = "denied"


class TrainingStatus(StrEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    overdue = "overdue"
    expired = "expired"


class AvailabilityType(StrEnum):
    specific_days = "specific_days"
    flexible = "flexible"
    weekend_only = "weekend_only"
    weekday_only = "weekday_only"
    on_call = "on_call"


class ShiftSignupStatus(StrEnum):
    confirmed = "confirmed"
    pending = "pending"
    cancelled = "cancelled"
    completed = "completed"
    no_show = "no_show"


class HourLogStatus(StrEnum):
    pending = "pending"
    submitted = "submitted"
    verified = "verified"
    rejected = "rejected"


class MilestoneType(StrEnum):
    hours_25 = "hours_25"
    hours_50 = "hours_50"
    hours_100 = "hours_100"
    hours_250 = "hours_250"
    hours_500 = "hours_500"
    hours_1000 = "hours_1000"
    shifts_10 = "shifts_10"
    shifts_50 = "shifts_50"
    years_1 = "years_1"
    years_5 = "years_5"


class VolunteerCommunicationType(StrEnum):
    email = "email"
    sms = "sms"
    phone = "phone"
    in_app = "in_app"
    mail = "mail"


class AppreciationType(StrEnum):
    thank_you_email = "thank_you_email"
    certificate = "certificate"
    badge = "badge"
    award = "award"
    public_recognition = "public_recognition"
    gift = "gift"
    event_invitation = "event_invitation"


# ============================================================================
# Core Volunteer Profile
# ============================================================================

class Volunteer(Base):
    __tablename__ = "volunteers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )

    # Volunteer status
    status = Column(
        SQLEnum(VolunteerStatus, name="volunteerstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=VolunteerStatus.pending_background,
        nullable=False
    )

    # Volunteer roles and categories
    primary_role_category = Column(
        SQLEnum(VolunteerRoleCategory, name="volunteerrolecategory", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    secondary_role_categories = Column(ARRAY(String), default=[], nullable=False)

    # Contact information
    phone = Column(String(20), nullable=False)
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relationship = Column(String(100), nullable=True)

    # Availability info
    preferred_frequency = Column(String(50), nullable=True)  # e.g., "weekly", "biweekly"
    max_hours_per_week = Column(Integer, default=10, nullable=False)
    start_date = Column(Date, nullable=True)
    expected_end_date = Column(Date, nullable=True)

    # Statistics
    total_hours = Column(Float, default=0, nullable=False)
    total_shifts = Column(Integer, default=0, nullable=False)
    last_active_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    driving_required = Column(Boolean, default=False)
    has_vehicle = Column(Boolean, default=False)
    background_check_required = Column(Boolean, default=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="general_volunteer_profile")
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        Index("ix_volunteers_status", "status"),
        Index("ix_volunteers_primary_role", "primary_role_category"),
    )


# ============================================================================
# Volunteer Application and Onboarding
# ============================================================================

class VolunteerApplication(Base):
    __tablename__ = "volunteer_applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Application status
    status = Column(
        SQLEnum(VolunteerApplicationStatus, name="volunteerapplicationstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=VolunteerApplicationStatus.draft,
        nullable=False
    )

    # Role preferences
    preferred_roles = Column(ARRAY(String), default=[], nullable=False)
    why_volunteer = Column(Text, nullable=False)
    previous_volunteer_experience = Column(Text, nullable=True)

    # Availability
    preferred_days = Column(ARRAY(String), default=[], nullable=False)
    availability_hours_per_week = Column(Integer, nullable=False)

    # Commitment
    volunteer_start_date = Column(Date, nullable=True)
    expected_duration_months = Column(Integer, nullable=True)

    # Requirements
    can_drive = Column(Boolean, default=False)
    has_vehicle = Column(Boolean, default=False)
    background_check_consent = Column(Boolean, default=False)
    references_provided = Column(Boolean, default=False)

    # Review and approval
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    denial_reason = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="volunteer_applications")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    volunteer_references = relationship(
        "VolunteerReference",
        back_populates="application",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_volunteer_applications_status", "status"),
        Index("ix_volunteer_applications_submitted", "submitted_at"),
    )


class VolunteerReference(Base):
    __tablename__ = "volunteer_references"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(
        Integer, ForeignKey("volunteer_applications.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Reference information
    reference_name = Column(String(200), nullable=False)
    reference_relationship = Column(String(100), nullable=False)
    reference_email = Column(String(255), nullable=False)
    reference_phone = Column(String(20), nullable=True)

    # Status
    invited_at = Column(DateTime(timezone=True), nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    response_content = Column(Text, nullable=True)

    # Relationships
    application = relationship("VolunteerApplication", back_populates="volunteer_references")


# ============================================================================
# Background Check Tracking
# ============================================================================

class BackgroundCheck(Base):
    __tablename__ = "background_checks"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(
        Integer, ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )

    # Check status
    status = Column(
        SQLEnum(BackgroundCheckStatus, name="backgroundcheckstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=BackgroundCheckStatus.not_started,
        nullable=False, index=True
    )

    # Check details
    check_type = Column(String(100), nullable=False)  # e.g., "criminal_record", "sex_offender"
    initiated_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(Date, nullable=True)

    # Provider information
    provider_name = Column(String(255), nullable=True)
    provider_reference_id = Column(String(255), nullable=True)

    # Results
    result_summary = Column(String(50), nullable=True)  # clear, issues, denied
    issues_found = Column(ARRAY(String), default=[], nullable=False)
    issues_description = Column(Text, nullable=True)
    clearance_notes = Column(Text, nullable=True)

    # Approval
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)

    # Relationships
    volunteer = relationship("Volunteer", backref="background_checks")
    approved_by = relationship("User")

    __table_args__ = (
        Index("ix_background_checks_status", "status"),
        Index("ix_background_checks_expires", "expires_at"),
    )


# ============================================================================
# Training Completion Records
# ============================================================================

class TrainingType(Base):
    __tablename__ = "training_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    required_for_roles = Column(ARRAY(String), default=[], nullable=False)
    duration_hours = Column(Float, nullable=False)
    recurrence_months = Column(Integer, nullable=True)  # NULL = one-time training, server_default=func.now())

    # Relationships
    training_records = relationship("TrainingRecord", backref="training_type")


class TrainingRecord(Base):
    __tablename__ = "training_records"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(
        Integer, ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    training_type_id = Column(
        Integer, ForeignKey("training_types.id", ondelete="CASCADE"),
        nullable=False
    )

    # Training status
    status = Column(
        SQLEnum(TrainingStatus, name="trainingstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=TrainingStatus.not_started,
        nullable=False
    )

    # Dates
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(Date, nullable=True)

    # Trainer and notes
    trainer_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    completion_notes = Column(Text, nullable=True)
    score = Column(Float, nullable=True)  # e.g., quiz score

    # Renewal
    renewal_required = Column(Boolean, default=False)
    last_renewal_date = Column(Date, nullable=True)

    # Relationships
    volunteer = relationship("Volunteer", backref="training_records")
    trainer = relationship("User")

    __table_args__ = (
        UniqueConstraint("volunteer_id", "training_type_id", name="uq_volunteer_training"),
        Index("ix_training_records_status", "status"),
        Index("ix_training_records_expires", "expires_at"),
    )


# ============================================================================
# Availability Preferences
# ============================================================================

class AvailabilityPreference(Base):
    __tablename__ = "availability_preferences"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(
        Integer, ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )

    # Availability type
    availability_type = Column(
        SQLEnum(AvailabilityType, name="availabilitytype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=AvailabilityType.specific_days,
        nullable=False
    )

    # Available days and times
    available_days = Column(ARRAY(String), default=[], nullable=False)  # ["Monday", "Wednesday", "Friday"]
    available_time_start = Column(String(10), nullable=True)  # "09:00"
    available_time_end = Column(String(10), nullable=True)    # "17:00"

    # Constraints
    max_hours_per_week = Column(Integer, default=10, nullable=False)
    max_hours_per_session = Column(Integer, nullable=True)
    min_hours_per_session = Column(Float, default=1, nullable=False)

    # Geographic preferences
    preferred_locations = Column(ARRAY(String), default=[], nullable=False)
    willing_to_travel = Column(Boolean, default=False)
    max_travel_distance_miles = Column(Integer, nullable=True)

    # Preferences
    prefers_recurring_shifts = Column(Boolean, default=True)
    prefers_flexible_shifts = Column(Boolean, default=False)

    # Relationships
    volunteer = relationship("Volunteer", backref="availability_preference")


# ============================================================================
# Volunteer Shifts and Sign-up
# ============================================================================

class VolunteerShift(Base):
    __tablename__ = "volunteer_shifts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    role_category = Column(
        SQLEnum(VolunteerRoleCategory, name="volunteerrolecategory", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Scheduling
    shift_date = Column(Date, nullable=False)
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)
    duration_hours = Column(Float, nullable=False)

    # Location
    location = Column(String(255), nullable=True)
    location_address = Column(Text, nullable=True)

    # Capacity
    volunteers_needed = Column(Integer, default=1, nullable=False)
    volunteers_signed_up = Column(Integer, default=0, nullable=False)

    # Requirements
    required_training = Column(ARRAY(String), default=[], nullable=False)
    required_skills = Column(ARRAY(String), default=[], nullable=False)

    # Status
    is_recurring = Column(Boolean, default=False)
    recurring_pattern = Column(String(50), nullable=True)  # e.g., "weekly", "biweekly"

    # Created by staff
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    notes = Column(Text, nullable=True)
    cancelled = Column(Boolean, default=False)

    # Relationships
    created_by = relationship("User")
    signups = relationship("ShiftSignup", back_populates="shift", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_volunteer_shifts_date", "shift_date"),
        Index("ix_volunteer_shifts_role", "role_category"),
    )


class ShiftSignup(Base):
    __tablename__ = "shift_signups"

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(
        Integer, ForeignKey("volunteer_shifts.id", ondelete="CASCADE"),
        nullable=False
    )
    volunteer_id = Column(
        Integer, ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False
    )

    # Signup status
    status = Column(
        SQLEnum(ShiftSignupStatus, name="shiftsignupstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ShiftSignupStatus.pending,
        nullable=False
    )

    # Signup timing
    signed_up_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Completion tracking
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    checked_out_at = Column(DateTime(timezone=True), nullable=True)
    actual_hours = Column(Float, nullable=True)  # Actual hours worked
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Notes
    cancellation_reason = Column(Text, nullable=True)
    staff_notes = Column(Text, nullable=True)

    # Relationships
    shift = relationship("VolunteerShift", back_populates="signups")
    volunteer = relationship("Volunteer", backref="shift_signups")

    __table_args__ = (
        UniqueConstraint("shift_id", "volunteer_id", name="uq_shift_volunteer"),
        Index("ix_shift_signups_volunteer", "volunteer_id"),
        Index("ix_shift_signups_status", "status"),
    )


# ============================================================================
# Skills and Skill Matching
# ============================================================================

class VolunteerSkill(Base):
    __tablename__ = "volunteer_skills"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(
        Integer, ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    skill_name = Column(String(255), nullable=False)
    proficiency_level = Column(String(50), default="intermediate", nullable=False)  # beginner, intermediate, advanced, expert
    years_of_experience = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    verified = Column(Boolean, default=False)

    # Relationships
    volunteer = relationship("Volunteer", backref="skills")

    __table_args__ = (
        UniqueConstraint("volunteer_id", "skill_name", name="uq_volunteer_skill"),
    )


class SkillOpportunity(Base):
    __tablename__ = "skill_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    role_category = Column(
        SQLEnum(VolunteerRoleCategory, name="volunteerrolecategory", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Required skills
    required_skills = Column(ARRAY(String), default=[], nullable=False)
    preferred_skills = Column(ARRAY(String), default=[], nullable=False)
    minimum_proficiency_level = Column(String(50), default="beginner", nullable=False)

    # Availability
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    ideal_commitment_hours = Column(Integer, nullable=True)

    active = Column(Boolean, default=True)

    # Relationships
    skill_matches = relationship("SkillMatch", back_populates="opportunity")


class SkillMatch(Base):
    __tablename__ = "skill_matches"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(
        Integer, ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False
    )
    opportunity_id = Column(
        Integer, ForeignKey("skill_opportunities.id", ondelete="CASCADE"),
        nullable=False
    )

    # Match scoring
    match_score = Column(Float, nullable=False)  # 0-100
    matched_skills = Column(ARRAY(String), default=[], nullable=False)
    missing_skills = Column(ARRAY(String), default=[], nullable=False)

    # Interest
    interested = Column(Boolean, default=False)
    interested_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    volunteer = relationship("Volunteer", backref="skill_matches")
    opportunity = relationship("SkillOpportunity", back_populates="skill_matches")

    __table_args__ = (
        UniqueConstraint("volunteer_id", "opportunity_id", name="uq_skill_match"),
    )


# ============================================================================
# Hour Logging and Verification
# ============================================================================

class GeneralVolunteerHourLog(Base):
    __tablename__ = "general_volunteer_hour_logs"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(
        Integer, ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    shift_signup_id = Column(
        Integer, ForeignKey("shift_signups.id", ondelete="SET NULL"),
        nullable=True
    )

    # Hours logged
    log_date = Column(Date, nullable=False)
    hours = Column(Float, nullable=False)
    activity_type = Column(String(100), nullable=False)  # shift_work, training, event, other

    # Status
    status = Column(
        SQLEnum(HourLogStatus, name="hourlogstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=HourLogStatus.pending,
        nullable=False
    )

    # Description and notes
    description = Column(Text, nullable=True)
    submitted_by_volunteer_at = Column(DateTime(timezone=True), nullable=True)

    # Verification
    verified_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_notes = Column(Text, nullable=True)
    rejected_reason = Column(Text, nullable=True)

    # Rejection
    rejected_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    rejected_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    volunteer = relationship("Volunteer", backref="hour_logs")
    shift_signup = relationship("ShiftSignup", backref="hour_logs")
    verified_by = relationship("User", foreign_keys=[verified_by_id])
    rejected_by = relationship("User", foreign_keys=[rejected_by_id])

    __table_args__ = (
        Index("ix_general_volunteer_hour_logs_volunteer_date", "volunteer_id", "log_date"),
        Index("ix_volunteer_hour_logs_status", "status"),
    )


# ============================================================================
# Recognition and Milestones
# ============================================================================

class VolunteerMilestone(Base):
    __tablename__ = "volunteer_milestones"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(
        Integer, ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Milestone type
    milestone_type = Column(
        SQLEnum(MilestoneType, name="milestonetype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Achievement details
    achieved_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    achievement_value = Column(Float, nullable=True)  # e.g., 100 for "100 hours"
    celebration_message = Column(Text, nullable=True)

    # Recognition
    staff_recognition = Column(Text, nullable=True)
    public_recognition = Column(Boolean, default=False)
    featured_on_social_media = Column(Boolean, default=False)

    # Relationships
    volunteer = relationship("Volunteer", backref="milestones")

    __table_args__ = (
        Index("ix_volunteer_milestones_volunteer_type", "volunteer_id", "milestone_type"),
    )


class RecognitionAward(Base):
    __tablename__ = "recognition_awards"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(
        Integer, ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False
    )

    # Award details
    award_name = Column(String(255), nullable=False)
    award_type = Column(
        SQLEnum(AppreciationType, name="appreciationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    description = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)

    # Presentation
    awarded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    awarded_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    presentation_details = Column(Text, nullable=True)
    public_announcement = Column(Boolean, default=False)

    # Relationships
    volunteer = relationship("Volunteer", backref="recognition_awards")
    awarded_by = relationship("User")


# ============================================================================
# Communication Tools
# ============================================================================

class VolunteerCommunication(Base):
    __tablename__ = "volunteer_communications"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(
        Integer, ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Communication details
    subject = Column(String(500), nullable=False)
    message_body = Column(Text, nullable=False)
    communication_type = Column(
        SQLEnum(VolunteerCommunicationType, name="communicationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Sender/recipient
    sent_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Category
    category = Column(String(100), nullable=True)  # shift_reminder, training_due, opportunity, other

    # Tracking
    response_required = Column(Boolean, default=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    response_content = Column(Text, nullable=True)

    # Relationships
    volunteer = relationship("Volunteer", backref="communications")
    sent_by = relationship("User")

    __table_args__ = (
        Index("ix_volunteer_communications_volunteer_type", "volunteer_id", "communication_type"),
    )


# ============================================================================
# Reference Letter Generation
# ============================================================================

class ReferenceLetter(Base):
    __tablename__ = "reference_letters"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(
        Integer, ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False
    )

    # Letter details
    purpose = Column(String(255), nullable=False)  # e.g., "job_application", "school_application"
    recipient_name = Column(String(255), nullable=True)
    recipient_organization = Column(String(255), nullable=True)

    # Generated letter
    letter_title = Column(String(500), nullable=False)
    letter_body = Column(Text, nullable=False)

    # Statistics to include
    volunteer_total_hours = Column(Float, nullable=False)
    volunteer_years_of_service = Column(Float, nullable=False)
    volunteer_roles = Column(ARRAY(String), default=[], nullable=False)
    key_achievements = Column(ARRAY(String), default=[], nullable=False)

    # Generation and approval
    generated_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Delivery
    shared_with_volunteer_at = Column(DateTime(timezone=True), nullable=True)
    sent_to_recipient_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    volunteer = relationship("Volunteer", backref="reference_letters")
    generated_by = relationship("User", foreign_keys=[generated_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        Index("ix_reference_letters_volunteer", "volunteer_id"),
    )


# ============================================================================
# Volunteer Appreciation Tracking
# ============================================================================

class AppreciationRecord(Base):
    __tablename__ = "appreciation_records"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(
        Integer, ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Appreciation details
    appreciation_type = Column(
        SQLEnum(AppreciationType, name="appreciationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    description = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)

    # Occasion
    occasion = Column(String(255), nullable=True)  # e.g., "100-hour milestone", "anniversary"
    occasion_date = Column(Date, nullable=True)

    # Recognition
    given_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    given_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    made_public = Column(Boolean, default=False)
    public_announcement_date = Column(Date, nullable=True)

    # Details
    gift_description = Column(Text, nullable=True)
    certificate_title = Column(String(255), nullable=True)
    badge_name = Column(String(255), nullable=True)

    # Relationships
    volunteer = relationship("Volunteer", backref="appreciation_records")
    given_by = relationship("User")

    __table_args__ = (
        Index("ix_appreciation_records_volunteer_type", "volunteer_id", "appreciation_type"),
        Index("ix_appreciation_records_given_at", "given_at"),
    )
