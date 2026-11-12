# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func

from ..core.database import Base


class FailedJobStatus(StrEnum):
    PENDING = "pending"  # Awaiting manual review
    RETRYING = "retrying"  # Being retried automatically
    RESOLVED = "resolved"  # Manually marked as resolved
    ABANDONED = "abandoned"  # Max retries exceeded, given up


class JobSeverity(StrEnum):
    LOW = "low"  # Non-critical, can be ignored
    MEDIUM = "medium"  # Should be reviewed
    HIGH = "high"  # Requires attention
    CRITICAL = "critical"  # Immediate attention required


class FailedJobRecord(Base):
    __tablename__ = "failed_job_records"

    id = Column(Integer, primary_key=True, index=True)

    # Job identification
    job_id = Column(String(100), nullable=False, index=True)  # e.g., "daily_fine_calculation"
    job_name = Column(String(255), nullable=False)  # Human-readable name

    # Failed item details
    entity_type = Column(String(100), nullable=True, index=True)  # e.g., "checkout", "hold", "user"
    entity_id = Column(Integer, nullable=True, index=True)  # ID of the failed entity

    # Error information
    error_message = Column(Text, nullable=False)
    error_type = Column(String(255), nullable=True)  # Exception class name
    stack_trace = Column(Text, nullable=True)

    # Context and metadata
    context = Column(JSON, nullable=True)  # Additional context (item details, etc.)

    # Status tracking
    status = Column(
        SQLEnum(FailedJobStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=FailedJobStatus.PENDING,
        index=True
    )
    severity = Column(
        SQLEnum(JobSeverity, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=JobSeverity.MEDIUM,
        index=True
    )

    # Retry tracking
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Resolution tracking
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(255), nullable=True)  # "system" or user email
    resolution_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_failed_jobs_job_status', 'job_id', 'status'),
        Index('ix_failed_jobs_entity', 'entity_type', 'entity_id'),
        Index('ix_failed_jobs_pending_retry', 'status', 'next_retry_at'),
    )

    def __repr__(self) -> str:
        return (
            f"<FailedJobRecord(id={self.id}, job_id={self.job_id}, "
            f"entity_type={self.entity_type}, entity_id={self.entity_id}, "
            f"status={self.status})>"
        )


class JobExecutionLog(Base):
    __tablename__ = "job_execution_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Job identification
    job_id = Column(String(100), nullable=False, index=True)
    job_name = Column(String(255), nullable=False)

    # Execution details
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Outcome
    success = Column(Boolean, nullable=False, default=True, index=True)
    error_message = Column(Text, nullable=True)
    error_type = Column(String(255), nullable=True)

    # Metrics
    items_processed = Column(Integer, nullable=True, default=0)
    items_succeeded = Column(Integer, nullable=True, default=0)
    items_failed = Column(Integer, nullable=True, default=0)

    # Additional metrics as JSON (job-specific)
    metrics = Column(JSON, nullable=True)

    # Misfire tracking
    was_misfire = Column(Boolean, nullable=False, default=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)

    # Instance tracking (for horizontal scaling)
    instance_id = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Composite indexes for analytics
    __table_args__ = (
        Index('ix_job_exec_job_time', 'job_id', 'started_at'),
        Index('ix_job_exec_job_success', 'job_id', 'success'),
        Index('ix_job_exec_recent', 'started_at', 'job_id'),
    )

    def __repr__(self) -> str:
        return (
            f"<JobExecutionLog(id={self.id}, job_id={self.job_id}, "
            f"success={self.success}, items_processed={self.items_processed})>"
        )


class JobAlertThreshold(Base):
    __tablename__ = "job_alert_thresholds"

    id = Column(Integer, primary_key=True, index=True)

    # Job identification (NULL means default for all jobs)
    job_id = Column(String(100), nullable=True, unique=True, index=True)

    # Error rate thresholds (percentage)
    warning_error_rate = Column(Float, nullable=False, default=5.0)  # 5%
    critical_error_rate = Column(Float, nullable=False, default=15.0)  # 15%

    # Consecutive failure thresholds
    warning_consecutive_failures = Column(Integer, nullable=False, default=2)
    critical_consecutive_failures = Column(Integer, nullable=False, default=5)

    # Time window for calculating error rates (in hours)
    error_rate_window_hours = Column(Integer, nullable=False, default=24)

    # Alert cooldown (don't alert again within this period, in minutes)
    alert_cooldown_minutes = Column(Integer, nullable=False, default=60)

    # Last alert timestamps
    last_warning_at = Column(DateTime(timezone=True), nullable=True)
    last_critical_at = Column(DateTime(timezone=True), nullable=True)

    # Enable/disable alerts for this job
    alerts_enabled = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return (
            f"<JobAlertThreshold(job_id={self.job_id or 'DEFAULT'}, "
            f"warning={self.warning_error_rate}%, critical={self.critical_error_rate}%)>"
        )
