# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import Enum, StrEnum
from datetime import date

from sqlalchemy import (Boolean, Column, Date, DateTime, Enum, ForeignKey,
                        Integer, String, Text)
from sqlalchemy.orm import relationship
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class DonationStatus(StrEnum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    PROCESSED = "processed"


class DonationRecord(Base, TimestampMixin):

    __tablename__ = "donation_records"

    id = Column(Integer, primary_key=True, index=True)

    # Donor info (optional -- anonymous donations allowed)
    donor_name = Column(String(255), nullable=True)
    donor_email = Column(String(255), nullable=True)
    donor_phone = Column(String(50), nullable=True)
    donor_address = Column(Text, nullable=True)
    is_anonymous = Column(Boolean, nullable=False, default=False)
    tax_receipt_requested = Column(Boolean, nullable=False, default=False)
    tax_receipt_sent = Column(Boolean, nullable=False, default=False)

    # Donation details
    title = Column(String(500), nullable=True)
    author = Column(String(500), nullable=True)
    isbn = Column(String(20), nullable=True)
    material_type = Column(String(50), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    condition_notes = Column(Text, nullable=True)
    estimated_value = Column(Integer, nullable=True)  # cents

    # Workflow
    status = Column(
        Enum(DonationStatus, name="donation_status", values_callable=lambda x: [m.value for m in x]),
        nullable=False,
        default=DonationStatus.PENDING,
    )
    received_date = Column(Date, nullable=False, default=date.today)
    received_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    decline_reason = Column(Text, nullable=True)
    staff_notes = Column(Text, nullable=True)

    # Link to created catalog item (set when PROCESSED)
    catalog_item_id = Column(Integer, ForeignKey("catalog_items.id"), nullable=True)
    item_copy_id = Column(Integer, ForeignKey("item_copies.id"), nullable=True)

    # Relationships
    received_by = relationship("User", foreign_keys=[received_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    catalog_item = relationship("CatalogItem", foreign_keys=[catalog_item_id])
    item_copy = relationship("ItemCopy", foreign_keys=[item_copy_id])
