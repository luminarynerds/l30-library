# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, JSON
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class PrintNoticeType(StrEnum):
    OVERDUE = "overdue"
    FINE = "fine"
    HOLD_READY = "hold_ready"
    ACCOUNT_EXPIRING = "account_expiring"
    ACCOUNT_BLOCKED = "account_blocked"
    WELCOME = "welcome"
    CUSTOM = "custom"
    # CIPA compliance notice types
    INTERNET_SAFETY_POLICY = "internet_safety_policy"
    COMPUTER_USE_RULES = "computer_use_rules"
    MINOR_SUPERVISION_NOTICE = "minor_supervision_notice"
    FILTERING_DISCLOSURE = "filtering_disclosure"
    AUP_VIOLATION = "aup_violation"


class PrintNoticeStatus(StrEnum):
    PENDING = "pending"          # Awaiting batch
    BATCHED = "batched"          # Added to batch for printing
    PRINTED = "printed"          # Batch has been printed
    MAILED = "mailed"            # Notice has been mailed
    DELIVERED = "delivered"      # Confirmed delivery
    RETURNED = "returned"        # Mail returned undeliverable
    CANCELLED = "cancelled"      # Notice cancelled


class PrintNoticeBatchStatus(StrEnum):
    OPEN = "open"                # Accepting notices
    CLOSED = "closed"            # No longer accepting, awaiting print
    PRINTING = "printing"        # Currently being printed
    PRINTED = "printed"          # Printed, ready for mailing
    MAILED = "mailed"            # All notices mailed
    COMPLETED = "completed"      # Process complete


