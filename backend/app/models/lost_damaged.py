# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, Date, Index
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class LostItemStatus(StrEnum):
    REPORTED = "reported"  # Initial report of lost item
    CONFIRMED = "confirmed"  # Staff confirmed item is lost
    CHARGED = "charged"  # Replacement charge applied to patron
    FOUND = "found"  # Item was found and returned
    WRITTEN_OFF = "written_off"  # Item written off (long-term loss)
    DISPUTE_PENDING = "dispute_pending"  # Patron has disputed the charge


class LostItemType(StrEnum):
    LOST_BY_PATRON = "lost_by_patron"  # Patron reports item lost
    LOST_IN_TRANSIT = "lost_in_transit"  # Lost during ILL or branch transfer
    OVERDUE_CONVERSION = "overdue_conversion"  # Auto-converted from overdue
    CLAIMS_RETURNED = "claims_returned"  # Patron claims they returned it
    MISSING_INVENTORY = "missing_inventory"  # Found missing during inventory audit


class DamagedItemStatus(StrEnum):
    REPORTED = "reported"  # Initial report of damage
    ASSESSMENT_PENDING = "assessment_pending"  # Waiting for staff assessment
    REPAIRABLE = "repairable"  # Can be repaired, sent to mending
    IN_MENDING = "in_mending"  # Currently being repaired
    REPAIRED = "repaired"  # Repair completed, item returned to circulation
    WITHDRAWN = "withdrawn"  # Beyond repair, removed from collection
    CHARGED = "charged"  # Damage charge applied to patron


class DamageSeverity(StrEnum):
    MINOR = "minor"  # Small issues like small tears, marks
    MODERATE = "moderate"  # Noticeable damage affecting usability
    SEVERE = "severe"  # Major damage, may require withdrawal
    TOTAL_LOSS = "total_loss"  # Complete destruction, must withdraw


class ClaimDisputeStatus(StrEnum):
    PENDING = "pending"  # Dispute filed, awaiting review
    UNDER_REVIEW = "under_review"  # Staff is reviewing the claim
    SEARCH_IN_PROGRESS = "search_in_progress"  # Actively searching for item
    APPROVED = "approved"  # Claim approved, charges waived
    DENIED = "denied"  # Claim denied, charges stand
    ITEM_FOUND = "item_found"  # Item was located, dispute resolved


class LostItemRecord(Base):
    __tablename__ = "lost_item_records"

    id = Column(Integer, primary_key=True, index=True)

    # Item and checkout references
    item_copy_id = Column(
        Integer,
        ForeignKey("item_copies.id", ondelete="SET NULL"),
        index=True,
    )
    checkout_id = Column(
        Integer,
        ForeignKey("checkouts.id", ondelete="SET NULL"),
        index=True,
    )
    catalog_item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="SET NULL"),
        index=True,
    )

    # Patron who had the item
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    # Status tracking
    status = Column(
        String(50),
        default=LostItemStatus.REPORTED,
        nullable=False,
    )
    lost_type = Column(
        String(50),
    )

    # Financial tracking
    item_price = Column(Numeric(10, 2))  # Original item price
    processing_fee = Column(Numeric(10, 2))  # Library processing fee
    replacement_cost = Column(Numeric(10, 2))  # Total charge (price + fee)
    fine_id = Column(
        Integer,
        ForeignKey("fines.id", ondelete="SET NULL"),
    )

    # Credit for found items
    credit_amount = Column(Numeric(10, 2))  # Amount credited if found
    credit_fine_id = Column(
        Integer,
        ForeignKey("fines.id", ondelete="SET NULL"),
    )  # Reference to credit/adjustment fine

    # Days overdue when marked lost (for automatic conversion)
    days_overdue_at_loss = Column(Integer)

    # Notes and metadata
    report_notes = Column(Text)  # Initial report notes
    resolution_notes = Column(Text)  # Notes on how it was resolved

    # Timestamps
    reported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    confirmed_at = Column(DateTime(timezone=True))
    charged_at = Column(DateTime(timezone=True))
    found_at = Column(DateTime(timezone=True))
    written_off_at = Column(DateTime(timezone=True))

    # Who handled it
    reported_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    confirmed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Search metadata for inventory tracking
    last_known_location = Column(String(100))
    search_notes = Column(Text)  # Notes from search efforts

    # Metadata

    # Relationships
    item_copy = relationship("ItemCopy", foreign_keys=[item_copy_id])
    checkout = relationship("Checkout", foreign_keys=[checkout_id])
    catalog_item = relationship("CatalogItem", foreign_keys=[catalog_item_id])
    patron = relationship("User", foreign_keys=[patron_id])
    fine = relationship("Fine", foreign_keys=[fine_id])
    credit_fine = relationship("Fine", foreign_keys=[credit_fine_id])
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    confirmed_by = relationship("User", foreign_keys=[confirmed_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])

    # Indexes for common queries
    __table_args__ = (
        Index("ix_lost_item_records_status_type", "status", "lost_type"),
        Index("ix_lost_item_records_patron_status", "patron_id", "status"),
        Index("ix_lost_item_records_reported_at", "reported_at"),
    )


