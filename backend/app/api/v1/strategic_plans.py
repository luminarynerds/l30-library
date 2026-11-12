# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Strategic Planning - Plans Endpoints

Handles strategic plan CRUD operations, activation, and basic plan management.
Includes plan creation, listing, retrieval, updates, and status management.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.strategic import PlanStatus, StrategicGoal, StrategicPlan
from ...models.user import User
from ...services.strategic_service import (
    create_plan as create_plan_svc,
    update_plan as update_plan_svc,
)
from .auth import get_current_user, get_current_user_optional
from .dependencies import check_admin_access, is_staff_or_admin

router = APIRouter(prefix="/strategic", tags=["strategic-plans"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class GoalResponse(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True


class PlanBase(BaseModel):
    title: str
    description: Optional[str] = None
    period_start: datetime
    period_end: datetime
    mission: Optional[str] = None
    vision: Optional[str] = None
    values: List[str] = []
    status: str = "draft"


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    mission: Optional[str] = None
    vision: Optional[str] = None
    values: Optional[List[str]] = None
    status: Optional[str] = None
    next_review: Optional[datetime] = None


class PlanResponse(PlanBase):
    id: int
    last_reviewed: Optional[datetime] = None
    next_review: Optional[datetime] = None
    created_at: datetime | None = None
    goals: List[GoalResponse] = []

    class Config:
        from_attributes = True


class PlanSummary(BaseModel):
    id: int
    title: str
    status: str
    period_start: datetime
    period_end: datetime
    goal_count: int
    overall_progress: int

    class Config:
        from_attributes = True


class PaginatedPlanSummary(BaseModel):
    items: List[PlanSummary]
    total: int
    page: int
    per_page: int
    total_pages: int


# ============================================================================
# Public Endpoints
# ============================================================================

@router.get("/plans/active", response_model=Optional[PlanResponse])
async def get_active_plan(db: AsyncSession = Depends(get_db)):
    """Get the current active strategic plan (public)."""
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.status == PlanStatus.ACTIVE)
        .options(selectinload(StrategicPlan.goals))
        .order_by(StrategicPlan.period_start.desc())
        .limit(1)
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        return None
    return PlanResponse.model_validate(plan)


@router.get("/plans", response_model=PaginatedPlanSummary)
async def list_plans(
    plan_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """List all strategic plans with pagination. Public sees only active, staff sees all."""
    # Build goal stats as a subquery instead of eager-loading all goals
    goal_stats = (
        select(
            StrategicGoal.plan_id,
            func.count(StrategicGoal.id).label("goal_count"),
            func.coalesce(func.avg(StrategicGoal.progress), 0).label("avg_progress"),
        )
        .group_by(StrategicGoal.plan_id)
        .subquery()
    )

    query = (
        select(
            StrategicPlan,
            func.coalesce(goal_stats.c.goal_count, 0).label("goal_count"),
            func.coalesce(goal_stats.c.avg_progress, 0).label("avg_progress"),
        )
        .outerjoin(goal_stats, StrategicPlan.id == goal_stats.c.plan_id)
    )
    count_query = select(func.count(StrategicPlan.id))

    # Non-authenticated or regular users only see active plans
    if not current_user or not is_staff_or_admin(current_user):
        query = query.where(StrategicPlan.status == PlanStatus.ACTIVE)
        count_query = count_query.where(StrategicPlan.status == PlanStatus.ACTIVE)
    elif plan_status:
        query = query.where(StrategicPlan.status == plan_status)
        count_query = count_query.where(StrategicPlan.status == plan_status)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(StrategicPlan.period_start.desc()).offset(offset).limit(per_page)
    result = await db.execute(query)
    rows = result.all()

    items = [
        PlanSummary(
            id=p.id,
            title=p.title,
            status=p.status.value if hasattr(p.status, "value") else p.status,
            period_start=p.period_start,
            period_end=p.period_end,
            goal_count=int(goal_count),
            overall_progress=int(avg_progress),
        )
        for p, goal_count, avg_progress in rows
    ]

    return PaginatedPlanSummary(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific strategic plan with its goals."""
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.id == plan_id)
        .options(selectinload(StrategicPlan.goals))
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return PlanResponse.model_validate(plan)


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.post("/plans", response_model=PlanResponse)
async def create_plan_endpoint(
    plan_data: PlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new strategic plan (admin only)."""
    check_admin_access(current_user)

    # Delegate to service layer
    plan_data_dict = plan_data.model_dump()
    plan = await create_plan_svc(plan_data_dict, db)

    # Reload with goals relationship
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.id == plan.id)
        .options(selectinload(StrategicPlan.goals))
    )
    return result.scalar_one()


@router.put("/plans/{plan_id}", response_model=PlanResponse)
async def update_plan_endpoint(
    plan_id: int,
    plan_data: PlanUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a strategic plan (admin only)."""
    check_admin_access(current_user)

    # Delegate to service layer
    plan = await update_plan_svc(plan_id, plan_data.model_dump(exclude_unset=True), db)

    # Reload with goals relationship
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.id == plan.id)
        .options(selectinload(StrategicPlan.goals))
    )
    return result.scalar_one()


@router.post("/plans/{plan_id}/activate")
async def activate_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Activate a plan (deactivates any currently active plan)."""
    check_admin_access(current_user)

    # Deactivate current active plan
    result = await db.execute(
        select(StrategicPlan).where(StrategicPlan.status == PlanStatus.ACTIVE)
    )
    for active_plan in result.scalars().all():
        active_plan.status = PlanStatus.ARCHIVED

    # Activate new plan
    plan = await get_or_404(db, StrategicPlan, plan_id, "Plan not found")

    plan.status = PlanStatus.ACTIVE
    plan.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": f"Plan '{plan.title}' is now active"}


@router.delete("/plans/{plan_id}")
async def delete_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a strategic plan (admin only, cannot delete active plans)."""
    check_admin_access(current_user)

    plan = await get_or_404(db, StrategicPlan, plan_id, "Plan not found")

    if plan.status == PlanStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete active plan. Archive it first."
        )

    await db.delete(plan)
    await db.commit()
    return {"message": "Plan deleted"}
