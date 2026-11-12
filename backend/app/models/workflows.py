# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    JSON, String, Text, func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TriggerType(StrEnum):
    event = "event"
    schedule = "schedule"
    manual = "manual"


class StepType(StrEnum):
    action = "action"
    condition = "condition"
    delay = "delay"
    notification = "notification"


class ActionType(StrEnum):
    send_email = "send_email"
    send_sms = "send_sms"
    create_transit = "create_transit"
    update_status = "update_status"
    generate_report = "generate_report"
    assign_task = "assign_task"
    place_hold = "place_hold"
    cancel_hold = "cancel_hold"
    flag_account = "flag_account"
    send_to_collections = "send_to_collections"
    auto_order_copies = "auto_order_copies"
    generate_marc_record = "generate_marc_record"
    check_duplicates = "check_duplicates"
    assign_shelf_location = "assign_shelf_location"
    move_to_hold_shelf = "move_to_hold_shelf"
    notify_next_in_queue = "notify_next_in_queue"


class ExecutionStatus(StrEnum):
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class StepResultStatus(StrEnum):
    pending = "pending"
    success = "success"
    failed = "failed"
    skipped = "skipped"


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    # Trigger configuration
    trigger = Column(SQLEnum(TriggerType, values_callable=lambda x: [e.value for e in x]), nullable=False, default=TriggerType.manual)
    trigger_config = Column(JSON, nullable=True)  # event_type, cron_expression, etc.

    # State
    active = Column(Boolean, default=True, nullable=False, index=True)
    is_template = Column(Boolean, default=False, nullable=False, index=True)
    template_name = Column(String(255), nullable=True)

    # Run stats
    last_run = Column(DateTime(timezone=True), nullable=True)
    run_count = Column(Integer, default=0, nullable=False)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    steps = relationship(
        "WorkflowStep",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowStep.order",
    )
    executions = relationship(
        "WorkflowExecution",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, name={self.name!r}, trigger={self.trigger})>"


# ---------------------------------------------------------------------------
# WorkflowStep
# ---------------------------------------------------------------------------

class WorkflowStep(Base, TimestampMixin):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(
        Integer,
        ForeignKey("workflows.id", ondelete="CASCADE"),
        index=True,
    )
    order = Column(Integer, nullable=False, default=0)
    name = Column(String(255), nullable=True)

    # Step type and sub-type
    step_type = Column(SQLEnum(StepType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    action_type = Column(SQLEnum(ActionType, values_callable=lambda x: [e.value for e in x]), nullable=True)

    # Condition expression (for condition steps)
    condition = Column(Text, nullable=True)

    # Delay duration in minutes (for delay steps)
    delay_duration = Column(Integer, nullable=True)
    delay_unit = Column(String(20), nullable=True)  # minutes, hours, days

    # Flexible per-step config: template_id, recipient, message, etc.
    config = Column(JSON, nullable=True)

    # Branching: next step on success / failure (step id or "stop")
    on_success = Column(String(50), nullable=True)
    on_failure = Column(String(50), nullable=True, default="stop")

    # Relationships
    workflow = relationship("Workflow", back_populates="steps")

    def __repr__(self) -> str:
        return (
            f"<WorkflowStep(id={self.id}, workflow_id={self.workflow_id}, "
            f"order={self.order}, step_type={self.step_type})>"
        )


# ---------------------------------------------------------------------------
# WorkflowExecution
# ---------------------------------------------------------------------------

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(
        Integer,
        ForeignKey("workflows.id", ondelete="CASCADE"),
        index=True,
    )
    triggered_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    # Timing
    triggered_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Status tracking
    status = Column(
        SQLEnum(ExecutionStatus, values_callable=lambda x: [e.value for e in x]),
        default=ExecutionStatus.running,
    )
    current_step = Column(Integer, nullable=True)

    # Context passed into the run (e.g. patron_id, item_id)
    context = Column(JSON, nullable=True)

    # Step-by-step results log
    step_results = Column(JSON, nullable=True, default=list)

    # Error info
    error_message = Column(Text, nullable=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="executions")
    triggered_by = relationship("User", foreign_keys=[triggered_by_id])

    def __repr__(self) -> str:
        return (
            f"<WorkflowExecution(id={self.id}, workflow_id={self.workflow_id}, "
            f"status={self.status})>"
        )
