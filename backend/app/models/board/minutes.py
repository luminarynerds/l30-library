# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from ..mixins import TimestampMixin, AuditMixin
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import StrEnum
from ...core.database import Base


class MinutesStatus(StrEnum):
    NOT_STARTED = "not_started"
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"


class BoardMinutes(Base, TimestampMixin, AuditMixin):
    __tablename__ = "board_minutes"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("board_meetings.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    status = Column(String(30), nullable=False, default="not_started", index=True)

    # Structured sections as JSON
    sections = Column(JSONB, default=list)  # [{"title": "Call to Order", "content": "...", "order": 1}]

    meeting_called_to_order_at = Column(DateTime(timezone=True))
    meeting_adjourned_at = Column(DateTime(timezone=True))

    # Attendance in minutes
    members_present = Column(JSONB, default=list)  # [{"id": 1, "name": "John", "title": "President"}]
    members_absent = Column(JSONB, default=list)
    members_excused = Column(JSONB, default=list)
    guests_present = Column(JSONB, default=list)

    quorum_met = Column(Boolean)
    quorum_count = Column(String(50))  # e.g., "5 of 7 members present"

    # Approval tracking
    approved = Column(Boolean, default=False)
    approved_at = Column(DateTime(timezone=True))
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approval_vote_result = Column(String(200))  # e.g., "Approved 7-0"

    # Recording info
    recording_url = Column(String(1000))
    recording_duration_minutes = Column(String(50))

    notes = Column(Text)
    plain_language_summary = Column(Text, nullable=True)

    # Executive session sealing
    is_sealed = Column(Boolean, default=False, index=True)
    sealed_at = Column(DateTime(timezone=True), nullable=True)
    sealed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    unsealed_at = Column(DateTime(timezone=True), nullable=True)
    unsealed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    unseal_reason = Column(Text, nullable=True)

    # Records retention
    is_permanent = Column(Boolean, default=True)

    # Metadata
    prepared_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    prepared_at = Column(DateTime(timezone=True))


    # Relationships
    meeting = relationship("BoardMeeting", back_populates="minutes")
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    prepared_by = relationship("User", foreign_keys=[prepared_by_id])
    sealed_by = relationship("User", foreign_keys=[sealed_by_id])
    unsealed_by = relationship("User", foreign_keys=[unsealed_by_id])
