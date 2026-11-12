# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from sqlalchemy import Column, DateTime, Integer, String, Text, CheckConstraint, ForeignKey
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base


class ReviewModerationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EventReview(Base, TimestampMixin):

    __tablename__ = "event_reviews"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    patron_email = Column(String(255), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5 star rating
    comment = Column(Text, nullable=True)

    # Moderation fields
    moderation_status = Column(
        SQLEnum(ReviewModerationStatus, name="reviewmoderationstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ReviewModerationStatus.PENDING,
        nullable=False,
        index=True
    )
    moderated_by = Column(String(255), nullable=True)  # Email of staff member who moderated
    moderated_at = Column(DateTime(timezone=True), nullable=True)  # When moderation action was taken
    moderation_reason = Column(Text, nullable=True)  # Reason for rejection or notes

    # Content reporting/removal
    is_removed = Column(Integer, default=0, nullable=False)  # 1 if removed by staff, 0 otherwise
    removal_reason = Column(Text, nullable=True)  # Reason for removal
    removed_by = Column(String(255), nullable=True)  # Email of staff member who removed it
    removed_at = Column(DateTime(timezone=True), nullable=True)  # When removal action was taken

    # Relationships
    responses = relationship(
        "EventReviewResponse",
        back_populates="review",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
        CheckConstraint("is_removed IN (0, 1)", name="check_is_removed_binary"),
    )
