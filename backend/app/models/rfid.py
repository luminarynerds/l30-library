# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from .mixins import TimestampMixin


class RFIDReaderType(StrEnum):
    CIRCULATION_DESK = "circulation_desk"  # Fixed reader at circulation desk
    SELF_CHECKOUT = "self_checkout"  # Self-checkout kiosk
    SECURITY_GATE = "security_gate"  # Security/exit gate
    HANDHELD = "handheld"  # Portable inventory scanner
    SHELF_READER = "shelf_reader"  # Fixed shelf scanning
    BOOK_DROP = "book_drop"  # Automated return station


class RFIDReaderStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class RFIDProtocol(StrEnum):
    SIP2 = "sip2"  # Standard Interchange Protocol 2
    NCIP = "ncip"  # NISO Circulation Interchange Protocol
    REST_API = "rest_api"  # Modern REST API
    TCP_SOCKET = "tcp_socket"  # Raw TCP socket communication
    SERIAL = "serial"  # Serial/RS-232 communication


class RFIDSessionType(StrEnum):
    BATCH_CHECKOUT = "batch_checkout"  # Multiple items checkout
    BATCH_CHECKIN = "batch_checkin"  # Multiple items return
    INVENTORY_SCAN = "inventory_scan"  # Inventory audit mode
    SHELF_READ = "shelf_read"  # Shelf reading verification
    TAG_PROGRAMMING = "tag_programming"  # Programming new tags
    SECURITY_MONITOR = "security_monitor"  # Security gate monitoring


class SecurityAlertType(StrEnum):
    UNAUTHORIZED_EXIT = "unauthorized_exit"  # Non-desensitized item at gate
    MISSING_TAG = "missing_tag"  # Item without RFID tag
    INVALID_TAG = "invalid_tag"  # Unrecognized tag ID
    MULTIPLE_ALERTS = "multiple_alerts"  # Multiple security violations


class RFIDReader(Base, TimestampMixin):
    __tablename__ = "rfid_readers"

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    name = Column(String(100), nullable=False)
    serial_number = Column(String(100), unique=True, nullable=False)
    location = Column(String(200))  # Physical location (e.g., "Main Entrance Gate 1")

    # Type and protocol
    reader_type = Column(
        String(50),
    )
    protocol = Column(
        String(50),
        default=RFIDProtocol.SIP2,
        nullable=False,
    )

    # Connection details
    ip_address = Column(String(45))  # Supports IPv6
    port = Column(Integer)
    connection_string = Column(Text)  # For serial/other protocols

    # Authentication (encrypted in production)
    username = Column(String(100))
    password = Column(String(255))  # Should be encrypted

    # Status and health
    status = Column(
        String(50),
        default=RFIDReaderStatus.OFFLINE,
        nullable=False,
    )
    last_heartbeat = Column(DateTime(timezone=True))
    last_error = Column(Text)

    # Configuration
    antenna_count = Column(Integer, default=1)
    power_level = Column(Float)  # dBm
    read_interval_ms = Column(Integer, default=100)  # Milliseconds between reads
    config_metadata = Column(JSONB, default={})

    # Audit
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    tags = relationship("RFIDTag", back_populates="programmed_by_reader")
    sessions = relationship("RFIDSession", back_populates="reader")
    security_alerts = relationship("SecurityAlert", back_populates="reader")


