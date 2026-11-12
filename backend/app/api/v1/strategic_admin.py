# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Strategic Planning - Admin & Settings Endpoints

Handles templates, goal templates, public story content, imports/exports,
and staff department views. Administrative configuration and data management.
"""

import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.strategic import (
    GoalStatus, PlanStatus, StrategicGoal, StrategicGoalTemplate,
    StrategicMilestone, StrategicPlan
)
from ...models.user import User
from .auth import get_current_user, get_current_user_optional
from .dependencies import check_staff_access, check_admin_access

router = APIRouter(prefix="/strategic", tags=["strategic-admin"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class TemplateMetricSchema(BaseModel):
    name: str
    unit: Optional[str] = None
    target_placeholder: Optional[str] = None


class TemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    suggested_timeline_months: Optional[int] = None
    default_metrics: List[dict] = []
    is_system_template: bool = False


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    suggested_timeline_months: Optional[int] = None
    default_metrics: Optional[List[dict]] = None
    is_system_template: Optional[bool] = None


class TemplateResponse(TemplateBase):
    id: int

    class Config:
        from_attributes = True


class TimelineEvent(BaseModel):
    year: int
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None


class PublicGoalProgress(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    progress: int
    status: str


class PublicMilestone(BaseModel):
    id: int
    title: str
    celebration_text: Optional[str] = None
    impact_story: Optional[str] = None
    photo_url: Optional[str] = None
    achieved_date: Optional[datetime] = None
    milestone_type: str


class OurStoryResponse(BaseModel):
    has_plan: bool
    library_name: str = os.environ.get("LIBRARY_NAME", "My Library")
    mission: Optional[str] = None
    vision: Optional[str] = None
    values: List[str] = []
    story_intro: Optional[str] = None
    hero_image_url: Optional[str] = None
    history_timeline: List[TimelineEvent] = []
    goals: List[PublicGoalProgress] = []
    milestones: List[PublicMilestone] = []
    plan_period: Optional[str] = None


class ImportPlanData(BaseModel):
    title: str
    description: Optional[str] = None
    period_start: str
    period_end: str
    mission: Optional[str] = None
    vision: Optional[str] = None
    values: Optional[List[str]] = []
    story_intro: Optional[str] = None
    hero_image_url: Optional[str] = None
    history_timeline: Optional[List[dict]] = []
    goals: Optional[List[dict]] = []
    milestones: Optional[List[dict]] = []


class StaffGoalView(BaseModel):
    id: int
    title: str
    description: Optional[str]
    category: Optional[str]
    department: Optional[str]
    progress: int
    status: str
    can_update: bool
    target_date: Optional[datetime]
    metrics: List[dict]


# ============================================================================
# Goal Template Endpoints
# ============================================================================

@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    category: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """List all goal templates."""
    query = select(StrategicGoalTemplate)
    if category:
        query = query.where(StrategicGoalTemplate.category == category)
    query = query.order_by(StrategicGoalTemplate.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific goal template."""
    template = await get_or_404(db, StrategicGoalTemplate, template_id, "Template not found")
    return template


