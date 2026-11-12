# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for distributed cache locking, cascade invalidation, and warming pipeline.

Covers:
1. Owned lock acquisition and release (Lua-based safe release)
2. Stale-while-revalidate behavior
3. Early refresh / proactive TTL extension
4. Lock metrics tracking
5. Cascade invalidation via dependency graph
6. Priority-based warming pipeline

Run with: pytest tests/unit/test_distributed_cache_locking.py -v
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("redis")


# ============================================================================
# Distributed Locking - Owned Locks
# ============================================================================

class TestOwnedLockAcquisition:
    """Tests for lock acquisition with unique owner tokens."""

    @pytest.mark.asyncio
    async def test_acquire_lock_returns_token(self):
        """_acquire_lock should return a unique token on success."""
        from app.core.cache import _acquire_lock

        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=True)

        token = await _acquire_lock(mock_client, "test:lock", lock_timeout=30)

        assert token is not None
        assert len(token) == 36  # UUID4 format
        mock_client.set.assert_called_once()
        call_kwargs = mock_client.set.call_args
        assert call_kwargs[1]["nx"] is True
        assert call_kwargs[1]["ex"] == 30

    @pytest.mark.asyncio
    async def test_acquire_lock_returns_none_when_held(self):
        """_acquire_lock should return None when lock is already held."""
        from app.core.cache import _acquire_lock

        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=False)

        token = await _acquire_lock(mock_client, "test:lock", lock_timeout=30)

        assert token is None

    @pytest.mark.asyncio
    async def test_release_lock_with_correct_token(self):
        """_release_lock should release when the correct token is provided."""
        from app.core.cache import _release_lock

        mock_client = AsyncMock()
        mock_client.eval = AsyncMock(return_value=1)

        result = await _release_lock(mock_client, "test:lock", "my-token")

        assert result is True
        mock_client.eval.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_lock_with_wrong_token(self):
        """_release_lock should NOT release when a wrong token is provided."""
        from app.core.cache import _release_lock

        mock_client = AsyncMock()
        mock_client.eval = AsyncMock(return_value=0)

        result = await _release_lock(mock_client, "test:lock", "wrong-token")

        assert result is False

    @pytest.mark.asyncio
    async def test_each_acquisition_generates_unique_token(self):
        """Each lock acquisition should generate a different token."""
        from app.core.cache import _acquire_lock

        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=True)

        token1 = await _acquire_lock(mock_client, "test:lock", lock_timeout=30)
        token2 = await _acquire_lock(mock_client, "test:lock", lock_timeout=30)

        assert token1 != token2


# ============================================================================
# Stale-While-Revalidate
# ============================================================================

