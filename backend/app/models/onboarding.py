# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Index, Integer, String, Text,
    UniqueConstraint, ForeignKey
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


# ============================================================================
# Enums
# ============================================================================

class OnboardingStatus(StrEnum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    on_hold = "on_hold"
    terminated = "terminated"


class OnboardingChecklistItemStatus(StrEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"
    blocked = "blocked"


class TrainingModuleStatus(StrEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    overdue = "overdue"


class SystemAccessStatus(StrEnum):
    not_requested = "not_requested"
    requested = "requested"
    provisioned = "provisioned"
    revoked = "revoked"
    pending_approval = "pending_approval"


class CheckInPeriod(StrEnum):
    first_day = "first_day"
    one_week = "one_week"
    thirty_day = "thirty_day"
    sixty_day = "sixty_day"
    ninety_day = "ninety_day"


class ProbationStatus(StrEnum):
    active = "active"
    passed = "passed"
    failed = "failed"
    extended = "extended"
    exempted = "exempted"


class FeedbackType(StrEnum):
    training = "training"
    orientation = "orientation"
    buddy_mentor = "buddy_mentor"
    general = "general"
    system_access = "system_access"


# ============================================================================
# Staff Onboarding Main Profile
# ============================================================================

class StaffOnboarding(Base):
    __tablename__ = "staff_onboarding"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )

    # Onboarding status and timeline
    status = Column(
        SQLEnum(OnboardingStatus, name="onboardingstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=OnboardingStatus.pending,
        nullable=False, index=True
    )
    start_date = Column(Date, nullable=False)
    expected_completion_date = Column(Date, nullable=False)
    actual_completion_date = Column(DateTime(timezone=True), nullable=True)

    # Department and position
    department = Column(String(100), nullable=False)
    position = Column(String(100), nullable=False)
    manager_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # Buddy/mentor assignment
    buddy_mentor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    buddy_mentor_assigned_at = Column(DateTime(timezone=True), nullable=True)

    # Probation period
    probation_start_date = Column(Date, nullable=True)
    probation_end_date = Column(Date, nullable=True)
    probation_status = Column(
        SQLEnum(ProbationStatus, name="probationstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ProbationStatus.active,
        nullable=False
    )

    # Completion tracking
    progress_percentage = Column(Integer, default=0, nullable=False)
    all_policies_acknowledged = Column(Boolean, default=False, nullable=False)
    all_systems_provisioned = Column(Boolean, default=False, nullable=False)

    # Metadata
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="onboarding_profile")
    manager = relationship("User", foreign_keys=[manager_id], backref="staff_managed")
    buddy_mentor = relationship("User", foreign_keys=[buddy_mentor_id], backref="mentees_onboarding")

    __table_args__ = (
        Index("ix_onboarding_status", "status"),
        Index("ix_onboarding_department", "department"),
        Index("ix_onboarding_manager", "manager_id"),
    )


# ============================================================================
# Pre-Arrival Checklist
# ============================================================================

class PreArrivalChecklistItem(Base):
    __tablename__ = "pre_arrival_checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    onboarding_id = Column(
        Integer, ForeignKey("staff_onboarding.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Item details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)  # e.g., "office", "equipment", "accounts", "keys"
    assigned_to_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Status tracking
    status = Column(
        SQLEnum(OnboardingChecklistItemStatus, name="checklistitemstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=OnboardingChecklistItemStatus.not_started,
        nullable=False, index=True
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Notes and evidence
    notes = Column(Text, nullable=True)
    evidence_url = Column(String(500), nullable=True)  # Link to photo or documentation, server_default=func.now())

    # Relationships
    onboarding = relationship("StaffOnboarding", backref="pre_arrival_checklist")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], backref="pre_arrival_assignments")
    completed_by = relationship("User", foreign_keys=[completed_by_id])

    __table_args__ = (
        Index("ix_pre_arrival_status", "status"),
        Index("ix_pre_arrival_category", "category"),
    )


# ============================================================================
# Day One Orientation
# ============================================================================

class OrientationSchedule(Base):
    __tablename__ = "orientation_schedules"

    id = Column(Integer, primary_key=True, index=True)
    onboarding_id = Column(
        Integer, ForeignKey("staff_onboarding.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Schedule details
    activity_title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    location = Column(String(200), nullable=True)

    # Facilitator/owner
    facilitator_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Completion tracking
    status = Column(
        SQLEnum(OnboardingChecklistItemStatus, name="checklistitemstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=OnboardingChecklistItemStatus.not_started,
        nullable=False
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    onboarding = relationship("StaffOnboarding", backref="orientation_schedule")
    facilitator = relationship("User", foreign_keys=[facilitator_id], backref="orientations_facilitated")


# ============================================================================
# Training Module Assignments
# ============================================================================

class TrainingModule(Base):
    __tablename__ = "training_modules"

    id = Column(Integer, primary_key=True, index=True)

    # Module details
    title = Column(String(200), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)  # e.g., "safety", "systems", "policies"
    duration_minutes = Column(Integer, nullable=False)
    is_mandatory = Column(Boolean, default=True, nullable=False)

    # Content and delivery
    content_url = Column(String(500), nullable=True)  # Link to training materials
    delivery_type = Column(String(50), nullable=False)  # "online", "in-person", "hybrid"
    passing_score = Column(Integer, default=80, nullable=False)  # Required percentage

    # Metadata
    order = Column(Integer, nullable=True)  # Order to complete modules, server_default=func.now())

    __table_args__ = (
        Index("ix_training_category", "category"),
    )


class TrainingModuleAssignment(Base):
    __tablename__ = "training_module_assignments"

    id = Column(Integer, primary_key=True, index=True)
    onboarding_id = Column(
        Integer, ForeignKey("staff_onboarding.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    training_module_id = Column(
        Integer, ForeignKey("training_modules.id", ondelete="CASCADE"),
        nullable=False
    )

    # Assignment details
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    due_date = Column(Date, nullable=False)

    # Completion tracking
    status = Column(
        SQLEnum(TrainingModuleStatus, name="trainingmodulestatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=TrainingModuleStatus.not_started,
        nullable=False, index=True
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    score = Column(Integer, nullable=True)
    passed = Column(Boolean, nullable=True)

    # Verification
    verified_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    verified_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    onboarding = relationship("StaffOnboarding", backref="training_assignments")
    training_module = relationship("TrainingModule")
    verified_by = relationship("User", foreign_keys=[verified_by_id])

    __table_args__ = (
        UniqueConstraint("onboarding_id", "training_module_id", name="uq_onboarding_training"),
        Index("ix_training_assignment_status", "status"),
    )


# ============================================================================
# Policy Acknowledgments
# ============================================================================

class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)

    # Policy details
    title = Column(String(200), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)  # e.g., "code of conduct", "safety", "confidentiality"
    content = Column(Text, nullable=False)
    version = Column(String(20), default="1.0", nullable=False)
    is_mandatory = Column(Boolean, default=True, nullable=False)

    # Effective date
    effective_date = Column(Date, nullable=False)
    supersedes_policy_id = Column(
        Integer, ForeignKey("policies.id", ondelete="SET NULL"),
        nullable=True
    )

    __table_args__ = (
        Index("ix_policies_category", "category"),
        Index("ix_policy_version", "title", "version"),
    )


class PolicyAcknowledgment(Base):
    __tablename__ = "policy_acknowledgments"

    id = Column(Integer, primary_key=True, index=True)
    onboarding_id = Column(
        Integer, ForeignKey("staff_onboarding.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    policy_id = Column(
        Integer, ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False
    )

    # Acknowledgment details
    acknowledged_at = Column(DateTime(timezone=True), nullable=False)
    acknowledged_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False
    )
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    notes = Column(Text, nullable=True)

    # Relationships
    onboarding = relationship("StaffOnboarding", backref="policy_acknowledgments")
    policy = relationship("Policy")
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_id])

    __table_args__ = (
        UniqueConstraint("onboarding_id", "policy_id", name="uq_onboarding_policy"),
        Index("ix_policy_ack_date", "acknowledged_at"),
    )


# ============================================================================
# System Access Provisioning
# ============================================================================

class SystemAccess(Base):
    __tablename__ = "system_access"

    id = Column(Integer, primary_key=True, index=True)

    # System details
    system_name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    access_type = Column(String(50), nullable=False)  # e.g., "email", "vpn", "database", "software"
    provisioning_instructions = Column(Text, nullable=True)
    deprovisioning_instructions = Column(Text, nullable=True)


class SystemAccessProvisioning(Base):
    __tablename__ = "system_access_provisioning"

    id = Column(Integer, primary_key=True, index=True)
    onboarding_id = Column(
        Integer, ForeignKey("staff_onboarding.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    system_access_id = Column(
        Integer, ForeignKey("system_access.id", ondelete="CASCADE"),
        nullable=False
    )

    # Provisioning details
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    requested_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Status tracking
    status = Column(
        SQLEnum(SystemAccessStatus, name="systemaccessstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=SystemAccessStatus.not_requested,
        nullable=False, index=True
    )
    provisioned_at = Column(DateTime(timezone=True), nullable=True)
    provisioned_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    credentials_provided = Column(Boolean, default=False, nullable=False)
    credentials_provided_at = Column(DateTime(timezone=True), nullable=True)

    # Revocation (for termination or role changes)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    revocation_reason = Column(String(200), nullable=True)

    notes = Column(Text, nullable=True)

    # Relationships
    onboarding = relationship("StaffOnboarding", backref="system_access_provisioning")
    system_access = relationship("SystemAccess")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    provisioned_by = relationship("User", foreign_keys=[provisioned_by_id])
    revoked_by = relationship("User", foreign_keys=[revoked_by_id])

    __table_args__ = (
        UniqueConstraint("onboarding_id", "system_access_id", name="uq_onboarding_system"),
        Index("ix_access_provisioning_status", "status"),
    )


# ============================================================================
# Check-in Meetings (30/60/90 day)
# ============================================================================

class CheckInMeeting(Base):
    __tablename__ = "check_in_meetings"

    id = Column(Integer, primary_key=True, index=True)
    onboarding_id = Column(
        Integer, ForeignKey("staff_onboarding.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Meeting details
    period = Column(
        SQLEnum(CheckInPeriod, name="checkinperiod", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    scheduled_date = Column(Date, nullable=False)
    scheduled_time = Column(DateTime(timezone=True), nullable=True)

    # Participants
    scheduled_with_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Preparation and topics
    topics = Column(ARRAY(String), default=[], nullable=False)
    preparation_notes = Column(Text, nullable=True)

    # Completion tracking
    completed_at = Column(DateTime(timezone=True), nullable=True)
    location = Column(String(200), nullable=True)
    meeting_notes = Column(Text, nullable=True)

    # Feedback and outcomes
    feedback_from_new_hire = Column(Text, nullable=True)
    feedback_from_manager = Column(Text, nullable=True)
    action_items = Column(ARRAY(String), default=[], nullable=False)
    next_steps = Column(Text, nullable=True)

    # Relationships
    onboarding = relationship("StaffOnboarding", backref="check_in_meetings")
    scheduled_with = relationship("User", foreign_keys=[scheduled_with_id])

    __table_args__ = (
        Index("ix_checkin_period", "period"),
        Index("ix_checkin_date", "scheduled_date"),
    )


# ============================================================================
# Introduction Announcements
# ============================================================================

class IntroductionAnnouncement(Base):
    __tablename__ = "introduction_announcements"

    id = Column(Integer, primary_key=True, index=True)
    onboarding_id = Column(
        Integer, ForeignKey("staff_onboarding.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Announcement details
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    announcement_type = Column(String(50), nullable=False)  # "email", "bulletin", "meeting", "all_staff"
    scheduled_date = Column(Date, nullable=False)

    # Distribution
    distributed_to = Column(ARRAY(String), default=[], nullable=False)  # e.g., ["department", "all_staff"]
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Tracking
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    onboarding = relationship("StaffOnboarding", backref="introduction_announcements")
    created_by = relationship("User", foreign_keys=[created_by_id])
    published_by = relationship("User", foreign_keys=[published_by_id])

    __table_args__ = (
        Index("ix_announcement_date", "scheduled_date"),
    )


# ============================================================================
# Onboarding Feedback
# ============================================================================

class OnboardingFeedback(Base):
    __tablename__ = "onboarding_feedback"

    id = Column(Integer, primary_key=True, index=True)
    onboarding_id = Column(
        Integer, ForeignKey("staff_onboarding.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Feedback details
    feedback_type = Column(
        SQLEnum(FeedbackType, name="feedbacktype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    rating = Column(Integer, nullable=True)  # 1-5 scale
    comments = Column(Text, nullable=True)

    # Source
    provided_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False
    )
    is_anonymous = Column(Boolean, default=False, nullable=False)

    # Metadata, server_default=func.now())

    # Relationships
    onboarding = relationship("StaffOnboarding", backref="feedback")
    provided_by = relationship("User", foreign_keys=[provided_by_id])

    __table_args__ = (
        Index("ix_feedback_type", "feedback_type"),
    )
