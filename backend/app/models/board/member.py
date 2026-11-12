# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from ..mixins import TimestampMixin
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import StrEnum
from ...core.database import Base


class BoardPosition(StrEnum):
    PRESIDENT = "president"
    VICE_PRESIDENT = "vice_president"
    SECRETARY = "secretary"
    TREASURER = "treasurer"
    MEMBER = "member"


class BoardMember(Base, TimestampMixin):
    __tablename__ = "board_members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    position = Column(String(50), default="member")  # president, vice_president, secretary, treasurer, member

    term_start_date = Column(DateTime(timezone=True), nullable=False)
    term_end_date = Column(DateTime(timezone=True))
    is_current = Column(Boolean, default=True, index=True)
    is_chair = Column(Boolean, default=False)

    # Term tracking
    term_number = Column(Integer, nullable=True)  # Which term (1st, 2nd, etc.)
    max_consecutive_terms = Column(Integer, nullable=True)  # Limit per bylaws

    bio = Column(Text)
    photo_url = Column(String(500))

    # Public contact info for website
    public_email = Column(String(255))
    office_hours = Column(Text)


    # Relationships
    user = relationship("User", foreign_keys=[user_id])
