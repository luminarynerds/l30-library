# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.cash_drawer import (
    CashDrawer, CashDrawerSession, CashTransaction,
    CashSessionStatus, TransactionDirection, TransactionCategory,
)
from ..models.user import User
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


async def get_drawer(db: AsyncSession, drawer_id: int) -> CashDrawer | None:
    result = await db.execute(select(CashDrawer).where(CashDrawer.id == drawer_id))
    return result.scalar_one_or_none()


async def list_drawers(db: AsyncSession, active_only: bool = True) -> list[CashDrawer]:
    query = select(CashDrawer)
    if active_only:
        query = query.where(CashDrawer.is_active == True)
    query = query.order_by(CashDrawer.name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_drawer(db: AsyncSession, **kwargs) -> CashDrawer:
    drawer = CashDrawer(**kwargs)
    db.add(drawer)
    await db.flush()
    return drawer


async def update_drawer(db: AsyncSession, drawer: CashDrawer, **kwargs) -> CashDrawer:
    for key, value in kwargs.items():
        if value is not None:
            setattr(drawer, key, value)
    await db.flush()
    return drawer


async def get_active_session(db: AsyncSession, drawer_id: int) -> CashDrawerSession | None:
    result = await db.execute(
        select(CashDrawerSession).where(
            and_(
                CashDrawerSession.drawer_id == drawer_id,
                CashDrawerSession.status.in_([CashSessionStatus.open, CashSessionStatus.pending_approval]),
            )
        )
    )
    return result.scalar_one_or_none()


async def open_session(
    db: AsyncSession, drawer_id: int, staff_id: int, opening_float: Decimal,
) -> CashDrawerSession:
    # Lock the drawer row to serialize concurrent open_session calls
    drawer_result = await db.execute(
        select(CashDrawer).where(CashDrawer.id == drawer_id).with_for_update()
    )
    if not drawer_result.scalar_one_or_none():
        raise ValueError("Drawer not found")

    existing = await get_active_session(db, drawer_id)
    if existing:
        raise ValueError("Drawer already has an active session")

    session = CashDrawerSession(
        drawer_id=drawer_id,
        opened_by=staff_id,
        opening_float=opening_float,
        status=CashSessionStatus.open,
    )
    db.add(session)
    await db.flush()
    return session


async def compute_session_totals(db: AsyncSession, session_id: int) -> dict:
    result = await db.execute(
        select(
            CashTransaction.direction,
            CashTransaction.category,
            func.sum(CashTransaction.amount).label("total"),
            func.count().label("count"),
        )
        .where(
            and_(
                CashTransaction.session_id == session_id,
                CashTransaction.voided == False,
            )
        )
        .group_by(CashTransaction.direction, CashTransaction.category)
    )
    rows = result.all()

    total_inflows = Decimal("0")
    total_outflows = Decimal("0")
    inflow_by_category = {}
    outflow_by_category = {}
    count = 0

    for row in rows:
        count += row.count
        if row.direction == TransactionDirection.inflow:
            total_inflows += row.total
            inflow_by_category[str(row.category)] = row.total
        else:
            total_outflows += row.total
            outflow_by_category[str(row.category)] = row.total

    return {
        "total_inflows": total_inflows,
        "total_outflows": total_outflows,
        "transaction_count": count,
        "inflow_by_category": inflow_by_category,
        "outflow_by_category": outflow_by_category,
    }


async def close_session(
    db: AsyncSession,
    session: CashDrawerSession,
    staff_id: int,
    counted_total: Decimal,
    denomination_breakdown: dict | None = None,
    notes: str | None = None,
) -> CashDrawerSession:
    if session.status != CashSessionStatus.open:
        raise ValueError("Session is not open")

    totals = await compute_session_totals(db, session.id)
    expected = session.opening_float + totals["total_inflows"] - totals["total_outflows"]
    discrepancy = counted_total - expected

    drawer = await get_drawer(db, session.drawer_id)
    threshold = drawer.discrepancy_threshold if drawer else Decimal("5.00")

    session.closed_by = staff_id
    session.expected_total = expected
    session.counted_total = counted_total
    session.discrepancy = discrepancy
    session.denomination_breakdown = denomination_breakdown
    session.notes = notes
    session.closed_at = utc_now()

    if abs(discrepancy) <= threshold:
        session.status = CashSessionStatus.closed
    else:
        session.status = CashSessionStatus.pending_approval
        logger.warning(
            "Cash drawer discrepancy exceeds threshold",
            extra={"session_id": session.id, "discrepancy": str(discrepancy), "threshold": str(threshold)},
        )

    await db.flush()
    return session


async def approve_session(
    db: AsyncSession, session: CashDrawerSession, manager_id: int, notes: str | None = None,
) -> CashDrawerSession:
    if session.status != CashSessionStatus.pending_approval:
        raise ValueError("Session is not pending approval")

    session.approved_by = manager_id
    session.status = CashSessionStatus.closed
    if notes:
        session.notes = (session.notes or "") + f"\n[Manager] {notes}"
    await db.flush()
    return session


async def log_transaction(
    db: AsyncSession,
    session_id: int,
    staff_id: int,
    direction: TransactionDirection,
    category: TransactionCategory,
    amount: Decimal,
    amount_tendered: Decimal | None = None,
    description: str | None = None,
    reference_type: str | None = None,
    reference_id: int | None = None,
) -> CashTransaction:
    result = await db.execute(
        select(CashDrawerSession).where(CashDrawerSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session or session.status != CashSessionStatus.open:
        raise ValueError("No open session for this drawer")

    change_given = None
    if amount_tendered and amount_tendered > amount:
        change_given = amount_tendered - amount

    txn = CashTransaction(
        session_id=session_id,
        staff_id=staff_id,
        direction=direction,
        category=category,
        amount=amount,
        amount_tendered=amount_tendered,
        change_given=change_given,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(txn)
    await db.flush()
    return txn


async def void_transaction(db: AsyncSession, txn: CashTransaction) -> CashTransaction:
    if txn.voided:
        raise ValueError("Transaction already voided")
    txn.voided = True
    await db.flush()
    return txn


async def get_session_transactions(
    db: AsyncSession, session_id: int, include_voided: bool = False,
) -> list[CashTransaction]:
    query = select(CashTransaction).where(CashTransaction.session_id == session_id)
    if not include_voided:
        query = query.where(CashTransaction.voided == False)
    query = query.order_by(CashTransaction.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def find_active_session_for_staff(db: AsyncSession, staff_id: int) -> CashDrawerSession | None:
    result = await db.execute(
        select(CashDrawerSession).where(
            and_(
                CashDrawerSession.opened_by == staff_id,
                CashDrawerSession.status == CashSessionStatus.open,
            )
        )
    )
    return result.scalar_one_or_none()
