# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.error_codes import ErrorCode
from ..core.exceptions import ResourceNotFoundError, ValidationError
from ..core.datetime_utils import utc_now
from ..models.strategic import (
    GoalStatus,
    PlanStatus,
    StrategicAttachment,
    StrategicComment,
    StrategicGoal,
    StrategicGoalTemplate,
    StrategicMilestone,
    StrategicNotification,
    StrategicPlan,
)

logger = get_logger(__name__)

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/uploads/strategic")


# ---------------------------------------------------------------------------
# Plan operations
# ---------------------------------------------------------------------------


async def get_active_plan(db: AsyncSession) -> Optional[StrategicPlan]:
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.status == PlanStatus.ACTIVE)
        .options(selectinload(StrategicPlan.goals))
        .order_by(StrategicPlan.period_start.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_plans(
    db: AsyncSession,
    *,
    is_staff: bool = False,
    plan_status: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> Dict[str, Any]:
    query = select(StrategicPlan).options(selectinload(StrategicPlan.goals))
    count_query = select(func.count(StrategicPlan.id))

    if not is_staff:
        query = query.where(StrategicPlan.status == PlanStatus.ACTIVE)
        count_query = count_query.where(StrategicPlan.status == PlanStatus.ACTIVE)
    elif plan_status:
        query = query.where(StrategicPlan.status == plan_status)
        count_query = count_query.where(StrategicPlan.status == plan_status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.order_by(StrategicPlan.period_start.desc()).offset(offset).limit(per_page)
    result = await db.execute(query)
    plans = result.scalars().all()

    return {"plans": plans, "total": total}


async def get_plan_by_id(db: AsyncSession, plan_id: int) -> StrategicPlan:
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.id == plan_id)
        .options(selectinload(StrategicPlan.goals))
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Plan not found",
        )
    return plan


async def create_plan(plan_data: dict, db: AsyncSession) -> StrategicPlan:
    db_plan = StrategicPlan(**plan_data)
    db.add(db_plan)
    await db.commit()
    await db.refresh(db_plan)

    # Reload with goals relationship
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.id == db_plan.id)
        .options(selectinload(StrategicPlan.goals))
    )
    return result.scalar_one()


async def update_plan(
    plan_id: int, plan_data: dict, db: AsyncSession
) -> StrategicPlan:
    result = await db.execute(
        select(StrategicPlan).where(StrategicPlan.id == plan_id)
    )
    db_plan = result.scalar_one_or_none()
    if not db_plan:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Strategic plan not found",
        )

    for key, value in plan_data.items():
        setattr(db_plan, key, value)
    db_plan.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_plan)

    # Reload with goals relationship
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.id == db_plan.id)
        .options(selectinload(StrategicPlan.goals))
    )
    return result.scalar_one()


async def activate_plan(plan_id: int, db: AsyncSession) -> str:
    # Deactivate current active plans
    result = await db.execute(
        select(StrategicPlan).where(StrategicPlan.status == PlanStatus.ACTIVE)
    )
    for active_plan in result.scalars().all():
        active_plan.status = PlanStatus.ARCHIVED

    # Activate the requested plan
    result = await db.execute(
        select(StrategicPlan).where(StrategicPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Plan not found",
        )

    plan.status = PlanStatus.ACTIVE
    plan.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return plan.title


async def delete_plan(plan_id: int, db: AsyncSession) -> None:
    result = await db.execute(
        select(StrategicPlan).where(StrategicPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Plan not found",
        )
    if plan.status == PlanStatus.ACTIVE:
        raise ValidationError(
            code=ErrorCode.INVALID_PARAMETER,
            message="Cannot delete active plan. Archive it first.",
        )
    await db.delete(plan)
    await db.commit()


async def export_plan(plan_id: int, db: AsyncSession) -> dict:
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.id == plan_id)
        .options(
            selectinload(StrategicPlan.goals),
            selectinload(StrategicPlan.milestones),
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Plan not found",
        )

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
                "achieved_date": m.achieved_date.isoformat() if m.achieved_date else None,
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


async def import_plan(
    plan_data: dict, user_id: int, db: AsyncSession
) -> Dict[str, Any]:
    from dateutil.parser import parse as parse_date

    plan = StrategicPlan(
        title=plan_data["title"],
        description=plan_data.get("description"),
        period_start=parse_date(plan_data["period_start"]),
        period_end=parse_date(plan_data["period_end"]),
        mission=plan_data.get("mission"),
        vision=plan_data.get("vision"),
        values=plan_data.get("values", []),
        story_intro=plan_data.get("story_intro"),
        hero_image_url=plan_data.get("hero_image_url"),
        history_timeline=plan_data.get("history_timeline", []),
        status="draft",
        created_by_id=user_id,
    )
    db.add(plan)
    await db.flush()

    goals_list = plan_data.get("goals") or []
    for goal_data in goals_list:
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

    milestones_list = plan_data.get("milestones") or []
    for milestone_data in milestones_list:
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
            created_by_id=user_id,
        )
        db.add(milestone)

    await db.commit()
    await db.refresh(plan)

    return {
        "message": "Plan imported successfully",
        "plan_id": plan.id,
        "goals_imported": len(goals_list),
        "milestones_imported": len(milestones_list),
    }


