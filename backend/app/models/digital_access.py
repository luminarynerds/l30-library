# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, Enum as SQLEnum, Float
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum, StrEnum
from ..core.database import Base


# ============================================================================
# Enums
# ============================================================================

class OrderStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"        # Manually or via Stripe webhook
    COMPLETED = "completed"      # Card issued
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class CardStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


# ============================================================================
# Models
# ============================================================================

class DigitalAccessOrder(Base):
    __tablename__ = "digital_access_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ebook_id = Column(Integer, ForeignKey("indie_ebooks.id", ondelete="CASCADE"), nullable=False, index=True)

    # Pricing
    amount = Column(Float, default=20.00, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)

    # Order status
    status = Column(
        SQLEnum(OrderStatus, name="orderstatus", create_type=False,
                values_callable=lambda x: [e.value for e in x]),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True
    )

    # Stripe integration (future)
    stripe_payment_intent_id = Column(String(255), nullable=True)

    # Revenue split
    stripe_fee = Column(Float, nullable=True)
    author_share = Column(Float, nullable=True)
    library_share = Column(Float, nullable=True)

    # Approval tracking
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="digital_access_orders")
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    card = relationship("DigitalAccessCard", back_populates="order", uselist=False)


class DigitalAccessCard(Base):
    __tablename__ = "digital_access_cards"

    id = Column(Integer, primary_key=True, index=True)
    card_number = Column(String(50), unique=True, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("digital_access_orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ebook_id = Column(Integer, ForeignKey("indie_ebooks.id", ondelete="CASCADE"), nullable=False, index=True)

    # Card status
    status = Column(
        SQLEnum(CardStatus, name="cardstatus", create_type=False,
                values_callable=lambda x: [e.value for e in x]),
        default=CardStatus.ACTIVE,
        nullable=False,
        index=True
    )

    # Access tracking
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Null = no expiry
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    access_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    order = relationship("DigitalAccessOrder", back_populates="card")
    user = relationship("User", foreign_keys=[user_id], backref="digital_access_cards")


