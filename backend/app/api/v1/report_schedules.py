# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Report schedule CRUD endpoints.

Mounted under /unified-reports/schedules on the existing unified_reports router.
"""

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.report_schedule import UnifiedReportSchedule
from ...models.user import User
from .auth import get_current_user
from .dependencies import check_staff_access

router = APIRouter(prefix="/unified-reports/schedules", tags=["report-schedules"])
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ReportScheduleCreate(BaseModel):
    name: str = Field(..., max_length=255)
    report_type: str = Field(..., pattern="^(circulation|financial|patron_activity|collection|compliance|community_outcomes)$")
    output_format: str = Field("pdf", pattern="^(csv|excel|pdf)$")
    frequency: str = Field(..., pattern="^(daily|weekly|monthly)$")
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    time_of_day: str = Field("08:00", pattern=r"^([01]?\d|2[0-3]):[0-5]\d$")
    branch_id: Optional[int] = None
    recipient_emails: List[str] = Field(default_factory=list)
    is_active: bool = True


class ReportScheduleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    report_type: Optional[str] = Field(None, pattern="^(circulation|financial|patron_activity|collection|compliance|community_outcomes)$")
    output_format: Optional[str] = Field(None, pattern="^(csv|excel|pdf)$")
    frequency: Optional[str] = Field(None, pattern="^(daily|weekly|monthly)$")
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    time_of_day: Optional[str] = Field(None, pattern=r"^([01]?\d|2[0-3]):[0-5]\d$")
    branch_id: Optional[int] = None
    recipient_emails: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ReportScheduleResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    report_type: str
    output_format: str
    frequency: str
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    time_of_day: str
    branch_id: Optional[int] = None
    recipient_emails: list[str]
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[ReportScheduleResponse])
async def list_report_schedules(
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    check_staff_access(current_user)
    query = select(UnifiedReportSchedule).order_by(UnifiedReportSchedule.created_at.desc())
    if active_only:
        query = query.where(UnifiedReportSchedule.is_active == True)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{schedule_id}", response_model=ReportScheduleResponse)
async def get_report_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    check_staff_access(current_user)
    result = await db.execute(
        select(UnifiedReportSchedule).where(UnifiedReportSchedule.id == schedule_id)
    )
    sched = result.scalars().first()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return sched


@router.post("", response_model=ReportScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_report_schedule(
    body: ReportScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    check_staff_access(current_user)

    sched = UnifiedReportSchedule(
        **body.model_dump(),
        created_by=current_user.id,
    )
    db.add(sched)
    await db.commit()
    await db.refresh(sched)

    # Register with live scheduler if running
    try:
        from ...services.report_schedule_service import get_report_scheduler
        scheduler = get_report_scheduler()
        if scheduler.scheduler and scheduler.scheduler.running:
            await scheduler.add_schedule(sched)
    except Exception:  # noqa: BLE001  # scheduler may not be running — picked up on next restart
        logger.debug("Scheduler not running; schedule will be picked up on next restart")

    logger.info("Created report schedule %d: %s", sched.id, sched.name)
    return sched


@router.put("/{schedule_id}", response_model=ReportScheduleResponse)
async def update_report_schedule(
    schedule_id: int,
    body: ReportScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    check_staff_access(current_user)
    result = await db.execute(
        select(UnifiedReportSchedule).where(UnifiedReportSchedule.id == schedule_id)
    )
    sched = result.scalars().first()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(sched, field, value)
    sched.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(sched)

    try:
        from ...services.report_schedule_service import get_report_scheduler
        scheduler = get_report_scheduler()
        if scheduler.scheduler and scheduler.scheduler.running:
            if sched.is_active:
                await scheduler.update_schedule(sched)
            else:
                await scheduler.remove_schedule(sched.id)
    except Exception:  # noqa: BLE001  # scheduler may not be running
        logger.debug("Scheduler not running")

    return sched


@router.delete("/{schedule_id}")
async def delete_report_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    check_staff_access(current_user)
    result = await db.execute(
        select(UnifiedReportSchedule).where(UnifiedReportSchedule.id == schedule_id)
    )
    sched = result.scalars().first()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    try:
        from ...services.report_schedule_service import get_report_scheduler
        scheduler = get_report_scheduler()
        if scheduler.scheduler and scheduler.scheduler.running:
            await scheduler.remove_schedule(sched.id)
    except Exception:  # noqa: BLE001  # scheduler may not be running
        pass

    await db.delete(sched)
    await db.commit()
    return {"message": "Schedule deleted"}
