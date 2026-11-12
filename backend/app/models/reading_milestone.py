# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class ReadingMilestone(Base, TimestampMixin):

    __tablename__ = "reading_milestones"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    milestone_type = Column(
        String(50), nullable=False
    )  # books_finished, genre_explored, goal_percent, first_book, first_progress
    milestone_key = Column(
        String(100), nullable=False
    )  # e.g. "books_finished_10", "genre_sci-fi", "goal_50pct"
    title = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    earned_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    dismissed = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("user_id", "milestone_key", name="uq_user_milestone_key"),
    )

    user = relationship("User")
