# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Index
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


class PurchaseRequestStatus(StrEnum):
    PENDING = "pending"           # Submitted by patron, awaiting review
    UNDER_REVIEW = "under_review" # Staff is reviewing
    APPROVED = "approved"         # Staff approved, will order
    ORDERED = "ordered"           # PO created / item ordered
    RECEIVED = "received"         # Item arrived at library
    DECLINED = "declined"         # Staff declined the request
    CANCELLED = "cancelled"       # Patron cancelled their request


class RequestMaterialType(StrEnum):
    BOOK = "book"
    AUDIOBOOK = "audiobook"
    EBOOK = "ebook"
    DVD = "dvd"
    CD = "cd"
    MAGAZINE = "magazine"
    OTHER = "other"


class PatronPurchaseRequest(Base, TimestampMixin):

    __tablename__ = "patron_purchase_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Patron who submitted
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Requested material info
    title = Column(String(500), nullable=False)
    author = Column(String(255))
    isbn = Column(String(20), index=True)
    material_type = Column(
        String(50),
        default=RequestMaterialType.BOOK,
        nullable=False,
    )
    publisher = Column(String(255))
    publication_year = Column(Integer)
    patron_notes = Column(Text)  # Why they want it

    # Status workflow
    status = Column(
        String(50),
        default=PurchaseRequestStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Staff review
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reviewed_at = Column(DateTime(timezone=True))
    staff_notes = Column(Text)  # Internal staff notes
    decline_reason = Column(Text)  # Reason shown to patron on decline

    # Duplicate detection
    duplicate_of_catalog_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)
    duplicate_check_done = Column(Boolean, default=False, nullable=False)

    # External review source data (auto-checked)
    review_source_rating = Column(Float)  # Average rating from external sources
    review_source_data = Column(Text)     # JSON: summary of external reviews
    review_source_checked = Column(Boolean, default=False, nullable=False)

    # Link to purchase order when ordered
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True, index=True)

    # Notification tracking
    ordered_notified = Column(Boolean, default=False, nullable=False)
    received_notified = Column(Boolean, default=False, nullable=False)

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    duplicate_of_catalog = relationship("CatalogItem")
    purchase_order = relationship("PurchaseOrder")

    __table_args__ = (
        Index("ix_purchase_request_patron_status", "patron_id", "status"),
        Index("ix_purchase_request_title_author", "title", "author"),
    )

    @property
    def patron_name(self) -> str | None:
        return self.patron.full_name if self.patron else None

    @property
    def reviewer_name(self) -> str | None:
        return self.reviewed_by.full_name if self.reviewed_by else None


class DeclineReasonTemplate(Base, TimestampMixin):

    __tablename__ = "decline_reason_templates"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(100), nullable=False, unique=True)  # Short name for staff
    message = Column(Text, nullable=False)  # Full message shown to patron
    is_active = Column(Boolean, default=True, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)

    # Who created it
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    created_by = relationship("User")
