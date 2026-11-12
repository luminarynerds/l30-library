# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, func
from sqlalchemy.orm import relationship

from ..core.database import Base


class PresenceStatus(StrEnum):
    AVAILABLE = "available"
    ON_BREAK = "on_break"
    NEEDS_HELP = "needs_help"
    OFF_DUTY = "off_duty"


class StaffPresence(Base):
    __tablename__ = "staff_presence"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    status = Column(
        SQLEnum(PresenceStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=PresenceStatus.OFF_DUTY,
    )
    status_changed_at = Column(DateTime(timezone=True), server_default=func.now())
    shift_started_at = Column(DateTime(timezone=True), nullable=True)
    shift_ended_at = Column(DateTime(timezone=True), nullable=True)
    break_started_at = Column(DateTime(timezone=True), nullable=True)
    organization_id = Column(Integer, nullable=True, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    staff = relationship("User", foreign_keys=[staff_id])
