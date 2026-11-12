# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from ..mixins import TimestampMixin
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ...core.database import Base


class BoardRecusalDeclaration(Base, TimestampMixin):
    __tablename__ = "board_recusal_declarations"

    id = Column(Integer, primary_key=True, index=True)
    board_member_id = Column(
        Integer,
        ForeignKey("board_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # What they are recusing from (at least one should be set)
    vote_id = Column(
        Integer,
        ForeignKey("board_votes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    motion_id = Column(
        Integer,
        ForeignKey("board_motions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    topic_description = Column(Text)  # Free text for broader recusals

    reason = Column(Text, nullable=False)
    declared_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Withdrawal tracking
    is_active = Column(Boolean, default=True, index=True)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    withdrawn_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    withdrawn_reason = Column(Text, nullable=True)

    # Relationships
    board_member = relationship("BoardMember", backref="recusal_declarations")
    vote = relationship("BoardVote", backref="recusal_declarations")
    motion = relationship("BoardMotion", backref="recusal_declarations")
    withdrawn_by = relationship("User", foreign_keys=[withdrawn_by_id])