async def get_import_info() -> dict:
    return {
        "import_types": [
            {
                "type": "goals",
                "description": "Import strategic goals from templates",
                "available": True,
            },
            {
                "type": "milestones",
                "description": "Import milestones for existing goals",
                "available": True,
            },
            {
                "type": "templates",
                "description": "Import goal templates",
                "available": True,
            },
        ],
        "message": "Use POST /strategic/import to import data",
    }


# ---------------------------------------------------------------------------
# Goal operations
# ---------------------------------------------------------------------------


async def create_goal(
    goal_data: dict, plan_id: int, db: AsyncSession
) -> StrategicGoal:
    plan_result = await db.execute(
        select(StrategicPlan).where(StrategicPlan.id == plan_id)
    )
    if not plan_result.scalar_one_or_none():
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Plan not found",
        )

    goal = StrategicGoal(plan_id=plan_id, **goal_data)
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


async def list_goals(
    db: AsyncSession,
    plan_id: int,
    *,
    page: int = 1,
    per_page: int = 20,
    goal_status: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    plan_result = await db.execute(
        select(StrategicPlan).where(StrategicPlan.id == plan_id)
    )
    if not plan_result.scalar_one_or_none():
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Plan not found",
        )

    query = select(StrategicGoal).where(StrategicGoal.plan_id == plan_id)
    count_query = select(func.count(StrategicGoal.id)).where(
        StrategicGoal.plan_id == plan_id
    )

    if goal_status:
        query = query.where(StrategicGoal.status == goal_status)
        count_query = count_query.where(StrategicGoal.status == goal_status)
    if category:
        query = query.where(StrategicGoal.category == category)
        count_query = count_query.where(StrategicGoal.category == category)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = (
        query.order_by(StrategicGoal.display_order, StrategicGoal.created_at)
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    goals = result.scalars().all()

    return {"goals": goals, "total": total}


async def get_goal_by_id(db: AsyncSession, goal_id: int) -> StrategicGoal:
    result = await db.execute(
        select(StrategicGoal).where(StrategicGoal.id == goal_id)
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Goal not found",
        )
    return goal


_UPDATABLE_GOAL_FIELDS = {"title", "description", "category", "target_date", "progress", "status", "metrics", "owner", "priority"}


async def update_goal(
    goal_id: int, goal_data: dict, db: AsyncSession
) -> StrategicGoal:
    goal = await get_goal_by_id(db, goal_id)

    new_status = goal_data.get("status")
    for key, value in goal_data.items():
        if key in _UPDATABLE_GOAL_FIELDS:
            setattr(goal, key, value)

    goal.updated_at = datetime.now(timezone.utc)

    if new_status == "completed" and not goal.completed_date:
        goal.completed_date = datetime.now(timezone.utc)
        goal.progress = 100

    await db.commit()
    await db.refresh(goal)
    return goal


async def record_goal_progress(
    goal_id: int,
    progress: int,
    note: Optional[str],
    status: Optional[str],
    user_email: str,
    db: AsyncSession,
) -> StrategicGoal:
    goal = await get_goal_by_id(db, goal_id)

    goal.progress = progress

    if status:
        goal.status = status

    if progress >= 100:
        goal.status = GoalStatus.COMPLETED
        goal.completed_date = datetime.now(timezone.utc)

    updates = goal.updates or []
    updates.append(
        {
            "date": datetime.now(timezone.utc).isoformat(),
            "progress": progress,
            "note": note,
            "updated_by": user_email,
        }
    )
    goal.updates = updates
    goal.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(goal)
    return goal


async def get_goal_progress(
    goal_id: int, db: AsyncSession
) -> dict:
    goal = await get_goal_by_id(db, goal_id)

    milestones_result = await db.execute(
        select(StrategicMilestone)
        .where(StrategicMilestone.goal_id == goal_id)
        .order_by(StrategicMilestone.achieved_date)
    )
    milestones = milestones_result.scalars().all()

    achieved_milestones = sum(1 for m in milestones if m.achieved_date is not None)
    total_milestones = len(milestones)
    milestone_progress = (
        (achieved_milestones / total_milestones * 100)
        if total_milestones > 0
        else 0
    )

    return {
        "goal_id": goal.id,
        "title": goal.title,
        "overall_progress": goal.progress,
        "status": goal.status,
        "target_date": goal.target_date,
        "completed_date": goal.completed_date,
        "milestones": {
            "total": total_milestones,
            "completed": achieved_milestones,
            "progress_percent": int(milestone_progress),
        },
        "metrics": goal.metrics or [],
        "updates": goal.updates or [],
    }


async def delete_goal(goal_id: int, db: AsyncSession) -> None:
    goal = await get_goal_by_id(db, goal_id)
    await db.delete(goal)
    await db.commit()


async def reorder_goals(
    plan_id: int, goal_ids: List[int], db: AsyncSession
) -> None:
    # Verify plan exists
    result = await db.execute(
        select(StrategicPlan).where(StrategicPlan.id == plan_id)
    )
    if not result.scalar_one_or_none():
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Plan not found",
        )

    for index, gid in enumerate(goal_ids):
        result = await db.execute(
            select(StrategicGoal).where(
                StrategicGoal.id == gid, StrategicGoal.plan_id == plan_id
            )
        )
        goal = result.scalar_one_or_none()
        if goal:
            goal.display_order = index
            goal.updated_at = utc_now()

    await db.commit()


