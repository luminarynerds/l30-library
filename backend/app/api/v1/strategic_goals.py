# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Strategic Planning - Goals Endpoints

Handles all goal-related operations including creation, updates, progress tracking,
reordering, and goal-specific analytics.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.strategic import GoalStatus, StrategicGoal, StrategicPlan
from ...models.user import User
from ...services.strategic_service import (
    update_goal_progress as update_goal_progress_svc,
)
from .auth import get_current_user, get_current_user_optional
from .dependencies import check_staff_access, check_admin_access
from app.core.datetime_utils import utc_now

router = APIRouter(prefix="/strategic", tags=["strategic-goals"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class MetricSchema(BaseModel):
    name: str
    current: float
    target: float
    unit: Optional[str] = None


class UpdateSchema(BaseModel):
    date: str
    progress: int
    note: Optional[str] = None


class GoalBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    target_date: Optional[datetime] = None
    progress: int = Field(default=0, ge=0, le=100)
    status: str = "not_started"
    metrics: Optional[List[dict]] = []
    owner: Optional[str] = None
    priority: int = Field(default=3, ge=1, le=5)


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    target_date: Optional[datetime] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[str] = None
    metrics: Optional[List[dict]] = None
    owner: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)


class GoalResponse(GoalBase):
    id: int
    plan_id: int
    completed_date: Optional[datetime] = None
    updates: Optional[List[dict]] = []
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class PaginatedGoalResponse(BaseModel):
    items: List[GoalResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class ProgressUpdateRequest(BaseModel):
    progress: int = Field(..., ge=0, le=100)
    note: Optional[str] = None
    status: Optional[str] = None


class ReorderGoalsRequest(BaseModel):
    goal_ids: List[int]


# ============================================================================
# Goal Endpoints
# ============================================================================

@router.post("/plans/{plan_id}/goals", response_model=GoalResponse)
async def create_goal(
    plan_id: int,
    goal_data: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a goal to a strategic plan (staff/admin)."""
    check_staff_access(current_user)

    result = await db.execute(select(StrategicPlan).where(StrategicPlan.id == plan_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    goal = StrategicGoal(plan_id=plan_id, **goal_data.model_dump())
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


@router.get("/plans/{plan_id}/goals", response_model=PaginatedGoalResponse)
async def list_goals(
    plan_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    goal_status: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List goals for a plan with pagination."""
    # Verify plan exists
    plan_result = await db.execute(select(StrategicPlan).where(StrategicPlan.id == plan_id))
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    query = select(StrategicGoal).where(StrategicGoal.plan_id == plan_id)
    count_query = select(func.count(StrategicGoal.id)).where(StrategicGoal.plan_id == plan_id)

    # Apply filters
    if goal_status:
        query = query.where(StrategicGoal.status == goal_status)
        count_query = count_query.where(StrategicGoal.status == goal_status)
    if category:
        query = query.where(StrategicGoal.category == category)
        count_query = count_query.where(StrategicGoal.category == category)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(StrategicGoal.display_order, StrategicGoal.created_at).offset(offset).limit(per_page)
    result = await db.execute(query)
    goals = result.scalars().all()

    return PaginatedGoalResponse(
        items=[GoalResponse.model_validate(g) for g in goals],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.put("/goals/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: int,
    goal_data: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a strategic goal (staff/admin)."""
    check_staff_access(current_user)

    goal = await get_or_404(db, StrategicGoal, goal_id, "Goal not found")

    update_data = goal_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(goal, field, value)

    goal.updated_at = datetime.now(timezone.utc)

    # Auto-set completed date if status changed to completed
    if goal_data.status == "completed" and not goal.completed_date:
        goal.completed_date = datetime.now(timezone.utc)
        goal.progress = 100

    await db.commit()
    await db.refresh(goal)
    return goal


@router.post("/goals/{goal_id}/progress", response_model=GoalResponse)
async def update_goal_progress_endpoint(
    goal_id: int,
    progress_data: ProgressUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a progress update for a goal (staff/admin)."""
    check_staff_access(current_user)

    goal = await get_or_404(db, StrategicGoal, goal_id, "Goal not found")

    # Update progress
    goal.progress = progress_data.progress

    # Update status if provided
    if progress_data.status:
        goal.status = progress_data.status

    # Auto-complete if 100%
    if progress_data.progress >= 100:
        goal.status = GoalStatus.COMPLETED
        goal.completed_date = datetime.now(timezone.utc)

    # Add to update history
    updates = goal.updates or []
    updates.append(
        {
            "date": datetime.now(timezone.utc).isoformat(),
            "progress": progress_data.progress,
            "note": progress_data.note,
            "updated_by": current_user.email,
        }
    )
    goal.updates = updates
    goal.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(goal)
    return goal


@router.delete("/goals/{goal_id}")
async def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a strategic goal (admin only)."""
    check_admin_access(current_user)

    goal = await get_or_404(db, StrategicGoal, goal_id, "Goal not found")

    await db.delete(goal)
    await db.commit()
    return {"message": "Goal deleted"}


@router.put("/plans/{plan_id}/goals/reorder")
async def reorder_goals(
    plan_id: int,
    reorder_data: ReorderGoalsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reorder goals within a plan (admin only)."""
    check_admin_access(current_user)

    # Verify plan exists
    await get_or_404(db, StrategicPlan, plan_id, "Plan not found")

    # Update display_order for each goal
    for index, goal_id in enumerate(reorder_data.goal_ids):
        result = await db.execute(
            select(StrategicGoal).where(
                StrategicGoal.id == goal_id, StrategicGoal.plan_id == plan_id
            )
        )
        goal = result.scalar_one_or_none()
        if goal:
            goal.display_order = index
            goal.updated_at = utc_now()

    await db.commit()
    return {"message": "Goals reordered successfully"}


@router.get("/goals/{goal_id}")
async def get_goals__goal_id_(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get /goals/{goal_id} information."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/goals/{goal_id}/progress")
async def get_goals__goal_id__progress(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get /goals/{goal_id}/progress information."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")

