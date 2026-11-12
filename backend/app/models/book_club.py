# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, Index
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class BookClubRole(StrEnum):
    admin = "admin"  # Can manage members and meetings
    facilitator = "facilitator"  # Can lead discussions
    member = "member"  # Regular member


class BookClubStatus(StrEnum):
    active = "active"
    inactive = "inactive"
    archived = "archived"


class DiscussionStatus(StrEnum):
    planned = "planned"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class BookClub(Base):

    __tablename__ = "book_clubs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    status = Column(
        SQLEnum(BookClubStatus, name="bookclubstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=BookClubStatus.active,
        nullable=False,
    )

    # Club settings
    max_members = Column(Integer, nullable=True)  # None = unlimited
    is_public = Column(Boolean, default=True, nullable=False)
    meeting_frequency = Column(String(100), nullable=True)  # e.g., "monthly", "weekly"
    genre = Column(String(64), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    members = relationship("BookClubMember", back_populates="book_club", cascade="all, delete-orphan")
    meetings = relationship("BookClubMeeting", back_populates="book_club", cascade="all, delete-orphan")
    kits = relationship("BookClubKit", back_populates="book_club", cascade="all, delete-orphan")
    waitlist_entries = relationship(
        "BookClubWaitlistEntry",
        back_populates="book_club",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_book_clubs_created_by", "created_by_id"),
        Index("ix_book_clubs_status", "status"),
    )


class BookClubMember(Base):

    __tablename__ = "book_club_members"

    id = Column(Integer, primary_key=True, index=True)
    book_club_id = Column(
        Integer, ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    role = Column(
        SQLEnum(BookClubRole, name="bookclubmemberrole", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=BookClubRole.member,
        nullable=False,
    )

    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    book_club = relationship("BookClub", back_populates="members")
    user = relationship("User")

    __table_args__ = (
        Index("ix_book_club_members_user", "user_id"),
        Index("ix_book_club_members_unique", "book_club_id", "user_id", unique=True),
    )


class BookClubMeeting(Base):

    __tablename__ = "book_club_meetings"

    id = Column(Integer, primary_key=True, index=True)
    book_club_id = Column(
        Integer, ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Book being discussed
    catalog_item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True
    )

    status = Column(
        SQLEnum(DiscussionStatus, name="discussionstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=DiscussionStatus.planned,
        nullable=False,
    )

    # Meeting details
    meeting_date = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    # Soft-archive: hides meeting + its discussions from default views while
    # preserving rows. Gated by the book_club_history_enabled feature flag.
    is_archived = Column(Boolean, nullable=False, default=False, server_default="false")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    book_club = relationship("BookClub", back_populates="meetings")
    catalog_item = relationship("CatalogItem")
    discussion_guide = relationship("DiscussionGuide", uselist=False, back_populates="meeting")
    discussions = relationship(
        "BookClubDiscussion",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_book_club_meetings_book_club", "book_club_id"),
        Index("ix_book_club_meetings_date", "meeting_date"),
        Index("ix_book_club_meetings_archived", "book_club_id", "is_archived"),
    )


class BookClubDiscussion(Base):

    __tablename__ = "book_club_discussions"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(
        Integer,
        ForeignKey("book_club_meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Cached author display so search snippets work even after a user is
    # deleted (user_id goes NULL). Populated at insert time from the
    # caller's preferred name.
    author_display_name = Column(String(255), nullable=False, default="")

    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    is_pinned = Column(Boolean, nullable=False, default=False, server_default="false")

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    meeting = relationship("BookClubMeeting", back_populates="discussions")
    author = relationship("User", foreign_keys=[user_id])

    # NOTE: ``search_vector`` is a Postgres ``tsvector`` column maintained
    # by the trigger created in the alembic migration. It is not declared
    # here on the SQLAlchemy model so init_db.py won't try to recreate it
    # (the trigger function would be lost). Queries reference it via raw
    # SQL ``column('search_vector')`` selectors.

    __table_args__ = (
        Index("ix_book_club_discussions_meeting", "meeting_id"),
        Index("ix_book_club_discussions_created_at", "created_at"),
    )


class DiscussionGuide(Base):

    __tablename__ = "discussion_guides"

    id = Column(Integer, primary_key=True, index=True)

    # Can be associated with a meeting or standalone
    book_club_meeting_id = Column(
        Integer, ForeignKey("book_club_meetings.id", ondelete="CASCADE"), nullable=True
    )

    catalog_item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)  # URL to PDF in storage
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(50), default="application/pdf", nullable=False)

    # Guide metadata
    author = Column(String(255), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_official = Column(Boolean, default=False, nullable=False)  # From publisher vs. community

    # Generated questions count
    auto_generated_questions_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    meeting = relationship("BookClubMeeting", back_populates="discussion_guide")
    catalog_item = relationship("CatalogItem")
    auto_questions = relationship("AutoGeneratedQuestion", back_populates="discussion_guide", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_discussion_guides_catalog_item", "catalog_item_id"),
        Index("ix_discussion_guides_meeting", "book_club_meeting_id"),
    )


class AutoGeneratedQuestion(Base):

    __tablename__ = "auto_generated_questions"

    id = Column(Integer, primary_key=True, index=True)
    discussion_guide_id = Column(
        Integer, ForeignKey("discussion_guides.id", ondelete="CASCADE"), nullable=False, index=True
    )

    question = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=True)  # e.g., "comprehension", "analysis", "personal_reflection"
    sort_order = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    discussion_guide = relationship("DiscussionGuide", back_populates="auto_questions")


class BookClubKit(Base):

    __tablename__ = "book_club_kits"

    id = Column(Integer, primary_key=True, index=True)
    book_club_id = Column(
        Integer, ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Kit composition (stored as JSON or via relationship)
    total_copies = Column(Integer, default=10, nullable=False)  # Standard kit size

    # Availability
    available_copies = Column(Integer, nullable=False)  # Dynamically updated

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    book_club = relationship("BookClub", back_populates="kits")
    items = relationship("KitContents", back_populates="kit", cascade="all, delete-orphan")
    checkouts = relationship("KitCheckout", back_populates="kit", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_book_club_kits_book_club", "book_club_id"),
    )


class KitContents(Base):

    __tablename__ = "kit_contents"

    id = Column(Integer, primary_key=True, index=True)
    kit_id = Column(
        Integer, ForeignKey("book_club_kits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    catalog_item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False
    )

    quantity = Column(Integer, default=1, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    # Relationships
    kit = relationship("BookClubKit", back_populates="items")
    catalog_item = relationship("CatalogItem")

    __table_args__ = (
        Index("ix_kit_contents_catalog_item", "catalog_item_id"),
    )


class KitCheckout(Base):

    __tablename__ = "kit_checkouts"

    id = Column(Integer, primary_key=True, index=True)
    kit_id = Column(
        Integer, ForeignKey("book_club_kits.id", ondelete="CASCADE"), nullable=False, index=True
    )

    book_club_id = Column(
        Integer, ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False
    )

    # Primary contact for the checkout
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    status = Column(
        String(50), default="active", nullable=False
    )  # active, returned, overdue, lost

    checked_out_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    returned_at = Column(DateTime(timezone=True), nullable=True)

    # Tracking individual item returns within kit
    all_items_returned = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    kit = relationship("BookClubKit", back_populates="checkouts")
    book_club = relationship("BookClub")
    user = relationship("User")

    __table_args__ = (
        Index("ix_kit_checkouts_kit", "kit_id"),
        Index("ix_kit_checkouts_status", "status"),
        Index("ix_kit_checkouts_due_date", "due_date"),
    )


class PopularBookClubPick(Base):

    __tablename__ = "popular_book_club_picks"

    id = Column(Integer, primary_key=True, index=True)
    catalog_item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Pick metrics
    total_discussions = Column(Integer, default=0, nullable=False)
    total_kits = Column(Integer, default=0, nullable=False)
    average_rating = Column(Integer, nullable=True)  # 1-5 stars

    # Featured/promoted
    is_featured = Column(Boolean, default=False, nullable=False)
    featured_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    first_discussed_at = Column(DateTime(timezone=True), nullable=True)
    last_discussed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    catalog_item = relationship("CatalogItem")

    __table_args__ = (
        Index("ix_popular_picks_featured", "is_featured"),
        Index("ix_popular_picks_discussions", "total_discussions"),
    )


class GroupHold(Base):

    __tablename__ = "group_holds"

    id = Column(Integer, primary_key=True, index=True)
    book_club_id = Column(
        Integer, ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kit_id = Column(
        Integer, ForeignKey("book_club_kits.id", ondelete="CASCADE"), nullable=False, index=True
    )

    requested_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    status = Column(
        String(50), default="pending", nullable=False
    )  # pending, ready, fulfilled, cancelled

    position_in_queue = Column(Integer, nullable=False)  # For multiple groups

    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ready_at = Column(DateTime(timezone=True), nullable=True)
    fulfilled_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    book_club = relationship("BookClub")
    kit = relationship("BookClubKit")
    requested_by = relationship("User")

    __table_args__ = (
        Index("ix_group_holds_book_club", "book_club_id"),
        Index("ix_group_holds_status", "status"),
        Index("ix_group_holds_position", "kit_id", "position_in_queue"),
    )


class BookClubMemberImport(Base):

    __tablename__ = "book_club_member_imports"

    # UUID primary key generated server-side via gen_random_uuid().
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )

    book_club_id = Column(
        Integer,
        ForeignKey("book_clubs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # imported_by_id is SET NULL on user delete so the audit row outlives the
    # staff user account.
    imported_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    imported_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    row_count = Column(Integer, nullable=False)
    success_count = Column(Integer, nullable=False)
    skipped_count = Column(Integer, nullable=False)
    error_count = Column(Integer, nullable=False)

    # JSONB on Postgres; SQLAlchemy maps via dialect-agnostic JSON type below.
    raw_outcome = Column(JSONB, nullable=False)

    # Relationships (lazy by default — endpoint never returns ORM objects).
    book_club = relationship("BookClub")
    imported_by = relationship("User")

    __table_args__ = (
        Index("ix_book_club_member_imports_club", "book_club_id"),
        Index("ix_book_club_member_imports_at", "imported_at"),
    )


class BookClubWaitlistEntry(Base):

    __tablename__ = "book_club_waitlist_entries"

    id = Column(Integer, primary_key=True, index=True)
    book_club_id = Column(
        Integer,
        ForeignKey("book_clubs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notified_at = Column(DateTime(timezone=True), nullable=True)

    book_club = relationship("BookClub", back_populates="waitlist_entries")
    user = relationship("User", lazy="raise")

    __table_args__ = (
        UniqueConstraint(
            "book_club_id", "user_id", name="uq_waitlist_club_user"
        ),
        Index(
            "ix_book_club_waitlist_entries_club_created",
            "book_club_id",
            "created_at",
        ),
    )