@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    template_data: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new goal template (admin only)."""
    check_admin_access(current_user)

    template = StrategicGoalTemplate(**template_data.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    template_data: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a goal template (admin only)."""
    check_admin_access(current_user)

    template = await get_or_404(db, StrategicGoalTemplate, template_id, "Template not found")

    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a goal template (admin only)."""
    check_admin_access(current_user)

    template = await get_or_404(db, StrategicGoalTemplate, template_id, "Template not found")

    await db.delete(template)
    await db.commit()
    return {"message": "Template deleted"}


@router.post("/templates/seed")
async def seed_default_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Seed default goal templates (admin only)."""
    check_admin_access(current_user)

    default_templates = [
        {
            "name": "Increase Library Card Registration",
            "description": "A goal focused on growing the number of library card holders in the community through outreach, partnerships, and promotional campaigns.",
            "category": "Community",
            "suggested_timeline_months": 12,
            "default_metrics": [
                {"name": "New registrations", "unit": "cards", "target_placeholder": "1000"},
                {"name": "Outreach events held", "unit": "events", "target_placeholder": "12"},
                {"name": "Partner organizations", "unit": "partners", "target_placeholder": "5"},
            ],
            "is_system_template": True,
        },
        {
            "name": "Expand Digital Collection",
            "description": "Enhance the library's digital offerings including e-books, audiobooks, streaming services, and online databases to meet patron demand.",
            "category": "Technology",
            "suggested_timeline_months": 18,
            "default_metrics": [
                {"name": "Digital titles added", "unit": "titles", "target_placeholder": "5000"},
                {"name": "Digital circulation increase", "unit": "%", "target_placeholder": "25"},
                {"name": "New digital services", "unit": "services", "target_placeholder": "3"},
            ],
            "is_system_template": True,
        },
        {
            "name": "Launch New Program",
            "description": "Develop and launch a new library program to serve community needs, including planning, piloting, and full implementation.",
            "category": "Programming",
            "suggested_timeline_months": 6,
            "default_metrics": [
                {"name": "Program sessions held", "unit": "sessions", "target_placeholder": "24"},
                {"name": "Participants reached", "unit": "people", "target_placeholder": "200"},
                {"name": "Satisfaction rating", "unit": "%", "target_placeholder": "90"},
            ],
            "is_system_template": True,
        },
        {
            "name": "Improve Facility",
            "description": "Upgrade library facilities to better serve patrons, including renovations, accessibility improvements, and new amenities.",
            "category": "Facilities",
            "suggested_timeline_months": 24,
            "default_metrics": [
                {"name": "Square footage improved", "unit": "sq ft", "target_placeholder": "1000"},
                {"name": "ADA compliance items", "unit": "items", "target_placeholder": "10"},
                {"name": "Patron satisfaction", "unit": "%", "target_placeholder": "85"},
            ],
            "is_system_template": True,
        },
        {
            "name": "Staff Training Initiative",
            "description": "Comprehensive staff development program to enhance skills, knowledge, and service quality across all departments.",
            "category": "Staff Development",
            "suggested_timeline_months": 12,
            "default_metrics": [
                {"name": "Training hours per staff", "unit": "hours", "target_placeholder": "40"},
                {"name": "Staff completing program", "unit": "%", "target_placeholder": "100"},
                {"name": "New certifications earned", "unit": "certifications", "target_placeholder": "15"},
            ],
            "is_system_template": True,
        },
    ]

    created_count = 0
    for template_data in default_templates:
        # Check if template with same name already exists
        result = await db.execute(
            select(StrategicGoalTemplate).where(
                StrategicGoalTemplate.name == template_data["name"]
            )
        )
        existing = result.scalar_one_or_none()
        if not existing:
            template = StrategicGoalTemplate(**template_data)
            db.add(template)
            created_count += 1

    await db.commit()
    return {
        "message": f"Seeded {created_count} default templates",
        "total_templates": len(default_templates),
        "created": created_count,
        "skipped": len(default_templates) - created_count,
    }


# ============================================================================
# Public "Our Story" Endpoint
# ============================================================================

@router.get("/our-story", response_model=OurStoryResponse)
async def get_our_story(db: AsyncSession = Depends(get_db)):
    """Get public-facing strategic plan content for 'Our Story' page."""
    # Get active plan with goals and milestones
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.status == "active")
        .options(
            selectinload(StrategicPlan.goals), selectinload(StrategicPlan.milestones)
        )
        .limit(1)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return OurStoryResponse(has_plan=False)

    # Filter public goals
    public_goals = [
        PublicGoalProgress(
            id=g.id,
            title=g.title,
            description=g.public_description or g.description,
            category=g.category,
            progress=g.progress,
            status=g.status,
        )
        for g in plan.goals
        if g.is_public
    ]

    # Filter public milestones
    public_milestones = [
        PublicMilestone(
            id=m.id,
            title=m.title,
            celebration_text=m.celebration_text,
            impact_story=m.impact_story,
            photo_url=m.photo_url,
            achieved_date=m.achieved_date,
            milestone_type=m.milestone_type,
        )
        for m in plan.milestones
        if m.is_public
    ]

    # Parse history timeline
    history = []
    if plan.history_timeline:
        for event in plan.history_timeline:
            history.append(
                TimelineEvent(
                    year=event.get("year", 0),
                    title=event.get("title", ""),
                    description=event.get("description"),
                    image_url=event.get("image_url"),
                )
            )

    return OurStoryResponse(
        has_plan=True,
        mission=plan.mission,
        vision=plan.vision,
        values=plan.values or [],
        story_intro=plan.story_intro,
        hero_image_url=plan.hero_image_url,
        history_timeline=history,
        goals=public_goals,
        milestones=public_milestones,
        plan_period=f"{plan.period_start.year}-{plan.period_end.year}",
    )


# ============================================================================
# Import/Export Endpoints
# ============================================================================

