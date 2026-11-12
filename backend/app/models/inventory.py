# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ItemCondition(StrEnum):
    NEW = "new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    DAMAGED = "damaged"
    WITHDRAWN = "withdrawn"


class DamageType(StrEnum):
    TORN_PAGES = "torn_pages"
    WATER_DAMAGE = "water_damage"
    MISSING_COVER = "missing_cover"
    SPINE_DAMAGE = "spine_damage"
    WRITING_MARKS = "writing_marks"
    STAINS = "stains"
    MISSING_PAGES = "missing_pages"
    BINDING_LOOSE = "binding_loose"
    MISSING_DISC = "missing_disc"  # Missing DVD/CD/Blu-ray from media item
    OTHER = "other"


class AcquisitionSource(StrEnum):
    PURCHASE = "purchase"
    DONATION = "donation"
    GRANT = "grant"
    TRANSFER = "transfer"
    OTHER = "other"


class ProcessingStep(StrEnum):
    RECEIVED = "received"
    LABELING = "labeling"
    RFID_TAGGING = "rfid_tagging"
    READY_TO_SHELVE = "ready_to_shelve"
    SHELVED = "shelved"


class ItemCopy(Base):

    __tablename__ = "item_copies"
    __table_args__ = (
        UniqueConstraint(
            "catalog_item_id", "copy_number", name="uq_item_copy_catalog_copy_number"
        ),
        CheckConstraint(
            "copy_number > 0",
            name="ck_item_copy_copy_number_positive",
        ),
        CheckConstraint(
            "replacement_cost IS NULL OR replacement_cost >= 0",
            name="ck_item_copy_replacement_cost_non_negative",
        ),
        Index("ix_item_copies_catalog_item_condition", "catalog_item_id", "condition"),
    )

    id = Column(Integer, primary_key=True, index=True)
    catalog_item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Identification
    barcode = Column(String(50), unique=True, nullable=False, index=True)
    copy_number = Column(Integer, nullable=False, default=1)

    # Condition
    condition = Column(
        String(50),
        default=ItemCondition.GOOD,
        nullable=False,
        index=True,
    )

    # Acquisition
    acquisition_date = Column(Date, default=date.today)
    acquisition_source = Column(
        String(50),
        default=AcquisitionSource.PURCHASE,
    )
    purchase_order_item_id = Column(Integer, ForeignKey("purchase_order_items.id", ondelete="SET NULL"))

    # Location & Value
    location = Column(String(100), index=True)  # Simple location string like "Adult Fiction A-3"
    replacement_cost = Column(Numeric(10, 2))

    # Processing queue
    processing_step = Column(
        String(50),
        nullable=True,
    )

    # Volume override for copies that diverge from the catalog item's
    # volume_number — e.g. an omnibus binding spanning "1-3", a single volume
    # missing from a set, or a replacement copy with different pagination.
    # Leave NULL to inherit volume_number from the parent CatalogItem.
    volume_override = Column(String(50), nullable=True)

    # Notes and special handling
    notes = Column(Text)
    is_fragile = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flag for fragile items; staff should handle with care during checkout"
    )
    handling_instructions = Column(
        Text,
        nullable=True,
        comment="Special instructions for handling (e.g., check binding, use care with pages)"
    )

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    catalog_item = relationship("CatalogItem")
    purchase_order_item = relationship("PurchaseOrderItem")
    condition_changes = relationship(
        "ConditionChange", back_populates="item_copy", cascade="all, delete-orphan"
    )
    checkouts = relationship("Checkout", back_populates="item_copy")
    lifecycle_events = relationship(
        "ItemLifecycleEvent", back_populates="item_copy",
        foreign_keys="[ItemLifecycleEvent.item_copy_id]",
    )

    @property
    def is_available(self) -> bool:
        return self.condition not in [ItemCondition.WITHDRAWN, ItemCondition.DAMAGED]


class ConditionChange(Base):

    __tablename__ = "condition_changes"

    id = Column(Integer, primary_key=True, index=True)
    item_copy_id = Column(
        Integer,
        ForeignKey("item_copies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Condition change
    previous_condition = Column(
        String(50),
        nullable=False,
    )
    new_condition = Column(
        String(50),
        nullable=False,
    )

    # Damage details (optional)
    damage_type = Column(
        String(50)
    )
    damage_description = Column(Text)
    photo_url = Column(Text)  # URL to damage photo

    # Repair info (if applicable)
    repair_cost = Column(Numeric(10, 2))
    repair_notes = Column(Text)
    repaired_at = Column(DateTime(timezone=True))

    # Who and when
    reported_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    item_copy = relationship("ItemCopy", back_populates="condition_changes")
    reported_by = relationship("User")


class InventoryAudit(Base):

    __tablename__ = "inventory_audits"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Scope
    location_filter = Column(String(100))  # Filter by location (e.g., "Adult Fiction")

    # Status
    started_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at = Column(DateTime(timezone=True))

    # Stats
    items_expected = Column(Integer, default=0)
    items_found = Column(Integer, default=0)
    items_missing = Column(Integer, default=0)
    items_misplaced = Column(Integer, default=0)

    # Who
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="ck_inventory_audit_completed_after_started",
        ),
        CheckConstraint(
            "items_expected >= 0",
            name="ck_inventory_audit_items_expected_non_negative",
        ),
        CheckConstraint(
            "items_found >= 0",
            name="ck_inventory_audit_items_found_non_negative",
        ),
        CheckConstraint(
            "items_missing >= 0",
            name="ck_inventory_audit_items_missing_non_negative",
        ),
        CheckConstraint(
            "items_misplaced >= 0",
            name="ck_inventory_audit_items_misplaced_non_negative",
        ),
    )

    # Relationships
    created_by = relationship("User")
    scanned_items = relationship(
        "AuditScan", back_populates="audit", cascade="all, delete-orphan"
    )
    lifecycle_events = relationship(
        "ItemLifecycleEvent", back_populates="related_audit",
        foreign_keys="[ItemLifecycleEvent.related_audit_id]",
    )


class AuditScan(Base):

    __tablename__ = "audit_scans"
    __table_args__ = (
        UniqueConstraint('audit_id', 'item_copy_id', name='uq_audit_scan_item'),
    )

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(
        Integer,
        ForeignKey("inventory_audits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_copy_id = Column(Integer, ForeignKey("item_copies.id", ondelete="CASCADE"), nullable=False)

    # Scan result
    found_at_location = Column(String(100))  # Where it was actually found
    is_misplaced = Column(Boolean, default=False)  # Found in wrong location

    # Metadata
    scanned_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    scanned_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    audit = relationship("InventoryAudit", back_populates="scanned_items")
    item_copy = relationship("ItemCopy")
    scanned_by = relationship("User")