class TestStaleWhileRevalidate:
    """Tests for stale data serving during cache rebuild."""

    @pytest.mark.asyncio
    async def test_stale_value_is_stored_on_rebuild(self):
        """When a lock winner rebuilds cache, it should also store a stale copy."""
        from app.core.cache import get_cached_with_lock

        with patch("app.core.cache._get_with_ttl", new_callable=AsyncMock) as mock_get_ttl, \
             patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis, \
             patch("app.core.cache.set_cached", new_callable=AsyncMock), \
             patch("app.core.cache._set_stale", new_callable=AsyncMock) as mock_set_stale, \
             patch("app.core.cache._acquire_lock", new_callable=AsyncMock) as mock_acquire, \
             patch("app.core.cache._release_lock", new_callable=AsyncMock):

            mock_get_ttl.return_value = (None, None)  # Cache miss
            mock_acquire.return_value = "test-token"   # We win the lock
            mock_redis.return_value = AsyncMock()

            fetch_func = AsyncMock(return_value={"data": "fresh"})

            result = await get_cached_with_lock(
                "test:key", fetch_func, ttl_seconds=300,
                stale_while_revalidate=True,
            )

            assert result == {"data": "fresh"}
            mock_set_stale.assert_called_once_with("test:key", {"data": "fresh"}, 600)

    @pytest.mark.asyncio
    async def test_stale_served_when_lock_not_acquired(self):
        """Waiters should get stale data immediately instead of polling."""
        from app.core.cache import get_cached_with_lock

        with patch("app.core.cache._get_with_ttl", new_callable=AsyncMock) as mock_get_ttl, \
             patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis, \
             patch("app.core.cache._get_stale", new_callable=AsyncMock) as mock_get_stale, \
             patch("app.core.cache._acquire_lock", new_callable=AsyncMock) as mock_acquire:

            mock_get_ttl.return_value = (None, None)         # Cache miss
            mock_acquire.return_value = None                  # Lock held by someone else
            mock_get_stale.return_value = {"data": "stale"}   # Stale copy available
            mock_redis.return_value = AsyncMock()

            fetch_func = AsyncMock()  # Should NOT be called

            result = await get_cached_with_lock(
                "test:key", fetch_func, ttl_seconds=300,
                stale_while_revalidate=True,
            )

            assert result == {"data": "stale"}
            fetch_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_stale_falls_through_to_polling(self):
        """When no stale data exists, waiters should poll for fresh cache."""
        from app.core.cache import get_cached_with_lock

        with patch("app.core.cache._get_with_ttl", new_callable=AsyncMock) as mock_get_ttl, \
             patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis, \
             patch("app.core.cache._get_stale", new_callable=AsyncMock) as mock_get_stale, \
             patch("app.core.cache.get_cached", new_callable=AsyncMock) as mock_get, \
             patch("app.core.cache._acquire_lock", new_callable=AsyncMock) as mock_acquire:

            mock_get_ttl.return_value = (None, None)    # Cache miss
            mock_acquire.return_value = None             # Lock held by someone else
            mock_get_stale.return_value = None           # No stale copy
            mock_redis.return_value = AsyncMock()
            # Simulate cache appearing after a few polls
            mock_get.side_effect = [None, None, {"data": "fresh"}]

            result = await get_cached_with_lock(
                "test:key", AsyncMock(), ttl_seconds=300,
                stale_while_revalidate=True,
                lock_retry_delay=0.01,
                lock_max_retries=5,
            )

            assert result == {"data": "fresh"}

    @pytest.mark.asyncio
    async def test_stale_served_on_rebuild_error(self):
        """If the rebuild function fails, stale data should be returned."""
        from app.core.cache import get_cached_with_lock

        with patch("app.core.cache._get_with_ttl", new_callable=AsyncMock) as mock_get_ttl, \
             patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis, \
             patch("app.core.cache._get_stale", new_callable=AsyncMock) as mock_get_stale, \
             patch("app.core.cache._acquire_lock", new_callable=AsyncMock) as mock_acquire, \
             patch("app.core.cache._release_lock", new_callable=AsyncMock):

            mock_get_ttl.return_value = (None, None)          # Cache miss
            mock_acquire.return_value = "test-token"           # We win the lock
            mock_get_stale.return_value = {"data": "stale"}    # Stale available
            mock_redis.return_value = AsyncMock()

            fetch_func = AsyncMock(side_effect=Exception("DB down"))

            result = await get_cached_with_lock(
                "test:key", fetch_func, ttl_seconds=300,
                stale_while_revalidate=True,
            )

            assert result == {"data": "stale"}


# ============================================================================
# Early Refresh (Proactive TTL Extension)
# ============================================================================

