# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from sqlalchemy import (
    Boolean, Column, DateTime, Integer, String, Text,
    ForeignKey
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class BetaFeedbackType(StrEnum):
    BUG = "bug"
    SUGGESTION = "suggestion"
    CONFUSION = "confusion"
    PRAISE = "praise"
    OTHER = "other"


class FeedbackPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FeedbackStatus(StrEnum):
    NEW = "new"
    REVIEWED = "reviewed"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


class BetaFeedback(Base):

    __tablename__ = "beta_feedback"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(BetaFeedbackType, name="beta_feedbacktype", create_type=False, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    status = Column(SQLEnum(FeedbackStatus, name="feedbackstatus", create_type=False, values_callable=lambda x: [e.value for e in x]), default=FeedbackStatus.NEW, nullable=False)
    priority = Column(SQLEnum(FeedbackPriority, name="feedbackpriority", create_type=False, values_callable=lambda x: [e.value for e in x]), default=FeedbackPriority.MEDIUM, nullable=False)

    # Content
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    page_url = Column(String(500), nullable=True)
    browser_info = Column(String(300), nullable=True)
    screenshot_url = Column(String(500), nullable=True)

    # Submitter
    submitted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    submitted_by = relationship("User", foreign_keys=[submitted_by_id])
    email = Column(String(254), nullable=True)  # For anonymous submissions

    # Admin response
    admin_notes = Column(Text, nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    extra_data = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
