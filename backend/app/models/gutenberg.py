# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from ..core.database import Base


class GutenbergFormat(PyEnum):
    EPUB = "epub"
    KINDLE = "kindle"
    HTML = "html"
    PLAIN_TEXT = "plain_text"
    PDF = "pdf"


class GutenbergBookshelf(PyEnum):
    FICTION = "fiction"
    SCIENCE_FICTION = "science fiction"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    ADVENTURE = "adventure"
    HISTORICAL_FICTION = "historical fiction"
    CHILDREN = "children's literature"
    POETRY = "poetry"
    DRAMA = "drama"
    PHILOSOPHY = "philosophy"
    HISTORY = "history"
    SCIENCE = "science"
    BIOGRAPHY = "biography"
    REFERENCE = "reference"
    OTHER = "other"


class GutenbergBook(Base):
    __tablename__ = "gutenberg_books"

    id = Column(Integer, primary_key=True, index=True)

    # Gutenberg identifiers
    gutenberg_id = Column(Integer, unique=True, nullable=False, index=True)

    # Core metadata
    title = Column(String(1000), nullable=False)

    # Authors stored as JSON string: [{"name": "Austen, Jane", "birth_year": 1775, "death_year": 1817}]
    authors = Column(Text, nullable=True)

    # Subjects and bookshelves stored as JSON arrays
    subjects = Column(Text, nullable=True)  # ["Fiction", "Love stories"]
    bookshelves = Column(Text, nullable=True)  # ["Best Books Ever Listings"]

    # Language (ISO 639-1 codes)
    languages = Column(String(100), nullable=True)  # e.g., "en", "en,fr"

    # Availability info
    copyright_status = Column(Boolean, default=False, nullable=False)  # False = public domain
    media_type = Column(String(50), default="Text", nullable=False)

    # Download formats stored as JSON: {"epub": "url", "kindle": "url", ...}
    formats = Column(Text, nullable=True)

    # Cover image URL
    cover_url = Column(String(1000), nullable=True)

    # Popularity metric from Gutenberg
    download_count = Column(Integer, default=0, nullable=False)

    # Link to local catalog (optional)
    catalog_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)

    # Sync tracking
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    catalog_item = relationship("CatalogItem", backref="gutenberg_books")
    downloads = relationship("GutenbergDownload", back_populates="book", cascade="all, delete-orphan")
    favorites = relationship("GutenbergFavorite", back_populates="book", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_gutenberg_books_title_author", "title"),
        Index("ix_gutenberg_books_download_count", "download_count"),
        Index("ix_gutenberg_books_catalog", "catalog_item_id"),
    )


class GutenbergDownload(Base):
    __tablename__ = "gutenberg_downloads"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("gutenberg_books.id", ondelete="CASCADE"), nullable=False)

    # Format that was downloaded
    format = Column(Enum(GutenbergFormat, values_callable=lambda x: [m.value for m in x]), nullable=False)

    # Timestamp
    downloaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="gutenberg_downloads")
    book = relationship("GutenbergBook", back_populates="downloads")

    __table_args__ = (
        Index("ix_gutenberg_downloads_user", "user_id", "downloaded_at"),
        Index("ix_gutenberg_downloads_book", "book_id"),
    )


class GutenbergFavorite(Base):
    __tablename__ = "gutenberg_favorites"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("gutenberg_books.id", ondelete="CASCADE"), nullable=False)

    # Optional notes
    notes = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="gutenberg_favorites")
    book = relationship("GutenbergBook", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_gutenberg_favorite"),
        Index("ix_gutenberg_favorites_user", "user_id"),
    )


class GutenbergSyncStatus(Base):
    __tablename__ = "gutenberg_sync_status"

    id = Column(Integer, primary_key=True, index=True)

    # Sync status
    last_full_sync_at = Column(DateTime, nullable=True)
    last_incremental_sync_at = Column(DateTime, nullable=True)

    # Progress tracking
    total_books_synced = Column(Integer, default=0, nullable=False)
    last_synced_page = Column(Integer, default=0, nullable=False)

    # Status
    is_syncing = Column(Boolean, default=False, nullable=False)
    sync_started_at = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
