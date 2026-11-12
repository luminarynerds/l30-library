# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

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
    func,
)
from sqlalchemy.orm import relationship

from ..core.database import Base


class ManyBooksBook(Base):
    __tablename__ = "manybooks_books"

    id = Column(Integer, primary_key=True, index=True)

    # ManyBooks identifier (URL slug)
    manybooks_id = Column(String(500), unique=True, nullable=False, index=True)

    # Core metadata
    title = Column(String(1000), nullable=False)

    # Authors stored as JSON: [{"name": "Jane Austen"}]
    authors = Column(Text, nullable=True)

    # Description
    summary = Column(Text, nullable=True)

    # Categories/genres stored as JSON array
    categories = Column(Text, nullable=True)

    # Language
    language = Column(String(10), default="en", nullable=False)

    # Publication info
    publication_year = Column(Integer, nullable=True)

    # Community ratings
    rating = Column(Float, nullable=True)  # Average rating (0-5)
    rating_count = Column(Integer, default=0, nullable=False)

    # Download formats as JSON: {"epub": "url", "mobi": "url", "pdf": "url"}
    formats = Column(Text, nullable=True)

    # Cover image
    cover_url = Column(String(1000), nullable=True)

    # Source URL on manybooks.net
    source_url = Column(String(1000), nullable=True)

    # Cross-reference to Gutenberg if available
    gutenberg_id = Column(Integer, nullable=True, index=True)

    # Link to local catalog (optional)
    catalog_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)

    # Sync tracking
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    catalog_item = relationship("CatalogItem", backref="manybooks_books")
    downloads = relationship("ManyBooksDownload", back_populates="book", cascade="all, delete-orphan")
    favorites = relationship("ManyBooksFavorite", back_populates="book", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_manybooks_books_title", "title"),
        Index("ix_manybooks_books_rating", "rating"),
        Index("ix_manybooks_books_catalog", "catalog_item_id"),
    )


class ManyBooksDownload(Base):
    __tablename__ = "manybooks_downloads"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("manybooks_books.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20), default="epub", nullable=False)

    downloaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="manybooks_downloads")
    book = relationship("ManyBooksBook", back_populates="downloads")

    __table_args__ = (
        Index("ix_manybooks_downloads_user", "user_id", "downloaded_at"),
        Index("ix_manybooks_downloads_book", "book_id"),
    )


class ManyBooksFavorite(Base):
    __tablename__ = "manybooks_favorites"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("manybooks_books.id", ondelete="CASCADE"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="manybooks_favorites")
    book = relationship("ManyBooksBook", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_manybooks_favorite"),
        Index("ix_manybooks_favorites_user", "user_id"),
    )


class ManyBooksSyncStatus(Base):
    __tablename__ = "manybooks_sync_status"

    id = Column(Integer, primary_key=True, index=True)

    last_sync_at = Column(DateTime, nullable=True)
    total_books_synced = Column(Integer, default=0, nullable=False)
    last_synced_page = Column(Integer, default=0, nullable=False)
    is_syncing = Column(Boolean, default=False, nullable=False)
    sync_started_at = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
