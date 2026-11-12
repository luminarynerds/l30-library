# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum, StrEnum
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SQLEnum, ForeignKey,
    Integer, String, Text, Index, Numeric, and_, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


class LiteracyLearnerStatus(StrEnum):
    PROSPECTIVE = "prospective"  # Inquiry stage
    INTAKE_SCHEDULED = "intake_scheduled"  # Scheduled for assessment
    ACTIVE = "active"  # Currently enrolled and attending
    ON_HOLD = "on_hold"  # Temporarily paused
    COMPLETED = "completed"  # Program completed
    INACTIVE = "inactive"  # No longer attending
    TRANSFERRED = "transferred"  # Moved to another program


class AssessmentType(StrEnum):
    INITIAL_INTAKE = "initial_intake"  # Intake assessment
    PHONICS = "phonics"  # Phonics and decoding
    COMPREHENSION = "comprehension"  # Reading comprehension
    FLUENCY = "fluency"  # Reading fluency
    VOCABULARY = "vocabulary"  # Vocabulary knowledge
    DIGITAL_LITERACY = "digital_literacy"  # Digital/tech skills
    MATH_BASIC = "math_basic"  # Basic numeracy
    GED_PREP = "ged_prep"  # GED readiness


class LearnerAssessmentLevel(StrEnum):
    PRE_LITERACY = "pre_literacy"  # No reading skills (0-40 wpm)
    EMERGENT = "emergent"  # Beginning reader (40-60 wpm)
    BEGINNING = "beginning"  # Basic proficiency (60-80 wpm)
    INTERMEDIATE = "intermediate"  # Good proficiency (80-120 wpm)
    ADVANCED = "advanced"  # Strong reader (120-160 wpm)
    PROFICIENT = "proficient"  # Grade-level or above (160+ wpm)


class GoalType(StrEnum):
    FLUENCY_IMPROVEMENT = "fluency_improvement"
    COMPREHENSION = "comprehension"
    DECODING = "decoding"
    VOCABULARY = "vocabulary"
    DIGITAL_LITERACY = "digital_literacy"
    EMPLOYMENT = "employment"
    GED_PREPARATION = "ged_preparation"
    FAMILY_LITERACY = "family_literacy"
    PERSONAL_FULFILLMENT = "personal_fulfillment"


class GoalStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    ABANDONED = "abandoned"
    ARCHIVED = "archived"


