# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import Enum, StrEnum
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, Float, ForeignKey,
    Integer, Numeric, String, Text, Time, UniqueConstraint, Index, JSON,
    Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


# =============================================================================
# ENUMS
# =============================================================================

class ScheduleGenerationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    TIMEOUT = "timeout"
    FAILED = "failed"


class ScheduleExplanationType(StrEnum):
    PREFERENCE_HONORED = "preference_honored"
    COVERAGE_REQUIRED = "coverage_required"
    FAIRNESS_BALANCE = "fairness_balance"
    SKILL_MATCH = "skill_match"
    SENIORITY = "seniority"
    AVAILABILITY = "availability"
    CALLOUT_COVERAGE = "callout_coverage"
    SWAP_RESULT = "swap_result"
    CONSTRAINT_FORCED = "constraint_forced"


class FatigueLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class CalloutStatus(StrEnum):
    OPEN = "open"
    SEARCHING = "searching"
    COVERED = "covered"
    PARTIAL = "partial"
    UNCOVERED = "uncovered"
    CANCELLED = "cancelled"


class CalloutUrgency(StrEnum):
    LOW = "low"           # >48 hours notice
    MEDIUM = "medium"     # 24-48 hours notice
    HIGH = "high"         # 4-24 hours notice
    EMERGENCY = "emergency"  # <4 hours notice


class PayrollExportStatus(StrEnum):
    PENDING = "pending"
    EXPORTED = "exported"
    CONFIRMED = "confirmed"
    ERROR = "error"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    TEMPORARY = "temporary"
    SEASONAL = "seasonal"


# =============================================================================
# CONSTRAINT SOLVER MODELS
# =============================================================================

