# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, JSON, String, Text, Index, func
from sqlalchemy.orm import relationship
from app.models.mixins import TimestampMixin

from ..core.database import Base


class FocusTimeStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERRIDDEN = "overridden"


class FocusWorkType(StrEnum):
    DEEP_WORK = "deep_work"
    CATALOGING = "cataloging"
    COLLECTION_DEVELOPMENT = "collection_development"
    PROGRAMMING = "programming"
    STRATEGIC_PLANNING = "strategic_planning"
    PROFESSIONAL_DEVELOPMENT = "professional_development"
    REPORT_WRITING = "report_writing"
    POLICY_DEVELOPMENT = "policy_development"
    GRANT_WRITING = "grant_writing"
    RESEARCH = "research"
    OTHER = "other"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OverrideReason(StrEnum):
    URGENT_PATRON = "urgent_patron"
    SYSTEM_ISSUE = "system_issue"
    STAFFING_EMERGENCY = "staffing_emergency"
    FACILITY_ISSUE = "facility_issue"
    SECURITY_CONCERN = "security_concern"
    DIRECTOR_REQUEST = "director_request"
    OTHER = "other"


class FocusTimeBlock(Base, TimestampMixin):
    __tablename__ = "focus_time_blocks"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Schedule details
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    work_type = Column(SQLEnum(FocusWorkType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    description = Column(Text, nullable=True)

    # Status tracking
    status = Column(SQLEnum(FocusTimeStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=FocusTimeStatus.PENDING_APPROVAL, index=True)
    requires_approval = Column(Boolean, default=True)

    # Recurring support
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(String(255), nullable=True)  # RRULE format
    recurrence_parent_id = Column(Integer, ForeignKey("focus_time_blocks.id", ondelete="CASCADE"), nullable=True)

    # Backup contact during focus time
    backup_contact_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Notification preferences
    batch_notifications = Column(Boolean, default=True)
    notification_method = Column(String(50), nullable=True)  # email, sms, slack, etc.

    # Timestamps
    cancelled_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    # Note: organization_id FK exists but no Organization model defined yet
    user = relationship("User", foreign_keys=[user_id])
    backup_contact = relationship("User", foreign_keys=[backup_contact_id])
    recurrence_parent = relationship("FocusTimeBlock", remote_side=[id], foreign_keys=[recurrence_parent_id], overlaps="recurrence_children")
    recurrence_children = relationship("FocusTimeBlock", foreign_keys=[recurrence_parent_id], remote_side=[recurrence_parent_id], overlaps="recurrence_parent")
    approvals = relationship("FocusTimeApproval", back_populates="focus_block", cascade="all, delete-orphan")
    overrides = relationship("FocusTimeOverride", back_populates="focus_block", cascade="all, delete-orphan")
    tracking = relationship("FocusTimeTracking", back_populates="focus_block", uselist=False, cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index("idx_focus_time_user_status", "user_id", "status"),
        Index("idx_focus_time_timerange", "start_time", "end_time"),
        Index("idx_focus_time_active", "status", "start_time", "end_time"),
    )


class FocusTimeApproval(Base):
    __tablename__ = "focus_time_approvals"

    id = Column(Integer, primary_key=True, index=True)
    focus_block_id = Column(Integer, ForeignKey("focus_time_blocks.id", ondelete="CASCADE"), nullable=False, index=True)
    manager_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Approval details
    status = Column(SQLEnum(ApprovalStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=ApprovalStatus.PENDING, index=True)
    decision_comment = Column(Text, nullable=True)
    conditions = Column(JSON, nullable=True)  # Optional conditions attached to approval

    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    focus_block = relationship("FocusTimeBlock", back_populates="approvals")
    manager = relationship("User")


class FocusTimeOverride(Base):
    __tablename__ = "focus_time_overrides"

    id = Column(Integer, primary_key=True, index=True)
    focus_block_id = Column(Integer, ForeignKey("focus_time_blocks.id", ondelete="CASCADE"), nullable=False, index=True)
    overridden_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Override details
    reason = Column(SQLEnum(OverrideReason, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    description = Column(Text, nullable=False)
    urgency_level = Column(Integer, nullable=True)  # 1-5 scale

    # Escalation
    requires_escalation = Column(Boolean, default=False)
    escalated_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    escalation_notes = Column(Text, nullable=True)

    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Timestamps

    # Relationships
    focus_block = relationship("FocusTimeBlock", back_populates="overrides")
    overridden_by = relationship("User", foreign_keys=[overridden_by_id])
    escalated_to = relationship("User", foreign_keys=[escalated_to_id])


class FocusTimeTracking(Base):
    __tablename__ = "focus_time_tracking"

    id = Column(Integer, primary_key=True, index=True)
    focus_block_id = Column(Integer, ForeignKey("focus_time_blocks.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Interruption tracking
    interruption_count = Column(Integer, default=0)
    interruption_details = Column(JSON, nullable=True)  # Array of interruption events

    # Work completion
    work_completed_percentage = Column(Float, nullable=True)  # 0.0-100.0
    tasks_completed = Column(Integer, nullable=True)
    tasks_planned = Column(Integer, nullable=True)

    # Quality and productivity
    quality_rating = Column(Integer, nullable=True)  # 1-5 stars
    productivity_rating = Column(Integer, nullable=True)  # 1-5 stars
    self_assessment_notes = Column(Text, nullable=True)

    # Effectiveness metrics
    would_schedule_again = Column(Boolean, nullable=True)
    optimal_time_of_day = Column(String(50), nullable=True)  # morning, afternoon, evening

    # Updated timestamp, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    focus_block = relationship("FocusTimeBlock", back_populates="tracking")


class FocusTimeSettings(Base):
    __tablename__ = "focus_time_settings"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    branch_id = Column(Integer, nullable=True, index=True)

    # Policy settings
    requires_manager_approval = Column(Boolean, default=True)
    min_advance_notice_hours = Column(Integer, default=24)
    max_duration_hours = Column(Integer, default=4)
    min_duration_minutes = Column(Integer, default=30)
    max_blocks_per_week = Column(Integer, default=5)

    # Feature toggles
    allow_recurring_blocks = Column(Boolean, default=True)
    allow_emergency_override = Column(Boolean, default=True)
    require_backup_contact = Column(Boolean, default=True)

    # Notification settings
    notification_enabled = Column(Boolean, default=True)
    notification_reminder_minutes = Column(Integer, default=15)
    batch_notification_interval_minutes = Column(Integer, default=30)

    # Timestamps

    # Relationships
    # Note: organization_id FK exists but no Organization model defined yet
