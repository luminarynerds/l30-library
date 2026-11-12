# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Read to Reduce API endpoints with gamification.
Allows children to log reading minutes to reduce their overdue "fines",
earn badges, track streaks, and export reports for teachers.
"""

import json
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, distinct, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.cache import get_cached_with_lock, make_cache_key
from ...core.cache_strategies import CacheTTL
from ...core.config import get_settings
from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.gamification import Achievement, UserAchievement
from ...models.reading import (ReadingExport, ReadingLog, ReadingLogStatus,
                               ReadingStats)
from ...models.user import User
from ...schemas.reading import (ReadingBalanceResponse, ReadingLogCreate,
                                ReadingLogResponse, ReadingLogReview)
from ...services.organization_features_service import OrganizationFeaturesService
from .auth import get_current_user
from .dependencies import check_staff_access


async def require_gamification_enabled(db: AsyncSession = Depends(get_db)) -> None:
    enabled = await OrganizationFeaturesService.is_feature_enabled(db, "gamification_enabled")
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gamification feature is not enabled",
        )


router = APIRouter(
    prefix="/reading",
    tags=["reading"],
    dependencies=[Depends(require_gamification_enabled)],
)


# Reading badge definitions
READING_BADGES = [
    {
        "slug": "reading-first",
        "name": "First Steps",
        "description": "Log your first reading session",
        "icon": "BookOpen",
        "xp_value": 10,
        "category": "reading",
    },
    {
        "slug": "reading-100",
        "name": "Bookworm",
        "description": "Read 100 total minutes",
        "icon": "BookMarked",
        "xp_value": 25,
        "category": "reading",
    },
    {
        "slug": "reading-500",
        "name": "Dragon Slayer",
        "description": "Read 500 total minutes",
        "icon": "Sword",
        "xp_value": 50,
        "category": "reading",
    },
    {
        "slug": "reading-1000",
        "name": "Reading Champion",
        "description": "Read 1000 total minutes",
        "icon": "Trophy",
        "xp_value": 100,
        "category": "reading",
    },
    {
        "slug": "reading-streak-3",
        "name": "On Fire",
        "description": "3-day reading streak",
        "icon": "Flame",
        "xp_value": 15,
        "category": "streak",
    },
    {
        "slug": "reading-streak-7",
        "name": "Unstoppable",
        "description": "7-day reading streak",
        "icon": "Zap",
        "xp_value": 30,
        "category": "streak",
    },
    {
        "slug": "reading-streak-30",
        "name": "Legendary Reader",
        "description": "30-day reading streak",
        "icon": "Crown",
        "xp_value": 100,
        "category": "streak",
    },
    {
        "slug": "reading-books-5",
        "name": "Genre Explorer",
        "description": "Read 5 different books",
        "icon": "Compass",
        "xp_value": 20,
        "category": "reading",
    },
    {
        "slug": "reading-notes-10",
        "name": "Story Teller",
        "description": "Write 10 reading notes",
        "icon": "PenTool",
        "xp_value": 20,
        "category": "reading",
    },
    {
        "slug": "reading-balance-clear",
        "name": "Debt Free",
        "description": "Clear your reading balance",
        "icon": "CheckCircle",
        "xp_value": 50,
        "category": "reading",
    },
]


async def ensure_badges_exist(db: AsyncSession):
    slug_list = [badge["slug"] for badge in READING_BADGES]
    result = await db.execute(
        select(Achievement.slug).where(Achievement.slug.in_(slug_list))
    )
    existing_slugs = set(row[0] for row in result.all())

    for badge in READING_BADGES:
        if badge["slug"] not in existing_slugs:
            achievement = Achievement(**badge)
            db.add(achievement)
    await db.commit()


async def get_or_create_stats(db: AsyncSession, user_id: int) -> ReadingStats:
    result = await db.execute(
        select(ReadingStats).where(ReadingStats.user_id == user_id)
    )
    stats = result.scalar_one_or_none()
    if not stats:
        stats = ReadingStats(user_id=user_id)
        db.add(stats)
        await db.commit()
        await db.refresh(stats)
    return stats


async def update_streak(db: AsyncSession, user_id: int) -> ReadingStats:
    stats = await get_or_create_stats(db, user_id)
    today = date.today()

    if stats.last_log_date == today:
        # Already logged today
        pass
    elif stats.last_log_date == today - timedelta(days=1):
        # Consecutive day - extend streak
        stats.current_streak += 1
        if stats.current_streak > stats.longest_streak:
            stats.longest_streak = stats.current_streak
    else:
        # Streak broken - reset to 1
        stats.current_streak = 1

    stats.last_log_date = today
    stats.total_submissions += 1
    await db.commit()
    await db.refresh(stats)
    return stats


async def check_and_award_badges(
    db: AsyncSession, user_id: int, stats: ReadingStats, user: User
) -> List[dict]:
    earned = []

    # Get user's existing achievements
    existing_result = await db.execute(
        select(UserAchievement.achievement_id).where(UserAchievement.user_id == user_id)
    )
    existing_ids = set(row[0] for row in existing_result.all())

    # Get all reading badges
    badges_result = await db.execute(
        select(Achievement).where(Achievement.category.in_(["reading", "streak"]))
    )
    badges = {b.slug: b for b in badges_result.scalars().all()}

    def check_badge(slug: str) -> bool:
        badge = badges.get(slug)
        return badge and badge.id not in existing_ids

    async def award(slug: str):
        badge = badges.get(slug)
        if badge:
            try:
                async with db.begin_nested():
                    ua = UserAchievement(user_id=user_id, achievement_id=badge.id)
                    db.add(ua)
                    await db.flush()  # Trigger constraint check within savepoint
                stats.xp += badge.xp_value
                earned.append(
                    {
                        "slug": slug,
                        "name": badge.name,
                        "icon": badge.icon,
                        "xp": badge.xp_value,
                    }
                )
            except IntegrityError:
                # Badge already awarded by concurrent request - savepoint rolled back
                pass

    # Check milestone badges
    if check_badge("reading-first") and stats.total_submissions >= 1:
        await award("reading-first")

    if check_badge("reading-100") and stats.total_approved_minutes >= 100:
        await award("reading-100")

    if check_badge("reading-500") and stats.total_approved_minutes >= 500:
        await award("reading-500")

    if check_badge("reading-1000") and stats.total_approved_minutes >= 1000:
        await award("reading-1000")

    # Check streak badges
    if check_badge("reading-streak-3") and stats.current_streak >= 3:
        await award("reading-streak-3")

    if check_badge("reading-streak-7") and stats.current_streak >= 7:
        await award("reading-streak-7")

    if check_badge("reading-streak-30") and stats.current_streak >= 30:
        await award("reading-streak-30")

    # Check unique books
    if check_badge("reading-books-5") and stats.unique_books >= 5:
        await award("reading-books-5")

    # Check notes written
    if check_badge("reading-notes-10") and stats.notes_written >= 10:
        await award("reading-notes-10")

    # Check balance cleared
    if check_badge("reading-balance-clear") and user.reading_minutes_balance == 0:
        await award("reading-balance-clear")

    if earned:
        await db.commit()

    return earned


# ============ Patron Endpoints ============


@router.get("/balance", response_model=ReadingBalanceResponse)
async def get_reading_balance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's reading minutes balance."""
    pending_result = await db.execute(
        select(func.coalesce(func.sum(ReadingLog.minutes), 0)).where(
            ReadingLog.user_id == current_user.id,
            ReadingLog.status == ReadingLogStatus.pending,
        )
    )
    pending_minutes = pending_result.scalar() or 0

    pending_count_result = await db.execute(
        select(func.count(ReadingLog.id)).where(
            ReadingLog.user_id == current_user.id,
            ReadingLog.status == ReadingLogStatus.pending,
        )
    )
    pending_count = pending_count_result.scalar() or 0

    return ReadingBalanceResponse(
        minutes_owed=current_user.reading_minutes_owed,
        minutes_logged=current_user.reading_minutes_logged,
        minutes_pending=pending_minutes,
        balance=current_user.reading_minutes_balance,
        pending_logs=pending_count,
    )


