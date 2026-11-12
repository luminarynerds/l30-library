# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select

from ...core.database import AsyncSessionLocal
from ...core.logging import get_logger
from ...models.job_failure import JobExecutionLog

logger = get_logger(__name__)

# Daily jobs that need catch-up on startup
# Job ID -> (job function, grace period in hours)
DAILY_JOBS_TO_CATCHUP = {
    "daily_overdue_notifications": None,  # Function ref set after imports
    "daily_data_retention": None,
    "child_to_adult_transitions": None,
    "daily_operational_alerts": None,
    "database_subscription_status_update": None,
    "certificate_expiration_check": None,
    "daily_fine_calculation": None,
}

CATCHUP_GRACE_HOURS = 26  # Alert if not run in 26 hours (24h + 2h buffer)


async def check_and_catchup_daily_jobs() -> dict:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=CATCHUP_GRACE_HOURS)

    triggered_jobs = []
    skipped_jobs = []
    job_details = {}

    async with AsyncSessionLocal() as db:
        for job_id in DAILY_JOBS_TO_CATCHUP.keys():
            # Find the most recent successful execution
            stmt = (
                select(func.max(JobExecutionLog.started_at))
                .where(
                    and_(
                        JobExecutionLog.job_id == job_id,
                        JobExecutionLog.success == True,  # noqa: E712
                    )
                )
            )

            result = await db.execute(stmt)
            last_run = result.scalar_one_or_none()

            if last_run is None:
                # Job has never run successfully
                logger.warning(
                    f"Daily job '{job_id}' has never run successfully. "
                    "Triggering immediately on startup.",
                    extra={"job_id": job_id},
                )
                triggered_jobs.append(job_id)
                job_details[job_id] = {
                    "last_run": None,
                    "hours_since_last_run": None,
                    "action": "triggered (never run)",
                }

            elif last_run < cutoff:
                # Job hasn't run within the grace period
                hours_since = (now - last_run).total_seconds() / 3600
                logger.warning(
                    f"Daily job '{job_id}' missed its last scheduled run. "
                    f"Last run was {hours_since:.1f} hours ago (threshold: {CATCHUP_GRACE_HOURS}h). "
                    "Triggering immediately on startup.",
                    extra={
                        "job_id": job_id,
                        "last_run": last_run.isoformat(),
                        "hours_since": hours_since,
                    },
                )
                triggered_jobs.append(job_id)
                job_details[job_id] = {
                    "last_run": last_run.isoformat(),
                    "hours_since_last_run": round(hours_since, 2),
                    "action": "triggered (overdue)",
                }

            else:
                # Job ran recently, skip it
                hours_since = (now - last_run).total_seconds() / 3600
                logger.info(
                    f"Daily job '{job_id}' ran recently. Skipping catch-up. "
                    f"Last run: {hours_since:.1f} hours ago",
                    extra={
                        "job_id": job_id,
                        "last_run": last_run.isoformat(),
                        "hours_since": round(hours_since, 2),
                    },
                )
                skipped_jobs.append(job_id)
                job_details[job_id] = {
                    "last_run": last_run.isoformat(),
                    "hours_since_last_run": round(hours_since, 2),
                    "action": "skipped (recently run)",
                }

    return {
        "triggered_jobs": triggered_jobs,
        "skipped_jobs": skipped_jobs,
        "job_details": job_details,
        "timestamp": now.isoformat(),
    }


async def trigger_daily_job(scheduler, job_id: str) -> bool:
    if scheduler is None:
        logger.error(
            f"Cannot trigger daily job '{job_id}': scheduler not available"
        )
        return False

    try:
        job = scheduler.get_job(job_id)
        if job is None:
            logger.error(
                f"Cannot trigger daily job '{job_id}': job not found in scheduler"
            )
            return False

        # Execute the job function immediately (don't wait for scheduled time)
        scheduler.add_job(
            job.func,
            "date",
            run_date=datetime.now(timezone.utc),
            id=f"{job_id}_catchup_{datetime.now(timezone.utc).timestamp()}",
            misfire_grace_time=60,
        )
        logger.info(
            f"Triggered catch-up execution for daily job '{job_id}'",
            extra={"job_id": job_id},
        )
        return True

    except Exception as e:
        logger.error(
            f"Failed to trigger daily job '{job_id}': {e}",
            exc_info=True,
            extra={"job_id": job_id},
        )
        return False
