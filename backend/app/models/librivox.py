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


class LibriVoxBookType(PyEnum):
    SOLO = "solo"            # Single reader
    GROUP = "group"          # Multiple readers
    DRAMATIC = "dramatic"    # Dramatic reading
    POETRY = "poetry"        # Poetry collection


class LibriVoxAudiobook(Base):
    __tablename__ = "librivox_audiobooks"

    id = Column(Integer, primary_key=True, index=True)

    # LibriVox identifier
    librivox_id = Column(Integer, unique=True, nullable=False, index=True)

    # Core metadata
    title = Column(String(1000), nullable=False)

    # Authors stored as JSON: [{"first_name": "Jane", "last_name": "Austen", "dob": "1775", "dod": "1817"}]
    authors = Column(Text, nullable=True)

    # Description
    description = Column(Text, nullable=True)

    # Genres/subjects stored as JSON array
    genres = Column(Text, nullable=True)

    # Language
    language = Column(String(100), nullable=True)

    # Recording info
    book_type = Column(Enum(LibriVoxBookType, values_callable=lambda x: [m.value for m in x]), default=LibriVoxBookType.SOLO, nullable=False)
    total_time = Column(String(20), nullable=True)  # e.g. "12:34:56"
    num_sections = Column(Integer, default=0, nullable=False)

    # Copyright info (year of text, not recording)
    copyright_year = Column(Integer, nullable=True)

    # URLs
    url_librivox = Column(String(1000), nullable=True)  # LibriVox page
    url_project = Column(String(1000), nullable=True)   # Archive.org page
    url_rss = Column(String(1000), nullable=True)       # RSS feed for episodes
    url_zip = Column(String(1000), nullable=True)       # ZIP download of all MP3s

    # Sections stored as JSON array of sections with reader, title, listen_url, etc.
    sections = Column(Text, nullable=True)

    # Readers stored as JSON: [{"display_name": "...", "reader_id": 123}]
    readers = Column(Text, nullable=True)

    # Popularity
    totaltime_secs = Column(Integer, default=0, nullable=False)

    # Link to Gutenberg (if available)
    gutenberg_id = Column(Integer, nullable=True, index=True)

    # Link to local catalog (optional)
    catalog_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)

    # Sync tracking
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    catalog_item = relationship("CatalogItem", backref="librivox_audiobooks")
    listens = relationship("LibriVoxListen", back_populates="audiobook", cascade="all, delete-orphan")
    favorites = relationship("LibriVoxFavorite", back_populates="audiobook", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_librivox_audiobooks_title", "title"),
        Index("ix_librivox_audiobooks_catalog", "catalog_item_id"),
    )


class LibriVoxListen(Base):
    __tablename__ = "librivox_listens"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    audiobook_id = Column(Integer, ForeignKey("librivox_audiobooks.id", ondelete="CASCADE"), nullable=False)

    # Which section they listened to (null for full audiobook download)
    section_number = Column(Integer, nullable=True)

    listened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="librivox_listens")
    audiobook = relationship("LibriVoxAudiobook", back_populates="listens")

    __table_args__ = (
        Index("ix_librivox_listens_user", "user_id", "listened_at"),
        Index("ix_librivox_listens_audiobook", "audiobook_id"),
    )


class LibriVoxFavorite(Base):
    __tablename__ = "librivox_favorites"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    audiobook_id = Column(Integer, ForeignKey("librivox_audiobooks.id", ondelete="CASCADE"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="librivox_favorites")
    audiobook = relationship("LibriVoxAudiobook", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "audiobook_id", name="uq_librivox_favorite"),
        Index("ix_librivox_favorites_user", "user_id"),
    )


class LibriVoxSyncStatus(Base):
    __tablename__ = "librivox_sync_status"

    id = Column(Integer, primary_key=True, index=True)

    last_sync_at = Column(DateTime, nullable=True)
    total_audiobooks_synced = Column(Integer, default=0, nullable=False)
    last_synced_offset = Column(Integer, default=0, nullable=False)
    is_syncing = Column(Boolean, default=False, nullable=False)
    sync_started_at = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
