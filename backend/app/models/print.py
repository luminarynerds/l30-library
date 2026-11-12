# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from decimal import Decimal
from enum import StrEnum
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, JSON, Float
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base


# ============================================================================
# ENUMS
# ============================================================================

class PrintJobStatus(StrEnum):
    submitted = "submitted"       # Job received from device
    queued = "queued"             # Queued for printer
    printing = "printing"         # Currently printing
    completed = "completed"       # Successfully printed
    failed = "failed"             # Print failed (hardware/error)
    cancelled = "cancelled"       # User cancelled
    held = "held"                 # Held at release station (awaiting payment/scan)


class ColorMode(StrEnum):
    blackwhite = "blackwhite"
    color = "color"


class PaperSize(StrEnum):
    letter = "letter"
    legal = "legal"
    a4 = "a4"


class PrinterStatus(StrEnum):
    online = "online"
    offline = "offline"
    error = "error"
    maintenance = "maintenance"
    disabled = "disabled"


class ScanToEmailStatus(StrEnum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"


class PrintRefundStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    completed = "completed"


# ============================================================================
# CORE PRINT MODELS
# ============================================================================

class PrintJob(Base):

    __tablename__ = "print_jobs"

    id = Column(Integer, primary_key=True, index=True)

    # User who submitted the job
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True, index=True  # Anonymous printing support
    )

    # Device/source that submitted the job
    device_id = Column(String(100), nullable=True, index=True)  # MAC address or UUID
    device_name = Column(String(255), nullable=True)  # "John's Laptop", "Lobby Kiosk", etc.
    device_type = Column(String(50), nullable=True)  # "laptop", "phone", "kiosk", "copy_machine"

    # Job identification
    job_name = Column(String(255), nullable=False)  # "resume.pdf", "Flyer 10 copies", etc.
    job_uid = Column(String(100), unique=True, nullable=False, index=True)  # Unique job ID

    # Print specifications
    status = Column(
        SQLEnum(PrintJobStatus, name="printjobstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PrintJobStatus.submitted,
        nullable=False, index=True
    )
    color_mode = Column(
        SQLEnum(ColorMode, name="colormode", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ColorMode.blackwhite,
        nullable=False
    )
    pages = Column(Integer, nullable=False)
    copies = Column(Integer, default=1, nullable=False)
    paper_size = Column(
        SQLEnum(PaperSize, name="papersize", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PaperSize.letter,
        nullable=False
    )
    double_sided = Column(Boolean, default=True, nullable=False)

    # Printer assignment
    printer_id = Column(
        Integer, ForeignKey("printers.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    printer_name = Column(String(255), nullable=True)

    # Cost calculation
    cost = Column(Numeric(10, 2), nullable=False)  # Calculated at submission time
    cost_breakdown = Column(JSON, nullable=True)  # {'pages': 0.50, 'color_surcharge': 0.25, ...}

    # File storage
    file_path = Column(String(500), nullable=True)  # PDF or original file location
    file_size_bytes = Column(Integer, nullable=True)
    file_mime_type = Column(String(100), nullable=True)

    # Preview image for user confirmation
    preview_image_path = Column(String(500), nullable=True)

    # Payment information
    payment_method = Column(String(50), nullable=True)  # 'card', 'cash', 'account_balance'
    payment_processed = Column(Boolean, default=False, nullable=False)
    payment_reference = Column(String(255), nullable=True)  # Transaction ID / receipt number
    payment_amount_charged = Column(Numeric(10, 2), nullable=True)

    # Account balance deduction (if user prepaid for prints)
    account_balance_used = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    # Release station information
    release_station_id = Column(
        Integer, ForeignKey("print_release_stations.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    release_code = Column(String(50), nullable=True, unique=True)  # 4-6 digit code for PIN-less auth
    card_number_scanned = Column(String(20), nullable=True)  # Last 4 digits only for PCI compliance
    release_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Job tracking
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    sent_to_printer_at = Column(DateTime(timezone=True), nullable=True)
    printing_started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Failure tracking
    failure_reason = Column(Text, nullable=True)
    last_error = Column(Text, nullable=True)

    # Metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="print_jobs")
    printer = relationship("Printer", back_populates="jobs")
    release_station = relationship("PrintReleaseStation", back_populates="held_jobs")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_print_jobs_user_status", "user_id", "status"),
        Index("ix_print_jobs_printer_status", "printer_id", "status"),
        Index("ix_print_jobs_submitted_at", "submitted_at"),
        Index("ix_print_jobs_release_code", "release_code"),
    )

    @property
    def total_pages(self) -> int:
        return self.pages * self.copies

    @property
    def is_held(self) -> bool:
        return self.status == PrintJobStatus.held

    @property
    def ready_for_release(self) -> bool:
        return self.status == PrintJobStatus.completed and self.payment_processed


class Printer(Base):

    __tablename__ = "printers"

    id = Column(Integer, primary_key=True, index=True)

    # Printer identification
    name = Column(String(255), nullable=False, unique=True, index=True)  # "Main Floor Printer"
    device_id = Column(String(100), nullable=True, unique=True, index=True)  # SNMP OID or IP
    printer_type = Column(String(50), nullable=False)  # 'inkjet', 'laser', 'copier', 'multifunction'
    model = Column(String(255), nullable=True)  # Brand/model for support

    # Status and location
    status = Column(
        SQLEnum(PrinterStatus, name="printerstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PrinterStatus.online,
        nullable=False, index=True
    )
    location = Column(String(255), nullable=False)  # "2nd Floor East Wing", "Circulation Desk"
    notes = Column(Text, nullable=True)

    # Configuration
    cups_printer_name = Column(String(255), nullable=True)  # For CUPS integration
    ipp_endpoint = Column(String(500), nullable=True)  # IPP (Internet Printing Protocol) endpoint
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    snmp_community = Column(String(100), nullable=True)  # SNMP community string for status

    # Capabilities
    supports_color = Column(Boolean, default=True, nullable=False)
    supports_double_sided = Column(Boolean, default=True, nullable=False)
    supports_paper_sizes = Column(JSON, default=lambda: ["letter", "legal", "a4"])  # Available sizes

    # Supply tracking (toner/ink levels)
    black_toner_level = Column(Float, nullable=True)  # 0-100 percentage
    color_toner_level = Column(Float, nullable=True)  # For color printers
    paper_level = Column(Float, nullable=True)  # 0-100 percentage

    # Alerts
    low_toner_threshold = Column(Float, default=20.0, nullable=False)  # Alert when below 20%
    low_paper_threshold = Column(Float, default=15.0, nullable=False)  # Alert when below 15%
    has_low_toner_alert = Column(Boolean, default=False, nullable=False, index=True)
    has_low_paper_alert = Column(Boolean, default=False, nullable=False, index=True)
    last_alert_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Usage tracking
    total_jobs = Column(Integer, default=0, nullable=False)
    total_pages_printed = Column(Integer, default=0, nullable=False)
    total_color_pages = Column(Integer, default=0, nullable=False)
    total_revenue = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    # Maintenance
    last_maintenance_date = Column(DateTime(timezone=True), nullable=True)
    next_maintenance_due = Column(DateTime(timezone=True), nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False, index=True)

    # Timestamps
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    jobs = relationship("PrintJob", back_populates="printer")

    @property
    def needs_maintenance_alert(self) -> bool:
        return (self.has_low_toner_alert or self.has_low_paper_alert or
                (self.next_maintenance_due and self.next_maintenance_due <= func.now()))


class PrintReleaseStation(Base):

    __tablename__ = "print_release_stations"

    id = Column(Integer, primary_key=True, index=True)

    # Station identification
    name = Column(String(255), nullable=False, unique=True, index=True)  # "Circulation Desk", "2nd Floor Kiosk"
    location = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)

    # Hardware configuration
    card_reader_type = Column(String(50), nullable=False)  # 'magnetic_stripe', 'rfid', 'barcode', 'nfc'
    has_display = Column(Boolean, default=True, nullable=False)  # User-facing display
    has_touchscreen = Column(Boolean, default=False, nullable=False)
    has_cash_payment = Column(Boolean, default=False, nullable=False)  # Cash payment capability
    has_card_payment = Column(Boolean, default=False, nullable=False)  # Card payment (Square, etc.)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_online = Column(Boolean, default=True, nullable=False)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)

    # Settings
    use_pin_code = Column(Boolean, default=True, nullable=False)  # Require PIN entry
    pin_length = Column(Integer, default=4, nullable=False)
    pin_expiration_minutes = Column(Integer, default=60, nullable=False)
    require_payment_before_release = Column(Boolean, default=True, nullable=False)

    # Tracking
    total_jobs_released = Column(Integer, default=0, nullable=False)
    total_payments_collected = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    held_jobs = relationship("PrintJob", back_populates="release_station")


class PrintPricing(Base):

    __tablename__ = "print_pricing"

    id = Column(Integer, primary_key=True, index=True)

    # Pricing per page
    blackwhite_price_per_page = Column(Numeric(10, 4), default=Decimal("0.10"), nullable=False)
    color_price_per_page = Column(Numeric(10, 4), default=Decimal("0.50"), nullable=False)

    # Discounts
    discount_percentage_for_bulk = Column(Integer, default=0, nullable=False)  # 0-100
    bulk_threshold_pages = Column(Integer, default=100, nullable=False)

    # Minimum charge
    minimum_charge = Column(Numeric(10, 2), default=Decimal("0.25"), nullable=False)

    # Double-sided discount (if any)
    double_sided_discount_percentage = Column(Integer, default=0, nullable=False)

    # Copy machine surcharge (if applicable)
    copy_machine_surcharge_percentage = Column(Integer, default=10, nullable=False)

    # Is active
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Effective dates
    effective_from = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    effective_to = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)

    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    created_by = relationship("User")


class PrintQuota(Base):

    __tablename__ = "print_quotas"

    id = Column(Integer, primary_key=True, index=True)

    # User quota
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )

    # Monthly quota
    monthly_pages_limit = Column(Integer, default=100, nullable=False)  # Pages per month
    monthly_dollar_limit = Column(Numeric(10, 2), default=Decimal("10.00"), nullable=False)  # Dollars per month

    # Current month tracking
    pages_used_this_month = Column(Integer, default=0, nullable=False)
    cost_incurred_this_month = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    month_starts_on = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Override for staff
    quota_override_enabled = Column(Boolean, default=False, nullable=False)
    quota_override_reason = Column(String(500), nullable=True)

    # Enforcement
    enforce_quota = Column(Boolean, default=True, nullable=False)
    allow_overage = Column(Boolean, default=False, nullable=False)  # Charge overage fees?, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="print_quota")

    @property
    def pages_remaining(self) -> int:
        return max(0, self.monthly_pages_limit - self.pages_used_this_month)

    @property
    def budget_remaining(self) -> Decimal:
        return max(Decimal("0.00"), self.monthly_dollar_limit - self.cost_incurred_this_month)


class PrintRefund(Base):

    __tablename__ = "print_refunds"

    id = Column(Integer, primary_key=True, index=True)

    # Related job
    print_job_id = Column(
        Integer, ForeignKey("print_jobs.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )

    # User requesting refund
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False, index=True
    )

    # Refund details
    status = Column(
        SQLEnum(PrintRefundStatus, name="printrefundstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PrintRefundStatus.pending,
        nullable=False, index=True
    )
    reason = Column(String(500), nullable=False)  # "Print quality issue", "Hardware failure", etc.
    refund_amount = Column(Numeric(10, 2), nullable=False)
    refund_method = Column(String(50), nullable=False)  # 'card', 'cash', 'account_credit'

    # Notes and documentation
    description = Column(Text, nullable=True)
    photo_evidence_path = Column(String(500), nullable=True)  # Path to photo of failed print

    # Processing, server_default=func.now(), index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    print_job = relationship("PrintJob")
    user = relationship("User", foreign_keys=[user_id], back_populates="print_refunds")
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    completed_by = relationship("User", foreign_keys=[completed_by_id])


class ScanToEmail(Base):

    __tablename__ = "scan_to_emails"

    id = Column(Integer, primary_key=True, index=True)

    # User and destination
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    recipient_email = Column(String(255), nullable=False)

    # Device information
    scanner_device_id = Column(String(100), nullable=True)  # IP or device ID
    scanner_name = Column(String(255), nullable=True)

    # Job details
    job_name = Column(String(255), nullable=False)
    status = Column(
        SQLEnum(ScanToEmailStatus, name="scantoemailstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ScanToEmailStatus.pending,
        nullable=False, index=True
    )

    # File information
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    page_count = Column(Integer, default=1, nullable=False)

    # Email metadata
    email_subject = Column(String(255), nullable=True)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Status tracking, server_default=func.now(), index=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="scan_to_emails")


class PrinterAlert(Base, TimestampMixin):

    __tablename__ = "printer_alerts"

    id = Column(Integer, primary_key=True, index=True)

    # Printer with issue
    printer_id = Column(
        Integer, ForeignKey("printers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Alert details
    alert_type = Column(String(50), nullable=False, index=True)  # 'low_toner', 'low_paper', 'offline', etc.
    severity = Column(String(20), nullable=False)  # 'info', 'warning', 'critical'
    message = Column(String(500), nullable=False)
    resolved = Column(Boolean, default=False, nullable=False, index=True)

    # Tracking
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    printer = relationship("Printer")
    resolved_by = relationship("User")
