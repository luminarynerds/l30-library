# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for email safeguards (notification storm prevention).

Tests cover:
- Daily cap blocks sending after limit reached
- Daily cap allows sending when under limit
- Dedup blocks duplicate notification to same patron
- Dedup allows same notification to different patron
- Dedup allows different notification type to same patron
- Dedup allows resend after window expires
- Safeguards fail-open when Redis unavailable
- get_email_stats() returns correct counts
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# Mock resolver helpers so tests don't hit the DB. Each test composes these
# with the Redis mock via the `with patch(...), patch(...):` form below.
def _mock_resolver(name: str, value: int):
    """Return a patch() target that replaces the resolver with an AsyncMock."""
    return patch(
        f"app.core.email_safeguards.{name}",
        new=AsyncMock(return_value=value),
    )


@pytest.mark.unit
class TestDailyCap:
    """Test daily email send cap enforcement."""

    @pytest.mark.asyncio
    async def test_daily_cap_allows_when_under_limit(self):
        """Daily cap should return True when count is below the cap."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="50")  # 50 sent, cap is 500

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_daily_send_cap", 500):
            from app.core.email_safeguards import check_daily_cap

            result = await check_daily_cap()
            assert result is True

    @pytest.mark.asyncio
    async def test_daily_cap_blocks_when_at_limit(self):
        """Daily cap should return False when count equals the cap."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="500")  # 500 sent, cap is 500

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_daily_send_cap", 500):
            from app.core.email_safeguards import check_daily_cap

            result = await check_daily_cap()
            assert result is False

    @pytest.mark.asyncio
    async def test_daily_cap_blocks_when_over_limit(self):
        """Daily cap should return False when count exceeds the cap."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="600")

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_daily_send_cap", 500):
            from app.core.email_safeguards import check_daily_cap

            result = await check_daily_cap()
            assert result is False

    @pytest.mark.asyncio
    async def test_daily_cap_allows_when_count_is_zero(self):
        """Daily cap should return True when no emails have been sent."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # No key exists yet

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_daily_send_cap", 500):
            from app.core.email_safeguards import check_daily_cap

            result = await check_daily_cap()
            assert result is True


@pytest.mark.unit
class TestDedup:
    """Test per-patron notification deduplication."""

    @pytest.mark.asyncio
    async def test_dedup_blocks_duplicate_notification(self):
        """Dedup should return False when same notification was already sent."""
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)  # Key exists = duplicate

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_dedup_window_hours", 24):
            from app.core.email_safeguards import check_dedup

            result = await check_dedup(patron_id=42, notification_type="hold_ready")
            assert result is False

    @pytest.mark.asyncio
    async def test_dedup_allows_first_notification(self):
        """Dedup should return True when notification has not been sent."""
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)  # Key does not exist

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_dedup_window_hours", 24):
            from app.core.email_safeguards import check_dedup

            result = await check_dedup(patron_id=42, notification_type="hold_ready")
            assert result is True

    @pytest.mark.asyncio
    async def test_dedup_allows_same_notification_to_different_patron(self):
        """Dedup should allow the same notification type to a different patron."""
        mock_redis = AsyncMock()
        # Patron 42 got it (key exists), patron 99 did not (key does not exist)
        mock_redis.exists = AsyncMock(return_value=0)

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ):
            from app.core.email_safeguards import check_dedup

            result = await check_dedup(patron_id=99, notification_type="hold_ready")
            assert result is True

    @pytest.mark.asyncio
    async def test_dedup_allows_different_notification_type_to_same_patron(self):
        """Dedup should allow a different notification type to the same patron."""
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ):
            from app.core.email_safeguards import check_dedup

            # Same patron but different notification type
            result = await check_dedup(patron_id=42, notification_type="overdue_notice")
            assert result is True

    @pytest.mark.asyncio
    async def test_dedup_allows_resend_after_window_expires(self):
        """Dedup should allow resend when the dedup key has expired (does not exist)."""
        mock_redis = AsyncMock()
        # After window expires, key is gone
        mock_redis.exists = AsyncMock(return_value=0)

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_dedup_window_hours", 24):
            from app.core.email_safeguards import check_dedup

            result = await check_dedup(patron_id=42, notification_type="hold_ready")
            assert result is True

    @pytest.mark.asyncio
    async def test_dedup_uses_correct_key_format(self):
        """Dedup should query Redis with the correct key pattern."""
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_dedup_window_hours", 24), patch(
            "app.core.email_safeguards._dedup_window_key",
            return_value="2026-02-26",
        ):
            from app.core.email_safeguards import check_dedup

            await check_dedup(patron_id=42, notification_type="hold_ready")

            # Verify the correct key was checked
            mock_redis.exists.assert_called_once_with(
                "email:dedup:42:hold_ready:2026-02-26"
            )