@router.get("/plans/{plan_id}/export")
async def export_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export a strategic plan as JSON (admin only)."""
    check_admin_access(current_user)

    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.id == plan_id)
        .options(
            selectinload(StrategicPlan.goals), selectinload(StrategicPlan.milestones)
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {
        "title": plan.title,
        "description": plan.description,
        "period_start": plan.period_start.isoformat() if plan.period_start else None,
        "period_end": plan.period_end.isoformat() if plan.period_end else None,
        "mission": plan.mission,
        "vision": plan.vision,
        "values": plan.values,
        "story_intro": plan.story_intro,
        "hero_image_url": plan.hero_image_url,
        "history_timeline": plan.history_timeline,
        "goals": [
            {
                "title": g.title,
                "description": g.description,
                "public_description": g.public_description,
                "category": g.category,
                "department": g.department,
                "target_date": g.target_date.isoformat() if g.target_date else None,
                "progress": g.progress,
                "status": g.status,
                "metrics": g.metrics,
                "priority": g.priority,
                "is_public": g.is_public,
                "staff_can_update": g.staff_can_update,
            }
            for g in plan.goals
        ],
        "milestones": [
            {
                "title": m.title,
                "description": m.description,
                "achieved_date": (
                    m.achieved_date.isoformat() if m.achieved_date else None
                ),
                "celebration_text": m.celebration_text,
                "impact_story": m.impact_story,
                "photo_url": m.photo_url,
                "is_public": m.is_public,
                "is_featured": m.is_featured,
                "display_order": m.display_order,
                "milestone_type": m.milestone_type,
            }
            for m in plan.milestones
        ],
    }


@router.post("/import")
async def import_plan(
    plan_data: ImportPlanData,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import a strategic plan from JSON (admin only)."""
    check_admin_access(current_user)

    # Parse dates
    from dateutil.parser import parse as parse_date

    plan = StrategicPlan(
        title=plan_data.title,
        description=plan_data.description,
        period_start=parse_date(plan_data.period_start),
        period_end=parse_date(plan_data.period_end),
        mission=plan_data.mission,
        vision=plan_data.vision,
        values=plan_data.values,
        story_intro=plan_data.story_intro,
        hero_image_url=plan_data.hero_image_url,
        history_timeline=plan_data.history_timeline,
        status="draft",
        created_by_id=current_user.id,
    )
    db.add(plan)
    await db.flush()  # Get the plan ID

    # Import goals
    for goal_data in plan_data.goals or []:
        goal = StrategicGoal(
            plan_id=plan.id,
            title=goal_data.get("title", "Untitled Goal"),
            description=goal_data.get("description"),
            public_description=goal_data.get("public_description"),
            category=goal_data.get("category"),
            department=goal_data.get("department"),
            target_date=(
                parse_date(goal_data["target_date"])
                if goal_data.get("target_date")
                else None
            ),
            progress=goal_data.get("progress", 0),
            status=goal_data.get("status", "not_started"),
            metrics=goal_data.get("metrics", []),
            priority=goal_data.get("priority", 3),
            is_public=goal_data.get("is_public", True),
            staff_can_update=goal_data.get("staff_can_update", False),
        )
        db.add(goal)

    # Import milestones
    for milestone_data in plan_data.milestones or []:
        milestone = StrategicMilestone(
            plan_id=plan.id,
            title=milestone_data.get("title", "Untitled Milestone"),
            description=milestone_data.get("description"),
            achieved_date=(
                parse_date(milestone_data["achieved_date"])
                if milestone_data.get("achieved_date")
                else None
            ),
            celebration_text=milestone_data.get("celebration_text"),
            impact_story=milestone_data.get("impact_story"),
            photo_url=milestone_data.get("photo_url"),
            is_public=milestone_data.get("is_public", True),
            is_featured=milestone_data.get("is_featured", False),
            display_order=milestone_data.get("display_order", 0),
            milestone_type=milestone_data.get("milestone_type", "achievement"),
            created_by_id=current_user.id,
        )
        db.add(milestone)

    await db.commit()
    await db.refresh(plan)

    return {
        "message": "Plan imported successfully",
        "plan_id": plan.id,
        "goals_imported": len(plan_data.goals or []),
        "milestones_imported": len(plan_data.milestones or []),
    }


# ============================================================================
# Staff Department View
# ============================================================================

@router.get("/staff/my-goals")
async def get_staff_goals(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get goals relevant to the current staff member's department."""
    check_staff_access(current_user)

    # Get active plan
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.status == "active")
        .options(selectinload(StrategicPlan.goals))
        .limit(1)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return {"has_plan": False, "goals": []}

    # For now, return all goals that staff can update
    # In future, could filter by department matching user's department
    staff_goals = [
        {
            "id": g.id,
            "title": g.title,
            "description": g.description,
            "category": g.category,
            "department": g.department,
            "progress": g.progress,
            "status": g.status,
            "can_update": g.staff_can_update,
            "target_date": g.target_date.isoformat() if g.target_date else None,
            "metrics": g.metrics,
        }
        for g in plan.goals
        if g.staff_can_update or g.department
    ]

    return {
        "has_plan": True,
        "plan_title": plan.title,
        "mission": plan.mission,
        "goals": staff_goals,
    }


@router.get("/import")
async def get_import(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get /import information."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")

