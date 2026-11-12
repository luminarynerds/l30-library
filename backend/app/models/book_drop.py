# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey,
    Integer, Numeric, String, Text, Time, UniqueConstraint, Index
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BookDropStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class BackdateMode(StrEnum):
    NONE = "none"  # No backdating
    FIXED_TIME = "fixed_time"  # Backdate to a specific time (e.g., closing time)
    PROCESSING_SCHEDULE = "processing_schedule"  # Backdate to last processing time
    CUSTOM_HOURS = "custom_hours"  # Backdate by a custom number of hours


class CheckInSessionStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CheckInResultStatus(StrEnum):
    SUCCESS = "success"
    HOLD_TRAPPED = "hold_trapped"
    TRANSIT_REQUIRED = "transit_required"
    EXCEPTION = "exception"
    NOT_CHECKED_OUT = "not_checked_out"
    ITEM_NOT_FOUND = "item_not_found"
    CONDITION_ISSUE = "condition_issue"


class ExceptionType(StrEnum):
    DAMAGED_ITEM = "damaged_item"
    ITEM_NOTE = "item_note"
    PATRON_BLOCKED = "patron_blocked"
    PATRON_NOTE = "patron_note"
    OVERDUE_FINE = "overdue_fine"
    LOST_ITEM_RETURNED = "lost_item_returned"
    CLAIMS_RETURNED = "claims_returned"
    MISSING_PARTS = "missing_parts"
    WRONG_ITEM = "wrong_item"
    OTHER = "other"


class SIP2DeviceStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class SortDestination(StrEnum):
    HOLD_SHELF = "hold_shelf"
    TRANSIT = "transit"
    RESHELVE = "reshelve"
    EXCEPTION = "exception"
    CONDITION_CHECK = "condition_check"


class BookDrop(Base):
    __tablename__ = "book_drops"

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False, index=True)
    description = Column(Text)

    # Location
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=False)  # deprecated; use branch_id
    physical_location = Column(String(255))  # e.g., "Outside main entrance"

    # Status
    status = Column(
        String(50),
        default=BookDropStatus.ACTIVE,
        nullable=False
    )

    def __init__(self, **kwargs):
        # Set defaults for Python object creation
        if 'status' not in kwargs:
            kwargs['status'] = BookDropStatus.ACTIVE
        if 'backdate_mode' not in kwargs:
            kwargs['backdate_mode'] = BackdateMode.FIXED_TIME
        if 'exempt_overnight_fines' not in kwargs:
            kwargs['exempt_overnight_fines'] = True
        if 'max_backdate_hours' not in kwargs:
            kwargs['max_backdate_hours'] = 16
        super().__init__(**kwargs)

    # Backdating configuration
    backdate_mode = Column(
        String(50),
        default=BackdateMode.FIXED_TIME,
        nullable=False
    )
    backdate_fixed_time = Column(Time)  # For FIXED_TIME mode (e.g., 21:00 closing time)
    backdate_hours = Column(Integer)  # For CUSTOM_HOURS mode

    # Days when backdating applies (JSON array of day numbers: 0=Monday, 6=Sunday)
    backdate_days = Column(JSONB, default=[])  # e.g., [0,1,2,3,4,5,6] for all days

    # Processing schedule (when items are typically processed)
    processing_start_time = Column(Time)  # e.g., 09:00
    processing_end_time = Column(Time)  # e.g., 17:00

    # Fine exemption settings
    exempt_overnight_fines = Column(Boolean, default=True)
    max_backdate_hours = Column(Integer, default=16)  # Maximum hours to backdate

    # SIP2 integration
    sip2_device_id = Column(Integer, ForeignKey("sip2_devices.id", ondelete="SET NULL"), nullable=True)

    # Audit (SET NULL: preserve book drop creation history), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    sip2_device = relationship("SIP2Device", back_populates="book_drops")
    created_by = relationship("User", foreign_keys=[created_by_id])
    check_in_sessions = relationship("CheckInSession", back_populates="book_drop")
    statistics = relationship("CheckInStatistic", back_populates="book_drop")

    __table_args__ = (
        UniqueConstraint("code", name="uq_book_drops_code"),
    )


