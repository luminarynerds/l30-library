# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Reports and Analytics Endpoints

Handles financial summaries, charges by type, inventory summaries,
category/location breakdowns, monthly trends, and patron risk reports.
"""

from app.core.logging import get_logger
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....schemas.lost_damaged import (
    FinancialSummaryResponse,
    ChargesByTypeResponse,
    FinancialDetailResponse,
    InventorySummaryResponse,
    LostByCategoryResponse,
    LostByLocationResponse,
    TrendDataResponse,
    PatronRiskReportResponse,
)
from ....services.lost_damaged_reports_service import LostDamagedReportsService
from ..auth import get_current_user
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Reports Endpoints
# ============================================================================

@router.get("/reports/financial-summary", response_model=FinancialSummaryResponse)
async def get_financial_summary(
    start_date: Optional[datetime] = Query(None, description="Start of period"),
    end_date: Optional[datetime] = Query(None, description="End of period"),
    location: Optional[str] = Query(None, description="Filter by location"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get financial summary for lost/damaged items."""
    service = LostDamagedReportsService(db)
    summary = await service.get_financial_summary(
        start_date=start_date,
        end_date=end_date,
        location=location,
    )

    return FinancialSummaryResponse(
        total_charges=summary.total_charges,
        total_collected=summary.total_collected,
        total_outstanding=summary.total_outstanding,
        total_waived=summary.total_waived,
        total_credits=summary.total_credits,
        collection_rate=summary.collection_rate,
        period_start=summary.period_start,
        period_end=summary.period_end,
    )


@router.get("/reports/charges-by-type", response_model=ChargesByTypeResponse)
async def get_charges_by_type(
    start_date: Optional[datetime] = Query(None, description="Start of period"),
    end_date: Optional[datetime] = Query(None, description="End of period"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get charges broken down by type (lost vs damaged)."""
    service = LostDamagedReportsService(db)
    charges = await service.get_charges_by_type(
        start_date=start_date,
        end_date=end_date,
    )

    return ChargesByTypeResponse(
        lost_item_charges=charges.lost_item_charges,
        damaged_item_charges=charges.damaged_item_charges,
        processing_fees=charges.processing_fees,
        total=charges.total,
    )


@router.get("/reports/inventory-summary", response_model=InventorySummaryResponse)
async def get_inventory_summary(
    start_date: Optional[datetime] = Query(None, description="Start of period"),
    end_date: Optional[datetime] = Query(None, description="End of period"),
    location: Optional[str] = Query(None, description="Filter by location"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get inventory summary for lost/damaged items."""
    service = LostDamagedReportsService(db)
    summary = await service.get_inventory_summary(
        start_date=start_date,
        end_date=end_date,
        location=location,
    )

    return InventorySummaryResponse(
        total_lost=summary.total_lost,
        lost_by_patron=summary.lost_by_patron,
        lost_in_transit=summary.lost_in_transit,
        claims_returned=summary.claims_returned,
        total_damaged=summary.total_damaged,
        damaged_repairable=summary.damaged_repairable,
        damaged_withdrawn=summary.damaged_withdrawn,
        in_mending=summary.in_mending,
        items_found=summary.items_found,
        period_start=summary.period_start,
        period_end=summary.period_end,
    )


@router.get("/reports/lost-by-category", response_model=List[LostByCategoryResponse])
async def get_lost_by_category(
    start_date: Optional[datetime] = Query(None, description="Start of period"),
    end_date: Optional[datetime] = Query(None, description="End of period"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get lost items grouped by category."""
    service = LostDamagedReportsService(db)
    categories = await service.get_lost_by_category(
        start_date=start_date,
        end_date=end_date,
    )

    return [
        LostByCategoryResponse(
            item_type=c.item_type,
            count=c.count,
            total_value=c.total_value,
            percentage_of_total=c.percentage_of_total,
        )
        for c in categories
    ]


@router.get("/reports/lost-by-location", response_model=List[LostByLocationResponse])
async def get_lost_by_location(
    start_date: Optional[datetime] = Query(None, description="Start of period"),
    end_date: Optional[datetime] = Query(None, description="End of period"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get lost items grouped by location."""
    service = LostDamagedReportsService(db)
    locations = await service.get_lost_by_location(
        start_date=start_date,
        end_date=end_date,
    )

    return [
        LostByLocationResponse(
            location=loc.location,
            count=loc.count,
            total_value=loc.total_value,
            percentage_of_total=loc.percentage_of_total,
        )
        for loc in locations
    ]


@router.get("/reports/monthly-trend", response_model=List[TrendDataResponse])
async def get_monthly_trend(
    months: int = Query(12, ge=1, le=36, description="Number of months to include"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get monthly trend data for lost/damaged items."""
    service = LostDamagedReportsService(db)
    trends = await service.get_monthly_trend(months=months)

    return [
        TrendDataResponse(
            period=t.period,
            lost_count=t.lost_count,
            damaged_count=t.damaged_count,
            charges=t.charges,
            credits=t.credits,
            net=t.net,
        )
        for t in trends
    ]


@router.get("/reports/patron-risk", response_model=List[PatronRiskReportResponse])
async def get_patron_risk_report(
    min_incidents: int = Query(2, ge=1, description="Minimum incidents to include"),
    days_back: int = Query(365, ge=30, le=730, description="Days to look back"),
    limit: int = Query(50, ge=1, le=200),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get patron risk report for high lost/damaged item rates."""
    service = LostDamagedReportsService(db)
    reports = await service.get_patron_risk_report(
        min_incidents=min_incidents,
        days_back=days_back,
        limit=limit,
    )

    return [
        PatronRiskReportResponse(
            patron_id=r.patron_id,
            patron_name=r.patron_name,
            patron_email=r.patron_email,
            lost_item_count=r.lost_item_count,
            damaged_item_count=r.damaged_item_count,
            claims_returned_count=r.claims_returned_count,
            total_charges=r.total_charges,
            outstanding_balance=r.outstanding_balance,
            risk_score=r.risk_score,
        )
        for r in reports
    ]