@router.post("/log", status_code=status.HTTP_201_CREATED)
async def submit_reading_log(
    log: ReadingLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a new reading log entry. Updates streak immediately."""
    # Normalize both datetimes to UTC for comparison
    reading_dt = log.reading_date
    if reading_dt.tzinfo is None:
        reading_dt = reading_dt.replace(tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)
    if reading_dt > now_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Reading date cannot be in the future"
        )

    if current_user.reading_minutes_owed <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You don't have any reading minutes owed"
        )

    reading_log = ReadingLog(
        user_id=current_user.id,
        minutes=log.minutes,
        book_title=log.book_title,
        book_author=log.book_author,
        notes=log.notes,
        reading_date=log.reading_date,
        status=ReadingLogStatus.pending,
    )

    db.add(reading_log)

    # Update streak immediately on submission
    stats = await update_streak(db, current_user.id)

    # Track unique books and notes
    if log.book_title:
        existing_books = await db.execute(
            select(func.count(distinct(ReadingLog.book_title))).where(
                ReadingLog.user_id == current_user.id, ReadingLog.book_title.isnot(None)
            )
        )
        stats.unique_books = existing_books.scalar() or 0

    if log.notes:
        stats.notes_written += 1

    await db.commit()
    await db.refresh(reading_log)

    # Check for streak badges
    earned = await check_and_award_badges(db, current_user.id, stats, current_user)

    return {
        "log": reading_log,
        "streak": stats.current_streak,
        "badges_earned": earned,
    }


@router.get("/logs", response_model=List[ReadingLogResponse])
async def get_my_reading_logs(
    status: ReadingLogStatus | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's reading logs."""
    query = select(ReadingLog).where(ReadingLog.user_id == current_user.id)

    if status:
        query = query.where(ReadingLog.status == status)

    query = query.order_by(ReadingLog.created_at.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/my-stats")
async def get_my_reading_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's gamification stats."""
    await ensure_badges_exist(db)
    stats = await get_or_create_stats(db, current_user.id)

    return {
        "streak": stats.current_streak,
        "longest_streak": stats.longest_streak,
        "xp": stats.xp,
        "level": stats.level,
        "xp_to_next_level": stats.xp_to_next_level,
        "total_approved_minutes": stats.total_approved_minutes,
        "total_submissions": stats.total_submissions,
        "unique_books": stats.unique_books,
        "notes_written": stats.notes_written,
        "last_log_date": (
            stats.last_log_date.isoformat() if stats.last_log_date else None
        ),
    }


@router.get("/achievements")
async def get_achievements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all reading badges with earned status."""
    await ensure_badges_exist(db)

    # Get all reading badges
    badges_result = await db.execute(
        select(Achievement).where(Achievement.category.in_(["reading", "streak"]))
    )
    badges = badges_result.scalars().all()

    # Get user's earned badges
    earned_result = await db.execute(
        select(UserAchievement).where(UserAchievement.user_id == current_user.id)
    )
    earned = {ua.achievement_id: ua.earned_at for ua in earned_result.scalars().all()}

    return [
        {
            "id": b.id,
            "slug": b.slug,
            "name": b.name,
            "description": b.description,
            "icon": b.icon,
            "xp": b.xp_value,
            "earned": b.id in earned,
            "earned_at": earned.get(b.id).isoformat() if b.id in earned else None,
        }
        for b in badges
    ]


@router.get("/community")
async def get_community_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get collective reading stats (non-competitive)."""
    # Total minutes this month
    first_of_month = date.today().replace(day=1)
    monthly_result = await db.execute(
        select(func.coalesce(func.sum(ReadingLog.minutes), 0)).where(
            ReadingLog.status == ReadingLogStatus.approved,
            ReadingLog.reviewed_at
            >= datetime.combine(first_of_month, datetime.min.time()),
        )
    )
    monthly_minutes = monthly_result.scalar() or 0

    # Total all time
    total_result = await db.execute(
        select(func.coalesce(func.sum(ReadingLog.minutes), 0)).where(
            ReadingLog.status == ReadingLogStatus.approved
        )
    )
    total_minutes = total_result.scalar() or 0

    # Active readers this month
    readers_result = await db.execute(
        select(func.count(distinct(ReadingLog.user_id))).where(
            ReadingLog.status == ReadingLogStatus.approved,
            ReadingLog.reviewed_at
            >= datetime.combine(first_of_month, datetime.min.time()),
        )
    )
    active_readers = readers_result.scalar() or 0

    return {
        "monthly_minutes": monthly_minutes,
        "total_minutes": total_minutes,
        "active_readers_this_month": active_readers,
        "message": f"Together, we've read {total_minutes:,} minutes!",
    }


@router.get("/leaderboard")
async def get_reading_leaderboard(
    period: str = "month",
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get reading leaderboard. Alias for /reading-minutes/leaderboard."""
    cache_key = make_cache_key("l30:reading:leaderboard", period=period, limit=limit)

    async def _fetch():
        # Get top readers by approved minutes
        result = await db.execute(
            select(User)
            .where(User.reading_minutes_logged > 0)
            .order_by(User.reading_minutes_logged.desc())
            .limit(limit)
        )
        users = result.scalars().all()

        return [
            {
                "rank": i + 1,
                "display_name": f"{u.first_name[:1]}***" if u.first_name else f"Reader #{u.id % 10000:04d}",
                "minutes_read": u.reading_minutes_logged,
                "books_completed": 0,
                "achievements_count": 0,
            }
            for i, u in enumerate(users)
        ]

    return await get_cached_with_lock(cache_key, _fetch, ttl_seconds=CacheTTL.WARM)


# ============ Export Endpoints ============


class ExportRequest(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    teacher_name: Optional[str] = Field(None, max_length=200)
    school_name: Optional[str] = Field(None, max_length=200)


@router.post("/export", status_code=status.HTTP_201_CREATED)
async def create_reading_export(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a reading report with verification code."""
    # Get approved logs in date range
    query = select(ReadingLog).where(
        ReadingLog.user_id == current_user.id,
        ReadingLog.status == ReadingLogStatus.approved,
    )

    if request.date_from:
        query = query.where(
            ReadingLog.reading_date
            >= datetime.combine(request.date_from, datetime.min.time())
        )
    if request.date_to:
        query = query.where(
            ReadingLog.reading_date
            <= datetime.combine(request.date_to, datetime.max.time())
        )

    result = await db.execute(query.order_by(ReadingLog.reading_date))
    logs = result.scalars().all()

    total_minutes = sum(log.minutes for log in logs)
    books = list(set(log.book_title for log in logs if log.book_title))

    # Generate verification code
    verification_code = secrets.token_urlsafe(12)[:16].upper()

    # Create export record
    export = ReadingExport(
        user_id=current_user.id,
        verification_code=verification_code,
        date_from=request.date_from,
        date_to=request.date_to,
        teacher_name=request.teacher_name,
        school_name=request.school_name,
        total_minutes=total_minutes,
        total_sessions=len(logs),
        books_read=json.dumps(books),
        expires_at=datetime.now(timezone.utc) + timedelta(days=365),  # Valid for 1 year
    )
    db.add(export)
    await db.commit()
    await db.refresh(export)

    # Get badges
    badges = await get_achievements(db, current_user)
    earned_badges = [b for b in badges if b["earned"]]

    stats = await get_or_create_stats(db, current_user.id)

    return {
        "verification_code": verification_code,
        "verification_url": f"/reading/verify/{verification_code}",
        "patron_name": current_user.full_name,
        "date_from": request.date_from,
        "date_to": request.date_to,
        "teacher_name": request.teacher_name,
        "school_name": request.school_name,
        "total_minutes": total_minutes,
        "total_sessions": len(logs),
        "books_read": books,
        "current_streak": stats.current_streak,
        "badges_earned": earned_badges,
        "logs": [
            {
                "date": log.reading_date.strftime("%Y-%m-%d"),
                "minutes": log.minutes,
                "book": log.book_title,
                "author": log.book_author,
            }
            for log in logs
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/verify/{code}")
async def verify_reading_report(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint for teachers to verify a reading report."""
    result = await db.execute(
        select(ReadingExport).where(ReadingExport.verification_code == code.upper())
    )
    export = result.scalar_one_or_none()

    if not export:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification code not found")

    if export.expires_at and export.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This report has expired")

    # Get patron name
    user_result = await db.execute(select(User).where(User.id == export.user_id))
    user = user_result.scalar_one_or_none()

    return {
        "valid": True,
        "patron_name": user.full_name if user else "Unknown",
        "date_from": export.date_from,
        "date_to": export.date_to,
        "total_minutes": export.total_minutes,
        "total_sessions": export.total_sessions,
        "books_read": json.loads(export.books_read) if export.books_read else [],
        "teacher_name": export.teacher_name,
        "school_name": export.school_name,
        "generated_at": export.created_at.isoformat(),
        "message": f"This reading report was verified by {get_settings().library_name}.",
    }


# ============ Staff Endpoints ============


@router.get("/pending", response_model=List[ReadingLogResponse])
async def get_pending_logs(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all pending reading logs for staff review."""
    check_staff_access(current_user)

    query = (
        select(ReadingLog)
        .options(selectinload(ReadingLog.user))
        .where(ReadingLog.status == ReadingLogStatus.pending)
        .order_by(ReadingLog.created_at.asc())
        .limit(limit)
    )

    result = await db.execute(query)
    logs = result.scalars().all()

    responses = []
    for log in logs:
        response = ReadingLogResponse.model_validate(log)
        if log.user:
            response.patron_name = log.user.full_name
        responses.append(response)

    return responses


@router.post("/{log_id}/review")
async def review_reading_log(
    log_id: int,
    review: ReadingLogReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve or reject a reading log. Awards XP and checks badges on approval."""
    check_staff_access(current_user)

    log = await get_or_404(db, ReadingLog, log_id, "Reading log not found")

    if log.status != ReadingLogStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Log has already been reviewed")

    log.reviewed_by_id = current_user.id
    log.reviewed_at = datetime.now(timezone.utc)

    earned_badges = []

    if review.approved:
        log.status = ReadingLogStatus.approved

        # Get patron
        user_result = await db.execute(select(User).where(User.id == log.user_id))
        user = user_result.scalar_one_or_none()

        if user:
            user.reading_minutes_logged += log.minutes

            # Update stats
            stats = await get_or_create_stats(db, user.id)
            stats.total_approved_minutes += log.minutes
            stats.xp += log.minutes  # 1 XP per minute

            await db.commit()

            # Check for badges
            earned_badges = await check_and_award_badges(db, user.id, stats, user)
    else:
        log.status = ReadingLogStatus.rejected
        log.rejection_reason = review.rejection_reason

    await db.commit()
    await db.refresh(log)

    return {
        "log": log,
        "badges_awarded": earned_badges,
    }


@router.get("/stats")
async def get_program_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Read to Reduce program statistics for staff."""
    check_staff_access(current_user)

    pending_result = await db.execute(
        select(func.count(ReadingLog.id)).where(
            ReadingLog.status == ReadingLogStatus.pending
        )
    )
    pending_count = pending_result.scalar() or 0

    first_of_month = date.today().replace(day=1)
    approved_result = await db.execute(
        select(func.coalesce(func.sum(ReadingLog.minutes), 0)).where(
            ReadingLog.status == ReadingLogStatus.approved,
            ReadingLog.reviewed_at
            >= datetime.combine(first_of_month, datetime.min.time()),
        )
    )
    approved_minutes = approved_result.scalar() or 0

    participants_result = await db.execute(
        select(func.count(User.id)).where(User.reading_minutes_owed > 0)
    )
    participants = participants_result.scalar() or 0

    return {
        "pending_reviews": pending_count,
        "approved_minutes_this_month": approved_minutes,
        "active_participants": participants,
    }


