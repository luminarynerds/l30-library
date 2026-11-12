# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class BoardAuditAction(StrEnum):

    # Meeting actions
    MEETING_CREATED = "meeting_created"
    MEETING_UPDATED = "meeting_updated"
    MEETING_CANCELLED = "meeting_cancelled"
    MEETING_DELETED = "meeting_deleted"
    MEETING_NOTICE_GENERATED = "meeting_notice_generated"
    MEETING_NOTICE_POSTED = "meeting_notice_posted"
    MEETING_NOTICE_PUBLISHED = "meeting_notice_published"
    MEETING_AGENDA_PUBLISHED = "meeting_agenda_published"

    # Agenda actions
    AGENDA_ITEM_ADDED = "agenda_item_added"
    AGENDA_ITEM_UPDATED = "agenda_item_updated"
    AGENDA_ITEM_DELETED = "agenda_item_deleted"

    # Minutes actions
    MINUTES_CREATED = "minutes_created"
    MINUTES_UPDATED = "minutes_updated"
    MINUTES_APPROVED = "minutes_approved"
    MINUTES_PUBLISHED = "minutes_published"
    MINUTES_VIEWED = "minutes_viewed"
    MINUTES_DELETED = "minutes_deleted"

    # Voting actions
    VOTE_CREATED = "vote_created"
    VOTE_OPENED = "vote_opened"
    VOTE_CLOSED = "vote_closed"
    VOTE_DELETED = "vote_deleted"
    VOTE_CAST = "vote_cast"
    VOTE_LOCKED = "vote_locked"

    # Motion actions
    MOTION_CREATED = "motion_created"
    MOTION_SECONDED = "motion_seconded"
    MOTION_DISCUSSION_OPENED = "motion_discussion_opened"
    MOTION_DISCUSSION_CLOSED = "motion_discussion_closed"
    MOTION_TABLED = "motion_tabled"
    MOTION_WITHDRAWN = "motion_withdrawn"
    MOTION_PASSED = "motion_passed"
    MOTION_FAILED = "motion_failed"
    MOTION_AMENDED = "motion_amended"
    MOTION_DELETED = "motion_deleted"

    # Document actions
    DOCUMENT_CREATED = "document_created"
    DOCUMENT_UPDATED = "document_updated"
    DOCUMENT_PUBLISHED = "document_published"
    DOCUMENT_VIEWED = "document_viewed"
    DOCUMENT_ARCHIVED = "document_archived"
    DOCUMENT_DELETED = "document_deleted"

    # Action item actions
    ACTION_ITEM_CREATED = "action_item_created"
    ACTION_ITEM_UPDATED = "action_item_updated"
    ACTION_ITEM_STATUS_CHANGED = "action_item_status_changed"
    ACTION_ITEM_DELETED = "action_item_deleted"

    # Board member actions
    BOARD_MEMBER_CREATED = "board_member_created"
    BOARD_MEMBER_UPDATED = "board_member_updated"
    BOARD_MEMBER_DELETED = "board_member_deleted"
    BOARD_MEMBER_TERM_ENDED = "board_member_term_ended"

    # Committee actions
    COMMITTEE_CREATED = "committee_created"
    COMMITTEE_UPDATED = "committee_updated"
    COMMITTEE_DELETED = "committee_deleted"
    COMMITTEE_MEMBER_ADDED = "committee_member_added"
    COMMITTEE_MEMBER_REMOVED = "committee_member_removed"

    # Attendance actions
    ATTENDANCE_RECORDED = "attendance_recorded"
    ATTENDANCE_CHECKED_IN = "attendance_checked_in"
    ATTENDANCE_CHECKED_OUT = "attendance_checked_out"
    ATTENDANCE_MARKED_ABSENT = "attendance_marked_absent"

    # Strategic planning actions
    STRATEGIC_GOAL_CREATED = "strategic_goal_created"
    STRATEGIC_GOAL_UPDATED = "strategic_goal_updated"
    STRATEGIC_GOAL_DELETED = "strategic_goal_deleted"
    STRATEGIC_MILESTONE_CREATED = "strategic_milestone_created"
    STRATEGIC_MILESTONE_DELETED = "strategic_milestone_deleted"

    # Public comment actions
    PUBLIC_COMMENT_SUBMITTED = "public_comment_submitted"
    PUBLIC_COMMENT_APPROVED = "public_comment_approved"
    PUBLIC_COMMENT_REJECTED = "public_comment_rejected"
    PUBLIC_COMMENT_READ_INTO_RECORD = "public_comment_read_into_record"

    # Executive session sealing actions
    MINUTES_SEALED = "minutes_sealed"
    MINUTES_UNSEALED = "minutes_unsealed"

    # Recusal actions
    RECUSAL_DECLARED = "recusal_declared"
    RECUSAL_WITHDRAWN = "recusal_withdrawn"

    # Records retention actions
    LEGAL_HOLD_PLACED = "legal_hold_placed"
    LEGAL_HOLD_RELEASED = "legal_hold_released"
    RECORD_DISPOSITION = "record_disposition"

    # COI disclosure actions
    COI_DISCLOSURE_SUBMITTED = "coi_disclosure_submitted"
    COI_DISCLOSURE_SUPERSEDED = "coi_disclosure_superseded"
    COI_OVERLAP_DETECTED = "coi_overlap_detected"


class BoardAuditLog(Base):
    __tablename__ = "board_audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Who performed the action (user who made the change)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # What action was performed
    action = Column(SQLEnum(BoardAuditAction, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)

    # What entity type was affected (e.g., "Meeting", "Motion", "Vote")
    entity_type = Column(String(50), nullable=False, index=True)

    # Which entity was affected (its ID)
    entity_id = Column(Integer, nullable=False, index=True)

    # Related meeting (for cross-referencing)
    meeting_id = Column(
        Integer,
        ForeignKey("board_meetings.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Detailed information about the change
    details = Column(JSON, nullable=True)
    # details should include:
    # - old_values: Previous values for update operations
    # - new_values: New values for update operations
    # - reason: Cancellation reason, approval reason, etc.
    # - result: Success/failure of operation
    # - error_message: If operation failed

    # IP address of the user who performed the action
    ip_address = Column(String(45), nullable=True)

    # User agent string for additional context
    user_agent = Column(String(500), nullable=True)

    # Additional notes
    notes = Column(Text, nullable=True)

    # Timestamp when action was performed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship(
        "User",
        foreign_keys=[user_id],
        backref="board_audit_logs"
    )

    meeting = relationship(
        "BoardMeeting",
        foreign_keys=[meeting_id],
        backref="audit_logs"
    )

    def __repr__(self) -> str:
        return (
            f"<BoardAuditLog(id={self.id}, action={self.action}, "
            f"entity_type={self.entity_type}, entity_id={self.entity_id}, "
            f"user_id={self.user_id})>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action.value,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "meeting_id": self.meeting_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