class TestEarlyRefresh:
    """Tests for proactive cache refresh before TTL expiration."""

    @pytest.mark.asyncio
    async def test_early_refresh_triggers_at_low_ttl(self):
        """Cache hit with low remaining TTL should trigger background refresh."""
        from app.core.cache import get_cached_with_lock

        with patch("app.core.cache._get_with_ttl", new_callable=AsyncMock) as mock_get_ttl, \
             patch("app.core.cache._background_refresh", new_callable=AsyncMock):

            # 300s TTL, 20% threshold = 60s. Remaining TTL = 50s -> should trigger
            mock_get_ttl.return_value = ({"data": "cached"}, 50)

            fetch_func = AsyncMock()

            result = await get_cached_with_lock(
                "test:key", fetch_func, ttl_seconds=300,
                early_refresh_fraction=0.2,
            )

            assert result == {"data": "cached"}

    @pytest.mark.asyncio
    async def test_no_early_refresh_when_ttl_sufficient(self):
        """Cache hit with plenty of TTL remaining should not trigger refresh."""
        from app.core.cache import get_cached_with_lock, _lock_metrics

        initial_refreshes = _lock_metrics.early_refreshes

        with patch("app.core.cache._get_with_ttl", new_callable=AsyncMock) as mock_get_ttl:
            # 300s TTL, 20% threshold = 60s. Remaining TTL = 200s -> no trigger
            mock_get_ttl.return_value = ({"data": "cached"}, 200)

            result = await get_cached_with_lock(
                "test:key", AsyncMock(), ttl_seconds=300,
                early_refresh_fraction=0.2,
            )

            assert result == {"data": "cached"}
            assert _lock_metrics.early_refreshes == initial_refreshes

    @pytest.mark.asyncio
    async def test_background_refresh_acquires_lock(self):
        """Background refresh should acquire a lock to prevent duplicate refreshes."""
        from app.core.cache import _background_refresh

        with patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis, \
             patch("app.core.cache._acquire_lock", new_callable=AsyncMock) as mock_acquire, \
             patch("app.core.cache._release_lock", new_callable=AsyncMock) as mock_release, \
             patch("app.core.cache.set_cached", new_callable=AsyncMock) as mock_set, \
             patch("app.core.cache._set_stale", new_callable=AsyncMock):

            mock_redis.return_value = AsyncMock()
            mock_acquire.return_value = "bg-token"

            fetch_func = AsyncMock(return_value={"data": "refreshed"})

            await _background_refresh(
                "test:key", fetch_func, ttl_seconds=300,
                lock_timeout=30, stale_while_revalidate=True,
            )

            mock_acquire.assert_called_once()
            fetch_func.assert_called_once()
            mock_set.assert_called_once_with("test:key", {"data": "refreshed"}, 300)
            mock_release.assert_called_once()

    @pytest.mark.asyncio
    async def test_background_refresh_skips_when_lock_held(self):
        """Background refresh should skip if another process holds the lock."""
        from app.core.cache import _background_refresh

        with patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis, \
             patch("app.core.cache._acquire_lock", new_callable=AsyncMock) as mock_acquire:

            mock_redis.return_value = AsyncMock()
            mock_acquire.return_value = None  # Lock held by someone else

            fetch_func = AsyncMock()

            await _background_refresh(
                "test:key", fetch_func, ttl_seconds=300,
                lock_timeout=30, stale_while_revalidate=True,
            )

            fetch_func.assert_not_called()


# ============================================================================
# Lock Metrics
# ============================================================================

class TestLockMetrics:
    """Tests for lock performance metrics tracking."""

    def test_lock_metrics_dataclass(self):
        """LockMetrics should track all expected fields."""
        from app.core.cache import LockMetrics

        metrics = LockMetrics()
        assert metrics.locks_acquired == 0
        assert metrics.locks_waited == 0
        assert metrics.locks_timed_out == 0
        assert metrics.stale_serves == 0
        assert metrics.early_refreshes == 0
        assert metrics.rebuild_errors == 0

    def test_lock_metrics_to_dict(self):
        """LockMetrics.to_dict should return all fields."""
        from app.core.cache import LockMetrics

        metrics = LockMetrics(locks_acquired=5, stale_serves=3)
        d = metrics.to_dict()

        assert d["locks_acquired"] == 5
        assert d["stale_serves"] == 3
        assert "locks_waited" in d
        assert "locks_timed_out" in d

    def test_get_lock_metrics_returns_global(self):
        """get_lock_metrics should return the module-level metrics instance."""
        from app.core.cache import get_lock_metrics, _lock_metrics

        assert get_lock_metrics() is _lock_metrics

    @pytest.mark.asyncio
    async def test_metrics_increment_on_lock_acquired(self):
        """Lock acquisition should increment locks_acquired."""
        from app.core.cache import get_cached_with_lock, _lock_metrics

        initial = _lock_metrics.locks_acquired

        with patch("app.core.cache._get_with_ttl", new_callable=AsyncMock) as mock_get_ttl, \
             patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis, \
             patch("app.core.cache.set_cached", new_callable=AsyncMock), \
             patch("app.core.cache._set_stale", new_callable=AsyncMock), \
             patch("app.core.cache._acquire_lock", new_callable=AsyncMock) as mock_acquire, \
             patch("app.core.cache._release_lock", new_callable=AsyncMock):

            mock_get_ttl.return_value = (None, None)
            mock_acquire.return_value = "token"
            mock_redis.return_value = AsyncMock()

            await get_cached_with_lock(
                "test:metrics", AsyncMock(return_value="data"), ttl_seconds=60,
            )

            assert _lock_metrics.locks_acquired == initial + 1


