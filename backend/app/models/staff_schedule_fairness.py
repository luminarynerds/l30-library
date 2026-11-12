# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import Enum, StrEnum
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer,
    Numeric, String, Text, Time, UniqueConstraint, Index, JSON, and_,
    Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


# =============================================================================
# ENUMS
# =============================================================================

class FairnessShiftType(StrEnum):
    OPENING = "opening"          # Early shift, opens branch
    CLOSING = "closing"          # Late shift, closes branch
    MIDDAY = "midday"            # Middle shift, 10am-3pm typically
    EVENING = "evening"          # Late afternoon/evening
    FULL_DAY = "full_day"        # Entire day coverage
    SPECIAL_EVENT = "special_event"  # Event coverage


class ShiftStatus(StrEnum):
    UNSCHEDULED = "unscheduled"
    ASSIGNED = "assigned"
    CONFIRMED = "confirmed"
    CALLED_OUT = "called_out"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PreferenceType(StrEnum):
    PREFERRED = "preferred"      # Staff wants this
    ACCEPTABLE = "acceptable"    # Staff can do this
    UNAVAILABLE = "unavailable"  # Staff cannot work


class FairnessPolicyType(StrEnum):
    WEEKEND_ROTATION = "weekend_rotation"
    HOLIDAY_ROTATION = "holiday_rotation"
    SHIFT_DISTRIBUTION = "shift_distribution"
    OVERTIME_EQUITY = "overtime_equity"
    CONSECUTIVE_DAYS_OFF = "consecutive_days_off"
    CLOPENING_PREVENTION = "clopening_prevention"
    MAX_HOURS_PER_WEEK = "max_hours_per_week"
    MIN_HOURS_GUARANTEED = "min_hours_guaranteed"
    SENIORITY_CONSIDERATION = "seniority_consideration"


class ViolationType(StrEnum):
    HARD_VIOLATION = "hard_violation"    # Must not occur
    SOFT_VIOLATION = "soft_violation"    # Undesirable, minimize
    WARNING = "warning"                  # Informational alert


# =============================================================================
# MODELS
# =============================================================================