class LiteracyLearner(Base, TimestampMixin):
    __tablename__ = "literacy_learners"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== ENROLLMENT INFORMATION ====================
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(
        String(50),
        default=LiteracyLearnerStatus.INTAKE_SCHEDULED,
        nullable=False,
        index=True
    )

    # ==================== LEARNER DEMOGRAPHICS ====================
    # These are stored separately from User model for literacy-specific tracking
    age = Column(Integer, nullable=True)  # Current age
    date_of_birth = Column(Date, nullable=True)
    native_language = Column(String(100), nullable=True)
    languages_spoken = Column(String(500), nullable=True)  # Comma-separated
    education_background = Column(Text, nullable=True)  # Previous education history
    employment_status = Column(String(50), nullable=True)  # employed, unemployed, seeking, student, etc.

    # ==================== CONFIDENTIAL INFORMATION ====================
    # These fields are masked based on user role
    income_level = Column(String(50), nullable=True)  # Sensitive - requires confidentiality
    barriers_to_literacy = Column(Text, nullable=True)  # Sensitive - requires confidentiality
    health_notes = Column(Text, nullable=True)  # Sensitive - requires confidentiality
    family_literacy_notes = Column(Text, nullable=True)  # Sensitive - requires confidentiality
    accessibility_needs = Column(Text, nullable=True)
    transportation_needs = Column(Boolean, default=False)
    childcare_needed = Column(Boolean, default=False)

    # ==================== ASSESSMENT TRACKING ====================
    current_level = Column(
        String(50),
        nullable=True
    )
    last_assessment_date = Column(DateTime(timezone=True), nullable=True)
    last_assessment_score = Column(Numeric(5, 2), nullable=True)

    # ==================== PROGRESS METRICS ====================
    total_hours_attended = Column(Numeric(8, 2), default=0, nullable=False)
    total_sessions_completed = Column(Integer, default=0, nullable=False)
    current_reading_level_wpm = Column(Integer, nullable=True)  # Words per minute

    # ==================== PROGRAM ENGAGEMENT ====================
    primary_goal_type = Column(
        String(50),
        nullable=True
    )
    referred_from = Column(String(255), nullable=True)  # How learner found the program
    notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    user = relationship("User", backref="literacy_learner")
    program = relationship("Program", backref="literacy_learners")
    assessments = relationship(
        "LiteracyAssessmentRecord",
        back_populates="learner",
        cascade="all, delete-orphan"
    )
    sessions = relationship(
        "LiteracySessionLog",
        back_populates="learner",
        cascade="all, delete-orphan"
    )
    goals = relationship(
        "LiteracyGoal",
        back_populates="learner",
        cascade="all, delete-orphan"
    )
    progress_records = relationship(
        "LiteracyProgress",
        back_populates="learner",
        cascade="all, delete-orphan"
    )
    matches = relationship(
        "LiteracyTutorMatch",
        back_populates="learner",
        cascade="all, delete-orphan",
        foreign_keys="LiteracyTutorMatch.learner_id"
    )
    resource_recommendations = relationship(
        "LiteracyResourceRecommendation",
        back_populates="learner",
        cascade="all, delete-orphan"
    )
    # referrals relationship removed — LiteracyLearnerReferral class does not exist
    outcomes = relationship(
        "LiteracyOutcome",
        back_populates="learner",
        cascade="all, delete-orphan"
    )
    consent_records = relationship(
        "LiteracyConsentRecord",
        back_populates="learner",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_literacy_learners_program_status", program_id, status),
        Index("idx_literacy_learners_user_program", user_id, program_id, unique=True),
        UniqueConstraint("user_id", "program_id", name="uq_literacy_learner_user_program"),
    )


class LiteracyAssessmentRecord(Base, TimestampMixin):
    __tablename__ = "literacy_assessments"

    id = Column(Integer, primary_key=True, index=True)
    learner_id = Column(Integer, ForeignKey("literacy_learners.id", ondelete="CASCADE"), nullable=False, index=True)
    assessor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # ==================== ASSESSMENT DETAILS ====================
    assessment_type = Column(
        String(50),
        nullable=False,
        index=True
    )
    assessment_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    # ==================== ASSESSMENT RESULTS ====================
    score = Column(Numeric(5, 2), nullable=False)  # Raw score
    percentage = Column(Numeric(5, 2), nullable=True)  # Percentage score
    level = Column(
        String(50),
        nullable=False
    )
    reading_speed_wpm = Column(Integer, nullable=True)  # Words per minute
    comprehension_percentage = Column(Numeric(5, 2), nullable=True)

    # ==================== ASSESSMENT CONTEXT ====================
    assessment_tool_used = Column(String(255), nullable=True)  # Name of assessment (TABE, BEST, etc.)
    location = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    # ==================== PROGRESSION ====================
    level_progression = Column(String(50), nullable=True)  # "improved", "maintained", "regressed"
    recommended_next_level = Column(
        String(50),
        nullable=True
    )

    # ==================== RELATIONSHIPS ====================
    learner = relationship("LiteracyLearner", back_populates="assessments")
    assessor = relationship("User", backref="literacy_assessments_conducted")

    __table_args__ = (
        Index("idx_literacy_assessment_learner_date", learner_id, assessment_date),
        Index("idx_literacy_assessment_learner_type", learner_id, assessment_type),
    )


