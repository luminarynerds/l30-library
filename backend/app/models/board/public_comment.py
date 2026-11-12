# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...core.database import Base


class CommentStatus(StrEnum):
    PENDING = "pending"  # Awaiting moderation
    APPROVED = "approved"  # Approved for inclusion
    REJECTED = "rejected"  # Rejected by moderator
    READ_INTO_RECORD = "read_into_record"  # Read during meeting


class CommentType(StrEnum):
    WRITTEN = "written"  # Written comment submitted in advance
    IN_PERSON = "in_person"  # In-person comment during meeting
    VIRTUAL = "virtual"  # Virtual comment during meeting


class PublicComment(Base):
    __tablename__ = "board_public_comments"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(
        Integer,
        ForeignKey("board_meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Optional - comment may be related to specific agenda item
    agenda_item_id = Column(
        Integer,
        ForeignKey("agenda_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    comment_type = Column(String(30), nullable=False, default="written", index=True)
    status = Column(String(30), nullable=False, default="pending", index=True)

    # Commenter information
    commenter_name = Column(String(200), nullable=False)
    commenter_email = Column(String(255))
    commenter_phone = Column(String(50))
    commenter_address = Column(Text)  # Optional address for record
    organization = Column(String(200))  # If representing an organization
    is_resident = Column(Boolean)  # Is local resident (for priority)

    # Comment content
    subject = Column(String(500))
    comment_text = Column(Text, nullable=False)

    # Attachment support
    attachment_filename = Column(String(500))
    attachment_file_path = Column(String(1000))
    attachment_mime_type = Column(String(100))
    attachment_file_size = Column(Integer)

    # Submission tracking
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(String(45))  # For spam prevention

    # Moderation
    moderated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    moderated_at = Column(DateTime(timezone=True))
    moderation_notes = Column(Text)  # Internal notes about moderation decision
    rejection_reason = Column(Text)  # If rejected, why

    # Reading into record
    read_at = Column(DateTime(timezone=True))
    read_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reading_notes = Column(Text)  # Notes about how it was read (summary, full, etc.)
    time_allocated_seconds = Column(Integer)  # Time given to speaker

    # For in-person/virtual comments
    speaker_order = Column(Integer)  # Order in which speakers present
    actual_start_time = Column(DateTime(timezone=True))
    actual_end_time = Column(DateTime(timezone=True))

    # Privacy settings
    include_in_minutes = Column(Boolean, default=True)  # Include in public minutes
    redact_contact_info = Column(Boolean, default=True)  # Redact email/phone in public record

    # Response tracking
    staff_response = Column(Text)
    staff_response_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    staff_response_at = Column(DateTime(timezone=True))
    board_response = Column(Text)
    board_response_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    meeting = relationship("BoardMeeting", backref="public_comments")
    agenda_item = relationship("AgendaItem", backref="public_comments")
    moderated_by = relationship("User", foreign_keys=[moderated_by_id])
    read_by = relationship("User", foreign_keys=[read_by_id])
    staff_response_by = relationship("User", foreign_keys=[staff_response_by_id])


class PublicCommentPeriod(Base):
    __tablename__ = "board_public_comment_periods"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(
        Integer,
        ForeignKey("board_meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Period definition
    title = Column(String(200), nullable=False)  # e.g., "General Public Comment"
    description = Column(Text)
    instructions = Column(Text)  # Instructions for commenters

    # Timing
    opens_at = Column(DateTime(timezone=True), nullable=False)
    closes_at = Column(DateTime(timezone=True), nullable=False)

    # During meeting timing
    scheduled_start_time = Column(DateTime(timezone=True))  # When during meeting
    actual_start_time = Column(DateTime(timezone=True))
    actual_end_time = Column(DateTime(timezone=True))

    # Limits
    max_comments = Column(Integer)  # Maximum number of comments accepted
    max_speakers = Column(Integer)  # Maximum in-person/virtual speakers
    time_per_speaker_seconds = Column(Integer, default=180)  # Default 3 minutes

    # Options
    allow_written = Column(Boolean, default=True)
    allow_in_person = Column(Boolean, default=True)
    allow_virtual = Column(Boolean, default=True)
    require_advance_signup = Column(Boolean, default=False)

    # Specific agenda item (if comment period is for specific item)
    agenda_item_id = Column(Integer, ForeignKey("agenda_items.id", ondelete="SET NULL"))

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    meeting = relationship("BoardMeeting", backref="comment_periods")
    agenda_item = relationship("AgendaItem")
    created_by = relationship("User", foreign_keys=[created_by_id])
