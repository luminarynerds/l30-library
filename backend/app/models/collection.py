# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.enum_helpers import EnumColumn


class ArchivalLevel(StrEnum):

    collection = "collection"
    fonds = "fonds"
    recordgrp = "recordgrp"
    subgrp = "subgrp"
    series = "series"
    subseries = "subseries"
    file = "file"
    item = "item"
    otherlevel = "otherlevel"


class CollectionItem(Base):

    __tablename__ = "collection_items"

    id = Column(Integer, primary_key=True)
    collection_id = Column(
        Integer,
        ForeignKey("collection.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    catalog_item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = Column(Integer, nullable=False, default=0)
    component_label = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    collection = relationship("Collection", back_populates="items")
    catalog_item = relationship("CatalogItem")

    __table_args__ = (
        UniqueConstraint(
            "collection_id",
            "catalog_item_id",
            name="uq_collection_items_collection_catalog",
        ),
        Index(
            "ix_collection_items_collection_position",
            "collection_id",
            "position",
        ),
    )


class Collection(Base):

    __tablename__ = "collection"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Hierarchy ---
    parent_id = Column(
        Integer,
        ForeignKey("collection.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    position = Column(Integer, nullable=False, default=0)
    level = EnumColumn(ArchivalLevel, nullable=True, index=True)

    # --- DACS 2.1-2.6 Identity & Context (single-level required) ---
    reference_code = Column(String(100), nullable=True, index=True, unique=True)
    title = Column(String(500), nullable=True)
    date_creation = Column(String(255), nullable=True)
    date_accumulation = Column(String(255), nullable=True)
    extent = Column(String(255), nullable=True)
    creator = Column(String(500), nullable=True, index=True)

    # --- DACS 2.7 Administrative/Biographical history ---
    biographical_history = Column(Text, nullable=True)
    archival_history = Column(Text, nullable=True)
    acquisition_source = Column(Text, nullable=True)

    # --- DACS 3 Content & structure ---
    scope_content = Column(Text, nullable=True)
    appraisal = Column(Text, nullable=True)
    accruals = Column(Text, nullable=True)
    arrangement = Column(Text, nullable=True)

    # --- DACS 4 Conditions of access and use ---
    access_conditions = Column(Text, nullable=True)
    reproduction_conditions = Column(Text, nullable=True)
    languages = Column(String(255), nullable=True)
    physical_access = Column(Text, nullable=True)
    technical_access = Column(Text, nullable=True)
    finding_aids = Column(Text, nullable=True)

    # --- DACS 5 Allied materials ---
    originals_location = Column(Text, nullable=True)
    copies_location = Column(Text, nullable=True)
    related_materials = Column(Text, nullable=True)
    publication_note = Column(Text, nullable=True)

    # --- DACS 6 Notes ---
    notes = Column(Text, nullable=True)

    # --- DACS 7 Description control ---
    description_rules = Column(String(255), nullable=True)
    description_status = Column(String(50), nullable=True)
    described_by = Column(String(255), nullable=True)
    described_at = Column(DateTime(timezone=True), nullable=True)

    parent = relationship(
        "Collection",
        remote_side="Collection.id",
        back_populates="children",
    )
    children = relationship(
        "Collection",
        back_populates="parent",
        order_by="Collection.position",
        cascade="save-update, merge",
        passive_deletes="all",
    )
    items = relationship(
        "CollectionItem",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="CollectionItem.position",
    )

    __table_args__ = (
        Index("ix_collection_parent_position", "parent_id", "position"),
    )

    def __repr__(self):
        return f"<Collection(id={self.id}, name={self.name!r}, level={self.level})>"