class LiteracyGoal(Base, TimestampMixin):
    __tablename__ = "literacy_goals"

    id = Column(Integer, primary_key=True, index=True)
    learner_id = Column(Integer, ForeignKey("literacy_learners.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== GOAL DEFINITION ====================
    goal_type = Column(
        String(50),
        nullable=False,
        index=True
    )
    goal_statement = Column(Text, nullable=False)  # SMART goal description
    target_level = Column(
        String(50),
        nullable=True
    )

    # ==================== TIMELINE ====================
    target_date = Column(Date, nullable=False)
    status = Column(
        String(50),
        default=GoalStatus.ACTIVE,
        nullable=False,
        index=True
    )
    completed_date = Column(DateTime(timezone=True), nullable=True)

    # ==================== PROGRESS TRACKING ====================
    progress_percentage = Column(Integer, default=0, nullable=False)  # 0-100
    notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    learner = relationship("LiteracyLearner", back_populates="goals")
    milestones = relationship(
        "LiteracyMilestone",
        back_populates="goal",
        cascade="all, delete-orphan"
    )
    celebrations = relationship(
        "LiteracyCelebration",
        back_populates="goal",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_literacy_goals_learner_status", learner_id, status),
        Index("idx_literacy_goals_target_date", target_date),
    )


class LiteracyMilestone(Base, TimestampMixin):
    __tablename__ = "literacy_milestones"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("literacy_goals.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== MILESTONE DETAILS ====================
    description = Column(Text, nullable=False)
    target_date = Column(Date, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_date = Column(DateTime(timezone=True), nullable=True)

    # ==================== TRACKING ====================
    notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    goal = relationship("LiteracyGoal", back_populates="milestones")


class LiteracyCelebration(Base, TimestampMixin):
    __tablename__ = "literacy_celebrations"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("literacy_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    learner_id = Column(Integer, ForeignKey("literacy_learners.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== CELEBRATION DETAILS ====================
    achievement_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    celebration_type = Column(String(100), nullable=True)  # "milestone_reached", "level_up", etc.
    celebration_notes = Column(Text, nullable=True)
    recognition_method = Column(String(255), nullable=True)  # "certificate", "public_announcement", etc.

    # ==================== RELATIONSHIPS ====================
    goal = relationship("LiteracyGoal", back_populates="celebrations")
    learner = relationship("LiteracyLearner")


class LiteracyProgress(Base, TimestampMixin):
    __tablename__ = "literacy_progress"

    id = Column(Integer, primary_key=True, index=True)
    learner_id = Column(Integer, ForeignKey("literacy_learners.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== PERIOD TRACKING ====================
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # ==================== SESSION ACTIVITY ====================
    sessions_scheduled = Column(Integer, default=0, nullable=False)
    sessions_completed = Column(Integer, default=0, nullable=False)
    sessions_missed = Column(Integer, default=0, nullable=False)
    total_hours = Column(Numeric(8, 2), default=0, nullable=False)

    # ==================== READING ACTIVITY ====================
    books_read = Column(Integer, default=0, nullable=False)
    pages_read = Column(Integer, default=0, nullable=False)

    # ==================== SKILL DEVELOPMENT ====================
    assessment_completed = Column(Boolean, default=False, nullable=False)
    new_level_achieved = Column(Boolean, default=False, nullable=False)

    # ==================== ENGAGEMENT METRICS ====================
    attendance_rate = Column(Numeric(5, 2), nullable=True)  # Percentage
    skills_improved = Column(Text, nullable=True)  # Comma-separated list
    next_level_readiness = Column(Numeric(5, 2), nullable=True)  # Percentage confidence

    # ==================== RELATIONSHIPS ====================
    learner = relationship("LiteracyLearner", back_populates="progress_records")

    __table_args__ = (
        Index("idx_literacy_progress_learner_period", learner_id, period_start),
        UniqueConstraint("learner_id", "period_start", "period_end", name="uq_literacy_progress_period"),
    )
