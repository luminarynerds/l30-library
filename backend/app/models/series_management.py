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
from app.models.mixins import TimestampMixin

from ..core.database import Base


# ============================================================================
# Enums
# ============================================================================


class SeriesType(StrEnum):
    main_series = "main_series"  # Primary book series
    subseries = "subseries"      # Part of a larger series
    spin_off = "spin_off"        # Spin-off from main series
    anthology = "anthology"      # Collection of stories
    graphic_novel_series = "graphic_novel_series"


class NotificationTrigger(StrEnum):
    new_release = "new_release"           # New book in series arrives
    next_available = "next_available"     # Next unread book in series available
    series_complete = "series_complete"   # All books in series available
    popular_series = "popular_series"     # Popular series update
    custom_date = "custom_date"           # Custom date-based trigger


class WaitlistStatus(StrEnum):
    active = "waiting"          # Waiting for book (PG enum label is "waiting")
    notified = "notified"       # Notified, waiting for patron action
    fulfilled = "fulfilled"     # Patron obtained book
    cancelled = "cancelled"     # Patron cancelled
    expired = "expired"         # Expired (book never released)


class RecommendationReason(StrEnum):
    similar_genre = "similar_genre"           # Similar genre to books read
    same_author = "same_author"               # Same author
    same_series = "same_series"               # Same series
    related_series = "related_series"         # Related/linked series
    reading_history = "reading_history"       # Based on reading history
    popularity = "popularity"                 # Popular among similar readers
    editorial = "editorial"                   # Staff recommendation
    user_followed = "user_followed"           # User explicitly follows series


# ============================================================================
# Core Series Management Models
# ============================================================================


