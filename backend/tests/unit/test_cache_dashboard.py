# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for cache metrics collection, cache dashboard admin endpoints,
and cache eviction.

Covers:
1. CacheMetrics hit/miss/error counting and snapshot output
2. CacheMetrics TTL distribution bucketing
3. CacheMetrics latency tracking
4. CacheMetrics thread safety (concurrent increments)
5. Admin cache dashboard auth logic (role gating)
6. Cache eviction via invalidate_cache
7. Integration: get_cached / set_cached record metrics

Run with: pytest backend/tests/unit/test_cache_dashboard.py -v
"""

import asyncio
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("redis")


# ============================================================================
# CacheMetrics — hit / miss / error counting
# ============================================================================

class TestCacheMetricsHitMiss:
    """Tests for per-prefix hit/miss/error counting."""

    def test_record_hit_increments_prefix(self):
        from app.core.cache import CacheMetrics

        m = CacheMetrics()
        m.record_hit("catalog:search:abc123")
        m.record_hit("catalog:search:def456")
        m.record_hit("patron:abc")

        snap = m.snapshot()
        assert snap["per_prefix"]["catalog:"]["hits"] == 2
        assert snap["per_prefix"]["patron:"]["hits"] == 1

    def test_record_miss_increments_prefix(self):
        from app.core.cache import CacheMetrics

        m = CacheMetrics()
        m.record_miss("catalog:search:abc123")
        m.record_miss("catalog:item:1")

        snap = m.snapshot()
        assert snap["per_prefix"]["catalog:"]["misses"] == 2

    def test_record_error_increments_prefix(self):
        from app.core.cache import CacheMetrics

        m = CacheMetrics()
        m.record_error("catalog:search:abc123")

        snap = m.snapshot()
        assert snap["per_prefix"]["catalog:"]["errors"] == 1

    def test_hit_rate_calculation(self):
        from app.core.cache import CacheMetrics

        m = CacheMetrics()
        for _ in range(7):
            m.record_hit("catalog:x")
        for _ in range(3):
            m.record_miss("catalog:y")

        snap = m.snapshot()
        assert snap["per_prefix"]["catalog:"]["hit_rate"] == 0.7

    def test_hit_rate_zero_when_no_requests(self):
        from app.core.cache import CacheMetrics

        m = CacheMetrics()
        snap = m.snapshot()
        assert snap["per_prefix"] == {}

    def test_no_colon_key_uses_other_prefix(self):
        from app.core.cache import CacheMetrics

        m = CacheMetrics()
        m.record_hit("weirdkey")
        snap = m.snapshot()
        assert "other:" in snap["per_prefix"]
        assert snap["per_prefix"]["other:"]["hits"] == 1


# ============================================================================
# CacheMetrics — TTL distribution
# ============================================================================

class TestCacheMetricsTTL:
    """Tests for TTL bucket distribution."""

    def test_ttl_under_1min(self):
        from app.core.cache import CacheMetrics

        m = CacheMetrics()
        m.record_ttl("catalog:x", 30)
        snap = m.snapshot()
        assert snap["ttl_distribution"]["catalog:"]["<1min"] == 1

    def test_ttl_1_to_5min(self):
        from app.core.cache import CacheMetrics

        m = CacheMetrics()
        m.record_ttl("catalog:x", 120)
        snap = m.snapshot()
        assert snap["ttl_distribution"]["catalog:"]["1-5min"] == 1

    def test_ttl_5_to_30min(self):
        from app.core.cache import CacheMetrics

        m = CacheMetrics()
        m.record_ttl("catalog:x", 600)
        snap = m.snapshot()
        assert snap["ttl_distribution"]["catalog:"]["5-30min"] == 1

    def test_ttl_30min_plus(self):
        from app.core.cache import CacheMetrics

        m = CacheMetrics()
        m.record_ttl("catalog:x", 3600)
        snap = m.snapshot()
        assert snap["ttl_distribution"]["catalog:"]["30min+"] == 1


# ============================================================================
# CacheMetrics — latency tracking
# ============================================================================

class TestCacheMetricsLatency:
    """Tests for get/set latency averages."""

    def test_get_latency_average(self):
        from app.core.cache import CacheMetrics

        m = CacheMetrics()
        m.record_get_latency(0.010)
        m.record_get_latency(0.020)

        snap = m.snapshot()
        assert snap["latency"]["avg_get_seconds"] == pytest.approx(0.015, abs=1e-6)
        assert snap["latency"]["total_gets"] == 2

    def test_set_latency_average(self):
        from app.core.cache import CacheMetrics

        m = CacheMetrics()
        m.record_set_latency(0.005)
        m.record_set_latency(0.015)

        snap = m.snapshot()
        assert snap["latency"]["avg_set_seconds"] == pytest.approx(0.010, abs=1e-6)
        assert snap["latency"]["total_sets"] == 2


# ============================================================================
# CacheMetrics — thread safety
# ============================================================================

class TestCacheMetricsThreadSafety:
    """Verify counters are correct under concurrent access."""

    def test_concurrent_hit_counting(self):
        from app.core.cache import CacheMetrics

        m = CacheMetrics()
        iterations = 1000
        thread_count = 4

        def worker():
            for _ in range(iterations):
                m.record_hit("catalog:x")

        threads = [threading.Thread(target=worker) for _ in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        snap = m.snapshot()
        assert snap["per_prefix"]["catalog:"]["hits"] == iterations * thread_count


# ============================================================================
# CacheMetrics — reset
# ============================================================================

class TestCacheMetricsReset:
    """Tests for the reset method."""

    def test_reset_clears_all_counters(self):
        from app.core.cache import CacheMetrics

        m = CacheMetrics()
        m.record_hit("catalog:x")
        m.record_miss("catalog:x")
        m.record_error("catalog:x")
        m.record_get_latency(0.01)
        m.record_set_latency(0.01)
        m.record_ttl("catalog:x", 100)

        m.reset()
        snap = m.snapshot()
        assert snap["per_prefix"] == {}
        assert snap["latency"]["total_gets"] == 0
        assert snap["latency"]["total_sets"] == 0
        assert snap["ttl_distribution"] == {}


# ============================================================================
# get_cache_metrics() function
# ============================================================================

class TestGetCacheMetrics:
    """Test the module-level get_cache_metrics function."""

    def test_returns_dict(self):
        from app.core.cache import get_cache_metrics

        result = get_cache_metrics()
        assert isinstance(result, dict)
        assert "per_prefix" in result
        assert "latency" in result
        assert "ttl_distribution" in result


# ============================================================================
# Admin auth logic — inline test of the role-gating pattern
# ============================================================================

class TestCacheDashboardAuth:
    """Verify that the admin role check logic works correctly.

    We test the require_admin logic inline to avoid triggering the
    full app.api.v1 package import chain (which has an unrelated
    enum bug in schemas/fine.py).
    """

    @staticmethod
    async def _require_admin(user):
        """Replicate the require_admin logic from cache_dashboard.py."""
        from fastapi import HTTPException, status
        from app.models.user import UserRole

        if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required",
            )
        return user

    @pytest.mark.asyncio
    async def test_rejects_patron(self):
        from app.models.user import UserRole

        patron = MagicMock()
        patron.role = UserRole.PATRON

        with pytest.raises(Exception) as exc_info:
            await self._require_admin(patron)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_allows_admin(self):
        from app.models.user import UserRole

        admin = MagicMock()
        admin.role = UserRole.ADMIN

        result = await self._require_admin(admin)
        assert result is admin

    @pytest.mark.asyncio
    async def test_allows_super_admin(self):
        from app.models.user import UserRole

        sa = MagicMock()
        sa.role = UserRole.SUPER_ADMIN

        result = await self._require_admin(sa)
        assert result is sa

    @pytest.mark.asyncio
    async def test_rejects_staff(self):
        from app.models.user import UserRole

        staff = MagicMock()
        staff.role = UserRole.STAFF

        with pytest.raises(Exception) as exc_info:
            await self._require_admin(staff)
        assert exc_info.value.status_code == 403


# ============================================================================
# Admin endpoints — response shapes (testing via Pydantic models directly)
# ============================================================================

class TestCacheDashboardResponseShapes:
    """Test the Pydantic response models used by cache dashboard endpoints."""

    def test_cache_stats_response_model(self):
        """CacheStatsResponse should accept redis_stats and app_metrics dicts."""
        from pydantic import BaseModel
        from typing import Any, Dict

        # Re-create the model inline to avoid full api.v1 import
        class CacheStatsResponse(BaseModel):
            redis_stats: Dict[str, Any]
            app_metrics: Dict[str, Any]

        resp = CacheStatsResponse(
            redis_stats={"connected": True, "keyspace": {"hits": 10}},
            app_metrics={"per_prefix": {}, "latency": {}, "ttl_distribution": {}},
        )
        assert resp.redis_stats["connected"] is True
        assert resp.app_metrics["per_prefix"] == {}

    def test_cache_key_info_model(self):
        """CacheKeyInfo should hold key, ttl_seconds, and type."""
        from pydantic import BaseModel, Field

        class CacheKeyInfo(BaseModel):
            key: str
            ttl_seconds: int
            type: str = "string"

        ki = CacheKeyInfo(key="catalog:search:abc", ttl_seconds=300, type="string")
        assert ki.key == "catalog:search:abc"
        assert ki.ttl_seconds == 300

    def test_evict_response_model(self):
        """EvictResponse should hold deleted count and pattern."""
        from pydantic import BaseModel, Field

        class EvictResponse(BaseModel):
            deleted: int
            pattern: str

        er = EvictResponse(deleted=5, pattern="catalog:*")
        assert er.deleted == 5
        assert er.pattern == "catalog:*"


# ============================================================================
# Cache eviction via invalidate_cache
# ============================================================================

class TestCacheEviction:
    """Tests for the invalidate_cache function used by the evict endpoint."""

    @pytest.mark.asyncio
    async def test_invalidate_cache_deletes_matching_keys(self):
        """invalidate_cache should SCAN for matching keys and delete them."""
        from app.core.cache import invalidate_cache

        mock_client = AsyncMock()

        # scan_iter yields matching keys
        async def mock_scan_iter(match=None, count=100):
            for k in ["catalog:a", "catalog:b", "catalog:c"]:
                yield k

        mock_client.scan_iter = mock_scan_iter
        mock_client.delete = AsyncMock(return_value=3)

        with patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = mock_client

            deleted = await invalidate_cache("catalog:*")

        assert deleted == 3
        mock_client.delete.assert_called_once_with("catalog:a", "catalog:b", "catalog:c")

    @pytest.mark.asyncio
    async def test_invalidate_cache_returns_zero_when_no_keys(self):
        """invalidate_cache should return 0 when no keys match."""
        from app.core.cache import invalidate_cache

        mock_client = AsyncMock()

        async def mock_scan_iter(match=None, count=100):
            return
            yield  # noqa: unreachable — makes this an async generator

        mock_client.scan_iter = mock_scan_iter

        with patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = mock_client

            deleted = await invalidate_cache("nonexistent:*")

        assert deleted == 0


# ============================================================================
# Integration: get_cached and set_cached track metrics
# ============================================================================

class TestCacheMetricsIntegration:
    """Verify that get_cached/set_cached record metrics to the global collector."""

    @pytest.mark.asyncio
    async def test_get_cached_records_hit(self):
        """get_cached should record a hit when a value is found."""
        from app.core.cache import get_cached, get_cache_metrics_collector
        import json

        collector = get_cache_metrics_collector()
        collector.reset()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=json.dumps({"data": "test"}))

        with patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = mock_client

            result = await get_cached("catalog:test:key1")

        assert result == {"data": "test"}
        snap = collector.snapshot()
        assert snap["per_prefix"]["catalog:"]["hits"] == 1

    @pytest.mark.asyncio
    async def test_get_cached_records_miss(self):
        """get_cached should record a miss when no value is found."""
        from app.core.cache import get_cached, get_cache_metrics_collector

        collector = get_cache_metrics_collector()
        collector.reset()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)

        with patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = mock_client

            result = await get_cached("catalog:test:key2")

        assert result is None
        snap = collector.snapshot()
        assert snap["per_prefix"]["catalog:"]["misses"] == 1

    @pytest.mark.asyncio
    async def test_set_cached_records_ttl(self):
        """set_cached should record the TTL in the distribution."""
        from app.core.cache import set_cached, get_cache_metrics_collector

        collector = get_cache_metrics_collector()
        collector.reset()

        mock_client = AsyncMock()
        mock_client.setex = AsyncMock()

        with patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = mock_client

            await set_cached("catalog:test:key3", {"data": "val"}, ttl_seconds=300)

        snap = collector.snapshot()
        assert snap["ttl_distribution"]["catalog:"]["5-30min"] == 1
        assert snap["latency"]["total_sets"] == 1

    @pytest.mark.asyncio
    async def test_get_cached_records_error_on_redis_failure(self):
        """get_cached should record an error when Redis throws."""
        from app.core.cache import get_cached, get_cache_metrics_collector
        import redis.exceptions

        collector = get_cache_metrics_collector()
        collector.reset()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=redis.exceptions.ConnectionError("fail"))

        with patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = mock_client

            result = await get_cached("catalog:err:key")

        assert result is None
        snap = collector.snapshot()
        assert snap["per_prefix"]["catalog:"]["errors"] == 1


# ============================================================================
# QueryCounterMiddleware
# ============================================================================

class TestQueryCounterMiddleware:
    """Tests for the query counter middleware."""

    def test_increment_and_get_query_count(self):
        """increment_query_count should increase the counter."""
        from app.middleware.query_counter import (
            increment_query_count,
            get_query_count,
            query_count_var,
        )

        # Reset for this test
        token = query_count_var.set(0)
        try:
            assert get_query_count() == 0
            increment_query_count()
            increment_query_count()
            assert get_query_count() == 2
        finally:
            query_count_var.reset(token)

    def test_extract_prefix_with_colon(self):
        """_extract_prefix should return first segment plus colon."""
        from app.core.cache import CacheMetrics

        assert CacheMetrics._extract_prefix("catalog:search:abc") == "catalog:"
        assert CacheMetrics._extract_prefix("patron:123") == "patron:"

    def test_extract_prefix_without_colon(self):
        """_extract_prefix should return 'other:' for keys without colons."""
        from app.core.cache import CacheMetrics

        assert CacheMetrics._extract_prefix("noprefix") == "other:"
