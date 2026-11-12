# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import Enum, StrEnum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SQLEnum, Float, ForeignKey,
    Integer, Numeric, String, Text, Time, UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class EODTaskType(StrEnum):
    CLOSE_REGISTERS = "close_registers"
    PROCESS_HOLDS = "process_holds"
    SEND_OVERDUE_NOTICES = "send_overdue_notices"
    BACKUP_CONFIRMATION = "backup_confirmation"
    SECURITY_CHECK = "security_check"
    STATISTICS_SUMMARY = "statistics_summary"
    TOMORROW_EVENTS = "tomorrow_events"
    HOLDS_PULL_LIST = "holds_pull_list"


class EODTaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EODSessionStatus(StrEnum):
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class SecurityCheckType(StrEnum):
    DOOR_LOCKS = "door_locks"
    ALARM_SYSTEM = "alarm_system"
    SAFE_LOCKED = "safe_locked"
    WINDOWS_LOCKED = "windows_locked"
    LIGHTS_OFF = "lights_off"
    COMPUTERS_SHUT_DOWN = "computers_shut_down"
    VALVES_CLOSED = "valves_closed"


class EODTemplate(Base):
    __tablename__ = "eod_templates"

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    name = Column(String(100), nullable=False)
    description = Column(Text)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=False, index=True)  # deprecated; use branch_id

    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    estimated_duration_minutes = Column(Integer, default=20, nullable=False)

    # Task configuration (JSON array of task configs)
    # e.g., [
    #   {"task_type": "close_registers", "required": True, "skip_reason": null},
    #   {"task_type": "process_holds", "required": False, "skip_reason": "Manual processing"}
    # ]
    task_configs = Column(JSON, default=[])

    # Audit, server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    sessions = relationship("EODSession", back_populates="template")

    __table_args__ = (
        UniqueConstraint("name", "branch_location", name="uq_eod_templates_name_branch"),
    )


class EODSession(Base):
    __tablename__ = "eod_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    session_code = Column(String(50), nullable=False, index=True)

    # Context
    template_id = Column(Integer, ForeignKey("eod_templates.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=False, index=True)  # deprecated; use branch_id
    closing_date = Column(Date, nullable=False, index=True)

    # Staff
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    assisted_by_ids = Column(JSON, default=[])  # Additional staff helping with closing

    # Status
    status = Column(
        String(50),
        default=EODSessionStatus.STARTED,
        nullable=False,
        index=True
    )

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    total_duration_seconds = Column(Integer, default=0)

    # Statistics (denormalized for quick access)
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    skipped_tasks = Column(Integer, default=0)

    # Backup and security info
    backup_status = Column(String(50))  # "pending", "in_progress", "success", "failed"
    backup_completed_at = Column(DateTime(timezone=True))
    backup_error_message = Column(Text)

    # Security checks (JSON array of check results)
    security_checks = Column(JSON, default=[])

    # Statistics summary (denormalized)
    statistics_summary = Column(JSON)  # e.g., {"total_checkouts": 150, "total_fines": 45.50}

    # Issues encountered (JSON array of issues)
    issues = Column(JSON, default=[])

    # Notes from closing staff
    notes = Column(Text)

    # Auto-logout info
    auto_logout_at = Column(DateTime(timezone=True))  # When auto-logout will trigger
    auto_logout_performed = Column(Boolean, default=False)

    # Relationships
    template = relationship("EODTemplate", back_populates="sessions")
    staff = relationship("User", foreign_keys=[staff_id])
    tasks = relationship("EODTask", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("session_code", name="uq_eod_sessions_session_code"),
        Index("ix_eod_sessions_date_branch", "closing_date", "branch_location"),
    )


class EODTask(Base):
    __tablename__ = "eod_tasks"

    id = Column(Integer, primary_key=True, index=True)

    # Session
    session_id = Column(
        Integer,
        ForeignKey("eod_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Task identification
    task_type = Column(
        String(50),
        nullable=False,
        index=True
    )
    display_name = Column(String(100), nullable=False)

    # Status
    status = Column(
        String(50),
        default=EODTaskStatus.PENDING,
        nullable=False,
        index=True
    )

    # Task-specific data (JSON)
    # Different task types can store different data:
    # - close_registers: {"drawer_count": 5, "total_cash": 1234.50}
    # - process_holds: {"pulls_generated": 45, "hold_count": 120}
    # - send_overdue_notices: {"notices_sent": 23, "failed_sends": 2}
    # - backup_confirmation: {"backup_size_mb": 512, "backup_location": "..."}
    # - security_check: {"checks_passed": 6, "checks_failed": 0, "checks": [...]}
    # - statistics_summary: {"checkouts": 150, "checkins": 148, "holds_placed": 12}
    # - tomorrow_events: {"event_count": 3, "events": [...]}
    # - holds_pull_list: {"pdf_generated": true, "pull_list_url": "..."}
    task_data = Column(JSON, default={})

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer, default=0)

    # Assigned to
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Completion info
    completed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    skip_reason = Column(String(255))
    error_message = Column(Text)

    # Audit, server_default=func.now(), nullable=False)

    # Relationships
    session = relationship("EODSession", back_populates="tasks")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    completed_by = relationship("User", foreign_keys=[completed_by_id])

    __table_args__ = (
        Index("ix_eod_tasks_session_type", "session_id", "task_type"),
    )


class EODSecurityCheck(Base):
    __tablename__ = "eod_security_checks"

    id = Column(Integer, primary_key=True, index=True)

    # Session
    session_id = Column(
        Integer,
        ForeignKey("eod_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Check type
    check_type = Column(
        String(50),
        nullable=False,
        index=True
    )
    display_name = Column(String(100), nullable=False)

    # Result
    passed = Column(Boolean, nullable=False)
    notes = Column(Text)

    # Location (for location-specific checks)
    location = Column(String(100))

    # Checked by
    checked_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Timing
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    session = relationship("EODSession")
    checked_by = relationship("User", foreign_keys=[checked_by_id])


class EODStatistics(Base):
    __tablename__ = "eod_statistics"

    id = Column(Integer, primary_key=True, index=True)

    # Date and location
    closing_date = Column(Date, nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=False, index=True)  # deprecated; use branch_id

    # Circulation metrics (denormalized from CheckInStatistic for the day)
    total_checkouts = Column(Integer, default=0)
    total_checkins = Column(Integer, default=0)
    total_holds_placed = Column(Integer, default=0)
    total_holds_ready = Column(Integer, default=0)
    overdue_items_count = Column(Integer, default=0)

    # Fine metrics
    total_fines_amount = Column(Numeric(10, 2), default=0)
    total_fines_paid = Column(Numeric(10, 2), default=0)
    total_fines_waived = Column(Numeric(10, 2), default=0)

    # Staff metrics
    total_sessions = Column(Integer, default=0)
    avg_closing_time_minutes = Column(Float, default=0)
    total_staff_involved = Column(Integer, default=0)

    # Issues and exceptions
    total_exceptions = Column(Integer, default=0)
    total_security_failures = Column(Integer, default=0)
    total_backup_failures = Column(Integer, default=0)

    # Tomorrow's planning
    tomorrow_events_count = Column(Integer, default=0)
    tomorrow_holds_to_process = Column(Integer, default=0)

    # Audit, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "closing_date", "branch_location",
            name="uq_eod_statistics_date_branch"
        ),
        Index("ix_eod_statistics_date", "closing_date"),
    )