class DamagedItemRecord(Base):
    __tablename__ = "damaged_item_records"

    id = Column(Integer, primary_key=True)

    # Item and checkout references
    item_copy_id = Column(
        Integer,
        ForeignKey("item_copies.id", ondelete="SET NULL"),
        index=True,
    )
    checkout_id = Column(
        Integer,
        ForeignKey("checkouts.id", ondelete="SET NULL"),
        index=True,
    )
    catalog_item_id = Column(
        Integer,
        ForeignKey("catalog_items.id", ondelete="SET NULL"),
        index=True,
    )

    # Patron who had the item (if applicable)
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    # Status tracking
    status = Column(
        String(50),
        default=DamagedItemStatus.REPORTED,
        nullable=False,
    )
    severity = Column(
        String(50),
    )

    # Damage details (can have multiple types)
    damage_types = Column(JSONB)  # List of DamageType values
    damage_description = Column(Text, nullable=False)
    photo_urls = Column(JSONB)  # List of photo URLs

    # Assessment
    assessment_notes = Column(Text)
    is_patron_responsible = Column(Boolean, default=False)
    patron_responsibility_reason = Column(Text)

    # Financial tracking
    estimated_repair_cost = Column(Numeric(10, 2))
    actual_repair_cost = Column(Numeric(10, 2))
    replacement_cost = Column(Numeric(10, 2))  # If withdrawn
    charge_amount = Column(Numeric(10, 2))  # Amount charged to patron
    fine_id = Column(
        Integer,
        ForeignKey("fines.id", ondelete="SET NULL"),
    )

    # Repair tracking
    repair_priority = Column(Integer, default=3)  # 1=urgent, 5=low priority
    repair_notes = Column(Text)
    sent_to_mending_at = Column(DateTime(timezone=True))
    repair_completed_at = Column(DateTime(timezone=True))

    # Withdrawal tracking (if beyond repair)
    withdrawal_reason = Column(Text)
    withdrawn_at = Column(DateTime(timezone=True))

    # Timestamps
    reported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assessed_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))

    # Who handled it
    reported_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    assessed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    repaired_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Metadata

    # Relationships
    item_copy = relationship("ItemCopy", foreign_keys=[item_copy_id])
    checkout = relationship("Checkout", foreign_keys=[checkout_id])
    catalog_item = relationship("CatalogItem", foreign_keys=[catalog_item_id])
    patron = relationship("User", foreign_keys=[patron_id])
    fine = relationship("Fine", foreign_keys=[fine_id])
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    assessed_by = relationship("User", foreign_keys=[assessed_by_id])
    repaired_by = relationship("User", foreign_keys=[repaired_by_id])

    # Indexes for common queries
    __table_args__ = (
        Index("ix_damaged_item_records_status_severity", "status", "severity"),
        Index("ix_damaged_item_records_patron_status", "patron_id", "status"),
        Index("ix_damaged_item_records_reported_at", "reported_at"),
    )


class ClaimsReturnedDispute(Base):
    __tablename__ = "claims_returned_disputes"

    id = Column(Integer, primary_key=True)

    # References
    lost_item_record_id = Column(
        Integer,
        ForeignKey("lost_item_records.id", ondelete="CASCADE"),
    )
    item_copy_id = Column(
        Integer,
        ForeignKey("item_copies.id", ondelete="SET NULL"),
        index=True,
    )
    checkout_id = Column(
        Integer,
        ForeignKey("checkouts.id", ondelete="SET NULL"),
        index=True,
    )
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    # Status
    status = Column(
        String(50),
        default=ClaimDisputeStatus.PENDING,
        nullable=False,
    )

    # Claim details
    patron_statement = Column(Text, nullable=False)
    claimed_return_date = Column(Date)
    claimed_return_location = Column(String(100))

    # Investigation
    investigation_notes = Column(Text)
    search_locations = Column(JSONB)  # List of locations searched
    witnesses_contacted = Column(JSONB)  # Staff/patrons contacted

    # Resolution
    resolution = Column(Text)
    resolution_reason = Column(Text)

    # If approved, track the credit
    credit_amount = Column(Numeric(10, 2))
    credit_fine_id = Column(
        Integer,
        ForeignKey("fines.id", ondelete="SET NULL"),
    )

    # Patron history (for context)
    patron_previous_claims_count = Column(Integer, default=0)
    patron_checkout_history_reviewed = Column(Boolean, default=False)

    # Timestamps
    filed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))

    # Who handled it
    filed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Metadata

    # Relationships
    lost_item_record = relationship("LostItemRecord", backref="disputes")
    item_copy = relationship("ItemCopy", foreign_keys=[item_copy_id])
    checkout = relationship("Checkout", foreign_keys=[checkout_id])
    patron = relationship("User", foreign_keys=[patron_id])
    credit_fine = relationship("Fine", foreign_keys=[credit_fine_id])
    filed_by = relationship("User", foreign_keys=[filed_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])

    # Indexes for common queries
    __table_args__ = (
        Index("ix_claims_disputes_patron_status", "patron_id", "status"),
        Index("ix_claims_disputes_filed_at", "filed_at"),
    )


