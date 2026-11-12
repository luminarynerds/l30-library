# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


class FundStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CLOSED = "closed"


class PurchaseOrderStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUBMITTED = "submitted"
    ORDERED = "ordered"
    SHIPPED = "shipped"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class SelectionPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SelectionSource(StrEnum):
    MANUAL = "manual"
    OPEN_LIBRARY = "open_library"
    GOOGLE_BOOKS = "google_books"


class Fund(Base, TimestampMixin):

    __tablename__ = "funds"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Budget
    fiscal_year = Column(Integer, nullable=False, index=True)
    allocated_amount = Column(Numeric(12, 2), nullable=False, default=0.00)
    encumbered_amount = Column(Numeric(12, 2), default=0.00)
    spent_amount = Column(Numeric(12, 2), default=0.00)

    # Settings
    status = Column(
        String(50),
        default=FundStatus.ACTIVE,
        nullable=False,
    )

    # Relationships
    purchase_orders = relationship("PurchaseOrder", back_populates="fund")
    serial_subscriptions = relationship("SerialSubscription", back_populates="fund")

    @validates("status")
    def validate_status_transition(self, key, value):
        # Only validate on existing objects (not during initial construction)
        if hasattr(self, "_sa_instance_state") and self._sa_instance_state.has_identity:
            if self.status == FundStatus.CLOSED and value != FundStatus.CLOSED:
                raise ValueError(
                    f"Cannot reopen closed fund '{self.code}'. Closed funds are final."
                )
        return value

    @validates("encumbered_amount")
    def validate_encumbered_amount(self, key, value):
        if hasattr(self, "_sa_instance_state") and self._sa_instance_state.has_identity:
            if self.status == FundStatus.CLOSED:
                raise ValueError(
                    f"Cannot modify encumbered amount on closed fund '{self.code}'"
                )
        return value

    @validates("spent_amount")
    def validate_spent_amount(self, key, value):
        if hasattr(self, "_sa_instance_state") and self._sa_instance_state.has_identity:
            if self.status == FundStatus.CLOSED:
                raise ValueError(
                    f"Cannot modify spent amount on closed fund '{self.code}'"
                )
        return value

    @property
    def available_amount(self) -> Decimal:
        return (
            Decimal(str(self.allocated_amount or 0))
            - Decimal(str(self.encumbered_amount or 0))
            - Decimal(str(self.spent_amount or 0))
        )


class Vendor(Base, TimestampMixin):

    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    contact_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    account_number = Column(String(100))
    notes = Column(Text)
    code = Column(String(50))
    website = Column(String(255))
    discount_percentage = Column(Numeric(5, 2))
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")
    edi_profile = relationship("VendorEDIProfile", back_populates="vendor", uselist=False, cascade="all, delete-orphan")
    edi_invoices = relationship("EDIInvoice", back_populates="vendor", cascade="all, delete-orphan")
    edi_shipment_notices = relationship("EDIShipmentNotice", back_populates="vendor", cascade="all, delete-orphan")
    edi_order_responses = relationship("EDIOrderResponse", back_populates="vendor", cascade="all, delete-orphan")
    serial_subscriptions = relationship("SerialSubscription", back_populates="vendor")


class SelectionListStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    ORDERED = "ordered"
    REJECTED = "rejected"


class SelectionListItem(Base, TimestampMixin):

    __tablename__ = "selection_list_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    author = Column(String(255))
    isbn = Column(String(20), index=True)
    cover_url = Column(Text)
    estimated_price = Column(Numeric(10, 2))

    # Source info
    source = Column(
        String(50),
        default=SelectionSource.MANUAL,
    )
    source_id = Column(String(100))  # Open Library key or Google Books ID

    # Priority and tracking
    priority = Column(
        String(50),
        default=SelectionPriority.MEDIUM,
    )
    requested_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notes = Column(Text)

    # Status and purchase request link
    status = Column(String(20), nullable=False, default="pending")
    purchase_request_id = Column(Integer, ForeignKey("patron_purchase_requests.id"), nullable=True)

    # Relationships
    requested_by = relationship("User")


