# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from ..mixins import TimestampMixin, AuditMixin
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import StrEnum
from ...core.database import Base


class BoardMeetingType(StrEnum):
    REGULAR = "regular"
    SPECIAL = "special"
    EMERGENCY = "emergency"
    COMMITTEE = "committee"
    WORKSHOP = "workshop"
    PUBLIC_HEARING = "public_hearing"


class BoardMeeting(Base, TimestampMixin, AuditMixin):
    __tablename__ = "board_meetings"

    id = Column(Integer, primary_key=True, index=True)
    meeting_type = Column(String(30), nullable=False, default="regular", index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)

    scheduled_date = Column(DateTime(timezone=True), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    location = Column(String(500))
    is_virtual = Column(Boolean, default=False)
    virtual_meeting_url = Column(String(1000))

    # Committee relationship
    committee_id = Column(Integer, ForeignKey("board_committees.id", ondelete="SET NULL"), nullable=True, index=True)

    is_cancelled = Column(Boolean, default=False)
    cancellation_reason = Column(Text)

    notice_status = Column(String(50), default="draft")
    notice_posted_at = Column(DateTime(timezone=True), nullable=True)
    public_comment_enabled = Column(Boolean, default=False)
    public_comment_instructions = Column(Text)
    accessibility_info = Column(Text)

    quorum_met = Column(Boolean)

    minutes_approved = Column(Boolean, default=False)
    minutes_approved_date = Column(DateTime(timezone=True))
    minutes_approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


    # Executive session
    has_executive_session = Column(Boolean, default=False)
    executive_session_reason = Column(Text)

    # Notice tracking
    notice_lead_days_required = Column(Integer, default=2)
    notice_posted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notice_posting_locations = Column(JSONB, default=list)
    notice_document_id = Column(Integer, ForeignKey("board_documents.id", ondelete="SET NULL", use_alter=True, name="board_meetings_notice_document_id_fkey"), nullable=True)

    # Agenda publishing
    agenda_published_at = Column(DateTime(timezone=True))
    agenda_published_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships - specify foreign_keys to avoid ambiguity
    committee = relationship("Committee", back_populates="meetings")
    documents = relationship("BoardDocument", foreign_keys="[BoardDocument.meeting_id]", back_populates="meeting", cascade="all, delete-orphan")
    notice_document = relationship("BoardDocument", foreign_keys=[notice_document_id], uselist=False)
    agenda_items = relationship("AgendaItem", back_populates="meeting", cascade="all, delete-orphan")
    minutes = relationship("BoardMinutes", back_populates="meeting", uselist=False)
    action_items = relationship("MeetingActionItem", foreign_keys="[MeetingActionItem.meeting_id]", back_populates="meeting", cascade="all, delete-orphan")
    attendance_records = relationship("MeetingAttendance", back_populates="meeting", cascade="all, delete-orphan")
    minutes_approved_by = relationship("User", foreign_keys=[minutes_approved_by_id])
    notice_posted_by = relationship("User", foreign_keys=[notice_posted_by_id])
    agenda_published_by = relationship("User", foreign_keys=[agenda_published_by_id])
