# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import and_, func, select

from ...core.config import get_settings
from ...core.database import AsyncSessionLocal
from ...core.logging import get_logger
from ...models.job_failure import JobExecutionLog

settings = get_settings()
logger = get_logger(__name__)


async def _push_to_kuma(up: bool, msg: str) -> None:
    """Ping the Uptime Kuma push monitor with the current heartbeat status.

    This is the positive side of the heartbeat: Kuma expects a ping every run
    and raises its own alert when the pings stop, so a dead scheduler (or a
    dead backend, which the failure email can't report on) still gets noticed.
    A monitoring outage must never break the check, so failures are swallowed.
    No-ops when no push token is configured.
    """
    token = settings.kuma_heartbeat_push_token
    if not token:
        return

    url = f"{settings.kuma_base_url.rstrip('/')}/api/push/{token}"
    params = {"status": "up" if up else "down", "msg": msg}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - heartbeat push is best-effort
        logger.warning("Heartbeat push to uptime monitor failed: %s", exc)

# Critical jobs and the maximum time allowed since their last successful run.
# If a job hasn't run within this window, it's considered missing.
CRITICAL_JOB_SCHEDULES: dict[str, timedelta] = {
    # Daily jobs: alert if not run in 26 hours (allows 2h grace over 24h)
    "daily_fine_calculation": timedelta(hours=26),
    "daily_data_retention": timedelta(hours=26),
    "child_to_adult_transitions": timedelta(hours=26),
    "daily_operational_alerts": timedelta(hours=26),
    "database_subscription_status_update": timedelta(hours=26),
    "certificate_expiration_check": timedelta(hours=26),
    # Hourly jobs: alert if not run in 2 hours
    "hourly_hold_expiration": timedelta(hours=2),
    "expired_suspension_processing": timedelta(hours=2),
    # Frequent jobs: alert if not run in 30 minutes
    "room_no_show_processing": timedelta(minutes=30),
    # Retry processing: alert if not run in 30 minutes (if enabled)
    "failed_job_retries": timedelta(minutes=30),
}


async def check_job_heartbeats() -> None:
    now = datetime.now(timezone.utc)
    missing_jobs = []
    healthy_jobs = []

    async with AsyncSessionLocal() as db:
        for job_id, max_age in CRITICAL_JOB_SCHEDULES.items():
            # Skip retry job check if retries are disabled
            if job_id == "failed_job_retries" and not settings.scheduler_retry_enabled:
                continue

            cutoff = now - max_age

            # Find the most recent successful execution
            stmt = (
                select(func.max(JobExecutionLog.started_at))
                .where(
                    and_(
                        JobExecutionLog.job_id == job_id,
                        JobExecutionLog.success == True,  # noqa: E712
                        JobExecutionLog.started_at >= cutoff,
                    )
                )
            )

            result = await db.execute(stmt)
            last_run = result.scalar_one_or_none()

            if last_run is None:
                # No successful run within the expected window
                missing_jobs.append({
                    "job_id": job_id,
                    "max_age": str(max_age),
                    "cutoff": cutoff.isoformat(),
                })
            else:
                healthy_jobs.append(job_id)

    if missing_jobs:
        logger.critical(
            f"HEARTBEAT ALERT: {len(missing_jobs)} critical job(s) have not run on schedule",
            extra={
                "missing_jobs": missing_jobs,
                "healthy_count": len(healthy_jobs),
                "total_monitored": len(CRITICAL_JOB_SCHEDULES),
            },
        )

        # Send alert email
        if settings.resend_api_key:
            try:
                from ...core.email import send_email

                job_rows = "".join(
                    f"<tr><td style='padding:8px;border:1px solid #ddd'><code>{j['job_id']}</code></td>"
                    f"<td style='padding:8px;border:1px solid #ddd'>{j['max_age']}</td></tr>"
                    for j in missing_jobs
                )

                html = f"""
                <h2>Scheduled Job Heartbeat Failure</h2>
                <p><strong>{len(missing_jobs)} critical job(s)</strong> have not completed
                   successfully within their expected intervals:</p>
                <table style="border-collapse:collapse;width:100%">
                    <tr style="background:#f2f2f2">
                        <th style="padding:8px;border:1px solid #ddd;text-align:left">Job ID</th>
                        <th style="padding:8px;border:1px solid #ddd;text-align:left">Expected Interval</th>
                    </tr>
                    {job_rows}
                </table>
                <p style="margin-top:16px">This may indicate the scheduler has stopped,
                   a job was deregistered, or a persistent failure is preventing completion.</p>
                <p><strong>Action required:</strong> Check scheduler health and job execution logs.</p>
                <p style="color:#888;font-size:12px">Checked at {now.isoformat()}</p>
                """

                admin_email = settings.job_alert_email or settings.from_email
                await send_email(admin_email, f"[CRITICAL] {len(missing_jobs)} scheduled job(s) overdue", html)
            except Exception as e:
                logger.error(f"Failed to send heartbeat alert email: {e}", exc_info=True)

        overdue = ", ".join(j["job_id"] for j in missing_jobs)
        await _push_to_kuma(False, f"{len(missing_jobs)} job(s) overdue: {overdue}")
    else:
        logger.info(
            "Job heartbeat check passed: all critical jobs running on schedule",
            extra={"healthy_count": len(healthy_jobs)},
        )
        await _push_to_kuma(True, f"all {len(healthy_jobs)} critical jobs healthy")
