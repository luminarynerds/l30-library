# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func

from ..core.database import Base


class NotificationChannel(StrEnum):
    EMAIL = "email"
    SMS = "sms"


class NotificationFailureStatus(StrEnum):
    PENDING = "pending"        # Awaiting retry
    RETRYING = "retrying"      # Currently being retried
    DELIVERED = "delivered"    # Successfully delivered on retry
    ABANDONED = "abandoned"    # Max retries exceeded


class FailedNotificationRecord(Base):
    __tablename__ = "failed_notification_records"

    id = Column(Integer, primary_key=True, index=True)

    # Channel and template identification
    channel = Column(
        SQLEnum(NotificationChannel, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    template_name = Column(String(255), nullable=False, index=True)  # e.g., "password_reset", "hold_ready"

    # Recipient (redacted for privacy -- store hash or last 4 chars)
    recipient_hash = Column(String(64), nullable=False)  # SHA-256 hash of email/phone
    recipient_hint = Column(String(100), nullable=True)   # e.g., "***@gmail.com", "***@luminarynerds.com", or "***4567"

    # Original send parameters (encrypted or minimal)
    subject = Column(String(500), nullable=True)          # Email subject (NULL for SMS)
    send_params = Column(JSON, nullable=True)             # Non-sensitive params for retry

    # Error information
    error_message = Column(Text, nullable=False)
    error_type = Column(String(255), nullable=True)       # "timeout", "api_error", "validation"
    http_status_code = Column(Integer, nullable=True)     # Response status from provider

    # Status tracking
    status = Column(
        SQLEnum(NotificationFailureStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=NotificationFailureStatus.PENDING,
        index=True,
    )

    # Retry tracking
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Resolution
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_failed_notif_channel_status', 'channel', 'status'),
        Index('ix_failed_notif_template_status', 'template_name', 'status'),
        Index('ix_failed_notif_pending_retry', 'status', 'next_retry_at'),
        Index('ix_failed_notif_created', 'channel', 'created_at'),
    )

    def __repr__(self) -> str:
        return (
            f"<FailedNotificationRecord(id={self.id}, channel={self.channel}, "
            f"template={self.template_name}, status={self.status})>"
        )


class NotificationMetrics(Base):
    __tablename__ = "notification_metrics"

    id = Column(Integer, primary_key=True, index=True)

    # Dimensions
    channel = Column(SQLEnum(NotificationChannel, values_callable=lambda x: [e.value for e in x]), nullable=False)
    template_name = Column(String(255), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)  # Start of aggregation window

    # Counters
    sent_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failure_count = Column(Integer, nullable=False, default=0)
    timeout_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('ix_notif_metrics_lookup', 'channel', 'template_name', 'window_start', unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationMetrics(channel={self.channel}, template={self.template_name}, "
            f"sent={self.sent_count}, failed={self.failure_count})>"
        )
