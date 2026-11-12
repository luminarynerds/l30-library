# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date
from enum import StrEnum
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, DateTime, Date, ForeignKey, Boolean, Text, Enum as SQLEnum, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PTORequestStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELLED = "cancelled"


class PTOType(StrEnum):
    VACATION = "vacation"
    SICK = "sick"
    PERSONAL = "personal"
    BEREAVEMENT = "bereavement"
    MEDICAL = "medical"
    JURY_DUTY = "jury_duty"


class PartialDayType(StrEnum):
    FULL_DAY = "full_day"
    MORNING_OFF = "morning_off"
    LEAVE_EARLY = "leave_early"


class PTORequest(Base):
    __tablename__ = "pto_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    pto_type = Column(SQLEnum(PTOType, values_callable=lambda x: [e.value for e in x]), default=PTOType.VACATION, nullable=False)
    status = Column(SQLEnum(PTORequestStatus, values_callable=lambda x: [e.value for e in x]), default=PTORequestStatus.DRAFT, nullable=False, index=True)

    # Partial day support
    partial_day_type = Column(SQLEnum(PartialDayType, values_callable=lambda x: [e.value for e in x]), default=PartialDayType.FULL_DAY, nullable=False)

    # Reason for PTO (optional but encouraged for planning)
    reason = Column(Text, nullable=True)

    # Documentation (for medical, bereavement, jury duty)
    documentation_url = Column(String(500), nullable=True)

    # Coverage planning
    coverage_notes = Column(Text, nullable=True, default="Coverage is manageable with team coordination")
    coverage_manager_assigned = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Delegate work items while away
    delegation_notes = Column(Text, nullable=True)
    auto_delegate = Column(Boolean, default=False)

    # Approval tracking
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approval_date = Column(DateTime, nullable=True)
    denial_reason = Column(Text, nullable=True)

    # Inbox management
    gradual_return_enabled = Column(Boolean, default=True)
    return_inbox_date = Column(Date, nullable=True)

    # Conflict tracking
    has_conflicts = Column(Boolean, default=False, index=True)
    conflict_checked_at = Column(DateTime, nullable=True)

    # Recurring request support
    is_recurring = Column(Boolean, default=False)
    recurring_parent_id = Column(Integer, ForeignKey("pto_requests.id", ondelete="SET NULL"), nullable=True)

    # Track created/updated, server_default=func.now(), nullable=False), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="pto_requests")
    coverage_manager = relationship("User", foreign_keys=[coverage_manager_assigned])
    approver = relationship("User", foreign_keys=[approved_by])

    # Number of days (calculated)
    @property
    def number_of_days(self) -> int:
        if not self.start_date or not self.end_date:
            return 0
        delta = self.end_date - self.start_date
        # For partial days, count as 0.5
        days = delta.days + 1
        if self.partial_day_type != PartialDayType.FULL_DAY:
            days -= 0.5
        return days


