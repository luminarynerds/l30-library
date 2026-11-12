# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum, StrEnum
from datetime import datetime, date

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SQLEnum, ForeignKey,
    Integer, String, Text, Index, Numeric
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


class OutcomeType(StrEnum):
    GED_PASSED = "ged_passed"
    GED_FAILED = "ged_failed"
    HIGH_SCHOOL_EQUIVALENT = "high_school_equivalent"
    EMPLOYMENT_GAINED = "employment_gained"
    EMPLOYMENT_PROMOTED = "employment_promoted"
    COLLEGE_ACCEPTANCE = "college_acceptance"
    CERTIFICATION_EARNED = "certification_earned"
    LEVEL_ADVANCEMENT = "level_advancement"
    GOAL_COMPLETED = "goal_completed"
    PROGRAM_COMPLETION = "program_completion"
    FAMILY_LITERACY = "family_literacy"


class OutcomeCategory(StrEnum):
    EDUCATIONAL = "educational"  # GED, certification, etc.
    EMPLOYMENT = "employment"  # Job-related outcomes
    PERSONAL_DEVELOPMENT = "personal_development"
    FAMILY = "family"
    COMMUNITY = "community"


class ReportingPeriod(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"


class LiteracyOutcome(Base, TimestampMixin):
    __tablename__ = "literacy_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    learner_id = Column(Integer, ForeignKey("literacy_learners.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== OUTCOME DETAILS ====================
    outcome_type = Column(
        String(50),
        nullable=False,
        index=True
    )
    outcome_category = Column(
        String(50),
        nullable=True
    )
    outcome_date = Column(Date, nullable=False, index=True)

    # ==================== OUTCOME SPECIFICS ====================
    # For GED outcomes
    ged_score = Column(Integer, nullable=True)  # Total score
    ged_passed = Column(Boolean, nullable=True)  # True/False/null
    ged_subject_scores = Column(Text, nullable=True)  # JSON with individual scores

    # For employment outcomes
    employment_job_title = Column(String(255), nullable=True)
    employment_employer = Column(String(255), nullable=True)
    employment_start_date = Column(Date, nullable=True)

    # For educational advancement
    education_institution = Column(String(255), nullable=True)
    education_program = Column(String(255), nullable=True)
    education_expected_completion = Column(Date, nullable=True)

    # For certifications
    certification_name = Column(String(255), nullable=True)
    certification_issuer = Column(String(255), nullable=True)

    # ==================== VERIFICATION ====================
    is_verified = Column(Boolean, default=False)
    verification_method = Column(String(100), nullable=True)  # "self_reported", "partner_confirmation", "official_record"
    verification_date = Column(DateTime(timezone=True), nullable=True)
    verified_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # ==================== DOCUMENTATION ====================
    details = Column(Text, nullable=True)
    evidence_url = Column(Text, nullable=True)  # Link to proof/documentation
    notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    learner = relationship("LiteracyLearner", back_populates="outcomes")
    verified_by_user = relationship("User", backref="literacy_outcomes_verified")

    __table_args__ = (
        Index("idx_literacy_outcome_learner_type", learner_id, outcome_type),
        Index("idx_literacy_outcome_date", outcome_date),
    )


class LiteracyProgramOutcomeMetrics(Base, TimestampMixin):
    __tablename__ = "literacy_impact_metrics"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== REPORTING PERIOD ====================
    period_type = Column(
        String(50),
        nullable=False
    )
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # ==================== PARTICIPATION METRICS ====================
    learners_served = Column(Integer, default=0, nullable=False)
    new_learners_enrolled = Column(Integer, default=0, nullable=False)
    learners_completed_program = Column(Integer, default=0, nullable=False)

    # ==================== SERVICE DELIVERY ====================
    total_sessions_offered = Column(Integer, default=0, nullable=False)
    total_sessions_completed = Column(Integer, default=0, nullable=False)
    total_tutor_hours = Column(Numeric(10, 2), default=0, nullable=False)
    average_hours_per_learner = Column(Numeric(8, 2), nullable=True)

    # ==================== OUTCOMES ====================
    ged_completions = Column(Integer, default=0, nullable=False)
    level_advancements = Column(Integer, default=0, nullable=False)
    employment_outcomes = Column(Integer, default=0, nullable=False)
    college_acceptances = Column(Integer, default=0, nullable=False)
    certifications_earned = Column(Integer, default=0, nullable=False)

    # ==================== EFFECTIVENESS METRICS ====================
    average_improvement = Column(Numeric(5, 2), nullable=True)  # Percentage improvement
    retention_rate = Column(Numeric(5, 2), nullable=True)  # Percentage retained
    goal_achievement_rate = Column(Numeric(5, 2), nullable=True)  # Percentage meeting goals
    satisfaction_rating = Column(Numeric(3, 2), nullable=True)  # 1-5 scale average

    # ==================== DEMOGRAPHICS ====================
    avg_learner_age = Column(Integer, nullable=True)
    percent_first_generation = Column(Numeric(5, 2), nullable=True)
    percent_esl = Column(Numeric(5, 2), nullable=True)

    # ==================== NOTES ====================
    notes = Column(Text, nullable=True)
    data_quality_notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    program = relationship("Program", backref="literacy_impact_metrics")

    __table_args__ = (
        Index("idx_literacy_metrics_program_period", program_id, period_start, period_end),
    )


class LiteracyCohort(Base, TimestampMixin):
    __tablename__ = "literacy_cohorts"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== COHORT IDENTIFICATION ====================
    cohort_name = Column(String(255), nullable=False)
    cohort_code = Column(String(50), nullable=True, unique=True)  # e.g., "2024-SPRING-A"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    # ==================== COHORT CHARACTERISTICS ====================
    target_enrollment = Column(Integer, nullable=True)
    actual_enrollment = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=True)

    # ==================== NOTES ====================
    notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    program = relationship("Program", backref="literacy_cohorts")
    learner_cohort_links = relationship(
        "LiteracyLearnerCohort",
        back_populates="cohort",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_literacy_cohort_program_start", program_id, start_date),
    )


class LiteracyLearnerCohort(Base):
    __tablename__ = "literacy_learner_cohorts"

    id = Column(Integer, primary_key=True, index=True)
    learner_id = Column(Integer, ForeignKey("literacy_learners.id", ondelete="CASCADE"), nullable=False, index=True)
    cohort_id = Column(Integer, ForeignKey("literacy_cohorts.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # ==================== RELATIONSHIPS ====================
    learner = relationship("LiteracyLearner", backref="cohort_memberships")
    cohort = relationship("LiteracyCohort", back_populates="learner_cohort_links")

    __table_args__ = (
        Index("idx_literacy_learner_cohort", learner_id, cohort_id, unique=True),
    )
