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


class FeedbooksBook(Base):
    __tablename__ = "feedbooks_books"

    id = Column(Integer, primary_key=True, index=True)

    # Feedbooks identifier
    feedbooks_id = Column(String(100), unique=True, nullable=False, index=True)

    # Core metadata
    title = Column(String(1000), nullable=False)

    # Authors stored as JSON: [{"name": "Jane Austen", "uri": "..."}]
    authors = Column(Text, nullable=True)

    # Description/summary
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)  # Longer description if available

    # Categories stored as JSON array
    categories = Column(Text, nullable=True)

    # Language
    language = Column(String(10), default="en", nullable=False)

    # Publication info
    published_at = Column(DateTime, nullable=True)
    publisher = Column(String(500), nullable=True)
    rights = Column(String(500), nullable=True)  # License info

    # Download URLs
    epub_url = Column(String(1000), nullable=True)
    mobi_url = Column(String(1000), nullable=True)
    pdf_url = Column(String(1000), nullable=True)

    # Cover image
    cover_url = Column(String(1000), nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)

    # Source URL on feedbooks.com
    source_url = Column(String(1000), nullable=True)

    # Link to local catalog (optional)
    catalog_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)

    # Sync tracking
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    catalog_item = relationship("CatalogItem", backref="feedbooks_books")
    downloads = relationship("FeedbooksDownload", back_populates="book", cascade="all, delete-orphan")
    favorites = relationship("FeedbooksFavorite", back_populates="book", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_feedbooks_books_title", "title"),
        Index("ix_feedbooks_books_catalog", "catalog_item_id"),
    )


class FeedbooksDownload(Base):
    __tablename__ = "feedbooks_downloads"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("feedbooks_books.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20), default="epub", nullable=False)  # epub, mobi, pdf

    downloaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="feedbooks_downloads")
    book = relationship("FeedbooksBook", back_populates="downloads")

    __table_args__ = (
        Index("ix_feedbooks_downloads_user", "user_id", "downloaded_at"),
        Index("ix_feedbooks_downloads_book", "book_id"),
    )


class FeedbooksFavorite(Base):
    __tablename__ = "feedbooks_favorites"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("feedbooks_books.id", ondelete="CASCADE"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="feedbooks_favorites")
    book = relationship("FeedbooksBook", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_feedbooks_favorite"),
        Index("ix_feedbooks_favorites_user", "user_id"),
    )


class FeedbooksSyncStatus(Base):
    __tablename__ = "feedbooks_sync_status"

    id = Column(Integer, primary_key=True, index=True)

    last_sync_at = Column(DateTime, nullable=True)
    total_books_synced = Column(Integer, default=0, nullable=False)
    is_syncing = Column(Boolean, default=False, nullable=False)
    sync_started_at = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