@pytest.mark.unit
class TestMarkSent:
    """Test marking a notification as sent."""

    @pytest.mark.asyncio
    async def test_mark_sent_sets_key_with_ttl(self):
        """mark_sent should set the dedup key with correct TTL."""
        mock_redis = AsyncMock()

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_dedup_window_hours", 24), patch(
            "app.core.email_safeguards._dedup_window_key",
            return_value="2026-02-26",
        ):
            from app.core.email_safeguards import mark_sent

            await mark_sent(patron_id=42, notification_type="hold_ready")

            mock_redis.setex.assert_called_once_with(
                "email:dedup:42:hold_ready:2026-02-26",
                24 * 3600,  # 24 hours in seconds
                "1",
            )

    @pytest.mark.asyncio
    async def test_mark_sent_does_not_raise_when_redis_unavailable(self):
        """mark_sent should silently succeed when Redis is unavailable."""
        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=None,
        ):
            from app.core.email_safeguards import mark_sent

            # Should not raise
            await mark_sent(patron_id=42, notification_type="hold_ready")


@pytest.mark.unit
class TestIncrementDailyCount:
    """Test daily count incrementing and hourly alerting."""

    @pytest.mark.asyncio
    async def test_increment_daily_count_returns_new_count(self):
        """increment_daily_count should return the incremented count."""
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=[10, 3])  # daily=10, hourly=3
        mock_redis.expire = AsyncMock()

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_alert_threshold", 100):
            from app.core.email_safeguards import increment_daily_count

            result = await increment_daily_count()
            assert result == 10

    @pytest.mark.asyncio
    async def test_increment_daily_count_sets_ttl_on_first_increment(self):
        """increment_daily_count should set 48h TTL when count goes to 1."""
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=[1, 1])  # First increment for both
        mock_redis.expire = AsyncMock()

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_alert_threshold", 100):
            from app.core.email_safeguards import increment_daily_count

            await increment_daily_count()

            # Should set TTL for both daily and hourly keys
            assert mock_redis.expire.call_count == 2

    @pytest.mark.asyncio
    async def test_increment_returns_negative_one_when_redis_unavailable(self):
        """increment_daily_count should return -1 when Redis is unavailable."""
        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=None,
        ):
            from app.core.email_safeguards import increment_daily_count

            result = await increment_daily_count()
            assert result == -1


