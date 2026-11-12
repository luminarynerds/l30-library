# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base

import enum


from enum import Enum, StrEnum
class CollectionStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class EbookFeatured(Base):
    __tablename__ = "ebook_featured"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metislib_ebook_id = Column(Integer, nullable=False, unique=True, index=True)
    display_order = Column(Integer, nullable=False, default=0)
    theme_title = Column(String(255), nullable=True)
    entry_type = Column(String(50), nullable=True)
    featured_from = Column(DateTime(timezone=True), nullable=True)
    featured_until = Column(DateTime(timezone=True), nullable=True)
    added_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    added_by = relationship("User", foreign_keys=[added_by_id])


class EbookCollection(Base):
    __tablename__ = "ebook_collections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(CollectionStatus, values_callable=lambda x: [e.value for e in x], name="collection_status_enum"), nullable=False, default=CollectionStatus.DRAFT)
    display_order = Column(Integer, nullable=False, default=0)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_id])
    items = relationship("EbookCollectionItem", back_populates="collection", cascade="all, delete-orphan", order_by="EbookCollectionItem.display_order")


class EbookCollectionItem(Base):
    __tablename__ = "ebook_collection_items"

    collection_id = Column(Integer, ForeignKey("ebook_collections.id", ondelete="CASCADE"), primary_key=True)
    metislib_ebook_id = Column(Integer, primary_key=True)
    display_order = Column(Integer, nullable=False, default=0)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    collection = relationship("EbookCollection", back_populates="items")

    __table_args__ = (
        UniqueConstraint("collection_id", "metislib_ebook_id", name="uq_collection_ebook"),
    )
