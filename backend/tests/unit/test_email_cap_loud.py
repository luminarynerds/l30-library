# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the daily-cap "loud + visible" path.

Asserts:
- increment_cap_skipped writes to Redis with TTL
- get_cap_skipped_today returns the current count
- get_email_stats includes cap_skipped_today
- send_email cap-hit branch routes through track_notification with
  error_type="daily_cap_exceeded" instead of silently dropping
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_resolver(name: str, value: int):
    return patch(
        f"app.core.email_safeguards.{name}",
        new=AsyncMock(return_value=value),
    )


@pytest.mark.unit
class TestIncrementCapSkipped:
    @pytest.mark.asyncio
    async def test_increment_first_call_sets_ttl(self):
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ):
            from app.core.email_safeguards import increment_cap_skipped
            count = await increment_cap_skipped()
            assert count == 1
            mock_redis.expire.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_increment_fail_open_when_redis_down(self):
        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=None,
        ):
            from app.core.email_safeguards import increment_cap_skipped
            assert await increment_cap_skipped() == -1


@pytest.mark.unit
class TestGetCapSkippedToday:
    @pytest.mark.asyncio
    async def test_returns_count(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="7")
        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ):
            from app.core.email_safeguards import get_cap_skipped_today
            assert await get_cap_skipped_today() == 7

    @pytest.mark.asyncio
    async def test_returns_zero_when_unset(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ):
            from app.core.email_safeguards import get_cap_skipped_today
            assert await get_cap_skipped_today() == 0


@pytest.mark.unit
class TestGetEmailStatsIncludesCapSkipped:
    @pytest.mark.asyncio
    async def test_includes_cap_skipped_field(self):
        mock_redis = AsyncMock()
        # daily_count, hourly_count, cap_skipped_today (in get_email_stats order)
        mock_redis.get = AsyncMock(side_effect=["12", "3", "5"])
        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_daily_send_cap", 500), _mock_resolver(
            "get_alert_threshold", 100
        ):
            from app.core.email_safeguards import get_email_stats
            stats = await get_email_stats()
            assert stats["cap_skipped_today"] == 5
            assert stats["daily_count"] == 12
            assert stats["status"] == "ok"

    @pytest.mark.asyncio
    async def test_redis_unavailable_returns_minus_one(self):
        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=None,
        ), _mock_resolver("get_daily_send_cap", 500):
            from app.core.email_safeguards import get_email_stats
            stats = await get_email_stats()
            assert stats["cap_skipped_today"] == -1


@pytest.mark.unit
class TestSendEmailCapHitIsLoud:
    """
    The core regression: when the daily cap is reached, send_email used to
    silently drop. It must now record to the DLQ and increment the skipped
    counter before returning False.
    """

    @pytest.mark.asyncio
    async def test_cap_hit_records_to_dlq_and_increments_counter(self):
        track_mock = AsyncMock()
        increment_mock = AsyncMock(return_value=1)

        with patch(
            "app.core.email_safeguards.check_daily_cap",
            new=AsyncMock(return_value=False),
        ), patch(
            "app.core.email_safeguards.increment_cap_skipped",
            new=increment_mock,
        ), patch(
            "app.core.notification_tracker.track_notification",
            new=track_mock,
        ):
            from app.core.email import send_email

            result = await send_email(
                to_email="patron@mockmail.dev",
                subject="Your hold is ready",
                html_content="<p>Pickup soon</p>",
            )

            assert result is False, "Cap-hit must still return False to caller"
            increment_mock.assert_awaited_once()
            track_mock.assert_awaited_once()
            kwargs = track_mock.await_args.kwargs
            assert kwargs["channel"] == "email"
            assert kwargs["success"] is False
            assert kwargs["error_type"] == "daily_cap_exceeded"
            assert kwargs["recipient"] == "patron@mockmail.dev"

    @pytest.mark.asyncio
    async def test_tracker_failure_does_not_break_return(self):
        """Even if DLQ write fails, send_email must still return False cleanly."""
        with patch(
            "app.core.email_safeguards.check_daily_cap",
            new=AsyncMock(return_value=False),
        ), patch(
            "app.core.email_safeguards.increment_cap_skipped",
            new=AsyncMock(side_effect=RuntimeError("redis explode")),
        ), patch(
            "app.core.notification_tracker.track_notification",
            new=AsyncMock(side_effect=RuntimeError("db explode")),
        ):
            from app.core.email import send_email
            result = await send_email(
                to_email="patron@mockmail.dev",
                subject="x",
                html_content="<p>y</p>",
            )
            assert result is False
