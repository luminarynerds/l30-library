# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import Enum, StrEnum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SQLEnum, Float,
    ForeignKey, Integer, Numeric, String, Text, Index, JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


class CheckInMethod(StrEnum):
    QR_CODE = "qr_code"
    LIBRARY_CARD = "library_card"
    WALK_IN = "walk_in"
    HEAD_COUNT = "head_count"
    PRE_REGISTERED = "pre_registered"


class AgeRange(StrEnum):
    CHILD_0_5 = "0-5"
    CHILD_6_12 = "6-12"
    TEEN_13_17 = "13-17"
    ADULT_18_34 = "18-34"
    ADULT_35_54 = "35-54"
    ADULT_55_64 = "55-64"
    SENIOR_65_PLUS = "65+"
    UNKNOWN = "unknown"


class AttendanceSessionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    FINALIZED = "finalized"


class SurveyStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    COMPLETED = "completed"
    FAILED = "failed"
    OPTED_OUT = "opted_out"


class AttendanceSession(Base, TimestampMixin):
    __tablename__ = "attendance_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Link to either an event or a program (one must be set)
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    program_id = Column(
        Integer,
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Session metadata
    session_name = Column(String(255), nullable=False)
    session_date = Column(Date, nullable=False, index=True)
    status = Column(
        String(50),
        default=AttendanceSessionStatus.OPEN,
        nullable=False,
        index=True,
    )

    # QR code for self-service check-in
    qr_code_token = Column(String(100), unique=True, nullable=False, index=True)

    # Head count mode (for large events where individual tracking isn't practical)
    head_count_mode = Column(Boolean, default=False, nullable=False)
    head_count_total = Column(Integer, default=0, nullable=False)
    head_count_by_age = Column(JSON, nullable=True, default=dict)
    # e.g., {"0-5": 10, "6-12": 15, "13-17": 5, "18-34": 20, ...}

    # Aggregate stats (denormalized for performance)
    total_checked_in = Column(Integer, default=0, nullable=False)
    total_walk_ins = Column(Integer, default=0, nullable=False)
    total_pre_registered = Column(Integer, default=0, nullable=False)
    total_card_scans = Column(Integer, default=0, nullable=False)
    total_qr_scans = Column(Integer, default=0, nullable=False)

    # Cost tracking for ROI calculation
    event_cost = Column(Numeric(10, 2), nullable=True)
    cost_notes = Column(Text, nullable=True)

    # Survey configuration
    survey_enabled = Column(Boolean, default=True, nullable=False)
    survey_link = Column(String(500), nullable=True)
    survey_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Staff who opened/managed the session
    opened_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    closed_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    closed_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)

    # Relationships
    event = relationship("Event", backref="attendance_sessions")
    program = relationship("Program", backref="attendance_sessions")
    opened_by = relationship("User", foreign_keys=[opened_by_id])
    closed_by = relationship("User", foreign_keys=[closed_by_id])
    check_ins = relationship(
        "AttendanceCheckIn",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_attendance_sessions_event_date", "event_id", "session_date"),
        Index("ix_attendance_sessions_program_date", "program_id", "session_date"),
    )


class AttendanceCheckIn(Base, TimestampMixin):
    __tablename__ = "attendance_check_ins"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(
        Integer,
        ForeignKey("attendance_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Patron link (nullable for anonymous walk-ins)
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Pre-registration attribution link. NULL except for the
    # check_in_method='pre_registered' path created by the staff Roster
    # "Mark attended" action — there it points back to the
    # EventRegistration the check-in satisfies. ON DELETE SET NULL so
    # historical attendance survives registration deletion.
    registration_id = Column(
        Integer,
        ForeignKey("event_registrations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Walk-in info (when patron_id is null)
    guest_name = Column(String(255), nullable=True)
    guest_email = Column(String(255), nullable=True)
    guest_phone = Column(String(50), nullable=True)

    # Check-in details
    check_in_method = Column(
        String(50),
        nullable=False,
        index=True,
    )
    checked_in_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    checked_in_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Library card info (for card scan method)
    library_card_number = Column(String(50), nullable=True, index=True)

    # Age range estimation
    age_range = Column(
        String(50),
        default=AgeRange.UNKNOWN,
        nullable=False,
    )

    # Repeat attendee tracking
    is_repeat_attendee = Column(Boolean, default=False, nullable=False)
    previous_visit_count = Column(Integer, default=0, nullable=False)
    first_visit_date = Column(Date, nullable=True)

    # Post-event survey
    survey_status = Column(
        String(50),
        default=SurveyStatus.PENDING,
        nullable=False,
    )
    survey_sent_at = Column(DateTime(timezone=True), nullable=True)
    survey_completed_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)

    # Relationships
    session = relationship("AttendanceSession", back_populates="check_ins")
    patron = relationship("User", foreign_keys=[patron_id])
    checked_in_by = relationship("User", foreign_keys=[checked_in_by_id])

    __table_args__ = (
        Index("ix_check_ins_session_patron", "session_id", "patron_id"),
        Index("ix_check_ins_session_method", "session_id", "check_in_method"),
        Index("ix_check_ins_card_number", "library_card_number"),
    )


class AttendanceTrend(Base, TimestampMixin):
    __tablename__ = "attendance_trends"

    id = Column(Integer, primary_key=True, index=True)

    # Period
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False, index=True)  # daily, weekly, monthly

    # Grouping dimensions
    program_type = Column(String(50), nullable=True, index=True)
    audience = Column(String(50), nullable=True, index=True)
    branch_id = Column(Integer, nullable=True, index=True)

    # Metrics
    total_sessions = Column(Integer, default=0, nullable=False)
    total_attendance = Column(Integer, default=0, nullable=False)
    avg_attendance_per_session = Column(Float, default=0.0, nullable=False)
    total_walk_ins = Column(Integer, default=0, nullable=False)
    total_repeat_attendees = Column(Integer, default=0, nullable=False)
    total_new_attendees = Column(Integer, default=0, nullable=False)

    # ROI metrics
    total_cost = Column(Numeric(10, 2), default=0, nullable=False)
    cost_per_attendee = Column(Numeric(10, 2), default=0, nullable=False)

    # Age breakdown
    age_distribution = Column(JSON, nullable=True, default=dict)
    # e.g., {"0-5": 50, "6-12": 80, "13-17": 30, ...}

    # Check-in method breakdown
    method_distribution = Column(JSON, nullable=True, default=dict)
    # e.g., {"qr_code": 40, "library_card": 30, "walk_in": 20, "head_count": 10}

    __table_args__ = (
        Index("ix_trends_period_type", "period_type", "period_start"),
        Index("ix_trends_program_audience", "program_type", "audience"),
    )
