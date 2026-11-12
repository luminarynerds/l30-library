# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job

from ..services.ebook_card_tasks import (
    reset_monthly_borrows,
    expire_and_notify_cards,
    send_monthly_digest,
)
from ..services.ban_tracker_digest_service import run_subscription_digest_job
from ..services.home_visit_safety_tasks import scan_and_notify_overdue_visits
from ..tasks.blog_publisher import publish_scheduled_blog_posts
from ..core.database import AsyncSessionLocal
from ..middleware.rate_limit_middleware import _in_memory_fallback, WINDOW_SECONDS

logger = get_logger(__name__)

scheduler: AsyncIOScheduler = None


async def _run_with_db(func):
    async with AsyncSessionLocal() as db:
        await func(db)


async def _reset_monthly_borrows():
    await _run_with_db(reset_monthly_borrows)


async def _expire_and_notify_cards():
    await _run_with_db(expire_and_notify_cards)


async def _send_monthly_digest():
    await _run_with_db(send_monthly_digest)


async def _send_ban_tracker_daily_digest():
    async with AsyncSessionLocal() as db:
        await run_subscription_digest_job(db, "daily")


async def _send_ban_tracker_weekly_digest():
    async with AsyncSessionLocal() as db:
        await run_subscription_digest_job(db, "weekly")


async def _scan_overdue_home_visits():
    async with AsyncSessionLocal() as db:
        await scan_and_notify_overdue_visits(db)


async def _cleanup_rate_limiter_memory():
    try:
        evicted = _in_memory_fallback.cleanup_stale(WINDOW_SECONDS)
        stats = _in_memory_fallback.get_stats()
        if evicted > 0:
            logger.info(
                "Rate limiter memory cleanup completed",
                extra={
                    "evicted_entries": evicted,
                    "remaining_entries": stats["tracked_ips"],
                    "capacity_usage_percent": stats["occupancy_percent"],
                },
            )
    except Exception as e:
        logger.error("Rate limiter cleanup failed: %s", e, exc_info=True)


async def _pen_america_weekly_sync() -> None:
    """Weekly cron wrapper for the PEN America banned-books sync.

    Runs PenAmericaSyncService.sync() in its own DB session, then flushes
    the ban_tracker and book_challenges public stats caches so fresh totals
    show up within seconds of a sync completing. A crash here must not take
    down the scheduler, so exceptions are logged and swallowed rather than
    propagated.
    """
    from ..core.cache import invalidate_cache
    from ..services.pen_america_sync_service import PenAmericaSyncService

    try:
        async with AsyncSessionLocal() as db:
            await PenAmericaSyncService.sync(db)
        await invalidate_cache("ban_tracker:stats*")
        await invalidate_cache("book_challenges:stats*")
    except Exception:
        logger.exception("PEN America weekly sync failed")


def init_scheduler() -> AsyncIOScheduler:
    global scheduler

    scheduler = AsyncIOScheduler()

    # Reset monthly borrow counters at 00:00 UTC on the 1st of each month
    scheduler.add_job(
        _reset_monthly_borrows,
        CronTrigger(day=1, hour=0, minute=0),
        id="reset_monthly_borrows",
        name="Reset Monthly Borrow Counters",
        replace_existing=True,
    )

    # Check for expired cards and send reminders daily at 08:00 UTC
    scheduler.add_job(
        _expire_and_notify_cards,
        CronTrigger(hour=8, minute=0),
        id="expire_and_notify_cards",
        name="Expire Cards and Send Reminders",
        replace_existing=True,
    )

    # Send monthly digest on the 1st at 10:00 UTC
    scheduler.add_job(
        _send_monthly_digest,
        CronTrigger(day=1, hour=10, minute=0),
        id="send_monthly_digest",
        name="Send Monthly Reading Digest",
        replace_existing=True,
    )

    # PEN America banned-books sync — Sundays at 03:00 UTC.
    # Manual trigger remains at POST /api/v1/ban-tracker/sync.
    scheduler.add_job(
        _pen_america_weekly_sync,
        CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="pen_america_weekly_sync",
        name="PEN America Weekly Sync",
        replace_existing=True,
        misfire_grace_time=3600,  # if missed (deploy/restart), run within 1h
    )

    # Clean up stale rate limiter entries every 5 minutes
    # (avoids memory growth during Redis outages)
    scheduler.add_job(
        _cleanup_rate_limiter_memory,
        CronTrigger(minute="*/5"),  # Every 5 minutes
        id="cleanup_rate_limiter_memory",
        name="Clean Up Rate Limiter Memory",
        replace_existing=True,
        misfire_grace_time=30,  # Allow 30 sec grace if missed
    )

    # Ban-tracker daily digest at 08:00 local time
    scheduler.add_job(
        _send_ban_tracker_daily_digest,
        CronTrigger(hour=8, minute=0),
        id="ban_tracker_daily_digest",
        name="Ban Tracker Daily Digest",
        replace_existing=True,
    )

    # Ban-tracker weekly digest at 08:00 local time on Mondays
    scheduler.add_job(
        _send_ban_tracker_weekly_digest,
        CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="ban_tracker_weekly_digest",
        name="Ban Tracker Weekly Digest",
        replace_existing=True,
    )

    # Lone-worker safety scan every 5 minutes. Cheap early-return when
    # the feature flag is off so the job is safe to leave registered.
    scheduler.add_job(
        _scan_overdue_home_visits,
        CronTrigger(minute="*/5"),
        id="scan_overdue_home_visits",
        name="Scan Overdue Home Visit Safety Check-outs",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Promote scheduled blog posts whose time has arrived (every minute).
    # Replaces the previous inline auto-publish that ran on every public
    # list/feed read — that pattern (a) wrote on the anonymous read path and
    # (b) left scheduled posts stuck if no one viewed the blog over a quiet
    # weekend.
    scheduler.add_job(
        publish_scheduled_blog_posts,
        CronTrigger(minute="*"),
        id="publish_scheduled_blog_posts",
        name="Publish Scheduled Blog Posts",
        replace_existing=True,
        misfire_grace_time=120,
    )

    logger.info("Scheduler initialized with 9 jobs")
    return scheduler


def get_scheduler() -> AsyncIOScheduler:
    global scheduler
    if scheduler is None:
        scheduler = init_scheduler()
    return scheduler


@asynccontextmanager
async def scheduler_context():
    global scheduler

    try:
        scheduler = init_scheduler()
        scheduler.start()
        logger.info("Scheduler started")
        yield scheduler
    except Exception as e:
        logger.error("Scheduler error: %s", e)
        raise
    finally:
        if scheduler and scheduler.running:
            scheduler.shutdown()
            logger.info("Scheduler shut down")


async def get_job(job_id: str) -> Job | None:
    scheduler = get_scheduler()
    return scheduler.get_job(job_id)


async def list_jobs() -> list[Job]:
    scheduler = get_scheduler()
    return scheduler.get_jobs()
