# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from sqlalchemy import (
    Column, DateTime, Integer, String, Text, CheckConstraint,
    ForeignKey, Float, Boolean, JSON
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class FlagType(StrEnum):
    SPAM = "spam"
    HATE_SPEECH = "hate_speech"
    EXCESSIVE_CAPS = "excessive_caps"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    OFF_TOPIC = "off_topic"
    DUPLICATE = "duplicate"


class FlagStatus(StrEnum):
    PENDING = "pending"  # Awaiting staff review
    RESOLVED = "resolved"  # Reviewed and appropriate
    FALSE_POSITIVE = "false_positive"  # Flag was incorrect
    FALSE_NEGATIVE = "false_negative"  # Should have been flagged but wasn't


class ContentFlag(Base):

    __tablename__ = "content_flags"

    id = Column(Integer, primary_key=True, index=True)

    # Review reference
    review_id = Column(Integer, nullable=False, index=True)
    review_type = Column(String(50), nullable=False, index=True)  # event_review, indie_review, etc.

    # Flag information
    flag_type = Column(
        SQLEnum(FlagType, name="flagtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    confidence_score = Column(
        Integer,
        nullable=False,
        index=True,
        comment="0-100 confidence score. Flag if > 70"
    )
    analysis_details = Column(
        JSON,
        nullable=True,
        comment="Detailed analysis results from content flagging service"
    )

    # Staff review and resolution
    status = Column(
        SQLEnum(FlagStatus, name="flagstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=FlagStatus.PENDING,
        nullable=False,
        index=True
    )
    resolved_by = Column(String(255), nullable=True, index=True)  # Staff email
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Staff feedback for model improvement
    is_correct_flag = Column(
        Boolean,
        nullable=True,
        comment="Whether staff confirmed this flag was correct"
    )
    staff_feedback = Column(
        Text,
        nullable=True,
        comment="Staff notes for AI model improvement"
    )

    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    analysis_results = relationship(
        "FlagAnalysisResult",
        back_populates="content_flag",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 100",
                       name="check_confidence_score_range"),
        CheckConstraint("review_type IN ('event_review', 'indie_review', 'other')",
                       name="check_review_type_valid"),
    )


class FlagAnalysisResult(Base):

    __tablename__ = "flag_analysis_results"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key
    content_flag_id = Column(
        Integer,
        ForeignKey("content_flags.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Category information
    flag_category = Column(
        SQLEnum(FlagType, name="flagtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    category_score = Column(
        Integer,
        nullable=False,
        comment="0-100 score for this specific category"
    )
    evidence = Column(
        JSON,
        nullable=True,
        comment="Detailed evidence for this category (patterns found, keywords, etc.)"
    )

    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    content_flag = relationship(
        "ContentFlag",
        back_populates="analysis_results"
    )

    __table_args__ = (
        CheckConstraint("category_score >= 0 AND category_score <= 100",
                       name="check_category_score_range"),
    )
