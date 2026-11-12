# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from enum import StrEnum
from ..core.database import Base


class EventRegistrationStatus(StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    WAITLISTED = "waitlisted"
    NO_SHOW = "no_show"


class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    patron_name = Column(String(255), nullable=False)
    # Nullable: patrons without email may register phone-only (the API
    # enforces at least one of email/phone).
    patron_email = Column(String(255), nullable=True)
    patron_phone = Column(String(50), nullable=True)
    # Nullable FK to the logged-in user who made this registration. NULL for
    # anonymous / phone-only registrations. ON DELETE SET NULL so the row
    # survives if the user account is deleted (library audit trail).
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), default=EventRegistrationStatus.CONFIRMED.value)
    reminder_requested = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Accommodation request workflow. accommodation_requested is the boolean
    # flag for "patron is asking for an accommodation"; accommodation_details
    # is the patron's free-text description; acknowledged_* fields track the
    # staff-side workflow of confirming the request has been read & arranged.
    accommodation_requested = Column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    accommodation_details = Column(Text, nullable=True)
    accommodation_acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    accommodation_acknowledged_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Photo-release consent. NULL means the question was never asked
    # (event.photos_will_be_taken was False at registration time); True/False
    # are explicit answers. Three-valued on purpose so we can distinguish
    # "didn't ask" from "asked, said no" in audits.
    photo_release_granted = Column(Boolean, nullable=True)

    event = relationship("Event", backref="registrations")
