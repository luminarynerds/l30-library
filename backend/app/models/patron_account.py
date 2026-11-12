# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric,
    String, Text
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class TransactionType(StrEnum):
    DEPOSIT = "deposit"
    CHARGE = "charge"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


class TransactionStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


class AccountPaymentMethod(StrEnum):
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    ONLINE = "online"
    SYSTEM = "system"  # For automated charges


class PatronAccount(Base):
    __tablename__ = "patron_accounts"

    id = Column(Integer, primary_key=True, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    balance = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    total_deposited = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    total_spent = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    low_balance_threshold = Column(Numeric(10, 2), default=Decimal("2.00"), nullable=False)
    auto_reload_enabled = Column(Boolean, default=False, nullable=False)
    auto_reload_amount = Column(Numeric(10, 2), nullable=True)
    auto_reload_threshold = Column(Numeric(10, 2), nullable=True)

    last_deposit_at = Column(DateTime(timezone=True), nullable=True)
    last_charge_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    patron = relationship("User", backref="patron_account")
    transactions = relationship("PatronTransaction", back_populates="account", lazy="selectin")

    __table_args__ = (
        Index("ix_patron_accounts_balance", "balance"),
    )


class PatronTransaction(Base):
    __tablename__ = "patron_transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("patron_accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    transaction_type = Column(
        SQLEnum(TransactionType, name="transactiontype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True
    )
    status = Column(
        SQLEnum(TransactionStatus, name="transactionstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=TransactionStatus.COMPLETED, nullable=False
    )

    amount = Column(Numeric(10, 2), nullable=False)
    balance_before = Column(Numeric(10, 2), nullable=False)
    balance_after = Column(Numeric(10, 2), nullable=False)

    payment_method = Column(
        SQLEnum(AccountPaymentMethod, name="accountpaymentmethod", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )

    description = Column(String(500), nullable=False)
    reference_type = Column(String(50), nullable=True)  # "print_job", "room_booking", etc.
    reference_id = Column(Integer, nullable=True)  # ID of the related entity

    processed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    receipt_number = Column(String(100), nullable=True, unique=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    account = relationship("PatronAccount", back_populates="transactions")
    processed_by = relationship("User", foreign_keys=[processed_by_id])

    __table_args__ = (
        Index("ix_patron_transactions_account_type", "account_id", "transaction_type"),
        Index("ix_patron_transactions_created", "created_at"),
        Index("ix_patron_transactions_reference", "reference_type", "reference_id"),
    )
