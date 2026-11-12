# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import os
import traceback
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, ParamSpec

from sqlalchemy import and_, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.database import AsyncSessionLocal
from ..core.logging import get_logger
from ..models.job_failure import (
    FailedJobRecord,
    FailedJobStatus,
    JobAlertThreshold,
    JobExecutionLog,
    JobSeverity,
)

settings = get_settings()
logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

# Instance ID for tracking which server processed a job (for horizontal scaling)
INSTANCE_ID = os.environ.get("INSTANCE_ID", os.environ.get("HOSTNAME", "default"))


class RetryConfig:

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay_seconds: float = 2.0,
        max_delay_seconds: float = 300.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple = (Exception,),
    ):
        self.max_retries = max_retries
        self.initial_delay_seconds = initial_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

    def calculate_delay(self, attempt: int) -> float:
        delay = self.initial_delay_seconds * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay_seconds)

        if self.jitter:
            # Add up to 25% random jitter to prevent thundering herd
            import random
            jitter_amount = delay * 0.25 * random.random()
            delay += jitter_amount

        return delay


# Default retry configurations for different scenarios
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    initial_delay_seconds=2.0,
    max_delay_seconds=60.0,
)

NETWORK_RETRY_CONFIG = RetryConfig(
    max_retries=5,
    initial_delay_seconds=1.0,
    max_delay_seconds=30.0,
    retryable_exceptions=(ConnectionError, TimeoutError, OSError),
)

DATABASE_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    initial_delay_seconds=0.5,
    max_delay_seconds=10.0,
)


async def retry_with_backoff(
    func: Callable[P, T],
    *args: P.args,
    config: RetryConfig = DEFAULT_RETRY_CONFIG,
    **kwargs: P.kwargs,
) -> T:
    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e

            if attempt < config.max_retries:
                delay = config.calculate_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{config.max_retries + 1} failed, "
                    f"retrying in {delay:.2f}s: {e}",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": config.max_retries + 1,
                        "delay_seconds": delay,
                        "error": str(e),
                    },
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"All {config.max_retries + 1} attempts failed: {e}",
                    extra={
                        "total_attempts": config.max_retries + 1,
                        "final_error": str(e),
                    },
                )

    raise last_exception


def with_retry(config: RetryConfig = DEFAULT_RETRY_CONFIG):
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await retry_with_backoff(func, *args, config=config, **kwargs)
        return wrapper
    return decorator


