# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class RelationshipType(StrEnum):
    # Adaptation relationships
    manga_to_anime = "manga_to_anime"  # Manga adapted as anime
    light_novel_to_manga = "light_novel_to_manga"  # Light novel adapted as manga
    light_novel_to_anime = "light_novel_to_anime"  # Light novel adapted as anime
    book_to_film = "book_to_film"  # Book adapted as film
    film_to_novelization = "film_to_novelization"  # Film has written novelization
    manga_to_live_action = "manga_to_live_action"  # Manga adapted as live-action

    # Supplementary relationships
    series_soundtrack = "series_soundtrack"  # Soundtrack CD for series
    series_artbook = "series_artbook"  # Art book for series
    series_encyclopedia = "series_encyclopedia"  # Encyclopedia/reference for series
    series_guide = "series_guide"  # Official guide for series

    # Spin-off and prequel/sequel relationships
    spin_off = "spin_off"  # Spin-off work from main series
    prequel = "prequel"  # Prequel to work
    sequel = "sequel"  # Sequel to work
    side_story = "side_story"  # Side story related to work

    # General relationships
    same_universe = "same_universe"  # Set in same fictional universe
    shared_setting = "shared_setting"  # Share same setting/world
    shared_characters = "shared_characters"  # Share some characters
    related_series = "related_series"  # Related but independent series

    # Discovery suggestions
    PARENT_CHILD = "parent_child"
    SIBLING = "sibling"
    OTHER = "other"
    if_you_liked = "if_you_liked"  # Recommendation: if you liked X, try Y


class RelationshipDirection(StrEnum):
    forward = "forward"  # Source -> Target (manga -> anime)
    backward = "backward"  # Target -> Source (anime <- manga)
    bidirectional = "bidirectional"  # Both directions


