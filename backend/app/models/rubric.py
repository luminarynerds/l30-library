# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text, UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base
from .mixins import TimestampMixin


class Rubric(Base, TimestampMixin):
    __tablename__ = "rubrics"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Source/attribution
    source_url = Column(String(500))  # Original source of the rubric
    source_attribution = Column(Text)  # Attribution text (e.g., "by Sarah Tribelhorn, CC BY-NC-SA 4.0")

    # Scoring configuration
    max_score = Column(Integer, default=4)  # Maximum score per criterion (e.g., 4 for Excellent)
    min_score = Column(Integer, default=1)  # Minimum score per criterion (e.g., 1 for Poor)

    # Level labels (customizable per rubric)
    level_labels = Column(JSONB, default={
        "4": "Excellent",
        "3": "Good",
        "2": "Fair",
        "1": "Poor"
    })

    # Organization/categorization
    category = Column(String(100), index=True)  # e.g., "ai_ethics", "digital_literacy", "information_literacy"
    tags = Column(JSONB, default=[])  # Searchable tags

    # Access control
    access_level = Column(String(20), default="patron")  # patron, staff, admin
    is_published = Column(Boolean, default=False, index=True)
    is_featured = Column(Boolean, default=False, index=True)

    # Optional association with learning content
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True, index=True)

    # Metadata
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    criteria = relationship(
        "RubricCriterion",
        back_populates="rubric",
        cascade="all, delete-orphan",
        order_by="RubricCriterion.sort_order"
    )
    assessments = relationship(
        "RubricAssessment",
        back_populates="rubric",
        cascade="all, delete-orphan"
    )


class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"

    id = Column(Integer, primary_key=True, index=True)
    rubric_id = Column(
        Integer, ForeignKey("rubrics.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name = Column(String(255), nullable=False)  # e.g., "Fairness and Bias"
    description = Column(Text)  # Optional expanded description of this criterion

    # Level descriptors: maps score to description text
    # Example: {
    #   "4": ["Identifies and actively mitigates potential biases", "Considers diverse perspectives"],
    #   "3": ["Identifies potential bias but mitigation strategies are limited"],
    #   "2": ["Some potential for bias is acknowledged but not addressed"],
    #   "1": ["No consideration of bias or diversity"]
    # }
    levels = Column(JSONB, nullable=False)

    # Weight for scoring (optional - for weighted rubrics)
    weight = Column(Integer, default=1)

    sort_order = Column(Integer, default=0)

    # Relationships
    rubric = relationship("Rubric", back_populates="criteria")


class RubricAssessment(Base):
    __tablename__ = "rubric_assessments"
    __table_args__ = (
        UniqueConstraint("rubric_id", "user_id", "target_identifier", name="uq_rubric_assessment_target"),
    )

    id = Column(Integer, primary_key=True, index=True)
    rubric_id = Column(
        Integer, ForeignKey("rubrics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # What is being assessed (flexible identifier)
    target_identifier = Column(String(255), nullable=False)  # e.g., "ChatGPT", "Project X", "self"
    target_description = Column(Text)  # Optional description of what's being assessed

    # Scores for each criterion
    # Example: {"1": 4, "2": 3, "3": 2}  (criterion_id: score)
    scores = Column(JSONB, nullable=False, default={})

    # Optional notes for each criterion
    # Example: {"1": "Strong bias mitigation...", "2": "Could improve..."}
    notes = Column(JSONB, default={})

    # Overall notes/summary
    overall_notes = Column(Text)

    # Calculated fields
    total_score = Column(Integer)
    max_possible_score = Column(Integer)
    percentage = Column(Integer)  # 0-100

    # Status
    is_complete = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True))

    # Metadata, server_default=func.now())

    # Relationships
    rubric = relationship("Rubric", back_populates="assessments")
