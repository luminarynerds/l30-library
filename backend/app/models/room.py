# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Index, Integer,
                        String, Text, text)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base


class RoomType(StrEnum):
    study_room = "study_room"  # Auto-approved
    meeting_room = "meeting_room"  # Requires staff approval
    computer_lab = "computer_lab"  # Auto-approved
    event_space = "event_space"  # Requires staff approval


class ReservationStatus(StrEnum):
    pending = "pending"  # Awaiting approval (meeting rooms)
    confirmed = "confirmed"  # Approved and confirmed
    checked_in = "checked_in"  # Patron has checked in
    completed = "completed"  # Reservation ended normally
    cancelled = "cancelled"  # Cancelled by patron or staff
    no_show = "no_show"  # Patron didn't check in within grace period
    rejected = "rejected"  # Staff rejected the request


class RejectionReason(StrEnum):
    schedule_conflict = "schedule_conflict"
    capacity_exceeded = "capacity_exceeded"
    incomplete_information = "incomplete_information"
    prior_policy_violation = "prior_policy_violation"
    fee_unpaid = "fee_unpaid"
    out_of_hours = "out_of_hours"
    other = "other"


class RecurrencePattern(StrEnum):
    daily = "daily"
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"


class Room(TimestampMixin, Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Branch/location association (nullable for single-branch libraries)
    branch_id = Column(Integer, nullable=True)
    branch_name = Column(String(255), nullable=True)

    # Room characteristics
    room_type = Column(
        SQLEnum(RoomType, name="roomtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=RoomType.study_room,
        nullable=False,
    )
    capacity = Column(Integer, nullable=False, default=4)
    floor = Column(String(50), nullable=True)
    room_number = Column(String(50), nullable=True)

    # Available equipment/amenities (stored as array)
    amenities = Column(ARRAY(String(100)), nullable=True, default=list)

    # Equipment add-ons available for this room
    available_equipment = Column(JSONB, nullable=True, default=list)
    # Example: [{"id": "projector", "name": "Projector", "requires_staff": false},
    #           {"id": "video_conf", "name": "Video Conferencing", "requires_staff": true}]

    # Booking rules
    requires_approval = Column(Boolean, default=False)
    max_duration_minutes = Column(Integer, default=120)  # Maximum booking length
    min_duration_minutes = Column(Integer, default=30)   # Minimum booking length
    advance_booking_days = Column(Integer, default=14)   # How far in advance can book
    min_advance_hours = Column(Integer, default=1)       # Minimum hours before reservation

    # Operating hours (stored as JSON for flexibility)
    # Example: {"monday": {"open": "09:00", "close": "21:00"}, ...}
    operating_hours = Column(JSONB, nullable=True)

    # Images
    image_url = Column(String(500), nullable=True)

    # Walk-in room management
    is_walkable = Column(Boolean, default=False)  # Whether room accepts walk-ins
    walk_in_enabled = Column(Boolean, default=False)  # Current walk-in status
    walk_in_duration_minutes = Column(Integer, default=60)  # Default walk-in booking duration
    max_concurrent_walkins = Column(Integer, default=1)  # Max concurrent walk-in bookings
    walkout_grace_minutes = Column(Integer, default=15)  # Grace period after booking ends
    enable_occupancy_sensor = Column(Boolean, default=False)  # Optional occupancy sensor

    # Status
    is_active = Column(Boolean, default=True)

    # Accessibility metadata (surfaced to patrons)
    wheelchair_accessible = Column(Boolean, default=False, nullable=False)
    hearing_loop = Column(Boolean, default=False, nullable=False)
    accessible_restroom_nearby = Column(Boolean, default=False, nullable=False)
    accessibility_notes = Column(Text, nullable=True)

    # Setup/teardown buffers (in minutes). When > 0, conflict-detection
    # extends the occupied window by these durations within the same room.
    setup_buffer_minutes = Column(Integer, default=0, nullable=False)
    teardown_buffer_minutes = Column(Integer, default=0, nullable=False)

    # Per-patron rolling 30-day booking cap. NULL = unlimited.
    max_bookings_per_patron_per_month = Column(Integer, nullable=True)

    # Per-language translations: {"es": {"name": "...", "description": "..."}}
    translations = Column(JSONB, nullable=False, server_default=text("'{}'"))

    # Timestamps, server_default=func.now())

    # Relationships
    reservations = relationship("RoomReservation", back_populates="room", lazy="dynamic")

    __table_args__ = (
        # Composite index for room listing queries
        Index("ix_rooms_active_type", "is_active", "room_type"),
        Index("ix_rooms_branch_active", "branch_id", "is_active"),
    )


class RoomReservation(TimestampMixin, Base):
    __tablename__ = "room_reservations"

    id = Column(Integer, primary_key=True, index=True)

    # Room and patron references
    room_id = Column(
        Integer,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False
    )
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Reservation timing
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    # Status tracking
    status = Column(
        SQLEnum(ReservationStatus, name="reservationstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ReservationStatus.pending,
        nullable=False,
    )

    # Booking details
    purpose = Column(String(500), nullable=True)
    attendee_count = Column(Integer, default=1)

    # Equipment add-ons requested
    equipment_requested = Column(ARRAY(String(100)), nullable=True, default=list)
    # Example: ["projector", "whiteboard", "video_conf"]

    # Contact information (for non-logged-in users or group bookings)
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True, index=True)
    contact_phone = Column(String(50), nullable=True)

    # Recurring reservation support
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(
        SQLEnum(RecurrencePattern, name="recurrencepattern", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    recurrence_end_date = Column(DateTime(timezone=True), nullable=True)
    parent_reservation_id = Column(
        Integer,
        ForeignKey("room_reservations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Approval workflow
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(String(500), nullable=True)
    # Structured rejection category (free-text rejection_reason becomes
    # supplementary notes when rejection_reason_code is set).
    rejection_reason_code = Column(
        SQLEnum(RejectionReason, name="rejectionreason", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )

    # Accommodation request (accessibility + special needs)
    accommodation_requested = Column(Boolean, default=False, nullable=False)
    accommodation_details = Column(Text, nullable=True)
    accommodation_acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    accommodation_acknowledged_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Meeting-room policy acknowledgement (required for approval-gated rooms)
    policy_acknowledged = Column(Boolean, default=False, nullable=False)
    policy_acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    # Check-in tracking for no-show detection
    checked_in_at = Column(DateTime(timezone=True), nullable=True)

    # Cancellation tracking
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cancellation_reason = Column(String(500), nullable=True)

    # Staff override (for priority bookings or emergencies)
    is_staff_override = Column(Boolean, default=False)
    override_reason = Column(String(500), nullable=True)

    # Notes
    internal_notes = Column(Text, nullable=True)  # Staff-only notes

    # Notification tracking
    confirmation_sent_at = Column(DateTime(timezone=True), nullable=True)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Walk-in specific fields
    is_walkin = Column(Boolean, default=False)  # Whether this is a walk-in reservation
    released_early_at = Column(DateTime(timezone=True), nullable=True)  # When user released early
    released_early_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # User who released
    extended_until = Column(DateTime(timezone=True), nullable=True)  # Extended booking end time
    queue_position = Column(Integer, nullable=True)  # Position in queue if waiting
    occupancy_sensor_active = Column(Boolean, default=False)  # Sensor detected occupancy

    # Timestamps, server_default=func.now())

    # Relationships
    room = relationship("Room", back_populates="reservations")
    patron = relationship("User", foreign_keys=[patron_id], backref="room_reservations")
    approver = relationship("User", foreign_keys=[approved_by])
    canceller = relationship("User", foreign_keys=[cancelled_by])
    early_releaser = relationship("User", foreign_keys=[released_early_by])
    accommodation_acknowledger = relationship("User", foreign_keys=[accommodation_acknowledged_by])
    # Self-referential relationship with lazy loading to prevent circular reference GC issues
    parent_reservation = relationship(
        "RoomReservation",
        remote_side=[id],
        back_populates="child_reservations",
        lazy="select"
    )
    child_reservations = relationship(
        "RoomReservation",
        back_populates="parent_reservation",
        lazy="select"
    )

    # Partial unique constraint: prevent overlapping confirmed/checked_in reservations
    __table_args__ = (
        # Composite index for availability queries (room + time range + status)
        Index("ix_reservations_room_time", "room_id", "start_time", "end_time"),
        # Index for patron's reservations
        Index("ix_reservations_patron_status", "patron_id", "status"),
        # Index for upcoming reservations (for reminders)
        Index("ix_reservations_start_status", "start_time", "status"),
        # Index for no-show detection
        Index(
            "ix_reservations_noshow_check",
            "start_time",
            "status",
            "checked_in_at",
            postgresql_where=text("status = 'confirmed' AND checked_in_at IS NULL"),
        ),
    )


class RoomEquipment(Base):
    __tablename__ = "room_equipment"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    equipment_code = Column(String(50), nullable=False, unique=True)  # e.g., "projector", "whiteboard"

    # Availability
    total_quantity = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)

    # Requirements
    requires_staff_setup = Column(Boolean, default=False)
    setup_instructions = Column(Text, nullable=True)

    # Timestamps, server_default=func.now())


class RoomWaitlistStatus(StrEnum):
    pending = "pending"  # Waiting for a cancellation
    notified = "notified"  # Room became available, patron notified
    expired = "expired"  # Waitlist entry expired


class RoomWaitlist(Base):
    __tablename__ = "room_waitlist"

    id = Column(Integer, primary_key=True, index=True)

    # Room and patron references
    room_id = Column(
        Integer,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False
    )
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Desired time window
    desired_start_time = Column(DateTime(timezone=True), nullable=False)
    desired_end_time = Column(DateTime(timezone=True), nullable=False)

    # Status tracking
    status = Column(
        SQLEnum(RoomWaitlistStatus, name="roomwaitliststatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=RoomWaitlistStatus.pending,
        nullable=False,
    )

    # Notification tracking
    notified_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Auto-expire after 7 days

    # Relationships
    room = relationship("Room")
    patron = relationship("User", backref="room_waitlist_entries")

    __table_args__ = (
        # Index for finding active waitlist entries for a room
        Index("ix_waitlist_room_status", "room_id", "status"),
        # Index for finding patron's waitlist entries
        Index("ix_waitlist_patron_status", "patron_id", "status"),
        # Index for cleanup jobs
        Index("ix_waitlist_expires", "expires_at", "status"),
    )


class RoomPrepNote(Base):
    __tablename__ = "room_prep_notes"

    id = Column(Integer, primary_key=True, index=True)

    # Reservation reference
    reservation_id = Column(
        Integer,
        ForeignKey("room_reservations.id", ondelete="CASCADE"),
        nullable=False
    )

    # Staff setup requirements
    setup_instructions = Column(Text, nullable=True)
    equipment_to_setup = Column(ARRAY(String(100)), nullable=True, default=list)
    special_requirements = Column(Text, nullable=True)

    # Status tracking
    is_completed = Column(Boolean, default=False)
    completed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps, server_default=func.now())

    # Relationships
    reservation = relationship("RoomReservation", backref="prep_notes")
    completed_by_user = relationship("User", foreign_keys=[completed_by])

    __table_args__ = (
        # Index for finding incomplete notes for upcoming reservations
        Index("ix_prep_notes_incomplete", "is_completed"),
    )


class RoomUsageStats(Base):
    __tablename__ = "room_usage_stats"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)

    # Time period
    date = Column(DateTime(timezone=True), nullable=False)

    # Metrics
    total_reservations = Column(Integer, default=0)
    completed_reservations = Column(Integer, default=0)
    cancelled_reservations = Column(Integer, default=0)
    no_show_count = Column(Integer, default=0)
    total_hours_booked = Column(Integer, default=0)  # In minutes
    total_attendees = Column(Integer, default=0)

    # Peak hours tracking (JSON with hour -> count mapping)
    hourly_usage = Column(JSONB, nullable=True, default=dict)

    # Relationships
    room = relationship("Room")

    __table_args__ = (
        Index("ix_room_stats_room_date", "room_id", "date", unique=True),
    )


class RoomQueue(Base):
    __tablename__ = "room_queues"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Queue position and timing
    position = Column(Integer, nullable=False)  # Queue order
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    estimated_ready_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    notified_at = Column(DateTime(timezone=True), nullable=True)  # When patron was notified room ready
    ready_timeout_at = Column(DateTime(timezone=True), nullable=True)  # When to expire notification

    # Relationships
    room = relationship("Room")
    patron = relationship("User")

    __table_args__ = (
        Index("ix_queue_room_position", "room_id", "position"),
        Index("ix_queue_room_patron", "room_id", "patron_id"),
    )


class RoomOccupancySensor(Base):
    __tablename__ = "room_occupancy_sensors"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    reservation_id = Column(
        Integer,
        ForeignKey("room_reservations.id", ondelete="SET NULL"),
        nullable=True
    )

    # Sensor data
    is_occupied = Column(Boolean, nullable=False)
    confidence = Column(Integer, default=100)  # Confidence percentage (0-100)
    sensor_type = Column(String(50), nullable=True)  # e.g., "motion", "thermal", "pressure"

    # Timing
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_motion_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    room = relationship("Room")
    reservation = relationship("RoomReservation")

    __table_args__ = (
        Index("ix_sensor_room_time", "room_id", "detected_at"),
    )


class RoomAmenity(Base):
    __tablename__ = "room_amenities"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_available = Column(Boolean, default=True, nullable=False)

    # Relationships
    room = relationship("Room")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_amenity_room", "room_id"),
    )
