# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff Analytics API Endpoints

Provides endpoints for the Staff Analytics Dashboard page (/staff/analytics).
Includes circulation trends, popular items, fine analytics, patron statistics,
and collection usage analytics.

All endpoints require STAFF+ role authentication.
"""

from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.catalog import CatalogItem
from ...models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ...models.fine import Fine, FinePaymentHistory, FineStatus, PaymentMethod
from ...models.user import PatronStatus, User, UserRole
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["staff-analytics"])


@router.get("")
async def analytics_overview(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    """Analytics overview - lists available analytics endpoints."""
    return {
        "available_reports": [
            {"name": "Circulation Trends", "path": "/analytics/circulation/trends"},
            {"name": "Popular Items", "path": "/analytics/popular-items"},
            {"name": "Fines Summary", "path": "/analytics/fines/summary"},
            {"name": "Patron Stats", "path": "/analytics/patrons/stats"},
            {"name": "Collection Usage", "path": "/analytics/collection/usage"},
        ]
    }


def _parse_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def _to_datetime(d: date) -> datetime:
    return datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    return float(val)


# =============================================================================
# 1. Circulation Trends
# =============================================================================


@router.get("/circulation/trends")
async def get_circulation_trends(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get circulation trend data for the staff analytics dashboard."""


    start = _parse_date(start_date)
    end = _parse_date(end_date)
    start_dt = _to_datetime(start)
    end_dt = _to_datetime(end + timedelta(days=1))
    period_days = (end - start).days or 1

    # Previous period for comparison
    prev_start_dt = _to_datetime(start - timedelta(days=period_days))
    prev_end_dt = start_dt

    # Current period checkouts
    checkout_count_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.checked_out_at >= start_dt,
            Checkout.checked_out_at < end_dt,
        )
    )
    total_checkouts = checkout_count_result.scalar() or 0

    # Current period returns
    return_count_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.returned_at >= start_dt,
            Checkout.returned_at < end_dt,
            Checkout.returned_at.isnot(None),
        )
    )
    total_returns = return_count_result.scalar() or 0

    # Previous period checkouts for comparison
    prev_checkout_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.checked_out_at >= prev_start_dt,
            Checkout.checked_out_at < prev_end_dt,
        )
    )
    prev_checkouts = prev_checkout_result.scalar() or 0

    # Previous period returns for comparison
    prev_return_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.returned_at >= prev_start_dt,
            Checkout.returned_at < prev_end_dt,
            Checkout.returned_at.isnot(None),
        )
    )
    prev_returns = prev_return_result.scalar() or 0

    # Current overdue count
    overdue_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.status == CheckoutStatus.overdue,
        )
    )
    overdue_count = overdue_result.scalar() or 0

    # Previous period overdue (approximate: overdue at the start of current period)
    prev_overdue_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.due_date < start_dt,
            Checkout.returned_at.is_(None),
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
    )
    prev_overdue = prev_overdue_result.scalar() or 0

    # Calculate change percentages
    def pct_change(current: int, previous: int) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        change = round(((current - previous) / previous) * 100, 1)
        return max(-999.9, min(999.9, change))

    checkout_change = pct_change(total_checkouts, prev_checkouts)
    return_change = pct_change(total_returns, prev_returns)
    overdue_change = pct_change(overdue_count, prev_overdue)

    # Daily trend data
    checkout_by_day = await db.execute(
        select(
            func.date(Checkout.checked_out_at).label("day"),
            func.count(Checkout.id).label("count"),
        )
        .where(Checkout.checked_out_at >= start_dt, Checkout.checked_out_at < end_dt)
        .group_by(func.date(Checkout.checked_out_at))
    )
    checkout_map = {row[0]: row[1] for row in checkout_by_day.all()}

    return_by_day = await db.execute(
        select(
            func.date(Checkout.returned_at).label("day"),
            func.count(Checkout.id).label("count"),
        )
        .where(
            Checkout.returned_at >= start_dt,
            Checkout.returned_at < end_dt,
            Checkout.returned_at.isnot(None),
        )
        .group_by(func.date(Checkout.returned_at))
    )
    return_map = {row[0]: row[1] for row in return_by_day.all()}

    trends = []
    current_date = start
    while current_date <= end:
        trends.append({
            "date": current_date.isoformat(),
            "checkouts": checkout_map.get(current_date, 0),
            "returns": return_map.get(current_date, 0),
        })
        current_date += timedelta(days=1)

    # Day of week aggregation
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    dow_checkouts = {i: 0 for i in range(7)}
    dow_returns = {i: 0 for i in range(7)}
    dow_counts = {i: 0 for i in range(7)}

    for t in trends:
        d = _parse_date(t["date"])
        dow = d.weekday()
        dow_checkouts[dow] += t["checkouts"]
        dow_returns[dow] += t["returns"]
        dow_counts[dow] += 1

    by_day_of_week = []
    for i in range(7):
        count = dow_counts[i] or 1
        by_day_of_week.append({
            "day": day_names[i],
            "checkouts": round(dow_checkouts[i] / count),
            "returns": round(dow_returns[i] / count),
        })

    daily_average = total_checkouts / period_days if period_days > 0 else 0

    return {
        "totalCheckouts": total_checkouts,
        "totalReturns": total_returns,
        "dailyAverage": round(daily_average, 1),
        "overdueCount": overdue_count,
        "checkoutChange": checkout_change,
        "returnChange": return_change,
        "overdueChange": overdue_change,
        "trends": trends,
        "byDayOfWeek": by_day_of_week,
    }


