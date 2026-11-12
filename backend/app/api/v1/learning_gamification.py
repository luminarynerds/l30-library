# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Learning - Gamification API Endpoints

Provides endpoints for:
- User stats (XP, level, streaks)
- Achievements
- Weekly activity analytics
- Comprehensive learning analytics
"""
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.gamification import Achievement, UserAchievement, UserStats
from ...models.learning import Course, Enrollment, Lesson, LessonProgress, Module
from ...models.user import User
from ...schemas.learning import (
    ComprehensiveAnalyticsResponse,
    DifficultyDistribution,
    RecentActivityItem,
    StreakDay,
    WeeklyActivityDay,
    WeeklyActivityResponse,
)
from ...services.organization_features_service import OrganizationFeaturesService
from .auth import get_current_user


async def require_gamification_enabled(db: AsyncSession = Depends(get_db)) -> None:
    enabled = await OrganizationFeaturesService.is_feature_enabled(db, "gamification_enabled")
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gamification feature is not enabled",
        )


router = APIRouter(
    prefix="/learning/gamification",
    tags=["learning-gamification"],
    dependencies=[Depends(require_gamification_enabled)],
)


def calculate_level(xp: int) -> int:
    level = 1
    xp_needed = 100
    remaining = xp
    while remaining >= xp_needed:
        remaining -= xp_needed
        level += 1
        xp_needed = int(100 * (1.5 ** (level - 1)))
    return level


@router.get("/stats")
async def get_my_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get current user's XP, level, streaks, and completion stats."""
    result = await db.execute(
        select(UserStats).where(UserStats.user_id == current_user.id)
    )
    stats = result.scalar_one_or_none()

    if not stats:
        stats = UserStats(
            user_id=current_user.id,
            total_xp=0,
            current_streak=0,
            longest_streak=0,
            lessons_completed=0,
            courses_completed=0,
            labs_completed=0,
        )
        db.add(stats)
        await db.commit()
        await db.refresh(stats)

    return {
        "total_xp": stats.total_xp,
        "current_streak": stats.current_streak,
        "longest_streak": stats.longest_streak,
        "lessons_completed": stats.lessons_completed,
        "courses_completed": stats.courses_completed,
        "labs_completed": stats.labs_completed,
        "level": calculate_level(stats.total_xp),
    }


