# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, Index
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class FoundItemStatus(StrEnum):
    LOGGED = "logged"  # Staff logged the found item
    WAITING_CLAIM = "waiting_claim"  # Waiting for patron to claim
    CLAIMED = "claimed"  # Patron has claimed the item
    VERIFIED = "verified"  # Claim verified, item returned to patron
    DONATED = "donated"  # Item donated after retention period
    DISPOSED = "disposed"  # Item disposed after retention period
    UNCLAIMED = "unclaimed"  # Retention period expired, not claimed


class MatchConfidenceLevel(StrEnum):
    LOW = "low"  # 25-50% match score
    MEDIUM = "medium"  # 50-75% match score
    HIGH = "high"  # 75-90% match score
    VERY_HIGH = "very_high"  # 90%+ match score


class ClaimVerificationStatus(StrEnum):
    PENDING = "pending"  # Claim filed, waiting for verification
    UNDER_REVIEW = "under_review"  # Staff reviewing the claim
    APPROVED = "approved"  # Claim approved, item returned
    REJECTED = "rejected"  # Claim rejected, item not returned
    AWAITING_PICKUP = "awaiting_pickup"  # Verified, waiting for patron pickup


class DisposalMethod(StrEnum):
    DONATED_TO_CHARITY = "donated_to_charity"
    DONATED_TO_SCHOOL = "donated_to_school"
    DONATED_TO_COMMUNITY = "donated_to_community"
    RECYCLED = "recycled"
    DISCARDED = "discarded"
    STAFF_BENEFIT = "staff_benefit"


