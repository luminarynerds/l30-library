# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from ..mixins import TimestampMixin, AuditMixin
from enum import StrEnum

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...core.database import Base


class MotionType(StrEnum):
    MAIN = "main"  # Primary motion introducing new business
    AMENDMENT = "amendment"  # Modifies a pending motion
    SUBSIDIARY = "subsidiary"  # Applied to other motions (postpone, refer, etc.)
    PRIVILEGED = "privileged"  # Urgent matters (recess, adjourn)
    INCIDENTAL = "incidental"  # Procedural (point of order, appeal)


class MotionStatus(StrEnum):
    DRAFT = "draft"  # Being prepared
    PENDING = "pending"  # Awaiting second
    SECONDED = "seconded"  # Has a second, ready for discussion
    UNDER_DISCUSSION = "under_discussion"  # Being discussed
    CALLED_TO_VOTE = "called_to_vote"  # Discussion closed, voting
    PASSED = "passed"  # Approved
    FAILED = "failed"  # Not approved
    TABLED = "tabled"  # Postponed indefinitely
    WITHDRAWN = "withdrawn"  # Withdrawn by mover
    REFERRED = "referred"  # Referred to committee
    AMENDED = "amended"  # Motion was amended


class ResolutionStatus(StrEnum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    ADOPTED = "adopted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    RESCINDED = "rescinded"


class BoardMotion(Base, TimestampMixin, AuditMixin):
    __tablename__ = "board_motions"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(
        Integer,
        ForeignKey("board_meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    motion_type = Column(String(30), nullable=False, default="main", index=True)
    status = Column(String(30), nullable=False, default="draft", index=True)

    # Motion content
    motion_number = Column(String(50))  # e.g., "2026-001"
    title = Column(String(500), nullable=False)
    motion_text = Column(Text, nullable=False)  # The actual motion wording
    rationale = Column(Text)  # Why this motion is being proposed
    plain_language_summary = Column(Text, nullable=True)

    # If this is an amendment, link to parent motion
    parent_motion_id = Column(Integer, ForeignKey("board_motions.id", ondelete="SET NULL"), nullable=True)
    amended_text = Column(Text)  # For amendments, the proposed new text

    # Motion workflow
    moved_by_id = Column(Integer, ForeignKey("board_members.id", ondelete="SET NULL"), nullable=True)
    moved_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    seconded_by_id = Column(Integer, ForeignKey("board_members.id", ondelete="SET NULL"), nullable=True)
    seconded_at = Column(DateTime(timezone=True))

    # Discussion tracking
    discussion_opened_at = Column(DateTime(timezone=True))
    discussion_closed_at = Column(DateTime(timezone=True))
    discussion_notes = Column(Text)  # Summary of key discussion points

    # Vote tracking (links to BoardVote for detailed vote records)
    vote_id = Column(Integer, ForeignKey("board_votes.id", ondelete="SET NULL"))
    vote_called_at = Column(DateTime(timezone=True))

    # Outcome
    outcome_recorded_at = Column(DateTime(timezone=True))
    outcome_notes = Column(Text)

    # For referred motions
    referred_to_committee_id = Column(Integer, ForeignKey("board_committees.id", ondelete="SET NULL"))
    referred_at = Column(DateTime(timezone=True))
    referred_notes = Column(Text)

    # For tabled motions
    tabled_at = Column(DateTime(timezone=True))
    tabled_until = Column(DateTime(timezone=True))
    tabled_reason = Column(Text)

    # For withdrawn motions
    withdrawn_at = Column(DateTime(timezone=True))
    withdrawn_reason = Column(Text)


    # Relationships
    meeting = relationship("BoardMeeting", backref="motions")
    # Self-referential relationship with lazy loading to prevent circular reference GC issues
    parent_motion = relationship(
        "BoardMotion",
        remote_side=[id],
        back_populates="amendments",
        lazy="select"
    )
    amendments = relationship(
        "BoardMotion",
        back_populates="parent_motion",
        lazy="select"
    )
    moved_by = relationship("BoardMember", foreign_keys=[moved_by_id])
    seconded_by = relationship("BoardMember", foreign_keys=[seconded_by_id])
    vote = relationship("BoardVote")
    referred_to_committee = relationship("Committee")


class BoardResolution(Base, TimestampMixin, AuditMixin):
    __tablename__ = "board_resolutions"

    id = Column(Integer, primary_key=True, index=True)

    # Resolution identification
    resolution_number = Column(String(50), nullable=False, unique=True, index=True)  # e.g., "RES-2026-001"
    title = Column(String(500), nullable=False)
    status = Column(String(30), nullable=False, default="draft", index=True)

    # Content
    preamble = Column(Text)  # "WHEREAS" clauses
    resolution_text = Column(Text, nullable=False)  # "RESOLVED" clauses
    summary = Column(Text)  # Plain language summary

    # Categories for organization
    category = Column(String(100), index=True)  # e.g., "Policy", "Budget", "Personnel"
    tags = Column(JSONB, default=list)

    # Source
    originating_motion_id = Column(Integer, ForeignKey("board_motions.id", ondelete="SET NULL"))
    meeting_id = Column(Integer, ForeignKey("board_meetings.id", ondelete="CASCADE"))
    committee_id = Column(Integer, ForeignKey("board_committees.id", ondelete="SET NULL"))

    # Adoption
    proposed_date = Column(DateTime(timezone=True))
    proposed_by_id = Column(Integer, ForeignKey("board_members.id", ondelete="SET NULL"), nullable=True)

    adopted_date = Column(DateTime(timezone=True))
    adopted_vote_id = Column(Integer, ForeignKey("board_votes.id", ondelete="SET NULL"))

    # Effective dates
    effective_date = Column(DateTime(timezone=True))
    expiration_date = Column(DateTime(timezone=True))  # For time-limited resolutions

    # Supersession
    supersedes_resolution_id = Column(Integer, ForeignKey("board_resolutions.id", ondelete="SET NULL"))
    superseded_by_resolution_id = Column(Integer, ForeignKey("board_resolutions.id", ondelete="SET NULL"))
    superseded_date = Column(DateTime(timezone=True))

    # Rescission
    rescinded_date = Column(DateTime(timezone=True))
    rescinded_by_motion_id = Column(Integer, ForeignKey("board_motions.id", ondelete="SET NULL"))
    rescinded_reason = Column(Text)

    # Publication
    is_public = Column(Boolean, default=True, index=True)
    published_date = Column(DateTime(timezone=True))
    published_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Attachments - linked to board documents
    attachment_document_ids = Column(JSONB, default=list)

    # Retention
    is_permanent = Column(Boolean, default=True)


    # Relationships
    originating_motion = relationship("BoardMotion", foreign_keys=[originating_motion_id])
    meeting = relationship("BoardMeeting", backref="resolutions")
    committee = relationship("Committee", backref="resolutions")
    proposed_by = relationship("BoardMember", foreign_keys=[proposed_by_id])
    adopted_vote = relationship("BoardVote")
    supersedes = relationship("BoardResolution", foreign_keys=[supersedes_resolution_id], remote_side=[id])
    superseded_by = relationship("BoardResolution", foreign_keys=[superseded_by_resolution_id], remote_side=[id])
    rescinded_by_motion = relationship("BoardMotion", foreign_keys=[rescinded_by_motion_id])
    published_by = relationship("User", foreign_keys=[published_by_id])