class JobExecutionContext:

    def __init__(
        self,
        job_id: str,
        job_name: str,
        scheduled_at: Optional[datetime] = None,
        severity: JobSeverity = JobSeverity.MEDIUM,
    ):
        self.job_id = job_id
        self.job_name = job_name
        self.scheduled_at = scheduled_at
        self.severity = severity

        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.success = True
        self.error_message: Optional[str] = None
        self.error_type: Optional[str] = None

        self.items_processed = 0
        self.items_succeeded = 0
        self.items_failed = 0
        self.metrics: dict = {}

        self._failed_records: list[dict] = []
        self._db: Optional[AsyncSession] = None

    async def __aenter__(self) -> "JobExecutionContext":
        self.started_at = datetime.now(timezone.utc)
        self._session_ctx = AsyncSessionLocal()
        self._db = await self._session_ctx.__aenter__()
        logger.info(
            f"Starting job: {self.job_name}",
            extra={"job_id": self.job_id, "started_at": self.started_at.isoformat()},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.completed_at = datetime.now(timezone.utc)

        if exc_val:
            self.success = False
            self.error_message = str(exc_val)
            self.error_type = exc_type.__name__ if exc_type else None

        try:
            # Save execution log
            await self._save_execution_log()

            # Save failed records to dead letter queue
            await self._save_failed_records()

            # Check alerting thresholds
            await self._check_alerts()

            await self._db.commit()
        except Exception as e:
            logger.error(f"Error saving job execution data: {e}", exc_info=True)
            await self._db.rollback()
        finally:
            await self._session_ctx.__aexit__(None, None, None)

        duration = (self.completed_at - self.started_at).total_seconds()

        # #3: Emit partial failure ratio metric
        failure_ratio = 0.0
        if self.items_processed > 0:
            failure_ratio = self.items_failed / self.items_processed
        try:
            from ..core.metrics import increment, set_gauge
            set_gauge("job_partial_failure_ratio", failure_ratio, {"job": self.job_id})
            increment("job_items_processed_total", {"job": self.job_id}, self.items_processed)
            increment("job_items_failed_total", {"job": self.job_id}, self.items_failed)
            set_gauge("job_duration_seconds", duration, {"job": self.job_id})
        except Exception:  # noqa: BLE001 -- metrics emission must not break job completion tracking
            logger.debug("Failed to emit job execution metrics for %s", self.job_id)

        # #3: Alert if item-level failure rate exceeds 5%
        if self.items_processed > 0 and failure_ratio > 0.05:
            logger.error(
                f"HIGH PARTIAL FAILURE RATE in {self.job_name}: "
                f"{self.items_failed}/{self.items_processed} items failed "
                f"({failure_ratio:.1%})",
                extra={
                    "job_id": self.job_id,
                    "failure_ratio": failure_ratio,
                    "items_failed": self.items_failed,
                    "items_processed": self.items_processed,
                },
            )

        log_extra = {
            "job_id": self.job_id,
            "success": self.success,
            "duration_seconds": duration,
            "items_processed": self.items_processed,
            "items_succeeded": self.items_succeeded,
            "items_failed": self.items_failed,
            "failure_ratio": failure_ratio,
            **self.metrics,
        }

        if self.success:
            logger.info(f"Job completed: {self.job_name}", extra=log_extra)
        else:
            logger.error(
                f"Job failed: {self.job_name}",
                extra={**log_extra, "error": self.error_message},
            )

        # Don't suppress exceptions
        return False

    def record_success(self, count: int = 1) -> None:
        self.items_processed += count
        self.items_succeeded += count

    def record_failure(
        self,
        error: Exception,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        context: Optional[dict] = None,
        severity: Optional[JobSeverity] = None,
    ) -> None:
        self.items_processed += 1
        self.items_failed += 1

        self._failed_records.append({
            "job_id": self.job_id,
            "job_name": self.job_name,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "error_message": str(error),
            "error_type": type(error).__name__,
            "stack_trace": traceback.format_exc(),
            "context": context or {},
            "severity": severity or self.severity,
        })

    def add_metric(self, key: str, value: Any) -> None:
        self.metrics[key] = value

    async def _save_execution_log(self) -> None:
        duration = None
        if self.started_at and self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()

        was_misfire = False
        if self.scheduled_at and self.started_at:
            # Consider it a misfire if started more than 60 seconds after scheduled
            delay = (self.started_at - self.scheduled_at).total_seconds()
            was_misfire = delay > 60

        log_entry = JobExecutionLog(
            job_id=self.job_id,
            job_name=self.job_name,
            started_at=self.started_at,
            completed_at=self.completed_at,
            duration_seconds=duration,
            success=self.success and self.items_failed == 0,
            error_message=self.error_message,
            error_type=self.error_type,
            items_processed=self.items_processed,
            items_succeeded=self.items_succeeded,
            items_failed=self.items_failed,
            metrics=self.metrics if self.metrics else None,
            was_misfire=was_misfire,
            scheduled_at=self.scheduled_at,
            instance_id=INSTANCE_ID,
        )
        self._db.add(log_entry)

    async def _save_failed_records(self) -> None:
        now = datetime.now(timezone.utc)

        for record in self._failed_records:
            # Calculate next retry time with exponential backoff
            next_retry = now + timedelta(seconds=DEFAULT_RETRY_CONFIG.initial_delay_seconds)

            failed_record = FailedJobRecord(
                job_id=record["job_id"],
                job_name=record["job_name"],
                entity_type=record["entity_type"],
                entity_id=record["entity_id"],
                error_message=record["error_message"],
                error_type=record["error_type"],
                stack_trace=record["stack_trace"],
                context=record["context"],
                status=FailedJobStatus.PENDING,
                severity=record["severity"],
                retry_count=0,
                max_retries=DEFAULT_RETRY_CONFIG.max_retries,
                next_retry_at=next_retry,
            )
            self._db.add(failed_record)

    async def _check_alerts(self) -> None:
        # Get threshold config for this job or default
        stmt = select(JobAlertThreshold).where(
            JobAlertThreshold.job_id.in_([self.job_id, None])
        ).order_by(JobAlertThreshold.job_id.desc().nullslast())

        result = await self._db.execute(stmt)
        threshold = result.scalars().first()

        if not threshold or not threshold.alerts_enabled:
            return

        # Calculate error rate over the window
        window_start = datetime.now(timezone.utc) - timedelta(
            hours=threshold.error_rate_window_hours
        )

        # Get recent execution stats
        stats_stmt = select(
            func.count(JobExecutionLog.id).label("total"),
            func.sum(
                case(
                    (JobExecutionLog.success == False, 1),  # noqa: E712
                    else_=0
                )
            ).label("failed"),
        ).where(
            and_(
                JobExecutionLog.job_id == self.job_id,
                JobExecutionLog.started_at >= window_start,
            )
        )

        stats_result = await self._db.execute(stats_stmt)
        stats = stats_result.first()

        if not stats or not stats.total:
            return

        error_rate = (stats.failed or 0) / stats.total * 100

        # Check consecutive failures
        consecutive_stmt = (
            select(JobExecutionLog)
            .where(JobExecutionLog.job_id == self.job_id)
            .order_by(JobExecutionLog.started_at.desc())
            .limit(threshold.critical_consecutive_failures)
        )
        consecutive_result = await self._db.execute(consecutive_stmt)
        recent_executions = consecutive_result.scalars().all()

        consecutive_failures = 0
        for exec_log in recent_executions:
            if not exec_log.success:
                consecutive_failures += 1
            else:
                break

        # Determine alert level
        now = datetime.now(timezone.utc)
        cooldown = timedelta(minutes=threshold.alert_cooldown_minutes)

        is_critical = (
            error_rate >= threshold.critical_error_rate
            or consecutive_failures >= threshold.critical_consecutive_failures
        )
        is_warning = (
            error_rate >= threshold.warning_error_rate
            or consecutive_failures >= threshold.warning_consecutive_failures
        )

        if is_critical:
            if not threshold.last_critical_at or (now - threshold.last_critical_at) > cooldown:
                await self._send_alert(
                    level="critical",
                    error_rate=error_rate,
                    consecutive_failures=consecutive_failures,
                    threshold=threshold,
                )
                threshold.last_critical_at = now
        elif is_warning:
            if not threshold.last_warning_at or (now - threshold.last_warning_at) > cooldown:
                await self._send_alert(
                    level="warning",
                    error_rate=error_rate,
                    consecutive_failures=consecutive_failures,
                    threshold=threshold,
                )
                threshold.last_warning_at = now

    async def _send_alert(
        self,
        level: str,
        error_rate: float,
        consecutive_failures: int,
        threshold: JobAlertThreshold,
    ) -> None:
        alert_data = {
            "level": level,
            "job_id": self.job_id,
            "job_name": self.job_name,
            "error_rate": f"{error_rate:.1f}%",
            "consecutive_failures": consecutive_failures,
            "threshold_error_rate": (
                f"{threshold.critical_error_rate}%"
                if level == "critical"
                else f"{threshold.warning_error_rate}%"
            ),
            "threshold_consecutive": (
                threshold.critical_consecutive_failures
                if level == "critical"
                else threshold.warning_consecutive_failures
            ),
            "instance_id": INSTANCE_ID,
        }

        # Log the alert
        if level == "critical":
            logger.critical(
                f"CRITICAL: Job {self.job_name} exceeded error threshold",
                extra=alert_data,
            )
        else:
            logger.warning(
                f"WARNING: Job {self.job_name} error rate elevated",
                extra=alert_data,
            )

        # Send email alert if configured
        if settings.resend_api_key:
            try:
                from ..core.email import send_email

                subject = f"[{level.upper()}] Background Job Alert: {self.job_name}"
                html_content = f"""
                <h2>Background Job Alert</h2>
                <p><strong>Level:</strong> {level.upper()}</p>
                <p><strong>Job:</strong> {self.job_name} ({self.job_id})</p>
                <p><strong>Error Rate:</strong> {error_rate:.1f}%
                   (threshold: {alert_data['threshold_error_rate']})</p>
                <p><strong>Consecutive Failures:</strong> {consecutive_failures}
                   (threshold: {alert_data['threshold_consecutive']})</p>
                <p><strong>Instance:</strong> {INSTANCE_ID}</p>
                <p><strong>Time:</strong> {datetime.now(timezone.utc).isoformat()}</p>
                <hr>
                <p>Please review the job execution logs and failed job records
                   in the admin dashboard.</p>
                """

                # Send to admin email (could be configured per job)
                admin_email = settings.job_alert_email or settings.from_email
                await send_email(admin_email, subject, html_content)
            except Exception as e:
                logger.error(f"Failed to send alert email: {e}", exc_info=True)


async def process_retry_queue() -> dict:
    stats = {
        "processed": 0,
        "retried": 0,
        "abandoned": 0,
        "errors": 0,
    }

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        # Find records ready for retry
        stmt = (
            select(FailedJobRecord)
            .where(
                and_(
                    FailedJobRecord.status == FailedJobStatus.PENDING,
                    FailedJobRecord.next_retry_at <= now,
                    FailedJobRecord.retry_count < FailedJobRecord.max_retries,
                )
            )
            .with_for_update(skip_locked=True)
            .limit(100)  # Process in batches
        )

        result = await db.execute(stmt)
        records = result.scalars().all()

        for record in records:
            stats["processed"] += 1

            try:
                # Mark as retrying
                record.status = FailedJobStatus.RETRYING
                record.retry_count += 1
                record.last_retry_at = now

                # Attempt to retry based on job type
                retry_success = await _retry_failed_item(record, db)

                if retry_success:
                    record.status = FailedJobStatus.RESOLVED
                    record.resolved_at = now
                    record.resolved_by = "system"
                    record.resolution_notes = f"Auto-resolved after retry {record.retry_count}"
                    stats["retried"] += 1
                else:
                    # Calculate next retry with exponential backoff
                    delay = DEFAULT_RETRY_CONFIG.calculate_delay(record.retry_count)
                    record.next_retry_at = now + timedelta(seconds=delay)
                    record.status = FailedJobStatus.PENDING

                    # Check if max retries exceeded
                    if record.retry_count >= record.max_retries:
                        record.status = FailedJobStatus.ABANDONED
                        record.resolution_notes = f"Abandoned after {record.retry_count} retries"
                        stats["abandoned"] += 1

            except Exception as e:
                logger.error(
                    f"Error processing retry for record {record.id}: {e}",
                    exc_info=True,
                )
                stats["errors"] += 1
                record.status = FailedJobStatus.PENDING
                record.next_retry_at = now + timedelta(minutes=5)

        await db.commit()

    logger.info(
        "Retry queue processing completed",
        extra=stats,
    )

    return stats


async def _retry_failed_item(record: FailedJobRecord, db: AsyncSession) -> bool:
    # Import handlers here to avoid circular imports
    from .fine_policy_service import apply_fine_policy

    try:
        if record.job_id == "daily_fine_calculation" and record.entity_type == "checkout":
            from ..models.circulation import Checkout
            from ..models.user import User
            from ..models.catalog import CatalogItem

            # Fetch the checkout and related entities
            checkout = await db.get(Checkout, record.entity_id)
            if not checkout:
                logger.warning(f"Checkout {record.entity_id} not found for retry")
                return False

            user = await db.get(User, checkout.user_id)
            item = await db.get(CatalogItem, checkout.item_id) if checkout.item_id else None

            if not user:
                logger.warning(f"User not found for checkout {record.entity_id}")
                return False

            # Retry the fine calculation
            fine, was_modified = await apply_fine_policy(checkout, user, item, db)
            return True

        # Add more job-specific retry handlers here
        # elif record.job_id == "other_job":
        #     ...

        logger.warning(
            f"No retry handler for job {record.job_id}, entity type {record.entity_type}"
        )
        return False

    except Exception as e:
        logger.error(
            f"Retry failed for {record.job_id}/{record.entity_type}/{record.entity_id}: {e}",
            exc_info=True,
        )
        return False


async def get_job_health_summary(
    job_id: Optional[str] = None,
    hours: int = 24,
) -> dict:
    async with AsyncSessionLocal() as db:
        window_start = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Base query
        base_where = [JobExecutionLog.started_at >= window_start]
        if job_id:
            base_where.append(JobExecutionLog.job_id == job_id)

        # Overall stats
        stats_stmt = select(
            JobExecutionLog.job_id,
            func.count(JobExecutionLog.id).label("total_runs"),
            func.sum(case((JobExecutionLog.success == True, 1), else_=0)).label("successful"),  # noqa: E712
            func.sum(case((JobExecutionLog.success == False, 1), else_=0)).label("failed"),  # noqa: E712
            func.avg(JobExecutionLog.duration_seconds).label("avg_duration"),
            func.sum(JobExecutionLog.items_processed).label("total_items"),
            func.sum(JobExecutionLog.items_failed).label("total_item_failures"),
        ).where(and_(*base_where)).group_by(JobExecutionLog.job_id)

        result = await db.execute(stats_stmt)
        job_stats = result.fetchall()

        # Pending failures in dead letter queue
        dlq_stmt = select(
            FailedJobRecord.job_id,
            func.count(FailedJobRecord.id).label("pending"),
        ).where(
            FailedJobRecord.status.in_([FailedJobStatus.PENDING, FailedJobStatus.RETRYING])
        ).group_by(FailedJobRecord.job_id)

        dlq_result = await db.execute(dlq_stmt)
        dlq_stats = {row.job_id: row.pending for row in dlq_result.fetchall()}

        # Format results
        summary = {
            "window_hours": hours,
            "jobs": {},
        }

        for row in job_stats:
            error_rate = 0
            if row.total_runs > 0:
                error_rate = (row.failed or 0) / row.total_runs * 100

            item_error_rate = 0
            if row.total_items and row.total_items > 0:
                item_error_rate = (row.total_item_failures or 0) / row.total_items * 100

            summary["jobs"][row.job_id] = {
                "total_runs": row.total_runs,
                "successful": row.successful or 0,
                "failed": row.failed or 0,
                "error_rate": f"{error_rate:.1f}%",
                "avg_duration_seconds": round(row.avg_duration, 2) if row.avg_duration else None,
                "total_items_processed": row.total_items or 0,
                "total_item_failures": row.total_item_failures or 0,
                "item_error_rate": f"{item_error_rate:.1f}%",
                "pending_in_dlq": dlq_stats.get(row.job_id, 0),
            }

        return summary


async def cleanup_old_job_logs(days: int = 90) -> dict:
    async with AsyncSessionLocal() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Delete old execution logs
        exec_stmt = (
            JobExecutionLog.__table__.delete()
            .where(JobExecutionLog.created_at < cutoff)
        )
        exec_result = await db.execute(exec_stmt)

        # Delete old resolved/abandoned failure records
        failed_stmt = (
            FailedJobRecord.__table__.delete()
            .where(
                and_(
                    FailedJobRecord.created_at < cutoff,
                    FailedJobRecord.status.in_([
                        FailedJobStatus.RESOLVED,
                        FailedJobStatus.ABANDONED,
                    ]),
                )
            )
        )
        failed_result = await db.execute(failed_stmt)

        await db.commit()

        stats = {
            "execution_logs_deleted": exec_result.rowcount,
            "failed_records_deleted": failed_result.rowcount,
            "retention_days": days,
        }

        logger.info("Job log cleanup completed", extra=stats)

        return stats
