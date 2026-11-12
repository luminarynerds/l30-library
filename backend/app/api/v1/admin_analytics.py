# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Admin Analytics API Endpoints

Provides staff/admin endpoints for accessing various analytics dashboards including
sharing metrics, circulation stats, reading activity, and more.

All endpoints require STAFF+ role authentication.
"""

from app.core.logging import get_logger
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.analytics import SharingDashboardResponse
from ...services.sharing_analytics_service import SharingAnalytics
from .dependencies import require_staff

VALID_RESOURCE_TYPES = {"book", "event", "reading_list", "author_profile", "staff_pick"}

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])


@router.get(
    "/sharing-dashboard",
    response_model=SharingDashboardResponse,
    summary="Get social sharing analytics dashboard",
    description="Returns comprehensive social sharing metrics including top shared resources, "
    "platform breakdown, active sharers, and sharing trends. Requires STAFF+ role.",
)
async def get_sharing_dashboard(
    days: int = Query(
        30,
        ge=7,
        le=365,
        description="Number of days to analyze (7-365, default 30)",
    ),
    resource_type: Optional[str] = Query(
        None,
        description="Comma-separated resource types to filter by (e.g. 'book,event'). "
        "Valid types: book, event, reading_list, author_profile, staff_pick",
    ),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> SharingDashboardResponse:
    """
    Get the sharing analytics dashboard with comprehensive metrics.

    Returns detailed sharing analytics including:
    - Top 10 most shared resources (books, events, reading lists)
    - Share count breakdown by platform (pie chart data)
    - Total and unique sharer metrics
    - Top 10 most active sharers
    - Share trends over the specified period
    - Platform usage percentages
    - Overall trend vs previous period

    Query Parameters:
        days: Analysis period in days (default 30, range 7-365)
        resource_type: Comma-separated list of resource types to filter by

    Returns:
        SharingDashboardResponse with comprehensive sharing metrics

    Example:
        GET /api/v1/admin/analytics/sharing-dashboard?days=30&resource_type=book,event

    Access Control:
        Requires STAFF, ADMIN, or SUPER_ADMIN role
    """
    # Parse and validate resource types
    resource_types: Optional[List[str]] = None
    if resource_type:
        resource_types = [rt.strip() for rt in resource_type.split(",") if rt.strip()]
        resource_types = [rt for rt in resource_types if rt in VALID_RESOURCE_TYPES]
        if not resource_types:
            resource_types = None

    logger.info(
        "Staff accessed sharing analytics dashboard",
        extra={
            "user_id": staff_user.id,
            "email": staff_user.email,
            "days": days,
            "resource_types": resource_types,
        },
    )

    analytics = SharingAnalytics(db)
    dashboard = await analytics.get_dashboard_stats(
        days=days, resource_types=resource_types
    )

    return dashboard
