# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.models.mixins import TimestampMixin
from ..core.database import Base


class LinkStatus(StrEnum):
    healthy = "healthy"
    degraded = "degraded"  # Slow response but accessible
    broken = "broken"  # 4xx/5xx errors
    timeout = "timeout"  # Request timed out
    dns_error = "dns_error"  # DNS resolution failed
    ssl_error = "ssl_error"  # SSL certificate issues
    redirect_loop = "redirect_loop"  # Too many redirects
    unknown = "unknown"  # Check not yet performed


class LinkSource(StrEnum):
    palace = "palace"
    external_resource = "external_resource"
    catalog_link = "catalog_link"
    lesson_resource = "lesson_resource"
    digital_collection = "digital_collection"
    vendor = "vendor"
    other = "other"


class LinkHealthCheck(Base):
    __tablename__ = "link_health_checks"

    id = Column(Integer, primary_key=True, index=True)

    # URL being checked
    url = Column(String(2000), nullable=False, index=True)
    url_hash = Column(String(64), nullable=False, index=True)  # SHA256 for indexing long URLs

    # Source identification
    source = Column(
        SQLEnum(LinkSource, name="linksource", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=LinkSource.other,
        nullable=False,
        index=True,
    )
    source_id = Column(Integer, nullable=True)  # ID in source table (e.g., external_resource.id)
    source_name = Column(String(255), nullable=True)  # Human-readable reference

    # Check results
    status = Column(
        SQLEnum(LinkStatus, name="linkstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=LinkStatus.unknown,
        nullable=False,
        index=True,
    )
    http_status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=True)  # Response time in milliseconds
    error_message = Column(Text, nullable=True)

    # Redirect tracking
    final_url = Column(String(2000), nullable=True)  # URL after redirects
    redirect_count = Column(Integer, default=0)

    # SSL info
    ssl_valid = Column(Boolean, nullable=True)
    ssl_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Check metadata
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    check_duration_ms = Column(Float, nullable=True)

    # Additional response info
    content_type = Column(String(100), nullable=True)
    content_length = Column(Integer, nullable=True)

    __table_args__ = (
        # Index for finding latest checks per URL
        Index("ix_link_health_checks_url_hash_checked", "url_hash", "checked_at"),
        # Index for finding broken links
        Index("ix_link_health_checks_status_checked", "status", "checked_at"),
        # Index for source-based queries
        Index("ix_link_health_checks_source_status", "source", "status"),
    )


class LinkHealthSummary(Base):
    __tablename__ = "link_health_summaries"

    id = Column(Integer, primary_key=True, index=True)

    # URL identification
    url = Column(String(2000), nullable=False)
    url_hash = Column(String(64), nullable=False, unique=True, index=True)

    # Source identification
    source = Column(
        SQLEnum(LinkSource, name="linksource", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=LinkSource.other,
        nullable=False,
        index=True,
    )
    source_id = Column(Integer, nullable=True)
    source_name = Column(String(255), nullable=True)

    # Current status
    current_status = Column(
        SQLEnum(LinkStatus, name="linkstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=LinkStatus.unknown,
        nullable=False,
        index=True,
    )
    last_http_status = Column(Integer, nullable=True)
    last_error_message = Column(Text, nullable=True)

    # Performance metrics
    avg_response_time_ms = Column(Float, nullable=True)
    last_response_time_ms = Column(Float, nullable=True)

    # Reliability metrics
    total_checks = Column(Integer, default=0)
    successful_checks = Column(Integer, default=0)
    failed_checks = Column(Integer, default=0)
    uptime_percentage = Column(Float, nullable=True)

    # Consecutive failure tracking for alerts
    consecutive_failures = Column(Integer, default=0)
    last_successful_at = Column(DateTime(timezone=True), nullable=True)
    last_failed_at = Column(DateTime(timezone=True), nullable=True)

    # Alert status
    alert_sent = Column(Boolean, default=False)
    alert_sent_at = Column(DateTime(timezone=True), nullable=True)
    alert_acknowledged = Column(Boolean, default=False)
    alert_acknowledged_by = Column(Integer, nullable=True)  # user_id

    # Timestamps
    first_checked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)

    # Monitoring configuration
    is_monitored = Column(Boolean, default=True, index=True)
    check_interval_minutes = Column(Integer, default=60)  # How often to check
    priority = Column(Integer, default=5)  # 1=critical, 10=low priority

    __table_args__ = (
        # Index for monitoring queries
        Index("ix_link_health_summaries_monitored_status", "is_monitored", "current_status"),
        # Index for alert queries
        Index("ix_link_health_summaries_alert", "alert_sent", "consecutive_failures"),
    )


class LinkHealthConfig(Base):
    __tablename__ = "link_health_config"

    id = Column(Integer, primary_key=True, index=True)

    # Check settings
    default_timeout_seconds = Column(Integer, default=30)
    default_check_interval_minutes = Column(Integer, default=60)
    max_redirects = Column(Integer, default=10)
    user_agent = Column(String(255), default="L30Library-LinkChecker/1.0")

    # Alert thresholds
    alert_on_consecutive_failures = Column(Integer, default=3)
    alert_on_response_time_ms = Column(Integer, default=5000)  # Alert if >5s
    degraded_response_time_ms = Column(Integer, default=2000)  # Mark degraded if >2s

    # Retention
    keep_history_days = Column(Integer, default=90)  # How long to keep check history

    # Feature flags
    monitoring_enabled = Column(Boolean, default=True)
    ssl_check_enabled = Column(Boolean, default=True)
    auto_disable_broken_links = Column(Boolean, default=False)

    # Email notification settings
    notify_on_broken = Column(Boolean, default=True)
    notify_on_recovered = Column(Boolean, default=True)
    notification_emails = Column(JSONB, default=[])  # List of email addresses

    # Rate limiting
    max_concurrent_checks = Column(Integer, default=10)
    delay_between_checks_ms = Column(Integer, default=100)

    # Timestamps, server_default=func.now())


class LinkHealthAlert(TimestampMixin, Base):
    __tablename__ = "link_health_alerts"

    id = Column(Integer, primary_key=True, index=True)

    # Link reference
    url_hash = Column(String(64), nullable=False, index=True)
    url = Column(String(2000), nullable=False)
    source = Column(
        SQLEnum(LinkSource, name="linksource", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Alert details
    alert_type = Column(String(50), nullable=False)  # broken, degraded, ssl_expiring, recovered
    severity = Column(String(20), default="warning")  # info, warning, critical
    message = Column(Text, nullable=False)

    # Status tracking
    status = Column(String(20), default="open", index=True)  # open, acknowledged, resolved
    acknowledged_by = Column(Integer, nullable=True)  # user_id
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Timestamps, server_default=func.now())

    __table_args__ = (
        Index("ix_link_health_alerts_status_created", "status", "created_at"),
    )
