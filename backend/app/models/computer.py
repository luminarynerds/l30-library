# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from enum import StrEnum
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, Float,
    JSON, Numeric, UnicodeText
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class ComputerType(StrEnum):
    kids = "kids"  # Ages 5-12
    teen = "teen"  # Ages 13-17
    adult = "adult"  # Ages 18+
    accessible = "accessible"  # ADA accessible workstations


class ComputerStatus(StrEnum):
    available = "available"  # Available for use
    in_use = "in_use"  # Currently in use
    maintenance = "maintenance"  # Under maintenance
    offline = "offline"  # Offline/broken
    reserved = "reserved"  # Reserved but not yet in use


class ComputerReservationStatus(StrEnum):
    pending = "pending"  # Pending approval (guest passes)
    confirmed = "confirmed"  # Confirmed and approved
    in_session = "in_session"  # Session is currently active
    completed = "completed"  # Session completed normally
    cancelled = "cancelled"  # Cancelled by patron or staff
    no_show = "no_show"  # Patron didn't show up
    extended = "extended"  # Session was extended


class ComputerWaitlistStatus(StrEnum):
    pending = "pending"  # Waiting for availability
    notified = "notified"  # Patron notified, awaiting confirmation
    expired = "expired"  # Waitlist entry expired
    fulfilled = "fulfilled"  # Patron got their slot


class ExtensionStatus(StrEnum):
    pending = "pending"  # Awaiting approval
    approved = "approved"  # Approved and time extended
    denied = "denied"  # Request was denied
    expired = "expired"  # Extension time limit passed


