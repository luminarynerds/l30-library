# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, StrEnum
from typing import Optional

from sqlalchemy import (
    JSON, Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey,
    Integer, String, Text, func
)
from sqlalchemy.orm import relationship

from ..core.database import Base


class MonitoringAlertSeverity(StrEnum):
    LOW = "low"              # Yellow - monitor but not urgent
    MEDIUM = "medium"        # Orange - needs attention soon
    HIGH = "high"            # Red - urgent action required
    CRITICAL = "critical"    # Red + alarm - immediate action required


class PrivacyChangeType(StrEnum):
    CONTENT_VISIBILITY = "content_visibility"      # Public/private toggle on content
    PROFILE_VISIBILITY = "profile_visibility"      # Public/private on profile
    LIST_VISIBILITY = "list_visibility"            # Sharing status of reading lists
    PREFERENCE_CHANGE = "preference_change"        # Notification/data sharing preferences
    BULK_CHANGE = "bulk_change"                    # Multiple items changed at once


class PrivacyAlert(Base):
    __tablename__ = "privacy_alerts"

    id = Column(Integer, primary_key=True, index=True)

    # Reference information
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user = relationship("User", foreign_keys=[user_id])

    # Alert metadata
    alert_type = Column(SQLEnum(PrivacyChangeType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    severity = Column(
        SQLEnum(MonitoringAlertSeverity, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
        default=MonitoringAlertSeverity.MEDIUM
    )

    # Details about the pattern detected
    change_count = Column(Integer, default=1)           # Number of changes in the pattern
    time_window_minutes = Column(Integer, default=60)   # Window in which changes occurred

    # Affected resources
    resource_type = Column(String(50))                 # e.g., "list", "book", "profile"
    resource_ids = Column(JSON, default=dict)          # {resource_id: change_details}

    # Pattern information
    old_visibility_states = Column(JSON)               # Before state
    new_visibility_states = Column(JSON)               # After state

    # Metadata
    description = Column(Text)                         # Human-readable description
    is_anomalous = Column(Boolean, default=True)       # True if pattern is unusual
    is_acknowledged = Column(Boolean, default=False, index=True)
    acknowledged_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    acknowledged_at = Column(DateTime(timezone=True))
    acknowledgment_notes = Column(Text)

    # Timestamps
    detected_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<PrivacyAlert(id={self.id}, user_id={self.user_id}, "
            f"type={self.alert_type}, severity={self.severity})>"
        )


class ModerationAlert(Base):
    __tablename__ = "moderation_alerts"

    id = Column(Integer, primary_key=True, index=True)

    # Alert type
    alert_type = Column(String(50), nullable=False, index=True)  # queue_backlog, overdue_item, etc.
    severity = Column(
        SQLEnum(MonitoringAlertSeverity, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
        default=MonitoringAlertSeverity.MEDIUM
    )

    # Queue metrics that triggered alert
    pending_count = Column(Integer, default=0)
    overdue_count = Column(Integer, default=0)
    oldest_item_age_hours = Column(Integer, default=0)  # Hours in queue
    average_turnaround_hours = Column(Float, default=0.0)

    # Thresholds crossed
    threshold_exceeded = Column(String(100))  # e.g., "pending_count > 10"
    threshold_value = Column(Integer)
    actual_value = Column(Integer)

    # Specific items if applicable
    review_items = Column(JSON, default=dict)  # {review_id: details}

    # Status
    description = Column(Text)
    is_resolved = Column(Boolean, default=False, index=True)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Timestamps
    triggered_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<ModerationAlert(id={self.id}, type={self.alert_type}, "
            f"severity={self.severity})>"
        )


class AlertThreshold(Base):
    __tablename__ = "alert_thresholds"

    id = Column(Integer, primary_key=True, index=True)

    # Threshold definition
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    category = Column(String(50), nullable=False)  # privacy, moderation, system
    threshold_type = Column(String(50))  # count, time, percentage

    # Threshold values
    warning_level = Column(Integer)     # Triggers MEDIUM alert
    critical_level = Column(Integer)    # Triggers HIGH/CRITICAL alert

    # Configuration
    time_window_minutes = Column(Integer, default=60)  # Period for counting
    enabled = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return (
            f"<AlertThreshold(name={self.name}, warning={self.warning_level}, "
            f"critical={self.critical_level})>"
        )


class SystemHealth(Base):
    __tablename__ = "system_health"

    id = Column(Integer, primary_key=True, index=True)

    # Status
    status = Column(String(20))  # healthy, degraded, unhealthy
    status_reason = Column(Text)

    # Share/Sharing events
    share_events_last_hour = Column(Integer, default=0)
    share_events_last_24h = Column(Integer, default=0)

    # Database metrics
    db_connection_active = Column(Integer, default=0)
    db_connection_idle = Column(Integer, default=0)
    db_slow_queries = Column(Integer, default=0)
    db_query_avg_time_ms = Column(Float, default=0.0)

    # Error tracking
    error_count_last_hour = Column(Integer, default=0)
    error_count_last_24h = Column(Integer, default=0)
    error_rate_percent = Column(Float, default=0.0)

    # API performance
    api_response_p50_ms = Column(Float, default=0.0)
    api_response_p95_ms = Column(Float, default=0.0)
    api_response_p99_ms = Column(Float, default=0.0)

    # Cache metrics
    cache_hit_rate_percent = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<SystemHealth(status={self.status}, created_at={self.created_at})>"
