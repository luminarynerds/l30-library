# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, Boolean
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class SIP2CommandType(StrEnum):

    # Requests (odd numbers, SC -> ACS)
    PATRON_STATUS_REQUEST = "23"
    CHECKOUT_REQUEST = "11"
    CHECKIN_REQUEST = "09"
    BLOCK_PATRON_REQUEST = "01"
    SC_STATUS_REQUEST = "99"
    LOGIN_REQUEST = "93"
    PATRON_INFO_REQUEST = "63"
    END_PATRON_SESSION = "35"
    FEE_PAID = "37"
    ITEM_INFO_REQUEST = "17"
    ITEM_STATUS_UPDATE = "19"
    PATRON_ENABLE = "25"
    HOLD_REQUEST = "15"
    RENEW_REQUEST = "29"
    RENEW_ALL_REQUEST = "65"

    # Responses (even numbers, ACS -> SC)
    PATRON_STATUS_RESPONSE = "24"
    CHECKOUT_RESPONSE = "12"
    CHECKIN_RESPONSE = "10"
    ACS_STATUS_RESPONSE = "98"
    LOGIN_RESPONSE = "94"
    PATRON_INFO_RESPONSE = "64"
    END_SESSION_RESPONSE = "36"
    FEE_PAID_RESPONSE = "38"
    ITEM_INFO_RESPONSE = "18"
    ITEM_STATUS_UPDATE_RESPONSE = "20"
    PATRON_ENABLE_RESPONSE = "26"
    HOLD_RESPONSE = "16"
    RENEW_RESPONSE = "30"
    RENEW_ALL_RESPONSE = "66"


class SIP2Transaction(Base):

    __tablename__ = "sip2_transactions"

    id = Column(Integer, primary_key=True, index=True)

    # Session information
    session_id = Column(String(64), nullable=False)
    terminal_id = Column(String(100), nullable=True)
    institution_id = Column(String(100), nullable=True)

    # Request details
    request_id = Column(String(32), nullable=True, index=True)
    command = Column(SQLEnum(SIP2CommandType, values_callable=lambda x: [e.value for e in x]), nullable=False)

    # Transaction participants
    patron_id = Column(String(100), nullable=True)
    item_id = Column(String(100), nullable=True, index=True)

    # Foreign keys to actual records (nullable for audit trail preservation)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    catalog_item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    checkout_id = Column(
        Integer,
        ForeignKey("checkouts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Transaction outcome
    success = Column(Boolean, default=False, nullable=False)
    error_message = Column(String(500), nullable=True)

    # Full request/response for debugging (consider truncating for privacy)
    request_message = Column(Text, nullable=True)
    response_message = Column(Text, nullable=True)

    # Additional context stored as JSON
    # e.g., due dates, fine amounts, screen messages
    transaction_data = Column(JSON, nullable=True)

    # Client information
    client_ip = Column(String(45), nullable=True)
    client_port = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    response_at = Column(DateTime(timezone=True), nullable=True)

    # Processing time in milliseconds
    processing_time_ms = Column(Integer, nullable=True)

    # Relationships
    user = relationship("User", backref="sip2_transactions")
    catalog_item = relationship("CatalogItem", backref="sip2_transactions")
    checkout = relationship("Checkout", backref="sip2_transactions")

    # Indexes for common query patterns
    __table_args__ = (
        # For querying transactions by session
        Index("ix_sip2_session_created", "session_id", "created_at"),
        # For querying transactions by terminal
        Index("ix_sip2_terminal_created", "terminal_id", "created_at"),
        # For querying patron history
        Index("ix_sip2_patron_created", "patron_id", "created_at"),
        # For querying by command type and success
        Index("ix_sip2_command_success", "command", "success"),
        # For daily reports
        Index("ix_sip2_created_command", "created_at", "command"),
    )

    def __repr__(self) -> str:
        return (
            f"<SIP2Transaction(id={self.id}, command={self.command}, "
            f"session={self.session_id[:8]}..., success={self.success})>"
        )


class SIP2Terminal(Base):

    __tablename__ = "sip2_terminals"

    id = Column(Integer, primary_key=True, index=True)

    # Terminal identification
    terminal_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Location information
    location = Column(String(200), nullable=True)
    institution_id = Column(String(100), nullable=True)

    # Authentication
    password_hash = Column(String(255), nullable=True)

    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    allow_checkout = Column(Boolean, default=True, nullable=False)
    allow_checkin = Column(Boolean, default=True, nullable=False)
    allow_renewal = Column(Boolean, default=True, nullable=False)
    allow_patron_info = Column(Boolean, default=True, nullable=False)

    # Terminal capabilities/settings stored as JSON
    settings = Column(JSON, nullable=True)

    # Status tracking
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    last_ip = Column(String(45), nullable=True)

    # Timestamps, server_default=func.now())

    def __repr__(self) -> str:
        return f"<SIP2Terminal(id={self.id}, terminal_id={self.terminal_id}, active={self.is_active})>"