class Computer(Base):
    __tablename__ = "computers"

    id = Column(Integer, primary_key=True, index=True)

    # Computer identification
    name = Column(String(255), nullable=False, unique=True)  # e.g., "Computer-Kids-001"
    computer_number = Column(String(50), nullable=False, unique=True)  # Physical label number
    description = Column(Text, nullable=True)

    # Branch/location association
    branch_id = Column(Integer, nullable=True)
    branch_name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)  # e.g., "Main Floor, West Wall"

    # Computer characteristics
    computer_type = Column(
        SQLEnum(ComputerType, name="computertype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ComputerType.adult,
        nullable=False,
        index=True
    )

    # Operating system and specs
    os_type = Column(String(50), nullable=True)  # Windows, macOS, Linux
    os_version = Column(String(50), nullable=True)
    processor = Column(String(100), nullable=True)
    ram_gb = Column(Integer, nullable=True)
    storage_gb = Column(Integer, nullable=True)

    # Software/applications installed (stored as array)
    installed_software = Column(ARRAY(String(100)), nullable=True, default=list)
    # Example: ["word", "excel", "zoom", "firefox", "chrome"]

    # Internet connectivity
    has_internet = Column(Boolean, default=True)
    internet_type = Column(String(50), nullable=True)  # WiFi, Ethernet, etc.

    # Accessibility features
    has_screen_reader = Column(Boolean, default=False)
    has_magnifier = Column(Boolean, default=False)
    has_keyboard_options = Column(Boolean, default=False)
    accessibility_features = Column(ARRAY(String(100)), nullable=True, default=list)

    # Printing capabilities
    has_print_release = Column(Boolean, default=True)
    print_balance_required = Column(Boolean, default=False)

    # Session limits
    max_session_minutes = Column(Integer, default=60)  # Default 1 hour
    is_extendable = Column(Boolean, default=True)
    max_extension_minutes = Column(Integer, default=60)  # Can extend by 1 hour max
    max_extensions_per_day = Column(Integer, default=1)

    # Status and availability
    status = Column(
        SQLEnum(ComputerStatus, name="computerstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ComputerStatus.available,
        nullable=False,
        index=True
    )
    is_active = Column(Boolean, default=True, index=True)

    # Last maintenance info
    last_maintenance_at = Column(DateTime(timezone=True), nullable=True)
    maintenance_notes = Column(Text, nullable=True)

    # Operating hours (JSON for flexibility)
    # Example: {"monday": {"open": "09:00", "close": "21:00"}, ...}
    operating_hours = Column(JSONB, nullable=True)

    # Images/documentation
    image_url = Column(String(500), nullable=True)

    # Lab map position (set via admin arrange UI)
    map_x = Column(Float, nullable=True)  # X coordinate, 0-1 normalized
    map_y = Column(Float, nullable=True)  # Y coordinate, 0-1 normalized
    map_floor = Column(String(50), nullable=True, index=True)  # e.g., "main", "upstairs"

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    reservations = relationship("ComputerReservation", back_populates="computer", lazy="dynamic", cascade="all, delete-orphan")
    # sessions relationship removed — ComputerSession canonical definition is in cipa_compliance.py
    # and uses workstation_id (string) instead of computer_id FK
    waitlist = relationship("ComputerWaitlist", back_populates="computer", lazy="dynamic", cascade="all, delete-orphan")
    usage_stats = relationship("ComputerUsageStats", back_populates="computer", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_computers_active_type", "is_active", "computer_type"),
        Index("ix_computers_status_branch", "status", "branch_id"),
        Index("ix_computers_type_status", "computer_type", "status"),
    )


class ComputerReservation(Base):
    __tablename__ = "computer_reservations"

    id = Column(Integer, primary_key=True, index=True)

    # Computer and patron references
    computer_id = Column(
        Integer,
        ForeignKey("computers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Reservation timing
    reserved_start_time = Column(DateTime(timezone=True), nullable=False)
    reserved_end_time = Column(DateTime(timezone=True), nullable=False)

    # Status tracking
    status = Column(
        SQLEnum(ComputerReservationStatus, name="computationreservationstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ComputerReservationStatus.pending,
        nullable=False,
        index=True
    )

    # Session details
    session_duration_minutes = Column(Integer, nullable=False)  # Requested duration

    # Guest pass information (for non-cardholders)
    is_guest_pass = Column(Boolean, default=False)
    guest_pass_code = Column(String(50), nullable=True, unique=True)  # Unique code for check-in
    guest_name = Column(String(255), nullable=True)
    guest_email = Column(String(255), nullable=True)
    guest_phone = Column(String(50), nullable=True)

    # Check-in/out tracking
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    actual_start_time = Column(DateTime(timezone=True), nullable=True)
    actual_end_time = Column(DateTime(timezone=True), nullable=True)

    # Extension information
    extension_requested = Column(Boolean, default=False)
    extended_until = Column(DateTime(timezone=True), nullable=True)
    extensions_used = Column(Integer, default=0)

    # Cancellation tracking
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cancellation_reason = Column(String(500), nullable=True)

    # Notification tracking
    confirmation_sent_at = Column(DateTime(timezone=True), nullable=True)
    five_min_warning_sent_at = Column(DateTime(timezone=True), nullable=True)
    expiration_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Staff notes
    internal_notes = Column(Text, nullable=True)

    # Print integration
    print_jobs_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    computer = relationship("Computer", back_populates="reservations")
    patron = relationship("User", foreign_keys=[patron_id], backref="computer_reservations")
    canceller = relationship("User", foreign_keys=[cancelled_by])
    # session relationship removed — ComputerSession canonical definition is in cipa_compliance.py
    # and doesn't have a reservation_id FK

    __table_args__ = (
        Index("ix_reservations_computer_time", "computer_id", "reserved_start_time", "reserved_end_time"),
        Index("ix_computer_reservations_patron_status", "patron_id", "status"),
        Index("ix_computer_reservations_start_status", "reserved_start_time", "status"),
        Index("ix_computer_reservations_guest_pass_code", "guest_pass_code"),
    )


# ComputerSession is defined in cipa_compliance.py (canonical table owner).
# Import here so relationship("ComputerSession") resolves within this module.
from .cipa_compliance import ComputerSession  # noqa: F401


class ComputerWaitlist(Base):
    __tablename__ = "computer_waitlist"

    id = Column(Integer, primary_key=True, index=True)

    # Computer and patron references
    computer_id = Column(
        Integer,
        ForeignKey("computers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Guest pass info (for non-cardholders)
    is_guest = Column(Boolean, default=False)
    guest_phone = Column(String(50), nullable=True)  # For SMS notifications

    # Desired time window
    desired_start_time = Column(DateTime(timezone=True), nullable=False)
    desired_duration_minutes = Column(Integer, nullable=False)

    # Status tracking
    status = Column(
        SQLEnum(ComputerWaitlistStatus, name="computerwaitliststatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ComputerWaitlistStatus.pending,
        nullable=False,
        index=True
    )

    # Queue position
    queue_position = Column(Integer, nullable=False)

    # Notification tracking
    notified_at = Column(DateTime(timezone=True), nullable=True)
    notification_method = Column(String(50), nullable=True)  # "sms", "email", "in_person"

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Auto-expire after 24 hours

    # Relationships
    computer = relationship("Computer", back_populates="waitlist")
    patron = relationship("User", backref="computer_waitlist_entries")

    __table_args__ = (
        Index("ix_waitlist_computer_status", "computer_id", "status"),
        Index("ix_computer_waitlist_patron_status", "patron_id", "status"),
        Index("ix_computer_waitlist_expires", "expires_at", "status"),
    )


class GuestPass(Base):
    __tablename__ = "guest_passes"

    id = Column(Integer, primary_key=True, index=True)

    # Guest information
    guest_name = Column(String(255), nullable=False)
    guest_email = Column(String(255), nullable=True)
    guest_phone = Column(String(50), nullable=True)

    # Pass details
    pass_code = Column(String(50), nullable=False, unique=True)  # Unique code for check-in

    # Usage limits
    max_sessions = Column(Integer, default=1)  # How many sessions this pass allows
    sessions_used = Column(Integer, default=0)
    max_duration_minutes_per_session = Column(Integer, default=60)

    # Pass validity
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False)  # Expiration date
    is_active = Column(Boolean, default=True)

    # Issuer information
    issued_by_staff_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Restrictions
    allowed_computer_types = Column(ARRAY(String(50)), nullable=True, default=list)  # If empty, all types allowed
    # Example: ["adult", "accessible"]

    # Tracking
    first_used_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    issued_by = relationship("User", foreign_keys=[issued_by_staff_id], backref="guest_passes_issued")

    __table_args__ = (
        Index("ix_guest_passes_pass_code", "pass_code"),
        Index("ix_guest_pass_active", "is_active", "valid_until"),
        Index("ix_guest_pass_phone", "guest_phone"),
    )


class SessionExtensionRequest(Base):
    __tablename__ = "session_extension_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Session reference
    reservation_id = Column(
        Integer,
        ForeignKey("computer_reservations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    session_id = Column(
        Integer,
        ForeignKey("computer_sessions.id", ondelete="CASCADE"),
        nullable=False
    )

    # Extension details
    extension_minutes = Column(Integer, nullable=False)
    status = Column(
        SQLEnum(ExtensionStatus, name="extensionstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ExtensionStatus.pending,
        nullable=False
    )

    # Request tracking
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Denial information
    denial_reason = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    reservation = relationship("ComputerReservation")
    session = relationship("ComputerSession")
    approver = relationship("User", foreign_keys=[approved_by])

    __table_args__ = (
        Index("ix_extension_request_status", "status"),
        Index("ix_extension_request_session", "session_id"),
    )


class ComputerUsageStats(Base):
    __tablename__ = "computer_usage_stats"

    id = Column(Integer, primary_key=True, index=True)

    computer_id = Column(
        Integer,
        ForeignKey("computers.id", ondelete="CASCADE"),
        nullable=False
    )

    # Time period (daily aggregation)
    date = Column(DateTime(timezone=True), nullable=False)

    # Metrics
    total_reservations = Column(Integer, default=0)
    completed_sessions = Column(Integer, default=0)
    cancelled_reservations = Column(Integer, default=0)
    no_show_count = Column(Integer, default=0)
    total_minutes_used = Column(Integer, default=0)
    total_extension_minutes = Column(Integer, default=0)

    # Guest usage
    guest_sessions = Column(Integer, default=0)
    cardholders_sessions = Column(Integer, default=0)

    # Extension statistics
    extension_requests = Column(Integer, default=0)
    extension_requests_granted = Column(Integer, default=0)
    extension_requests_denied = Column(Integer, default=0)

    # Peak hours tracking (JSON with hour -> count mapping)
    hourly_usage = Column(JSONB, nullable=True, default=dict)

    # Availability tracking
    downtime_minutes = Column(Integer, default=0)
    maintenance_events = Column(Integer, default=0)

    # Print jobs
    print_jobs_count = Column(Integer, default=0)

    # Relationships
    computer = relationship("Computer", back_populates="usage_stats")

    __table_args__ = (
        Index("ix_computer_stats_date", "computer_id", "date", unique=True),
        Index("ix_computer_stats_period", "date"),
    )


class ComputerSystemLog(Base):
    __tablename__ = "computer_system_logs"

    id = Column(Integer, primary_key=True, index=True)

    # What happened
    event_type = Column(String(100), nullable=False)  # "reservation_created", "session_started", "auto_logout", etc.
    description = Column(String(500), nullable=False)

    # Related entities
    computer_id = Column(Integer, ForeignKey("computers.id", ondelete="SET NULL"), nullable=True)
    reservation_id = Column(Integer, ForeignKey("computer_reservations.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(Integer, ForeignKey("computer_sessions.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Additional context
    system_metadata = Column(JSONB, nullable=True, default=dict)

    # Severity for monitoring
    severity = Column(String(20), default="info")  # "debug", "info", "warning", "error", "critical"

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_log_event_type", "event_type"),
        Index("ix_log_computer", "computer_id"),
        Index("ix_log_created", "created_at"),
    )
