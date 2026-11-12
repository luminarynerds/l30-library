# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from ..mixins import TimestampMixin, AuditMixin
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ...core.database import Base


class BoardMinutesAmendment(Base, TimestampMixin, AuditMixin):
    __tablename__ = "board_minutes_amendments"

    id = Column(Integer, primary_key=True, index=True)
    minutes_id = Column(
        Integer,
        ForeignKey("board_minutes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # What changed
    amendment_text = Column(Text, nullable=False)
    section_title = Column(String(200))  # Which section was amended
    original_text = Column(Text)  # Snapshot of text before amendment

    # Approval
    amendment_reason = Column(Text, nullable=False)
    amendment_vote_result = Column(String(200))  # e.g., "Approved 6-1"
    approved_at = Column(DateTime(timezone=True))
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    minutes = relationship("BoardMinutes", backref="amendments")
    approved_by = relationship("User", foreign_keys=[approved_by_id])
