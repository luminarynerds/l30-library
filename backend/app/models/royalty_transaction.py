# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import enum

from enum import Enum, StrEnum
from sqlalchemy import (
    Column, DateTime, Float, Integer, Numeric, String, Text,
    Enum as SQLEnum, func,
)
from app.core.database import Base


class RoyaltyTransactionStatus(StrEnum):
    pending = "pending"
    earned = "earned"
    paid = "paid"
    clawed_back = "clawed_back"


class RoyaltyTransaction(Base):
    __tablename__ = "royalty_transactions"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, nullable=False, index=True)
    ebook_id = Column(Integer, nullable=False, index=True)
    borrow_id = Column(Integer, nullable=True)
    library_id = Column(Integer, nullable=True)
    access_record_id = Column(Integer, nullable=True)
    pool_balance_after = Column(Numeric, nullable=True)
    amount = Column(Float, nullable=False)
    royalty_rate = Column(Float, nullable=True)
    status = Column(
        SQLEnum(RoyaltyTransactionStatus, name="royaltytransactionstatus",
                create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=RoyaltyTransactionStatus.pending,
        nullable=False,
        index=True,
    )
    transaction_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    paid_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)
