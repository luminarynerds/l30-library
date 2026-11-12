# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, Index, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import and_
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


# Journey types tracked
JOURNEY_TYPES = {
    "search_to_hold": "Search→Hold",
    "register": "Register",
    "renewal": "Renewal",
    "account_self_service": "Account Self-Service",
    "staff_checkin": "Staff Check-in",
}


class JourneyEvent(Base, TimestampMixin):
    __tablename__ = "journey_events"

    id = Column(Integer, primary_key=True, index=True)

    # Journey identification
    journey_type = Column(String(50), nullable=False, index=True)  # e.g., "search_to_hold"
    session_id = Column(String(255), nullable=False, index=True)  # Session identifier (hashed)
    user_id = Column(String(255), nullable=True, index=True)  # User identifier (hashed/null for unauth)

    # Event sequencing
    event_sequence = Column(Integer, nullable=False)  # Order within journey (1, 2, 3, ...)
    stage_name = Column(String(100), nullable=False)  # e.g., "search_initiated", "results_displayed", "hold_placed"

    # Timing data
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    time_since_journey_start_ms = Column(Integer, nullable=False)  # Milliseconds since journey began
    time_since_previous_event_ms = Column(Integer, nullable=True)  # Milliseconds since previous stage

    # Device/context segmentation
    device_type = Column(String(50), nullable=True)  # "mobile", "tablet", "desktop"
    user_type = Column(String(50), nullable=True)  # "returning", "new", "guest"
    accessibility_mode = Column(Boolean, default=False)  # High contrast, screen reader, etc
    browser_type = Column(String(50), nullable=True)  # "chrome", "safari", "firefox", etc
    os_type = Column(String(50), nullable=True)  # "ios", "android", "windows", "macos", "linux"

    # Event metadata
    properties = Column(JSON, nullable=True)  # Event-specific data (e.g., search_query_length, results_count)
    error_code = Column(String(100), nullable=True)  # If event failed (e.g., "API_ERROR", "TIMEOUT")

    # Indexing for common queries
    __table_args__ = (
        Index("idx_journey_session", "journey_type", "session_id"),
        Index("idx_journey_timestamp", "journey_type", "event_timestamp"),
        Index("idx_journey_user_type", "journey_type", "user_type", "event_timestamp"),
        Index("idx_journey_device_type", "journey_type", "device_type", "event_timestamp"),
    )


class JourneyMetrics(Base):
    __tablename__ = "journey_metrics"

    id = Column(Integer, primary_key=True, index=True)

    # Time dimension
    metric_time = Column(DateTime(timezone=True), nullable=False, index=True)
    metric_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    metric_hour = Column(Integer, nullable=False)  # 0-23

    # Journey dimension
    journey_type = Column(String(50), nullable=False, index=True)

    # Segmentation dimensions
    segment_key = Column(String(255), nullable=False)  # Composite key: "device_mobile|user_returning|access_false"
    device_type = Column(String(50), nullable=True)
    user_type = Column(String(50), nullable=True)
    accessibility_mode = Column(Boolean, nullable=True)

    # Stage metrics (per stage)
    stage_name = Column(String(100), nullable=False)

    # Counts
    stage_event_count = Column(Integer, default=0, nullable=False)  # Total events at this stage
    unique_sessions = Column(Integer, default=0, nullable=False)  # Sessions reaching this stage
    unique_users = Column(Integer, default=0, nullable=False)  # Users reaching this stage

    # Time metrics
    avg_time_to_stage_ms = Column(Float, nullable=True)  # Avg time from journey start to this stage
    median_time_to_stage_ms = Column(Float, nullable=True)
    p95_time_to_stage_ms = Column(Float, nullable=True)

    # Error metrics
    error_event_count = Column(Integer, default=0, nullable=False)
    error_rate = Column(Float, default=0.0, nullable=False)  # Percentage

    # Completion metrics (only for final stage)
    completion_count = Column(Integer, default=0, nullable=False)
    abandonment_count = Column(Integer, default=0, nullable=False)  # Sessions that didn't complete

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_metrics_journey_time", "journey_type", "metric_time"),
        Index("idx_metrics_segment_time", "segment_key", "metric_time"),
        Index("idx_metrics_device_time", "device_type", "journey_type", "metric_time"),
    )


class JourneyDropOff(Base, TimestampMixin):
    __tablename__ = "journey_dropoffs"

    id = Column(Integer, primary_key=True, index=True)

    # Journey identification
    journey_type = Column(String(50), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=True, index=True)

    # Drop-off info
    last_completed_stage = Column(String(100), nullable=False)  # Last stage user reached
    expected_next_stage = Column(String(100), nullable=False)  # Stage they should have gone to
    stages_completed = Column(Integer, nullable=False)  # 1, 2, 3, etc
    total_stages = Column(Integer, nullable=False)  # Total stages in journey

    # Timing
    time_in_journey_ms = Column(Integer, nullable=False)  # Total time before drop-off
    time_at_last_stage_ms = Column(Integer, nullable=False)  # Time spent at drop-off stage

    # Context
    device_type = Column(String(50), nullable=True)
    user_type = Column(String(50), nullable=True)
    accessibility_mode = Column(Boolean, default=False)

    # Drop-off reason (inferred)
    reason = Column(String(100), nullable=True)  # "timeout", "error", "navigation_change", "unknown"
    reason_code = Column(String(100), nullable=True)  # If error: "API_ERROR", "VALIDATION_ERROR", etc

    # Metadata
    properties = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_dropoff_journey", "journey_type", "session_id"),
        Index("idx_dropoff_stage", "journey_type", "last_completed_stage"),
        Index("idx_dropoff_timestamp", "journey_type", "created_at"),
    )


class JourneyAlert(Base):
    __tablename__ = "journey_alerts"

    id = Column(Integer, primary_key=True, index=True)

    # Alert identification
    journey_type = Column(String(50), nullable=False, index=True)
    alert_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # "completion_rate_drop", "error_rate_spike", "abandonment_increase"

    # Metric dimension
    segment_key = Column(String(255), nullable=True)  # Overall or specific segment
    device_type = Column(String(50), nullable=True)
    user_type = Column(String(50), nullable=True)

    # Values
    current_value = Column(Float, nullable=False)  # Current metric value
    baseline_value = Column(Float, nullable=False)  # 7-day average baseline
    percent_change = Column(Float, nullable=False)  # (current - baseline) / baseline

    # Alert severity
    severity = Column(String(20), nullable=False)  # "low" (<10% drop), "medium" (10-20%), "high" (>20%)

    # Alert status
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_note = Column(Text, nullable=True)

    # Raw metrics for investigation
    metrics_snapshot = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_alert_journey_time", "journey_type", "alert_timestamp"),
        Index("idx_alert_unresolved", "journey_type", "is_resolved"),
    )
