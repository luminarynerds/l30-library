# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Strategic planning - KPI definitions, value recording, and alert management."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.strategic import KPIAlert, StrategicKPI, StrategicPlan
from app.models.user import User
from app.schemas.strategic import (
    KPIAlertResolve,
    KPIAlertResponse,
    KPICreate,
    KPIResponse,
    KPIUpdate,
    KPIValueCreate,
    KPIValueResponse,
)
from app.services.strategic_leadership_service import create_kpi, record_kpi_value
from ..auth import get_current_user
from .common import require_admin, require_staff

router = APIRouter(prefix="/strategic", tags=["strategic-kpis"])


async def _load_kpi(db: AsyncSession, kpi_id: int) -> StrategicKPI:
    result = await db.execute(
        select(StrategicKPI)
        .where(StrategicKPI.id == kpi_id)
        .options(
            selectinload(StrategicKPI.values),
            selectinload(StrategicKPI.alerts),
        )
    )
    return result.scalar_one_or_none()


@router.get("/plans/{plan_id}/kpis", response_model=List[KPIResponse])
async def list_kpis(
    plan_id: int,
    active_only: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List KPIs for a strategic plan (staff/admin)."""
    require_staff(current_user)
    plan = await db.get(StrategicPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    q = select(StrategicKPI).where(StrategicKPI.plan_id == plan_id).options(
        selectinload(StrategicKPI.values),
        selectinload(StrategicKPI.alerts),
    )
    if active_only:
        q = q.where(StrategicKPI.is_active == True)  # noqa: E712
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/plans/{plan_id}/kpis", response_model=KPIResponse, status_code=201)
async def create_kpi_endpoint(
    plan_id: int,
    kpi_data: KPICreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a KPI to a strategic plan (staff/admin)."""
    require_staff(current_user)
    plan = await db.get(StrategicPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    kpi = await create_kpi(db, plan_id, kpi_data.model_dump(), current_user.id)
    return await _load_kpi(db, kpi.id)


@router.patch("/kpis/{kpi_id}", response_model=KPIResponse)
async def update_kpi(
    kpi_id: int,
    kpi_data: KPIUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a KPI definition (staff/admin)."""
    require_staff(current_user)
    kpi = await db.get(StrategicKPI, kpi_id)
    if kpi is None:
        raise HTTPException(status_code=404, detail="KPI not found")
    for field, value in kpi_data.model_dump(exclude_unset=True).items():
        setattr(kpi, field, value)
    await db.commit()
    return await _load_kpi(db, kpi_id)


@router.delete("/kpis/{kpi_id}", status_code=204)
async def delete_kpi(
    kpi_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a KPI (admin only)."""
    require_admin(current_user)
    kpi = await db.get(StrategicKPI, kpi_id)
    if kpi is None:
        raise HTTPException(status_code=404, detail="KPI not found")
    await db.delete(kpi)
    await db.commit()


@router.post("/kpis/{kpi_id}/values", response_model=KPIValueResponse, status_code=201)
async def record_kpi_value_endpoint(
    kpi_id: int,
    value_data: KPIValueCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a data point for a KPI (staff/admin)."""
    require_staff(current_user)
    kpi = await db.get(StrategicKPI, kpi_id)
    if kpi is None:
        raise HTTPException(status_code=404, detail="KPI not found")
    kpi_value = await record_kpi_value(
        db,
        kpi_id,
        value_data.value,
        current_user.id,
        notes=value_data.notes,
        is_estimated=value_data.is_estimated,
    )
    return kpi_value


@router.post("/kpi-alerts/{alert_id}/acknowledge", response_model=KPIAlertResponse)
async def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge a KPI alert (staff/admin)."""
    require_staff(current_user)
    alert = await db.get(KPIAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = True
    alert.acknowledged_by_id = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.post("/kpi-alerts/{alert_id}/resolve", response_model=KPIAlertResponse)
async def resolve_alert(
    alert_id: int,
    body: KPIAlertResolve,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a KPI alert (staff/admin)."""
    require_staff(current_user)
    alert = await db.get(KPIAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = True
    alert.resolution_notes = body.resolution_notes
    await db.commit()
    await db.refresh(alert)
    return alert