class RFIDTag(Base, TimestampMixin):
    __tablename__ = "rfid_tags"
    __table_args__ = (
        UniqueConstraint("tag_id", name="uq_rfid_tag_id"),
        Index("ix_rfid_tags_item_barcode", "item_barcode"),
        Index("ix_rfid_tags_security_bit", "security_bit"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Tag identification (EPC or UID)
    tag_id = Column(String(64), nullable=False, unique=True)  # Hex-encoded tag ID

    # Link to library item
    item_barcode = Column(
        String(50),
        ForeignKey("item_copies.barcode", ondelete="SET NULL"),
    )

    # Security
    security_bit = Column(Boolean, default=True, nullable=False)  # True = active (not checked out)
    afi_byte = Column(String(4))  # Application Family Identifier (hex)
    eas_enabled = Column(Boolean, default=True)  # Electronic Article Surveillance

    # Tag metadata
    tag_type = Column(String(50))  # ISO 15693, ISO 14443, etc.
    memory_size = Column(Integer)  # Bytes
    manufacturer = Column(String(100))

    # Programming info
    programmed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    programmed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    programmed_by_reader_id = Column(Integer, ForeignKey("rfid_readers.id", ondelete="SET NULL"))
    last_read_at = Column(DateTime(timezone=True))
    read_count = Column(Integer, default=0)

    # Data stored on tag (subset of item data for quick reads)
    tag_data = Column(JSONB, default={})  # Encoded item info

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    deactivated_at = Column(DateTime(timezone=True))
    deactivation_reason = Column(String(255))

    # Audit

    # Relationships
    item_copy = relationship(
        "ItemCopy",
        foreign_keys=[item_barcode],
        primaryjoin="RFIDTag.item_barcode == ItemCopy.barcode",
    )
    programmed_by = relationship("User")
    programmed_by_reader = relationship("RFIDReader", back_populates="tags")


class RFIDSession(Base):
    __tablename__ = "rfid_sessions"
    __table_args__ = (
        Index("ix_rfid_sessions_reader_started", "reader_id", "started_at"),
        Index("ix_rfid_sessions_type_status", "session_type", "is_active"),
    )

    id = Column(Integer, primary_key=True)

    # Session identification
    session_type = Column(
        String(50),
    )

    # Reader and operator
    reader_id = Column(Integer, ForeignKey("rfid_readers.id", ondelete="CASCADE"), nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # For batch checkout/checkin
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # For inventory/shelf reading
    inventory_audit_id = Column(Integer, ForeignKey("inventory_audits.id", ondelete="SET NULL"))
    target_location = Column(String(100))  # Location being scanned

    # Session timing
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, nullable=False)

    # Statistics
    tags_scanned = Column(Integer, default=0)
    tags_processed = Column(Integer, default=0)
    tags_failed = Column(Integer, default=0)

    # Session metadata
    session_metadata = Column(JSONB, default={})

    # Relationships
    reader = relationship("RFIDReader", back_populates="sessions")
    operator = relationship("User", foreign_keys=[operator_id])
    patron = relationship("User", foreign_keys=[patron_id])
    inventory_audit = relationship("InventoryAudit")
    scans = relationship("RFIDScan", back_populates="session", cascade="all, delete-orphan")


class RFIDScan(Base):
    __tablename__ = "rfid_scans"
    __table_args__ = (
        Index("ix_rfid_scans_session_scanned", "session_id", "scanned_at"),
        Index("ix_rfid_scans_tag_id", "tag_id"),
    )

    id = Column(Integer, primary_key=True)

    # Session reference
    session_id = Column(
        Integer,
        ForeignKey("rfid_sessions.id", ondelete="CASCADE"),
    )

    # Tag identification
    tag_id = Column(String(64), nullable=False)  # The scanned tag ID
    rfid_tag_id = Column(
        Integer, ForeignKey("rfid_tags.id", ondelete="SET NULL")
    )  # Link to registered tag

    # Scan result
    item_barcode = Column(String(50))  # Resolved barcode
    item_title = Column(String(500))  # Cached for display

    # Processing status
    processed = Column(Boolean, default=False)
    process_result = Column(String(50))  # checkout_success, checkin_success, error, etc.
    error_message = Column(Text)

    # Signal quality
    signal_strength = Column(Float)  # RSSI in dBm
    antenna_id = Column(Integer)

    # Location (for inventory/shelf reading)
    found_at_location = Column(String(100))
    expected_location = Column(String(100))
    is_misplaced = Column(Boolean, default=False)

    # Timing
    scanned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True))

    # Relationships
    session = relationship("RFIDSession", back_populates="scans")
    rfid_tag = relationship("RFIDTag")


class SecurityAlert(Base):
    __tablename__ = "security_alerts"
    __table_args__ = (
        Index("ix_security_alerts_reader_created", "reader_id", "created_at"),
        Index("ix_security_alerts_resolved", "is_resolved"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Alert source
    reader_id = Column(Integer, ForeignKey("rfid_readers.id", ondelete="CASCADE"), nullable=False)

    # Alert type
    alert_type = Column(
        String(50),
    )

    # Tag/Item info
    tag_id = Column(String(64))
    item_barcode = Column(String(50))
    item_title = Column(String(500))

    # Alert details
    description = Column(Text)
    signal_strength = Column(Float)

    # Photo capture (if supported by gate)
    photo_url = Column(Text)

    # Resolution
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    resolution_notes = Column(Text)

    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    reader = relationship("RFIDReader", back_populates="security_alerts")
    resolved_by = relationship("User")
