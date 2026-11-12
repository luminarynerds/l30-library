# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from datetime import datetime, date, time

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, Index, Integer, String, Text,
    Time, UniqueConstraint, ForeignKey, Numeric
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY

from ..core.database import Base


# ============================================================================
# Enums
# ============================================================================

class ShiftSwapListingType(StrEnum):
    giving_away = "giving_away"     # Staff offering their shift to others
    looking_for = "looking_for"      # Staff seeking additional shifts


class ShiftSwapListingStatus(StrEnum):
    open = "open"                    # Active and available for claiming
    claimed = "claimed"              # Someone has claimed it
    completed = "completed"          # Swap was completed/approved
    withdrawn = "withdrawn"          # Original poster withdrew
    expired = "expired"              # Past the shift date


class ShiftSwapClaimStatus(StrEnum):
    pending = "pending"              # Awaiting approval
    approved = "approved"            # Claim approved, swap confirmed
    completed = "completed"          # Swap successfully completed
    cancelled = "cancelled"          # Claim cancelled by requester
    rejected = "rejected"            # Claim rejected by listing owner


class ShiftType(StrEnum):
    opening = "opening"              # Morning shift (opens branch)
    closing = "closing"              # Evening shift (closes branch)
    mid_day = "mid_day"              # Middle shift
    full_day = "full_day"            # Full day shift
    partial = "partial"              # Partial coverage


class SwapMatchStatus(StrEnum):
    pending_notification = "pending_notification"  # Match found, not yet notified
    notified = "notified"                          # Match notified to both parties
    accepted = "accepted"                          # Both parties accepted
    rejected = "rejected"                          # One party rejected
    completed = "completed"                        # Swap completed


class ShiftSwapNotificationType(StrEnum):
    new_match = "new_match"                  # New compatible match found
    match_accepted = "match_accepted"        # Other party accepted your match
    match_rejected = "match_rejected"        # Match was rejected
    swap_claimed = "swap_claimed"            # Someone claimed your listing
    swap_expiring = "swap_expiring"          # Listing expiring soon (24h notice)
    claim_approved = "claim_approved"        # Your claim was approved
    claim_rejected = "claim_rejected"        # Your claim was rejected


# ============================================================================
# Core Shift Swap Models
# ============================================================================

