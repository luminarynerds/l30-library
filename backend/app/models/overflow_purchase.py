# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import (
    Column, Integer, String, DateTime,
    ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum, StrEnum
from ..core.database import Base


class OverflowPurchaseStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class OverflowPurchase(Base):
    __tablename__ = "overflow_purchases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    metislib_ebook_id = Column(Integer, nullable=False, index=True)
    ebook_title = Column(String(500), nullable=False)
    ebook_author = Column(String(300), nullable=True)

    # Stripe
    stripe_checkout_session_id = Column(String(255), unique=True, nullable=False, index=True)
    stripe_payment_intent_id = Column(String(255), unique=True, nullable=True, index=True)

    # Pricing (cents)
    sale_price_cents = Column(Integer, nullable=False)
    stripe_fee_cents = Column(Integer, nullable=True)
    library_kickback_cents = Column(Integer, nullable=True)
    author_royalty_cents = Column(Integer, nullable=True)
    currency = Column(String(3), default="USD", nullable=False)
    library_kickback_percent = Column(Integer, nullable=False)

    # Status
    status = Column(
        SQLEnum(OverflowPurchaseStatus, name="overflowpurchasestatus",
                create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=OverflowPurchaseStatus.PENDING,
        nullable=False,
        index=True,
    )

    # MetisLib access granted after payment
    metislib_access_id = Column(Integer, nullable=True)

    # Linked royalty transaction
    # use_alter=True defers the FK as an ALTER TABLE so this table can be created
    # even when royalty_transactions is in the deferred list.
    royalty_transaction_id = Column(Integer, ForeignKey("royalty_transactions.id", ondelete="SET NULL", use_alter=True, name="fk_overflow_purchases_royalty_transaction_id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