@router.get("/my-achievements")
async def get_my_achievements(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get current user's earned achievements."""
    result = await db.execute(
        select(UserAchievement)
        .options(selectinload(UserAchievement.achievement))
        .where(UserAchievement.user_id == current_user.id)
        .order_by(UserAchievement.earned_at.desc())
    )
    user_achievements = result.scalars().all()

    return [
        {
            "id": ua.achievement.id,
            "slug": ua.achievement.slug,
            "name": ua.achievement.name,
            "description": ua.achievement.description,
            "icon": ua.achievement.icon,
            "xp_value": ua.achievement.xp_value,
            "earned_at": ua.earned_at,
        }
        for ua in user_achievements
    ]


@router.get("/achievements")
async def get_all_achievements(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get all available achievements (non-secret ones)."""
    result = await db.execute(
        select(Achievement)
        .where(Achievement.is_secret == False)
        .order_by(Achievement.category, Achievement.name)
    )
    achievements = result.scalars().all()

    return [
        {
            "id": a.id,
            "slug": a.slug,
            "name": a.name,
            "description": a.description,
            "icon": a.icon,
            "xp_value": a.xp_value,
            "category": a.category,
        }
        for a in achievements
    ]


@router.get("/weekly-activity", response_model=WeeklyActivityResponse)
async def get_weekly_activity(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Get weekly learning activity for the current user.

    Returns lessons completed and minutes spent for each day of the last 7 days.
    """
    # Calculate date range for last 7 days (including today)
    now = datetime.now(timezone.utc)
    today = now.date()
    week_start = today - timedelta(days=6)  # 6 days ago + today = 7 days

    # Day names for display
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Initialize activity data for each day
    activity_by_date = {}
    for i in range(7):
        date = week_start + timedelta(days=i)
        activity_by_date[date] = {"lessons": 0, "minutes": 0}

    # Query completed lessons in the last 7 days with their estimated minutes
    result = await db.execute(
        select(LessonProgress, Lesson)
        .join(Lesson, LessonProgress.lesson_id == Lesson.id)
        .where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.status == "completed",
            LessonProgress.completed_at.isnot(None),
            func.date(LessonProgress.completed_at) >= week_start,
            func.date(LessonProgress.completed_at) <= today,
        )
    )

    completed_lessons = result.all()

    # Aggregate by date
    for progress, lesson in completed_lessons:
        if progress.completed_at:
            completed_date = progress.completed_at.date()
            if completed_date in activity_by_date:
                activity_by_date[completed_date]["lessons"] += 1
                activity_by_date[completed_date]["minutes"] += lesson.estimated_minutes or 0

    # Build response with day names
    activity = []
    total_lessons = 0
    total_minutes = 0

    for i in range(7):
        date = week_start + timedelta(days=i)
        day_name = day_names[date.weekday()]
        data = activity_by_date[date]
        activity.append(WeeklyActivityDay(
            day=day_name,
            lessons=data["lessons"],
            minutes=data["minutes"]
        ))
        total_lessons += data["lessons"]
        total_minutes += data["minutes"]

    return WeeklyActivityResponse(
        activity=activity,
        total_lessons=total_lessons,
        total_minutes=total_minutes
    )


@router.get("/analytics", response_model=ComprehensiveAnalyticsResponse)
async def get_comprehensive_analytics(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive learning analytics for the current user.

    Includes:
    - Course statistics (enrolled, completed, in-progress)
    - Lesson completion stats
    - Time invested
    - Streak history (last 30 days)
    - Recent activity feed (last 10 completions)
    """
    # Get user's gamification stats
    stats_result = await db.execute(
        select(UserStats).where(UserStats.user_id == current_user.id)
    )
    user_stats = stats_result.scalar_one_or_none()

    # Get user's enrollments with course data
    enrollments_result = await db.execute(
        select(Enrollment, Course)
        .join(Course, Enrollment.course_id == Course.id)
        .where(Enrollment.user_id == current_user.id)
    )
    enrollments = enrollments_result.all()

    # Calculate course stats
    total_courses_enrolled = len(enrollments)
    courses_completed = sum(1 for e, c in enrollments if e.completed_at is not None)
    courses_in_progress = total_courses_enrolled - courses_completed

    # Calculate difficulty distribution
    difficulty_dist = {"beginner": 0, "intermediate": 0, "advanced": 0}
    for enrollment, course in enrollments:
        diff = course.difficulty or "beginner"
        if diff in difficulty_dist:
            difficulty_dist[diff] += 1

    # Get all lessons from enrolled courses
    course_ids = [e.course_id for e, c in enrollments]
    total_lessons = 0
    total_content_minutes = 0

    if course_ids:
        # Get total lesson count and minutes for enrolled courses
        lessons_result = await db.execute(
            select(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .where(Module.course_id.in_(course_ids))
        )
        all_lessons = lessons_result.scalars().all()
        total_lessons = len(all_lessons)
        total_content_minutes = sum(l.estimated_minutes or 0 for l in all_lessons)

    # Get completed lessons count and minutes
    completed_result = await db.execute(
        select(LessonProgress, Lesson)
        .join(Lesson, LessonProgress.lesson_id == Lesson.id)
        .where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.status == "completed"
        )
    )
    completed_lessons_data = completed_result.all()
    lessons_completed = len(completed_lessons_data)
    total_minutes_invested = sum(l.estimated_minutes or 0 for p, l in completed_lessons_data)

    # Calculate completion rate
    lesson_completion_rate = (lessons_completed / total_lessons * 100) if total_lessons > 0 else 0.0

    # Get streak history (last 30 days)
    now = datetime.now(timezone.utc)
    today = now.date()
    thirty_days_ago = today - timedelta(days=29)

    # Query all activity dates in the last 30 days
    activity_dates_result = await db.execute(
        select(func.date(LessonProgress.completed_at).label("activity_date"))
        .where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.status == "completed",
            LessonProgress.completed_at.isnot(None),
            func.date(LessonProgress.completed_at) >= thirty_days_ago,
            func.date(LessonProgress.completed_at) <= today,
        )
        .group_by(func.date(LessonProgress.completed_at))
    )
    activity_dates = {row.activity_date for row in activity_dates_result}

    # Build streak history
    streak_history = []
    for i in range(30):
        date = thirty_days_ago + timedelta(days=i)
        streak_history.append(StreakDay(
            date=date.isoformat(),
            had_activity=date in activity_dates
        ))

    # Get recent activity (last 10 lesson completions)
    recent_result = await db.execute(
        select(LessonProgress, Lesson, Module, Course)
        .join(Lesson, LessonProgress.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.status == "completed",
            LessonProgress.completed_at.isnot(None)
        )
        .order_by(LessonProgress.completed_at.desc())
        .limit(10)
    )
    recent_completions = recent_result.all()

    recent_activity = [
        RecentActivityItem(
            lesson_id=lesson.id,
            lesson_title=lesson.title,
            course_id=course.id,
            course_title=course.title,
            completed_at=progress.completed_at,
            xp_earned=lesson.xp_reward or 0,
            estimated_minutes=lesson.estimated_minutes
        )
        for progress, lesson, module, course in recent_completions
    ]

    return ComprehensiveAnalyticsResponse(
        total_courses_enrolled=total_courses_enrolled,
        courses_completed=courses_completed,
        courses_in_progress=courses_in_progress,
        total_lessons=total_lessons,
        lessons_completed=lessons_completed,
        lesson_completion_rate=round(lesson_completion_rate, 1),
        total_minutes_invested=total_minutes_invested,
        total_content_minutes=total_content_minutes,
        total_xp=user_stats.total_xp if user_stats else 0,
        level=calculate_level(user_stats.total_xp) if user_stats else 1,
        current_streak=user_stats.current_streak if user_stats else 0,
        longest_streak=user_stats.longest_streak if user_stats else 0,
        difficulty_distribution=DifficultyDistribution(**difficulty_dist),
        streak_history=streak_history,
        recent_activity=recent_activity
    )


# ---------------------------------------------------------------------------
# AI literacy labs - badge awards
# ---------------------------------------------------------------------------

ALLOWED_LAB_SLUGS: set[str] = {
    "real-or-fake",
    "ai-said-what",
    "fix-this-prompt",
    "who-wrote-this",
}


class LabCompleteRequest(BaseModel):
    score: int = Field(..., ge=0)
    total: int = Field(..., ge=0)


router_labs = APIRouter(
    prefix="/learning/labs",
    tags=["learning-gamification"],
    dependencies=[Depends(require_gamification_enabled)],
)


@router_labs.post("/{slug}/complete")
async def complete_ai_literacy_lab(
    slug: str,
    body: LabCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if slug not in ALLOWED_LAB_SLUGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown AI literacy lab",
        )

    achievement_slug = f"ai_lab_{slug.replace('-', '_')}"

    ach_result = await db.execute(
        select(Achievement).where(Achievement.slug == achievement_slug)
    )
    achievement = ach_result.scalar_one_or_none()
    if achievement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Badge not seeded for this lab",
        )

    existing_result = await db.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == current_user.id,
            UserAchievement.achievement_id == achievement.id,
        )
    )
    existing = existing_result.scalar_one_or_none()

    is_first_completion = existing is None

    if is_first_completion:
        db.add(
            UserAchievement(
                user_id=current_user.id,
                achievement_id=achievement.id,
            )
        )

        stats_result = await db.execute(
            select(UserStats).where(UserStats.user_id == current_user.id)
        )
        stats = stats_result.scalar_one_or_none()
        if stats is None:
            stats = UserStats(
                user_id=current_user.id,
                total_xp=0,
                current_streak=0,
                longest_streak=0,
                lessons_completed=0,
                courses_completed=0,
                labs_completed=0,
            )
            db.add(stats)
            await db.flush()

        stats.total_xp = (stats.total_xp or 0) + (achievement.xp_value or 0)
        stats.labs_completed = (stats.labs_completed or 0) + 1

        await db.commit()

    return {
        "awarded": is_first_completion,
        "badge": {
            "slug": achievement.slug,
            "name": achievement.name,
            "xp_value": achievement.xp_value,
        },
        "is_first_completion": is_first_completion,
    }
