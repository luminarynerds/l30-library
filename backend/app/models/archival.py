# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint, Column, Date, DateTime, ForeignKey, Index,
    Integer, String, Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.enum_helpers import EnumColumn
from app.models.mixins import TimestampMixin


class FindingAidStatus(StrEnum):
    draft = "draft"
    in_progress = "in_progress"
    published = "published"
    revised = "revised"


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


class ArchivalCollection(Base, TimestampMixin):
    __tablename__ = "archival_collections"

    id = Column(Integer, primary_key=True, index=True)

    # DACS 2.1 - Reference code / collection identifier
    identifier = Column(String(100), nullable=False, unique=True, index=True)
    # DACS 2.3 - Title
    title = Column(String(500), nullable=False, index=True)
    # DACS 2.6 - Name of creator
    creator = Column(String(500), nullable=True, index=True)
    # DACS 2.2 - Repository / name of holding institution
    repository = Column(String(255), nullable=True)

    # DACS 2.4 - Inclusive dates (machine-parseable + free text)
    date_inclusive_start = Column(Date, nullable=True)
    date_inclusive_end = Column(Date, nullable=True)
    date_inclusive_text = Column(String(255), nullable=True)
    # DACS 2.4 - Bulk dates
    date_bulk_start = Column(Date, nullable=True)
    date_bulk_end = Column(Date, nullable=True)

    # DACS 2.5 - Extent
    extent = Column(String(255), nullable=True)
    # DACS 4.5 - Languages of materials (comma-separated ISO 639-2 codes)
    languages = Column(String(255), nullable=True)

    # DACS 3.1 - Scope and content
    scope_and_content = Column(Text, nullable=True)
    # DACS 2.7 - Administrative / biographical history
    biographical_historical = Column(Text, nullable=True)
    # DACS 3.2 - System of arrangement
    arrangement = Column(Text, nullable=True)
    # DACS 5.1 - Processing information
    processing_info = Column(Text, nullable=True)
    # DACS 5.2 - Immediate source of acquisition
    acquisition_info = Column(Text, nullable=True)
    # DACS 5.1.1 - Custodial history
    custodial_history = Column(Text, nullable=True)
    # DACS 4.1 - Conditions governing access
    access_restrictions = Column(Text, nullable=True)
    # DACS 4.4 - Conditions governing reproduction and use
    use_restrictions = Column(Text, nullable=True)
    # DACS 7.1.5 - Preferred citation of described materials
    preferred_citation = Column(Text, nullable=True)
    # DACS 6.3 - Related archival materials
    related_materials = Column(Text, nullable=True)

    # External finding-aid URL (used when crosswalking to MARC 856)
    finding_aid_url = Column(String(500), nullable=True)

    finding_aid_status = EnumColumn(
        FindingAidStatus,
        nullable=False,
        default=FindingAidStatus.draft,
        index=True,
    )
    published_at = Column(DateTime(timezone=True), nullable=True)

    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )

    components = relationship(
        "ArchivalComponent",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="ArchivalComponent.sort_order",
    )

    __table_args__ = (
        CheckConstraint(
            "date_inclusive_end IS NULL OR date_inclusive_start IS NULL "
            "OR date_inclusive_end >= date_inclusive_start",
            name="ck_archival_collection_inclusive_date_order",
        ),
        CheckConstraint(
            "date_bulk_end IS NULL OR date_bulk_start IS NULL "
            "OR date_bulk_end >= date_bulk_start",
            name="ck_archival_collection_bulk_date_order",
        ),
    )


class ArchivalComponent(Base, TimestampMixin):
    __tablename__ = "archival_components"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(
        Integer,
        ForeignKey("archival_collections.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    parent_id = Column(
        Integer,
        ForeignKey("archival_components.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )

    level = EnumColumn(
        ArchivalLevel, nullable=False, index=True, default=ArchivalLevel.series,
    )

    # Component reference (e.g. "Series 1", "1.2", "Box 3, Folder 5")
    identifier = Column(String(100), nullable=True, index=True)
    title = Column(String(500), nullable=False)

    date_inclusive_start = Column(Date, nullable=True)
    date_inclusive_end = Column(Date, nullable=True)
    date_inclusive_text = Column(String(255), nullable=True)
    extent = Column(String(255), nullable=True)

    scope_and_content = Column(Text, nullable=True)
    arrangement = Column(Text, nullable=True)
    access_restrictions = Column(Text, nullable=True)

    # Container summary (e.g. "Box 3, Folder 5"), for finding-aid display
    container_summary = Column(String(255), nullable=True)

    # Stable, dense ordering within siblings; lower sorts first
    sort_order = Column(Integer, nullable=False, default=0)

    # Item-level components may correspond to a circulating physical item.
    catalog_item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    collection = relationship("ArchivalCollection", back_populates="components")
    parent = relationship(
        "ArchivalComponent",
        remote_side="ArchivalComponent.id",
        back_populates="children",
    )
    children = relationship(
        "ArchivalComponent",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="ArchivalComponent.sort_order",
    )
    catalog_item = relationship("CatalogItem", foreign_keys=[catalog_item_id])

    __table_args__ = (
        CheckConstraint(
            "date_inclusive_end IS NULL OR date_inclusive_start IS NULL "
            "OR date_inclusive_end >= date_inclusive_start",
            name="ck_archival_component_inclusive_date_order",
        ),
        Index(
            "ix_archival_components_collection_parent",
            "collection_id", "parent_id",
        ),
        Index(
            "ix_archival_components_collection_sort",
            "collection_id", "sort_order",
        ),
    )
