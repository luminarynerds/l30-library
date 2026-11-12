# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Strategic Planning - Board Meeting & Analytics Endpoints

Handles board reports, analytics dashboards, and strategic plan metrics.
Provides comprehensive views for board meetings and leadership review.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.strategic import GoalStatus, PlanStatus, StrategicGoal, StrategicPlan
from ...models.user import User
from .auth import get_current_user, get_current_user_optional
from .dependencies import check_staff_access, check_admin_access
from app.core.datetime_utils import utc_now

router = APIRouter(prefix="/strategic", tags=["strategic-board"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class GoalStatusBreakdown(BaseModel):
    not_started: int = 0
    on_track: int = 0
    at_risk: int = 0
    delayed: int = 0
    completed: int = 0


class DepartmentBreakdown(BaseModel):
    department: str
    count: int
    progress: int


class CategoryBreakdown(BaseModel):
    category: str
    count: int
    progress: int


class RecentProgressUpdate(BaseModel):
    goal_id: int
    goal_title: str
    progress: int
    note: Optional[str] = None
    updated_at: str
    updated_by: Optional[str] = None


class UpcomingDeadline(BaseModel):
    goal_id: int
    title: str
    target_date: datetime
    progress: int
    status: str
    days_remaining: int


class AtRiskGoal(BaseModel):
    id: int
    title: str
    status: str
    progress: int
    target_date: Optional[datetime] = None
    reason: str


class AnalyticsResponse(BaseModel):
    overall_progress: int
    goals_by_status: GoalStatusBreakdown
    goals_by_department: List[DepartmentBreakdown]
    goals_by_category: List[CategoryBreakdown]
    recent_progress_updates: List[RecentProgressUpdate]
    upcoming_deadlines: List[UpcomingDeadline]
    at_risk_goals: List[AtRiskGoal]
    total_goals: int
    plan_period: Optional[str] = None


class BoardReportGoal(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    progress: int
    status: str
    target_date: Optional[datetime] = None
    owner: Optional[str] = None
    recent_updates: List[dict] = []


class BoardReportResponse(BaseModel):
    generated_at: datetime
    plan_id: int
    plan_title: str
    plan_period: str
    mission: Optional[str] = None
    vision: Optional[str] = None
    overall_progress: int
    status_summary: GoalStatusBreakdown
    goals_by_category: dict
    goals: List[BoardReportGoal]
    milestones: List[dict]
    key_achievements: List[str]
    areas_of_concern: List[str]


class DashboardResponse(BaseModel):
    has_active_plan: bool
    plan: Optional[dict] = None
    progress: Optional[dict] = None
    by_category: Optional[dict] = None
    next_review: Optional[str] = None


# ============================================================================
# Dashboard Endpoint
# ============================================================================

@router.get("/dashboard", response_model=DashboardResponse)
async def get_strategic_dashboard(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Get strategic planning dashboard summary."""
    # Get active plan
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.status == PlanStatus.ACTIVE)
        .options(selectinload(StrategicPlan.goals))
        .limit(1)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return DashboardResponse(has_active_plan=False, message="No active strategic plan")

    goals = plan.goals
    total_goals = len(goals)

    # Calculate stats
    completed = sum(1 for g in goals if g.status == GoalStatus.COMPLETED)
    on_track = sum(1 for g in goals if g.status == GoalStatus.ON_TRACK)
    at_risk = sum(1 for g in goals if g.status == GoalStatus.AT_RISK)
    delayed = sum(1 for g in goals if g.status == GoalStatus.DELAYED)

    overall_progress = (
        sum(g.progress for g in goals) // total_goals if total_goals > 0 else 0
    )

    # Goals by category
    categories = {}
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

    return DashboardResponse(
        has_active_plan=True,
        plan={
            "id": plan.id,
            "title": plan.title,
            "period": f"{plan.period_start.year}-{plan.period_end.year}",
            "mission": plan.mission,
            "vision": plan.vision,
            "values": plan.values or [],
        },
        progress={
            "overall": overall_progress,
            "total_goals": total_goals,
            "completed": completed,
            "on_track": on_track,
            "at_risk": at_risk,
            "delayed": delayed,
            "not_started": total_goals - completed - on_track - at_risk - delayed,
        },
        by_category=categories,
        next_review=plan.next_review.isoformat() if plan.next_review else None,
    )


# ============================================================================
# Analytics Endpoint
# ============================================================================

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive strategic planning analytics (staff/admin)."""
    check_staff_access(current_user)

    # Get active plan with goals
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.status == PlanStatus.ACTIVE)
        .options(selectinload(StrategicPlan.goals))
        .limit(1)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return AnalyticsResponse(
            overall_progress=0,
            goals_by_status=GoalStatusBreakdown(),
            goals_by_department=[],
            goals_by_category=[],
            recent_progress_updates=[],
            upcoming_deadlines=[],
            at_risk_goals=[],
            total_goals=0,
            plan_period=None,
        )

    goals = plan.goals
    total_goals = len(goals)
    now = utc_now()

    # Single pass over all goals to collect every metric at once
    progress_sum = 0
    status_counts = {"not_started": 0, "on_track": 0, "at_risk": 0, "delayed": 0, "completed": 0}
    dept_map = {}
    cat_map = {}
    recent_updates = []
    upcoming_deadlines = []
    at_risk_goals = []

    for g in goals:
        progress_sum += g.progress
        status_str = str(g.status)

        # Status counting
        for key in status_counts:
            if key in status_str.lower():
                status_counts[key] += 1
                break

        # Department aggregation
        dept = g.department or "Unassigned"
        if dept not in dept_map:
            dept_map[dept] = {"count": 0, "progress_sum": 0}
        dept_map[dept]["count"] += 1
        dept_map[dept]["progress_sum"] += g.progress

        # Category aggregation
        cat = g.category or "Uncategorized"
        if cat not in cat_map:
            cat_map[cat] = {"count": 0, "progress_sum": 0}
        cat_map[cat]["count"] += 1
        cat_map[cat]["progress_sum"] += g.progress

        # Recent updates
        if g.updates:
            for update in g.updates[-3:]:
                recent_updates.append(
                    RecentProgressUpdate(
                        goal_id=g.id,
                        goal_title=g.title,
                        progress=update.get("progress", 0),
                        note=update.get("note"),
                        updated_at=update.get("date", ""),
                        updated_by=update.get("updated_by"),
                    )
                )

        # Deadline and at-risk classification
        is_completed = status_str.lower() in ("completed", "goalstatus.completed")
        days_remaining = None
        if g.target_date and not is_completed:
            days_remaining = ((g.target_date if g.target_date.tzinfo else g.target_date.replace(tzinfo=timezone.utc)) - now).days
            if 0 <= days_remaining <= 30:
                upcoming_deadlines.append(
                    UpcomingDeadline(
                        goal_id=g.id,
                        title=g.title,
                        target_date=g.target_date,
                        progress=g.progress,
                        status=status_str,
                        days_remaining=days_remaining,
                    )
                )

        if status_str.lower() in ("at_risk", "goalstatus.at_risk"):
            at_risk_goals.append(
                AtRiskGoal(id=g.id, title=g.title, status=status_str, progress=g.progress,
                           target_date=g.target_date, reason="Marked as at-risk"))
        elif status_str.lower() in ("delayed", "goalstatus.delayed"):
            at_risk_goals.append(
                AtRiskGoal(id=g.id, title=g.title, status=status_str, progress=g.progress,
                           target_date=g.target_date, reason="Goal is delayed"))
        elif days_remaining is not None and days_remaining < 0:
            at_risk_goals.append(
                AtRiskGoal(id=g.id, title=g.title, status=status_str, progress=g.progress,
                           target_date=g.target_date, reason=f"Overdue by {abs(days_remaining)} days"))

    overall_progress = progress_sum // total_goals if total_goals > 0 else 0

    status_breakdown = GoalStatusBreakdown(
        not_started=status_counts["not_started"],
        on_track=status_counts["on_track"],
        at_risk=status_counts["at_risk"],
        delayed=status_counts["delayed"],
        completed=status_counts["completed"],
    )

    goals_by_department = [
        DepartmentBreakdown(
            department=dept,
            count=data["count"],
            progress=data["progress_sum"] // data["count"] if data["count"] > 0 else 0,
        )
        for dept, data in dept_map.items()
    ]

    goals_by_category = [
        CategoryBreakdown(
            category=cat,
            count=data["count"],
            progress=data["progress_sum"] // data["count"] if data["count"] > 0 else 0,
        )
        for cat, data in cat_map.items()
    ]

    recent_updates.sort(key=lambda x: x.updated_at, reverse=True)
    recent_updates = recent_updates[:10]
    upcoming_deadlines.sort(key=lambda x: x.days_remaining)

    return AnalyticsResponse(
        overall_progress=overall_progress,
        goals_by_status=status_breakdown,
        goals_by_department=goals_by_department,
        goals_by_category=goals_by_category,
        recent_progress_updates=recent_updates,
        upcoming_deadlines=upcoming_deadlines,
        at_risk_goals=at_risk_goals,
        total_goals=total_goals,
        plan_period=f"{plan.period_start.year}-{plan.period_end.year}",
    )


# ============================================================================
# Board Report Endpoint
# ============================================================================

@router.get("/plans/{plan_id}/board-report", response_model=BoardReportResponse)
async def get_board_report(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a formatted board report for a strategic plan (admin only)."""
    check_admin_access(current_user)

    # Get plan with goals and milestones
    result = await db.execute(
        select(StrategicPlan)
        .where(StrategicPlan.id == plan_id)
        .options(
            selectinload(StrategicPlan.goals),
            selectinload(StrategicPlan.milestones)
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    goals = plan.goals
    total_goals = len(goals)

    # Overall progress
    overall_progress = sum(g.progress for g in goals) // total_goals if total_goals > 0 else 0

    # Status summary
    status_summary = GoalStatusBreakdown(
        not_started=sum(1 for g in goals if g.status == GoalStatus.NOT_STARTED),
        on_track=sum(1 for g in goals if g.status == GoalStatus.ON_TRACK),
        at_risk=sum(1 for g in goals if g.status == GoalStatus.AT_RISK),
        delayed=sum(1 for g in goals if g.status == GoalStatus.DELAYED),
        completed=sum(1 for g in goals if g.status == GoalStatus.COMPLETED),
    )

    # Goals by category
    goals_by_cat = {}
    for g in goals:
        cat = g.category or "Uncategorized"
        if cat not in goals_by_cat:
            goals_by_cat[cat] = {"count": 0, "progress": 0}
        goals_by_cat[cat]["count"] += 1
        goals_by_cat[cat]["progress"] += g.progress

    for cat in goals_by_cat:
        goals_by_cat[cat]["progress"] = (
            goals_by_cat[cat]["progress"] // goals_by_cat[cat]["count"]
            if goals_by_cat[cat]["count"] > 0 else 0
        )

    # Format goals for report
    report_goals = [
        BoardReportGoal(
            id=g.id,
            title=g.title,
            description=g.description,
            category=g.category,
            department=g.department,
            progress=g.progress,
            status=g.status.value,
            target_date=g.target_date,
            owner=g.owner,
            recent_updates=g.updates[-3:] if g.updates else [],
        )
        for g in goals
    ]

    # Format milestones for report
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
        if m.achieved_date  # Only include achieved milestones
    ]

    # Key achievements (completed goals and achieved milestones)
    key_achievements = []
    for g in goals:
        if g.status == GoalStatus.COMPLETED:
            key_achievements.append(f"Completed: {g.title}")
    for m in plan.milestones:
        if m.achieved_date:
            key_achievements.append(f"Milestone: {m.title}")

    # Areas of concern (at-risk and delayed goals)
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

    return BoardReportResponse(
        generated_at=utc_now(),
        plan_id=plan.id,
        plan_title=plan.title,
        plan_period=f"{plan.period_start.year}-{plan.period_end.year}",
        mission=plan.mission,
        vision=plan.vision,
        overall_progress=overall_progress,
        status_summary=status_summary,
        goals_by_category=goals_by_cat,
        goals=report_goals,
        milestones=report_milestones,
        key_achievements=key_achievements,
        areas_of_concern=areas_of_concern,
    )
