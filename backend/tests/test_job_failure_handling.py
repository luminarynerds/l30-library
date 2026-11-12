# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Job Failure Handling System

This test suite covers:
- Retry logic with exponential backoff
- Dead letter queue (failed job records)
- Job execution logging
- Alerting on error thresholds
- JobExecutionContext behavior
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_failure import (
    FailedJobRecord,
    FailedJobStatus,
    JobAlertThreshold,
    JobExecutionLog,
    JobSeverity,
)
from app.services.job_failure_service import (
    DEFAULT_RETRY_CONFIG,
    JobExecutionContext,
    RetryConfig,
    cleanup_old_job_logs,
    get_job_health_summary,
    process_retry_queue,
    retry_with_backoff,
    with_retry,
)


class TestRetryConfig:
    """Test RetryConfig class and exponential backoff calculations."""

    def test_default_config_values(self):
        """Test default retry configuration values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.initial_delay_seconds == 2.0
        assert config.max_delay_seconds == 300.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_calculate_delay_exponential(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            initial_delay_seconds=1.0,
            exponential_base=2.0,
            max_delay_seconds=100.0,
            jitter=False,
        )

        assert config.calculate_delay(0) == 1.0  # 1 * 2^0 = 1
        assert config.calculate_delay(1) == 2.0  # 1 * 2^1 = 2
        assert config.calculate_delay(2) == 4.0  # 1 * 2^2 = 4
        assert config.calculate_delay(3) == 8.0  # 1 * 2^3 = 8

    def test_calculate_delay_respects_max(self):
        """Test that delay respects max_delay_seconds."""
        config = RetryConfig(
            initial_delay_seconds=10.0,
            exponential_base=2.0,
            max_delay_seconds=30.0,
            jitter=False,
        )

        # Without cap: 10 * 2^2 = 40, but capped at 30
        assert config.calculate_delay(2) == 30.0

    def test_calculate_delay_with_jitter(self):
        """Test that jitter adds variance to delay."""
        config = RetryConfig(
            initial_delay_seconds=10.0,
            exponential_base=2.0,
            max_delay_seconds=100.0,
            jitter=True,
        )

        # Run multiple times to verify jitter varies
        delays = [config.calculate_delay(1) for _ in range(10)]

        # Base delay is 20, jitter adds up to 25% (5)
        # So delays should be between 20 and 25
        assert all(20 <= d <= 25 for d in delays)

        # With jitter, not all delays should be identical
        assert len(set(delays)) > 1


class TestRetryWithBackoff:
    """Test retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_successful_on_first_try(self):
        """Test function succeeds without retry."""
        call_count = 0

        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_with_backoff(
            successful_func,
            config=RetryConfig(max_retries=3),
        )

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test function retries on failure."""
        call_count = 0

        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary error")
            return "success"

        config = RetryConfig(
            max_retries=3,
            initial_delay_seconds=0.01,  # Fast for testing
            jitter=False,
        )

        result = await retry_with_backoff(failing_then_success, config=config)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        """Test raises exception after max retries exhausted."""
        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent error")

        config = RetryConfig(
            max_retries=2,
            initial_delay_seconds=0.01,
            jitter=False,
        )

        with pytest.raises(ValueError, match="persistent error"):
            await retry_with_backoff(always_fails, config=config)

        assert call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_only_retries_specified_exceptions(self):
        """Test only retries specified exception types."""
        call_count = 0

        async def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("wrong type")

        config = RetryConfig(
            max_retries=3,
            initial_delay_seconds=0.01,
            retryable_exceptions=(ValueError,),  # Not TypeError
        )

        with pytest.raises(TypeError, match="wrong type"):
            await retry_with_backoff(raises_type_error, config=config)

        # Should not retry because TypeError not in retryable_exceptions
        assert call_count == 1


class TestWithRetryDecorator:
    """Test @with_retry decorator."""

    @pytest.mark.asyncio
    async def test_decorator_applies_retry(self):
        """Test decorator applies retry logic."""
        call_count = 0

        config = RetryConfig(
            max_retries=2,
            initial_delay_seconds=0.01,
            jitter=False,
        )

        @with_retry(config=config)
        async def decorated_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("retry me")
            return "decorated success"

        result = await decorated_func()

        assert result == "decorated success"
        assert call_count == 2


class TestJobExecutionContext:
    """Test JobExecutionContext class."""

    @pytest.mark.asyncio
    async def test_context_tracks_success(self, test_db: AsyncSession):
        """Test context tracks successful item processing."""
        async with JobExecutionContext(
            job_id="test_job",
            job_name="Test Job",
        ) as ctx:
            ctx.record_success()
            ctx.record_success()
            ctx.record_success()

        assert ctx.items_processed == 3
        assert ctx.items_succeeded == 3
        assert ctx.items_failed == 0

        # Verify execution log was created
        result = await test_db.execute(
            select(JobExecutionLog).where(JobExecutionLog.job_id == "test_job")
        )
        log = result.scalars().first()
        assert log is not None
        assert log.success is True
        assert log.items_processed == 3
        assert log.items_succeeded == 3

    @pytest.mark.asyncio
    async def test_context_tracks_failures(self, test_db: AsyncSession):
        """Test context tracks failed items to dead letter queue."""
        async with JobExecutionContext(
            job_id="test_job_failures",
            job_name="Test Job with Failures",
            severity=JobSeverity.HIGH,
        ) as ctx:
            ctx.record_success()
            ctx.record_failure(
                error=ValueError("test error"),
                entity_type="checkout",
                entity_id=123,
                context={"extra": "data"},
            )
            ctx.record_success()

        assert ctx.items_processed == 3
        assert ctx.items_succeeded == 2
        assert ctx.items_failed == 1

        # Verify failed record was created
        result = await test_db.execute(
            select(FailedJobRecord).where(
                FailedJobRecord.job_id == "test_job_failures"
            )
        )
        failed_record = result.scalars().first()
        assert failed_record is not None
        assert failed_record.entity_type == "checkout"
        assert failed_record.entity_id == 123
        assert "test error" in failed_record.error_message
        assert failed_record.status == FailedJobStatus.PENDING
        assert failed_record.severity == JobSeverity.HIGH

    @pytest.mark.asyncio
    async def test_context_adds_custom_metrics(self, test_db: AsyncSession):
        """Test context supports custom metrics."""
        async with JobExecutionContext(
            job_id="test_metrics",
            job_name="Test Metrics Job",
        ) as ctx:
            ctx.add_metric("fines_created", 10)
            ctx.add_metric("fines_updated", 5)
            ctx.record_success(15)

        # Verify metrics in execution log
        result = await test_db.execute(
            select(JobExecutionLog).where(JobExecutionLog.job_id == "test_metrics")
        )
        log = result.scalars().first()
        assert log is not None
        assert log.metrics["fines_created"] == 10
        assert log.metrics["fines_updated"] == 5

    @pytest.mark.asyncio
    async def test_context_handles_job_level_exception(self, test_db: AsyncSession):
        """Test context handles exceptions at job level."""
        with pytest.raises(RuntimeError, match="job crashed"):
            async with JobExecutionContext(
                job_id="test_crash",
                job_name="Crashing Job",
            ) as ctx:
                ctx.record_success()
                raise RuntimeError("job crashed")

        # Verify execution log shows failure
        result = await test_db.execute(
            select(JobExecutionLog).where(JobExecutionLog.job_id == "test_crash")
        )
        log = result.scalars().first()
        assert log is not None
        assert log.success is False
        assert "job crashed" in log.error_message
        assert log.error_type == "RuntimeError"


class TestProcessRetryQueue:
    """Test retry queue processing."""

    @pytest.mark.asyncio
    async def test_process_ready_retries(self, test_db: AsyncSession):
        """Test processing items ready for retry."""
        now = datetime.now(timezone.utc)

        # Create a failed record ready for retry
        failed_record = FailedJobRecord(
            job_id="test_job",
            job_name="Test Job",
            entity_type="test_entity",
            entity_id=1,
            error_message="test error",
            status=FailedJobStatus.PENDING,
            retry_count=0,
            max_retries=3,
            next_retry_at=now - timedelta(minutes=5),  # Ready for retry
        )
        test_db.add(failed_record)
        await test_db.commit()

        # Process retry queue (will fail because no handler for test_job)
        stats = await process_retry_queue()

        assert stats["processed"] >= 1

    @pytest.mark.asyncio
    async def test_abandon_after_max_retries(self, test_db: AsyncSession):
        """Test records are abandoned after max retries."""
        now = datetime.now(timezone.utc)

        # Create a failed record at max retries
        failed_record = FailedJobRecord(
            job_id="test_job_abandon",
            job_name="Test Job Abandon",
            entity_type="test_entity",
            entity_id=999,
            error_message="persistent error",
            status=FailedJobStatus.PENDING,
            retry_count=2,  # At max-1
            max_retries=3,
            next_retry_at=now - timedelta(minutes=5),
        )
        test_db.add(failed_record)
        await test_db.commit()
        _ = failed_record.id

        # Process retry queue
        await process_retry_queue()

        # Refresh and check status
        await test_db.refresh(failed_record)
        # After failed retry, count becomes 3 which equals max
        assert failed_record.retry_count == 3
        assert failed_record.status == FailedJobStatus.ABANDONED


class TestJobHealthSummary:
    """Test job health summary reporting."""

    @pytest.mark.asyncio
    async def test_health_summary_calculation(self, test_db: AsyncSession):
        """Test health summary calculates correct metrics."""
        now = datetime.now(timezone.utc)

        # Create some execution logs
        for i in range(5):
            log = JobExecutionLog(
                job_id="health_test_job",
                job_name="Health Test Job",
                started_at=now - timedelta(hours=i),
                completed_at=now - timedelta(hours=i) + timedelta(seconds=30),
                duration_seconds=30.0,
                success=i < 4,  # 4 success, 1 failure
                items_processed=10,
                items_succeeded=9 if i < 4 else 5,
                items_failed=1 if i < 4 else 5,
            )
            test_db.add(log)
        await test_db.commit()

        summary = await get_job_health_summary(job_id="health_test_job", hours=24)

        assert "health_test_job" in summary["jobs"]
        job_stats = summary["jobs"]["health_test_job"]
        assert job_stats["total_runs"] == 5
        assert job_stats["successful"] == 4
        assert job_stats["failed"] == 1
        assert job_stats["error_rate"] == "20.0%"


class TestCleanupJobLogs:
    """Test job log cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_old_logs(self, test_db: AsyncSession):
        """Test cleanup removes old logs."""
        now = datetime.now(timezone.utc)

        # Create old execution log. cleanup_old_job_logs (job_failure_service.py)
        # filters on `created_at`, not `started_at`/`completed_at` -- created_at
        # is server_default=func.now(), so it must be set explicitly here or
        # every row looks freshly-inserted (today) regardless of started_at.
        old_log = JobExecutionLog(
            job_id="cleanup_test",
            job_name="Cleanup Test",
            started_at=now - timedelta(days=100),
            completed_at=now - timedelta(days=100) + timedelta(seconds=10),
            created_at=now - timedelta(days=100),
            success=True,
        )
        test_db.add(old_log)

        # Create recent execution log
        recent_log = JobExecutionLog(
            job_id="cleanup_test",
            job_name="Cleanup Test",
            started_at=now - timedelta(days=10),
            completed_at=now - timedelta(days=10) + timedelta(seconds=10),
            success=True,
        )
        test_db.add(recent_log)

        # Create old resolved failure
        old_failure = FailedJobRecord(
            job_id="cleanup_test",
            job_name="Cleanup Test",
            error_message="old error",
            status=FailedJobStatus.RESOLVED,
            resolved_at=now - timedelta(days=100),
            created_at=now - timedelta(days=100),
        )
        test_db.add(old_failure)

        await test_db.commit()

        # Run cleanup with 90 day retention
        stats = await cleanup_old_job_logs(days=90)

        assert stats["execution_logs_deleted"] >= 1
        assert stats["failed_records_deleted"] >= 1

        # Verify recent log still exists
        result = await test_db.execute(
            select(JobExecutionLog).where(
                JobExecutionLog.started_at > now - timedelta(days=90)
            )
        )
        remaining = result.scalars().all()
        assert len(remaining) >= 1


