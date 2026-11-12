# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.inventory import InventoryAudit  # noqa: F401 — needed for ORM mapper
from app.models.weeding import WeedingCandidate  # noqa: F401 — needed for ORM mapper


class LifecycleEventType(StrEnum):

    # Acquisition events
    ORDERED = "ordered"
    RECEIVED = "received"

    # Cataloging events
    CATALOGING_STARTED = "cataloging_started"
    CATALOGED = "cataloged"

    # Processing events
    COPY_CREATED = "copy_created"
    SHELVED = "shelved"

    # Circulation events
    CHECKED_OUT = "checked_out"
    RETURNED = "returned"
    RENEWED = "renewed"
    HOLD_PLACED = "hold_placed"
    HOLD_FILLED = "hold_filled"

    # Condition events
    CONDITION_CHANGED = "condition_changed"
    DAMAGED = "damaged"
    REPAIRED = "repaired"

    # Inventory events
    INVENTORIED = "inventoried"
    MISSING = "missing"
    FOUND = "found"

    # Weeding events
    MARKED_FOR_WEEDING = "marked_for_weeding"
    WEEDING_APPROVED = "weeding_approved"
    WEEDING_REJECTED = "weeding_rejected"
    WEEDED = "weeded"
    DISPOSED = "disposed"

    # Transfer/location events
    LOCATION_CHANGED = "location_changed"
    TRANSFERRED = "transferred"

    # Other events
    NOTE_ADDED = "note_added"
    OTHER = "other"


class ItemLifecycleEvent(Base):

    __tablename__ = "item_lifecycle_events"
    __table_args__ = (
        CheckConstraint(
            """
            (event_type NOT IN (
                'marked_for_weeding', 'weeding_approved',
                'weeding_rejected', 'weeded', 'disposed'
            ))
            OR related_weeding_id IS NOT NULL
            """,
            name="ck_lifecycle_weeding_events_require_weeding_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Reference to the item copy
    item_copy_id = Column(
        Integer, ForeignKey("item_copies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Event type
    event_type = Column(
        String(50),
        nullable=False,
        index=True,
    )

    # Event description
    description = Column(Text)  # Human-readable description of the event

    # Event metadata (flexible JSON field for additional data)
    # Examples:
    # - CHECKED_OUT: {"patron_id": 123, "due_date": "2024-01-15"}
    # - CONDITION_CHANGED: {"from": "good", "to": "fair", "reason": "wear"}
    # - CATALOGED: {"cataloger_id": 45, "call_number": "813.54 SMI"}
    event_metadata = Column(JSONB, default={})

    # Who performed the action (if applicable)
    performed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Related record IDs for cross-referencing (optional)
    related_checkout_id = Column(Integer, ForeignKey("checkouts.id", ondelete="SET NULL"))
    related_po_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="SET NULL"))
    related_audit_id = Column(
        Integer, ForeignKey("inventory_audits.id", ondelete="SET NULL")
    )
    related_weeding_id = Column(
        Integer, ForeignKey("weeding_candidates.id", ondelete="SET NULL")
    )

    # Timestamps
    event_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    item_copy = relationship("ItemCopy", back_populates="lifecycle_events")
    performed_by = relationship("User")
    related_checkout = relationship("Checkout")
    related_purchase_order = relationship("PurchaseOrder")
    related_audit = relationship(
        "InventoryAudit", back_populates="lifecycle_events",
        foreign_keys=[related_audit_id],
    )
    related_weeding = relationship(
        "WeedingCandidate", back_populates="lifecycle_events",
        foreign_keys=[related_weeding_id],
    )
