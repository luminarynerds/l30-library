# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, Index, Integer,
    Numeric, String, Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ILLRequestStatus(StrEnum):
    pending = "pending"                # Patron submitted, awaiting staff review
    searching = "searching"            # Auto-searching partner libraries
    located = "located"                # Item found at partner library
    not_found = "not_found"            # Could not locate at any partner
    submitted = "submitted"            # Request sent to lending library
    approved = "approved"              # Lending library approved
    denied = "denied"                  # Lending library denied
    in_transit = "in_transit"          # Item shipped to borrowing library
    received = "received"              # Borrowing library received item
    checked_out = "checked_out"        # Patron has item
    returned = "returned"              # Patron returned to borrowing library
    return_in_transit = "return_in_transit"  # Item shipped back to lender
    completed = "completed"            # Item received back by lending library
    cancelled = "cancelled"            # Request cancelled
    lost = "lost"                      # Item lost during ILL process


class ILLRequestType(StrEnum):
    borrow = "borrow"
    lend = "lend"


class PartnerLibraryStatus(StrEnum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class ShippingMethod(StrEnum):
    usps = "usps"
    ups = "ups"
    fedex = "fedex"
    courier = "courier"
    digital = "digital"


class ILLCostCategory(StrEnum):
    shipping = "shipping"
    lending_fee = "lending_fee"
    photocopy = "photocopy"
    processing = "processing"
    lost_item = "lost_item"
    damage = "damage"
    other = "other"


# ---------------------------------------------------------------------------
# Partner Library
# ---------------------------------------------------------------------------

class PartnerLibrary(Base, TimestampMixin):
    __tablename__ = "ill_partner_libraries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    country = Column(String(100), default="US")
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    website = Column(String(500), nullable=True)

    # Integration
    ils_type = Column(String(100), nullable=True)  # e.g. "Koha", "Sierra", "Evergreen"
    z3950_host = Column(String(255), nullable=True)
    z3950_port = Column(Integer, nullable=True)
    z3950_database = Column(String(100), nullable=True)
    ncip_endpoint = Column(String(500), nullable=True)

    # Reciprocal lending terms
    status = Column(
        SQLEnum(PartnerLibraryStatus, name="partnerlibrarystatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PartnerLibraryStatus.active,
        nullable=False,
    )
    lending_fee = Column(Numeric(10, 2), default=0, nullable=False)
    borrowing_fee = Column(Numeric(10, 2), default=0, nullable=False)
    max_loan_days = Column(Integer, default=21)
    max_renewals = Column(Integer, default=1)
    reciprocal_agreement = Column(Boolean, default=False)
    agreement_expires_at = Column(Date, nullable=True)

    notes = Column(Text, nullable=True)

    # Relationships
    ill_requests = relationship("ILLRequest", back_populates="partner_library")

    __table_args__ = (
        Index("ix_ill_partner_status", "status"),
    )


# ---------------------------------------------------------------------------
# ILL Request
# ---------------------------------------------------------------------------

class ILLRequest(Base, TimestampMixin):
    __tablename__ = "ill_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Who is requesting
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    staff_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # What type (borrow from / lend to partner)
    request_type = Column(
        SQLEnum(ILLRequestType, name="illrequesttype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Partner library
    partner_library_id = Column(
        Integer, ForeignKey("ill_partner_libraries.id", ondelete="SET NULL"), nullable=True
    )

    # Catalog item reference (nullable – item may not be in our catalog)
    catalog_item_id = Column(
        Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True
    )

    # Requested material description (for items not in our catalog)
    title = Column(String(500), nullable=False)
    author = Column(String(500), nullable=True)
    isbn = Column(String(30), nullable=True)
    issn = Column(String(30), nullable=True)
    publication_year = Column(String(10), nullable=True)
    edition = Column(String(100), nullable=True)
    volume = Column(String(100), nullable=True)
    material_type = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    patron_notes = Column(Text, nullable=True)

    # Status tracking
    status = Column(
        SQLEnum(ILLRequestStatus, name="illrequeststatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ILLRequestStatus.pending,
        nullable=False,
    )

    # Pickup / return
    pickup_branch_id = Column(
        Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True
    )

    # Dates
    needed_by = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    checked_out_at = Column(DateTime(timezone=True), nullable=True)
    returned_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Shipping
    shipping_method = Column(
        SQLEnum(ShippingMethod, name="illshippingmethod", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    outbound_tracking = Column(String(255), nullable=True)
    return_tracking = Column(String(255), nullable=True)

    # Cost
    estimated_cost = Column(Numeric(10, 2), default=0)
    actual_cost = Column(Numeric(10, 2), default=0)

    # Renewal
    renewal_count = Column(Integer, default=0, nullable=False)
    max_renewals = Column(Integer, default=1, nullable=False)

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id], backref="ill_requests_as_patron")
    staff = relationship("User", foreign_keys=[staff_id])
    partner_library = relationship("PartnerLibrary", back_populates="ill_requests")
    catalog_item = relationship("CatalogItem")
    pickup_branch = relationship("Branch")
    tracking_updates = relationship(
        "ILLTrackingUpdate", back_populates="ill_request",
        order_by="ILLTrackingUpdate.created_at.desc()"
    )
    cost_records = relationship("ILLCostRecord", back_populates="ill_request")

    __table_args__ = (
        Index("ix_ill_requests_patron_status", "patron_id", "status"),
        Index("ix_ill_requests_partner_status", "partner_library_id", "status"),
        Index("ix_ill_requests_status", "status"),
        Index("ix_ill_requests_due_date", "due_date"),
    )


# ---------------------------------------------------------------------------
# Tracking Updates
# ---------------------------------------------------------------------------

class ILLTrackingUpdate(Base, TimestampMixin):
    __tablename__ = "ill_tracking_updates"

    id = Column(Integer, primary_key=True, index=True)
    ill_request_id = Column(
        Integer, ForeignKey("ill_requests.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(
        SQLEnum(ILLRequestStatus, name="illrequeststatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    message = Column(Text, nullable=False)
    is_patron_visible = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    ill_request = relationship("ILLRequest", back_populates="tracking_updates")
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_ill_tracking_request", "ill_request_id"),
    )


# ---------------------------------------------------------------------------
# Cost Records
# ---------------------------------------------------------------------------

class ILLCostRecord(Base, TimestampMixin):
    __tablename__ = "ill_cost_records"

    id = Column(Integer, primary_key=True, index=True)
    ill_request_id = Column(
        Integer, ForeignKey("ill_requests.id", ondelete="CASCADE"), nullable=False
    )
    category = Column(
        SQLEnum(ILLCostCategory, name="illcostcategory", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    description = Column(String(500), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    is_invoiced = Column(Boolean, default=False, nullable=False)
    invoiced_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    ill_request = relationship("ILLRequest", back_populates="cost_records")
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_ill_cost_request", "ill_request_id"),
    )
