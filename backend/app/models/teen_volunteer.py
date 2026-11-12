# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from app.models.mixins import TimestampMixin
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

class TeenVolunteerStatus(StrEnum):
    pending_approval = "pending_approval"
    active = "active"
    inactive = "inactive"
    on_leave = "on_leave"
    suspended = "suspended"
    completed = "completed"


class TeenConsentStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    declined = "declined"
    revoked = "revoked"


class TaskDifficulty(StrEnum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class TaskType(StrEnum):
    reading_helper = "reading_helper"
    shelving = "shelving"
    tech_support = "tech_support"
    event_assistant = "event_assistant"
    summer_reading = "summer_reading"
    community_outreach = "community_outreach"
    program_helper = "program_helper"
    book_curation = "book_curation"
    mentoring = "mentoring"
    administrative = "administrative"


class MentorshipStatus(StrEnum):
    pending_match = "pending_match"
    active = "active"
    paused = "paused"
    completed = "completed"
    terminated = "terminated"


class AchievementType(StrEnum):
    hours_milestone = "hours_milestone"  # 10, 25, 50, 100 hours
    task_completion = "task_completion"
    leadership = "leadership"
    community_impact = "community_impact"
    summer_reading_helper = "summer_reading_helper"
    mentorship = "mentorship"
    college_prep = "college_prep"
    teen_board = "teen_board"
    special_event = "special_event"


class SchoolVerificationLetterStatus(StrEnum):
    pending = "pending"
    generated = "generated"
    sent = "sent"
    picked_up = "picked_up"


# ============================================================================
# Teen Volunteer Profile
# ============================================================================

class TeenVolunteer(TimestampMixin, Base):
    __tablename__ = "teen_volunteers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )

    # Enrollment status
    status = Column(
        SQLEnum(TeenVolunteerStatus, name="teenvolunteerstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=TeenVolunteerStatus.pending_approval,
        nullable=False
    )

    # Age and safety info
    date_of_birth = Column(Date, nullable=False)
    age_at_registration = Column(Integer, nullable=False)  # Snapshot for safety checks

    # School information
    school_name = Column(String(200), nullable=True)
    school_district = Column(String(200), nullable=True)
    grade_level = Column(String(20), nullable=True)  # e.g., "9th Grade", "Junior"
    school_phone = Column(String(20), nullable=True)

    # Parent/Guardian Information
    guardian_name = Column(String(200), nullable=False)
    guardian_email = Column(String(255), nullable=False)
    guardian_phone = Column(String(20), nullable=False)
    guardian_relationship = Column(String(50), nullable=True)  # Mother, Father, Guardian, etc.

    # Alternate emergency contact
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relationship = Column(String(50), nullable=True)

    # Medical information
    has_health_restrictions = Column(Boolean, default=False)
    health_restrictions_notes = Column(Text, nullable=True)
    emergency_medical_info = Column(Text, nullable=True)  # Allergies, medications, etc.
    insurance_provider = Column(String(200), nullable=True)
    insurance_policy_number = Column(String(100), nullable=True)

    # Safety and clearance
    background_check_completed = Column(Boolean, default=False)
    background_check_date = Column(Date, nullable=True)
    background_check_status = Column(String(50), default="pending")  # pending, passed, failed
    training_completed = Column(Boolean, default=False)
    training_date = Column(Date, nullable=True)
    safety_acknowledgment = Column(Boolean, default=False)
    safety_acknowledgment_date = Column(DateTime(timezone=True), nullable=True)

    # Interests and strengths
    interests = Column(ARRAY(String), default=[], nullable=False)  # Tech, art, sports, etc.
    strengths = Column(ARRAY(String), default=[], nullable=False)  # Leadership, creative, etc.
    preferred_task_types = Column(
        ARRAY(String), default=[], nullable=False
    )  # Based on TaskType enum

    # Availability
    available_days = Column(ARRAY(String), default=[])  # ["Monday", "Wednesday", "Friday"]
    available_time_start = Column(String(10), nullable=True)  # "14:00"
    available_time_end = Column(String(10), nullable=True)  # "17:00"
    max_hours_per_week = Column(Integer, default=10)

    # Statistics
    total_service_hours = Column(Float, default=0, nullable=False)
    total_verified_hours = Column(Float, default=0, nullable=False)
    total_tasks_completed = Column(Integer, default=0, nullable=False)

    # Approval workflow
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approval_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Recognition and gamification
    current_recognition_level = Column(String(50), default="bronze")  # bronze, silver, gold, platinum
    total_achievements = Column(Integer, default=0)
    is_teen_board_member = Column(Boolean, default=False)

    # Important dates
    last_active_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="teen_volunteer")
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    service_hours = relationship(
        "TeenVolunteerHourLog",
        back_populates="volunteer",
        cascade="all, delete-orphan"
    )
    task_assignments = relationship(
        "TeenVolunteerTask",
        back_populates="volunteer",
        cascade="all, delete-orphan"
    )
    parent_consent = relationship(
        "ParentGuardianConsent",
        back_populates="volunteer",
        uselist=False,
        cascade="all, delete-orphan"
    )
    mentorship_mentee = relationship(
        "MentorshipPairing",
        foreign_keys="MentorshipPairing.mentee_id",
        back_populates="mentee",
        cascade="all, delete-orphan"
    )
    mentorship_mentor = relationship(
        "MentorshipPairing",
        foreign_keys="MentorshipPairing.mentor_id",
        back_populates="mentor",
        cascade="all, delete-orphan"
    )
    achievements = relationship(
        "TeenAchievement",
        back_populates="volunteer",
        cascade="all, delete-orphan"
    )
    college_support = relationship(
        "CollegeApplicationSupport",
        back_populates="volunteer",
        uselist=False,
        cascade="all, delete-orphan"
    )
    verification_letters = relationship(
        "SchoolVerificationLetter",
        back_populates="volunteer",
        cascade="all, delete-orphan"
    )
    summer_reading_assignments = relationship(
        "SummerReadingHelperAssignment",
        back_populates="volunteer",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_teen_volunteers_status_created", "status", "created_at"),
        Index("ix_teen_volunteers_school", "school_name", "grade_level"),
    )


# ============================================================================
# Parent/Guardian Consent
# ============================================================================

class ParentGuardianConsent(Base):
    __tablename__ = "parent_guardian_consents"

    id = Column(Integer, primary_key=True)
    volunteer_id = Column(
        Integer, ForeignKey("teen_volunteers.id", ondelete="CASCADE"),
        nullable=False, unique=True
    )

    # Consent status
    status = Column(
        SQLEnum(TeenConsentStatus, name="consentstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=TeenConsentStatus.pending,
        nullable=False
    )

    # Consent document
    consent_form_version = Column(String(50), nullable=False)  # 1.0, 2.0, etc.
    consent_document_url = Column(Text, nullable=True)
    consent_signed_date = Column(DateTime(timezone=True), nullable=True)
    consent_declined_date = Column(DateTime(timezone=True), nullable=True)
    consent_revoked_date = Column(DateTime(timezone=True), nullable=True)
    revocation_reason = Column(Text, nullable=True)

    # Parental approval details
    approved_by_name = Column(String(200), nullable=True)
    approved_by_email = Column(String(255), nullable=True)
    approved_by_signature = Column(Text, nullable=True)  # Base64 image

    # Risk acknowledgments
    acknowledges_health_risks = Column(Boolean, default=False)
    acknowledges_background_check = Column(Boolean, default=False)
    authorizes_transportation = Column(Boolean, default=False)
    authorizes_photo_use = Column(Boolean, default=False)
    authorizes_media_mention = Column(Boolean, default=False)

    # Restrictions from parent
    special_restrictions = Column(Text, nullable=True)
    task_restrictions = Column(ARRAY(String), default=[])  # Task types to avoid
    time_restrictions = Column(Text, nullable=True)

    # Communication preferences
    contact_frequency = Column(String(50), default="monthly")  # weekly, monthly, as_needed
    preferred_contact_method = Column(String(50), default="email")  # email, phone, mail, server_default=func.now())

    # Relationships
    volunteer = relationship("TeenVolunteer", back_populates="parent_consent")


# ============================================================================
# Service Hour Tracking
# ============================================================================

class TeenVolunteerHourLog(Base):
    __tablename__ = "teen_volunteer_hour_logs"

    id = Column(Integer, primary_key=True)
    volunteer_id = Column(
        Integer, ForeignKey("teen_volunteers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Date and hours
    service_date = Column(Date, nullable=False)
    hours = Column(Float, nullable=False)
    minutes = Column(Integer, default=0)  # For sub-hour precision

    # Task information
    task_id = Column(
        Integer, ForeignKey("teen_volunteer_tasks.id", ondelete="SET NULL"),
        nullable=True
    )
    task_type = Column(
        SQLEnum(TaskType, name="tasktype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    task_description = Column(Text, nullable=True)

    # Location
    branch_id = Column(
        Integer,
        nullable=True
    )
    location_notes = Column(Text, nullable=True)

    # Impact metrics
    items_shelved = Column(Integer, default=0)
    programs_assisted = Column(Integer, default=0)
    patrons_helped = Column(Integer, default=0)
    books_cataloged = Column(Integer, default=0)

    # Verification
    verified = Column(Boolean, default=False)
    verified_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_notes = Column(Text, nullable=True)

    # Staff supervision
    supervised_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Notes
    volunteer_notes = Column(Text, nullable=True)
    staff_notes = Column(Text, nullable=True)

    # Relationships
    volunteer = relationship("TeenVolunteer", back_populates="service_hours")
    task = relationship("TeenVolunteerTask", back_populates="hour_logs")
    verified_by = relationship("User", foreign_keys=[verified_by_id])
    supervised_by = relationship("User", foreign_keys=[supervised_by_id])
    # DISABLED: # DISABLED: branch relationship

    __table_args__ = (
        Index("ix_teen_volunteer_hours_volunteer_date", "volunteer_id", "service_date"),
        Index("ix_teen_volunteer_hours_verified", "verified", "verified_by_id"),
    )


# ============================================================================
# Task Assignments
# ============================================================================

class TeenVolunteerTask(Base):
    __tablename__ = "teen_volunteer_tasks"

    id = Column(Integer, primary_key=True)
    volunteer_id = Column(
        Integer, ForeignKey("teen_volunteers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Task details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    task_type = Column(
        SQLEnum(TaskType, name="tasktype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    difficulty = Column(
        SQLEnum(TaskDifficulty, name="taskdifficulty", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=TaskDifficulty.beginner,
        nullable=False
    )

    # Age appropriateness
    min_age_required = Column(Integer, default=13)
    max_age_recommended = Column(Integer, nullable=True)
    requires_background_check = Column(Boolean, default=False)
    requires_training = Column(Boolean, default=False)

    # Task requirements
    estimated_hours = Column(Float, nullable=False)
    skills_required = Column(ARRAY(String), default=[])
    equipment_needed = Column(ARRAY(String), default=[])
    supervision_level = Column(String(50), default="standard")  # light, standard, close

    # Safety info
    hazards = Column(Text, nullable=True)
    safety_precautions = Column(Text, nullable=True)
    requires_parental_approval = Column(Boolean, default=False)

    # Assignment status
    assigned_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    due_date = Column(Date, nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="assigned")  # assigned, in_progress, completed, cancelled

    # Task feedback
    volunteer_feedback = Column(Text, nullable=True)
    staff_feedback = Column(Text, nullable=True)
    difficulty_rating = Column(Integer, nullable=True)  # 1-5 scale from volunteer, server_default=func.now())

    # Relationships
    volunteer = relationship("TeenVolunteer", back_populates="task_assignments")
    assigned_by = relationship("User")
    hour_logs = relationship("TeenVolunteerHourLog", back_populates="task")

    __table_args__ = (
        Index("ix_teen_volunteer_tasks_status", "status", "assigned_date"),
        Index("ix_teen_volunteer_tasks_difficulty", "difficulty", "min_age_required"),
    )


# ============================================================================
# School Verification Letters
# ============================================================================

class SchoolVerificationLetter(Base):
    __tablename__ = "school_verification_letters"

    id = Column(Integer, primary_key=True)
    volunteer_id = Column(
        Integer, ForeignKey("teen_volunteers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Request details
    request_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    requested_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Letter period
    service_period_start = Column(Date, nullable=False)
    service_period_end = Column(Date, nullable=False)
    total_service_hours = Column(Float, nullable=False)  # Hours during period

    # Status
    status = Column(
        SQLEnum(SchoolVerificationLetterStatus, name="schoolverificationletterstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=SchoolVerificationLetterStatus.pending,
        nullable=False
    )

    # Letter content
    letter_template = Column(String(100), nullable=True)  # Name of template used
    generated_date = Column(DateTime(timezone=True), nullable=True)
    letter_text = Column(Text, nullable=True)
    letter_format = Column(String(20), default="pdf")  # pdf, doc, html

    # Distribution
    sent_to_school = Column(Boolean, default=False)
    sent_date = Column(DateTime(timezone=True), nullable=True)
    school_email = Column(String(255), nullable=True)
    school_contact_person = Column(String(200), nullable=True)
    school_phone = Column(String(20), nullable=True)

    picked_up_date = Column(DateTime(timezone=True), nullable=True)
    picked_up_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Signature
    signed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    signed_date = Column(DateTime(timezone=True), nullable=True)

    # Additional notes
    special_notes = Column(Text, nullable=True)  # Achievements to highlight, etc., server_default=func.now())

    # Relationships
    volunteer = relationship("TeenVolunteer", back_populates="verification_letters")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    picked_up_by = relationship("User", foreign_keys=[picked_up_by_id])
    signed_by = relationship("User", foreign_keys=[signed_by_id])

    __table_args__ = (
        Index("ix_school_verification_letters_status", "status", "request_date"),
        Index("ix_school_verification_letters_volunteer", "volunteer_id", "service_period_start"),
    )


# ============================================================================
# Mentorship Pairings
# ============================================================================

class MentorshipPairing(Base):
    __tablename__ = "mentorship_pairings"

    id = Column(Integer, primary_key=True)
    mentor_id = Column(
        Integer, ForeignKey("teen_volunteers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    mentee_id = Column(
        Integer, ForeignKey("teen_volunteers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Status
    status = Column(
        SQLEnum(MentorshipStatus, name="mentorshipstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=MentorshipStatus.pending_match,
        nullable=False
    )

    # Pairing details
    paired_date = Column(DateTime(timezone=True), nullable=True)
    paired_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    pairing_reason = Column(Text, nullable=True)

    # Mentorship goals
    goals = Column(ARRAY(String), default=[])
    expected_duration = Column(String(50), nullable=True)  # e.g., "3 months", "semester"
    focus_areas = Column(ARRAY(String), default=[])  # Task areas, skills, etc.

    # Meeting schedule
    meeting_frequency = Column(String(50), default="weekly")  # weekly, biweekly, monthly
    preferred_meeting_time = Column(String(10), nullable=True)
    meeting_location = Column(String(200), nullable=True)

    # Completion tracking
    completed_date = Column(DateTime(timezone=True), nullable=True)
    completion_reason = Column(Text, nullable=True)
    mentor_feedback = Column(Text, nullable=True)
    mentee_feedback = Column(Text, nullable=True)

    # Progress notes
    notes = Column(Text, nullable=True)

    # Relationships
    mentor = relationship(
        "TeenVolunteer",
        foreign_keys=[mentor_id],
        back_populates="mentorship_mentor"
    )
    mentee = relationship(
        "TeenVolunteer",
        foreign_keys=[mentee_id],
        back_populates="mentorship_mentee"
    )
    paired_by = relationship("User")

    __table_args__ = (
        Index("ix_mentorship_pairings_status", "status", "paired_date"),
        Index("ix_mentorship_pairings_pair", "mentor_id", "mentee_id"),
        UniqueConstraint("mentor_id", "mentee_id", name="uq_mentorship_pair"),
    )


# ============================================================================
# College Application Support
# ============================================================================

class CollegeApplicationSupport(TimestampMixin, Base):
    __tablename__ = "college_application_support"

    id = Column(Integer, primary_key=True)
    volunteer_id = Column(
        Integer, ForeignKey("teen_volunteers.id", ondelete="CASCADE"),
        nullable=False, unique=True
    )

    # Support provided
    has_letter_of_recommendation = Column(Boolean, default=False)
    letter_of_recommendation_date = Column(DateTime(timezone=True), nullable=True)
    letter_of_recommendation_written_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Volunteer hours for college applications
    certified_hours = Column(Float, default=0)  # Hours certified for college use
    total_service_value = Column(Float, nullable=True)  # Estimated monetary value

    # Essay/statement support
    community_service_essay_started = Column(Boolean, default=False)
    essay_feedback_provided = Column(Boolean, default=False)
    essay_feedback_date = Column(DateTime(timezone=True), nullable=True)

    # Interview preparation
    interview_prep_completed = Column(Boolean, default=False)
    interview_prep_sessions = Column(Integer, default=0)

    # Leadership and achievements summary
    leadership_summary = Column(Text, nullable=True)
    impact_statement = Column(Text, nullable=True)

    # College counselor coordination
    college_counselor_contacted = Column(Boolean, default=False)
    college_counselor_name = Column(String(200), nullable=True)
    college_counselor_email = Column(String(255), nullable=True)

    # Colleges being applied to
    target_colleges = Column(ARRAY(String), default=[])  # College names
    college_interests = Column(ARRAY(String), default=[])  # Intended majors, etc.

    # Support notes
    notes = Column(Text, nullable=True)

    # Relationships
    volunteer = relationship("TeenVolunteer", back_populates="college_support")
    letter_writer = relationship("User", foreign_keys=[letter_of_recommendation_written_by_id])

    __table_args__ = (
        Index("ix_college_application_support_updated", "updated_at"),
    )


# ============================================================================
# Teen Advisory Board
# ============================================================================

class TeenAdvisoryBoardMember(Base):
    __tablename__ = "teen_advisory_board_members"

    id = Column(Integer, primary_key=True)
    volunteer_id = Column(
        Integer, ForeignKey("teen_volunteers.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )

    # Membership details
    joined_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    term_start = Column(Date, nullable=False)
    term_end = Column(Date, nullable=True)
    position = Column(String(100), nullable=True)  # President, Vice-President, Member, etc.

    # Participation
    total_meetings_attended = Column(Integer, default=0)
    total_meetings_held = Column(Integer, default=0)
    attendance_percentage = Column(Float, default=0)

    # Contributions
    initiatives_proposed = Column(Integer, default=0)
    initiatives_approved = Column(Integer, default=0)
    projects_led = Column(ARRAY(String), default=[])

    # Voting rights
    has_voting_rights = Column(Boolean, default=True)
    votes_cast = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    left_date = Column(DateTime(timezone=True), nullable=True)
    left_reason = Column(Text, nullable=True)

    # Feedback and evaluation
    performance_notes = Column(Text, nullable=True)
    leadership_rating = Column(Integer, nullable=True)  # 1-5 scale
    contribution_impact = Column(Text, nullable=True)

    # Relationships
    volunteer = relationship("TeenVolunteer")

    __table_args__ = (
        Index("ix_teen_advisory_board_members_active", "is_active", "joined_date"),
        Index("ix_teen_advisory_board_members_term", "term_start", "term_end"),
    )


# ============================================================================
# Achievements and Recognition
# ============================================================================

class TeenAchievement(Base):
    __tablename__ = "teen_achievements"

    id = Column(Integer, primary_key=True)
    volunteer_id = Column(
        Integer, ForeignKey("teen_volunteers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Achievement details
    achievement_type = Column(
        SQLEnum(AchievementType, name="achievementtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    badge_icon_url = Column(Text, nullable=True)  # URL or base64 image

    # Earning criteria
    criteria_met = Column(Text, nullable=True)
    earned_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    earned_by_trigger = Column(String(200), nullable=True)  # What triggered this achievement

    # Recognition
    is_public = Column(Boolean, default=True)  # Can be displayed on profile
    recognition_level = Column(String(50), nullable=True)  # bronze, silver, gold
    display_order = Column(Integer, nullable=True)  # For ordering on profile

    # Milestone tracking
    milestone_number = Column(Integer, nullable=True)  # 1st, 2nd, etc. for same type
    associated_hours = Column(Float, nullable=True)  # For hour-based achievements

    # Sharing and promotion
    promoted_on_social = Column(Boolean, default=False)
    promoted_date = Column(DateTime(timezone=True), nullable=True)
    featured_in_newsletter = Column(Boolean, default=False)

    # Relationships
    volunteer = relationship("TeenVolunteer", back_populates="achievements")

    __table_args__ = (
        Index("ix_teen_achievements_volunteer_type", "volunteer_id", "achievement_type"),
        Index("ix_teen_achievements_earned_date", "earned_date"),
    )


# ============================================================================
# Summer Reading Helper Program
# ============================================================================

class SummerReadingHelperAssignment(Base):
    __tablename__ = "summer_reading_helper_assignments"

    id = Column(Integer, primary_key=True)
    volunteer_id = Column(
        Integer, ForeignKey("teen_volunteers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Assignment details
    summer_year = Column(Integer, nullable=False)
    assignment_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Responsibilities
    responsibilities = Column(ARRAY(String), default=[])
    age_groups_assigned = Column(ARRAY(String), default=[])  # e.g., "6-8", "9-12", "13-15"
    branch_assignments = Column(ARRAY(Integer), default=[])  # Branch IDs

    # Program participation
    kickoff_attended = Column(Boolean, default=False)
    final_event_attended = Column(Boolean, default=False)
    total_hours = Column(Float, default=0)

    # Performance tracking
    children_helped = Column(Integer, default=0)
    sessions_led = Column(Integer, default=0)
    program_rating = Column(Integer, nullable=True)  # 1-5 scale

    # Impact
    children_feedback_positive = Column(Integer, default=0)
    parent_feedback = Column(Text, nullable=True)
    staff_evaluation = Column(Text, nullable=True)

    # Status
    status = Column(String(50), default="assigned")  # assigned, active, completed
    completion_date = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    volunteer = relationship("TeenVolunteer", back_populates="summer_reading_assignments")
    assigned_by = relationship("User")

    __table_args__ = (
        Index("ix_summer_reading_assignments_year", "summer_year", "status"),
        Index("ix_summer_reading_assignments_volunteer", "volunteer_id", "summer_year"),
    )
