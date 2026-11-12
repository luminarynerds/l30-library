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
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


# ============================================================================
# Enums for Comic Cataloging
# ============================================================================


class ComicFormat(StrEnum):
    single_issue = "single_issue"        # Individual comic book issue
    trade_paperback = "trade_paperback"  # Collected trade paperback
    hardcover = "hardcover"              # Hardcover collection
    omnibus = "omnibus"                  # Large collected volume
    graphic_novel = "graphic_novel"      # Standalone graphic novel
    annual = "annual"                    # Annual special edition
    limited_series = "limited_series"    # Finite series run
    one_shot = "one_shot"                # Single standalone issue


class ComicContentWarning(StrEnum):
    violence = "violence"
    graphic_violence = "graphic_violence"
    sexual_content = "sexual_content"
    substance_use = "substance_use"
    self_harm = "self_harm"
    suicide = "suicide"
    abuse = "abuse"
    body_horror = "body_horror"
    animal_harm = "animal_harm"
    death = "death"
    discrimination = "discrimination"
    mild_language = "mild_language"
    strong_language = "strong_language"
    other = "other"


class VariantCoverType(StrEnum):
    first_print = "first_print"              # Original print run
    second_print = "second_print"            # Later reprint
    virgin_cover = "virgin_cover"            # Cover art without text
    variant_artist = "variant_artist"        # Different artist cover
    incentive_variant = "incentive_variant"  # Retail incentive variant
    blank_variant = "blank_variant"          # Blank for signatures
    photo_cover = "photo_cover"              # Photographic cover
    lenticular = "lenticular"                # 3D lenticular effect
    foil_cover = "foil_cover"                # Foil/metallic embossing
    metal_cover = "metal_cover"              # Metal/premium material
    regional_exclusive = "regional_exclusive" # Region-specific variant
    retailer_exclusive = "retailer_exclusive" # Retailer-specific variant
    convention_exclusive = "convention_exclusive" # Convention exclusive
    error = "error"                          # Error variant/misprint
    other = "other"


# ============================================================================
# Core Comic Cataloging Models
# ============================================================================