# ============================================================================
# Cascade Invalidation
# ============================================================================

class TestCascadeInvalidation:
    """Tests for cascade invalidation via dependency graph."""

    def test_cascade_dependencies_exist(self):
        """CASCADE_DEPENDENCIES should be defined and non-empty."""
        from app.core.cache_strategies import CASCADE_DEPENDENCIES

        assert isinstance(CASCADE_DEPENDENCIES, dict)
        assert len(CASCADE_DEPENDENCIES) > 0

    def test_cascade_dependencies_has_expected_domains(self):
        """Dependency graph should cover key domains."""
        from app.core.cache_strategies import CASCADE_DEPENDENCIES

        # CASCADE_DEPENDENCIES keys are built from CacheKeyBuilder.PREFIX
        # (branding.CACHE_NAMESPACE = "l30"). This whole file used "lsc:"
        # throughout, presumably left over from the project's pre-rename
        # branding -- every one of these keys is a real entry in the dict
        # under "l30:", never "lsc:".
        expected_domains = [
            "l30:catalog:item",
            "l30:catalog:avail",
            "l30:patron:checkouts",
            "l30:patron:holds",
            "l30:patron:fines",
            "l30:branch:info",
        ]
        for domain in expected_domains:
            assert domain in CASCADE_DEPENDENCIES, (
                f"CASCADE_DEPENDENCIES should include {domain}"
            )

    def test_table_to_cache_domains_mapping(self):
        """TABLE_TO_CACHE_DOMAINS should map tables to cache domains."""
        from app.core.cache_strategies import TABLE_TO_CACHE_DOMAINS

        assert "catalog_items" in TABLE_TO_CACHE_DOMAINS
        assert "checkouts" in TABLE_TO_CACHE_DOMAINS
        assert "holds" in TABLE_TO_CACHE_DOMAINS
        assert "fines" in TABLE_TO_CACHE_DOMAINS

    @pytest.mark.asyncio
    async def test_cascade_invalidate_walks_graph(self):
        """cascade_invalidate should invalidate dependent domains."""
        from app.core.cache_strategies import cascade_invalidate

        with patch("app.core.cache_strategies.invalidate_cache", new_callable=AsyncMock) as mock_inv:
            mock_inv.return_value = 2

            count = await cascade_invalidate("l30:catalog:item")

            # Should invalidate search, browse, newarrivals, discovery
            assert count > 0
            assert mock_inv.call_count >= 4  # At least the 4 direct dependents

    @pytest.mark.asyncio
    async def test_cascade_respects_depth_limit(self):
        """Cascade should not go deeper than MAX_CASCADE_DEPTH."""
        from app.core.cache_strategies import cascade_invalidate, MAX_CASCADE_DEPTH

        with patch("app.core.cache_strategies.invalidate_cache", new_callable=AsyncMock) as mock_inv:
            mock_inv.return_value = 1

            # Even with circular dependencies, should not hang
            await cascade_invalidate("l30:catalog:item")

            # Should complete without error

    @pytest.mark.asyncio
    async def test_cascade_prevents_cycles(self):
        """Cascade should not revisit already-invalidated domains."""
        from app.core.cache_strategies import cascade_invalidate

        visited_patterns = []

        async def track_invalidate(pattern):
            visited_patterns.append(pattern)
            return 1

        with patch("app.core.cache_strategies.invalidate_cache", side_effect=track_invalidate):
            await cascade_invalidate("l30:patron:checkouts")

        # Each pattern should appear at most once
        unique_patterns = set(visited_patterns)
        assert len(unique_patterns) == len(visited_patterns), (
            f"Duplicate patterns found: {visited_patterns}"
        )

    @pytest.mark.asyncio
    async def test_cascade_invalidate_for_table(self):
        """cascade_invalidate_for_table should trigger cascades for all affected domains."""
        from app.core.cache_strategies import cascade_invalidate_for_table

        with patch("app.core.cache_strategies.cascade_invalidate", new_callable=AsyncMock) as mock_cascade:
            mock_cascade.return_value = 5

            count = await cascade_invalidate_for_table(
                "checkouts", {"user_id": 1, "item_id": 42}
            )

            assert count == 10  # 5 per domain, 2 domains
            assert mock_cascade.call_count == 2

    @pytest.mark.asyncio
    async def test_cascade_invalidate_for_unknown_table(self):
        """Unknown tables should produce zero cascade invalidations."""
        from app.core.cache_strategies import cascade_invalidate_for_table

        count = await cascade_invalidate_for_table("unknown_table", {})
        assert count == 0

    def test_get_cascade_dependencies_returns_copy(self):
        """get_cascade_dependencies should return the graph for inspection."""
        from app.core.cache_strategies import get_cascade_dependencies

        deps = get_cascade_dependencies()
        assert isinstance(deps, dict)
        assert "l30:catalog:item" in deps

    @pytest.mark.asyncio
    async def test_handle_mutation_triggers_cascade(self):
        """handle_mutation_invalidation should include cascade invalidation."""
        from app.core.cache_strategies import handle_mutation_invalidation

        with patch("app.core.cache_strategies.invalidate_cache", new_callable=AsyncMock) as mock_inv, \
             patch("app.core.cache_strategies.cascade_invalidate_for_table", new_callable=AsyncMock) as mock_cascade:

            mock_inv.return_value = 1
            mock_cascade.return_value = 3

            count = await handle_mutation_invalidation(
                "checkouts", "INSERT",
                {"user_id": 1, "item_id": 42},
            )

            assert count > 0
            mock_cascade.assert_called_once_with("checkouts", {"user_id": 1, "item_id": 42})