# =============================================================================
# 2. Popular Items
# =============================================================================


@router.get("/popular-items")
async def get_popular_items(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get popular items data for the staff analytics dashboard."""


    start_dt = _to_datetime(_parse_date(start_date))
    end_dt = _to_datetime(_parse_date(end_date) + timedelta(days=1))
    period_days = (_parse_date(end_date) - _parse_date(start_date)).days or 1

    # Previous period for growth calculation
    prev_start_dt = _to_datetime(_parse_date(start_date) - timedelta(days=period_days))
    prev_end_dt = start_dt

    # Top checkouts
    top_checkouts_result = await db.execute(
        select(
            CatalogItem.id,
            CatalogItem.title,
            CatalogItem.author,
            CatalogItem.item_type,
            func.count(Checkout.id).label("checkout_count"),
        )
        .join(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(Checkout.checked_out_at >= start_dt, Checkout.checked_out_at < end_dt)
        .group_by(CatalogItem.id, CatalogItem.title, CatalogItem.author, CatalogItem.item_type)
        .order_by(func.count(Checkout.id).desc())
        .limit(10)
    )
    top_checkouts = [
        {
            "itemId": row[0],
            "title": row[1] or "Unknown",
            "author": row[2] or "Unknown",
            "count": row[4],
            "category": (row[3] or "other"),
        }
        for row in top_checkouts_result.all()
    ]

    # Top holds
    top_holds_result = await db.execute(
        select(
            CatalogItem.id,
            CatalogItem.title,
            CatalogItem.author,
            CatalogItem.item_type,
            func.count(Hold.id).label("hold_count"),
        )
        .join(CatalogItem, Hold.item_id == CatalogItem.id)
        .where(Hold.created_at >= start_dt, Hold.created_at < end_dt)
        .group_by(CatalogItem.id, CatalogItem.title, CatalogItem.author, CatalogItem.item_type)
        .order_by(func.count(Hold.id).desc())
        .limit(10)
    )
    top_holds = [
        {
            "itemId": row[0],
            "title": row[1] or "Unknown",
            "author": row[2] or "Unknown",
            "count": row[4],
            "category": (row[3] or "other"),
        }
        for row in top_holds_result.all()
    ]

    # Trending items (biggest growth vs previous period)
    current_counts_result = await db.execute(
        select(
            CatalogItem.id,
            CatalogItem.title,
            CatalogItem.author,
            CatalogItem.item_type,
            func.count(Checkout.id).label("current_count"),
        )
        .join(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(Checkout.checked_out_at >= start_dt, Checkout.checked_out_at < end_dt)
        .group_by(CatalogItem.id, CatalogItem.title, CatalogItem.author, CatalogItem.item_type)
        .having(func.count(Checkout.id) >= 2)
        .order_by(func.count(Checkout.id).desc())
        .limit(50)
    )
    current_items = current_counts_result.all()

    trending = []
    if current_items:
        item_ids = [row[0] for row in current_items]
        prev_counts_result = await db.execute(
            select(
                Checkout.item_id,
                func.count(Checkout.id).label("prev_count"),
            )
            .where(
                Checkout.item_id.in_(item_ids),
                Checkout.checked_out_at >= prev_start_dt,
                Checkout.checked_out_at < prev_end_dt,
            )
            .group_by(Checkout.item_id)
        )
        prev_map = {row[0]: row[1] for row in prev_counts_result.all()}

        for row in current_items:
            item_id, title, author, item_type, current_count = row
            prev_count = prev_map.get(item_id, 0)
            if prev_count == 0:
                growth = 100.0
            else:
                growth = ((current_count - prev_count) / prev_count) * 100
            if growth > 0:
                trending.append({
                    "itemId": item_id,
                    "title": title or "Unknown",
                    "author": author or "Unknown",
                    "count": current_count,
                    "category": (item_type or "other"),
                    "growthPercent": round(growth, 1),
                })

        trending.sort(key=lambda x: x["growthPercent"], reverse=True)
        trending = trending[:10]

    # By category
    category_result = await db.execute(
        select(
            CatalogItem.item_type,
            func.count(Checkout.id).label("count"),
        )
        .join(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(Checkout.checked_out_at >= start_dt, Checkout.checked_out_at < end_dt)
        .group_by(CatalogItem.item_type)
        .order_by(func.count(Checkout.id).desc())
    )
    by_category = [
        {"category": (row[0] or "other"), "count": row[1]}
        for row in category_result.all()
    ]

    return {
        "topCheckouts": top_checkouts,
        "topHolds": top_holds,
        "trending": trending,
        "byCategory": by_category,
    }


# =============================================================================
# 3. Fines Summary
# =============================================================================


@router.get("/fines/summary")
async def get_fines_summary(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get fines summary for the staff analytics dashboard."""


    start = _parse_date(start_date)
    end = _parse_date(end_date)
    start_dt = _to_datetime(start)
    end_dt = _to_datetime(end + timedelta(days=1))
    period_days = (end - start).days or 1

    prev_start_dt = _to_datetime(start - timedelta(days=period_days))
    prev_end_dt = start_dt

    # Outstanding fines total
    outstanding_result = await db.execute(
        select(func.sum(Fine.amount - Fine.amount_paid)).where(
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
        )
    )
    total_outstanding = _safe_float(outstanding_result.scalar())

    # Collected in period (payments made)
    collected_result = await db.execute(
        select(func.sum(FinePaymentHistory.amount)).where(
            FinePaymentHistory.created_at >= start_dt,
            FinePaymentHistory.created_at < end_dt,
        )
    )
    total_collected = _safe_float(collected_result.scalar())

    # Previous period collected for comparison
    prev_collected_result = await db.execute(
        select(func.sum(FinePaymentHistory.amount)).where(
            FinePaymentHistory.created_at >= prev_start_dt,
            FinePaymentHistory.created_at < prev_end_dt,
        )
    )
    prev_collected = _safe_float(prev_collected_result.scalar())

    # Waived in period
    waived_result = await db.execute(
        select(func.sum(Fine.amount)).where(
            Fine.status == FineStatus.waived,
            Fine.waived_at >= start_dt,
            Fine.waived_at < end_dt,
        )
    )
    total_waived = _safe_float(waived_result.scalar())

    # Patrons with outstanding fines
    patrons_with_fines_result = await db.execute(
        select(func.count(distinct(Fine.user_id))).where(
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
        )
    )
    patrons_with_fines = patrons_with_fines_result.scalar() or 0

    # Collection change percentage
    if prev_collected == 0:
        collection_change = 100.0 if total_collected > 0 else 0.0
    else:
        collection_change = round(((total_collected - prev_collected) / prev_collected) * 100, 1)

    # Trend data: group payments and new fines by week
    # Collected by week
    collected_by_week = await db.execute(
        select(
            func.date(FinePaymentHistory.created_at).label("day"),
            func.sum(FinePaymentHistory.amount).label("amount"),
        )
        .where(
            FinePaymentHistory.created_at >= start_dt,
            FinePaymentHistory.created_at < end_dt,
        )
        .group_by(func.date(FinePaymentHistory.created_at))
    )
    collected_map = {row[0]: _safe_float(row[1]) for row in collected_by_week.all()}

    # Assessed (new fines) by day
    assessed_by_day = await db.execute(
        select(
            func.date(Fine.created_at).label("day"),
            func.sum(Fine.amount).label("amount"),
        )
        .where(
            Fine.created_at >= start_dt,
            Fine.created_at < end_dt,
        )
        .group_by(func.date(Fine.created_at))
    )
    assessed_map = {row[0]: _safe_float(row[1]) for row in assessed_by_day.all()}

    # Build weekly trend points
    trends = []
    current_date = start
    week_collected = 0.0
    week_assessed = 0.0
    week_start = start

    while current_date <= end:
        week_collected += collected_map.get(current_date, 0.0)
        week_assessed += assessed_map.get(current_date, 0.0)

        # Every 7 days or at the end, emit a data point
        if (current_date - week_start).days >= 6 or current_date == end:
            trends.append({
                "date": week_start.isoformat(),
                "collected": round(week_collected, 2),
                "assessed": round(week_assessed, 2),
            })
            week_collected = 0.0
            week_assessed = 0.0
            week_start = current_date + timedelta(days=1)

        current_date += timedelta(days=1)

    return {
        "totalOutstanding": round(total_outstanding, 2),
        "totalCollected": round(total_collected, 2),
        "totalWaived": round(total_waived, 2),
        "patronsWithFines": patrons_with_fines,
        "collectionChange": collection_change,
        "trends": trends,
    }


# =============================================================================
# 4. Fine Aging
# =============================================================================


@router.get("/fines/aging")
async def get_fine_aging(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get outstanding fines grouped by age bracket."""


    now = datetime.now(timezone.utc)

    # Get all unpaid/partial fines with their creation date
    fines_result = await db.execute(
        select(Fine.created_at, Fine.amount, Fine.amount_paid).where(
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
        )
    )
    fines = fines_result.all()

    brackets = {
        "0-30 days": 0.0,
        "31-60 days": 0.0,
        "61-90 days": 0.0,
        "91-180 days": 0.0,
        "180+ days": 0.0,
    }

    total_outstanding = 0.0
    for created_at, amount, amount_paid in fines:
        balance = float(amount) - float(amount_paid or 0)
        if balance <= 0:
            continue
        total_outstanding += balance

        if created_at is None:
            brackets["180+ days"] += balance
            continue

        days_old = (now - created_at).days
        if days_old <= 30:
            brackets["0-30 days"] += balance
        elif days_old <= 60:
            brackets["31-60 days"] += balance
        elif days_old <= 90:
            brackets["61-90 days"] += balance
        elif days_old <= 180:
            brackets["91-180 days"] += balance
        else:
            brackets["180+ days"] += balance

    bracket_list = [
        {"bracket": k, "amount": round(v, 2), "count": 0}
        for k, v in brackets.items()
    ]

    # Get counts per bracket
    for created_at, amount, amount_paid in fines:
        balance = float(amount) - float(amount_paid or 0)
        if balance <= 0:
            continue
        if created_at is None:
            bracket_list[4]["count"] += 1
            continue
        days_old = (now - created_at).days
        if days_old <= 30:
            bracket_list[0]["count"] += 1
        elif days_old <= 60:
            bracket_list[1]["count"] += 1
        elif days_old <= 90:
            bracket_list[2]["count"] += 1
        elif days_old <= 180:
            bracket_list[3]["count"] += 1
        else:
            bracket_list[4]["count"] += 1

    return {
        "brackets": bracket_list,
        "totalOutstanding": round(total_outstanding, 2),
    }


# =============================================================================
# 5. Payment Methods
# =============================================================================


@router.get("/fines/payment-methods")
async def get_payment_methods(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get payment method breakdown for the staff analytics dashboard."""


    start_dt = _to_datetime(_parse_date(start_date))
    end_dt = _to_datetime(_parse_date(end_date) + timedelta(days=1))

    result = await db.execute(
        select(
            FinePaymentHistory.payment_method,
            func.sum(FinePaymentHistory.amount).label("total"),
            func.count(FinePaymentHistory.id).label("count"),
        )
        .where(
            FinePaymentHistory.created_at >= start_dt,
            FinePaymentHistory.created_at < end_dt,
        )
        .group_by(FinePaymentHistory.payment_method)
        .order_by(func.sum(FinePaymentHistory.amount).desc())
    )
    rows = result.all()

    total_amount = sum(_safe_float(row[1]) for row in rows)

    methods = []
    for row in rows:
        method_name = row[0] if isinstance(row[0], str) else (row[0].value if row[0] else "other")
        amount = _safe_float(row[1])
        methods.append({
            "method": method_name.capitalize(),
            "amount": round(amount, 2),
            "count": row[2],
            "percentage": round((amount / total_amount * 100) if total_amount > 0 else 0, 1),
        })

    return {
        "methods": methods,
        "totalAmount": round(total_amount, 2),
    }


# =============================================================================
# 6. Waived Fines
# =============================================================================


@router.get("/fines/waived")
async def get_waived_fines(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get waived fines summary for the staff analytics dashboard."""


    start_dt = _to_datetime(_parse_date(start_date))
    end_dt = _to_datetime(_parse_date(end_date) + timedelta(days=1))

    # Totals
    waived_result = await db.execute(
        select(
            func.sum(Fine.amount).label("total"),
            func.count(Fine.id).label("count"),
        ).where(
            Fine.status == FineStatus.waived,
            Fine.waived_at >= start_dt,
            Fine.waived_at < end_dt,
        )
    )
    row = waived_result.one()
    total_waived = _safe_float(row[0])
    waived_count = row[1] or 0
    avg_amount = (total_waived / waived_count) if waived_count > 0 else 0.0

    # Top waiver reasons (from fine_type + notes)
    reasons_result = await db.execute(
        select(
            Fine.fine_type,
            func.count(Fine.id).label("count"),
            func.sum(Fine.amount).label("amount"),
        )
        .where(
            Fine.status == FineStatus.waived,
            Fine.waived_at >= start_dt,
            Fine.waived_at < end_dt,
        )
        .group_by(Fine.fine_type)
        .order_by(func.count(Fine.id).desc())
    )

    reason_labels = {
        "overdue": "Overdue fine waiver",
        "lost_item": "Lost item charge waiver",
        "damaged_item": "Damaged item charge waiver",
        "other": "Other fee waiver",
    }

    top_reasons = []
    for row in reasons_result.all():
        fine_type = row[0] if isinstance(row[0], str) else (row[0].value if row[0] else "other")
        top_reasons.append({
            "reason": reason_labels.get(fine_type, fine_type),
            "count": row[1],
            "amount": round(_safe_float(row[2]), 2),
        })

    return {
        "totalWaived": round(total_waived, 2),
        "count": waived_count,
        "averageAmount": round(avg_amount, 2),
        "topReasons": top_reasons,
    }


# =============================================================================
# 7. Patron Statistics
# =============================================================================


@router.get("/patrons/stats")
async def get_patron_stats(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get patron statistics for the staff analytics dashboard."""


    start = _parse_date(start_date)
    end = _parse_date(end_date)
    start_dt = _to_datetime(start)
    end_dt = _to_datetime(end + timedelta(days=1))
    period_days = (end - start).days or 1

    prev_start_dt = _to_datetime(start - timedelta(days=period_days))
    prev_end_dt = start_dt

    patron_roles = [UserRole.PATRON, UserRole.CHILD, UserRole.HOMEBOND]

    # Total patrons
    total_result = await db.execute(
        select(func.count(User.id)).where(
            User.role.in_(patron_roles),
            User.is_active.is_(True),
        )
    )
    total_patrons = total_result.scalar() or 0

    # New registrations in period
    new_reg_result = await db.execute(
        select(func.count(User.id)).where(
            User.role.in_(patron_roles),
            User.created_at >= start_dt,
            User.created_at < end_dt,
        )
    )
    new_registrations = new_reg_result.scalar() or 0

    # Previous period registrations
    prev_reg_result = await db.execute(
        select(func.count(User.id)).where(
            User.role.in_(patron_roles),
            User.created_at >= prev_start_dt,
            User.created_at < prev_end_dt,
        )
    )
    prev_registrations = prev_reg_result.scalar() or 0

    if prev_registrations == 0:
        registration_change = 100.0 if new_registrations > 0 else 0.0
    else:
        registration_change = round(
            ((new_registrations - prev_registrations) / prev_registrations) * 100, 1
        )

    # Active patrons (had a checkout in last 30 days)
    thirty_days_ago = _to_datetime(end - timedelta(days=30))
    active_result = await db.execute(
        select(func.count(distinct(Checkout.user_id))).where(
            Checkout.checked_out_at >= thirty_days_ago,
            Checkout.checked_out_at < end_dt,
        )
    )
    active_patrons = active_result.scalar() or 0

    # Blocked patrons
    blocked_result = await db.execute(
        select(func.count(User.id)).where(
            User.role.in_(patron_roles),
            User.patron_status == PatronStatus.BLOCKED,
        )
    )
    blocked_patrons = blocked_result.scalar() or 0

    # Registration trends (daily)
    reg_trends_result = await db.execute(
        select(
            func.date(User.created_at).label("day"),
            func.count(User.id).label("count"),
        )
        .where(
            User.role.in_(patron_roles),
            User.created_at >= start_dt,
            User.created_at < end_dt,
        )
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )
    reg_map = {row[0]: row[1] for row in reg_trends_result.all()}

    # Build weekly registration trend
    registration_trends = []
    current_date = start
    week_count = 0
    week_start = start

    while current_date <= end:
        week_count += reg_map.get(current_date, 0)

        if (current_date - week_start).days >= 6 or current_date == end:
            registration_trends.append({
                "date": week_start.isoformat(),
                "registrations": week_count,
            })
            week_count = 0
            week_start = current_date + timedelta(days=1)

        current_date += timedelta(days=1)

    # Activity distribution (checkouts per patron in period)
    activity_result = await db.execute(
        select(
            Checkout.user_id,
            func.count(Checkout.id).label("checkout_count"),
        )
        .where(
            Checkout.checked_out_at >= start_dt,
            Checkout.checked_out_at < end_dt,
        )
        .group_by(Checkout.user_id)
    )
    patron_activity = [row[1] for row in activity_result.all()]

    # Bucket into ranges
    ranges = [
        ("1-2 items", 1, 2),
        ("3-5 items", 3, 5),
        ("6-10 items", 6, 10),
        ("11-20 items", 11, 20),
        ("21+ items", 21, 99999),
    ]

    activity_distribution = []
    for label, low, high in ranges:
        count = sum(1 for c in patron_activity if low <= c <= high)
        activity_distribution.append({"range": label, "count": count})

    # Top active patrons
    top_patrons_result = await db.execute(
        select(
            Checkout.user_id,
            User.first_name,
            User.last_name,
            func.count(Checkout.id).label("checkout_count"),
        )
        .join(User, Checkout.user_id == User.id)
        .where(
            Checkout.checked_out_at >= start_dt,
            Checkout.checked_out_at < end_dt,
        )
        .group_by(Checkout.user_id, User.first_name, User.last_name)
        .order_by(func.count(Checkout.id).desc())
        .limit(10)
    )
    top_active_patrons = [
        {
            "patronId": row[0],
            "name": f"{row[1] or ''} {row[2] or ''}".strip() or "Unknown",
            "checkoutCount": row[3],
        }
        for row in top_patrons_result.all()
    ]

    return {
        "totalPatrons": total_patrons,
        "newRegistrations": new_registrations,
        "activePatrons": active_patrons,
        "blockedPatrons": blocked_patrons,
        "registrationChange": registration_change,
        "registrationTrends": registration_trends,
        "activityDistribution": activity_distribution,
        "topActivePatrons": top_active_patrons,
    }


# =============================================================================
# 8. Collection Usage
# =============================================================================


@router.get("/collection/usage")
async def get_collection_usage(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get collection usage data for the staff analytics dashboard."""


    start_dt = _to_datetime(_parse_date(start_date))
    end_dt = _to_datetime(_parse_date(end_date) + timedelta(days=1))

    # Total titles and copies
    totals_result = await db.execute(
        select(
            func.count(CatalogItem.id).label("total_titles"),
        )
    )
    total_titles = totals_result.scalar() or 0

    # Total copies (count of items, since each CatalogItem row is effectively a title)
    # Use total_checkouts to estimate copies, or just use title count
    total_copies = total_titles  # Simplified; in reality would count ItemCopy

    # Total checkouts in period
    checkout_count_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.checked_out_at >= start_dt,
            Checkout.checked_out_at < end_dt,
        )
    )
    total_checkouts = checkout_count_result.scalar() or 0

    # Turnover rate
    turnover_rate = (total_checkouts / total_copies) if total_copies > 0 else 0.0

    # Items never circulated (no checkout records in database)
    items_with_checkouts = (
        select(distinct(Checkout.item_id).label("item_id"))
        .where(Checkout.item_id.isnot(None))
        .scalar_subquery()
    )
    never_circ_result = await db.execute(
        select(func.count(CatalogItem.id)).where(
            ~CatalogItem.id.in_(items_with_checkouts)
        )
    )
    never_circulated = never_circ_result.scalar() or 0

    # By category
    category_result = await db.execute(
        select(
            CatalogItem.item_type,
            func.count(CatalogItem.id).label("titles"),
            func.sum(
                case(
                    (
                        and_(
                            Checkout.checked_out_at >= start_dt,
                            Checkout.checked_out_at < end_dt,
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("checkouts"),
        )
        .outerjoin(Checkout, Checkout.item_id == CatalogItem.id)
        .group_by(CatalogItem.item_type)
        .order_by(func.count(CatalogItem.id).desc())
    )
    categories = category_result.all()

    by_category = []
    for row in categories:
        cat_type = row[0] if isinstance(row[0], str) else (row[0] if row[0] else "other")
        titles = row[1] or 0
        checkouts = row[2] or 0
        copies = titles  # Simplified
        cat_turnover = (checkouts / copies) if copies > 0 else 0.0
        pct = (titles / total_titles * 100) if total_titles > 0 else 0.0

        by_category.append({
            "category": cat_type,
            "titles": titles,
            "copies": copies,
            "checkouts": checkouts,
            "turnoverRate": round(cat_turnover, 2),
            "percentOfCollection": round(pct, 1),
        })

    return {
        "totalTitles": total_titles,
        "totalCopies": total_copies,
        "turnoverRate": round(turnover_rate, 2),
        "neverCirculated": never_circulated,
        "byCategory": by_category,
    }


@router.get("/collection/details")
async def get_collection_details(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Extended collection analytics: condition breakdown, top/least circulated,
    avg age, and cost-per-circulation."""
    from ...models.inventory import ItemCopy, ItemCondition

    start_dt = _to_datetime(_parse_date(start_date))
    end_dt = _to_datetime(_parse_date(end_date) + timedelta(days=1))
    current_year = date.today().year

    # --- Condition distribution (from ItemCopy) ---
    cond_result = await db.execute(
        select(ItemCopy.condition, func.count(ItemCopy.id))
        .where(ItemCopy.condition != ItemCondition.WITHDRAWN)
        .group_by(ItemCopy.condition)
    )
    by_condition = {str(row[0]): row[1] for row in cond_result.all()}

    # --- Avg age (years) based on publication_year ---
    avg_age_result = await db.execute(
        select(func.avg(current_year - CatalogItem.publication_year)).where(
            CatalogItem.publication_year.isnot(None),
            CatalogItem.publication_year > 0,
        )
    )
    avg_age = avg_age_result.scalar()
    avg_age_years = round(float(avg_age), 1) if avg_age else 0.0

    # --- Avg checkouts per item (in date range) ---
    total_items_result = await db.execute(select(func.count(CatalogItem.id)))
    total_items = total_items_result.scalar() or 0

    total_checkouts_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.checked_out_at >= start_dt,
            Checkout.checked_out_at < end_dt,
        )
    )
    total_checkouts = total_checkouts_result.scalar() or 0
    avg_checkouts_per_item = round(total_checkouts / total_items, 2) if total_items else 0.0

    # --- Top 10 most-circulated ---
    top_result = await db.execute(
        select(
            Checkout.item_id,
            func.count(Checkout.id).label("cnt"),
            func.max(Checkout.checked_out_at).label("last_checkout"),
        )
        .where(
            Checkout.checked_out_at >= start_dt,
            Checkout.checked_out_at < end_dt,
            Checkout.item_id.isnot(None),
        )
        .group_by(Checkout.item_id)
        .order_by(func.count(Checkout.id).desc())
        .limit(10)
    )
    top_rows = top_result.all()
    top_ids = [r[0] for r in top_rows]

    # --- Bottom 10 (least-circulated, at least 1 checkout) ---
    bottom_result = await db.execute(
        select(
            Checkout.item_id,
            func.count(Checkout.id).label("cnt"),
            func.max(Checkout.checked_out_at).label("last_checkout"),
        )
        .where(
            Checkout.checked_out_at >= start_dt,
            Checkout.checked_out_at < end_dt,
            Checkout.item_id.isnot(None),
        )
        .group_by(Checkout.item_id)
        .order_by(func.count(Checkout.id).asc())
        .limit(10)
    )
    bottom_rows = bottom_result.all()
    bottom_ids = [r[0] for r in bottom_rows]

    # Fetch catalog details for all referenced items
    all_ids = list(set(top_ids + bottom_ids))
    catalog_map: dict = {}
    if all_ids:
        cat_result = await db.execute(
            select(CatalogItem.id, CatalogItem.title, CatalogItem.author).where(
                CatalogItem.id.in_(all_ids)
            )
        )
        for row in cat_result.all():
            catalog_map[row[0]] = {"title": row[1], "author": row[2]}

    def _build_items(rows):
        items = []
        for item_id, cnt, last_co in rows:
            cat = catalog_map.get(item_id, {})
            items.append({
                "catalogItemId": item_id,
                "title": cat.get("title", "Unknown"),
                "author": cat.get("author"),
                "checkoutCount": cnt,
                "lastCheckout": last_co.isoformat() if last_co else None,
            })
        return items

    top_items = _build_items(top_rows)
    bottom_items = _build_items(bottom_rows)

    # --- Cost per circulation ---
    cost_result = await db.execute(
        select(
            func.sum(ItemCopy.replacement_cost),
            func.count(distinct(ItemCopy.id)),
        ).where(ItemCopy.replacement_cost.isnot(None), ItemCopy.replacement_cost > 0)
    )
    cost_row = cost_result.one()
    total_replacement_cost = float(cost_row[0]) if cost_row[0] else 0.0
    copies_with_cost = cost_row[1] or 0

    if copies_with_cost > 0:
        costed_item_ids = (
            select(distinct(ItemCopy.catalog_item_id))
            .where(ItemCopy.replacement_cost.isnot(None), ItemCopy.replacement_cost > 0)
            .scalar_subquery()
        )
        costed_checkouts_result = await db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.checked_out_at >= start_dt,
                Checkout.checked_out_at < end_dt,
                Checkout.item_id.in_(costed_item_ids),
            )
        )
        costed_checkouts = costed_checkouts_result.scalar() or 0
        avg_cost_per_circ = round(total_replacement_cost / costed_checkouts, 2) if costed_checkouts > 0 else None
    else:
        costed_checkouts = 0
        avg_cost_per_circ = None

    return {
        "totalItems": total_items,
        "totalCheckouts": total_checkouts,
        "avgCheckoutsPerItem": avg_checkouts_per_item,
        "avgAgeYears": avg_age_years,
        "byCondition": by_condition,
        "topCirculated": top_items,
        "leastCirculated": bottom_items,
        "costEfficiency": {
            "totalReplacementCost": round(total_replacement_cost, 2),
            "copiesWithCost": copies_with_cost,
            "checkoutsOfCostedItems": costed_checkouts,
            "avgCostPerCirculation": avg_cost_per_circ,
        },
    }
