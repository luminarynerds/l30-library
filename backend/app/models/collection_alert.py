# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from datetime import datetime
from sqlalchemy import Column, DateTime, Index, Integer, String, Text, Enum as SQLEnum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base


class AlertType(StrEnum):
    LAST_COPY_CHECKOUT = "last_copy_checkout"  # Only 1 copy available
    HIGH_DEMAND_HOLD = "high_demand_hold"  # Placing hold on item with 3+ holds
    LOW_INVENTORY = "low_inventory"  # Less than 3 copies total or 0 in branch
    NON_CIRCULATING = "non_circulating"  # No checkouts in 12+ months
    LONG_HOLD_QUEUE = "long_hold_queue"  # 5+ items waiting


class CollectionAlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CollectionAlertStatus(StrEnum):
    ACTIVE = "active"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


class CollectionAlert(Base, TimestampMixin):
    __tablename__ = "collection_alerts"
    __table_args__ = (
        Index("ix_collection_alerts_item_type_status", "catalog_item_id", "alert_type", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # What item/alert is this about
    catalog_item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Alert classification
    alert_type = Column(
        String(50),
        nullable=False, index=True
    )
    severity = Column(
        String(50),
        default=CollectionAlertSeverity.WARNING, nullable=False
    )
    status = Column(
        String(50),
        default=CollectionAlertStatus.ACTIVE, nullable=False, index=True
    )

    # Context-specific data (JSON would be better, but using text for simplicity)
    # Examples:
    # last_copy_checkout: {"available_copies": 1, "total_copies": 5}
    # high_demand_hold: {"hold_count": 4, "available_copies": 2}
    # low_inventory: {"available_copies": 1, "total_copies": 3, "branch": "Main"}
    # non_circulating: {"months_since_checkout": 15, "last_checkout_date": "2022-11-15"}
    # long_hold_queue: {"pending_holds": 7, "available_copies": 2}
    context_data = Column(Text, nullable=True)

    # Location-specific alerts (for low_inventory and branch-specific alerts)
    location = Column(String(100), nullable=True, index=True)

    # Timestamps
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    catalog_item = relationship("CatalogItem")
    dismissed_by = relationship("User")