class PrintNotice(Base):

    __tablename__ = "print_notices"

    id = Column(Integer, primary_key=True, index=True)

    # Patron who receives the notice
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Notice type and status
    notice_type = Column(
        SQLEnum(PrintNoticeType, name="printnoticetype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True
    )
    status = Column(
        SQLEnum(PrintNoticeStatus, name="printnoticestatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PrintNoticeStatus.PENDING,
        nullable=False, index=True
    )

    # Batch reference (set when notice is batched)
    batch_id = Column(
        Integer, ForeignKey("print_notice_batches.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # Merge group: notices with same merge_key get combined into one mailing
    merge_key = Column(String(100), nullable=True, index=True)

    # Recipient address (snapshot at time of notice creation)
    recipient_name = Column(String(200), nullable=False)
    address_line1 = Column(String(100), nullable=False)
    address_line2 = Column(String(100), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=False)
    country = Column(String(50), default="USA", nullable=False)

    # Notice content
    subject = Column(String(255), nullable=False)
    body_html = Column(Text, nullable=False)

    # Context data for template rendering
    context_data = Column(JSON, nullable=True)

    # Related records (for linking to specific items/fines/holds)
    checkout_id = Column(
        Integer, ForeignKey("checkouts.id", ondelete="SET NULL"),
        nullable=True
    )
    hold_id = Column(
        Integer, ForeignKey("holds.id", ondelete="SET NULL"),
        nullable=True
    )
    fine_id = Column(
        Integer, ForeignKey("fines.id", ondelete="SET NULL"),
        nullable=True
    )

    # PDF storage (generated when batch is printed)
    pdf_file_path = Column(String(500), nullable=True)
    pdf_generated_at = Column(DateTime(timezone=True), nullable=True)

    # Cost tracking (individual notice cost)
    print_cost = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    postage_cost = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    pages = Column(Integer, default=1, nullable=False)

    # Tracking timestamps
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    printed_at = Column(DateTime(timezone=True), nullable=True)
    mailed_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    returned_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Return mail info
    return_reason = Column(String(255), nullable=True)

    # Staff who processed
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    printed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    mailed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id])
    batch = relationship("PrintNoticeBatch", back_populates="notices")
    created_by = relationship("User", foreign_keys=[created_by_id])
    printed_by = relationship("User", foreign_keys=[printed_by_id])
    mailed_by = relationship("User", foreign_keys=[mailed_by_id])

    @property
    def total_cost(self) -> Decimal:
        return self.print_cost + self.postage_cost

    @property
    def full_address(self) -> str:
        lines = [self.recipient_name, self.address_line1]
        if self.address_line2:
            lines.append(self.address_line2)
        lines.append(f"{self.city}, {self.state} {self.zip_code}")
        if self.country and self.country != "USA":
            lines.append(self.country)
        return "\n".join(lines)


class PrintNoticeBatch(Base):

    __tablename__ = "print_notice_batches"

    id = Column(Integer, primary_key=True, index=True)

    # Batch identification
    batch_number = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)  # Optional friendly name

    status = Column(
        SQLEnum(PrintNoticeBatchStatus, name="printnoticebatchstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=PrintNoticeBatchStatus.OPEN,
        nullable=False, index=True
    )

    # Batch configuration
    notice_types = Column(JSON, nullable=True)  # Filter by notice type
    auto_close_at = Column(DateTime(timezone=True), nullable=True)  # Auto-close time

    # Counts and totals
    notice_count = Column(Integer, default=0, nullable=False)
    page_count = Column(Integer, default=0, nullable=False)

    # Cost tracking
    total_print_cost = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    total_postage_cost = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    # PDF for entire batch
    merged_pdf_path = Column(String(500), nullable=True)
    manifest_pdf_path = Column(String(500), nullable=True)

    # Timestamps
    opened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    printed_at = Column(DateTime(timezone=True), nullable=True)
    mailed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Staff tracking
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    closed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    printed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    mailed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Notes
    notes = Column(Text, nullable=True)

    # Relationships
    notices = relationship("PrintNotice", back_populates="batch")
    created_by = relationship("User", foreign_keys=[created_by_id])
    closed_by = relationship("User", foreign_keys=[closed_by_id])
    printed_by = relationship("User", foreign_keys=[printed_by_id])
    mailed_by = relationship("User", foreign_keys=[mailed_by_id])

    @property
    def total_cost(self) -> Decimal:
        return self.total_print_cost + self.total_postage_cost


class PrintNoticeCostConfig(Base):

    __tablename__ = "print_notice_cost_config"

    id = Column(Integer, primary_key=True, index=True)

    # Cost per page for printing
    cost_per_page = Column(Numeric(10, 4), default=Decimal("0.05"), nullable=False)

    # Postage rates by weight/size
    first_class_letter = Column(Numeric(10, 2), default=Decimal("0.68"), nullable=False)
    first_class_large_envelope = Column(Numeric(10, 2), default=Decimal("1.50"), nullable=False)
    presort_standard = Column(Numeric(10, 2), default=Decimal("0.45"), nullable=False)

    # Pages threshold for large envelope
    large_envelope_page_threshold = Column(Integer, default=6, nullable=False)

    # Active configuration flag (only one should be active)
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


class PrintNoticeHistory(Base):

    __tablename__ = "print_notice_history"

    id = Column(Integer, primary_key=True, index=True)

    # Original notice reference
    notice_id = Column(Integer, nullable=True, index=True)
    batch_id = Column(Integer, nullable=True, index=True)

    # Patron (preserved even if user deleted)
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    patron_name = Column(String(200), nullable=False)
    patron_library_card = Column(String(50), nullable=True)

    # Notice details
    notice_type = Column(
        SQLEnum(PrintNoticeType, name="printnoticetype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True
    )
    subject = Column(String(255), nullable=False)

    # Address at time of mailing
    mailing_address = Column(Text, nullable=False)

    # Outcome
    final_status = Column(String(50), nullable=False)
    mailed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    returned = Column(Boolean, default=False, nullable=False)
    return_reason = Column(String(255), nullable=True)

    # Cost
    total_cost = Column(Numeric(10, 2), nullable=False)

    # Context for record keeping
    context_summary = Column(Text, nullable=True)

    # Relationships
    patron = relationship("User")
