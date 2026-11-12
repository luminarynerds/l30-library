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


class StandardEbook(Base):
    __tablename__ = "standard_ebooks"

    id = Column(Integer, primary_key=True, index=True)

    # Standard Ebooks identifier (URL path, e.g. "jane-austen/pride-and-prejudice")
    se_identifier = Column(String(500), unique=True, nullable=False, index=True)

    # Core metadata
    title = Column(String(1000), nullable=False)

    # Authors stored as JSON: [{"name": "Jane Austen", "url": "..."}]
    authors = Column(Text, nullable=True)

    # Description (long-form blurb)
    description = Column(Text, nullable=True)
    long_description = Column(Text, nullable=True)

    # Subject/genre stored as JSON array
    subjects = Column(Text, nullable=True)

    # Language
    language = Column(String(10), default="en", nullable=False)

    # Publication dates
    published_at = Column(DateTime, nullable=True)
    updated_at_source = Column(DateTime, nullable=True)

    # Word count and reading time
    word_count = Column(Integer, nullable=True)
    reading_ease = Column(String(50), nullable=True)  # e.g. "easy", "intermediate"

    # Download URLs
    epub_url = Column(String(1000), nullable=True)
    azw3_url = Column(String(1000), nullable=True)
    kepub_url = Column(String(1000), nullable=True)
    epub_advanced_url = Column(String(1000), nullable=True)

    # Cover image
    cover_url = Column(String(1000), nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)

    # Source URL on standardebooks.org
    source_url = Column(String(1000), nullable=True)

    # Link to local catalog (optional)
    catalog_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)

    # Sync tracking
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    catalog_item = relationship("CatalogItem", backref="standard_ebooks")
    downloads = relationship("StandardEbookDownload", back_populates="book", cascade="all, delete-orphan")
    favorites = relationship("StandardEbookFavorite", back_populates="book", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_standard_ebooks_title", "title"),
        Index("ix_standard_ebooks_catalog", "catalog_item_id"),
    )


class StandardEbookDownload(Base):
    __tablename__ = "standard_ebook_downloads"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("standard_ebooks.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20), default="epub", nullable=False)  # epub, azw3, kepub

    downloaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="standard_ebook_downloads")
    book = relationship("StandardEbook", back_populates="downloads")

    __table_args__ = (
        Index("ix_standard_ebook_downloads_user", "user_id", "downloaded_at"),
        Index("ix_standard_ebook_downloads_book", "book_id"),
    )


class StandardEbookFavorite(Base):
    __tablename__ = "standard_ebook_favorites"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("standard_ebooks.id", ondelete="CASCADE"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="standard_ebook_favorites")
    book = relationship("StandardEbook", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_standard_ebook_favorite"),
        Index("ix_standard_ebook_favorites_user", "user_id"),
    )


class StandardEbookSyncStatus(Base):
    __tablename__ = "standard_ebook_sync_status"

    id = Column(Integer, primary_key=True, index=True)

    last_sync_at = Column(DateTime, nullable=True)
    total_books_synced = Column(Integer, default=0, nullable=False)
    is_syncing = Column(Boolean, default=False, nullable=False)
    sync_started_at = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
