# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Public Library Statistics API.

Provides unauthenticated, aggregate-only statistics for the public-facing
library stats page. All data is anonymized and cached.
"""

from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.catalog import CatalogItem
from ...models.circulation import Checkout, CheckoutStatus
from ...models.user import User, UserRole, PatronStatus

router = APIRouter(prefix="/public/stats", tags=["public-stats"])
logger = get_logger(__name__)


# ==================== Response Models ====================


class OverviewResponse(BaseModel):
    total_items_in_collection: int
    total_cardholders: int
    checkouts_today: int
    checkouts_this_month: int
    checkouts_this_year: int
    active_checkouts: int


class MonthlyTrend(BaseModel):
    month: str
    checkouts: int


class MonthlyTrendsResponse(BaseModel):
    trends: List[MonthlyTrend]


class PopularItem(BaseModel):
    id: int
    title: str
    author: str | None
    checkout_count: int


class PopularItemsResponse(BaseModel):
    items: List[PopularItem]
    period_days: int


# ==================== Endpoints ====================


@router.get("/overview", response_model=OverviewResponse)
async def get_public_overview(db: AsyncSession = Depends(get_db)):
    """Aggregate library statistics safe for public display.

    No authentication required. Returns only anonymized counts.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    month_start = today_start.replace(day=1)
    year_start = today_start.replace(month=1, day=1)

    # Run queries sequentially — asyncio.gather with a single session is unsafe
    total_items = await db.scalar(select(func.count()).select_from(CatalogItem))
    total_cardholders = await db.scalar(
        select(func.count()).select_from(User).where(
            User.role == UserRole.PATRON,
            User.is_active.is_(True),
            User.patron_status == PatronStatus.ACTIVE,
        )
    )
    checkouts_today = await db.scalar(
        select(func.count()).select_from(Checkout).where(
            Checkout.checked_out_at.between(today_start, today_end),
        )
    )
    checkouts_month = await db.scalar(
        select(func.count()).select_from(Checkout).where(
            Checkout.checked_out_at >= month_start,
        )
    )
    checkouts_year = await db.scalar(
        select(func.count()).select_from(Checkout).where(
            Checkout.checked_out_at >= year_start,
        )
    )
    active_checkouts = await db.scalar(
        select(func.count()).select_from(Checkout).where(
            Checkout.status == CheckoutStatus.active,
        )
    )

    return OverviewResponse(
        total_items_in_collection=total_items or 0,
        total_cardholders=total_cardholders or 0,
        checkouts_today=checkouts_today or 0,
        checkouts_this_month=checkouts_month or 0,
        checkouts_this_year=checkouts_year or 0,
        active_checkouts=active_checkouts or 0,
    )


@router.get("/monthly-trends", response_model=MonthlyTrendsResponse)
async def get_public_monthly_trends(
    months: int = Query(12, ge=1, le=24, description="Number of months"),
    db: AsyncSession = Depends(get_db),
):
    """Monthly checkout trends for public display. No auth required."""
    now = datetime.now(timezone.utc)

    # Calculate the start date using proper month arithmetic
    start_year = now.year
    start_month = now.month - (months - 1)
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    range_start = datetime(start_year, start_month, 1, tzinfo=timezone.utc)

    # Single query with GROUP BY month instead of N+1
    month_trunc = func.date_trunc(literal_column("'month'"), Checkout.checked_out_at)
    stmt = (
        select(
            month_trunc.label("month"),
            func.count(Checkout.id).label("count"),
        )
        .where(Checkout.checked_out_at >= range_start)
        .group_by(month_trunc)
        .order_by(month_trunc)
    )

    result = await db.execute(stmt)
    rows = {row.month.strftime("%Y-%m"): row.count for row in result}

    # Build complete list including months with zero checkouts
    trends = []
    y, m = start_year, start_month
    for _ in range(months):
        key = f"{y:04d}-{m:02d}"
        trends.append(MonthlyTrend(month=key, checkouts=rows.get(key, 0)))
        m += 1
        if m > 12:
            m = 1
            y += 1

    return MonthlyTrendsResponse(trends=trends)


@router.get("/popular-items", response_model=PopularItemsResponse)
async def get_public_popular_items(
    limit: int = Query(10, ge=1, le=25),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Most popular items by checkout count. No auth required.

    Returns title and author only - no patron data.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            CatalogItem.id,
            CatalogItem.title,
            CatalogItem.author,
            func.count(Checkout.id).label("checkout_count"),
        )
        .join(Checkout, Checkout.item_id == CatalogItem.id)
        .where(Checkout.checked_out_at >= cutoff)
        .group_by(CatalogItem.id, CatalogItem.title, CatalogItem.author)
        .order_by(func.count(Checkout.id).desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return PopularItemsResponse(
        items=[
            PopularItem(
                id=row.id,
                title=row.title,
                author=row.author,
                checkout_count=row.checkout_count,
            )
            for row in rows
        ],
        period_days=days,
    )
