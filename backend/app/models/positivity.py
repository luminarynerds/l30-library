# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.mixins import TimestampMixin


class PositivityEntryType(StrEnum):
    FEEDBACK = "feedback"
    WIN = "win"
    PROGRAM = "program"
    THANK_YOU = "thank-you"
    COMPLIMENT = "compliment"
    STORY = "story"
    APPRECIATION = "appreciation"


class PositivitySource(StrEnum):
    STAFF = "staff"
    PATRON = "patron"


class ModerationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PositivityEntry(Base, TimestampMixin):
    __tablename__ = "positivity_entries"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    entry_type = Column(String(50), nullable=False, index=True)
    text = Column(Text, nullable=False)

    # Source tracking
    source = Column(String(20), nullable=False, server_default="staff")

    # Patron submission fields
    patron_name = Column(String(255), nullable=True)
    patron_email = Column(String(255), nullable=True)

    # Advocacy pipeline
    flagged_for_advocacy = Column(Boolean, nullable=False, server_default="false")
    flagged_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    flagged_at = Column(DateTime(timezone=True), nullable=True)

    # Moderation
    moderation_status = Column(String(20), nullable=False, server_default="approved")
    moderated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    moderated_at = Column(DateTime(timezone=True), nullable=True)
    moderation_note = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    flagged_by = relationship("User", foreign_keys=[flagged_by_id])
    moderated_by = relationship("User", foreign_keys=[moderated_by_id])

    # Indexes for common queries
    __table_args__ = (
        Index("ix_positivity_entries_org_created", "organization_id", "created_at"),
        Index("ix_positivity_entries_user_created", "user_id", "created_at"),
        Index("ix_positivity_entries_flagged", "flagged_for_advocacy"),
        Index("ix_positivity_entries_source", "source"),
        Index("ix_positivity_entries_moderation", "moderation_status"),
    )
