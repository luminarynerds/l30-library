# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import relationship

from ..core.database import Base


class TaskBatchType(StrEnum):
    PRINT_HOLD_SLIPS = "print_hold_slips"
    PROCESS_CARDS = "process_cards"
    BATCH_CHECKINS = "batch_checkins"
    OVERDUE_NOTICES = "overdue_notices"
    FINE_PAYMENTS = "fine_payments"
    MATERIAL_TRANSFERS = "material_transfers"
    HOLDS_SHELF = "holds_shelf"
    REFERENCE_QUESTIONS = "reference_questions"
    ILL_REQUESTS = "ill_requests"
    CATALOG_UPDATES = "catalog_updates"
    PATRON_OUTREACH = "patron_outreach"
    INVENTORY_TASKS = "inventory_tasks"
    WEEDING_DECISIONS = "weeding_decisions"
    PROGRAM_PREP = "program_prep"
    TECH_SUPPORT = "tech_support"
    CONSOLIDATE_NOTIFICATIONS = "consolidate_notifications"
    RETURN_PHONE_CALLS = "return_phone_calls"
    BATCH_EMAIL_RESPONSES = "batch_email_responses"


class BatchSuggestReason(StrEnum):
    VOLUME_THRESHOLD = "volume_threshold"  # Enough tasks to batch
    TIME_EFFICIENCY = "time_efficiency"  # Time savings expected
    PROXIMITY = "proximity"  # Tasks in same location
    DEADLINE_CLUSTERING = "deadline_clustering"  # Similar deadlines
    RESOURCE_SHARING = "resource_sharing"  # Share equipment/materials
    CONTEXT_SIMILARITY = "context_similarity"  # Similar mental context
    PATRON_EXPERIENCE = "patron_experience"  # Better patron service
    STAFF_REQUEST = "staff_request"  # Staff initiated
    PATTERN_DETECTED = "pattern_detected"  # Recurring pattern
    SKILL_MATCH = "skill_match"  # Matches staff skills


class TaskPriorityLevel(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskBatchSuggestion(Base):
    __tablename__ = "task_batch_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Batch details
    batch_type = Column(SQLEnum(TaskBatchType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # Suggestion reasoning
    reason = Column(SQLEnum(BatchSuggestReason, values_callable=lambda x: [e.value for e in x]), nullable=False)
    confidence_score = Column(Float, nullable=False)  # 0.0-1.0

    # Task details
    task_count = Column(Integer, nullable=False)
    estimated_time_minutes = Column(Integer, nullable=False)
    estimated_savings_minutes = Column(Integer, nullable=True)  # Time saved vs individual tasks

    # Priority planning support
    priority_level = Column(SQLEnum(TaskPriorityLevel, values_callable=lambda x: [e.value for e in x]), nullable=False, default=TaskPriorityLevel.MEDIUM, index=True)
    manager_priority_note = Column(Text, nullable=True)
    manager_set_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    can_wait_until = Column(DateTime, nullable=True, index=True)  # Explicit "this can wait" permission
    deadline_at = Column(DateTime, nullable=True, index=True)
    conflict_resolution_note = Column(Text, nullable=True)
    drop_everything = Column(Boolean, default=False, index=True)
    protected_time_recommended = Column(Boolean, default=False)
    distraction_deflection_script = Column(Text, nullable=True)
    completed_tasks_count = Column(Integer, default=0)
    priority_completed_at = Column(DateTime, nullable=True)

    # Context and hints
    location_hint = Column(String(255), nullable=True)  # Where to do these tasks
    timing_hint = Column(String(255), nullable=True)  # Best time to do batch
    prerequisites = Column(JSON, nullable=True)  # What's needed before starting

    # Status tracking
    is_active = Column(Boolean, default=True, index=True)
    is_accepted = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    dismissed_reason = Column(Text, nullable=True)

    # Activity tracking, server_default=func.now(), nullable=False, index=True)
    accepted_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)

    # Staff tracking
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    accepted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Additional context
    extra_data = Column(JSON, nullable=True)  # Extra data for specific batch types

    # Relationships
    # Note: organization_id FK exists but no Organization model defined yet
    created_by = relationship("User", foreign_keys=[created_by_id])
    accepted_by = relationship("User", foreign_keys=[accepted_by_id])
    manager_set_by = relationship("User", foreign_keys=[manager_set_by_id])
    sessions = relationship("BatchProcessingSession", back_populates="suggestion", cascade="all, delete-orphan")


class BatchProcessingSession(Base):
    __tablename__ = "batch_processing_sessions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    suggestion_id = Column(Integer, ForeignKey("task_batch_suggestions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Session details
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    batch_type = Column(SQLEnum(TaskBatchType, values_callable=lambda x: [e.value for e in x]), nullable=False)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    actual_duration_minutes = Column(Integer, nullable=True)

    # Metrics
    tasks_completed = Column(Integer, nullable=True)
    tasks_attempted = Column(Integer, nullable=True)
    completion_rate = Column(Float, nullable=True)  # 0.0-1.0

    # Efficiency tracking
    estimated_time_minutes = Column(Integer, nullable=False)
    time_saved_minutes = Column(Integer, nullable=True)
    interruptions_count = Column(Integer, default=0)

    # Feedback
    quality_rating = Column(Integer, nullable=True)  # 1-5 stars
    efficiency_rating = Column(Integer, nullable=True)  # 1-5 stars
    would_batch_again = Column(Boolean, nullable=True)
    staff_notes = Column(Text, nullable=True)

    # Status
    is_complete = Column(Boolean, default=False, index=True)
    was_abandoned = Column(Boolean, default=False)
    abandon_reason = Column(Text, nullable=True)

    # Additional data
    extra_data = Column(JSON, nullable=True)

    # Relationships
    # Note: organization_id FK exists but no Organization model defined yet
    suggestion = relationship("TaskBatchSuggestion", back_populates="sessions")
    staff = relationship("User")
