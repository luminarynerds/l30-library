# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import enum

from enum import StrEnum
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class WaitlistStatus(StrEnum):
    WAITING = "waiting"
    NOTIFIED = "notified"
    CLAIMED = "claimed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# Active statuses count toward queue position + the partial unique index.
ACTIVE_WAITLIST_STATUSES = (WaitlistStatus.WAITING.value, WaitlistStatus.NOTIFIED.value)


class EventWaitlistEntry(Base):
    __tablename__ = "event_waitlist_entries"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    registrant_count = Column(Integer, nullable=False, default=1, server_default="1")
    notes = Column(Text, nullable=True)
    status = Column(
        String(20),
        nullable=False,
        default=WaitlistStatus.WAITING.value,
        server_default=WaitlistStatus.WAITING.value,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notified_at = Column(DateTime(timezone=True), nullable=True)
    claim_token = Column(String(64), nullable=True, index=True)
    claim_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    cancel_token = Column(String(64), nullable=True)

    event = relationship("Event", backref="waitlist_entries")
