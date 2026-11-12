# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from decimal import Decimal

from sqlalchemy import Column, Date, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class RepairType(StrEnum):
    in_house_repair = "in_house_repair"
    bindery = "bindery"
    rebinding = "rebinding"
    replacement_cover = "replacement_cover"
    page_repair = "page_repair"
    spine_repair = "spine_repair"


class RepairStatus(StrEnum):
    assessed = "assessed"
    approved = "approved"
    in_repair = "in_repair"
    at_bindery = "at_bindery"
    returned = "returned"
    completed = "completed"
    withdrawn = "withdrawn"


VALID_REPAIR_TRANSITIONS = {
    "assessed": ["approved", "withdrawn"],
    "approved": ["in_repair", "at_bindery", "withdrawn"],
    "in_repair": ["returned", "completed", "withdrawn"],
    "at_bindery": ["returned"],
    "returned": ["completed", "in_repair"],
    "completed": [],
    "withdrawn": [],
}


class RepairRecord(Base, TimestampMixin):
    __tablename__ = "repair_records"

    id = Column(Integer, primary_key=True, index=True)
    catalog_item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    reported_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    repair_type = Column(
        String(50),
        nullable=False,
    )
    status = Column(
        String(50),
        nullable=False, default=RepairStatus.assessed,
    )
    damage_description = Column(Text, nullable=True)
    repair_notes = Column(Text, nullable=True)
    estimated_cost = Column(Numeric(10, 2), nullable=True)
    actual_cost = Column(Numeric(10, 2), nullable=True)
    fund_id = Column(
        Integer, ForeignKey("funds.id", ondelete="SET NULL"), nullable=True,
    )
    vendor_id = Column(
        Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True,
    )
    sent_date = Column(Date, nullable=True)
    expected_return_date = Column(Date, nullable=True)
    returned_date = Column(Date, nullable=True)
    completed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    completed_date = Column(Date, nullable=True)

    # Relationships
    catalog_item = relationship("CatalogItem", foreign_keys=[catalog_item_id])
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    completed_by = relationship("User", foreign_keys=[completed_by_id])
    fund = relationship("Fund", foreign_keys=[fund_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])

    __table_args__ = (
        Index("ix_repair_records_status", "status"),
        Index("ix_repair_records_item_status", "catalog_item_id", "status"),
    )