class PTOApproval(Base):
    __tablename__ = "pto_approvals"

    id = Column(Integer, primary_key=True, index=True)
    pto_request_id = Column(Integer, ForeignKey("pto_requests.id", ondelete="CASCADE"), nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(SQLEnum(PTORequestStatus, values_callable=lambda x: [e.value for e in x]), nullable=False)
    notes = Column(Text, nullable=True)
    coverage_assessment = Column(Text, nullable=True)

    # Relationships
    pto_request = relationship("PTORequest", backref="approvals")
    approver = relationship("User", foreign_keys=[approver_id])


class PTOBalance(Base):
    __tablename__ = "pto_balance"
    # One balance row per (user, PTO type, accrual year). The old unique=True on
    # user_id alone made the year-rollover in pto_service (and per-type balances)
    # impossible: the second row for the same user violated the index.
    __table_args__ = (
        UniqueConstraint("user_id", "pto_type", "year", name="uq_pto_balance_user_type_year"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    pto_type = Column(SQLEnum(PTOType, values_callable=lambda x: [e.value for e in x]), nullable=False)

    # Accrual tracking
    annual_allotment = Column(Float, default=0.0)  # Days per year
    accrued_days = Column(Float, default=0.0)  # Total accrued
    used_days = Column(Float, default=0.0)  # Days used
    pending_days = Column(Float, default=0.0)  # Days in pending requests
    carryover_days = Column(Float, default=0.0)  # Days carried over from previous year
    carryover_limit = Column(Float, default=5.0)  # Max carryover allowed

    # Dates
    year = Column(Integer, nullable=False)  # Calendar year for accrual
    last_accrual_date = Column(DateTime, nullable=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="pto_balance")


class PTOReminder(Base):
    __tablename__ = "pto_reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    pto_type = Column(SQLEnum(PTOType, values_callable=lambda x: [e.value for e in x]), nullable=False)

    # Reminder details
    days_available = Column(Float, nullable=False)
    reminder_type = Column(String(50), nullable=False)  # "balance_warning", "upcoming_expiry", "encouragement"
    message = Column(Text, nullable=False)

    # Tracking
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="pto_reminders")


class PTOVacationCelebration(Base):
    __tablename__ = "pto_vacation_celebrations"

    id = Column(Integer, primary_key=True, index=True)
    pto_request_id = Column(Integer, ForeignKey("pto_requests.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Celebration message
    celebration_message = Column(Text, nullable=False)
    celebration_sent_at = Column(DateTime, nullable=True)

    # Team notification
    team_notified = Column(Boolean, default=False)

    # Return message
    welcome_back_message = Column(Text, nullable=True)
    welcome_back_sent_at = Column(DateTime, nullable=True)

    # Relationships
    pto_request = relationship("PTORequest", backref="celebration")


class PTORecurrence(Base):
    __tablename__ = "pto_recurrences"

    id = Column(Integer, primary_key=True, index=True)
    pto_request_id = Column(Integer, ForeignKey("pto_requests.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Recurrence pattern (iCalendar RRULE format)
    recurrence_rule = Column(String(500), nullable=False)  # e.g., "FREQ=WEEKLY;BYDAY=WE"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # None = indefinite

    # Next occurrence for quick lookup
    next_occurrence_date = Column(Date, nullable=True, index=True)

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Track created/updated
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    pto_request = relationship("PTORequest", backref="recurrence")


class PTOCoverage(Base):
    __tablename__ = "pto_coverage"

    id = Column(Integer, primary_key=True, index=True)
    pto_request_id = Column(Integer, ForeignKey("pto_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    coverage_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Coverage status
    coverage_status = Column(String(50), default="assigned", nullable=False)  # assigned, accepted, declined

    # Coverage notes
    coverage_notes = Column(Text, nullable=True)

    # Tracking dates
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    responded_at = Column(DateTime, nullable=True)

    # Relationships
    pto_request = relationship("PTORequest", backref="coverage_assignments")
    coverage_user = relationship("User", foreign_keys=[coverage_user_id])


class PTOConflict(Base):
    __tablename__ = "pto_conflicts"

    id = Column(Integer, primary_key=True, index=True)
    pto_request_id = Column(Integer, ForeignKey("pto_requests.id", ondelete="CASCADE"), nullable=False, index=True)

    # Conflict details
    conflict_type = Column(String(100), nullable=False)  # overlapping_request, coverage_unavailable, partial_day_overlap
    conflicting_request_ids = Column(String(500), nullable=True)  # CSV of IDs
    conflict_description = Column(Text, nullable=False)

    # Status
    is_resolved = Column(Boolean, default=False, index=True)
    resolution_notes = Column(Text, nullable=True)

    # Tracking
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    pto_request = relationship("PTORequest", backref="conflicts")


class PTOStatusHistory(Base):
    __tablename__ = "pto_status_history"

    id = Column(Integer, primary_key=True, index=True)
    pto_request_id = Column(Integer, ForeignKey("pto_requests.id", ondelete="CASCADE"), nullable=False, index=True)

    # Status transition
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)

    # Who made the change
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Reason/notes
    change_reason = Column(Text, nullable=True)

    # Timestamp
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    pto_request = relationship("PTORequest", backref="status_history")
    changed_by = relationship("User", foreign_keys=[changed_by_id])
