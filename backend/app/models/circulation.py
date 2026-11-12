# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from app.models.mixins import TimestampMixin
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Index, String, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class CheckoutStatus(StrEnum):
    active = "active"
    returned = "returned"
    overdue = "overdue"
    lost = "lost"
    # Extended statuses for lost/damaged workflows
    lost_by_patron = "lost_by_patron"
    lost_in_transit = "lost_in_transit"
    claims_returned = "claims_returned"
    damaged = "damaged"
    returned_damaged = "returned_damaged"


class HoldStatus(StrEnum):
    pending = "pending"
    ready = "ready"
    fulfilled = "fulfilled"
    cancelled = "cancelled"
    expired = "expired"


class Checkout(Base):
    __tablename__ = "checkouts"

    id = Column(Integer, primary_key=True, index=True)
    # RESTRICT on delete: cannot delete user/item with checkout history
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    # Changed from item_id to item_copy_id for individual copy tracking
    # Legacy item_id kept for backwards compatibility with catalog_items
    # RESTRICT on delete: cannot delete item with checkout history
    item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="RESTRICT"), nullable=False
    )
    item_copy_id = Column(
        Integer, ForeignKey("item_copies.id", ondelete="SET NULL"), nullable=True
    )

    status = Column(
        SQLEnum(CheckoutStatus, name="checkoutstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=CheckoutStatus.active,
        nullable=False,
    )

    checked_out_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    returned_at = Column(DateTime(timezone=True), nullable=True)
    renewal_count = Column(Integer, default=0, nullable=False)

    # Track overdue days already processed for reading minutes (prevents duplicate additions)
    last_overdue_days_processed = Column(Integer, default=0, nullable=False)

    # Timestamps, onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="checkouts")
    item = relationship(
        "CatalogItem", back_populates="checkouts"
    )  # Legacy, kept for migration
    item_copy = relationship("ItemCopy", back_populates="checkouts")

    # Active-checkout uniqueness is enforced per physical COPY (one active loan
    # per item_copy) via ix_active_item_copy_checkout below. There is intentionally
    # NO title-level (item_id) active-unique index: a multi-copy title must be able
    # to have one active checkout per copy concurrently. (The old title-level
    # ix_active_item_checkout was dropped 2026-06-09; it wrongly capped a whole
    # title at one active loan regardless of copy count.)
    # PERFORMANCE OPTIMIZATION: Composite indexes for common query patterns
    __table_args__ = (
        CheckConstraint(
            "due_date >= checked_out_at",
            name="ck_checkout_due_after_checkout",
        ),
        CheckConstraint(
            "returned_at IS NULL OR returned_at >= checked_out_at",
            name="ck_checkout_return_after_checkout",
        ),
        CheckConstraint(
            "renewal_count >= 0",
            name="ck_checkout_renewal_count_non_negative",
        ),
        Index(
            "ix_active_item_copy_checkout",
            "item_copy_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        # Composite index for user's checkouts by status (GET /checkouts, patron queries)
        Index("ix_checkouts_user_status", "user_id", "status"),
        # Composite index for overdue detection queries (due_date + status)
        Index("ix_checkouts_due_status", "due_date", "status"),
        # Composite index for item copy checkout lookups (RFID inventory, batch operations)
        Index("ix_checkouts_item_copy_status", "item_copy_id", "status"),
    )


class Hold(Base, TimestampMixin):
    __tablename__ = "holds"

    id = Column(Integer, primary_key=True, index=True)
    # RESTRICT on delete: cannot delete user/item with hold history
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="RESTRICT"), nullable=False
    )
    # Pickup location - defaults to user's home branch
    pickup_location_id = Column(
        Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True
    )

    status = Column(
        SQLEnum(HoldStatus, name="holdstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=HoldStatus.pending,
        nullable=False,
    )

    position = Column(Integer, default=1)  # Position in hold queue, server_default=func.now())
    notified_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Cancellation metadata
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(String(500), nullable=True)
    cancelled_by = Column(String(50), nullable=True)  # "patron", "staff", "system"

    # Smart hold shelf fields
    shelf_slot = Column(String(20), nullable=True)  # Assigned shelf slot e.g. "A-03"
    patron_on_way = Column(Boolean, default=False, nullable=False)  # Patron said they're coming
    patron_on_way_at = Column(DateTime(timezone=True), nullable=True)  # When patron said on way
    no_show_count = Column(Integer, default=0, nullable=False)  # Times patron didn't pick up
    qr_pickup_code = Column(String(64), nullable=True, unique=True)  # QR code for self-pickup

    # Relationships
    user = relationship("User", back_populates="holds")
    item = relationship("CatalogItem", back_populates="holds")
    pickup_location = relationship("Branch", foreign_keys=[pickup_location_id])

    # Partial unique index: only prevent duplicate active holds (pending/ready)
    # This allows users to place new holds on items they previously held
    # The actual index is created via migration with:
    # CREATE UNIQUE INDEX ix_active_user_item_hold ON holds (user_id, item_id)
    # WHERE status IN ('pending', 'ready')
    # PERFORMANCE OPTIMIZATION: Composite indexes for common query patterns
    __table_args__ = (
        CheckConstraint(
            "position > 0",
            name="ck_hold_position_positive",
        ),
        CheckConstraint(
            "no_show_count >= 0",
            name="ck_hold_no_show_count_non_negative",
        ),
        Index(
            "ix_active_user_item_hold",
            "user_id",
            "item_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'ready')"),
        ),
        # Composite index for holds by user (GET /holds queries)
        Index("ix_holds_user_status", "user_id", "status"),
        # Composite index for item hold queue queries (item_id + status + position)
        Index("ix_holds_item_status_position", "item_id", "status", "position"),
        # Supports pickup-location filtering for ready-hold workflows
        Index("ix_holds_pickup_location_id", "pickup_location_id"),
        # Smart shelf: lookup by shelf slot within a branch
        Index(
            "ix_holds_shelf_slot_ready",
            "pickup_location_id",
            "shelf_slot",
            postgresql_where=text("status = 'ready' AND shelf_slot IS NOT NULL"),
        ),
    )