class SIP2Device(Base):
    __tablename__ = "sip2_devices"

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    name = Column(String(100), nullable=False)
    device_id = Column(String(50), nullable=False, index=True)

    # Connection settings
    host = Column(String(255), nullable=False)
    port = Column(Integer, default=6001, nullable=False)
    institution_id = Column(String(100), nullable=False)
    terminal_password = Column(String(100))  # Encrypted in production

    # Status
    status = Column(
        String(50),
        default=SIP2DeviceStatus.OFFLINE,
        nullable=False,
        index=True
    )
    last_communication = Column(DateTime(timezone=True))
    error_message = Column(Text)

    # Configuration
    timeout_seconds = Column(Integer, default=30)
    retry_attempts = Column(Integer, default=3)

    # Supported operations
    supports_checkin = Column(Boolean, default=True)
    supports_checkout = Column(Boolean, default=True)
    supports_sorting = Column(Boolean, default=False)

    # Sorting configuration (JSON map of conditions to destinations)
    # e.g., {"hold": "bin_1", "transit": "bin_2", "reshelve": "bin_3"}
    sort_bin_mapping = Column(JSONB, default={})

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    book_drops = relationship("BookDrop", back_populates="sip2_device")

    __table_args__ = (
        UniqueConstraint("device_id", name="uq_sip2_devices_device_id"),
    )


class CheckInSession(Base):
    __tablename__ = "check_in_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Session identification
    session_code = Column(String(50), nullable=False, index=True)

    # Context
    book_drop_id = Column(Integer, ForeignKey("book_drops.id", ondelete="CASCADE"), nullable=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=False)  # deprecated; use branch_id
    workstation_id = Column(String(50))

    # Staff
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)

    # Status
    status = Column(
        String(50),
        default=CheckInSessionStatus.ACTIVE,
        nullable=False,
        index=True
    )

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True))

    # Backdating (if processing a book drop)
    use_backdating = Column(Boolean, default=False)
    backdate_to = Column(DateTime(timezone=True))

    # Statistics (denormalized for quick access)
    total_items = Column(Integer, default=0)
    successful_checkins = Column(Integer, default=0)
    holds_trapped = Column(Integer, default=0)
    transits_created = Column(Integer, default=0)
    exceptions_count = Column(Integer, default=0)

    def __init__(self, **kwargs):
        # Set defaults for Python object creation
        if 'status' not in kwargs:
            kwargs['status'] = CheckInSessionStatus.ACTIVE
        if 'use_backdating' not in kwargs:
            kwargs['use_backdating'] = False
        if 'total_items' not in kwargs:
            kwargs['total_items'] = 0
        if 'successful_checkins' not in kwargs:
            kwargs['successful_checkins'] = 0
        if 'holds_trapped' not in kwargs:
            kwargs['holds_trapped'] = 0
        if 'transits_created' not in kwargs:
            kwargs['transits_created'] = 0
        if 'exceptions_count' not in kwargs:
            kwargs['exceptions_count'] = 0
        super().__init__(**kwargs)

    # Relationships
    book_drop = relationship("BookDrop", back_populates="check_in_sessions")
    staff = relationship("User")
    check_in_results = relationship(
        "CheckInResult",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("session_code", name="uq_check_in_sessions_session_code"),
        Index("ix_checkin_sessions_date_branch", "started_at", "branch_location"),
    )


class CheckInResult(Base):
    __tablename__ = "check_in_results"

    id = Column(Integer, primary_key=True, index=True)

    # Session
    session_id = Column(
        Integer,
        ForeignKey("check_in_sessions.id", ondelete="CASCADE"),
    )

    # Item identification
    barcode = Column(String(50), nullable=False, index=True)
    item_copy_id = Column(Integer, ForeignKey("item_copies.id", ondelete="SET NULL"), nullable=True)
    checkout_id = Column(Integer, ForeignKey("checkouts.id", ondelete="SET NULL"), nullable=True)

    # Result
    status = Column(
        String(50),
    )

    # Sort destination (for AMH systems)
    sort_destination = Column(
        String(50),
    )
    sort_bin = Column(String(50))  # Physical bin identifier

    # Hold information (if trapped)
    hold_id = Column(Integer, ForeignKey("holds.id", ondelete="SET NULL"), nullable=True)
    hold_patron_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Transit information (if required)
    destination_branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    destination_branch = Column(String(100))  # deprecated; use destination_branch_id

    # Timing
    checked_in_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    effective_checkin_time = Column(DateTime(timezone=True))  # After backdating

    # Overdue/fine info
    was_overdue = Column(Boolean, default=False)
    overdue_days = Column(Integer, default=0)
    fine_amount = Column(Numeric(10, 2), default=0)
    fine_waived_by_backdate = Column(Boolean, default=False)

    # Condition check
    condition_checked = Column(Boolean, default=False)
    condition_status = Column(String(50))  # "good", "damaged", etc.
    condition_notes = Column(Text)

    # Exception details
    exception_type = Column(
        String(50),
    )
    exception_message = Column(Text)
    exception_resolved = Column(Boolean, default=False)
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True))
    resolution_notes = Column(Text)

    # Relationships
    session = relationship("CheckInSession", back_populates="check_in_results")
    item_copy = relationship("ItemCopy")
    checkout = relationship("Checkout")
    hold = relationship("Hold")
    hold_patron = relationship("User", foreign_keys=[hold_patron_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])

    __table_args__ = (
        Index("ix_checkin_results_session_status", "session_id", "status"),
    )