class SeriesReadingOrder(Base):
    __tablename__ = "series_reading_order"

    id = Column(Integer, primary_key=True, index=True)

    # Series identification
    series_title = Column(String(500), nullable=False, index=True)
    series_type = Column(
        SQLEnum(SeriesType, name="seriestype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=SeriesType.main_series,
        nullable=False
    )

    # Book in series (from BIBFRAME work)
    bibframe_work_id = Column(
        Integer,
        ForeignKey("bibframe_works.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Sequence information
    sequence_number = Column(Float, nullable=False)  # 1.0, 1.5, 2.0 (allows for prequels)
    book_title = Column(String(1000), nullable=False)
    publication_year = Column(Integer, nullable=True)
    alternate_titles = Column(Text, nullable=True)  # JSON array of alternate titles

    # Reading recommendation
    is_recommended_starting_point = Column(Boolean, default=False)
    skip_note = Column(Text, nullable=True)  # Notes about skipping this book
    contains_spoilers_for = Column(Text, nullable=True)  # JSON array of book IDs

    # Parent series relationship (for subseries)
    parent_series_id = Column(Integer, ForeignKey("series_reading_order.id", ondelete="SET NULL"), nullable=True)

    # Administrative
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified = Column(Boolean, default=False)  # Verified by librarian
    verified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps, server_default=func.now())

    # Relationships
    work = relationship("BibframeWork")
    subseries = relationship("SeriesReadingOrder", remote_side=[id])

    __table_args__ = (
        UniqueConstraint("series_title", "sequence_number", name="uq_series_sequence"),
        Index("ix_series_reading_order_title_seq", "series_title", "sequence_number"),
        Index("ix_series_reading_order_parent", "parent_series_id"),
    )


class PatronReadingHistory(Base):
    __tablename__ = "patron_reading_history"

    id = Column(Integer, primary_key=True, index=True)

    # Patron and book identification
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    bibframe_work_id = Column(
        Integer,
        ForeignKey("bibframe_works.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Reading tracking
    started_date = Column(DateTime(timezone=True), nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    is_completed = Column(Boolean, default=False, nullable=False)

    # Reading engagement
    rating = Column(Float, nullable=True)  # 0.0-5.0
    review = Column(Text, nullable=True)
    favorite = Column(Boolean, default=False)
    did_not_finish = Column(Boolean, default=False)

    # Context
    format_read = Column(String(50), nullable=True)  # print, ebook, audiobook
    source = Column(String(100), nullable=True)  # library, purchased, borrowed

    # Timestamps, server_default=func.now())

    # Relationships
    user = relationship("User")
    work = relationship("BibframeWork")

    __table_args__ = (
        UniqueConstraint("user_id", "bibframe_work_id", name="uq_patron_work_history"),
        Index("ix_reading_history_user_completed", "user_id", "is_completed"),
        Index("ix_reading_history_completed_date", "completed_date"),
    )


class SeriesCompletion(Base):
    __tablename__ = "series_completion"

    id = Column(Integer, primary_key=True, index=True)

    # Patron and series identification
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    series_title = Column(String(500), nullable=False, index=True)

    # Completion tracking
    total_books_in_series = Column(Integer, nullable=True)
    books_read = Column(Integer, default=0, nullable=False)
    books_available = Column(Integer, default=0, nullable=False)

    # Progress details
    last_book_read_number = Column(Float, nullable=True)  # Sequence number of last read
    next_book_number = Column(Float, nullable=True)      # Sequence number of next to read
    last_book_read_title = Column(String(1000), nullable=True)
    next_book_title = Column(String(1000), nullable=True)

    # Status
    is_completed = Column(Boolean, default=False, nullable=False)
    is_following = Column(Boolean, default=False, nullable=False)  # Following series updates

    # Engagement
    preferred = Column(Boolean, default=False, nullable=False)  # Patron's preferred series
    last_read_date = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    started_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_date = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("user_id", "series_title", name="uq_patron_series_completion"),
        Index("ix_series_completion_user_following", "user_id", "is_following"),
        Index("ix_series_completion_user_preferred", "user_id", "preferred"),
    )


class SeriesWaitlist(Base):
    __tablename__ = "series_waitlist"

    id = Column(Integer, primary_key=True, index=True)

    # Patron and series identification
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    series_title = Column(String(500), nullable=False, index=True)

    # What they're waiting for
    next_book_sequence = Column(Float, nullable=True)  # Sequence of next expected book
    next_book_title = Column(String(1000), nullable=True)
    expected_publication_date = Column(DateTime(timezone=True), nullable=True)

    # Waitlist status
    status = Column(
        SQLEnum(WaitlistStatus, name="waitliststatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=WaitlistStatus.active,
        nullable=False
    )

    # Notification tracking
    position = Column(Integer, default=1, nullable=False)
    notified_at = Column(DateTime(timezone=True), nullable=True)
    notification_method = Column(String(50), nullable=True)  # email, sms, both
    reminder_frequency = Column(String(50), default="weekly", nullable=False)
    last_reminder_sent = Column(DateTime(timezone=True), nullable=True)

    # Resolution
    fulfilled_date = Column(DateTime(timezone=True), nullable=True)
    fulfilled_by_bibframe_work_id = Column(
        Integer,
        ForeignKey("bibframe_works.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps, server_default=func.now())

    # Relationships
    user = relationship("User")
    fulfilled_by_work = relationship("BibframeWork")

    __table_args__ = (
        Index("ix_series_waitlist_user_status", "user_id", "status"),
        Index("ix_series_waitlist_series_status", "series_title", "status"),
        Index("ix_series_waitlist_active", "status"),
    )


class SeriesRecommendation(Base, TimestampMixin):
    __tablename__ = "series_recommendations"

    id = Column(Integer, primary_key=True, index=True)

    # Patron identification
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Recommended series
    series_title = Column(String(500), nullable=False, index=True)
    first_book_bibframe_work_id = Column(
        Integer,
        ForeignKey("bibframe_works.id", ondelete="SET NULL"),
        nullable=True
    )
    series_description = Column(Text, nullable=True)

    # Recommendation metadata
    reason = Column(
        SQLEnum(RecommendationReason, name="recommendationreason", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    confidence_score = Column(Float, default=0.5, nullable=False)  # 0.0-1.0
    related_books_or_series = Column(Text, nullable=True)  # JSON array

    # Engagement tracking
    viewed = Column(Boolean, default=False, nullable=False)
    viewed_at = Column(DateTime(timezone=True), nullable=True)
    clicked = Column(Boolean, default=False, nullable=False)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    added_to_wishlist = Column(Boolean, default=False, nullable=False)
    started_series = Column(Boolean, default=False, nullable=False)

    # Timestamps provided by TimestampMixin (created_at, updated_at)

    # Relationships
    user = relationship("User")
    first_book = relationship("BibframeWork")

    __table_args__ = (
        Index("ix_recommendations_user_created", "user_id", "created_at"),
        Index("ix_recommendations_reason", "reason"),
        Index("ix_recommendations_confidence", "confidence_score"),
    )


class SeriesNotificationRule(Base):
    __tablename__ = "series_notification_rules"

    id = Column(Integer, primary_key=True, index=True)

    # User and series
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    series_title = Column(String(500), nullable=False, index=True)

    # Notification trigger
    trigger_type = Column(
        SQLEnum(NotificationTrigger, name="notificationtrigger", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    trigger_metadata = Column(JSONB, nullable=True)  # Additional trigger details

    # Notification preferences
    is_active = Column(Boolean, default=True, nullable=False)
    notification_method = Column(String(50), default="email", nullable=False)  # email, sms, both
    frequency = Column(String(50), default="immediate", nullable=False)  # immediate, daily, weekly, monthly

    # Delivery tracking
    last_notification_sent = Column(DateTime(timezone=True), nullable=True)
    notification_count = Column(Integer, default=0, nullable=False)

    # Administrative
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps, server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        UniqueConstraint("user_id", "series_title", "trigger_type", name="uq_notification_rule"),
        Index("ix_notification_rules_active", "is_active"),
        Index("ix_notification_rules_user_active", "user_id", "is_active"),
    )


class SeriesPopularity(Base):
    __tablename__ = "series_popularity"

    id = Column(Integer, primary_key=True, index=True)

    # Series identification
    series_title = Column(String(500), nullable=False, unique=True, index=True)

    # Popularity metrics
    patron_followers = Column(Integer, default=0, nullable=False)
    patron_completion_count = Column(Integer, default=0, nullable=False)
    average_rating = Column(Float, nullable=True)
    total_checkouts = Column(Integer, default=0, nullable=False)
    unique_patrons_read = Column(Integer, default=0, nullable=False)

    # Trending
    is_trending = Column(Boolean, default=False, nullable=False)
    trend_score = Column(Float, nullable=True)  # Calculated trend metric

    # Timestamps
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_series_popularity_followers", "patron_followers"),
        Index("ix_series_popularity_trending", "is_trending"),
        Index("ix_series_popularity_rating", "average_rating"),
    )