async def get_staff_goals(db: AsyncSession) -> dict:
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.status == "active")
        .options(selectinload(StrategicPlan.goals))
        .limit(1)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return {"has_plan": False, "goals": []}

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


async def update_goal_progress(
    goal_id: int, progress: int, db: AsyncSession
) -> StrategicGoal:
    if not (0 <= progress <= 100):
        raise ValidationError(
            code=ErrorCode.INVALID_PARAMETER,
            message="Progress must be between 0 and 100",
        )

    goal = await get_goal_by_id(db, goal_id)
    goal.progress = progress
    goal.updated_at = datetime.now(timezone.utc)

    if progress == 100 and goal.status != GoalStatus.COMPLETED:
        goal.status = GoalStatus.COMPLETED
        goal.completed_date = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(goal)
    return goal


async def update_goal_status(
    goal_id: int, status: str, db: AsyncSession
) -> StrategicGoal:
    goal = await get_goal_by_id(db, goal_id)
    if isinstance(status, str):
        status = GoalStatus(status)
    goal.status = status
    goal.updated_at = datetime.now(timezone.utc)

    if status == GoalStatus.COMPLETED and not goal.completed_date:
        goal.completed_date = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(goal)
    return goal


# ---------------------------------------------------------------------------
# Milestone operations
# ---------------------------------------------------------------------------


async def list_milestones(
    db: AsyncSession,
    plan_id: int,
    *,
    page: int = 1,
    per_page: int = 20,
    include_private: bool = False,
    is_staff: bool = False,
) -> Dict[str, Any]:
    query = select(StrategicMilestone).where(StrategicMilestone.plan_id == plan_id)
    count_query = select(func.count(StrategicMilestone.id)).where(
        StrategicMilestone.plan_id == plan_id
    )

    if not include_private or not is_staff:
        query = query.where(StrategicMilestone.is_public == True)  # noqa: E712
        count_query = count_query.where(StrategicMilestone.is_public == True)  # noqa: E712

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = (
        query.order_by(
            StrategicMilestone.display_order,
            StrategicMilestone.achieved_date.desc(),
        )
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    milestones = result.scalars().all()

    return {"milestones": milestones, "total": total}


async def create_milestone(
    milestone_data: dict,
    plan_id: int,
    user_id: int,
    db: AsyncSession,
) -> StrategicMilestone:
    plan_result = await db.execute(
        select(StrategicPlan).where(StrategicPlan.id == plan_id)
    )
    if not plan_result.scalar_one_or_none():
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Plan not found",
        )

    milestone = StrategicMilestone(
        plan_id=plan_id, created_by_id=user_id, **milestone_data
    )
    db.add(milestone)
    await db.commit()
    await db.refresh(milestone)
    return milestone


