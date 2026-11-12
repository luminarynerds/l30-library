# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
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


# ============================================================================
# Enums
# ============================================================================


class PublisherType(StrEnum):
    publisher = "publisher"           # Main publisher
    imprint = "imprint"              # Sub-label/imprint of a publisher
    independent = "independent"      # Self-published or independent


class PublisherRegion(StrEnum):
    north_america = "north_america"
    europe = "europe"
    asia = "asia"
    japan = "japan"
    latin_america = "latin_america"
    australia_oceania = "australia_oceania"
    world = "world"


class OutOfPrintStatus(StrEnum):
    in_print = "in_print"
    limited_availability = "limited_availability"
    out_of_print = "out_of_print"
    out_of_print_pending = "out_of_print_pending"
    reprinting = "reprinting"


class ContentRatingSystem(StrEnum):
    teen = "teen"                   # All ages (Shonen)
    young_adult = "young_adult"     # Young adult (Shojo)
    mature = "mature"               # Mature (Seinen)
    explicit = "explicit"           # Explicit (Hentai)


# ============================================================================
# Core Publisher Models
# ============================================================================


class Publisher(Base):
    __tablename__ = "publishers"

    id = Column(Integer, primary_key=True, index=True)

    # Identity
    name = Column(String(500), nullable=False, unique=True, index=True)
    name_sort = Column(String(500), nullable=True)  # Sortable form
    display_name = Column(String(500), nullable=True)  # How to display to patrons

    # Publisher info
    publisher_type = Column(
        SQLEnum(PublisherType, name="publishertype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PublisherType.publisher,
        nullable=False,
    )

    # Parent imprint relationship
    parent_publisher_id = Column(
        Integer,
        ForeignKey("publishers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Description and notes
    description = Column(Text, nullable=True)
    history = Column(Text, nullable=True)  # Publisher history/background

    # Contact and location info
    headquarters_location = Column(String(500), nullable=True)
    primary_region = Column(
        SQLEnum(PublisherRegion, name="publisherregion", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PublisherRegion.north_america,
        nullable=True,
    )
    regions_served = Column(Text, nullable=True)  # JSON array of PublisherRegion

    # Digital presence
    website_url = Column(String(1000), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    social_media = Column(JSONB, nullable=True)  # {twitter, instagram, facebook, etc.}

    # Content rating info (publisher-specific)
    default_rating_system = Column(
        SQLEnum(ContentRatingSystem, name="contentratingsystem", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    content_ratings_info = Column(Text, nullable=True)  # Description of rating scale

    # Authority identifiers
    viaf_id = Column(String(50), nullable=True)
    wikidata_id = Column(String(20), nullable=True)
    isni = Column(String(20), nullable=True)

    # Administrative
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps, server_default=func.now())

    # Relationships
    imprints = relationship(
        "Publisher",
        foreign_keys=[parent_publisher_id],
        back_populates="parent_publisher",
        cascade="all, delete-orphan"
    )
    parent_publisher = relationship(
        "Publisher",
        foreign_keys=[parent_publisher_id],
        remote_side=[id],
        back_populates="imprints"
    )
    magazines = relationship(
        "MangaMagazine",
        back_populates="publisher",
        cascade="all, delete-orphan"
    )
    series = relationship(
        "PublisherSeries",
        back_populates="publisher",
        cascade="all, delete-orphan"
    )

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("name", name="uq_publisher_name"),
        Index("ix_publishers_type_active", "publisher_type", "is_active"),
        Index("ix_publishers_parent", "parent_publisher_id"),
        Index("ix_publishers_region", "primary_region"),
    )

    def __repr__(self):
        return f"<Publisher(id={self.id}, name='{self.name}')>"


class MangaMagazine(Base):
    __tablename__ = "manga_magazines"

    id = Column(Integer, primary_key=True, index=True)

    # Identity
    name = Column(String(500), nullable=False, unique=True, index=True)
    english_name = Column(String(500), nullable=True)
    original_language = Column(String(10), default="ja", nullable=False)  # ISO 639-2 code

    # Publisher relationship
    publisher_id = Column(
        Integer,
        ForeignKey("publishers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Publication details
    publication_frequency = Column(String(100), nullable=True)  # e.g., "Weekly"
    first_published = Column(Integer, nullable=True)  # Year
    last_published = Column(Integer, nullable=True)  # Year (NULL if ongoing)
    is_ongoing = Column(Boolean, default=True, nullable=False)

    # Description
    description = Column(Text, nullable=True)
    target_demographic = Column(String(100), nullable=True)  # e.g., "Shonen", "Shojo"

    # Authority info
    issn = Column(String(10), nullable=True)
    wikidata_id = Column(String(20), nullable=True)

    # Timestamps, server_default=func.now())

    # Relationships
    publisher = relationship("Publisher", back_populates="magazines")
    serializations = relationship(
        "MangaSerialization",
        back_populates="magazine",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("name", name="uq_magazine_name"),
        Index("ix_magazines_publisher", "publisher_id"),
        Index("ix_magazines_ongoing", "is_ongoing"),
    )

    def __repr__(self):
        return f"<MangaMagazine(id={self.id}, name='{self.name}')>"


class MangaSerialization(Base):
    __tablename__ = "manga_serializations"

    id = Column(Integer, primary_key=True, index=True)

    # Work being serialized
    bibframe_work_id = Column(
        Integer,
        ForeignKey("bibframe_works.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Magazine details
    magazine_id = Column(
        Integer,
        ForeignKey("manga_magazines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Serialization period
    start_date = Column(String(50), nullable=True)  # Flexible date (e.g., "2019", "2019-01")
    end_date = Column(String(50), nullable=True)    # NULL if ongoing
    is_ongoing = Column(Boolean, default=False, nullable=False)

    # Chapter info
    start_chapter = Column(String(50), nullable=True)  # e.g., "1", "Prologue"
    end_chapter = Column(String(50), nullable=True)

    # Additional notes
    notes = Column(Text, nullable=True)

    # Timestamps, server_default=func.now())

    # Relationships
    work = relationship("BibframeWork")
    magazine = relationship("MangaMagazine", back_populates="serializations")

    __table_args__ = (
        UniqueConstraint("bibframe_work_id", "magazine_id", name="uq_serialization"),
        Index("ix_serializations_work", "bibframe_work_id"),
        Index("ix_serializations_magazine", "magazine_id"),
    )

    def __repr__(self):
        return f"<MangaSerialization(work_id={self.bibframe_work_id}, magazine_id={self.magazine_id})>"


class PublisherSeries(Base):
    __tablename__ = "publisher_series"

    id = Column(Integer, primary_key=True, index=True)

    # Publisher/Imprint
    publisher_id = Column(
        Integer,
        ForeignKey("publishers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Series info
    series_title = Column(String(500), nullable=False, index=True)
    series_description = Column(Text, nullable=True)

    # Publisher-specific metadata
    publisher_series_number = Column(String(100), nullable=True)  # Internal series code
    is_featured = Column(Boolean, default=False, nullable=False)

    # Statistics
    total_published_books = Column(Integer, nullable=True)
    books_in_library = Column(Integer, default=0, nullable=False)

    # Timestamps, server_default=func.now())

    # Relationships
    publisher = relationship("Publisher", back_populates="series")

    __table_args__ = (
        UniqueConstraint("publisher_id", "series_title", name="uq_publisher_series"),
        Index("ix_publisher_series_publisher", "publisher_id"),
        Index("ix_publisher_series_title", "series_title"),
    )

    def __repr__(self):
        return f"<PublisherSeries(publisher_id={self.publisher_id}, series='{self.series_title}')>"


# ============================================================================
# Work and Instance Extensions
# ============================================================================
# These fields will be added to existing models via migration


class MangaMetadata(Base):
    __tablename__ = "manga_metadata"

    id = Column(Integer, primary_key=True, index=True)

    # Link to BIBFRAME Work
    bibframe_work_id = Column(
        Integer,
        ForeignKey("bibframe_works.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Original Japanese info
    original_japanese_title = Column(String(1000), nullable=True)
    romaji_title = Column(String(1000), nullable=True)

    # Translation info
    translator_name = Column(String(500), nullable=True)
    translator_notes = Column(Text, nullable=True)
    original_publication_country = Column(String(2), default="JP", nullable=False)  # ISO 3166-1 alpha-2

    # Format/Structure
    is_volume_collection = Column(Boolean, default=True, nullable=False)  # vs. single chapter
    volume_number = Column(Integer, nullable=True)
    total_chapters_in_work = Column(Integer, nullable=True)
    chapter_range = Column(String(100), nullable=True)  # e.g., "chapters 1-20"

    # Reading direction
    reading_direction = Column(String(20), default="right-to-left", nullable=False)  # RTL or LTR

    # Localization dates
    original_publication_date = Column(String(50), nullable=True)  # Original JP date
    english_publication_date = Column(String(50), nullable=True)  # English date

    # Timestamps, server_default=func.now())

    # Relationships
    work = relationship("BibframeWork")

    __table_args__ = (
        UniqueConstraint("bibframe_work_id", name="uq_manga_metadata_work"),
    )

    def __repr__(self):
        return f"<MangaMetadata(work_id={self.bibframe_work_id})>"
