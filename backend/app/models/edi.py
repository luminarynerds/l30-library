# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


class EDIStandard(StrEnum):
    EDIFACT = "edifact"  # UN/EDIFACT - most common for international
    X12 = "x12"  # ANSI X12 - common in North America


class EDIMessageType(StrEnum):
    ORDERS = "orders"  # Purchase order
    ORDRSP = "ordrsp"  # Order response
    DESADV = "desadv"  # Despatch advice (shipping notice)
    INVOIC = "invoic"  # Invoice


class TransportProtocol(StrEnum):
    FTP = "ftp"
    SFTP = "sftp"
    FTPS = "ftps"
    AS2 = "as2"
    EMAIL = "email"


class EDITransactionStatus(StrEnum):
    PENDING = "pending"  # Waiting to be sent/processed
    SENT = "sent"  # Message sent, awaiting acknowledgement
    ACKNOWLEDGED = "acknowledged"  # Received ACK from vendor
    PROCESSED = "processed"  # Fully processed
    FAILED = "failed"  # Failed to send/process
    RETRY = "retry"  # Scheduled for retry


class EDIInvoiceStatus(StrEnum):
    PENDING = "pending"  # Not yet reconciled
    MATCHED = "matched"  # Fully matched to PO
    PARTIAL_MATCH = "partial_match"  # Some items matched
    DISPUTED = "disputed"  # Discrepancy found
    APPROVED = "approved"  # Approved for payment
    PAID = "paid"  # Payment processed


class VendorEDIProfile(Base, TimestampMixin):

    __tablename__ = "vendor_edi_profiles"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(
        Integer,
        ForeignKey("vendors.id", ondelete="CASCADE"),
        unique=True,
        index=True
    )

    # EDI Settings
    is_enabled = Column(Boolean, default=False, nullable=False)
    edi_standard = Column(
        String(50),
        default=EDIStandard.EDIFACT,
        nullable=False
    )

    # Identifiers
    sender_id = Column(String(35), nullable=True)  # Our ID (library)
    sender_qualifier = Column(String(4), default="ZZ")  # ID qualifier
    receiver_id = Column(String(35), nullable=True)  # Vendor's EDI ID
    receiver_qualifier = Column(String(4), default="ZZ")

    # Transport Configuration
    transport_protocol = Column(
        String(50),
        default=TransportProtocol.SFTP,
        nullable=False
    )
    transport_host = Column(String(255))
    transport_port = Column(Integer)
    transport_username = Column(String(255))
    transport_password = Column(Text)  # Encrypted
    transport_directory_outbound = Column(String(500), default="/outbound")
    transport_directory_inbound = Column(String(500), default="/inbound")

    # SSH Key for SFTP (encrypted)
    ssh_private_key = Column(Text)

    # Vendor-specific settings (JSON)
    # e.g., {"currency": "USD", "date_format": "CCYYMMDD", "decimal_notation": "."}
    vendor_settings = Column(Text)

    # Message Type Support
    supports_orders = Column(Boolean, default=True, nullable=False)
    supports_ordrsp = Column(Boolean, default=True, nullable=False)
    supports_desadv = Column(Boolean, default=True, nullable=False)
    supports_invoic = Column(Boolean, default=True, nullable=False)

    # Retry Configuration
    max_retries = Column(Integer, default=3)
    retry_interval_minutes = Column(Integer, default=60)

    # Auto-processing settings
    auto_send_orders = Column(Boolean, default=False, nullable=False)
    auto_process_responses = Column(Boolean, default=True, nullable=False)
    auto_approve_invoices = Column(Boolean, default=False, nullable=False)
    invoice_tolerance_percent = Column(Numeric(5, 2), default=Decimal("5.00"))

    # Test mode
    is_test_mode = Column(Boolean, default=True, nullable=False)

    # Metadata
    last_transmission_at = Column(DateTime(timezone=True))
    last_successful_transmission_at = Column(DateTime(timezone=True))

    # Relationships
    vendor = relationship("Vendor", back_populates="edi_profile", uselist=False)
    transactions = relationship("EDITransaction", back_populates="vendor_edi_profile", cascade="all, delete-orphan")


class EDITransaction(Base, TimestampMixin):

    __tablename__ = "edi_transactions"

    id = Column(Integer, primary_key=True, index=True)

    # Reference to vendor EDI profile
    vendor_edi_profile_id = Column(
        Integer,
        ForeignKey("vendor_edi_profiles.id", ondelete="SET NULL"),
        index=True
    )

    # Reference to purchase order (for ORDERS, ORDRSP, DESADV)
    purchase_order_id = Column(
        Integer,
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        index=True
    )

    # Message Details
    message_type = Column(
        String(50),
        index=True
    )
    direction = Column(String(10), nullable=False)  # "outbound" or "inbound"
    interchange_control_number = Column(String(14), unique=True, index=True)
    message_reference_number = Column(String(14))

    # Status
    status = Column(
        String(50),
        default=EDITransactionStatus.PENDING,
        nullable=False,
        index=True
    )

    # Content
    raw_message = Column(Text)  # The actual EDI message
    parsed_data = Column(Text)  # JSON representation of parsed data

    # File tracking
    filename = Column(String(255))
    file_path = Column(String(500))

    # Retry tracking
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime(timezone=True))
    last_error = Column(Text)

    # Timestamps
    sent_at = Column(DateTime(timezone=True))
    received_at = Column(DateTime(timezone=True))
    processed_at = Column(DateTime(timezone=True))

    # Relationships
    vendor_edi_profile = relationship("VendorEDIProfile", back_populates="transactions")
    purchase_order = relationship("PurchaseOrder", back_populates="edi_transactions")
    invoices = relationship("EDIInvoice", back_populates="edi_transaction", cascade="all, delete-orphan")
    shipment_notices = relationship("EDIShipmentNotice", back_populates="edi_transaction", cascade="all, delete-orphan")
    order_responses = relationship("EDIOrderResponse", back_populates="edi_transaction", cascade="all, delete-orphan")


