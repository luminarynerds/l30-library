# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from enum import StrEnum
from typing import Optional

from app.models.mixins import TimestampMixin
from sqlalchemy import (
    Boolean, Column, DateTime, Float, Index, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


# ============================================================================
# Enums
# ============================================================================

class OverrideCategory(StrEnum):
    immediate = "immediate"          # Safety, accommodation, de-escalation
    documented = "documented"        # Fine adjustments, circulation exceptions
    reviewed = "reviewed"            # Multi-patron impact, financial threshold


class OverrideStatus(StrEnum):
    active = "active"
    resolved = "resolved"
    reviewed = "reviewed"
    led_to_policy_change = "led_to_policy_change"


class ExceptionOutcome(StrEnum):
    positive = "positive"
    neutral = "neutral"
    mixed = "mixed"
    learning_opportunity = "learning_opportunity"


class CommitteeStatus(StrEnum):
    active = "active"
    on_hold = "on_hold"
    completed = "completed"         # For ad-hoc committees
    archived = "archived"


class CommitteeMemberRole(StrEnum):
    member = "member"
    chair = "chair"
    secretary = "secretary"
    facilitator = "facilitator"


class MembershipStatus(StrEnum):
    active = "active"
    on_leave = "on_leave"
    departed = "departed"


class ProjectStatus(StrEnum):
    proposed = "proposed"
    approved = "approved"
    in_progress = "in_progress"
    completed = "completed"
    paused = "paused"
    cancelled = "cancelled"


class PolicyFeedbackType(StrEnum):
    comment = "comment"
    proposal = "proposal"
    concern = "concern"
    endorsement = "endorsement"
    amendment = "amendment"


class PolicyFeedbackStatus(StrEnum):
    submitted = "submitted"
    under_review = "under_review"
    accepted = "accepted"
    partially_accepted = "partially_accepted"
    deferred = "deferred"
    declined = "declined"


class ExpertiseLevel(StrEnum):
    developing = "developing"
    proficient = "proficient"
    advanced = "advanced"
    expert = "expert"


class DevelopmentCategory(StrEnum):
    technical_skills = "technical_skills"
    subject_expertise = "subject_expertise"
    leadership = "leadership"
    community_engagement = "community_engagement"
    innovation = "innovation"
    personal_growth = "personal_growth"


class DevelopmentActivityType(StrEnum):
    conference = "conference"
    course = "course"
    workshop = "workshop"
    reading = "reading"
    peer_learning = "peer_learning"
    mentoring = "mentoring"
    presentation = "presentation"
    publication = "publication"
    certification = "certification"
    project_based = "project_based"


class ProfessionalRecognitionType(StrEnum):
    peer_recognition = "peer_recognition"
    conference_presentation = "conference_presentation"
    internal_training_led = "internal_training_led"
    publication = "publication"
    mentorship = "mentorship"
    project_leadership = "project_leadership"


# ============================================================================
# Policy Override Tracking
# ============================================================================

class PolicyOverride(TimestampMixin, Base):
    __tablename__ = "policy_overrides"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Who made the override
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # What was overridden
    policy_area = Column(String(200), nullable=False, index=True)  # e.g., "circulation", "fines", "access"
    standard_policy = Column(Text, nullable=False)  # What the standard policy requires
    action_taken = Column(Text, nullable=False)  # What the staff member did instead

    # Why - the professional reasoning
    reasoning = Column(Text, nullable=False)  # 1-3 sentences of professional judgment
    patron_circumstance = Column(Text, nullable=True)  # Context without PII

    # Classification
    category = Column(
        SQLEnum(OverrideCategory, name="override_category", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True
    )
    status = Column(
        SQLEnum(OverrideStatus, name="override_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=OverrideStatus.active, nullable=False, index=True
    )

    # Outcome tracking
    outcome = Column(
        SQLEnum(ExceptionOutcome, name="exception_outcome", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )
    outcome_notes = Column(Text, nullable=True)

    # Review (for reviewed category)
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_date = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    # Policy impact
    led_to_policy_review = Column(Boolean, default=False)
    policy_change_reference = Column(String(500), nullable=True)

    # Financial impact (if applicable)
    financial_impact = Column(Float, nullable=True)

    # Timestamps provided by TimestampMixin

    # Relationships
    staff = relationship("User", foreign_keys=[staff_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        Index("ix_override_org_area", "organization_id", "policy_area"),
        Index("ix_override_staff_date", "staff_id", "created_at"),
        Index("ix_override_category_status", "category", "status"),
    )


# ============================================================================
# Committee Management
# ============================================================================

class StaffCommittee(TimestampMixin, Base):
    __tablename__ = "committees"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Committee details
    name = Column(String(200), nullable=False)
    purpose = Column(Text, nullable=False)
    meeting_frequency = Column(String(100), nullable=True)  # e.g., "monthly", "biweekly", "quarterly"

    # Status
    status = Column(
        SQLEnum(CommitteeStatus, name="committee_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=CommitteeStatus.active, nullable=False, index=True
    )
    is_standing = Column(Boolean, default=True)  # Standing vs ad-hoc

    # Formation
    proposed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_date = Column(DateTime(timezone=True), nullable=True)

    # Scope
    focus_areas = Column(JSONB, default=list)  # Array of focus area strings
    expected_outcomes = Column(Text, nullable=True)

    # Timestamps provided by TimestampMixin

    # Relationships
    proposed_by = relationship("User", foreign_keys=[proposed_by_id])
    members = relationship("StaffCommitteeMember", back_populates="committee", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_committee_org", "organization_id"),
        Index("ix_committee_status", "status"),
        UniqueConstraint("organization_id", "name", name="uq_committee_name"),
    )


class StaffCommitteeMember(TimestampMixin, Base):
    __tablename__ = "committee_members"

    id = Column(Integer, primary_key=True, index=True)
    committee_id = Column(Integer, ForeignKey("committees.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Role and status
    role = Column(
        SQLEnum(CommitteeMemberRole, name="committee_member_role", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=CommitteeMemberRole.member, nullable=False
    )
    status = Column(
        SQLEnum(MembershipStatus, name="membership_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=MembershipStatus.active, nullable=False, index=True
    )

    # Dates
    joined_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    departed_date = Column(DateTime(timezone=True), nullable=True)

    # Contributions
    contributions_summary = Column(Text, nullable=True)

    # Timestamps provided by TimestampMixin

    # Relationships
    committee = relationship("StaffCommittee", back_populates="members")
    staff = relationship("User", foreign_keys=[staff_id])

    __table_args__ = (
        Index("ix_committee_member_staff", "staff_id"),
        UniqueConstraint("committee_id", "staff_id", name="uq_committee_member"),
    )


# ============================================================================
# Project Leadership
# ============================================================================

class StaffProject(TimestampMixin, Base):
    __tablename__ = "staff_projects"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Project details
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    expected_impact = Column(Text, nullable=True)
    resources_needed = Column(Text, nullable=True)

    # Leadership
    lead_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    team_member_ids = Column(JSONB, default=list)  # Array of user IDs

    # Status
    status = Column(
        SQLEnum(ProjectStatus, name="project_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ProjectStatus.proposed, nullable=False, index=True
    )

    # Approval
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_date = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)

    # Budget
    budget_requested = Column(Float, nullable=True)
    budget_approved = Column(Float, nullable=True)
    budget_spent = Column(Float, default=0.0)

    # Timeline
    proposed_start_date = Column(DateTime(timezone=True), nullable=True)
    proposed_end_date = Column(DateTime(timezone=True), nullable=True)
    actual_start_date = Column(DateTime(timezone=True), nullable=True)
    actual_end_date = Column(DateTime(timezone=True), nullable=True)

    # Outcomes
    outcomes_summary = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)
    is_innovation_project = Column(Boolean, default=False)

    # Tags for categorization
    tags = Column(JSONB, default=list)

    # Timestamps provided by TimestampMixin

    # Relationships
    lead = relationship("User", foreign_keys=[lead_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        Index("ix_project_org", "organization_id"),
        Index("ix_project_lead", "lead_id"),
        Index("ix_project_status", "status"),
    )


# ============================================================================
# Policy Feedback & Voice
# ============================================================================

class PolicyFeedback(TimestampMixin, Base):
    __tablename__ = "policy_feedback"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Who submitted (nullable for anonymous)
    submitted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_anonymous = Column(Boolean, default=False)

    # What policy
    policy_name = Column(String(300), nullable=False, index=True)
    policy_document = Column(String(500), nullable=True)  # File path or reference

    # Feedback details
    feedback_type = Column(
        SQLEnum(PolicyFeedbackType, name="policy_feedback_type", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True
    )
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    proposed_change = Column(Text, nullable=True)  # Specific proposed wording if applicable
    rationale = Column(Text, nullable=True)

    # Status
    status = Column(
        SQLEnum(PolicyFeedbackStatus, name="policy_feedback_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PolicyFeedbackStatus.submitted, nullable=False, index=True
    )

    # Review
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_date = Column(DateTime(timezone=True), nullable=True)
    review_response = Column(Text, nullable=True)

    # Impact
    led_to_change = Column(Boolean, default=False)
    change_description = Column(Text, nullable=True)

    # Timestamps provided by TimestampMixin

    # Relationships
    submitted_by = relationship("User", foreign_keys=[submitted_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        Index("ix_feedback_org", "organization_id"),
        Index("ix_feedback_policy", "policy_name"),
        Index("ix_feedback_type_status", "feedback_type", "status"),
    )


# ============================================================================
# Expertise Recognition
# ============================================================================

class StaffExpertise(TimestampMixin, Base):
    __tablename__ = "staff_expertise"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Expertise details
    domain = Column(String(200), nullable=False, index=True)  # e.g., "youth services", "cataloging", "digital media"
    description = Column(Text, nullable=True)
    level = Column(
        SQLEnum(ExpertiseLevel, name="expertise_level", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ExpertiseLevel.proficient, nullable=False
    )

    # Credentials
    relevant_credentials = Column(JSONB, default=list)  # Array of credential strings
    years_experience = Column(Integer, nullable=True)

    # Availability
    willing_to_mentor = Column(Boolean, default=False)
    willing_to_train = Column(Boolean, default=False)
    willing_to_consult = Column(Boolean, default=True)

    # Visibility
    is_public = Column(Boolean, default=True)  # Visible in staff directory

    # Timestamps provided by TimestampMixin

    # Relationships
    staff = relationship("User", foreign_keys=[staff_id])

    __table_args__ = (
        Index("ix_expertise_staff", "staff_id"),
        Index("ix_expertise_domain", "domain"),
        Index("ix_expertise_org", "organization_id"),
        UniqueConstraint("staff_id", "domain", name="uq_staff_expertise_domain"),
    )


class ExpertiseRecognition(TimestampMixin, Base):
    __tablename__ = "expertise_recognitions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Who is recognized
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Recognition details
    recognition_type = Column(
        SQLEnum(ProfessionalRecognitionType, name="recognition_type", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True
    )
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Who gave the recognition (nullable for system-generated)
    recognized_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Related expertise
    expertise_domain = Column(String(200), nullable=True, index=True)

    # Details
    event_name = Column(String(300), nullable=True)  # Conference, training, etc.
    event_date = Column(DateTime(timezone=True), nullable=True)
    external_url = Column(String(500), nullable=True)  # Link to publication, presentation, etc.

    # Timestamps provided by TimestampMixin

    # Relationships
    staff = relationship("User", foreign_keys=[staff_id])
    recognized_by = relationship("User", foreign_keys=[recognized_by_id])

    __table_args__ = (
        Index("ix_recognition_staff", "staff_id"),
        Index("ix_recognition_org", "organization_id"),
        Index("ix_recognition_type", "recognition_type"),
    )


# ============================================================================
# Professional Development Choice
# ============================================================================

class ProfessionalDevelopmentPlan(TimestampMixin, Base):
    __tablename__ = "professional_development_plans"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Plan details
    title = Column(String(300), nullable=False)
    career_goals = Column(Text, nullable=True)
    focus_areas = Column(JSONB, default=list)  # Array of DevelopmentCategory values
    planned_activities = Column(JSONB, default=list)  # Array of activity descriptions

    # Budget
    annual_budget = Column(Float, nullable=True)
    budget_used = Column(Float, default=0.0)

    # Period
    plan_year = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)

    # Collaborative review
    last_review_date = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)  # Staff's own notes from review

    # Timestamps provided by TimestampMixin

    # Relationships
    staff = relationship("User", foreign_keys=[staff_id])
    activities = relationship("ProfessionalDevelopmentActivity", back_populates="plan", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_dev_plan_staff", "staff_id"),
        Index("ix_dev_plan_org", "organization_id"),
        Index("ix_dev_plan_year", "plan_year"),
        UniqueConstraint("staff_id", "plan_year", name="uq_staff_dev_plan_year"),
    )


class ProfessionalDevelopmentActivity(TimestampMixin, Base):
    __tablename__ = "professional_development_activities"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("professional_development_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Activity details
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    activity_type = Column(
        SQLEnum(DevelopmentActivityType, name="dev_activity_type", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True
    )
    category = Column(
        SQLEnum(DevelopmentCategory, name="dev_category", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Scheduling
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    hours_spent = Column(Float, nullable=True)

    # Cost
    cost = Column(Float, nullable=True)
    approved = Column(Boolean, default=True)

    # Completion
    completed = Column(Boolean, default=False)
    completion_date = Column(DateTime(timezone=True), nullable=True)
    reflection = Column(Text, nullable=True)  # Staff's own reflection on the activity

    # External details
    provider = Column(String(300), nullable=True)  # Organization, institution, etc.
    external_url = Column(String(500), nullable=True)
    certificate_earned = Column(Boolean, default=False)

    # Timestamps provided by TimestampMixin

    # Relationships
    plan = relationship("ProfessionalDevelopmentPlan", back_populates="activities")
    staff = relationship("User", foreign_keys=[staff_id])

    __table_args__ = (
        Index("ix_dev_activity_plan", "plan_id"),
        Index("ix_dev_activity_staff", "staff_id"),
        Index("ix_dev_activity_type", "activity_type"),
    )