class CheckInStatistic(Base):
    __tablename__ = "check_in_statistics"
    __table_args__ = (
        UniqueConstraint(
            "date", "hour", "branch_location", "book_drop_id",
            name="uq_checkin_stats_date_hour_location"
        ),
        Index("ix_checkin_stats_date_branch", "date", "branch_location"),
    )

    id = Column(Integer, primary_key=True)

    # Time period
    date = Column(Date, nullable=False)
    hour = Column(Integer, nullable=False)  # 0-23
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday

    # Location
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=False)  # deprecated; use branch_id
    book_drop_id = Column(Integer, ForeignKey("book_drops.id", ondelete="SET NULL"), nullable=True)

    # Volume counts
    total_checkins = Column(Integer, default=0)
    staff_checkins = Column(Integer, default=0)
    book_drop_checkins = Column(Integer, default=0)
    self_service_checkins = Column(Integer, default=0)

    # Results breakdown
    successful_count = Column(Integer, default=0)
    holds_trapped_count = Column(Integer, default=0)
    transits_count = Column(Integer, default=0)
    exceptions_count = Column(Integer, default=0)

    # Overdue stats
    overdue_items_count = Column(Integer, default=0)
    total_fines_amount = Column(Numeric(10, 2), default=0)
    fines_waived_amount = Column(Numeric(10, 2), default=0)

    # Processing time (average seconds per item)
    avg_processing_time = Column(Float, default=0)

    def __init__(self, **kwargs):
        # Set defaults for Python object creation
        if 'total_checkins' not in kwargs:
            kwargs['total_checkins'] = 0
        if 'staff_checkins' not in kwargs:
            kwargs['staff_checkins'] = 0
        if 'book_drop_checkins' not in kwargs:
            kwargs['book_drop_checkins'] = 0
        if 'self_service_checkins' not in kwargs:
            kwargs['self_service_checkins'] = 0
        if 'successful_count' not in kwargs:
            kwargs['successful_count'] = 0
        if 'holds_trapped_count' not in kwargs:
            kwargs['holds_trapped_count'] = 0
        if 'transits_count' not in kwargs:
            kwargs['transits_count'] = 0
        if 'exceptions_count' not in kwargs:
            kwargs['exceptions_count'] = 0
        if 'overdue_items_count' not in kwargs:
            kwargs['overdue_items_count'] = 0
        if 'total_fines_amount' not in kwargs:
            kwargs['total_fines_amount'] = 0
        if 'fines_waived_amount' not in kwargs:
            kwargs['fines_waived_amount'] = 0
        if 'avg_processing_time' not in kwargs:
            kwargs['avg_processing_time'] = 0
        super().__init__(**kwargs)

    # Timestamps, server_default=func.now(), nullable=False)

    # Relationships
    book_drop = relationship("BookDrop", back_populates="statistics")


class CheckInException(Base):
    __tablename__ = "check_in_exceptions"

    id = Column(Integer, primary_key=True, index=True)

    # Link to check-in result
    check_in_result_id = Column(
        Integer,
        ForeignKey("check_in_results.id", ondelete="CASCADE"),
        index=True
    )

    # Exception details
    exception_type = Column(
        String(50),
        index=True
    )
    severity = Column(String(20), default="normal")  # low, normal, high, critical

    # Item and patron info
    item_copy_id = Column(Integer, ForeignKey("item_copies.id", ondelete="SET NULL"), nullable=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Details
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Related data (JSON for flexibility)
    # e.g., {"note_text": "...", "fine_amount": 5.00, "damage_type": "water"}
    exception_data = Column(JSONB, default={})

    # Resolution
    requires_action = Column(Boolean, default=True)
    action_taken = Column(Text)
    resolved = Column(Boolean, default=False)
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True))

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    check_in_result = relationship("CheckInResult")
    item_copy = relationship("ItemCopy")
    patron = relationship("User", foreign_keys=[patron_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])
