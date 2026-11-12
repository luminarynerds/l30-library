# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Community Outcomes API endpoints."""

from app.core.logging import get_logger
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.user import User
from ...services.community_metrics_service import CommunityMetricsService
from .auth import get_current_user
from .dependencies import check_staff_access

router = APIRouter(prefix="/community-outcomes", tags=["community-outcomes"])
logger = get_logger(__name__)


@router.get("/dashboard")
@limiter.limit("20/minute")
async def get_dashboard(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    branch_id: Optional[int] = Query(None, description="Branch ID filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """All 6 community outcome categories for a date range. Staff only."""
    check_staff_access(current_user)
    today = date.today()
    start = _parse_date(start_date) if start_date else date(today.year, 1, 1)
    end = _parse_date(end_date) if end_date else today
    service = CommunityMetricsService(db)
    return await service.get_dashboard(start, end, branch_id)


@router.get("/trends")
@limiter.limit("20/minute")
async def get_trends(
    request: Request,
    category: str = Query(..., description="Category name"),
    periods: int = Query(12, ge=1, le=36, description="Number of monthly periods"),
    branch_id: Optional[int] = Query(None, description="Branch ID filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Monthly trend data for a single category. Staff only."""
    check_staff_access(current_user)
    service = CommunityMetricsService(db)
    return {"category": category, "trends": await service.get_trends(category, periods, branch_id)}


@router.get("/summary")
@limiter.limit("30/minute")
async def get_summary(
    request: Request,
    branch_id: Optional[int] = Query(None, description="Branch ID filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lightweight YTD summary. Staff only."""
    check_staff_access(current_user)
    service = CommunityMetricsService(db)
    return await service.get_summary(branch_id)


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()
