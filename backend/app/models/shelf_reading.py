# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ShelfReadingStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ScanResult(StrEnum):
    IN_ORDER = "in_order"
    OUT_OF_ORDER = "out_of_order"
    WRONG_SHELF = "wrong_shelf"


class ScheduleFrequency(StrEnum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class ShelfReadingSession(Base):

    __tablename__ = "shelf_reading_sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Scope - which shelf/range is being read
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    location = Column(String(100), nullable=False)  # e.g., "Adult Fiction A-3"
    call_number_start = Column(String(100), nullable=True)  # Start of range
    call_number_end = Column(String(100), nullable=True)  # End of range

    # Status
    status = Column(
        String(50),
        default=ShelfReadingStatus.IN_PROGRESS,
        nullable=False,
    )

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    paused_at = Column(DateTime(timezone=True), nullable=True)

    # Stats (denormalized for quick access)
    total_items_scanned = Column(Integer, default=0, nullable=False)
    items_in_order = Column(Integer, default=0, nullable=False)
    items_out_of_order = Column(Integer, default=0, nullable=False)
    items_wrong_shelf = Column(Integer, default=0, nullable=False)
    accuracy_percentage = Column(Float, default=0.0, nullable=False)

    # Who
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Gamification
    points_earned = Column(Integer, default=0, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    branch = relationship("Branch")
    created_by = relationship("User")
    scans = relationship(
        "ShelfReadingScan", back_populates="session", cascade="all, delete-orphan",
        order_by="ShelfReadingScan.scan_order",
    )


class ShelfReadingScan(Base):

    __tablename__ = "shelf_reading_scans"
    __table_args__ = (
        UniqueConstraint("session_id", "item_copy_id", name="uq_shelf_scan_session_item"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("shelf_reading_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_copy_id = Column(Integer, ForeignKey("item_copies.id", ondelete="CASCADE"), nullable=False)

    # Scan data
    scan_order = Column(Integer, nullable=False)  # Order in which item was scanned
    scanned_call_number = Column(String(100), nullable=True)  # Call number as scanned
    previous_call_number = Column(String(100), nullable=True)  # Call number of previous item

    # Result
    result = Column(
        String(50),
        nullable=False,
    )
    expected_location = Column(String(100), nullable=True)  # Where item should be
    correct_position_after = Column(String(100), nullable=True)  # Call number it should follow

    # Metadata
    scanned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    scanned_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Relationships
    session = relationship("ShelfReadingSession", back_populates="scans")
    item_copy = relationship("ItemCopy")
    scanned_by = relationship("User")


class ShelfReadingSchedule(Base):

    __tablename__ = "shelf_reading_schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Scope
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    location = Column(String(100), nullable=False)
    call_number_start = Column(String(100), nullable=True)
    call_number_end = Column(String(100), nullable=True)

    # Schedule
    frequency = Column(
        String(50),
        nullable=False,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    last_completed_at = Column(DateTime(timezone=True), nullable=True)
    next_due_at = Column(DateTime(timezone=True), nullable=True)

    # Assigned staff
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Metadata
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    branch = relationship("Branch")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
