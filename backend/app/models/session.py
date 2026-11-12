# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class ModuleSession(Base):
    __tablename__ = "module_sessions"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200))
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    location = Column(String(200))
    facilitator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    max_participants = Column(Integer)
    materials = Column(JSONB, default=list)
    notes = Column(Text)
    is_cancelled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    module = relationship("Module", backref="sessions")
    facilitator = relationship("User", foreign_keys=[facilitator_id])
    rsvps = relationship("SessionRSVP", back_populates="session", cascade="all, delete-orphan")


class SessionRSVP(Base):
    __tablename__ = "session_rsvps"
    __table_args__ = (UniqueConstraint("session_id", "user_id", name="uq_session_rsvp"),)

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("module_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="attending")
    responded_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ModuleSession", back_populates="rsvps")