class ShiftSwapListing(Base):
    __tablename__ = "shift_swap_listings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    branch_id = Column(
        Integer,
        nullable=False, index=True
    )

    # Listing type: are they giving away or looking for a shift?
    listing_type = Column(
        SQLEnum(ShiftSwapListingType, name="shiftswaplistingtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True
    )

    # Shift details
    shift_date = Column(Date, nullable=False, index=True)
    shift_start_time = Column(Time, nullable=False)
    shift_end_time = Column(Time, nullable=False)
    shift_type = Column(
        SQLEnum(ShiftType, name="fairnessshifttype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # For partial shifts: specify exact coverage needed/offered
    is_partial = Column(Boolean, default=False)
    partial_description = Column(String(255), nullable=True)  # e.g., "2-5pm coverage of 12-5pm shift"

    # Status
    status = Column(
        SQLEnum(ShiftSwapListingStatus, name="shiftswaplistingstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ShiftSwapListingStatus.open,
        nullable=False, index=True
    )

    # Description of the shift or request
    description = Column(Text, nullable=True)

    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    withdrawn_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="shift_swap_listings")
    # DISABLED: # DISABLED: branch relationship
    withdrawn_by = relationship("User", foreign_keys=[withdrawn_by_id])
    claims = relationship(
        "ShiftSwapClaim",
        back_populates="listing",
        cascade="all, delete-orphan"
    )
    matches = relationship(
        "ShiftSwapMatch",
        foreign_keys="[ShiftSwapMatch.giver_listing_id]",
        back_populates="listing"
    )

    __table_args__ = (
        Index("ix_shift_swap_listings_user_date", "user_id", "shift_date"),
        Index("ix_shift_swap_listings_branch_date_status", "branch_id", "shift_date", "status"),
        Index("ix_shift_swap_listings_status_expires", "status", "expires_at"),
    )


class ShiftSwapClaim(Base):
    __tablename__ = "shift_swap_claims"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(
        Integer, ForeignKey("shift_swap_listings.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    claimer_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Status of the claim
    status = Column(
        SQLEnum(ShiftSwapClaimStatus, name="shiftswapclaimstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ShiftSwapClaimStatus.pending,
        nullable=False, index=True
    )

    # If this is a swap (not just claiming), what shift is the claimer offering?
    # This makes it a "swap" request rather than just "I want to take your shift"
    swap_shift_date = Column(Date, nullable=True)
    swap_shift_start_time = Column(Time, nullable=True)
    swap_shift_end_time = Column(Time, nullable=True)

    # Claim message/notes
    message = Column(Text, nullable=True)

    # Approval tracking
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approval_notes = Column(Text, nullable=True)

    # Rejection tracking
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejected_reason = Column(Text, nullable=True)

    # Completion tracking
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    listing = relationship("ShiftSwapListing", back_populates="claims")
    claimer = relationship("User", foreign_keys=[claimer_id], backref="shift_swap_claims")
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        Index("ix_shift_swap_claims_listing_claimer", "listing_id", "claimer_id"),
        Index("ix_shift_swap_claims_status", "status"),
        UniqueConstraint("listing_id", "claimer_id", name="uq_listing_claimer"),
    )


# ============================================================================
# Staff Preferences & Reliability
# ============================================================================

class StaffPreferenceProfile(Base):
    __tablename__ = "staff_preference_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )

    # Standing requests
    wants_extra_hours = Column(Boolean, default=False, index=True)
    preferred_shift_types = Column(ARRAY(String), default=[])  # ["opening", "closing", "mid_day"]
    preferred_branches = Column(ARRAY(Integer), default=[])    # Branch IDs
    preferred_days_of_week = Column(ARRAY(String), default=[]) # ["Monday", "Tuesday", ...]
    days_available = Column(ARRAY(String), default=[])        # Days available for extra shifts

    # Time preferences
    earliest_available_time = Column(Time, nullable=True)      # e.g., 07:00
    latest_available_time = Column(Time, nullable=True)        # e.g., 21:00

    # Constraints
    max_extra_hours_per_week = Column(Integer, default=10, nullable=False)
    max_consecutive_days = Column(Integer, default=5, nullable=False)

    # Auto-matching preferences
    auto_claim_compatible = Column(Boolean, default=False)     # Automatically claim compatible swaps?
    notify_on_new_matches = Column(Boolean, default=True)      # Send notifications for matches?

    # Notes
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="shift_preference_profile", uselist=False)

    __table_args__ = (
        Index("ix_staff_preference_profiles_wants_extra", "wants_extra_hours"),
    )


class SwapperReliabilityScore(Base):
    __tablename__ = "swapper_reliability_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )

    # Swap completion stats
    total_completed_swaps = Column(Integer, default=0, nullable=False)
    total_swap_claims = Column(Integer, default=0, nullable=False)

    # Reliability metrics (0-100 scale)
    reliability_score = Column(Float, default=100.0, nullable=False)  # Overall score
    completion_rate = Column(Float, default=100.0, nullable=False)    # % of swaps completed

    # Negative factors
    cancelled_after_claiming_count = Column(Integer, default=0, nullable=False)
    called_out_after_swap_count = Column(Integer, default=0, nullable=False)
    no_show_count = Column(Integer, default=0, nullable=False)

    # Trust metrics
    times_stood_up = Column(Integer, default=0, nullable=False)       # Times others depended on them
    times_let_down = Column(Integer, default=0, nullable=False)       # Times they let others down

    # Dates
    last_swap_date = Column(Date, nullable=True)
    score_calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Notes from admin
    flags = Column(Text, nullable=True)  # e.g., "Pattern of cancellations" or "Reliable swapper"

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="reliability_score", uselist=False)

    __table_args__ = (
        Index("ix_swapper_reliability_scores_score", "reliability_score"),
        Index("ix_swapper_reliability_scores_completion_rate", "completion_rate"),
    )


# ============================================================================
# Automated Matching & Notifications
# ============================================================================

class ShiftSwapMatch(Base):
    __tablename__ = "shift_swap_matches"

    id = Column(Integer, primary_key=True, index=True)

    # The two listings being matched
    giver_listing_id = Column(
        Integer, ForeignKey("shift_swap_listings.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    taker_listing_id = Column(
        Integer, ForeignKey("shift_swap_listings.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Match quality/compatibility score (0-100)
    compatibility_score = Column(Float, default=0.0, nullable=False)

    # Match status
    status = Column(
        SQLEnum(SwapMatchStatus, name="swapmatchstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=SwapMatchStatus.pending_notification,
        nullable=False, index=True
    )

    # Notification tracking
    notified_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    listing = relationship(
        "ShiftSwapListing",
        foreign_keys=[giver_listing_id],
        back_populates="matches"
    )
    giver_listing = relationship(
        "ShiftSwapListing",
        foreign_keys=[giver_listing_id],
        viewonly=True
    )
    taker_listing = relationship(
        "ShiftSwapListing",
        foreign_keys=[taker_listing_id],
        viewonly=True
    )

    __table_args__ = (
        Index("ix_shift_swap_matches_status", "status"),
        Index("ix_shift_swap_matches_score", "compatibility_score"),
        UniqueConstraint(
            "giver_listing_id", "taker_listing_id",
            name="uq_giver_taker_match"
        ),
    )


class ShiftSwapNotification(Base):
    __tablename__ = "shift_swap_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # What triggered the notification
    notification_type = Column(
        SQLEnum(ShiftSwapNotificationType, name="notificationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True
    )

    # Related objects
    match_id = Column(
        Integer, ForeignKey("shift_swap_matches.id", ondelete="SET NULL"),
        nullable=True
    )
    listing_id = Column(
        Integer, ForeignKey("shift_swap_listings.id", ondelete="SET NULL"),
        nullable=True
    )
    claim_id = Column(
        Integer, ForeignKey("shift_swap_claims.id", ondelete="SET NULL"),
        nullable=True
    )

    # Notification content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Read status
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="shift_swap_notifications")
    match = relationship("ShiftSwapMatch")
    listing = relationship("ShiftSwapListing")
    claim = relationship("ShiftSwapClaim")

    __table_args__ = (
        Index("ix_shift_swap_notifications_user_read", "user_id", "is_read"),
        Index("ix_shift_swap_notifications_type", "notification_type"),
    )


# ============================================================================
# Gaming Prevention
# ============================================================================

class ShiftSwapAudit(Base):
    __tablename__ = "shift_swap_audits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    action = Column(String(50), nullable=False)  # created_listing, claimed_shift, approved_swap, etc.
    shift_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    action_metadata = Column(String(1000), nullable=True)  # JSON string with additional data

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_shift_swap_audits_user_action", "user_id", "action"),
        Index("ix_shift_swap_audits_shift_date", "shift_date"),
    )
