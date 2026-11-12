# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base


class ReadingList(Base, TimestampMixin):

    __tablename__ = "reading_lists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False, index=True)  # Privacy setting for reading list
    share_token = Column(String(32), unique=True, nullable=True, index=True)  # Unique token for public sharing

    # Social sharing metrics
    share_count = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="reading_lists")
    items = relationship(
        "ListItem", back_populates="reading_list", cascade="all, delete-orphan"
    )


class ListItem(Base):

    __tablename__ = "list_items"

    id = Column(Integer, primary_key=True, index=True)
    list_id = Column(
        Integer,
        ForeignKey("reading_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    catalog_item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    personal_tags = Column(JSON, default=list, nullable=False, server_default='[]')

    __table_args__ = (
        UniqueConstraint("list_id", "catalog_item_id", name="uq_list_catalog_item"),
    )

    # Relationships
    reading_list = relationship("ReadingList", back_populates="items")
    catalog_item = relationship("CatalogItem", back_populates="list_items")