class ScheduleGeneration(Base):
    __tablename__ = "schedule_generations"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, nullable=False, index=True)
    generated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Schedule period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Solver configuration
    status = Column(SQLEnum(ScheduleGenerationStatus, values_callable=lambda x: [e.value for e in x]), default=ScheduleGenerationStatus.PENDING, nullable=False)
    solver_config = Column(JSON, nullable=False, server_default="{}")
    # Example config:
    # {
    #   "max_solve_time_seconds": 120,
    #   "preference_weight": 0.3,
    #   "fairness_weight": 0.4,
    #   "coverage_weight": 0.3,
    #   "min_staff_per_shift": 2,
    #   "skills_required": {"opening": ["cash_register", "alarm_codes"]}
    # }

    # Solver results
    objective_value = Column(Float, nullable=True)
    solve_time_seconds = Column(Float, nullable=True)
    total_shifts_assigned = Column(Integer, default=0, nullable=False)
    total_violations = Column(Integer, default=0, nullable=False)
    fairness_score = Column(Float, nullable=True)

    # Constraint satisfaction summary (JSON)
    constraint_summary = Column(JSON, nullable=True)
    # Example:
    # {
    #   "hard_constraints_met": 45,
    #   "hard_constraints_total": 45,
    #   "soft_constraints_met": 38,
    #   "soft_constraints_total": 42,
    #   "preferences_honored": 0.82,
    #   "coverage_gaps": 0
    # }

    # Approval workflow
    is_published = Column(Boolean, default=False, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # DISABLED: # DISABLED: branch relationship
    generated_by = relationship("User", foreign_keys=[generated_by_id], backref="schedule_generations")
    published_by = relationship("User", foreign_keys=[published_by_id])

    __table_args__ = (
        Index("ix_schedule_generations_branch_period", "branch_id", "period_start", "period_end"),
        Index("ix_schedule_generations_status", "status"),
    )


# =============================================================================
# SCHEDULE TRANSPARENCY / EXPLANATIONS
# =============================================================================

class ScheduleExplanation(Base):
    __tablename__ = "schedule_explanations"

    id = Column(Integer, primary_key=True, index=True)
    generation_id = Column(Integer, ForeignKey("schedule_generations.id", ondelete="CASCADE"), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("staff_shifts.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Explanation
    explanation_type = Column(SQLEnum(ScheduleExplanationType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    explanation_text = Column(Text, nullable=False)

    # Factors that contributed to this assignment (JSON)
    contributing_factors = Column(JSON, nullable=False, server_default="[]")
    # Example:
    # [
    #   {"factor": "preference_match", "weight": 0.3, "score": 0.9, "detail": "Preferred morning shifts"},
    #   {"factor": "fairness_balance", "weight": 0.4, "score": 0.7, "detail": "Below avg weekend shifts"},
    #   {"factor": "skill_match", "weight": 0.2, "score": 1.0, "detail": "Has cash register cert"},
    #   {"factor": "availability", "weight": 0.1, "score": 1.0, "detail": "Marked available Mon AM"}
    # ]

    # Impact on fairness score
    fairness_impact = Column(Float, default=0.0, nullable=False)

    # Relationships
    generation = relationship("ScheduleGeneration", backref="explanations")
    shift = relationship("StaffShift", backref="schedule_explanations")
    staff = relationship("User", backref="schedule_explanations")

    __table_args__ = (
        Index("ix_schedule_explanations_staff", "staff_id", "generation_id"),
    )


# =============================================================================
# PREFERENCE LEARNING
# =============================================================================

class LearnedPreference(Base):
    __tablename__ = "learned_preferences"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # What was learned
    preference_category = Column(String(50), nullable=False)  # day_of_week, shift_type, time_range, branch
    preference_value = Column(String(100), nullable=False)     # e.g. "monday", "opening", "08:00-12:00"
    preference_strength = Column(Float, nullable=False)        # -1.0 (strong dislike) to 1.0 (strong like)
    confidence = Column(Float, nullable=False)                 # 0.0 to 1.0

    # Evidence supporting this preference
    evidence = Column(JSON, nullable=False, server_default="[]")
    # Example:
    # [
    #   {"type": "swap_away", "count": 5, "detail": "Traded away 5 Monday closing shifts"},
    #   {"type": "swap_seek", "count": 3, "detail": "Sought 3 Tuesday opening shifts"},
    #   {"type": "callout", "count": 2, "detail": "Called out on 2 Friday evenings"},
    #   {"type": "explicit", "count": 1, "detail": "Stated preference for mornings"}
    # ]

    # Data window
    data_start_date = Column(Date, nullable=False)
    data_end_date = Column(Date, nullable=False)
    sample_size = Column(Integer, nullable=False)  # Number of data points

    # Whether staff confirmed or overrode this learned preference
    is_confirmed = Column(Boolean, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    staff = relationship("User", backref="learned_preferences")

    __table_args__ = (
        Index("ix_learned_preferences_staff_cat", "staff_id", "preference_category"),
        UniqueConstraint(
            "staff_id", "preference_category", "preference_value",
            name="uq_learned_pref_staff_cat_val"
        ),
    )


# =============================================================================
# EXHAUSTION / FATIGUE TRACKING
# =============================================================================

class StaffFatigueRecord(Base):
    __tablename__ = "staff_fatigue_records"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    record_date = Column(Date, nullable=False, index=True)

    # Fatigue assessment
    fatigue_level = Column(SQLEnum(FatigueLevel, values_callable=lambda x: [e.value for e in x]), nullable=False)
    fatigue_score = Column(Float, nullable=False)  # 0-100, higher = more fatigued

    # Contributing metrics
    consecutive_days_worked = Column(Integer, default=0, nullable=False)
    hours_last_7_days = Column(Float, default=0.0, nullable=False)
    hours_last_14_days = Column(Float, default=0.0, nullable=False)
    closing_shifts_last_7_days = Column(Integer, default=0, nullable=False)
    short_turnarounds_last_14_days = Column(Integer, default=0, nullable=False)  # <10hr gaps
    overtime_hours_last_30_days = Column(Float, default=0.0, nullable=False)
    days_since_last_day_off = Column(Integer, default=0, nullable=False)
    weekend_shifts_last_30_days = Column(Integer, default=0, nullable=False)

    # Trend
    fatigue_trend = Column(String(20), nullable=True)  # increasing, stable, decreasing

    # Alerts
    alert_triggered = Column(Boolean, default=False, nullable=False)
    alert_message = Column(Text, nullable=True)

    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    staff = relationship("User", backref="fatigue_records")

    __table_args__ = (
        Index("ix_staff_fatigue_staff_date", "staff_id", "record_date"),
        UniqueConstraint("staff_id", "record_date", name="uq_fatigue_staff_date"),
    )


# =============================================================================
# CALL-OUT COVERAGE
# =============================================================================

class CalloutCoverageRequest(Base):
    __tablename__ = "callout_coverage_requests"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, nullable=False, index=True)
    original_shift_id = Column(Integer, ForeignKey("staff_shifts.id", ondelete="CASCADE"), nullable=False)
    callout_staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Callout details
    callout_reason = Column(String(200), nullable=True)
    callout_time = Column(DateTime(timezone=True), nullable=False)
    shift_date = Column(Date, nullable=False, index=True)
    shift_start = Column(Time, nullable=False)
    shift_end = Column(Time, nullable=False)

    # Status and urgency
    status = Column(SQLEnum(CalloutStatus, values_callable=lambda x: [e.value for e in x]), default=CalloutStatus.OPEN, nullable=False)
    urgency = Column(SQLEnum(CalloutUrgency, values_callable=lambda x: [e.value for e in x]), nullable=False)

    # Coverage search
    staff_contacted = Column(JSON, nullable=False, server_default="[]")
    # [{"staff_id": 5, "contacted_at": "...", "response": "declined", "reason": "unavailable"}]

    staff_contacted_count = Column(Integer, default=0, nullable=False)
    auto_match_attempted = Column(Boolean, default=False, nullable=False)

    # Resolution
    covering_staff_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    covering_shift_id = Column(Integer, ForeignKey("staff_shifts.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Manager handling
    handled_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # DISABLED: # DISABLED: branch relationship
    original_shift = relationship("StaffShift", foreign_keys=[original_shift_id], backref="callout_request")
    callout_staff = relationship("User", foreign_keys=[callout_staff_id], backref="callouts_made")
    covering_staff = relationship("User", foreign_keys=[covering_staff_id], backref="callouts_covered")
    covering_shift = relationship("StaffShift", foreign_keys=[covering_shift_id])
    handled_by = relationship("User", foreign_keys=[handled_by_id])

    __table_args__ = (
        Index("ix_callout_coverage_branch_date", "branch_id", "shift_date"),
        Index("ix_callout_coverage_status", "status"),
    )


# =============================================================================
# PAYROLL INTEGRATION
# =============================================================================

class PayrollRecord(Base):
    __tablename__ = "payroll_records"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("staff_shifts.id", ondelete="CASCADE"), nullable=False, index=True)

    # Pay period
    pay_period_start = Column(Date, nullable=False, index=True)
    pay_period_end = Column(Date, nullable=False)

    # Hours breakdown
    regular_hours = Column(Float, default=0.0, nullable=False)
    overtime_hours = Column(Float, default=0.0, nullable=False)
    holiday_hours = Column(Float, default=0.0, nullable=False)
    weekend_differential_hours = Column(Float, default=0.0, nullable=False)
    evening_differential_hours = Column(Float, default=0.0, nullable=False)

    # Rate multipliers
    overtime_multiplier = Column(Float, default=1.5, nullable=False)
    holiday_multiplier = Column(Float, default=2.0, nullable=False)
    weekend_differential = Column(Float, default=1.1, nullable=False)
    evening_differential = Column(Float, default=1.15, nullable=False)

    # Export tracking
    export_status = Column(SQLEnum(PayrollExportStatus, values_callable=lambda x: [e.value for e in x]), default=PayrollExportStatus.PENDING, nullable=False)
    exported_at = Column(DateTime(timezone=True), nullable=True)
    export_batch_id = Column(String(100), nullable=True)
    payroll_system_ref = Column(String(200), nullable=True)

    # Discrepancy tracking
    scheduled_hours = Column(Float, nullable=False)
    actual_hours = Column(Float, nullable=True)

    # Pay rate snapshot + computed pay (populated by payroll_integration_service)
    hourly_rate_at_pay = Column(Numeric(10, 2), nullable=True)
    regular_pay = Column(Numeric(10, 2), nullable=True)
    overtime_pay = Column(Numeric(10, 2), nullable=True)
    holiday_pay = Column(Numeric(10, 2), nullable=True)
    weekend_differential_pay = Column(Numeric(10, 2), nullable=True)
    evening_differential_pay = Column(Numeric(10, 2), nullable=True)
    total_pay = Column(Numeric(10, 2), nullable=True)

    discrepancy_notes = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    staff = relationship("User", foreign_keys=[staff_id], backref="payroll_records")
    shift = relationship("StaffShift", backref="payroll_record")
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        Index("ix_payroll_staff_period", "staff_id", "pay_period_start"),
        Index("ix_payroll_export_status", "export_status"),
        UniqueConstraint("staff_id", "shift_id", name="uq_payroll_staff_shift"),
    )


class PayrollPolicy(Base):
    """Single-row, admin-edited pay policy. Generated PayrollRecords stamp the
    values used at generation time, so editing this never rewrites history."""
    __tablename__ = "payroll_policy"

    id = Column(Integer, primary_key=True, default=1)
    overtime_multiplier = Column(Numeric(4, 2), nullable=False, default=Decimal("1.50"), server_default="1.50")
    holiday_multiplier = Column(Numeric(4, 2), nullable=False, default=Decimal("2.00"), server_default="2.00")
    weekend_differential = Column(Numeric(4, 2), nullable=False, default=Decimal("1.10"), server_default="1.10")
    evening_differential = Column(Numeric(4, 2), nullable=False, default=Decimal("1.15"), server_default="1.15")
    default_ot_threshold_hours = Column(Numeric(4, 1), nullable=False, default=Decimal("40.0"), server_default="40.0")
    evening_start_local = Column(Time, nullable=False, default=time(18, 0), server_default="18:00:00")

    # Audit: who last touched the policy. Per-record multiplier stamps are the
    # history; this row only carries the current values.
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    updated_by = relationship("User", foreign_keys=[updated_by_id])

    __table_args__ = (
        CheckConstraint("id = 1", name="ck_payroll_policy_single_row"),
    )


class PayrollExportBatch(Base):
    __tablename__ = "payroll_export_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(100), unique=True, nullable=False, index=True)
    branch_id = Column(Integer, nullable=True)

    pay_period_start = Column(Date, nullable=False)
    pay_period_end = Column(Date, nullable=False)

    total_records = Column(Integer, default=0, nullable=False)
    total_regular_hours = Column(Float, default=0.0, nullable=False)
    total_overtime_hours = Column(Float, default=0.0, nullable=False)
    total_holiday_hours = Column(Float, default=0.0, nullable=False)

    export_status = Column(SQLEnum(PayrollExportStatus, values_callable=lambda x: [e.value for e in x]), default=PayrollExportStatus.PENDING, nullable=False)
    export_format = Column(String(50), default="csv", nullable=False)  # csv, json, adp, paychex
    exported_at = Column(DateTime(timezone=True), nullable=True)
    exported_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    error_message = Column(Text, nullable=True)

    # Relationships
    # DISABLED: # DISABLED: branch relationship
    exported_by = relationship("User", foreign_keys=[exported_by_id])

    __table_args__ = (
        Index("ix_payroll_batch_period", "pay_period_start", "pay_period_end"),
    )


# =============================================================================
# STAFF EMPLOYMENT PROFILE (for PT/FT balance)
# =============================================================================

class StaffSchedulingProfile(Base):
    __tablename__ = "staff_scheduling_profiles"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    branch_id = Column(Integer, nullable=True)

    # Employment classification
    employment_type = Column(SQLEnum(EmploymentType, values_callable=lambda x: [e.value for e in x]), nullable=False)

    # Contracted hours
    contracted_hours_per_week = Column(Float, nullable=False)
    min_hours_per_week = Column(Float, nullable=False)
    max_hours_per_week = Column(Float, nullable=False)

    # Skills and certifications (for constraint solver)
    skills = Column(JSON, nullable=False, server_default="[]")
    # ["cash_register", "reference_desk", "children_programs", "alarm_codes", "opening_procedures"]

    # Seniority (for preference priority)
    hire_date = Column(Date, nullable=True)
    seniority_level = Column(Integer, default=1, nullable=False)  # 1=newest, higher=more senior

    # Scheduling constraints
    max_consecutive_days = Column(Integer, default=5, nullable=False)
    min_hours_between_shifts = Column(Float, default=10.0, nullable=False)
    max_weekend_shifts_per_month = Column(Integer, default=4, nullable=False)
    max_closing_shifts_per_week = Column(Integer, default=3, nullable=False)

    # Desirable shift allocation tracking
    desirable_shift_score = Column(Float, default=50.0, nullable=False)  # 0-100, equity score

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    staff = relationship("User", backref="scheduling_profile", uselist=False)
    # DISABLED: # DISABLED: branch relationship

    __table_args__ = (
        Index("ix_scheduling_profile_employment", "employment_type"),
        Index("ix_scheduling_profile_active", "is_active"),
    )
