# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class MangaCatalogingTemplate(Base, TimestampMixin):

    __tablename__ = "manga_cataloging_templates"

    id = Column(Integer, primary_key=True, index=True)

    # Template metadata
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_shared = Column(Boolean, default=True)  # Share across staff

    # Series defaults
    series_title = Column(String(500), nullable=False)
    author = Column(String(255), nullable=True)
    original_language = Column(String(50), default="Japanese")
    publisher = Column(String(255), nullable=True)

    # Format defaults for manga
    item_type = Column(String(50), default="book")
    genre = Column(String(255), default="manga,graphic novels")
    subjects = Column(String(500), default="manga,graphic novels,Japanese comics")

    # Collection defaults
    catalog_series_type = Column(String(50), default="graphic_novel_series")

    # Media format specifics
    format = Column(String(100), default="volume")  # volume, complete, partial series box
    isbn_pattern = Column(String(100), nullable=True)  # e.g., "978-1-234-5678" with notes on volume numbering
    covers_color = Column(Boolean, default=True)
    page_count_average = Column(Integer, nullable=True)  # e.g., 200 pages typical

    # Metadata fields (as JSON for flexibility)
    default_fields = Column(
        JSONB,
        default={
            "location": "Manga Section",
            "dewey_decimal": "741.5952",  # Dewey for manga
            "lc_classification": "PN1997.2",  # LC for manga comics
        },
    )

    # Flags
    auto_increment_volume = Column(Boolean, default=True)
    auto_fetch_cover = Column(Boolean, default=True)
    auto_populate_series_info = Column(Boolean, default=True)

    # Timestamps, server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])


class MangaVolumeRecord(Base):

    __tablename__ = "manga_volume_records"

    id = Column(Integer, primary_key=True, index=True)

    # Links to catalog item and series
    catalog_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False, index=True)
    series_title = Column(String(500), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("manga_cataloging_templates.id", ondelete="SET NULL"), nullable=True)

    # Volume information
    volume_number = Column(Integer, nullable=False)  # e.g., 1, 2, 3... or 0 for omnibus
    volume_title = Column(String(500), nullable=True)  # Optional subtitle for specific volumes
    isbn = Column(String(20), nullable=True, index=True)
    cover_image_url = Column(String(500), nullable=True)
    cover_fetch_source = Column(
        String(100), nullable=True
    )  # e.g., "open_library", "google_books", "manual"

    # Publication info
    publication_date = Column(DateTime(timezone=True), nullable=True)
    publisher = Column(String(255), nullable=True)
    original_language = Column(String(50), nullable=True)

    # Physical characteristics
    page_count = Column(Integer, nullable=True)
    is_color = Column(Boolean, nullable=True)

    # Relationship to previous volume for copy incrementing
    previous_volume_id = Column(Integer, ForeignKey("manga_volume_records.id", ondelete="SET NULL"), nullable=True)

    # Timestamp tracking, server_default=func.now())

    # Relationships
    catalog_item = relationship("CatalogItem")
    template = relationship("MangaCatalogingTemplate")
    previous_volume = relationship(
        "MangaVolumeRecord",
        remote_side=[id],
        foreign_keys=[previous_volume_id],
        backref="next_volume",
    )
