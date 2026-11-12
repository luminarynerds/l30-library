# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import relationship
from ..core.database import Base

class ChecklistCategory(StrEnum):
    WRAP_UP = "wrap_up"  # Close out tasks and open items
    HANDOFF = "handoff"  # Hand off in-progress items
    TOMORROW = "tomorrow"  # Clear priorities for next day
    MENTAL = "mental"  # Mental transition ritual
    CELEBRATION = "celebration"  # Celebrate daily wins

class ChecklistItemStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"

class ShiftChecklistSession(Base):
    __tablename__ = "shift_checklist_sessions"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shift_date = Column(DateTime, nullable=False, index=True)
    shift_end_time = Column(DateTime(timezone=True), nullable=True)  # When shift actually ended
    items_completed = Column(Integer, default=0)
    total_items = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)  # All checklist items done
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)  # Optional notes about the shift
    staff = relationship("User")
    checklist_items = relationship("ChecklistItem", back_populates="session", cascade="all, delete-orphan")

class ChecklistItem(Base):
    __tablename__ = "checklist_items"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("shift_checklist_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(SQLEnum(ChecklistCategory, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)  # Helpful guidance for this item
    status = Column(SQLEnum(ChecklistItemStatus, values_callable=lambda x: [e.value for e in x]), default=ChecklistItemStatus.PENDING, nullable=False)
    order = Column(Integer, default=0)  # Display order within category
    required = Column(Boolean, default=False)  # Must complete to finish shift
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)  # Optional staff notes on this item
    session = relationship("ShiftChecklistSession", back_populates="checklist_items")

class DailyWin(Base):
    __tablename__ = "daily_wins"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("shift_checklist_sessions.id", ondelete="CASCADE"), nullable=True)  # Link to session
    win_description = Column(Text, nullable=False)
    win_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    is_public = Column(Boolean, default=False)
    celebration_emoji = Column(String(10), default="🎉")  # Celebratory emoji
    staff = relationship("User")
    session = relationship("ShiftChecklistSession")

class ChecklistTemplate(Base):
    __tablename__ = "checklist_templates"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)  # e.g., "Standard End-of-Shift"
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    items = Column(JSON, nullable=True)  # JSON array of template items
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
