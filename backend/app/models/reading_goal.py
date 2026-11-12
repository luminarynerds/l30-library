# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class ReadingGoal(Base, TimestampMixin):

    __tablename__ = "reading_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year = Column(Integer, nullable=False)
    target_books = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "year", name="uq_user_year_reading_goal"),
    )

    user = relationship("User")
