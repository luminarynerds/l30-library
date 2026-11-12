# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import Enum, StrEnum
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SQLEnum, ForeignKey,
    Integer, Numeric, String, Text, Time, Index, JSON, and_
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


class ProgramAudience(StrEnum):
    CHILDREN = "children"      # Ages 0-12
    TEEN = "teen"              # Ages 13-18
    ADULT = "adult"            # Ages 19-64
    SENIOR = "senior"          # Ages 65+
    FAMILY = "family"          # Mixed ages
    ALL_AGES = "all_ages"


class LibraryProgramType(StrEnum):
    STORYTIME = "storytime"
    WORKSHOP = "workshop"
    BOOK_CLUB = "book_club"
    LECTURE = "lecture"
    PERFORMANCE = "performance"
    EDUCATIONAL = "educational"
    RECREATIONAL = "recreational"
    OUTREACH = "outreach"
    READING_PROGRAM = "reading_program"
    TECHNOLOGY = "technology"
    ARTS_CRAFTS = "arts_crafts"
    STEM = "stem"
    MUSIC = "music"
    OTHER = "other"


class ProgramStatus(StrEnum):
    PLANNED = "planned"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"
    RESCHEDULED = "rescheduled"


class ProgramRegistrationStatus(StrEnum):
    REGISTERED = "registered"
    WAITLISTED = "waitlisted"
    ATTENDED = "attended"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


class Program(Base, TimestampMixin):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True)

    # ==================== IDENTIFICATION ====================
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Program categorization
    program_type = Column(
        String(50),
        nullable=False,
        index=True
    )
    audience = Column(
        String(50),
        nullable=False,
        index=True
    )

    # ==================== SCHEDULING ====================
    program_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=True)

    # Branch/location information
    branch_id = Column(
        Integer,
        ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    location_name = Column(String(255), nullable=True)  # For non-branch locations

    is_virtual = Column(Boolean, default=False, nullable=False)
    virtual_link = Column(String(500), nullable=True)

    # ==================== CAPACITY & REGISTRATION ====================
    max_capacity = Column(Integer, nullable=True)
    registration_required = Column(Boolean, default=False, nullable=False)

    # Tracking for state reporting
    expected_attendance = Column(Integer, nullable=True)
    actual_attendance = Column(Integer, default=0, nullable=False)

    # ==================== STATUS ====================
    status = Column(
        SQLEnum(
            ProgramStatus,
            name="programstatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ProgramStatus.PLANNED,
        nullable=False,
        index=True,
    )

    # ==================== FACILITATOR ====================
    facilitator_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    facilitator_name = Column(String(255), nullable=True)  # For external facilitators

    # ==================== DEMOGRAPHICS DATA ====================
    # Denormalized participant demographics for compliance reporting
    # Calculated from registrations but cached for performance
    registered_count = Column(Integer, default=0, nullable=False)
    attended_count = Column(Integer, default=0, nullable=False)

    # Attendance by age group (JSONB for state reporting)
    # e.g., {"children_0_5": 10, "children_6_12": 25, "teen_13_18": 5, ...}
    attendance_by_age_group = Column(JSON, nullable=True, default={})

    # Attendance demographics (JSONB)
    # e.g., {"resident": 30, "non_resident": 5}
    attendance_demographics = Column(JSON, nullable=True, default={})

    # ==================== NOTES ====================
    notes = Column(Text, nullable=True)

    # ==================== AUDIT ====================
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # ==================== RELATIONSHIPS ====================
    branch = relationship("Branch", foreign_keys=[branch_id], backref="programs")
    facilitator = relationship("User", foreign_keys=[facilitator_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    registrations = relationship(
        "ProgramRegistration",
        back_populates="program",
        cascade="all, delete-orphan",
        lazy="select"
    )

    __table_args__ = (
        Index("ix_programs_date_audience", "program_date", "audience"),
        Index("ix_programs_date_branch", "program_date", "branch_id"),
        Index("ix_programs_status", "status"),
    )


class ProgramRegistration(Base, TimestampMixin):
    __tablename__ = "program_registrations"

    id = Column(Integer, primary_key=True, index=True)

    # ==================== PROGRAM REFERENCE ====================
    program_id = Column(
        Integer,
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # ==================== PARTICIPANT IDENTIFICATION ====================
    # Can be linked to a patron or unlinked (for external registrations)
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # For unlinked registrations (walk-ins, external participants)
    participant_name = Column(String(255), nullable=True)
    participant_email = Column(String(255), nullable=True, index=True)
    participant_phone = Column(String(50), nullable=True)

    # ==================== REGISTRATION STATUS ====================
    status = Column(
        String(50),
        default=ProgramRegistrationStatus.REGISTERED,
        nullable=False,
        index=True
    )

    registered_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # ==================== ATTENDANCE ====================
    attended = Column(Boolean, default=False, nullable=False)
    attended_at = Column(DateTime(timezone=True), nullable=True)

    # Attendance verification
    checked_in_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # ==================== DEMOGRAPHICS (for state reporting) ====================
    # Capture at registration time for compliance reporting
    age_group = Column(String(50), nullable=True)  # e.g., "children_0_5", "teen_13_18"
    resident_status = Column(String(50), nullable=True)  # "resident", "non_resident"

    # Additional demographic fields for state-specific reporting
    demographics_data = Column(JSON, nullable=True, default={})
    # e.g., {"zip_code": "12345", "special_needs": false}

    # ==================== CANCELLATION ====================
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(String(255), nullable=True)
    cancelled_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # ==================== NOTES ====================
    notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    program = relationship("Program", back_populates="registrations")
    patron = relationship("User", foreign_keys=[patron_id], backref="program_registrations")
    checked_in_by = relationship("User", foreign_keys=[checked_in_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])

    __table_args__ = (
        Index("ix_program_registrations_program_status", "program_id", "status"),
        Index("ix_program_registrations_patron", "patron_id"),
        Index("ix_program_registrations_attended", "attended"),
    )
