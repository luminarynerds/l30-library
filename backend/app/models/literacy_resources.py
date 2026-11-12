# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum, StrEnum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SQLEnum, ForeignKey,
    Integer, String, Text, Index, Numeric
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


class LiteracyResourceType(StrEnum):
    BOOK = "book"
    AUDIOBOOK = "audiobook"
    DIGITAL_MATERIAL = "digital_material"
    WORKSHEET = "worksheet"
    ASSESSMENT_TOOL = "assessment_tool"
    LEARNING_VIDEO = "learning_video"
    INTERACTIVE_TOOL = "interactive_tool"
    ARTICLE = "article"
    GUIDE = "guide"
    EXERCISE_SET = "exercise_set"


class ResourceFormat(StrEnum):
    PRINT = "print"
    DIGITAL = "digital"
    AUDIO = "audio"
    VIDEO = "video"
    INTERACTIVE = "interactive"
    HYBRID = "hybrid"


class AssessmentLevel(StrEnum):
    PRE_LITERACY = "pre_literacy"
    EMERGENT = "emergent"
    BEGINNING = "beginning"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PROFICIENT = "proficient"


class ResourceTheme(StrEnum):
    FICTION_GENERAL = "fiction_general"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    SCIENCE_FICTION = "science_fiction"
    FANTASY = "fantasy"
    BIOGRAPHY = "biography"
    HISTORY = "history"
    SCIENCE = "science"
    NATURE = "nature"
    COOKING = "cooking"
    TRAVEL = "travel"
    BUSINESS = "business"
    SELF_HELP = "self_help"
    POETRY = "poetry"
    GRAPHIC_NOVEL = "graphic_novel"


class LiteracyResource(Base, TimestampMixin):
    __tablename__ = "literacy_resources"

    id = Column(Integer, primary_key=True, index=True)

    # ==================== RESOURCE IDENTIFICATION ====================
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    isbn = Column(String(20), nullable=True, unique=True)  # For books

    # ==================== RESOURCE CLASSIFICATION ====================
    resource_type = Column(
        String(50),
        nullable=False,
        index=True
    )
    format = Column(
        String(50),
        nullable=False,
        default=ResourceFormat.PRINT
    )

    # ==================== LEVEL TARGETING ====================
    min_level = Column(
        String(50),
        nullable=True
    )
    max_level = Column(
        String(50),
        nullable=True
    )

    # ==================== CONTENT CATEGORIZATION ====================
    theme = Column(
        String(50),
        nullable=True
    )
    keywords = Column(Text, nullable=True)  # Comma-separated search keywords
    subject_area = Column(String(100), nullable=True)

    # ==================== RESOURCE CONTENT ====================
    author = Column(String(255), nullable=True)
    publisher = Column(String(255), nullable=True)
    publication_year = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)  # For books
    duration_minutes = Column(Integer, nullable=True)  # For videos
    estimated_reading_level = Column(Integer, nullable=True)  # Flesch-Kincaid grade level

    # ==================== AVAILABILITY AND ACCESS ====================
    resource_url = Column(Text, nullable=True)  # Link to resource or purchase page
    url_type = Column(String(50), nullable=True)  # "open_access", "purchase", "library_link", etc.
    is_digital = Column(Boolean, default=False)
    digital_file_url = Column(Text, nullable=True)  # Link to actual file if available online
    library_copy_id = Column(Integer, nullable=True)  # Link to library item if available

    # ==================== METADATA ====================
    is_active = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False)
    difficulty_rating = Column(Integer, nullable=True)  # 1-5 scale
    learner_reviews = Column(Integer, default=0, nullable=False)
    average_rating = Column(Numeric(3, 2), nullable=True)  # 1-5 scale
    accessibility_notes = Column(Text, nullable=True)  # Large print, audio, etc.

    # ==================== RELATIONSHIPS ====================
    recommendations = relationship(
        "LiteracyResourceRecommendation",
        back_populates="resource",
        cascade="all, delete-orphan"
    )
    collection_items = relationship(
        "LiteracyCollectionItem",
        back_populates="resource",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_literacy_resource_type_level", resource_type, min_level, max_level),
        Index("idx_literacy_resource_active", is_active),
    )


class LiteracyResourceRecommendation(Base, TimestampMixin):
    __tablename__ = "literacy_resource_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    learner_id = Column(Integer, ForeignKey("literacy_learners.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = Column(Integer, ForeignKey("literacy_resources.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== RECOMMENDATION DETAILS ====================
    recommended_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    recommendation_score = Column(Numeric(3, 2), nullable=True)  # 0-1 scale

    # ==================== RANKING ====================
    order_rank = Column(Integer, nullable=False)  # Position in recommendation list
    reason = Column(Text, nullable=True)  # Why this was recommended

    # ==================== LEARNER ENGAGEMENT ====================
    was_accessed = Column(Boolean, default=False)
    was_borrowed = Column(Boolean, default=False)
    learner_feedback = Column(Text, nullable=True)  # Learner's comments
    learner_rating = Column(Integer, nullable=True)  # 1-5 scale

    # ==================== RELATIONSHIPS ====================
    learner = relationship("LiteracyLearner", back_populates="resource_recommendations")
    resource = relationship("LiteracyResource", back_populates="recommendations")

    __table_args__ = (
        Index("idx_literacy_recommendation_learner_rank", learner_id, order_rank),
    )


class LiteracyCollection(Base, TimestampMixin):
    __tablename__ = "literacy_collections"

    id = Column(Integer, primary_key=True, index=True)
    curator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # ==================== COLLECTION IDENTIFICATION ====================
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    collection_type = Column(String(50), nullable=True)  # "theme", "level", "topic", "author", etc.

    # ==================== TARGETING ====================
    min_level = Column(
        String(50),
        nullable=True
    )
    max_level = Column(
        String(50),
        nullable=True
    )
    theme = Column(
        String(50),
        nullable=True
    )

    # ==================== STATUS ====================
    is_active = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False)

    # ==================== STATISTICS ====================
    item_count = Column(Integer, default=0, nullable=False)

    # ==================== RELATIONSHIPS ====================
    curator = relationship("User", backref="literacy_collections_created")
    items = relationship(
        "LiteracyCollectionItem",
        back_populates="collection",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_literacy_collection_active", is_active),
    )


class LiteracyCollectionItem(Base, TimestampMixin):
    __tablename__ = "literacy_collection_items"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("literacy_collections.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = Column(Integer, ForeignKey("literacy_resources.id", ondelete="CASCADE"), nullable=False, index=True)

    # ==================== ORDERING ====================
    position = Column(Integer, nullable=False)  # Position in collection

    # ==================== METADATA ====================
    notes = Column(Text, nullable=True)

    # ==================== RELATIONSHIPS ====================
    collection = relationship("LiteracyCollection", back_populates="items")
    resource = relationship("LiteracyResource", back_populates="collection_items")

    __table_args__ = (
        Index("idx_literacy_collection_item_collection_pos", collection_id, position),
    )
