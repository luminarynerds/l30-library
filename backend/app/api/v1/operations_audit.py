# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Operations Audit API Endpoints

Provides queryable access to the operations audit trail for answering
forensic questions about library operations.

Key queries supported:
- Circulation trends over time (answers "why did circulation drop 40%?")
- Fine waivers by staff member (answers "who waived $50K in fines?")
- Policy change history (answers "when did we change the checkout limit?")
- Patron account history (answers "what happened to patron #12847?")
- Item lifecycle (answers "why do 500 items have no checkout history?")

All endpoints require ADMIN or SUPER_ADMIN role.
"""

from app.core.logging import get_logger
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.pagination import PaginationParams, calculate_total_pages
from ...models.operations_audit_log import (
    OperationCategory,
    OperationsAuditLog,
    OperationType,
    PolicyChangeLog,
)
from ...models.user import User
from .auth import get_current_user
from .dependencies import require_admin

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/operations-audit", tags=["operations-audit"])




# =============================================================================
# Response schemas
# =============================================================================

class OperationsAuditEntry(BaseModel):
    id: int
    category: str
    operation_type: str
    patron_id: Optional[int] = None
    patron_identifier: Optional[str] = None
    staff_id: Optional[int] = None
    staff_identifier: Optional[str] = None
    item_id: Optional[int] = None
    item_identifier: Optional[str] = None
    checkout_id: Optional[int] = None
    fine_id: Optional[int] = None
    hold_id: Optional[int] = None
    amount_cents: Optional[int] = None
    before_state: Optional[dict] = None
    after_state: Optional[dict] = None
    reason: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OperationsAuditResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    entries: List[OperationsAuditEntry]


class PolicyChangeEntry(BaseModel):
    id: int
    policy_type: str
    policy_name: str
    changed_by_staff_id: Optional[int] = None
    changed_by_identifier: Optional[str] = None
    before_value: Optional[dict] = None
    after_value: Optional[dict] = None
    fields_changed: Optional[list] = None
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PolicyChangeResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    entries: List[PolicyChangeEntry]


class FineWaiverSummary(BaseModel):
    staff_id: Optional[int] = None
    staff_identifier: Optional[str] = None
    total_waived_cents: int
    total_waived_display: str  # e.g. "$5,230.00"
    waiver_count: int


class FineWaiverSummaryResponse(BaseModel):
    start_date: datetime
    end_date: datetime
    summaries: List[FineWaiverSummary]
    grand_total_cents: int
    grand_total_display: str


class CirculationDailySummary(BaseModel):
    date: str
    checkouts: int
    returns: int
    renewals: int
    holds_placed: int
    holds_cancelled: int


class CirculationTrendResponse(BaseModel):
    start_date: str
    end_date: str
    daily_summaries: List[CirculationDailySummary]
    total_checkouts: int
    total_returns: int


# =============================================================================
# Helper
# =============================================================================

def _normalize_dates(
    start_date: Optional[date], end_date: Optional[date], default_days_back: int = 30
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if start_date is None and end_date is None:
        return now - timedelta(days=default_days_back), now
    s = datetime.combine(start_date or end_date, time.min, tzinfo=timezone.utc)
    e = datetime.combine(end_date or start_date, time.max, tzinfo=timezone.utc)
    if s > e:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")
    return s, e


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "/events",
    response_model=OperationsAuditResponse,
    summary="Query operations audit log",
    description="Search the operations audit trail with flexible filtering.",
)
async def query_operations_audit(
    category: Optional[str] = Query(None, description="Filter by category: CIRCULATION, FINE, PATRON, CATALOG, POLICY, SYSTEM"),
    operation_type: Optional[str] = Query(None, description="Filter by specific operation type"),
    patron_id: Optional[int] = Query(None, description="Filter by patron ID"),
    staff_id: Optional[int] = Query(None, description="Filter by staff ID"),
    item_id: Optional[int] = Query(None, description="Filter by catalog item ID"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OperationsAuditResponse:
    """General-purpose query for the operations audit log."""
    start_dt, end_dt = _normalize_dates(start_date, end_date, default_days_back=30)

    conditions = [
        OperationsAuditLog.created_at >= start_dt,
        OperationsAuditLog.created_at <= end_dt,
    ]
    if category:
        conditions.append(OperationsAuditLog.category == category)
    if operation_type:
        conditions.append(OperationsAuditLog.operation_type == operation_type)
    if patron_id is not None:
        conditions.append(OperationsAuditLog.patron_id == patron_id)
    if staff_id is not None:
        conditions.append(OperationsAuditLog.staff_id == staff_id)
    if item_id is not None:
        conditions.append(OperationsAuditLog.item_id == item_id)
    if correlation_id:
        conditions.append(OperationsAuditLog.correlation_id == correlation_id)

    where = and_(*conditions)

    count_result = await db.execute(
        select(func.count(OperationsAuditLog.id)).where(where)
    )
    total = count_result.scalar() or 0

    query = (
        select(OperationsAuditLog)
        .where(where)
        .order_by(desc(OperationsAuditLog.created_at))
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    result = await db.execute(query)
    entries = [
        OperationsAuditEntry(
            id=e.id,
            category=e.category,
            operation_type=e.operation_type,
            patron_id=e.patron_id,
            patron_identifier=e.patron_identifier,
            staff_id=e.staff_id,
            staff_identifier=e.staff_identifier,
            item_id=e.item_id,
            item_identifier=e.item_identifier,
            checkout_id=e.checkout_id,
            fine_id=e.fine_id,
            hold_id=e.hold_id,
            amount_cents=e.amount_cents,
            before_state=e.before_state,
            after_state=e.after_state,
            reason=e.reason,
            correlation_id=e.correlation_id,
            created_at=e.created_at,
        )
        for e in result.scalars().all()
    ]

    return OperationsAuditResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=calculate_total_pages(total, pagination.page_size),
        entries=entries,
    )


@router.get(
    "/patron/{patron_id}/history",
    response_model=OperationsAuditResponse,
    summary="Get complete history for a patron",
    description="Answers: 'What happened to patron #12847's account?'",
)
async def get_patron_history(
    patron_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OperationsAuditResponse:
    """Get complete audit trail for a specific patron across all operation types."""
    start_dt, end_dt = _normalize_dates(start_date, end_date, default_days_back=365)

    conditions = [
        OperationsAuditLog.patron_id == patron_id,
        OperationsAuditLog.created_at >= start_dt,
        OperationsAuditLog.created_at <= end_dt,
    ]
    where = and_(*conditions)

    count_result = await db.execute(
        select(func.count(OperationsAuditLog.id)).where(where)
    )
    total = count_result.scalar() or 0

    query = (
        select(OperationsAuditLog)
        .where(where)
        .order_by(desc(OperationsAuditLog.created_at))
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    result = await db.execute(query)
    entries = [
        OperationsAuditEntry(
            id=e.id, category=e.category, operation_type=e.operation_type,
            patron_id=e.patron_id, patron_identifier=e.patron_identifier,
            staff_id=e.staff_id, staff_identifier=e.staff_identifier,
            item_id=e.item_id, item_identifier=e.item_identifier,
            checkout_id=e.checkout_id, fine_id=e.fine_id, hold_id=e.hold_id,
            amount_cents=e.amount_cents, before_state=e.before_state,
            after_state=e.after_state, reason=e.reason,
            correlation_id=e.correlation_id, created_at=e.created_at,
        )
        for e in result.scalars().all()
    ]

    return OperationsAuditResponse(
        total=total, page=pagination.page, page_size=pagination.page_size,
        total_pages=calculate_total_pages(total, pagination.page_size),
        entries=entries,
    )


@router.get(
    "/fine-waivers/by-staff",
    response_model=FineWaiverSummaryResponse,
    summary="Fine waivers aggregated by staff member",
    description="Answers: 'Which staff member waived $50K in fines?'",
)
async def get_fine_waivers_by_staff(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> FineWaiverSummaryResponse:
    """Aggregate fine waiver amounts by staff member over a date range."""
    start_dt, end_dt = _normalize_dates(start_date, end_date, default_days_back=365)

    query = (
        select(
            OperationsAuditLog.staff_id,
            OperationsAuditLog.staff_identifier,
            func.coalesce(func.sum(OperationsAuditLog.amount_cents), 0).label("total_cents"),
            func.count(OperationsAuditLog.id).label("waiver_count"),
        )
        .where(
            OperationsAuditLog.operation_type == OperationType.FINE_WAIVED.value,
            OperationsAuditLog.created_at >= start_dt,
            OperationsAuditLog.created_at <= end_dt,
        )
        .group_by(OperationsAuditLog.staff_id, OperationsAuditLog.staff_identifier)
        .order_by(desc("total_cents"))
    )
    result = await db.execute(query)
    rows = result.all()

    summaries = []
    grand_total = 0
    for row in rows:
        total = int(row.total_cents)
        grand_total += total
        summaries.append(FineWaiverSummary(
            staff_id=row.staff_id,
            staff_identifier=row.staff_identifier,
            total_waived_cents=total,
            total_waived_display=f"${total / 100:,.2f}",
            waiver_count=int(row.waiver_count),
        ))

    return FineWaiverSummaryResponse(
        start_date=start_dt,
        end_date=end_dt,
        summaries=summaries,
        grand_total_cents=grand_total,
        grand_total_display=f"${grand_total / 100:,.2f}",
    )


@router.get(
    "/circulation-trends",
    response_model=CirculationTrendResponse,
    summary="Daily circulation statistics",
    description="Answers: 'Why did circulation drop 40% in March 2027?'",
)
async def get_circulation_trends(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CirculationTrendResponse:
    """Get daily circulation counts for trend analysis."""
    start_dt, end_dt = _normalize_dates(start_date, end_date, default_days_back=90)

    # Query daily counts grouped by operation type
    day_col = func.date(OperationsAuditLog.created_at).label("day")
    query = (
        select(
            day_col,
            OperationsAuditLog.operation_type,
            func.count(OperationsAuditLog.id).label("cnt"),
        )
        .where(
            OperationsAuditLog.category == OperationCategory.CIRCULATION.value,
            OperationsAuditLog.created_at >= start_dt,
            OperationsAuditLog.created_at <= end_dt,
        )
        .group_by(day_col, OperationsAuditLog.operation_type)
        .order_by(day_col)
    )
    result = await db.execute(query)
    rows = result.all()

    # Build daily summaries
    daily_data: dict[str, dict[str, int]] = {}
    for row in rows:
        d = str(row.day)
        if d not in daily_data:
            daily_data[d] = {"checkouts": 0, "returns": 0, "renewals": 0, "holds_placed": 0, "holds_cancelled": 0}
        op = row.operation_type
        if op == OperationType.CHECKOUT_CREATED.value:
            daily_data[d]["checkouts"] = int(row.cnt)
        elif op == OperationType.CHECKOUT_RETURNED.value:
            daily_data[d]["returns"] = int(row.cnt)
        elif op == OperationType.CHECKOUT_RENEWED.value:
            daily_data[d]["renewals"] = int(row.cnt)
        elif op == OperationType.HOLD_PLACED.value:
            daily_data[d]["holds_placed"] = int(row.cnt)
        elif op == OperationType.HOLD_CANCELLED.value:
            daily_data[d]["holds_cancelled"] = int(row.cnt)

    summaries = [
        CirculationDailySummary(date=d, **counts)
        for d, counts in sorted(daily_data.items())
    ]

    total_checkouts = sum(s.checkouts for s in summaries)
    total_returns = sum(s.returns for s in summaries)

    return CirculationTrendResponse(
        start_date=str(start_dt.date()),
        end_date=str(end_dt.date()),
        daily_summaries=summaries,
        total_checkouts=total_checkouts,
        total_returns=total_returns,
    )


@router.get(
    "/policy-changes",
    response_model=PolicyChangeResponse,
    summary="Policy change history",
    description="Answers: 'When did we change the checkout limit policy?'",
)
async def get_policy_changes(
    policy_type: Optional[str] = Query(None, description="Filter by policy type"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PolicyChangeResponse:
    """List policy changes with full before/after snapshots."""
    start_dt, end_dt = _normalize_dates(start_date, end_date, default_days_back=365)

    conditions = [
        PolicyChangeLog.created_at >= start_dt,
        PolicyChangeLog.created_at <= end_dt,
    ]
    if policy_type:
        conditions.append(PolicyChangeLog.policy_type == policy_type)

    where = and_(*conditions)

    count_result = await db.execute(
        select(func.count(PolicyChangeLog.id)).where(where)
    )
    total = count_result.scalar() or 0

    query = (
        select(PolicyChangeLog)
        .where(where)
        .order_by(desc(PolicyChangeLog.created_at))
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    result = await db.execute(query)
    entries = [
        PolicyChangeEntry(
            id=e.id, policy_type=e.policy_type, policy_name=e.policy_name,
            changed_by_staff_id=e.changed_by_staff_id,
            changed_by_identifier=e.changed_by_identifier,
            before_value=e.before_value, after_value=e.after_value,
            fields_changed=e.fields_changed, reason=e.reason,
            created_at=e.created_at,
        )
        for e in result.scalars().all()
    ]

    return PolicyChangeResponse(
        total=total, page=pagination.page, page_size=pagination.page_size,
        total_pages=calculate_total_pages(total, pagination.page_size),
        entries=entries,
    )


@router.get(
    "/items/{item_id}/history",
    response_model=OperationsAuditResponse,
    summary="Get complete history for a catalog item",
    description="Answers: 'Why does this item have no checkout history?'",
)
async def get_item_history(
    item_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OperationsAuditResponse:
    """Get complete audit trail for a specific catalog item."""
    start_dt, end_dt = _normalize_dates(start_date, end_date, default_days_back=365 * 3)

    conditions = [
        OperationsAuditLog.item_id == item_id,
        OperationsAuditLog.created_at >= start_dt,
        OperationsAuditLog.created_at <= end_dt,
    ]
    where = and_(*conditions)

    count_result = await db.execute(
        select(func.count(OperationsAuditLog.id)).where(where)
    )
    total = count_result.scalar() or 0

    query = (
        select(OperationsAuditLog)
        .where(where)
        .order_by(desc(OperationsAuditLog.created_at))
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    result = await db.execute(query)
    entries = [
        OperationsAuditEntry(
            id=e.id, category=e.category, operation_type=e.operation_type,
            patron_id=e.patron_id, patron_identifier=e.patron_identifier,
            staff_id=e.staff_id, staff_identifier=e.staff_identifier,
            item_id=e.item_id, item_identifier=e.item_identifier,
            checkout_id=e.checkout_id, fine_id=e.fine_id, hold_id=e.hold_id,
            amount_cents=e.amount_cents, before_state=e.before_state,
            after_state=e.after_state, reason=e.reason,
            correlation_id=e.correlation_id, created_at=e.created_at,
        )
        for e in result.scalars().all()
    ]

    return OperationsAuditResponse(
        total=total, page=pagination.page, page_size=pagination.page_size,
        total_pages=calculate_total_pages(total, pagination.page_size),
        entries=entries,
    )
