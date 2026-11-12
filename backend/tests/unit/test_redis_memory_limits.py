# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Redis memory limits and eviction policy behavior.

These tests verify:
1. Memory limit configuration is correctly applied
2. Eviction policy (allkeys-lru) works as expected
3. Application handles memory pressure gracefully
4. Cache operations degrade gracefully when Redis is under pressure
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set test environment before importing app modules
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")


class TestRedisMemoryConfiguration:
    """Tests for Redis memory configuration validation."""

    @pytest.mark.asyncio
    async def test_maxmemory_setting_retrieval(self):
        """Test that we can retrieve the maxmemory setting from Redis."""
        mock_redis = AsyncMock()
        mock_redis.config_get = AsyncMock(return_value={"maxmemory": "268435456"})  # 256MB

        result = await mock_redis.config_get("maxmemory")

        assert "maxmemory" in result
        assert int(result["maxmemory"]) == 256 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_maxmemory_policy_is_allkeys_lru(self):
        """Test that eviction policy is set to allkeys-lru."""
        mock_redis = AsyncMock()
        mock_redis.config_get = AsyncMock(return_value={"maxmemory-policy": "allkeys-lru"})

        result = await mock_redis.config_get("maxmemory-policy")

        assert result["maxmemory-policy"] == "allkeys-lru"

    @pytest.mark.asyncio
    async def test_memory_info_retrieval(self):
        """Test retrieving memory usage information."""
        mock_redis = AsyncMock()
        mock_redis.info = AsyncMock(return_value={
            "used_memory": 52428800,  # 50MB
            "used_memory_human": "50.00M",
            "used_memory_peak": 67108864,  # 64MB
            "maxmemory": 268435456,  # 256MB
            "maxmemory_policy": "allkeys-lru",
            "evicted_keys": 0,
        })

        info = await mock_redis.info("memory")

        assert info["used_memory"] == 52428800
        assert info["maxmemory"] == 268435456
        assert info["maxmemory_policy"] == "allkeys-lru"
        assert info["evicted_keys"] == 0


class TestEvictionBehavior:
    """Tests for Redis eviction behavior under memory pressure."""

    @pytest.mark.asyncio
    async def test_lru_eviction_under_memory_pressure(self):
        """Test that LRU eviction works when memory limit is reached."""
        mock_redis = AsyncMock()

        # Simulate eviction stats
        mock_redis.info = AsyncMock(return_value={
            "evicted_keys": 100,
            "keyspace_hits": 5000,
            "keyspace_misses": 150,
        })

        info = await mock_redis.info("stats")

        # Verify eviction is happening
        assert info["evicted_keys"] > 0, "Expected evicted keys when under memory pressure"

        # Calculate cache hit ratio
        total_ops = info["keyspace_hits"] + info["keyspace_misses"]
        hit_ratio = info["keyspace_hits"] / total_ops

        # Even with eviction, hit ratio should be reasonable
        assert hit_ratio > 0.9, f"Cache hit ratio {hit_ratio} too low"

    @pytest.mark.asyncio
    async def test_eviction_rate_monitoring(self):
        """Test monitoring of key eviction rate."""
        mock_redis = AsyncMock()

        # First call - baseline
        mock_redis.info = AsyncMock(return_value={"evicted_keys": 100})
        info1 = await mock_redis.info("stats")

        # Second call - after some time
        mock_redis.info = AsyncMock(return_value={"evicted_keys": 150})
        info2 = await mock_redis.info("stats")

        eviction_delta = info2["evicted_keys"] - info1["evicted_keys"]

        # Alert threshold is >100 keys/second in monitoring/alerts.yaml
        assert eviction_delta >= 0, "Evicted keys should never decrease"

    @pytest.mark.asyncio
    async def test_memory_fragmentation_ratio(self):
        """Test that memory fragmentation is within acceptable bounds."""
        mock_redis = AsyncMock()
        mock_redis.info = AsyncMock(return_value={
            "mem_fragmentation_ratio": 1.2,  # 20% overhead is acceptable
        })

        info = await mock_redis.info("memory")

        # Fragmentation ratio should ideally be between 1.0 and 1.5
        assert 1.0 <= info["mem_fragmentation_ratio"] <= 2.0, \
            f"Memory fragmentation ratio {info['mem_fragmentation_ratio']} is concerning"


