# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import StrEnum
from ...core.database import Base


class BriefStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class BoardMeetingBrief(Base):
    __tablename__ = "board_meeting_briefs"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("board_meetings.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Brief content
    executive_summary = Column(Text, nullable=False)
    background_context = Column(Text)
    agenda_highlights = Column(ARRAY(String), default=list)
    recommended_prep = Column(ARRAY(String), default=list)
    action_items_pending = Column(ARRAY(String), default=list)
    key_documents = Column(JSONB, default=list)

    # AI generation metadata
    ai_model_used = Column(String(100))
    generation_time_ms = Column(Integer)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)

    # Status
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text)

    # Timestamps
    generated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    meeting = relationship("BoardMeeting", backref="brief")
    created_by = relationship("User", foreign_keys=[created_by_id])
