# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ...core.database import Base


class AgendaItem(Base):
    __tablename__ = "agenda_items"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("board_meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_item_id = Column(Integer, ForeignKey("agenda_items.id", ondelete="SET NULL"))

    item_number = Column(String(20), nullable=False)  # e.g., "1", "2.a", "3.b.i"
    title = Column(String(500), nullable=False)
    description = Column(Text)
    presenter = Column(String(200))
    estimated_duration_minutes = Column(Integer)

    sort_order = Column(Integer, nullable=False, default=0)

    requires_action = Column(Boolean, default=False)
    action_type = Column(String(100))  # e.g., "vote", "discussion", "information"
    action_taken = Column(Text)
    vote_result = Column(String(200))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    meeting = relationship("BoardMeeting", back_populates="agenda_items")
    parent_item = relationship("AgendaItem", remote_side=[id], backref="sub_items")
    created_by = relationship("User")