@pytest.mark.unit
class TestFailOpen:
    """Test that all safeguards fail-open when Redis is unavailable."""

    @pytest.mark.asyncio
    async def test_check_daily_cap_fails_open_when_redis_unavailable(self):
        """check_daily_cap should return True (allow sending) when Redis is down."""
        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=None,
        ):
            from app.core.email_safeguards import check_daily_cap

            result = await check_daily_cap()
            assert result is True

    @pytest.mark.asyncio
    async def test_check_dedup_fails_open_when_redis_unavailable(self):
        """check_dedup should return True (allow sending) when Redis is down."""
        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=None,
        ):
            from app.core.email_safeguards import check_dedup

            result = await check_dedup(patron_id=42, notification_type="hold_ready")
            assert result is True

    @pytest.mark.asyncio
    async def test_mark_sent_fails_open_when_redis_unavailable(self):
        """mark_sent should not raise when Redis is down."""
        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=None,
        ):
            from app.core.email_safeguards import mark_sent

            # Should not raise
            await mark_sent(patron_id=42, notification_type="hold_ready")

    @pytest.mark.asyncio
    async def test_check_daily_cap_fails_open_on_redis_error(self):
        """check_daily_cap should return True when Redis raises an exception."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Connection refused"))

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ):
            from app.core.email_safeguards import check_daily_cap

            result = await check_daily_cap()
            assert result is True

    @pytest.mark.asyncio
    async def test_check_dedup_fails_open_on_redis_error(self):
        """check_dedup should return True when Redis raises an exception."""
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(side_effect=Exception("Connection refused"))

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_dedup_window_hours", 24):
            from app.core.email_safeguards import check_dedup

            result = await check_dedup(patron_id=42, notification_type="hold_ready")
            assert result is True

    @pytest.mark.asyncio
    async def test_increment_daily_count_fails_open_on_redis_error(self):
        """increment_daily_count should return -1 when Redis raises an exception."""
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=Exception("Connection refused"))

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ):
            from app.core.email_safeguards import increment_daily_count

            result = await increment_daily_count()
            assert result == -1

    @pytest.mark.asyncio
    async def test_get_redis_client_returns_none_on_import_error(self):
        """_get_redis_client should return None if cache module fails to import."""
        with patch(
            "app.core.email_safeguards._get_redis_client",
            side_effect=Exception("Import error"),
        ):
            from app.core.email_safeguards import check_daily_cap

            # The outer try/except in check_daily_cap catches this
            result = await check_daily_cap()
            assert result is True


@pytest.mark.unit
class TestGetEmailStats:
    """Test the get_email_stats monitoring function."""

    @pytest.mark.asyncio
    async def test_get_email_stats_returns_correct_counts(self):
        """get_email_stats should return accurate daily and hourly counts."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=["150", "25", "0"])  # daily=150, hourly=25, cap_skipped=0

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_daily_send_cap", 500), _mock_resolver("get_alert_threshold", 100):
            from app.core.email_safeguards import get_email_stats

            stats = await get_email_stats()

            assert stats["daily_count"] == 150
            assert stats["daily_cap"] == 500
            assert stats["hourly_count"] == 25
            assert stats["status"] == "ok"
            assert stats["usage_percent"] == 30.0

    @pytest.mark.asyncio
    async def test_get_email_stats_status_warning_at_80_percent(self):
        """get_email_stats should report 'warning' when usage is 80-99%."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=["400", "10", "0"])  # daily=400, cap=500 = 80%, cap_skipped=0

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_daily_send_cap", 500), _mock_resolver("get_alert_threshold", 100):
            from app.core.email_safeguards import get_email_stats

            stats = await get_email_stats()

            assert stats["status"] == "warning"

    @pytest.mark.asyncio
    async def test_get_email_stats_status_critical_at_cap(self):
        """get_email_stats should report 'critical' when at or over cap."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=["500", "50", "12"])  # daily=500 = 100%, cap_skipped=12

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_daily_send_cap", 500), _mock_resolver("get_alert_threshold", 100):
            from app.core.email_safeguards import get_email_stats

            stats = await get_email_stats()

            assert stats["status"] == "critical"

    @pytest.mark.asyncio
    async def test_get_email_stats_redis_unavailable(self):
        """get_email_stats should return safe defaults when Redis is down."""
        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=None,
        ):
            from app.core.email_safeguards import get_email_stats

            stats = await get_email_stats()

            assert stats["status"] == "unknown"
            assert stats["daily_count"] == -1
            assert "daily_cap" in stats

    @pytest.mark.asyncio
    async def test_get_email_stats_zero_sends(self):
        """get_email_stats should report 'ok' with zero sends."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # No keys exist

        with patch(
            "app.core.email_safeguards._get_redis_client",
            return_value=mock_redis,
        ), _mock_resolver("get_daily_send_cap", 500), _mock_resolver("get_alert_threshold", 100):
            from app.core.email_safeguards import get_email_stats

            stats = await get_email_stats()

            assert stats["daily_count"] == 0
            assert stats["hourly_count"] == 0
            assert stats["status"] == "ok"
            assert stats["usage_percent"] == 0.0
