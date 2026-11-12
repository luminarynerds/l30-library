# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import StrEnum
from ...core.database import Base


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    EXCUSED = "excused"
    TARDY = "tardy"
    LEFT_EARLY = "left_early"


class RSVPStatus(StrEnum):
    NO_RESPONSE = "no_response"
    ATTENDING = "attending"
    NOT_ATTENDING = "not_attending"
    TENTATIVE = "tentative"


class MeetingAttendance(Base):
    __tablename__ = "meeting_attendance"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("board_meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # RSVP
    rsvp_status = Column(String(30), nullable=False, default="no_response")
    rsvp_at = Column(DateTime(timezone=True))
    rsvp_notes = Column(Text)

    # Actual attendance
    attendance_status = Column(String(30), index=True)
    checked_in_at = Column(DateTime(timezone=True))
    checked_out_at = Column(DateTime(timezone=True))

    is_voting_member = Column(Boolean, default=True)
    is_guest = Column(Boolean, default=False)
    guest_affiliation = Column(String(200))

    # Remote attendance
    attended_remotely = Column(Boolean, default=False)
    remote_connection_method = Column(String(100))

    absence_reason = Column(Text)
    excused_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    meeting = relationship("BoardMeeting", back_populates="attendance_records")
    user = relationship("User", foreign_keys=[user_id])
    excused_by = relationship("User", foreign_keys=[excused_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        UniqueConstraint('meeting_id', 'user_id', name='uq_meeting_attendance_user'),
    )
