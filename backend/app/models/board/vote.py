# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from ..mixins import TimestampMixin, AuditMixin
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import StrEnum
from ...core.database import Base


class VoteType(StrEnum):
    SIMPLE_MAJORITY = "simple_majority"
    TWO_THIRDS = "two_thirds"
    UNANIMOUS = "unanimous"


class VoteStatus(StrEnum):
    UPCOMING = "upcoming"
    OPEN = "open"
    CLOSED = "closed"


class VoteChoice(StrEnum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"
    RECUSAL = "recusal"


class BoardVote(Base, TimestampMixin, AuditMixin):
    __tablename__ = "board_votes"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("board_meetings.id", ondelete="SET NULL"), index=True)

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    vote_type = Column(String(30), nullable=False, default="simple_majority")

    opens_at = Column(DateTime(timezone=True), nullable=False, index=True)
    closes_at = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="upcoming", index=True)

    quorum_required = Column(Integer, nullable=False, default=4)
    passed = Column(Boolean)
    final_tally_yes = Column(Integer, default=0)
    final_tally_no = Column(Integer, default=0)
    final_tally_abstain = Column(Integer, default=0)
    final_tally_recusal = Column(Integer, default=0)

    closed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_at_actual = Column(DateTime(timezone=True))
    locked_at = Column(DateTime(timezone=True), nullable=True, index=True)


    # Relationships
    meeting = relationship("BoardMeeting")
    votes_cast = relationship("BoardVoteCast", back_populates="vote", cascade="all, delete-orphan")
    closed_by = relationship("User", foreign_keys=[closed_by_id])


class BoardVoteCast(Base):
    __tablename__ = "board_votes_cast"

    id = Column(Integer, primary_key=True, index=True)
    vote_id = Column(Integer, ForeignKey("board_votes.id", ondelete="CASCADE"), nullable=False, index=True)
    board_member_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    choice = Column(String(20), nullable=False)  # yes, no, abstain
    comment = Column(Text)

    cast_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    vote = relationship("BoardVote", back_populates="votes_cast")
    board_member = relationship("User")

    __table_args__ = (
        UniqueConstraint('vote_id', 'board_member_id', name='uq_vote_cast_member'),
    )