class PurchaseOrder(Base, TimestampMixin):

    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String(50), unique=True, nullable=False, index=True)

    # References
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    fund_id = Column(Integer, ForeignKey("funds.id", ondelete="SET NULL"), nullable=True, index=True)

    # Order Details
    order_date = Column(Date, nullable=False, default=date.today)
    expected_delivery = Column(Date)
    actual_delivery = Column(Date)

    status = Column(
        String(50),
        default=PurchaseOrderStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # Financial
    total_amount = Column(Numeric(12, 2), default=0.00)

    # Notes
    notes = Column(Text)

    # Approval Workflow
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    approved_at = Column(DateTime(timezone=True))
    rejection_notes = Column(Text)

    # Metadata
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)

    # Relationships
    vendor = relationship("Vendor", back_populates="purchase_orders")
    fund = relationship("Fund", back_populates="purchase_orders")
    items = relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        cascade="all, delete-orphan",
    )
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    edi_transactions = relationship("EDITransaction", back_populates="purchase_order", cascade="all, delete-orphan")
    edi_invoices = relationship("EDIInvoice", back_populates="purchase_order", cascade="all, delete-orphan")
    edi_shipment_notices = relationship("EDIShipmentNotice", back_populates="purchase_order", cascade="all, delete-orphan")
    edi_order_responses = relationship("EDIOrderResponse", back_populates="purchase_order", cascade="all, delete-orphan")

    @property
    def vendor_name(self) -> str | None:
        return self.vendor.name if self.vendor else None

    @property
    def fund_name(self) -> str | None:
        return self.fund.name if self.fund else None

    @property
    def total_items(self) -> int:
        if not self.items:
            return 0
        return sum(item.quantity for item in self.items)

    @property
    def has_backorders(self) -> bool:
        """Derived from line items -- no BACKORDERED PurchaseOrderStatus.

        A dedicated status would overlap the existing partial-received
        state and risk bugs in the fund/cancel logic in
        _process_order_response (spec decision, 2026-06-17).
        """
        if not self.items:
            return False
        return any((item.backordered_quantity or 0) > 0 for item in self.items)


class PurchaseOrderItem(Base, TimestampMixin):

    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(
        Integer,
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Item Details
    title = Column(String(500), nullable=False)
    author = Column(String(255))
    isbn = Column(String(50))

    # Quantities & Pricing
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0.00)
    received_quantity = Column(Integer, default=0)

    notes = Column(Text)
    # EDI backorder tracking (populated from ORDRSP order responses;
    # see services/edi/edi_processor.py _process_order_response)
    backordered_quantity = Column(Integer, nullable=True)
    expected_ship_date = Column(Date, nullable=True)
    last_status_at = Column(DateTime(timezone=True), nullable=True)
    # Link to catalog on receipt
    catalog_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    catalog_item = relationship("CatalogItem")

    @property
    def line_total(self) -> Decimal:
        return Decimal(str(self.quantity or 0)) * Decimal(str(self.unit_price or 0))

    @property
    def is_fully_received(self) -> bool:
        return (self.received_quantity or 0) >= (self.quantity or 0)


class OrderTemplate(Base, TimestampMixin):

    __tablename__ = "order_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Default vendor and fund for orders created from this template
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    fund_id = Column(Integer, ForeignKey("funds.id", ondelete="SET NULL"), nullable=True, index=True)

    # Creator and sharing
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    is_shared = Column(Boolean, default=False, nullable=False)

    # Template items stored as JSON array
    # Each item: {"title": str, "author": str|null, "isbn": str|null, "quantity": int, "unit_price": Decimal|null, "notes": str|null}
    template_items = Column(Text)  # JSON stored as text for SQLite compatibility

    # Relationships
    vendor = relationship("Vendor")
    fund = relationship("Fund")
    created_by = relationship("User")
