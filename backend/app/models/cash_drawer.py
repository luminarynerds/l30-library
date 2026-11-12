# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from decimal import Decimal
from enum import Enum, StrEnum

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text, Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base
from .mixins import TimestampMixin


class DrawerMode(StrEnum):
    shift_based = "shift_based"
    day_based = "day_based"


class CashSessionStatus(StrEnum):
    open = "open"
    pending_approval = "pending_approval"
    closed = "closed"


class TransactionDirection(StrEnum):
    inflow = "inflow"
    outflow = "outflow"


class TransactionCategory(StrEnum):
    fine_payment = "fine_payment"
    print_fee = "print_fee"
    copy_fee = "copy_fee"
    room_fee = "room_fee"
    card_replacement = "card_replacement"
    makerspace_fee = "makerspace_fee"
    petty_cash = "petty_cash"
    other = "other"


class CashDrawer(Base, TimestampMixin):
    __tablename__ = "cash_drawers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    default_float = Column(Numeric(10, 2), nullable=False, default=Decimal("100.00"))
    mode = Column(
        SQLEnum(DrawerMode, name="cash_drawer_mode", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DrawerMode.day_based,
    )
    discrepancy_threshold = Column(Numeric(10, 2), nullable=False, default=Decimal("5.00"))
    is_active = Column(Boolean, default=True, nullable=False)

    sessions = relationship("CashDrawerSession", back_populates="drawer", lazy="dynamic")


class CashDrawerSession(Base, TimestampMixin):
    __tablename__ = "cash_drawer_sessions"

    id = Column(Integer, primary_key=True, index=True)
    drawer_id = Column(Integer, ForeignKey("cash_drawers.id", ondelete="CASCADE"), nullable=False, index=True)
    opened_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    closed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(
        SQLEnum(CashSessionStatus, name="cash_session_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=CashSessionStatus.open,
    )
    opening_float = Column(Numeric(10, 2), nullable=False)
    expected_total = Column(Numeric(10, 2), nullable=True)
    counted_total = Column(Numeric(10, 2), nullable=True)
    discrepancy = Column(Numeric(10, 2), nullable=True)
    denomination_breakdown = Column(JSONB, nullable=True)
    notes = Column(Text, nullable=True)
    opened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    drawer = relationship("CashDrawer", back_populates="sessions")
    transactions = relationship("CashTransaction", back_populates="session", lazy="dynamic")
    opener = relationship("User", foreign_keys=[opened_by])
    closer = relationship("User", foreign_keys=[closed_by])
    approver = relationship("User", foreign_keys=[approved_by])


class CashTransaction(Base):
    __tablename__ = "cash_transactions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("cash_drawer_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    direction = Column(
        SQLEnum(TransactionDirection, name="cash_transaction_direction", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    category = Column(
        SQLEnum(TransactionCategory, name="cash_transaction_category", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    amount = Column(Numeric(10, 2), nullable=False)
    amount_tendered = Column(Numeric(10, 2), nullable=True)
    change_given = Column(Numeric(10, 2), nullable=True)
    description = Column(Text, nullable=True)
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(Integer, nullable=True)
    voided = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("CashDrawerSession", back_populates="transactions")
    staff = relationship("User", foreign_keys=[staff_id])
