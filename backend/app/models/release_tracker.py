# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (ForeignKey, Integer, Numeric, String, Text,
                        UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AgeRating(StrEnum):

    ADULT = "adult"
    TEEN = "teen"
    CHILD = "child"


class ReleaseStatus(StrEnum):

    UPCOMING = "upcoming"
    RELEASED = "released"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class ReleaseSource(StrEnum):

    AUTHOR_SCAN = "author_scan"
    LIBRARYREADS = "libraryreads"
    LJ_PREPUB = "lj_prepub"
    EDITORIAL_RSS = "editorial_rss"
    INDIE_MASTODON = "indie_mastodon"
    INDIE_ITCHIO = "indie_itchio"


class ProfileType(StrEnum):

    PARENT = "parent"
    CHILD = "child"


class TrackerAuthor(Base):

    __tablename__ = "tracker_authors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    google_id = Column(String(100), index=True)
    open_library_id = Column(String(100), index=True)
    bio = Column(Text)
    image_url = Column(Text)

    # Tracking metadata
    last_scanned_at = Column(DateTime(timezone=True))
    scan_frequency_days = Column(Integer, default=7)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    books = relationship(
        "TrackerBook", back_populates="author", cascade="all, delete-orphan"
    )
    followers = relationship(
        "UserFollow", back_populates="author", cascade="all, delete-orphan"
    )

    @property
    def follower_count(self) -> int:
        return len(self.followers) if self.followers else 0

    @property
    def book_count(self) -> int:
        return len(self.books) if self.books else 0


class TrackerBook(Base):

    __tablename__ = "tracker_books"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tracker_authors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Book details
    title = Column(String(500), nullable=False)
    normalized_title = Column(String(500), index=True)  # lowercase for deduplication
    subtitle = Column(String(500))
    description = Column(Text)

    # Release info
    release_date = Column(Date, index=True)
    is_date_exact = Column(Boolean, default=True)
    status = Column(
        String(50),
        default=ReleaseStatus.UPCOMING,
        nullable=False,
        index=True,
    )

    # Identifiers
    isbn_13 = Column(String(13), index=True)  # NOT unique - multiple editions possible
    isbn_10 = Column(String(10))
    google_books_id = Column(String(100))
    open_library_key = Column(String(100))

    # Metadata
    age_rating = Column(
        String(50),
        default=AgeRating.ADULT,
    )
    raw_categories = Column(JSONB, server_default="[]")
    publisher = Column(String(255))
    page_count = Column(Integer)
    language = Column(String(10), default="en")

    # Out-of-print status for tracked releases
    out_of_print_status = Column(String(50), nullable=True, default="in_print")  # in_print, out_of_print, reprinting
    out_of_print_date = Column(String(50), nullable=True)

    # Pricing
    list_price = Column(Numeric(10, 2))
    currency = Column(String(3), default="USD")

    # Media
    cover_url = Column(Text)
    thumbnail_url = Column(Text)

    # Editorial provenance (pre-pub source connectors)
    source = Column(
        String(30),
        default=ReleaseSource.AUTHOR_SCAN.value,
        server_default=ReleaseSource.AUTHOR_SCAN.value,
        nullable=False,
        index=True,
    )
    source_url = Column(Text)
    blurb = Column(Text)
    blurb_credit = Column(String(255))
    is_featured = Column(
        Boolean, default=False, server_default="false", nullable=False, index=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    author = relationship("TrackerAuthor", back_populates="books")

    @property
    def author_name(self) -> str | None:
        return self.author.name if self.author else None

    def set_normalized_title(self):
        if self.title:
            self.normalized_title = self.title.lower().strip()


class UserFollow(Base):

    __tablename__ = "user_follows"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tracker_authors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Profile type for filtering (parent sees all, child filtered)
    profile_type = Column(
        String(50),
        default=ProfileType.PARENT,
    )

    # Notification preferences
    notify_on_release = Column(Boolean, default=True)
    notify_days_before = Column(Integer, default=7)  # Days before release to notify

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    author = relationship("TrackerAuthor", back_populates="followers")

    __table_args__ = (
        UniqueConstraint("user_id", "author_id", name="uq_user_author_follow"),
    )


class ProcessedRssPost(Base):

    __tablename__ = "processed_rss_posts"

    id = Column(Integer, primary_key=True)
    url = Column(String(1000), nullable=False, unique=True, index=True)
    outlet = Column(String(40), nullable=False)
    processed_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