class MendingQueue(Base):
    __tablename__ = "mending_queue"

    id = Column(Integer, primary_key=True)

    # References
    damaged_item_record_id = Column(
        Integer,
        ForeignKey("damaged_item_records.id", ondelete="CASCADE"),
    )
    item_copy_id = Column(
        Integer,
        ForeignKey("item_copies.id", ondelete="SET NULL"),
    )

    # Queue position and priority
    priority = Column(Integer, default=3, nullable=False)  # 1=urgent, 5=low
    queue_position = Column(Integer)  # Calculated position in queue

    # Repair details
    repair_type = Column(String(100))  # e.g., "rebinding", "page repair", etc.
    repair_instructions = Column(Text)
    materials_needed = Column(Text)
    estimated_time_hours = Column(Numeric(5, 2))

    # Status
    is_in_progress = Column(Boolean, default=False, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)

    # Tracking
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Who handled it
    added_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    completed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Cost tracking
    estimated_cost = Column(Numeric(10, 2))
    actual_cost = Column(Numeric(10, 2))

    # Notes
    notes = Column(Text)
    completion_notes = Column(Text)

    # Metadata

    # Relationships
    damaged_item_record = relationship("DamagedItemRecord", backref="mending_entries")
    item_copy = relationship("ItemCopy", foreign_keys=[item_copy_id])
    added_by = relationship("User", foreign_keys=[added_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    completed_by = relationship("User", foreign_keys=[completed_by_id])

    # Indexes
    __table_args__ = (
        Index("ix_mending_queue_priority_position", "priority", "queue_position"),
        Index("ix_mending_queue_in_progress", "is_in_progress"),
    )


class LostDamagedSettings(Base):
    __tablename__ = "lost_damaged_settings"

    id = Column(Integer, primary_key=True, index=True)

    # Scope (can be system-wide or per-branch)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True, index=True)  # NULL = system-wide

    # Lost item settings
    lost_item_processing_fee = Column(Numeric(10, 2), default=Decimal("5.00"), nullable=False)
    default_replacement_cost = Column(Numeric(10, 2), default=Decimal("25.00"), nullable=False)
    overdue_to_lost_days = Column(Integer, default=30, nullable=False)
    auto_convert_overdue_enabled = Column(Boolean, default=True, nullable=False)

    # Found item credit settings
    found_item_full_credit = Column(Boolean, default=True, nullable=False)  # Credit full amount?
    found_item_credit_percentage = Column(Numeric(5, 2), default=Decimal("100.00"))  # Or percentage
    found_item_grace_period_days = Column(Integer, default=365)  # After this, no credit

    # Damaged item settings
    minor_damage_charge_percentage = Column(Numeric(5, 2), default=Decimal("0.00"))
    moderate_damage_charge_percentage = Column(Numeric(5, 2), default=Decimal("25.00"))
    severe_damage_charge_percentage = Column(Numeric(5, 2), default=Decimal("50.00"))
    total_loss_charge_percentage = Column(Numeric(5, 2), default=Decimal("100.00"))

    # Claims returned settings
    claims_returned_review_days = Column(Integer, default=30)  # Days to search before decision
    max_claims_per_patron_year = Column(Integer, default=3)  # After this, auto-deny

    # Notifications
    notify_patron_on_lost = Column(Boolean, default=True, nullable=False)
    notify_patron_on_damaged_charge = Column(Boolean, default=True, nullable=False)
    notify_patron_on_found = Column(Boolean, default=True, nullable=False)
    notify_staff_on_claims = Column(Boolean, default=True, nullable=False)

    # Tracking
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    created_by = relationship("User")
