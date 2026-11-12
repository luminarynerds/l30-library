# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for cash drawer service layer.

Tests cover:
- Session lifecycle (open, close, approve)
- Transaction logging with change calculation
- Reconciliation with discrepancy detection
- Void transactions
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

from app.models.cash_drawer import (
    CashDrawer, CashDrawerSession, CashTransaction,
    DrawerMode, CashSessionStatus, TransactionDirection, TransactionCategory,
)
from app.models.user import User, UserRole
from app.services.cash_drawer_service import (
    open_session,
    close_session,
    approve_session,
    log_transaction,
    void_transaction,
    compute_session_totals,
)


# Use a targeted metadata that only includes the tables we need
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text, Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func


class TestBase(DeclarativeBase):
    pass


# Mirror just enough of User for FK references
class TestUser(TestBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))


class TestCashDrawer(TestBase):
    __tablename__ = "cash_drawers"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    default_float = Column(Numeric(10, 2), nullable=False, default=Decimal("100.00"))
    mode = Column(String(20), nullable=False, default="day_based")
    discrepancy_threshold = Column(Numeric(10, 2), nullable=False, default=Decimal("5.00"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class TestCashDrawerSession(TestBase):
    __tablename__ = "cash_drawer_sessions"
    id = Column(Integer, primary_key=True)
    drawer_id = Column(Integer, ForeignKey("cash_drawers.id"), nullable=False)
    opened_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    closed_by = Column(Integer, ForeignKey("users.id"))
    approved_by = Column(Integer, ForeignKey("users.id"))
    status = Column(String(30), nullable=False, default="open")
    opening_float = Column(Numeric(10, 2), nullable=False)
    expected_total = Column(Numeric(10, 2))
    counted_total = Column(Numeric(10, 2))
    discrepancy = Column(Numeric(10, 2))
    denomination_breakdown = Column(Text)
    notes = Column(Text)
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class TestCashTransaction(TestBase):
    __tablename__ = "cash_transactions"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("cash_drawer_sessions.id"), nullable=False)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    direction = Column(String(20), nullable=False)
    category = Column(String(30), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    amount_tendered = Column(Numeric(10, 2))
    change_given = Column(Numeric(10, 2))
    description = Column(Text)
    reference_type = Column(String(50))
    reference_id = Column(Integer)
    voided = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


@pytest.fixture
async def db():
    """Create an in-memory SQLite database with only cash drawer tables."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.create_all)

    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_factory() as session:
        # Map the real models to these test tables by adding them to the mapper
        yield session

    await engine.dispose()


@pytest.fixture
async def setup_data(db: AsyncSession):
    """Create test user and drawer."""
    user = TestUser(id=1, email="staff@test.com", first_name="Jane", last_name="Staff")
    manager = TestUser(id=2, email="manager@test.com", first_name="Mike", last_name="Manager")
    drawer = TestCashDrawer(
        id=1, name="Main Drawer", default_float=Decimal("100.00"),
        mode="day_based", discrepancy_threshold=Decimal("5.00"), is_active=True,
    )
    db.add_all([user, manager, drawer])
    await db.commit()
    return {"user_id": 1, "manager_id": 2, "drawer_id": 1}


@pytest.mark.asyncio
async def test_open_session_creates_session(db, setup_data):
    session = await open_session(db, setup_data["drawer_id"], setup_data["user_id"], Decimal("100.00"))
    await db.commit()

    assert session.drawer_id == setup_data["drawer_id"]
    assert session.opened_by == setup_data["user_id"]
    assert session.opening_float == Decimal("100.00")
    assert session.status == CashSessionStatus.open


@pytest.mark.asyncio
async def test_open_session_rejects_when_already_open(db, setup_data):
    await open_session(db, setup_data["drawer_id"], setup_data["user_id"], Decimal("100.00"))
    await db.commit()

    with pytest.raises(ValueError, match="already has an active session"):
        await open_session(db, setup_data["drawer_id"], setup_data["user_id"], Decimal("100.00"))


@pytest.mark.asyncio
async def test_log_transaction_calculates_change(db, setup_data):
    session = await open_session(db, setup_data["drawer_id"], setup_data["user_id"], Decimal("100.00"))
    await db.commit()

    txn = await log_transaction(
        db, session.id, setup_data["user_id"],
        direction=TransactionDirection.inflow,
        category=TransactionCategory.fine_payment,
        amount=Decimal("3.50"),
        amount_tendered=Decimal("5.00"),
    )
    await db.commit()

    assert txn.amount == Decimal("3.50")
    assert txn.amount_tendered == Decimal("5.00")
    assert txn.change_given == Decimal("1.50")


@pytest.mark.asyncio
async def test_close_session_auto_closes_within_threshold(db, setup_data):
    session = await open_session(db, setup_data["drawer_id"], setup_data["user_id"], Decimal("100.00"))
    await db.commit()

    await log_transaction(
        db, session.id, setup_data["user_id"],
        direction=TransactionDirection.inflow,
        category=TransactionCategory.fine_payment,
        amount=Decimal("20.00"),
    )
    await db.commit()

    # Expected: 100 + 20 = 120. Count 121 (within $5 threshold)
    closed = await close_session(
        db, session, setup_data["user_id"], counted_total=Decimal("121.00"),
    )
    await db.commit()

    assert closed.status == CashSessionStatus.closed
    assert closed.expected_total == Decimal("120.00")
    assert closed.counted_total == Decimal("121.00")
    assert closed.discrepancy == Decimal("1.00")


@pytest.mark.asyncio
async def test_close_session_pending_approval_over_threshold(db, setup_data):
    session = await open_session(db, setup_data["drawer_id"], setup_data["user_id"], Decimal("100.00"))
    await db.commit()

    closed = await close_session(
        db, session, setup_data["user_id"], counted_total=Decimal("110.00"),
    )
    await db.commit()

    assert closed.status == CashSessionStatus.pending_approval
    assert closed.discrepancy == Decimal("10.00")


@pytest.mark.asyncio
async def test_approve_session_closes_pending(db, setup_data):
    session = await open_session(db, setup_data["drawer_id"], setup_data["user_id"], Decimal("100.00"))
    await db.commit()

    closed = await close_session(
        db, session, setup_data["user_id"], counted_total=Decimal("120.00"),
    )
    await db.commit()
    assert closed.status == CashSessionStatus.pending_approval

    approved = await approve_session(db, closed, setup_data["manager_id"], notes="Reviewed")
    await db.commit()

    assert approved.status == CashSessionStatus.closed
    assert approved.approved_by == setup_data["manager_id"]
    assert "Manager" in (approved.notes or "")


@pytest.mark.asyncio
async def test_void_transaction_marks_voided(db, setup_data):
    session = await open_session(db, setup_data["drawer_id"], setup_data["user_id"], Decimal("100.00"))
    await db.commit()

    txn = await log_transaction(
        db, session.id, setup_data["user_id"],
        direction=TransactionDirection.inflow,
        category=TransactionCategory.other,
        amount=Decimal("10.00"),
    )
    await db.commit()

    voided = await void_transaction(db, txn)
    await db.commit()

    assert voided.voided is True

    with pytest.raises(ValueError, match="already voided"):
        await void_transaction(db, voided)


@pytest.mark.asyncio
async def test_compute_totals_excludes_voided(db, setup_data):
    session = await open_session(db, setup_data["drawer_id"], setup_data["user_id"], Decimal("100.00"))
    await db.commit()

    txn1 = await log_transaction(
        db, session.id, setup_data["user_id"],
        direction=TransactionDirection.inflow,
        category=TransactionCategory.fine_payment,
        amount=Decimal("10.00"),
    )
    await log_transaction(
        db, session.id, setup_data["user_id"],
        direction=TransactionDirection.inflow,
        category=TransactionCategory.print_fee,
        amount=Decimal("5.00"),
    )
    await db.commit()

    await void_transaction(db, txn1)
    await db.commit()

    totals = await compute_session_totals(db, session.id)
    assert totals["total_inflows"] == Decimal("5.00")
    assert totals["transaction_count"] == 1