async def update_milestone(
    milestone_id: int, milestone_data: dict, db: AsyncSession
) -> StrategicMilestone:
    result = await db.execute(
        select(StrategicMilestone).where(StrategicMilestone.id == milestone_id)
    )
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Milestone not found",
        )

    for key, value in milestone_data.items():
        setattr(milestone, key, value)
    milestone.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(milestone)
    return milestone


async def delete_milestone(milestone_id: int, db: AsyncSession) -> None:
    result = await db.execute(
        select(StrategicMilestone).where(StrategicMilestone.id == milestone_id)
    )
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Milestone not found",
        )
    await db.delete(milestone)
    await db.commit()


# ---------------------------------------------------------------------------
# Template operations
# ---------------------------------------------------------------------------


async def list_templates(
    db: AsyncSession, *, category: Optional[str] = None
) -> List[StrategicGoalTemplate]:
    query = select(StrategicGoalTemplate)
    if category:
        query = query.where(StrategicGoalTemplate.category == category)
    query = query.order_by(StrategicGoalTemplate.name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_template_by_id(
    db: AsyncSession, template_id: int
) -> StrategicGoalTemplate:
    result = await db.execute(
        select(StrategicGoalTemplate).where(
            StrategicGoalTemplate.id == template_id
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Template not found",
        )
    return template


async def create_template(
    template_data: dict, db: AsyncSession
) -> StrategicGoalTemplate:
    template = StrategicGoalTemplate(**template_data)
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def update_template(
    template_id: int, template_data: dict, db: AsyncSession
) -> StrategicGoalTemplate:
    template = await get_template_by_id(db, template_id)
    for key, value in template_data.items():
        setattr(template, key, value)
    await db.commit()
    await db.refresh(template)
    return template


async def delete_template(template_id: int, db: AsyncSession) -> None:
    template = await get_template_by_id(db, template_id)
    await db.delete(template)
    await db.commit()


async def seed_default_templates(db: AsyncSession) -> dict:
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
    for tpl_data in default_templates:
        result = await db.execute(
            select(StrategicGoalTemplate).where(
                StrategicGoalTemplate.name == tpl_data["name"]
            )
        )
        if not result.scalar_one_or_none():
            db.add(StrategicGoalTemplate(**tpl_data))
            created_count += 1

    await db.commit()
    return {
        "message": f"Seeded {created_count} default templates",
        "total_templates": len(default_templates),
        "created": created_count,
        "skipped": len(default_templates) - created_count,
    }


# ---------------------------------------------------------------------------
# Comment operations
# ---------------------------------------------------------------------------


async def create_comment(
    goal_id: int,
    user_id: int,
    content: str,
    parent_id: Optional[int],
    db: AsyncSession,
) -> StrategicComment:
    await get_goal_by_id(db, goal_id)

    if parent_id:
        parent_result = await db.execute(
            select(StrategicComment).where(
                StrategicComment.id == parent_id,
                StrategicComment.goal_id == goal_id,
            )
        )
        if not parent_result.scalar_one_or_none():
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Parent comment not found",
            )

    comment = StrategicComment(
        goal_id=goal_id,
        user_id=user_id,
        content=content,
        parent_id=parent_id,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


async def list_comments(
    goal_id: int, db: AsyncSession
) -> List[Dict[str, Any]]:
    # Verify goal exists
    goal_result = await db.execute(
        select(StrategicGoal).where(StrategicGoal.id == goal_id)
    )
    if not goal_result.scalar_one_or_none():
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Goal not found",
        )

    result = await db.execute(
        select(StrategicComment)
        .where(StrategicComment.goal_id == goal_id)
        .options(selectinload(StrategicComment.user))
        .order_by(StrategicComment.created_at)
    )
    all_comments = result.scalars().all()

    comment_map: Dict[int, dict] = {}
    for c in all_comments:
        comment_map[c.id] = {
            "id": c.id,
            "goal_id": c.goal_id,
            "user_id": c.user_id,
            "content": c.content,
            "parent_id": c.parent_id,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "user": c.user,
            "replies": [],
        }

    root_comments: List[dict] = []
    for c in all_comments:
        if c.parent_id and c.parent_id in comment_map:
            comment_map[c.parent_id]["replies"].append(comment_map[c.id])
        else:
            root_comments.append(comment_map[c.id])

    return root_comments


async def get_comment_by_id(
    comment_id: int, db: AsyncSession
) -> Tuple[StrategicComment, List[StrategicComment]]:
    result = await db.execute(
        select(StrategicComment)
        .where(StrategicComment.id == comment_id)
        .options(selectinload(StrategicComment.user))
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Comment not found",
        )

    replies_result = await db.execute(
        select(StrategicComment)
        .where(StrategicComment.parent_id == comment_id)
        .options(selectinload(StrategicComment.user))
        .order_by(StrategicComment.created_at)
    )
    replies = list(replies_result.scalars().all())
    return comment, replies


async def update_comment(
    comment_id: int, content: str, user_id: int, db: AsyncSession
) -> StrategicComment:
    result = await db.execute(
        select(StrategicComment)
        .where(StrategicComment.id == comment_id)
        .options(selectinload(StrategicComment.user))
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Comment not found",
        )

    if comment.user_id != user_id:
        raise ValidationError(
            code=ErrorCode.INVALID_PARAMETER,
            message="Only the comment owner can update this comment",
        )

    comment.content = content
    comment.updated_at = utc_now()
    await db.commit()
    await db.refresh(comment)
    return comment


async def delete_comment(
    comment_id: int, user_id: int, is_admin: bool, db: AsyncSession
) -> None:
    result = await db.execute(
        select(StrategicComment).where(StrategicComment.id == comment_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Comment not found",
        )

    if comment.user_id != user_id and not is_admin:
        raise ValidationError(
            code=ErrorCode.INVALID_PARAMETER,
            message="Only the comment owner or admin can delete this comment",
        )

    await db.delete(comment)
    await db.commit()


# ---------------------------------------------------------------------------
# Notification operations
# ---------------------------------------------------------------------------


async def list_notifications(
    user_id: int,
    db: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 20,
    unread_only: bool = False,
) -> List[StrategicNotification]:
    query = select(StrategicNotification).where(
        StrategicNotification.user_id == user_id
    )
    if unread_only:
        query = query.where(StrategicNotification.is_read == False)  # noqa: E712

    offset = (page - 1) * per_page
    query = (
        query.order_by(StrategicNotification.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def mark_notification_read(
    notification_id: int, user_id: int, db: AsyncSession
) -> None:
    result = await db.execute(
        select(StrategicNotification).where(
            StrategicNotification.id == notification_id,
            StrategicNotification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Notification not found",
        )
    notification.is_read = True
    await db.commit()


async def mark_all_notifications_read(
    user_id: int, db: AsyncSession
) -> int:
    result = await db.execute(
        select(StrategicNotification).where(
            StrategicNotification.user_id == user_id,
            StrategicNotification.is_read == False,  # noqa: E712
        )
    )
    notifications = result.scalars().all()
    count = 0
    for n in notifications:
        n.is_read = True
        count += 1
    await db.commit()
    return count


async def get_unread_notification_count(
    user_id: int, db: AsyncSession
) -> int:
    result = await db.execute(
        select(func.count(StrategicNotification.id)).where(
            StrategicNotification.user_id == user_id,
            StrategicNotification.is_read == False,  # noqa: E712
        )
    )
    return result.scalar() or 0


# ---------------------------------------------------------------------------
# Attachment operations
# ---------------------------------------------------------------------------


async def upload_attachment(
    goal_id: int,
    filename: Optional[str],
    content_type: Optional[str],
    content: bytes,
    user_id: int,
    db: AsyncSession,
) -> StrategicAttachment:
    # Verify goal exists
    goal_result = await db.execute(
        select(StrategicGoal).where(StrategicGoal.id == goal_id)
    )
    if not goal_result.scalar_one_or_none():
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Goal not found",
        )

    if len(content) > 10 * 1024 * 1024:
        raise ValidationError(
            code=ErrorCode.INVALID_PARAMETER,
            message="File too large. Maximum size is 10MB.",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_ext = os.path.splitext(filename)[1] if filename else ""
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    attachment = StrategicAttachment(
        goal_id=goal_id,
        filename=filename or unique_filename,
        file_url=f"/uploads/strategic/{unique_filename}",
        file_type=content_type,
        file_size=len(content),
        uploaded_by_id=user_id,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    return attachment


async def list_attachments(
    goal_id: int, db: AsyncSession
) -> List[StrategicAttachment]:
    goal_result = await db.execute(
        select(StrategicGoal).where(StrategicGoal.id == goal_id)
    )
    if not goal_result.scalar_one_or_none():
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Goal not found",
        )

    result = await db.execute(
        select(StrategicAttachment)
        .where(StrategicAttachment.goal_id == goal_id)
        .order_by(StrategicAttachment.created_at.desc())
    )
    return list(result.scalars().all())


async def get_attachment_by_id(
    attachment_id: int, db: AsyncSession
) -> StrategicAttachment:
    result = await db.execute(
        select(StrategicAttachment).where(
            StrategicAttachment.id == attachment_id
        )
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Attachment not found",
        )
    return attachment


async def delete_attachment(attachment_id: int, db: AsyncSession) -> None:
    attachment = await get_attachment_by_id(attachment_id, db)

    try:
        file_path = os.path.join(UPLOAD_DIR, os.path.basename(attachment.file_url))
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        pass  # Continue even if file deletion fails

    await db.delete(attachment)
    await db.commit()


# ---------------------------------------------------------------------------
# Analytics / Dashboard / Board Report
# ---------------------------------------------------------------------------


def _compute_status_breakdown(goals) -> Dict[str, int]:
    return {
        "not_started": sum(1 for g in goals if g.status == GoalStatus.NOT_STARTED),
        "on_track": sum(1 for g in goals if g.status == GoalStatus.ON_TRACK),
        "at_risk": sum(1 for g in goals if g.status == GoalStatus.AT_RISK),
        "delayed": sum(1 for g in goals if g.status == GoalStatus.DELAYED),
        "completed": sum(1 for g in goals if g.status == GoalStatus.COMPLETED),
    }


def _compute_goals_by_department(goals) -> List[Dict[str, Any]]:
    dept_map: Dict[str, Dict[str, int]] = {}
    for g in goals:
        dept = g.department or "Unassigned"
        if dept not in dept_map:
            dept_map[dept] = {"count": 0, "progress_sum": 0}
        dept_map[dept]["count"] += 1
        dept_map[dept]["progress_sum"] += g.progress
    return [
        {
            "department": dept,
            "count": data["count"],
            "progress": data["progress_sum"] // data["count"] if data["count"] > 0 else 0,
        }
        for dept, data in dept_map.items()
    ]


def _compute_goals_by_category(goals) -> List[Dict[str, Any]]:
    cat_map: Dict[str, Dict[str, int]] = {}
    for g in goals:
        cat = g.category or "Uncategorized"
        if cat not in cat_map:
            cat_map[cat] = {"count": 0, "progress_sum": 0}
        cat_map[cat]["count"] += 1
        cat_map[cat]["progress_sum"] += g.progress
    return [
        {
            "category": cat,
            "count": data["count"],
            "progress": data["progress_sum"] // data["count"] if data["count"] > 0 else 0,
        }
        for cat, data in cat_map.items()
    ]


def _compute_at_risk_goals(goals, now) -> List[Dict[str, Any]]:
    at_risk: List[Dict[str, Any]] = []
    for g in goals:
        if g.status == GoalStatus.AT_RISK:
            at_risk.append({
                "id": g.id, "title": g.title, "status": g.status.value,
                "progress": g.progress, "target_date": g.target_date,
                "reason": "Marked as at-risk",
            })
        elif g.status == GoalStatus.DELAYED:
            at_risk.append({
                "id": g.id, "title": g.title, "status": g.status.value,
                "progress": g.progress, "target_date": g.target_date,
                "reason": "Goal is delayed",
            })
        elif g.target_date and g.status != GoalStatus.COMPLETED:
            days_remaining = ((g.target_date if g.target_date.tzinfo else g.target_date.replace(tzinfo=timezone.utc)) - now).days
            if days_remaining < 0:
                at_risk.append({
                    "id": g.id, "title": g.title, "status": g.status.value,
                    "progress": g.progress, "target_date": g.target_date,
                    "reason": f"Overdue by {abs(days_remaining)} days",
                })
    return at_risk


async def get_dashboard(db: AsyncSession) -> dict:
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.status == PlanStatus.ACTIVE)
        .options(selectinload(StrategicPlan.goals))
        .limit(1)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return {"has_active_plan": False, "message": "No active strategic plan"}

    goals = plan.goals
    total_goals = len(goals)

    completed = sum(1 for g in goals if g.status == GoalStatus.COMPLETED)
    on_track = sum(1 for g in goals if g.status == GoalStatus.ON_TRACK)
    at_risk = sum(1 for g in goals if g.status == GoalStatus.AT_RISK)
    delayed = sum(1 for g in goals if g.status == GoalStatus.DELAYED)
    overall_progress = (
        sum(g.progress for g in goals) // total_goals if total_goals > 0 else 0
    )

    categories: Dict[str, Dict[str, int]] = {}
    for g in goals:
        cat = g.category or "Uncategorized"
        if cat not in categories:
            categories[cat] = {"count": 0, "progress": 0}
        categories[cat]["count"] += 1
        categories[cat]["progress"] += g.progress
    for cat in categories:
        categories[cat]["progress"] = (
            categories[cat]["progress"] // categories[cat]["count"]
        )

    return {
        "has_active_plan": True,
        "plan": {
            "id": plan.id,
            "title": plan.title,
            "period": f"{plan.period_start.year}-{plan.period_end.year}",
            "mission": plan.mission,
            "vision": plan.vision,
            "values": plan.values or [],
        },
        "progress": {
            "overall": overall_progress,
            "total_goals": total_goals,
            "completed": completed,
            "on_track": on_track,
            "at_risk": at_risk,
            "delayed": delayed,
            "not_started": total_goals - completed - on_track - at_risk - delayed,
        },
        "by_category": categories,
        "next_review": plan.next_review.isoformat() if plan.next_review else None,
    }


async def get_our_story(db: AsyncSession) -> dict:
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.status == "active")
        .options(
            selectinload(StrategicPlan.goals),
            selectinload(StrategicPlan.milestones),
        )
        .limit(1)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return {"has_plan": False}

    public_goals = [
        {
            "id": g.id,
            "title": g.title,
            "description": g.public_description or g.description,
            "category": g.category,
            "progress": g.progress,
            "status": g.status,
        }
        for g in plan.goals
        if g.is_public
    ]

    public_milestones = [
        {
            "id": m.id,
            "title": m.title,
            "celebration_text": m.celebration_text,
            "impact_story": m.impact_story,
            "photo_url": m.photo_url,
            "achieved_date": m.achieved_date,
            "milestone_type": m.milestone_type,
        }
        for m in plan.milestones
        if m.is_public
    ]

    history = []
    if plan.history_timeline:
        for event in plan.history_timeline:
            history.append({
                "year": event.get("year", 0),
                "title": event.get("title", ""),
                "description": event.get("description"),
                "image_url": event.get("image_url"),
            })

    return {
        "has_plan": True,
        "mission": plan.mission,
        "vision": plan.vision,
        "values": plan.values or [],
        "story_intro": plan.story_intro,
        "hero_image_url": plan.hero_image_url,
        "history_timeline": history,
        "goals": public_goals,
        "milestones": public_milestones,
        "plan_period": f"{plan.period_start.year}-{plan.period_end.year}",
    }


async def get_analytics(db: AsyncSession) -> dict:
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.status == PlanStatus.ACTIVE)
        .options(selectinload(StrategicPlan.goals))
        .limit(1)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return {
            "overall_progress": 0,
            "goals_by_status": {"not_started": 0, "on_track": 0, "at_risk": 0, "delayed": 0, "completed": 0},
            "goals_by_department": [],
            "goals_by_category": [],
            "recent_progress_updates": [],
            "upcoming_deadlines": [],
            "at_risk_goals": [],
            "total_goals": 0,
            "plan_period": None,
        }

    goals = plan.goals
    total_goals = len(goals)
    overall_progress = (
        sum(g.progress for g in goals) // total_goals if total_goals > 0 else 0
    )

    status_breakdown = _compute_status_breakdown(goals)
    goals_by_department = _compute_goals_by_department(goals)
    goals_by_category = _compute_goals_by_category(goals)

    # Recent progress updates
    recent_updates = []
    for g in goals:
        if g.updates:
            for update in g.updates[-3:]:
                recent_updates.append({
                    "goal_id": g.id,
                    "goal_title": g.title,
                    "progress": update.get("progress", 0),
                    "note": update.get("note"),
                    "updated_at": update.get("date", ""),
                    "updated_by": update.get("updated_by"),
                })
    recent_updates.sort(key=lambda x: x["updated_at"], reverse=True)
    recent_updates = recent_updates[:10]

    # Upcoming deadlines
    now = utc_now()
    upcoming_deadlines = []
    for g in goals:
        if g.target_date and g.status != GoalStatus.COMPLETED:
            days_remaining = ((g.target_date if g.target_date.tzinfo else g.target_date.replace(tzinfo=timezone.utc)) - now).days
            if 0 <= days_remaining <= 30:
                upcoming_deadlines.append({
                    "goal_id": g.id,
                    "title": g.title,
                    "target_date": g.target_date,
                    "progress": g.progress,
                    "status": str(g.status),
                    "days_remaining": days_remaining,
                })
    upcoming_deadlines.sort(key=lambda x: x["days_remaining"])

    at_risk_goals = _compute_at_risk_goals(goals, now)

    return {
        "overall_progress": overall_progress,
        "goals_by_status": status_breakdown,
        "goals_by_department": goals_by_department,
        "goals_by_category": goals_by_category,
        "recent_progress_updates": recent_updates,
        "upcoming_deadlines": upcoming_deadlines,
        "at_risk_goals": at_risk_goals,
        "total_goals": total_goals,
        "plan_period": f"{plan.period_start.year}-{plan.period_end.year}",
    }


async def get_board_report(plan_id: int, db: AsyncSession) -> dict:
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.id == plan_id)
        .options(
            selectinload(StrategicPlan.goals),
            selectinload(StrategicPlan.milestones),
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Plan not found",
        )

    goals = plan.goals
    total_goals = len(goals)
    overall_progress = (
        sum(g.progress for g in goals) // total_goals if total_goals > 0 else 0
    )

    status_summary = _compute_status_breakdown(goals)

    # Goals by category (dict form for the report)
    goals_by_cat: Dict[str, Dict[str, int]] = {}
    for g in goals:
        cat = g.category or "Uncategorized"
        if cat not in goals_by_cat:
            goals_by_cat[cat] = {"count": 0, "progress": 0}
        goals_by_cat[cat]["count"] += 1
        goals_by_cat[cat]["progress"] += g.progress
    for cat in goals_by_cat:
        goals_by_cat[cat]["progress"] = (
            goals_by_cat[cat]["progress"] // goals_by_cat[cat]["count"]
            if goals_by_cat[cat]["count"] > 0
            else 0
        )

    report_goals = [
        {
            "id": g.id,
            "title": g.title,
            "description": g.description,
            "category": g.category,
            "department": g.department,
            "progress": g.progress,
            "status": str(g.status),
            "target_date": g.target_date,
            "owner": g.owner,
            "recent_updates": g.updates[-3:] if g.updates else [],
        }
        for g in goals
    ]

    report_milestones = [
        {
            "id": m.id,
            "title": m.title,
            "description": m.description,
            "achieved_date": m.achieved_date.isoformat() if m.achieved_date else None,
            "celebration_text": m.celebration_text,
            "milestone_type": m.milestone_type,
        }
        for m in plan.milestones
        if m.achieved_date
    ]

    key_achievements = []
    for g in goals:
        if g.status == GoalStatus.COMPLETED:
            key_achievements.append(f"Completed: {g.title}")
    for m in plan.milestones:
        if m.achieved_date:
            key_achievements.append(f"Milestone: {m.title}")

    areas_of_concern = []
    now = utc_now()
    for g in goals:
        if g.status == GoalStatus.AT_RISK:
            areas_of_concern.append(f"At Risk: {g.title} - {g.progress}% complete")
        elif g.status == GoalStatus.DELAYED:
            areas_of_concern.append(f"Delayed: {g.title} - {g.progress}% complete")
        elif g.target_date and g.status != GoalStatus.COMPLETED:
            days_remaining = ((g.target_date if g.target_date.tzinfo else g.target_date.replace(tzinfo=timezone.utc)) - now).days
            if days_remaining < 0:
                areas_of_concern.append(
                    f"Overdue: {g.title} - {g.progress}% complete, {abs(days_remaining)} days overdue"
                )

    return {
        "generated_at": utc_now(),
        "plan_id": plan.id,
        "plan_title": plan.title,
        "plan_period": f"{plan.period_start.year}-{plan.period_end.year}",
        "mission": plan.mission,
        "vision": plan.vision,
        "overall_progress": overall_progress,
        "status_summary": status_summary,
        "goals_by_category": goals_by_cat,
        "goals": report_goals,
        "milestones": report_milestones,
        "key_achievements": key_achievements,
        "areas_of_concern": areas_of_concern,
    }
