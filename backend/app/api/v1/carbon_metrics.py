# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Carbon metrics API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from .dependencies import get_current_user
from ...models.user import User, UserRole
from ...services.carbon_metrics_service import (
    get_monthly_summary,
    get_section_breakdown,
    get_heaviest_pages,
    get_public_summary,
)

router = APIRouter(prefix="/carbon-metrics", tags=["carbon-metrics"])

STAFF_ROLES = (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN)


@router.get("/public-summary")
async def public_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public carbon footprint summary. No auth required."""
    return await get_public_summary(db)


@router.get("/admin/summary")
async def admin_summary(
    request: Request,
    months: int = Query(default=6, ge=1, le=24),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Monthly CO2 totals and trends. Staff only."""
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")
    return {"months": await get_monthly_summary(db, months)}


@router.get("/admin/breakdown")
async def admin_breakdown(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """CO2 breakdown by site section. Staff only."""
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")
    return {"sections": await get_section_breakdown(db, days)}


@router.get("/admin/heaviest")
async def admin_heaviest(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Heaviest pages by transfer size. Staff only."""
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")
    return {"pages": await get_heaviest_pages(db, limit)}
