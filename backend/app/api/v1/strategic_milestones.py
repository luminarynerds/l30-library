# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Strategic Planning - Milestones Endpoints

Handles milestone creation, updates, and public milestone displays.
Supports featuring milestones and sharing achievement stories.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.strategic import StrategicMilestone, StrategicPlan
from ...models.user import User
from .auth import get_current_user, get_current_user_optional
from .dependencies import require_admin, require_staff

router = APIRouter(prefix="/strategic", tags=["strategic-milestones"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class MilestoneBase(BaseModel):
    title: str
    description: Optional[str] = None
    achieved_date: Optional[datetime] = None
    celebration_text: Optional[str] = None
    impact_story: Optional[str] = None
    photo_url: Optional[str] = None
    is_public: bool = True
    is_featured: bool = False
    display_order: Optional[int] = 0
    milestone_type: str = "achievement"
    goal_id: Optional[int] = None


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    achieved_date: Optional[datetime] = None
    celebration_text: Optional[str] = None
    impact_story: Optional[str] = None
    photo_url: Optional[str] = None
    is_public: Optional[bool] = None
    is_featured: Optional[bool] = None
    display_order: Optional[int] = None
    milestone_type: Optional[str] = None
    goal_id: Optional[int] = None


class MilestoneResponse(MilestoneBase):
    id: int
    plan_id: int
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class PaginatedMilestoneResponse(BaseModel):
    items: List[MilestoneResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class TimelineEvent(BaseModel):
    year: int
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None


class PublicMilestone(BaseModel):
    id: int
    title: str
    celebration_text: Optional[str] = None
    impact_story: Optional[str] = None
    photo_url: Optional[str] = None
    achieved_date: Optional[datetime] = None
    milestone_type: str


# ============================================================================
# Milestone Endpoints
# ============================================================================

@router.get("/plans/{plan_id}/milestones", response_model=PaginatedMilestoneResponse)
async def list_milestones(
    plan_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    include_private: bool = False,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """List milestones for a plan with pagination."""
    query = select(StrategicMilestone).where(StrategicMilestone.plan_id == plan_id)
    count_query = select(func.count(StrategicMilestone.id)).where(StrategicMilestone.plan_id == plan_id)

    # Only staff/admin can see private milestones
    if (
        not include_private
        or not current_user
        or str(current_user.role).lower() not in ["staff", "admin", "super_admin", "director"]
    ):
        query = query.where(StrategicMilestone.is_public == True)
        count_query = count_query.where(StrategicMilestone.is_public == True)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(
        StrategicMilestone.display_order, StrategicMilestone.achieved_date.desc()
    ).offset(offset).limit(per_page)
    result = await db.execute(query)
    milestones = result.scalars().all()

    return PaginatedMilestoneResponse(
        items=[MilestoneResponse.model_validate(m) for m in milestones],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.post("/plans/{plan_id}/milestones", response_model=MilestoneResponse)
async def create_milestone(
    plan_id: int,
    milestone_data: MilestoneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a milestone (staff/admin)."""
    await require_staff(current_user)

    # Verify plan exists
    result = await db.execute(select(StrategicPlan).where(StrategicPlan.id == plan_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    milestone = StrategicMilestone(
        plan_id=plan_id, created_by_id=current_user.id, **milestone_data.model_dump()
    )
    db.add(milestone)
    await db.commit()
    await db.refresh(milestone)
    return milestone


@router.put("/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    milestone_id: int,
    milestone_data: MilestoneUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a milestone (staff/admin)."""
    await require_staff(current_user)

    milestone = await get_or_404(db, StrategicMilestone, milestone_id, "Milestone not found")

    update_data = milestone_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(milestone, field, value)

    milestone.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(milestone)
    return milestone


@router.delete("/milestones/{milestone_id}")
async def delete_milestone(
    milestone_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a milestone (admin only)."""
    await require_admin(current_user)

    milestone = await get_or_404(db, StrategicMilestone, milestone_id, "Milestone not found")

    await db.delete(milestone)
    await db.commit()
    return {"message": "Milestone deleted"}
