# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

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
    func,
)
from sqlalchemy.orm import relationship

from ..core.database import Base


class OpenLibraryBook(Base):
    __tablename__ = "open_library_books"

    id = Column(Integer, primary_key=True, index=True)

    # Open Library identifiers
    ol_work_id = Column(String(50), unique=True, nullable=False, index=True)  # e.g. "OL45804W"
    ol_edition_id = Column(String(50), nullable=True, index=True)  # e.g. "OL7353617M"

    # Core metadata
    title = Column(String(1000), nullable=False)

    # Authors stored as JSON string: [{"name": "Jane Austen", "ol_id": "OL21594A"}]
    authors = Column(Text, nullable=True)

    # Subjects stored as JSON array
    subjects = Column(Text, nullable=True)

    # Language (ISO 639-1 codes)
    languages = Column(String(100), nullable=True)

    # Publication info
    first_publish_year = Column(Integer, nullable=True)
    publisher = Column(String(500), nullable=True)
    isbn_13 = Column(String(20), nullable=True)
    isbn_10 = Column(String(15), nullable=True)

    # Availability
    has_fulltext = Column(Boolean, default=False, nullable=False)
    public_scan = Column(Boolean, default=False, nullable=False)

    # Cover image (Open Library cover ID)
    cover_id = Column(Integer, nullable=True)
    cover_url = Column(String(1000), nullable=True)

    # Reading formats available as JSON: {"read_url": "...", "borrow_url": "..."}
    availability = Column(Text, nullable=True)

    # Popularity
    edition_count = Column(Integer, default=0, nullable=False)

    # Link to local catalog (optional)
    catalog_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)

    # Sync tracking
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    catalog_item = relationship("CatalogItem", backref="open_library_books")
    downloads = relationship("OpenLibraryDownload", back_populates="book", cascade="all, delete-orphan")
    favorites = relationship("OpenLibraryFavorite", back_populates="book", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_open_library_books_title", "title"),
        Index("ix_open_library_books_edition_count", "edition_count"),
        Index("ix_open_library_books_catalog", "catalog_item_id"),
    )


class OpenLibraryDownload(Base):
    __tablename__ = "open_library_downloads"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("open_library_books.id", ondelete="CASCADE"), nullable=False)

    # How the patron accessed the book
    access_type = Column(String(50), default="read_online", nullable=False)  # read_online, borrow, download

    # Timestamp
    accessed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="open_library_downloads")
    book = relationship("OpenLibraryBook", back_populates="downloads")

    __table_args__ = (
        Index("ix_open_library_downloads_user", "user_id", "accessed_at"),
        Index("ix_open_library_downloads_book", "book_id"),
    )


class OpenLibraryFavorite(Base):
    __tablename__ = "open_library_favorites"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("open_library_books.id", ondelete="CASCADE"), nullable=False)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="open_library_favorites")
    book = relationship("OpenLibraryBook", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_open_library_favorite"),
        Index("ix_open_library_favorites_user", "user_id"),
    )


class OpenLibrarySyncStatus(Base):
    __tablename__ = "open_library_sync_status"

    id = Column(Integer, primary_key=True, index=True)

    last_full_sync_at = Column(DateTime, nullable=True)
    last_incremental_sync_at = Column(DateTime, nullable=True)
    total_books_synced = Column(Integer, default=0, nullable=False)
    last_synced_offset = Column(Integer, default=0, nullable=False)
    is_syncing = Column(Boolean, default=False, nullable=False)
    sync_started_at = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
