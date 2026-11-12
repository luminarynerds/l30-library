# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, ForeignKey, CheckConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class ResponseModerationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EventReviewResponse(Base):

    __tablename__ = "event_review_responses"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("event_reviews.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    # Response content
    content = Column(Text, nullable=False)

    # Author information (cached for display)
    author_name = Column(String(255), nullable=True)
    author_email = Column(String(255), nullable=True)
    is_staff_response = Column(Boolean, default=False, nullable=False)

    # Moderation fields
    moderation_status = Column(
        SQLEnum(ResponseModerationStatus, name="responsemoderationstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ResponseModerationStatus.PENDING,
        nullable=False,
        index=True
    )
    moderated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    moderated_at = Column(DateTime(timezone=True), nullable=True)
    moderation_reason = Column(Text, nullable=True)

    # Timestamps, server_default=func.now())

    # Relationships
    review = relationship("EventReview", back_populates="responses")
    author = relationship("User", foreign_keys=[author_id])
    moderated_by = relationship("User", foreign_keys=[moderated_by_id])