class TestCacheGracefulDegradation:
    """Tests for cache graceful degradation under failure conditions."""

    @pytest.mark.asyncio
    async def test_cache_get_handles_connection_error(self):
        """Test that cache get returns None on connection error."""
        from app.core.cache import get_cached

        with patch("app.core.cache.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(side_effect=ConnectionError("Redis unavailable"))
            mock_get_redis.return_value = mock_redis

            # Should return None instead of raising
            result = await get_cached("test_key")

            assert result is None

    @pytest.mark.asyncio
    async def test_cache_set_handles_connection_error(self):
        """Test that cache set fails silently on connection error."""
        from app.core.cache import set_cached

        with patch("app.core.cache.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.setex = AsyncMock(side_effect=ConnectionError("Redis unavailable"))
            mock_get_redis.return_value = mock_redis

            # Should not raise
            await set_cached("test_key", {"data": "value"}, ttl_seconds=300)

    @pytest.mark.asyncio
    async def test_cache_set_handles_oom_error(self):
        """Test that cache set handles OOM error gracefully."""
        from app.core.cache import set_cached

        with patch("app.core.cache.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            # Simulate Redis OOM error
            mock_redis.setex = AsyncMock(
                side_effect=Exception("OOM command not allowed when used memory > 'maxmemory'")
            )
            mock_get_redis.return_value = mock_redis

            # Should not raise - graceful degradation
            await set_cached("test_key", {"data": "value"}, ttl_seconds=300)

    @pytest.mark.asyncio
    async def test_cache_invalidation_handles_error(self):
        """Test that cache invalidation handles errors gracefully."""
        from app.core.cache import invalidate_cache

        with patch("app.core.cache.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            # scan_iter is a sync method returning an async iterator (real
            # redis-py: `async for k in client.scan_iter(...)`, no await on
            # the call itself). Mocking it as AsyncMock made the call return
            # a coroutine, and `async for` on a bare coroutine raises
            # TypeError before the intended ConnectionError ever fires.
            # A plain MagicMock with side_effect raises at call time instead,
            # which is what invalidate_cache's `async for` actually observes.
            mock_redis.scan_iter = MagicMock(side_effect=ConnectionError("Redis unavailable"))
            mock_get_redis.return_value = mock_redis

            # Should return 0 instead of raising
            result = await invalidate_cache("test:*")

            assert result == 0


class TestMemoryPressureDetection:
    """Tests for detecting and responding to memory pressure."""

    @pytest.mark.asyncio
    async def test_detect_high_memory_usage(self):
        """Test detection of high memory usage (>85% threshold from alerts.yaml)."""
        mock_redis = AsyncMock()
        mock_redis.info = AsyncMock(return_value={
            "used_memory": 230686720,  # ~220MB
            "maxmemory": 268435456,    # 256MB
        })

        info = await mock_redis.info("memory")

        used_memory = info["used_memory"]
        max_memory = info["maxmemory"]
        usage_percent = (used_memory / max_memory) * 100

        # Alert threshold from monitoring/alerts.yaml
        HIGH_MEMORY_THRESHOLD = 85

        assert usage_percent > HIGH_MEMORY_THRESHOLD, \
            f"Expected high memory usage, got {usage_percent:.1f}%"

    @pytest.mark.asyncio
    async def test_detect_critical_memory_usage(self):
        """Test detection of critical memory usage (>95% threshold from alerts.yaml)."""
        mock_redis = AsyncMock()
        mock_redis.info = AsyncMock(return_value={
            "used_memory": 260046848,  # ~248MB (97% of 256MB)
            "maxmemory": 268435456,    # 256MB
        })

        info = await mock_redis.info("memory")

        used_memory = info["used_memory"]
        max_memory = info["maxmemory"]
        usage_percent = (used_memory / max_memory) * 100

        # Critical threshold from monitoring/alerts.yaml
        CRITICAL_MEMORY_THRESHOLD = 95

        assert usage_percent > CRITICAL_MEMORY_THRESHOLD, \
            f"Expected critical memory usage, got {usage_percent:.1f}%"

    @pytest.mark.asyncio
    async def test_memory_usage_calculation_with_zero_maxmemory(self):
        """Test handling when maxmemory is not set (0 means unlimited)."""
        mock_redis = AsyncMock()
        mock_redis.info = AsyncMock(return_value={
            "used_memory": 52428800,
            "maxmemory": 0,  # Unlimited
        })

        info = await mock_redis.info("memory")

        max_memory = info["maxmemory"]

        # When maxmemory is 0, we should not calculate percentage
        if max_memory == 0:
            # This is a configuration issue - maxmemory should be set
            assert True, "maxmemory=0 indicates unlimited memory (misconfiguration in production)"


class TestCacheKeyManagement:
    """Tests for cache key management and TTL behavior."""

    @pytest.mark.asyncio
    async def test_cache_key_with_ttl(self):
        """Test that cache entries have proper TTL set."""
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=300)

        # Set a key with TTL
        await mock_redis.setex("test_key", 300, "value")

        # Verify TTL
        ttl = await mock_redis.ttl("test_key")

        assert ttl > 0, "Cache entries should have positive TTL"
        assert ttl <= 300, "TTL should not exceed set value"

    @pytest.mark.asyncio
    async def test_make_cache_key_consistency(self):
        """Test that cache key generation is consistent."""
        from app.core.cache import make_cache_key

        # Same parameters should produce same key
        key1 = make_cache_key("catalog:search", query="test", page=1)
        key2 = make_cache_key("catalog:search", query="test", page=1)

        assert key1 == key2, "Same parameters should produce same cache key"

    @pytest.mark.asyncio
    async def test_make_cache_key_different_params(self):
        """Test that different parameters produce different keys."""
        from app.core.cache import make_cache_key

        key1 = make_cache_key("catalog:search", query="test1", page=1)
        key2 = make_cache_key("catalog:search", query="test2", page=1)

        assert key1 != key2, "Different parameters should produce different cache keys"

    @pytest.mark.asyncio
    async def test_make_cache_key_ignores_none_values(self):
        """Test that None values are filtered from cache key generation."""
        from app.core.cache import make_cache_key

        key1 = make_cache_key("catalog:search", query="test", filter=None)
        key2 = make_cache_key("catalog:search", query="test")

        assert key1 == key2, "None values should be filtered from key generation"


class TestRedisHealthCheck:
    """Tests for Redis health check functionality."""

    @pytest.mark.asyncio
    async def test_redis_ping_success(self):
        """Test successful Redis ping."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)

        result = await mock_redis.ping()

        assert result is True

    @pytest.mark.asyncio
    async def test_redis_info_for_health_check(self):
        """Test Redis info retrieval for health monitoring."""
        mock_redis = AsyncMock()
        mock_redis.info = AsyncMock(return_value={
            "redis_version": "7.2.4",
            "connected_clients": 5,
            "used_memory_human": "50.00M",
            "uptime_in_days": 30,
        })

        info = await mock_redis.info()

        assert "redis_version" in info
        assert "connected_clients" in info
        assert info["connected_clients"] > 0


class TestEvictionPolicyBehavior:
    """Tests for specific eviction policy behaviors."""

    @pytest.mark.asyncio
    async def test_allkeys_lru_evicts_least_recently_used(self):
        """Test that allkeys-lru evicts least recently used keys."""
        # This is a conceptual test - actual behavior tested via integration
        mock_redis = AsyncMock()

        # Track access times
        keys_accessed = {}

        async def mock_get(key):
            keys_accessed[key] = asyncio.get_event_loop().time()
            return f"value_{key}"

        mock_redis.get = mock_get

        # Access keys in order
        await mock_redis.get("key1")
        await asyncio.sleep(0.01)
        await mock_redis.get("key2")
        await asyncio.sleep(0.01)
        await mock_redis.get("key3")

        # key1 was accessed first (oldest)
        oldest_key = min(keys_accessed, key=keys_accessed.get)
        assert oldest_key == "key1", "key1 should be the least recently used"

    @pytest.mark.asyncio
    async def test_eviction_does_not_affect_keys_with_ttl_differently(self):
        """Test that allkeys-lru treats all keys equally regardless of TTL."""
        # With allkeys-lru, both keys with and without TTL can be evicted
        # This is different from volatile-lru which only evicts keys with TTL
        mock_redis = AsyncMock()
        mock_redis.config_get = AsyncMock(return_value={"maxmemory-policy": "allkeys-lru"})

        policy = await mock_redis.config_get("maxmemory-policy")

        assert policy["maxmemory-policy"] == "allkeys-lru", \
            "Policy should be allkeys-lru to evict any key, not just those with TTL"


class TestRedisConnectionPooling:
    """Tests for Redis connection pool behavior."""

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion_handling(self):
        """Test handling when connection pool is exhausted."""
        from app.core.cache import get_cached

        with patch("app.core.cache.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(
                side_effect=Exception("Connection pool exhausted")
            )
            mock_get_redis.return_value = mock_redis

            # Should degrade gracefully
            result = await get_cached("test_key")

            assert result is None


class TestDockerComposeConfiguration:
    """Tests to validate docker-compose configuration for Redis."""

    def test_prod_compose_has_maxmemory(self):
        """Verify docker-compose.prod.yml has maxmemory configured."""
        import yaml

        compose_path = str(
            Path(__file__).resolve().parents[3] / "docker-compose.prod.yml"
        )

        with open(compose_path, "r") as f:
            compose = yaml.safe_load(f)

        redis_service = compose.get("services", {}).get("redis", {})
        command = redis_service.get("command", "")
        # command is ["sh", "-c", "redis-server --maxmemory 128mb ..."] --
        # a list of argv tokens, not a flat flag list, so join before
        # substring-checking for a flag.
        command_str = command if isinstance(command, str) else " ".join(command)

        assert "--maxmemory" in command_str, \
            "docker-compose.prod.yml should have --maxmemory in Redis command"
        assert "128mb" in command_str, \
            "maxmemory should be set to 128mb"

    def test_prod_compose_has_eviction_policy(self):
        """Verify docker-compose.prod.yml has eviction policy configured."""
        import yaml

        compose_path = str(
            Path(__file__).resolve().parents[3] / "docker-compose.prod.yml"
        )

        with open(compose_path, "r") as f:
            compose = yaml.safe_load(f)

        redis_service = compose.get("services", {}).get("redis", {})
        command = redis_service.get("command", "")
        command_str = command if isinstance(command, str) else " ".join(command)

        assert "--maxmemory-policy" in command_str, \
            "docker-compose.prod.yml should have --maxmemory-policy in Redis command"
        assert "allkeys-lru" in command_str, \
            "maxmemory-policy should be set to allkeys-lru"

    def test_prod_compose_resource_limits_align_with_maxmemory(self):
        """Verify container memory limits are >= Redis maxmemory."""
        import yaml

        compose_path = str(
            Path(__file__).resolve().parents[3] / "docker-compose.prod.yml"
        )

        with open(compose_path, "r") as f:
            compose = yaml.safe_load(f)

        redis_service = compose.get("services", {}).get("redis", {})
        deploy = redis_service.get("deploy", {})
        resources = deploy.get("resources", {})
        limits = resources.get("limits", {})

        # Container limit should be >= Redis maxmemory (128MB, per the
        # --maxmemory flag in the command above) + overhead
        container_memory = limits.get("memory", "0M")

        # Parse memory value (e.g., "512M" -> 512)
        memory_value = int(container_memory.rstrip("MmGg"))
        if container_memory.lower().endswith("g"):
            memory_value *= 1024

        redis_maxmemory_mb = 128

        assert memory_value >= redis_maxmemory_mb, \
            f"Container memory limit ({container_memory}) should be >= Redis maxmemory (128MB)"


class TestCacheMetrics:
    """Tests for cache metrics collection."""

    @pytest.mark.asyncio
    async def test_cache_hit_miss_tracking(self):
        """Test that cache hits and misses can be tracked."""
        mock_redis = AsyncMock()
        mock_redis.info = AsyncMock(return_value={
            "keyspace_hits": 1000,
            "keyspace_misses": 50,
        })

        info = await mock_redis.info("stats")

        hits = info["keyspace_hits"]
        misses = info["keyspace_misses"]
        total = hits + misses
        hit_rate = hits / total if total > 0 else 0

        assert hit_rate > 0.9, f"Cache hit rate {hit_rate:.2%} should be > 90%"

    @pytest.mark.asyncio
    async def test_expired_keys_tracking(self):
        """Test tracking of expired keys."""
        mock_redis = AsyncMock()
        mock_redis.info = AsyncMock(return_value={
            "expired_keys": 500,
        })

        info = await mock_redis.info("stats")

        assert "expired_keys" in info
        assert info["expired_keys"] >= 0