class FoundItem(Base):
    __tablename__ = "found_items"

    id = Column(Integer, primary_key=True, index=True)

    # Item identification and description
    description = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False)  # e.g., "jacket", "book", "glasses", etc.
    color = Column(String(100), nullable=True)
    brand_or_label = Column(String(200), nullable=True)
    size = Column(String(50), nullable=True)
    condition = Column(String(200), nullable=True)  # e.g., "good", "worn", "damaged"
    additional_details = Column(Text, nullable=True)

    # Location information
    location_found = Column(String(200), nullable=False)  # e.g., "circulation desk", "study room 3"
    location_details = Column(Text, nullable=True)  # More detailed location info
    date_found = Column(DateTime(timezone=True), nullable=False)

    # Storage information
    storage_location_id = Column(
        Integer,
        ForeignKey("found_item_storage_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    secure_storage_flag = Column(Boolean, default=False)  # For valuable items
    estimated_value = Column(Numeric(10, 2), nullable=True)

    # Status tracking
    status = Column(
        String(50),
        default=FoundItemStatus.LOGGED,
        nullable=False,
    )

    # Retention and disposition
    retention_period_days = Column(Integer, default=30, nullable=False)
    retention_end_date = Column(DateTime(timezone=True), nullable=False)
    disposal_method = Column(
        String(50),
        nullable=True,
    )
    disposed_at = Column(DateTime(timezone=True), nullable=True)
    disposal_notes = Column(Text, nullable=True)

    # Who found it and staff notes
    found_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    staff_notes = Column(Text, nullable=True)
    logged_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps, server_default=func.now(), nullable=False)
    storage_moved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    found_by = relationship("User", foreign_keys=[found_by_id])
    logged_by = relationship("User", foreign_keys=[logged_by_id])
    storage_location = relationship("FoundItemStorageLocation", back_populates="items")
    photos = relationship("FoundItemPhoto", back_populates="found_item", cascade="all, delete-orphan")
    matches = relationship("FoundItemMatch", back_populates="found_item", cascade="all, delete-orphan")
    claim = relationship(
        "FoundItemClaimVerification",
        back_populates="found_item",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_found_items_status", "status"),
        Index("ix_found_items_date_found", "date_found"),
        Index("ix_found_items_retention_end", "retention_end_date"),
        Index("ix_found_items_secure_storage", "secure_storage_flag"),
        Index("ix_found_items_found_by", "found_by_id"),
        Index("ix_found_items_status_retention", "status", "retention_end_date"),
    )


class FoundItemPhoto(Base):
    __tablename__ = "found_item_photos"

    id = Column(Integer, primary_key=True, index=True)

    # References
    found_item_id = Column(
        Integer,
        ForeignKey("found_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Photo information
    photo_url = Column(String(500), nullable=False)
    photo_key = Column(String(200), nullable=False)  # Storage backend key
    upload_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_primary = Column(Boolean, default=False)  # Mark primary/thumbnail photo

    # Metadata
    photo_notes = Column(Text, nullable=True)

    # Timestamps, server_default=func.now(), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    found_item = relationship("FoundItem", back_populates="photos")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

    __table_args__ = (
        Index("ix_found_item_photos_found_item", "found_item_id"),
        Index("ix_found_item_photos_primary", "found_item_id", "is_primary"),
    )


class FoundItemStorageLocation(Base):
    __tablename__ = "found_item_storage_locations"

    id = Column(Integer, primary_key=True, index=True)

    # Location information
    location_name = Column(String(200), nullable=False)  # e.g., "Lost & Found Shelf A"
    location_code = Column(String(50), nullable=False, unique=True)  # e.g., "LF-A-001"
    description = Column(Text, nullable=True)
    branch = Column(String(100), nullable=True)  # For multi-branch systems

    # Capacity tracking
    max_items = Column(Integer, nullable=True)
    current_item_count = Column(Integer, default=0, nullable=False)

    # Security
    is_secure_storage = Column(Boolean, default=False)  # For valuable items
    requires_verification = Column(Boolean, default=False)  # Requires identity check
    access_restricted = Column(Boolean, default=False)  # Only certain staff can access

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps, server_default=func.now(), nullable=False)

    # Relationships
    items = relationship("FoundItem", back_populates="storage_location")

    __table_args__ = (
        Index("ix_storage_locations_code", "location_code"),
        Index("ix_storage_locations_secure", "is_secure_storage"),
        Index("ix_storage_locations_active", "is_active"),
    )


class FoundItemMatch(Base):
    __tablename__ = "found_item_matches"

    id = Column(Integer, primary_key=True, index=True)

    # References
    found_item_id = Column(
        Integer,
        ForeignKey("found_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lost_item_record_id = Column(
        Integer,
        ForeignKey("lost_item_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Match scoring
    confidence_level = Column(
        String(50),
        default=MatchConfidenceLevel.MEDIUM,
        nullable=False,
    )
    match_score = Column(Numeric(5, 2), nullable=False)  # 0-100 percentage

    # Matching factors (JSONB for flexibility)
    matching_factors = Column(JSONB, nullable=True)  # e.g., {"color": 90, "size": 85, "category": 100}
    non_matching_factors = Column(JSONB, nullable=True)  # e.g., {"brand": "different"}

    # Match status
    is_confirmed = Column(Boolean, default=False)
    confirmation_notes = Column(Text, nullable=True)

    # Notification tracking
    patron_notified = Column(Boolean, default=False)
    patron_notified_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps, server_default=func.now(), nullable=False)

    # Who confirmed/rejected the match
    confirmed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    found_item = relationship("FoundItem", back_populates="matches")
    lost_item_record = relationship("LostItemRecord")
    confirmed_by = relationship("User", foreign_keys=[confirmed_by_id])

    __table_args__ = (
        Index("ix_found_item_matches_found_item", "found_item_id"),
        Index("ix_found_item_matches_lost_item", "lost_item_record_id"),
        Index("ix_found_item_matches_confidence", "confidence_level"),
        Index("ix_found_item_matches_confirmed", "is_confirmed"),
    )


class FoundItemClaimVerification(Base):
    __tablename__ = "found_item_claim_verifications"

    id = Column(Integer, primary_key=True, index=True)

    # References
    found_item_id = Column(
        Integer,
        ForeignKey("found_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Claim details
    claim_statement = Column(Text, nullable=False)  # How patron describes the item
    date_claimed = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Verification status
    status = Column(
        String(50),
        default=ClaimVerificationStatus.PENDING,
        nullable=False,
    )

    # Identity verification
    identity_verified = Column(Boolean, default=False)
    verification_method = Column(String(100), nullable=True)  # e.g., "library card", "photo id"
    verification_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Item confirmation
    item_confirmed = Column(Boolean, default=False)
    confirmation_notes = Column(Text, nullable=True)
    distinctive_features_mentioned = Column(JSONB, nullable=True)  # Features patron mentioned

    # Review and decision
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    approval_decision = Column(Boolean, nullable=True)  # True=approved, False=rejected
    rejection_reason = Column(Text, nullable=True)

    # Pickup tracking
    picked_up_at = Column(DateTime(timezone=True), nullable=True)
    picked_up_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps, server_default=func.now(), nullable=False)

    # Relationships
    found_item = relationship("FoundItem", back_populates="claim")
    patron = relationship("User", foreign_keys=[patron_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    picked_up_by = relationship("User", foreign_keys=[picked_up_by_id])

    __table_args__ = (
        Index("ix_claim_verifications_found_item", "found_item_id"),
        Index("ix_claim_verifications_patron", "patron_id"),
        Index("ix_claim_verifications_status", "status"),
        Index("ix_claim_verifications_date", "date_claimed"),
    )