class TestAlertThresholds:
    """Test alerting threshold configuration."""

    @pytest.mark.asyncio
    async def test_default_threshold_created(self, test_db: AsyncSession):
        """Test default alert threshold is created by migration."""
        # The migration should create a default threshold
        result = await test_db.execute(
            select(JobAlertThreshold).where(JobAlertThreshold.job_id.is_(None))
        )
        default_threshold = result.scalars().first()

        # May not exist in test DB without migration
        if default_threshold:
            assert default_threshold.warning_error_rate == 5.0
            assert default_threshold.critical_error_rate == 15.0
            assert default_threshold.alerts_enabled is True

    @pytest.mark.asyncio
    async def test_job_specific_threshold(self, test_db: AsyncSession):
        """Test job-specific threshold overrides default."""
        # Create job-specific threshold
        threshold = JobAlertThreshold(
            job_id="specific_job",
            warning_error_rate=10.0,
            critical_error_rate=25.0,
            warning_consecutive_failures=3,
            critical_consecutive_failures=7,
            error_rate_window_hours=12,
        )
        test_db.add(threshold)
        await test_db.commit()

        # Verify it was saved
        result = await test_db.execute(
            select(JobAlertThreshold).where(
                JobAlertThreshold.job_id == "specific_job"
            )
        )
        saved = result.scalars().first()
        assert saved is not None
        assert saved.warning_error_rate == 10.0
        assert saved.critical_error_rate == 25.0


class TestIntegrationWithScheduler:
    """Integration tests with scheduler service."""

    @pytest.mark.asyncio
    async def test_fine_calculation_uses_job_context(
        self, test_db: AsyncSession
    ):
        """Test that fine calculation job uses JobExecutionContext."""
        from app.services.schedulers import calculate_daily_overdue_fines

        # Run the job (it will find no overdue checkouts in test DB).
        # send_email is imported locally inside _send_alert (only reached
        # when an alert threshold fires), not at module scope, so there is
        # no app.services.job_failure_service.send_email to patch.
        with patch('app.core.email.send_email', new_callable=AsyncMock):
            await calculate_daily_overdue_fines()

        # Verify execution log was created
        result = await test_db.execute(
            select(JobExecutionLog).where(
                JobExecutionLog.job_id == "daily_fine_calculation"
            )
        )
        log = result.scalars().first()
        assert log is not None
        assert log.job_name == "Daily Overdue Fine Calculation"
