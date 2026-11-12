# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import Column, DateTime, Index, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.mixins import TimestampMixin
from ..core.database import Base


class PatronActivityType(StrEnum):
    checkout = "checkout"
    return_item = "return"
    fine_created = "fine_created"
    fine_paid = "fine_paid"
    fine_waived = "fine_waived"
    hold_placed = "hold_placed"
    hold_fulfilled = "hold_fulfilled"
    hold_cancelled = "hold_cancelled"
    hold_expired = "hold_expired"
    account_blocked = "account_blocked"
    account_unblocked = "account_unblocked"
    account_created = "account_created"
    profile_updated = "profile_updated"
    renewal = "renewal"


class PatronActivity(TimestampMixin, Base):
    __tablename__ = "patron_activities"

    id = Column(Integer, primary_key=True, index=True)

    # The patron this activity belongs to
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Staff member who performed the action (if applicable)
    staff_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Activity type
    activity_type = Column(
        SQLEnum(PatronActivityType, name="patronactivitytype", create_type=False, values_callable=lambda x: [e.value for e in x]),
    )

    # Description of the activity
    description = Column(Text, nullable=False)

    # Related item information (optional, for checkouts, returns, holds)
    item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True
    )
    item_title = Column(String(500), nullable=True)
    item_author = Column(String(255), nullable=True)

    # Related fine information (optional, for fine activities)
    fine_id = Column(
        Integer, ForeignKey("fines.id", ondelete="SET NULL"), nullable=True
    )
    fine_amount = Column(String(20), nullable=True)

    # Related checkout information (optional)
    checkout_id = Column(
        Integer, ForeignKey("checkouts.id", ondelete="SET NULL"), nullable=True
    )

    # Related hold information (optional)
    hold_id = Column(
        Integer, ForeignKey("holds.id", ondelete="SET NULL"), nullable=True
    )

    # Additional metadata as JSON string
    metadata_json = Column(Text, nullable=True)

    # Timestamps, server_default=func.now())

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id], backref="activities")
    staff = relationship("User", foreign_keys=[staff_id])
    item = relationship("CatalogItem", backref="patron_activities")
    fine = relationship("Fine", backref="patron_activities")
    checkout = relationship("Checkout", backref="patron_activities")
    hold = relationship("Hold", backref="patron_activities")

    # Indexes for common query patterns
    __table_args__ = (
        # Composite index for patron activity timeline queries
        Index("ix_patron_activities_patron_created", "patron_id", "created_at"),
        # Composite index for filtering by type
        Index("ix_patron_activities_patron_type", "patron_id", "activity_type"),
    )