class WorkRelationship(Base):
    __tablename__ = "work_relationships"

    id = Column(Integer, primary_key=True, index=True)

    # Work identification
    source_work_id = Column(
        Integer,
        ForeignKey("bibframe_works.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    target_work_id = Column(
        Integer,
        ForeignKey("bibframe_works.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationship type
    relationship_type = Column(
        SQLEnum(RelationshipType, name="relationshiptype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )

    # Direction
    direction = Column(
        SQLEnum(RelationshipDirection, name="relationshipdirection", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=RelationshipDirection.forward,
        nullable=False
    )

    # Metadata
    title = Column(String(500), nullable=True)  # Display title for relationship
    description = Column(Text, nullable=True)  # Description of relationship
    notes = Column(Text, nullable=True)  # Internal notes about relationship

    # Temporal information
    adaptation_year = Column(Integer, nullable=True)  # Year of adaptation
    announcement_date = Column(DateTime(timezone=True), nullable=True)  # When adaptation announced
    release_date = Column(DateTime(timezone=True), nullable=True)  # When adapted work released

    # Quality and relevance
    is_official = Column(Boolean, default=True, nullable=False)  # Official vs fan adaptation
    is_complete = Column(Boolean, default=False, nullable=False)  # Adaptation is complete
    adaptation_fidelity = Column(String(50), nullable=True)  # faithful, loose, very_loose

    # Discovery/recommendation
    show_in_discovery = Column(Boolean, default=True, nullable=False)  # Show in suggestions
    recommendation_reason = Column(String(500), nullable=True)  # Why we recommend this
    popularity_score = Column(Integer, default=0, nullable=True)  # Popularity of relationship

    # Authority/source information
    source_authority = Column(String(100), nullable=True)  # Authority source (e.g., "anilist", "mal", "manual")
    authority_id = Column(String(100), nullable=True)  # ID in authority source
    authority_uri = Column(String(500), nullable=True)  # URI in authority source
    verified = Column(Boolean, default=False, nullable=False)  # Verified by librarian

    # Administrative
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Linked data
    linked_data = Column(JSONB, nullable=True)  # Additional metadata as JSON

    # Timestamps, server_default=func.now())

    # Relationships
    source_work = relationship(
        "BibframeWork",
        foreign_keys=[source_work_id],
        backref="related_works_as_source"
    )
    target_work = relationship(
        "BibframeWork",
        foreign_keys=[target_work_id],
        backref="related_works_as_target"
    )
    created_by = relationship("User", foreign_keys=[created_by_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint(
            "source_work_id", "target_work_id", "relationship_type",
            name="uq_work_relationship"
        ),
        Index("ix_work_relationships_source", "source_work_id"),
        Index("ix_work_relationships_target", "target_work_id"),
        Index("ix_work_relationships_type", "relationship_type"),
        Index("ix_work_relationships_verified", "verified"),
        Index("ix_work_relationships_discoverable", "show_in_discovery"),
        Index("ix_work_relationships_type_discoverable", "relationship_type", "show_in_discovery"),
    )

    def __repr__(self):
        return f"<WorkRelationship(id={self.id}, type='{self.relationship_type}', source={self.source_work_id}, target={self.target_work_id})>"


class CrossFormatDiscovery(Base):
    __tablename__ = "cross_format_discovery"

    id = Column(Integer, primary_key=True, index=True)

    # Series/work identification
    primary_work_id = Column(
        Integer,
        ForeignKey("bibframe_works.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Canonical series name
    series_name = Column(String(500), nullable=False, index=True)
    series_slug = Column(String(500), nullable=True, unique=True)  # URL-friendly

    # Counts by format
    format_counts = Column(JSONB, nullable=True)  # {"manga": 2, "anime": 1, "light_novel": 3}
    available_formats = Column(JSONB, nullable=True)  # List of available format types

    # All related works (for discovery)
    related_work_ids = Column(JSONB, nullable=True)  # Array of related work IDs
    relationship_types = Column(JSONB, nullable=True)  # {"manga_to_anime": [...], ...}

    # Popular/trending info
    total_popularity_score = Column(Integer, default=0, nullable=True)
    is_trending = Column(Boolean, default=False, nullable=False)

    # Administrative
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    primary_work = relationship("BibframeWork", foreign_keys=[primary_work_id])

    __table_args__ = (
        Index("ix_cross_format_discovery_series_name", "series_name"),
        Index("ix_cross_format_discovery_trending", "is_trending"),
    )

    def __repr__(self):
        return f"<CrossFormatDiscovery(id={self.id}, series='{self.series_name}')>"


class FormatSuggestion(Base):
    __tablename__ = "format_suggestions"

    id = Column(Integer, primary_key=True, index=True)

    # Source and target formats
    source_work_id = Column(
        Integer,
        ForeignKey("bibframe_works.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    target_work_id = Column(
        Integer,
        ForeignKey("bibframe_works.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Suggestion text (displayed to patrons)
    suggestion_text = Column(String(500), nullable=False)
    suggestion_icon = Column(String(100), nullable=True)  # e.g., "book", "film", "music"

    # Suggestion quality
    confidence_score = Column(Integer, default=50, nullable=False)  # 0-100
    is_global = Column(Boolean, default=True, nullable=False)  # Global vs user-specific

    # Engagement tracking
    suggested_count = Column(Integer, default=0, nullable=False)
    clicked_count = Column(Integer, default=0, nullable=False)
    conversion_count = Column(Integer, default=0, nullable=False)  # User followed suggestion

    # Administrative
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps, server_default=func.now())

    # Relationships
    source_work = relationship("BibframeWork", foreign_keys=[source_work_id])
    target_work = relationship("BibframeWork", foreign_keys=[target_work_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint(
            "source_work_id", "target_work_id",
            name="uq_format_suggestion"
        ),
        Index("ix_format_suggestions_active", "is_active"),
        Index("ix_format_suggestions_global", "is_global"),
        Index("ix_format_suggestions_confidence", "confidence_score"),
    )

    def __repr__(self):
        return f"<FormatSuggestion(id={self.id}, text='{self.suggestion_text[:50]}')>"