class ComicSeries(Base):
    __tablename__ = "comic_series"

    id = Column(Integer, primary_key=True, index=True)

    # Series identification
    title = Column(String(500), nullable=False, index=True, unique=True)
    sort_title = Column(String(500), nullable=True)  # For sorting (remove "The", etc.)
    description = Column(Text, nullable=True)

    # Publisher and creator info
    publisher = Column(String(255), nullable=False, index=True)
    publisher_imprint = Column(String(255), nullable=True)  # e.g., "DC Comics" / "Vertigo"
    original_language = Column(String(50), default="English")

    # Series characteristics
    comic_format = Column(
        SQLEnum(ComicFormat, name="comicformat", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ComicFormat.single_issue,
        nullable=False,
    )
    is_ongoing = Column(Boolean, default=True)  # Ongoing vs completed series
    first_publication_year = Column(Integer, nullable=True)
    last_publication_year = Column(Integer, nullable=True)  # NULL if ongoing

    # Count information
    total_issues_published = Column(Integer, nullable=True)
    total_volumes = Column(Integer, nullable=True)  # For trade collections

    # Community and discovery
    genres = Column(ARRAY(String), nullable=True)  # e.g., ["superhero", "action", "drama"]
    characters = Column(ARRAY(String), nullable=True)  # Main character names
    is_crossover_series = Column(Boolean, default=False)

    # Cover image
    cover_image_url = Column(String(500), nullable=True)
    series_logo_url = Column(String(500), nullable=True)

    # Metadata, server_default=func.now())

    # Relationships
    issues = relationship("ComicIssue", back_populates="series", cascade="all, delete-orphan")
    story_arcs = relationship("StoryArc", back_populates="series", cascade="all, delete-orphan")


class ComicIssue(Base):
    __tablename__ = "comic_issues"
    __table_args__ = (
        UniqueConstraint("series_id", "issue_number", name="unique_series_issue"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Link to series and catalog
    series_id = Column(Integer, ForeignKey("comic_series.id", ondelete="CASCADE"), nullable=False, index=True)
    catalog_item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Issue identification
    issue_number = Column(String(20), nullable=False)  # e.g., "1", "2.1", "100", "1A"
    variant_designation = Column(String(100), nullable=True)  # e.g., "1:25 variant", "2nd print"
    issue_title = Column(String(500), nullable=True)  # Optional story title
    is_annual = Column(Boolean, default=False)
    is_special = Column(Boolean, default=False)

    # Volume information (for trade collections)
    volume_number = Column(Integer, nullable=True)  # For trade paperbacks
    collected_issues = Column(ARRAY(String), nullable=True)  # e.g., ["1", "2", "3"]

    # Publication details
    publication_date = Column(DateTime(timezone=True), nullable=True)
    cover_date = Column(String(20), nullable=True)  # e.g., "March 2024" (for printing accuracy)
    isbn = Column(String(20), nullable=True, index=True)
    upc_code = Column(String(20), nullable=True, index=True)  # UPC barcode

    # Story information
    story_synopsis = Column(Text, nullable=True)
    story_arcs_involved = Column(ARRAY(String), nullable=True)  # Story arc titles

    # Creator information (denormalized for quick access)
    # Full creator details in separate ComicIssueCreator table
    writers = Column(ARRAY(String), nullable=True)
    artists = Column(ARRAY(String), nullable=True)
    colorists = Column(ARRAY(String), nullable=True)
    letterers = Column(ARRAY(String), nullable=True)
    editor = Column(String(255), nullable=True)

    # Physical characteristics
    page_count = Column(Integer, nullable=True)
    is_color = Column(Boolean, nullable=True)

    # Content information
    content_warnings = Column(ARRAY(String), nullable=True)  # ComicContentWarning enum values
    rating = Column(String(50), nullable=True)  # e.g., "T for Teen", "M for Mature"
    parental_advisory = Column(Text, nullable=True)  # Custom advisory text

    # Reader community metadata
    has_variant_covers = Column(Boolean, default=False)
    first_appearance_characters = Column(ARRAY(String), nullable=True)
    guest_stars = Column(ARRAY(String), nullable=True)

    # Crossover tracking
    is_part_of_crossover = Column(Boolean, default=False)
    crossover_event = Column(String(500), nullable=True)  # Event name like "Crisis on Infinite Earths"

    # Timestamps, server_default=func.now())

    # Relationships
    series = relationship("ComicSeries", back_populates="issues")
    catalog_item = relationship("CatalogItem")
    variant_covers = relationship("VariantCover", back_populates="issue", cascade="all, delete-orphan")
    creators = relationship("ComicIssueCreator", back_populates="issue", cascade="all, delete-orphan")
    story_arcs = relationship(
        "StoryArc",
        secondary="story_arc_issues",
        back_populates="issues",
    )


class VariantCover(Base):
    __tablename__ = "variant_covers"

    id = Column(Integer, primary_key=True, index=True)

    # Link to issue
    issue_id = Column(Integer, ForeignKey("comic_issues.id", ondelete="CASCADE"), nullable=False, index=True)

    # Variant identification
    variant_type = Column(
        SQLEnum(VariantCoverType, name="variantcovertype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    variant_name = Column(String(255), nullable=True)  # e.g., "1:25 Variant", "Virgin Cover"
    cover_artist = Column(String(255), nullable=True)

    # Distribution information
    print_run = Column(String(100), nullable=True)  # e.g., "1st print", "2nd print", "1:50 ratio variant"
    retailer_exclusive = Column(String(255), nullable=True)  # e.g., "Midtown Comics Exclusive"
    production_notes = Column(Text, nullable=True)  # e.g., "Foil embossing", "Lenticular effect"

    # Cover image
    cover_image_url = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)

    # Metadata, server_default=func.now())

    # Relationships
    issue = relationship("ComicIssue", back_populates="variant_covers")


class ComicIssueCreator(Base):
    __tablename__ = "comic_issue_creators"
    __table_args__ = (
        UniqueConstraint("issue_id", "creator_name", "creator_role", name="unique_issue_creator_role"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Links
    issue_id = Column(Integer, ForeignKey("comic_issues.id", ondelete="CASCADE"), nullable=False, index=True)

    # Creator information
    creator_name = Column(String(255), nullable=False, index=True)
    creator_role = Column(String(100), nullable=False)  # e.g., "writer", "penciller", "inker", etc.

    # Display order for multiple creators
    display_order = Column(Integer, nullable=True)

    # Authority linking
    creator_authority_id = Column(String(255), nullable=True)  # e.g., VIAF or LCNAF ID
    creator_authority_source = Column(String(50), nullable=True)  # e.g., "viaf", "lcnaf"

    # Timestamps, server_default=func.now())

    # Relationships
    issue = relationship("ComicIssue", back_populates="creators")


class StoryArc(Base):
    __tablename__ = "story_arcs"
    __table_args__ = (
        UniqueConstraint("series_id", "arc_title", name="unique_series_arc"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Core arc information
    series_id = Column(Integer, ForeignKey("comic_series.id", ondelete="CASCADE"), nullable=False, index=True)
    arc_title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Arc scope and span
    is_crossover = Column(Boolean, default=False)  # Spans multiple series
    crossover_event_name = Column(String(500), nullable=True)  # For major events like "Infinite Crisis"
    related_series = Column(ARRAY(String), nullable=True)  # Other series involved

    # Issue range
    start_issue_number = Column(String(20), nullable=True)
    end_issue_number = Column(String(20), nullable=True)
    issue_count = Column(Integer, nullable=True)

    # Publication span
    start_publication_date = Column(DateTime(timezone=True), nullable=True)
    end_publication_date = Column(DateTime(timezone=True), nullable=True)

    # Sequence for complex multi-arc storylines
    sequence_number = Column(Integer, nullable=True)  # For ordering within series
    is_prequel = Column(Boolean, default=False)
    is_sequel = Column(Boolean, default=False)
    sequel_to_arc_id = Column(Integer, ForeignKey("story_arcs.id", ondelete="SET NULL"), nullable=True)

    # Themes and content
    themes = Column(ARRAY(String), nullable=True)  # e.g., ["time travel", "alternate universe"]
    characters_involved = Column(ARRAY(String), nullable=True)
    plot_summary = Column(Text, nullable=True)

    # Reader engagement
    recommended_reading_order = Column(Boolean, default=False)
    skip_notes = Column(Text, nullable=True)  # e.g., "Can skip if you've read X arc"
    contains_major_spoilers_for = Column(ARRAY(String), nullable=True)  # Arc titles

    # Timestamps, server_default=func.now())

    # Relationships
    series = relationship("ComicSeries", back_populates="story_arcs")
    issues = relationship(
        "ComicIssue",
        secondary="story_arc_issues",
        back_populates="story_arcs",
    )
    sequel_from = relationship(
        "StoryArc",
        remote_side=[id],
        foreign_keys=[sequel_to_arc_id],
        backref="sequels",
    )


# Association table for many-to-many relationship between StoryArc and ComicIssue
story_arc_issues = Table(
    "story_arc_issues",
    Base.metadata,
    Column("story_arc_id", Integer, ForeignKey("story_arcs.id", ondelete="CASCADE")),
    Column("issue_id", Integer, ForeignKey("comic_issues.id", ondelete="CASCADE")),
)


class ComicPublisherImprint(Base):
    __tablename__ = "comic_publisher_imprints"

    id = Column(Integer, primary_key=True, index=True)

    # Imprint information
    imprint_name = Column(String(255), nullable=False, index=True)
    parent_publisher = Column(String(255), nullable=False, index=True)  # e.g., "DC Comics"
    description = Column(Text, nullable=True)

    # Imprint characteristics
    target_audience = Column(String(100), nullable=True)  # e.g., "adult", "young_adult", "all_ages"
    founded_year = Column(Integer, nullable=True)

    # Metadata, server_default=func.now())


class ComicContentAdvisory(Base):
    __tablename__ = "comic_content_advisories"

    id = Column(Integer, primary_key=True, index=True)

    # Link to issue
    issue_id = Column(Integer, ForeignKey("comic_issues.id", ondelete="CASCADE"), nullable=False, index=True)

    # Warning details
    warning_type = Column(String(100), nullable=False)  # ComicContentWarning enum value
    severity = Column(String(20), nullable=True)  # "mild", "moderate", "severe"
    description = Column(Text, nullable=False)  # Detailed explanation for parents/readers

    # Context
    appears_in_pages = Column(String(100), nullable=True)  # e.g., "pages 15-17, 42-45"
    recurring = Column(Boolean, default=False)  # If content appears throughout

    # Metadata
    added_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    added_by = relationship("User")


class ReadingOrderEvent(Base):
    __tablename__ = "reading_order_events"

    id = Column(Integer, primary_key=True, index=True)

    # Event identification
    event_name = Column(String(500), nullable=False, index=True, unique=True)
    description = Column(Text, nullable=True)
    event_type = Column(String(100), nullable=True)  # "crossover", "event", "story_arc"

    # Scope
    primary_series = Column(ARRAY(String), nullable=True)  # Main series involved
    crossover_series = Column(ARRAY(String), nullable=True)  # Tie-in series
    total_issues = Column(Integer, nullable=True)

    # Chronology
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    # Metadata, server_default=func.now())


class ReadingOrderEventIssue(Base):
    __tablename__ = "reading_order_event_issues"
    __table_args__ = (
        UniqueConstraint("event_id", "sequence_number", name="unique_event_sequence"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Links
    event_id = Column(Integer, ForeignKey("reading_order_events.id", ondelete="CASCADE"), nullable=False, index=True)
    issue_id = Column(Integer, ForeignKey("comic_issues.id", ondelete="CASCADE"), nullable=False, index=True)

    # Sequence information
    sequence_number = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    is_essential = Column(Boolean, default=False)  # Critical to understanding event
    is_optional = Column(Boolean, default=False)  # Supplementary/tie-in material

    # Notes
    reading_notes = Column(Text, nullable=True)

    # Relationships
    issue = relationship("ComicIssue")