class EDIInvoice(Base, TimestampMixin):

    __tablename__ = "edi_invoices"

    id = Column(Integer, primary_key=True, index=True)

    # Reference to transaction
    edi_transaction_id = Column(
        Integer,
        ForeignKey("edi_transactions.id", ondelete="SET NULL"),
        index=True
    )

    # Reference to purchase order
    purchase_order_id = Column(
        Integer,
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        index=True
    )

    # Vendor reference
    vendor_id = Column(
        Integer,
        ForeignKey("vendors.id", ondelete="SET NULL"),
        index=True
    )

    # Invoice details
    invoice_number = Column(String(50), index=True)
    invoice_date = Column(DateTime(timezone=True))
    due_date = Column(DateTime(timezone=True))

    # Amounts
    subtotal = Column(Numeric(12, 2))
    tax_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    shipping_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    discount_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    total_amount = Column(Numeric(12, 2))

    # Currency
    currency_code = Column(String(3), default="USD")

    # Status
    status = Column(
        String(50),
        default=EDIInvoiceStatus.PENDING,
        nullable=False,
        index=True
    )

    # Reconciliation
    po_total = Column(Numeric(12, 2))  # Original PO total for comparison
    variance_amount = Column(Numeric(12, 2))  # Difference from PO
    variance_reason = Column(Text)  # Explanation for variance
    matched_line_items = Column(Integer, default=0)
    total_line_items = Column(Integer, default=0)

    # Approval (SET NULL: preserve invoice approval history)
    approved_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True
    )
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)

    # Notes
    notes = Column(Text)

    # Raw line items (JSON)
    line_items = Column(Text)

    # Timestamps
    # Relationships
    edi_transaction = relationship("EDITransaction", back_populates="invoices")
    purchase_order = relationship("PurchaseOrder", back_populates="edi_invoices")
    vendor = relationship("Vendor", back_populates="edi_invoices")
    approved_by = relationship("User")


class EDIShipmentNotice(Base, TimestampMixin):

    __tablename__ = "edi_shipment_notices"

    id = Column(Integer, primary_key=True, index=True)

    # Reference to transaction
    edi_transaction_id = Column(
        Integer,
        ForeignKey("edi_transactions.id", ondelete="SET NULL"),
        index=True
    )

    # Reference to purchase order
    purchase_order_id = Column(
        Integer,
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        index=True
    )

    # Vendor reference
    vendor_id = Column(
        Integer,
        ForeignKey("vendors.id", ondelete="SET NULL"),
        index=True
    )

    # Shipment details
    shipment_number = Column(String(50), index=True)
    ship_date = Column(DateTime(timezone=True))
    expected_delivery_date = Column(DateTime(timezone=True))

    # Carrier info
    carrier_name = Column(String(255))
    carrier_code = Column(String(50))
    tracking_number = Column(String(100))

    # Package info
    package_count = Column(Integer, default=1)
    total_weight = Column(Numeric(10, 2))
    weight_unit = Column(String(10), default="LB")

    # Items shipped (JSON)
    shipped_items = Column(Text)
    total_items_shipped = Column(Integer, default=0)

    # Processing status
    is_processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime(timezone=True))

    # Timestamps
    # Relationships
    edi_transaction = relationship("EDITransaction", back_populates="shipment_notices")
    purchase_order = relationship("PurchaseOrder", back_populates="edi_shipment_notices")
    vendor = relationship("Vendor", back_populates="edi_shipment_notices")


class EDIOrderResponse(Base, TimestampMixin):

    __tablename__ = "edi_order_responses"

    id = Column(Integer, primary_key=True, index=True)

    # Reference to transaction
    edi_transaction_id = Column(
        Integer,
        ForeignKey("edi_transactions.id", ondelete="SET NULL"),
        index=True
    )

    # Reference to purchase order
    purchase_order_id = Column(
        Integer,
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        index=True
    )

    # Vendor reference
    vendor_id = Column(
        Integer,
        ForeignKey("vendors.id", ondelete="SET NULL"),
        index=True
    )

    # Response details
    vendor_order_number = Column(String(50))
    response_date = Column(DateTime(timezone=True))

    # Response type
    response_code = Column(String(3))  # 4=Changed, 27=Not accepted, 29=Accepted
    response_description = Column(Text)

    # Item status summary
    items_accepted = Column(Integer, default=0)
    items_rejected = Column(Integer, default=0)
    items_backordered = Column(Integer, default=0)
    items_substituted = Column(Integer, default=0)

    # Expected dates
    expected_ship_date = Column(DateTime(timezone=True))
    expected_delivery_date = Column(DateTime(timezone=True))

    # Line item details (JSON)
    line_items = Column(Text)

    # Processing status
    is_processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime(timezone=True))

    # Timestamps
    # Relationships
    edi_transaction = relationship("EDITransaction", back_populates="order_responses")
    purchase_order = relationship("PurchaseOrder", back_populates="edi_order_responses")
    vendor = relationship("Vendor", back_populates="edi_order_responses")
