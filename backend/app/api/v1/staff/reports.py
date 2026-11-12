# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Reporting API Endpoints

Provides endpoints for:
- Circulation statistics
- Popular items report
"""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.catalog import CatalogItem
from ....models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ....models.user import User, UserRole
from ..dependencies import require_staff

router = APIRouter(prefix="/staff", tags=["staff-reports"])


class CirculationReport(BaseModel):
    date: date
    checkouts_today: int
    returns_today: int
    overdue_count: int
    active_holds: int
    new_patrons_today: int


class PopularItem(BaseModel):
    item_id: int
    title: str
    author: str | None
    checkout_count: int


class PopularItemsReport(BaseModel):
    items: list[PopularItem]
    period_days: int


@router.get("/reports/circulation", response_model=CirculationReport)
async def get_circulation_report(
    report_date: date | None = Query(
        None, description="Date for report (defaults to today)"
    ),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get circulation statistics for a given day."""
    target_date = report_date or date.today()
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())

    checkouts_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.checked_out_at >= start_of_day,
            Checkout.checked_out_at <= end_of_day,
        )
    )
    checkouts_today = checkouts_result.scalar() or 0

    returns_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.returned_at >= start_of_day, Checkout.returned_at <= end_of_day
        )
    )
    returns_today = returns_result.scalar() or 0

    now = datetime.now(timezone.utc)
    overdue_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.status == CheckoutStatus.active, Checkout.due_date < now
        )
    )
    overdue_count = overdue_result.scalar() or 0

    holds_result = await db.execute(
        select(func.count(Hold.id)).where(
            Hold.status.in_([HoldStatus.pending, HoldStatus.ready])
        )
    )
    active_holds = holds_result.scalar() or 0

    patrons_result = await db.execute(
        select(func.count(User.id)).where(
            User.role == UserRole.PATRON,
            User.created_at >= start_of_day,
            User.created_at <= end_of_day,
        )
    )
    new_patrons_today = patrons_result.scalar() or 0

    return CirculationReport(
        date=target_date,
        checkouts_today=checkouts_today,
        returns_today=returns_today,
        overdue_count=overdue_count,
        active_holds=active_holds,
        new_patrons_today=new_patrons_today,
    )


@router.get("/reports/popular", response_model=PopularItemsReport)
async def get_popular_items(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(10, ge=1, le=50, description="Number of items to return"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get the most popular items based on checkout count."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            CatalogItem.id,
            CatalogItem.title,
            CatalogItem.author,
            func.count(Checkout.id).label("checkout_count"),
        )
        .join(Checkout, CatalogItem.id == Checkout.item_id)
        .where(Checkout.checked_out_at >= cutoff_date)
        .group_by(CatalogItem.id, CatalogItem.title, CatalogItem.author)
        .order_by(func.count(Checkout.id).desc())
        .limit(limit)
    )
    rows = result.all()

    items = [
        PopularItem(
            item_id=row.id,
            title=row.title,
            author=row.author,
            checkout_count=row.checkout_count,
        )
        for row in rows
    ]

    return PopularItemsReport(items=items, period_days=days)
