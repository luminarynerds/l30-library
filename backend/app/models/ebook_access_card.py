# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Index, Integer, String, Text
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class EbookCardStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"
    PENDING_PAYMENT = "pending_payment"


class EbookCardTier(StrEnum):
    BASIC = "basic"          # Limited borrows per month
    STANDARD = "standard"    # Standard access
    UNLIMITED = "unlimited"  # Unlimited borrows


class EbookAccessCard(Base):
    __tablename__ = "ebook_access_cards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Card identification
    card_number = Column(String(50), unique=True, nullable=False, index=True)

    # Subscription details
    tier = Column(
        SQLEnum(EbookCardTier, name="ebookcardtier", create_type=False,
                values_callable=lambda x: [e.value for e in x]),
        default=EbookCardTier.STANDARD,
        nullable=False,
        index=True
    )
    status = Column(
        SQLEnum(EbookCardStatus, name="ebookcardstatus", create_type=False,
                values_callable=lambda x: [e.value for e in x]),
        default=EbookCardStatus.PENDING_PAYMENT,
        nullable=False,
        index=True
    )

    # Pricing
    annual_fee = Column(Float, nullable=False)  # Amount charged
    fee_paid_at = Column(DateTime(timezone=True), nullable=True)

    # Stripe payment tracking
    stripe_payment_intent_id = Column(String(255), nullable=True, unique=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True)

    # Subscription period
    starts_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Access limits (per tier)
    max_concurrent_borrows = Column(Integer, default=3, nullable=False)
    max_monthly_borrows = Column(Integer, default=10, nullable=False)
    borrows_this_month = Column(Integer, default=0, nullable=False)
    month_reset_at = Column(DateTime(timezone=True), nullable=True)

    # Usage stats
    total_borrows = Column(Integer, default=0, nullable=False)

    # Non-resident info
    home_state = Column(String(50), nullable=True)
    home_zip = Column(String(20), nullable=True)

    # Admin notes
    notes = Column(Text, nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Auto-renew preference
    auto_renew = Column(Boolean, default=False, nullable=False)

    # Cancellation
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="ebook_access_cards")
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        Index("ix_ebook_access_cards_status_expires", "status", "expires_at"),
        Index("ix_ebook_access_cards_user_status", "user_id", "status"),
    )

    @property
    def is_active(self) -> bool:
        from datetime import datetime, timezone
        if self.status != EbookCardStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    @property
    def can_borrow(self) -> bool:
        if not self.is_active:
            return False
        if self.borrows_this_month >= self.max_monthly_borrows:
            return False
        return True


class EbookCardTierConfig(Base):
    __tablename__ = "ebook_card_tier_configs"

    id = Column(Integer, primary_key=True, index=True)
    tier = Column(
        SQLEnum(EbookCardTier, name="ebookcardtier", create_type=False,
                values_callable=lambda x: [e.value for e in x]),
        unique=True,
        nullable=False
    )

    # Display
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Pricing
    annual_fee = Column(Float, nullable=False)

    # Limits
    max_concurrent_borrows = Column(Integer, nullable=False)
    max_monthly_borrows = Column(Integer, nullable=False)

    # Availability
    is_available = Column(Boolean, default=True, nullable=False)

    # Revenue split (percentage going to author royalty pool)
    author_royalty_share_pct = Column(Float, default=40.0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