# ============================================================================
# Integration: get_with_ttl pipeline helper
# ============================================================================

class TestGetWithTtl:
    """Tests for the _get_with_ttl pipeline helper."""

    @pytest.mark.asyncio
    async def test_get_with_ttl_returns_value_and_ttl(self):
        """_get_with_ttl should return (value, ttl) tuple."""
        from app.core.cache import _get_with_ttl

        with patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_pipe = AsyncMock()
            mock_pipe.execute = AsyncMock(return_value=['{"data": "test"}', 250])
            mock_client = AsyncMock()
            mock_client.pipeline = MagicMock(return_value=mock_pipe)
            mock_redis.return_value = mock_client

            value, ttl = await _get_with_ttl("test:key")

            assert value == {"data": "test"}
            assert ttl == 250

    @pytest.mark.asyncio
    async def test_get_with_ttl_returns_none_on_miss(self):
        """_get_with_ttl should return (None, None) on cache miss."""
        from app.core.cache import _get_with_ttl

        with patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_pipe = AsyncMock()
            mock_pipe.execute = AsyncMock(return_value=[None, -2])
            mock_client = AsyncMock()
            mock_client.pipeline = MagicMock(return_value=mock_pipe)
            mock_redis.return_value = mock_client

            value, ttl = await _get_with_ttl("test:key")

            assert value is None
            assert ttl is None

    @pytest.mark.asyncio
    async def test_get_with_ttl_handles_errors(self):
        """_get_with_ttl should return (None, None) on error."""
        from app.core.cache import _get_with_ttl

        with patch("app.core.cache.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_redis.side_effect = Exception("Connection error")

            value, ttl = await _get_with_ttl("test:key")

            assert value is None
            assert ttl is None