class StaffShift(Base):
    __tablename__ = "staff_shifts"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Shift details
    shift_date = Column(Date, nullable=False, index=True)
    shift_type = Column(SQLEnum(FairnessShiftType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    status = Column(SQLEnum(ShiftStatus, values_callable=lambda x: [e.value for e in x]), default=ShiftStatus.UNSCHEDULED, nullable=False)

    # Time tracking
    scheduled_start = Column(Time, nullable=False)
    scheduled_end = Column(Time, nullable=False)
    actual_start = Column(Time, nullable=True)
    actual_end = Column(Time, nullable=True)

    # Hours and compensation
    scheduled_hours = Column(Float, nullable=False)  # Decimal hours
    actual_hours = Column(Float, nullable=True)
    is_overtime = Column(Boolean, default=False, nullable=False)

    # Special flags
    is_holiday = Column(Boolean, default=False, nullable=False)
    is_weekend = Column(Boolean, default=False, nullable=False)

    # Notes and tracking
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # DISABLED: # DISABLED: branch relationship
    staff = relationship("User", backref="staff_shifts")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_staff_shifts_branch_date", "branch_id", "shift_date"),
        Index("ix_staff_shifts_staff_date", "staff_id", "shift_date"),
        Index("ix_staff_shifts_status_date", "status", "shift_date"),
    )


class ShiftPreference(Base):
    __tablename__ = "shift_preferences"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(Integer, nullable=True, index=True)  # Null = all branches

    # Preference details
    day_of_week = Column(String(20), nullable=True)  # monday-sunday, null = all days
    shift_type = Column(SQLEnum(FairnessShiftType, values_callable=lambda x: [e.value for e in x]), nullable=True)  # null = all shifts
    preference_type = Column(SQLEnum(PreferenceType, values_callable=lambda x: [e.value for e in x]), nullable=False)

    # Time preferences
    preferred_start_time = Column(Time, nullable=True)
    preferred_end_time = Column(Time, nullable=True)

    # Notes about the preference
    reason = Column(String(500), nullable=True)

    # Validity period
    effective_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # Null = ongoing, server_default=func.now(), nullable=False), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    staff = relationship("User", backref="shift_preferences")
    # DISABLED: # DISABLED: branch relationship

    __table_args__ = (
        Index("ix_shift_preferences_staff_date", "staff_id", "effective_date"),
        Index("ix_shift_preferences_branch", "branch_id"),
    )


class FairnessPolicy(Base):
    __tablename__ = "fairness_policies"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, nullable=True, index=True)  # Null = system-wide

    # Policy details
    policy_type = Column(SQLEnum(FairnessPolicyType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # Configuration as JSON
    # Examples:
    # {"max_hours": 40, "week_definition": "monday-sunday"}
    # {"min_consecutive_days": 2}
    # {"max_weekend_shifts_per_quarter": 12}
    config = Column(JSON, nullable=False, server_default="{}")

    # Enforcement
    is_active = Column(Boolean, default=True, nullable=False)
    violation_type = Column(SQLEnum(ViolationType, values_callable=lambda x: [e.value for e in x]), nullable=False)

    # Dates
    effective_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # Null = ongoing, server_default=func.now(), nullable=False), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # DISABLED: # DISABLED: branch relationship

    __table_args__ = (
        Index("ix_fairness_policies_type_branch", "policy_type", "branch_id"),
        Index("ix_fairness_policies_active", "is_active", "effective_date"),
    )


class PolicyException(Base):
    __tablename__ = "policy_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("fairness_policies.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Exception details
    reason = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Scope
    affected_date = Column(Date, nullable=False)
    affected_shift_id = Column(Integer, ForeignKey("staff_shifts.id", ondelete="SET NULL"), nullable=True)

    # Approval workflow
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Status
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Validity
    valid_from = Column(Date, nullable=False)
    valid_until = Column(Date, nullable=False)

    # Tracking, server_default=func.now(), nullable=False), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    policy = relationship("FairnessPolicy", backref="exceptions")
    staff = relationship("User", foreign_keys=[staff_id], backref="policy_exceptions")
    created_by = relationship("User", foreign_keys=[created_by_id], backref="exceptions_created")
    approved_by = relationship("User", foreign_keys=[approved_by_id], backref="exceptions_approved")
    affected_shift = relationship("StaffShift", backref="policy_exceptions")

    __table_args__ = (
        Index("ix_policy_exceptions_staff_date", "staff_id", "affected_date"),
        Index("ix_policy_exceptions_status", "is_approved"),
    )


class ShiftConstraintViolation(Base):
    __tablename__ = "shift_constraint_violations"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey("fairness_policies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Violation details
    violation_type = Column(SQLEnum(ViolationType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    description = Column(Text, nullable=False)

    # Affected shift(s)
    affected_shift_id = Column(Integer, ForeignKey("staff_shifts.id", ondelete="SET NULL"), nullable=True)
    affected_date = Column(Date, nullable=False, index=True)

    # Severity and metrics
    severity_score = Column(Float, default=1.0, nullable=False)  # 0.0-10.0

    # Status
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Tracking
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # DISABLED: # DISABLED: branch relationship
    staff = relationship("User", backref="constraint_violations")
    policy = relationship("FairnessPolicy", backref="violations")
    affected_shift = relationship("StaffShift", backref="constraint_violations")

    __table_args__ = (
        Index("ix_violations_staff_date", "staff_id", "affected_date"),
        Index("ix_violations_type", "violation_type"),
        Index("ix_violations_resolved", "is_resolved"),
    )


class ScheduleBalanceMetrics(Base):
    __tablename__ = "schedule_balance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(Integer, nullable=True, index=True)

    # Time period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Hours metrics
    total_hours_scheduled = Column(Float, nullable=False)
    total_hours_worked = Column(Float, nullable=False)
    total_overtime_hours = Column(Float, nullable=False)

    # Shift type distribution
    opening_shifts = Column(Integer, default=0, nullable=False)
    closing_shifts = Column(Integer, default=0, nullable=False)
    midday_shifts = Column(Integer, default=0, nullable=False)
    evening_shifts = Column(Integer, default=0, nullable=False)

    # Weekend and holiday distribution
    weekend_shifts = Column(Integer, default=0, nullable=False)
    holiday_shifts = Column(Integer, default=0, nullable=False)

    # Consecutive days
    max_consecutive_days_worked = Column(Integer, default=0, nullable=False)
    min_consecutive_days_off = Column(Integer, default=0, nullable=False)

    # Clopening (close then open) violations
    clopening_count = Column(Integer, default=0, nullable=False)

    # Fairness scores (0-100, higher = more fair)
    hours_fairness_score = Column(Float, default=100.0, nullable=False)
    shift_type_fairness_score = Column(Float, default=100.0, nullable=False)
    weekend_fairness_score = Column(Float, default=100.0, nullable=False)
    holiday_fairness_score = Column(Float, default=100.0, nullable=False)
    overall_fairness_score = Column(Float, default=100.0, nullable=False)

    # Comparison to team average
    hours_vs_average = Column(Float, nullable=False)  # Actual - average

    # Metrics calculated
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    staff = relationship("User", backref="schedule_metrics")
    # DISABLED: # DISABLED: branch relationship

    __table_args__ = (
        Index("ix_metrics_staff_period", "staff_id", "period_start", "period_end"),
        UniqueConstraint("staff_id", "branch_id", "period_start", "period_end", name="uq_metrics_staff_branch_period"),
    )
