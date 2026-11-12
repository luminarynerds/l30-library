# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import StrEnum
from ...core.database import Base


class ActionItemStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class ActionItemPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MeetingActionItem(Base):
    __tablename__ = "meeting_action_items"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("board_meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    agenda_item_id = Column(Integer, ForeignKey("agenda_items.id", ondelete="SET NULL"))

    title = Column(String(500), nullable=False)
    description = Column(Text)

    # Assignment
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    assigned_to_name = Column(String(200))  # Fallback if not a user
    assigned_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    status = Column(String(30), nullable=False, default="not_started", index=True)
    priority = Column(String(20), nullable=False, default="medium", index=True)

    due_date = Column(Date, index=True)
    completed_at = Column(DateTime(timezone=True))

    progress_percentage = Column(Integer, default=0)  # 0-100
    notes = Column(Text)

    # Follow-up tracking
    requires_board_update = Column(Boolean, default=False)
    board_update_provided = Column(Boolean, default=False)
    board_update_meeting_id = Column(Integer, ForeignKey("board_meetings.id", ondelete="SET NULL"))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    meeting = relationship("BoardMeeting", foreign_keys=[meeting_id], back_populates="action_items")
    agenda_item = relationship("AgendaItem")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])
    board_update_meeting = relationship("BoardMeeting", foreign_keys=[board_update_meeting_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
