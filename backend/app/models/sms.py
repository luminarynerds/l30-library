# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import time
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean, Column, DateTime, Integer, String, Text, JSON, Numeric,
    ForeignKey, UniqueConstraint, Time, Index
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base


class SMSDeliveryStatus(StrEnum):
    PENDING = "pending"          # Queued for sending
    SENT = "sent"                # Sent to provider (Twilio)
    DELIVERED = "delivered"      # Confirmed delivered to phone
    FAILED = "failed"            # Delivery failed
    UNDELIVERED = "undelivered"  # Could not reach phone
    CANCELLED = "cancelled"      # Cancelled before sending
    QUEUED_DND = "queued_dnd"    # Queued due to DND hours


class SMSNotificationType(StrEnum):
    # Circulation notifications
    HOLD_READY = "hold_ready"
    HOLD_EXPIRED = "hold_expired"
    DUE_DATE_REMINDER = "due_date_reminder"
    OVERDUE_NOTICE = "overdue_notice"
    CHECKOUT_RECEIPT = "checkout_receipt"

    # Event notifications
    EVENT_REMINDER = "event_reminder"
    EVENT_CANCELLED = "event_cancelled"
    EVENT_UPDATED = "event_updated"

    # Room/Space notifications
    WALK_IN_ALERT = "walk_in_alert"

    # Account notifications
    PHONE_VERIFICATION = "phone_verification"
    ACCOUNT_ALERT = "account_alert"

    # Staff/Admin
    AD_HOC = "ad_hoc"


class SMSQueue(Base, TimestampMixin):

    __tablename__ = "sms_queue"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    notification_type = Column(
        SQLEnum(SMSNotificationType, name="smsnotificationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    status = Column(
        SQLEnum(SMSDeliveryStatus, name="smsdeliverystatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=SMSDeliveryStatus.PENDING,
        nullable=False
    )

    # Recipient info
    recipient_phone = Column(String(20), nullable=False, index=True)
    recipient_name = Column(String(200), nullable=True)

    # Message content
    message_body = Column(Text, nullable=False)
    message_segments = Column(Integer, default=1, nullable=False)  # Number of SMS segments

    # Context data for template rendering
    context_data = Column(JSON, nullable=True)

    # Twilio tracking
    twilio_sid = Column(String(50), nullable=True, index=True)
    twilio_status = Column(String(50), nullable=True)
    twilio_error_code = Column(String(20), nullable=True)
    twilio_error_message = Column(Text, nullable=True)

    # Scheduling
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)

    # Retry tracking
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Cost tracking
    cost_cents = Column(Integer, nullable=True)  # Cost in cents (USD)

    # Staff/admin who initiated (for ad-hoc messages)
    initiated_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    initiated_by = relationship("User", foreign_keys=[initiated_by_user_id])

    # Indexes for common queries
    __table_args__ = (
        Index('ix_sms_queue_status_scheduled', 'status', 'scheduled_for'),
        Index('ix_sms_queue_user_type', 'user_id', 'notification_type'),
    )


class SMSDeliveryLog(Base):

    __tablename__ = "sms_delivery_log"

    id = Column(Integer, primary_key=True)
    sms_queue_id = Column(
        Integer, ForeignKey("sms_queue.id", ondelete="CASCADE"),
        nullable=False
    )

    # Status change tracking
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)

    # Twilio callback data
    twilio_sid = Column(String(50), nullable=True)
    twilio_status = Column(String(50), nullable=True)
    twilio_error_code = Column(String(20), nullable=True)
    twilio_error_message = Column(Text, nullable=True)

    # Raw callback payload for debugging
    raw_callback_data = Column(JSON, nullable=True)

    # Relationships
    sms_queue = relationship("SMSQueue")


class SMSCostRecord(Base):

    __tablename__ = "sms_cost_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Time period (monthly aggregation)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)

    notification_type = Column(
        SQLEnum(SMSNotificationType, name="smsnotificationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Counts
    messages_sent = Column(Integer, default=0, nullable=False)
    messages_delivered = Column(Integer, default=0, nullable=False)
    messages_failed = Column(Integer, default=0, nullable=False)
    total_segments = Column(Integer, default=0, nullable=False)

    # Cost in cents (USD)
    total_cost_cents = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint('user_id', 'year', 'month', 'notification_type',
                        name='uq_sms_cost_user_period_type'),
        Index('ix_sms_cost_period', 'year', 'month'),
    )


class SMSTemplate(Base):

    __tablename__ = "sms_templates"

    id = Column(Integer, primary_key=True, index=True)

    notification_type = Column(
        SQLEnum(SMSNotificationType, name="smsnotificationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        unique=True
    )

    # Template content with placeholders like {patron_name}, {book_title}
    template_body = Column(Text, nullable=False)

    # Maximum character limit for this template
    max_chars = Column(Integer, default=160, nullable=False)

    # Whether to allow multi-part messages
    allow_multipart = Column(Boolean, default=True, nullable=False)
    max_segments = Column(Integer, default=3, nullable=False)

    # Template metadata
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit fields
    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    updated_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    updated_by = relationship("User", foreign_keys=[updated_by_user_id])


class SMSOptOut(Base):

    __tablename__ = "sms_opt_outs"

    id = Column(Integer, primary_key=True)

    # Phone number that opted out (normalized E.164 format)
    phone_number = Column(String(20), nullable=False, unique=True)

    # Associated user (may be null if phone changed)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Opt-out details
    opted_out_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    opt_out_message = Column(Text, nullable=True)  # The actual STOP message received
    twilio_sid = Column(String(50), nullable=True)

    # Opt-back-in tracking
    opted_in_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)  # False if opted back in, server_default=func.now())

    # Relationships
    user = relationship("User")


class DoNotDisturbHours(Base):

    __tablename__ = "do_not_disturb_hours"

    id = Column(Integer, primary_key=True)

    # If user_id is null, this is the global/default configuration
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True
    )

    # DND time range (in user's local timezone or library timezone)
    start_time = Column(Time, nullable=False, default=time(21, 0))  # 9 PM
    end_time = Column(Time, nullable=False, default=time(8, 0))     # 8 AM

    # Timezone for the DND hours
    timezone = Column(String(50), default="America/New_York", nullable=False)

    # Days of week when DND applies (JSON array of day numbers, 0=Monday, 6=Sunday)
    # Default: all days
    active_days = Column(JSON, default=[0, 1, 2, 3, 4, 5, 6], nullable=False)

    is_enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User")

    __table_args__ = (
        # Only one global config (user_id = null) allowed
        # Each user can have only one config
        UniqueConstraint('user_id', name='uq_dnd_user'),
    )


class PhoneVerification(Base):

    __tablename__ = "phone_verifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Phone number being verified (normalized E.164 format)
    phone_number = Column(String(20), nullable=False)

    # Verification code (hashed)
    verification_code_hash = Column(String(255), nullable=False)

    # Tracking
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Status
    verified_at = Column(DateTime(timezone=True), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Twilio tracking
    twilio_sid = Column(String(50), nullable=True)

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index('ix_phone_verification_user_phone', 'user_id', 'phone_number'),
    )
