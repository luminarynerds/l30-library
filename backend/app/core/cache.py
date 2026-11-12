# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import json
import hashlib
from app.core.logging import get_logger
import ssl
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, Callable, List, TypeVar
from datetime import datetime

import redis.asyncio as aioredis
import redis.exceptions

from .config import get_settings

T = TypeVar('T')

logger = get_logger(__name__)
settings = get_settings()


# =============================================================================
# Cache Metrics — Thread-safe hit/miss/error/latency tracking
# =============================================================================

class CacheMetrics:

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Counts keyed by prefix (e.g. "catalog:", "patron:")
        self._hits: Dict[str, int] = defaultdict(int)
        self._misses: Dict[str, int] = defaultdict(int)
        self._errors: Dict[str, int] = defaultdict(int)
        # Latency tracking (cumulative seconds and count)
        self._get_latency_sum: float = 0.0
        self._get_latency_count: int = 0
        self._set_latency_sum: float = 0.0
        self._set_latency_count: int = 0
        # TTL distribution buckets keyed by prefix
        # Each set operation records the TTL into one of four buckets
        self._ttl_buckets: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"<1min": 0, "1-5min": 0, "5-30min": 0, "30min+": 0}
        )

    # -- helpers to extract prefix from a cache key -------------------------

    @staticmethod
    def _extract_prefix(key: str) -> str:
        idx = key.find(":")
        if idx == -1:
            return "other:"
        return key[: idx + 1]

    # -- recording methods --------------------------------------------------

    def record_hit(self, key: str) -> None:
        prefix = self._extract_prefix(key)
        with self._lock:
            self._hits[prefix] += 1

    def record_miss(self, key: str) -> None:
        prefix = self._extract_prefix(key)
        with self._lock:
            self._misses[prefix] += 1

    def record_error(self, key: str) -> None:
        prefix = self._extract_prefix(key)
        with self._lock:
            self._errors[prefix] += 1

    def record_get_latency(self, seconds: float) -> None:
        with self._lock:
            self._get_latency_sum += seconds
            self._get_latency_count += 1

    def record_set_latency(self, seconds: float) -> None:
        with self._lock:
            self._set_latency_sum += seconds
            self._set_latency_count += 1

    def record_ttl(self, key: str, ttl_seconds: int) -> None:
        prefix = self._extract_prefix(key)
        if ttl_seconds < 60:
            bucket = "<1min"
        elif ttl_seconds < 300:
            bucket = "1-5min"
        elif ttl_seconds < 1800:
            bucket = "5-30min"
        else:
            bucket = "30min+"
        with self._lock:
            self._ttl_buckets[prefix][bucket] += 1

    # -- query methods ------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            all_prefixes = sorted(
                set(self._hits.keys())
                | set(self._misses.keys())
                | set(self._errors.keys())
            )
            per_prefix = {}
            for pfx in all_prefixes:
                hits = self._hits.get(pfx, 0)
                misses = self._misses.get(pfx, 0)
                errors = self._errors.get(pfx, 0)
                total = hits + misses
                per_prefix[pfx] = {
                    "hits": hits,
                    "misses": misses,
                    "errors": errors,
                    "hit_rate": round(hits / total, 4) if total else 0.0,
                }

            avg_get = (
                round(self._get_latency_sum / self._get_latency_count, 6)
                if self._get_latency_count
                else 0.0
            )
            avg_set = (
                round(self._set_latency_sum / self._set_latency_count, 6)
                if self._set_latency_count
                else 0.0
            )

            ttl_dist = {k: dict(v) for k, v in self._ttl_buckets.items()}

            return {
                "per_prefix": per_prefix,
                "latency": {
                    "avg_get_seconds": avg_get,
                    "avg_set_seconds": avg_set,
                    "total_gets": self._get_latency_count,
                    "total_sets": self._set_latency_count,
                },
                "ttl_distribution": ttl_dist,
            }

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
            self._misses.clear()
            self._errors.clear()
            self._get_latency_sum = 0.0
            self._get_latency_count = 0
            self._set_latency_sum = 0.0
            self._set_latency_count = 0
            self._ttl_buckets.clear()


# Singleton instance
_cache_metrics = CacheMetrics()


def get_cache_metrics() -> Dict[str, Any]:
    return _cache_metrics.snapshot()


def get_cache_metrics_collector() -> CacheMetrics:
    return _cache_metrics

redis_client: Optional[aioredis.Redis] = None

# Lua script for safe lock release (only release if we own the lock)
_RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

# Memory thresholds aligned with monitoring/alerts.yaml
MEMORY_WARNING_THRESHOLD = 0.85  # 85% - triggers warning alert
MEMORY_CRITICAL_THRESHOLD = 0.95  # 95% - triggers critical alert


@dataclass
class RedisMemoryStatus:

    used_memory: int
    max_memory: int
    used_memory_human: str
    evicted_keys: int
    memory_fragmentation_ratio: float
    maxmemory_policy: str

    @property
    def usage_percent(self) -> float:
        if self.max_memory == 0:
            return 0.0
        return (self.used_memory / self.max_memory) * 100

    @property
    def is_warning(self) -> bool:
        if self.max_memory == 0:
            return False
        return (self.used_memory / self.max_memory) >= MEMORY_WARNING_THRESHOLD

    @property
    def is_critical(self) -> bool:
        if self.max_memory == 0:
            return False
        return (self.used_memory / self.max_memory) >= MEMORY_CRITICAL_THRESHOLD

    @property
    def available_memory(self) -> int:
        if self.max_memory == 0:
            return -1  # Unlimited
        return max(0, self.max_memory - self.used_memory)


def _get_redis_ssl_context() -> Optional[ssl.SSLContext]:
    if not settings.redis_ssl:
        return None

    context = ssl.create_default_context()

    # Configure certificate verification
    if settings.redis_ssl_cert_reqs == "required":
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
    elif settings.redis_ssl_cert_reqs == "optional":
        context.check_hostname = False
        context.verify_mode = ssl.CERT_OPTIONAL
    else:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    # Load CA certificates if specified
    if settings.redis_ssl_ca_certs:
        context.load_verify_locations(settings.redis_ssl_ca_certs)

    return context


async def get_redis() -> Optional[aioredis.Redis]:
    global redis_client
    if redis_client is None:
        try:
            ssl_context = _get_redis_ssl_context()
            connection_kwargs = {
                "decode_responses": True,
            }
            # Only add ssl parameter if SSL context is provided
            if ssl_context is not None:
                connection_kwargs["ssl"] = ssl_context
            redis_client = aioredis.from_url(
                settings.redis_url,
                **connection_kwargs,
            )
            # Test the connection
            await redis_client.ping()
            logger.info("Redis connection established successfully")
        except (redis.exceptions.RedisError, OSError) as e:
            logger.warning(
                f"Failed to connect to Redis: {str(e)}",
                extra={"error_type": type(e).__name__},
            )
            redis_client = None
    return redis_client


def make_cache_key(prefix: str, **kwargs) -> str:
    # Filter out None values to ensure consistent keys
    filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
    param_str = json.dumps(filtered_kwargs, sort_keys=True)
    param_hash = hashlib.md5(param_str.encode()).hexdigest()[:12]
    return f"{prefix}:{param_hash}"


def _json_serializer(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


async def get_cached(key: str) -> Optional[Any]:
    t0 = time.monotonic()
    try:
        client = await get_redis()
        if client is None:
            logger.warning("Redis client is None, cache unavailable")
            _track_cache_fallback("redis_unavailable")
            _cache_metrics.record_miss(key)
            return None
        value = await client.get(key)
        elapsed = time.monotonic() - t0
        _cache_metrics.record_get_latency(elapsed)
        if value:
            _cache_metrics.record_hit(key)
            return json.loads(value)
        _cache_metrics.record_miss(key)
        return None
    except Exception as e:  # noqa: BLE001 - cache-read boundary: must fail open to None on ANY redis-client error (e.g. "Connection pool exhausted"), not just RedisError/JSONDecodeError/OSError -- see test_connection_pool_exhaustion_handling
        elapsed = time.monotonic() - t0
        _cache_metrics.record_get_latency(elapsed)
        _cache_metrics.record_error(key)
        logger.warning(
            f"Cache get error for key {key}: {str(e)}",
            extra={"error_type": type(e).__name__, "key": key},
        )
        _track_cache_fallback(type(e).__name__)
        return None


async def set_cached(key: str, value: Any, ttl_seconds: int = 300) -> None:
    t0 = time.monotonic()
    try:
        client = await get_redis()
        if client is None:
            logger.warning("Redis client is None, cannot cache")
            _track_cache_fallback("redis_unavailable")
            return
        serialized = json.dumps(value, default=_json_serializer)
        await client.setex(key, int(ttl_seconds), serialized)
        elapsed = time.monotonic() - t0
        _cache_metrics.record_set_latency(elapsed)
        _cache_metrics.record_ttl(key, ttl_seconds)
    except Exception as e:  # noqa: BLE001 - cache-write boundary: must fail open (never raise) on ANY error, e.g. Redis OOM ("OOM command not allowed when used memory > 'maxmemory'") -- see test_cache_set_handles_oom_error
        elapsed = time.monotonic() - t0
        _cache_metrics.record_set_latency(elapsed)
        _cache_metrics.record_error(key)
        logger.warning(
            f"Cache set error for key {key}: {str(e)}",
            extra={"error_type": type(e).__name__, "key": key},
        )
        _track_cache_fallback(type(e).__name__)


def _track_cache_fallback(reason: str) -> None:
    try:
        from .metrics import increment
        increment("cache_fallback_total", {"reason": reason})
    except Exception:  # noqa: BLE001  # metrics emission must never affect cache fallback path
        logger.debug("Failed to track cache fallback metric for reason %s", reason)


async def invalidate_cache(pattern: str, _retries: int = 2) -> int:
    import asyncio

    last_error: Exception | None = None
    for attempt in range(_retries + 1):
        try:
            client = await get_redis()
            if client is None:
                return 0
            keys = []
            # Use SCAN to find keys matching pattern (safer than KEYS for large datasets)
            async for key in client.scan_iter(match=pattern, count=100):
                keys.append(key)

            if keys:
                deleted = await client.delete(*keys)
                logger.info("Invalidated %s cache keys matching pattern: %s", deleted, pattern)
                return deleted
            return 0
        except (redis.exceptions.RedisError, OSError) as e:
            last_error = e
            if attempt < _retries:
                await asyncio.sleep(0.25 * (2 ** attempt))  # 0.25s, 0.5s
                continue

    logger.warning(
        "Cache invalidation failed after %s attempts for pattern %s: %s",
        _retries + 1, pattern, str(last_error),
        extra={"error_type": type(last_error).__name__, "pattern": pattern},
    )
    return 0


async def invalidate_catalog_cache() -> int:
    return await invalidate_cache("catalog:*")


# =============================================================================
# Cache Stampede Protection with Distributed Locking
# =============================================================================

# Default lock configuration
DEFAULT_LOCK_TIMEOUT = 30  # seconds
DEFAULT_LOCK_RETRY_DELAY = 0.1  # seconds
DEFAULT_LOCK_MAX_RETRIES = 50

# Early refresh: rebuild cache when remaining TTL drops below this fraction
DEFAULT_EARLY_REFRESH_FRACTION = 0.2  # refresh when 20% TTL remains

# Stale value metadata suffix
_STALE_SUFFIX = ":stale"


@dataclass
class LockMetrics:
    locks_acquired: int = 0
    locks_waited: int = 0
    locks_timed_out: int = 0
    stale_serves: int = 0
    early_refreshes: int = 0
    rebuild_errors: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "locks_acquired": self.locks_acquired,
            "locks_waited": self.locks_waited,
            "locks_timed_out": self.locks_timed_out,
            "stale_serves": self.stale_serves,
            "early_refreshes": self.early_refreshes,
            "rebuild_errors": self.rebuild_errors,
        }


# Global lock metrics
_lock_metrics = LockMetrics()


def get_lock_metrics() -> LockMetrics:
    return _lock_metrics


async def _acquire_lock(
    client: aioredis.Redis,
    lock_key: str,
    lock_timeout: int,
) -> Optional[str]:
    token = str(uuid.uuid4())
    acquired = await client.set(lock_key, token, nx=True, ex=lock_timeout)
    return token if acquired else None


async def _release_lock(
    client: aioredis.Redis,
    lock_key: str,
    token: str,
) -> bool:
    result = await client.eval(_RELEASE_LOCK_SCRIPT, 1, lock_key, token)
    return result == 1


async def _get_with_ttl(key: str) -> tuple[Optional[Any], Optional[int]]:
    try:
        client = await get_redis()
        pipe = client.pipeline(transaction=False)
        pipe.get(key)
        pipe.ttl(key)
        results = await pipe.execute()

        raw_value, ttl = results[0], results[1]
        if raw_value is not None:
            return json.loads(raw_value), max(ttl, 0)
        return None, None
    except Exception as e:  # noqa: BLE001 - cache-read boundary: fail open to (None, None) on ANY error, not just RedisError/JSONDecodeError/OSError (e.g. a bare Exception from get_redis() itself, per test_get_with_ttl_handles_errors)
        logger.warning(
            f"Cache get_with_ttl error for key {key}: {str(e)}",
            extra={"error_type": type(e).__name__, "key": key},
        )
        return None, None


async def _set_stale(key: str, value: Any, stale_ttl: int) -> None:
    try:
        client = await get_redis()
        stale_key = f"{key}{_STALE_SUFFIX}"
        serialized = json.dumps(value, default=_json_serializer)
        await client.setex(stale_key, int(stale_ttl), serialized)
    except (redis.exceptions.RedisError, TypeError, ValueError, OSError) as e:
        logger.debug(
            f"Failed to set stale value for {key}: {str(e)}",
            extra={"error_type": type(e).__name__},
        )


async def _get_stale(key: str) -> Optional[Any]:
    try:
        client = await get_redis()
        stale_key = f"{key}{_STALE_SUFFIX}"
        value = await client.get(stale_key)
        if value:
            return json.loads(value)
        return None
    except (redis.exceptions.RedisError, json.JSONDecodeError, OSError) as e:
        logger.debug(
            f"Failed to get stale value for {key}: {str(e)}",
            extra={"error_type": type(e).__name__},
        )
        return None


async def get_cached_with_lock(
    key: str,
    fetch_func: Callable[[], Any],
    ttl_seconds: int = 300,
    lock_timeout: int = DEFAULT_LOCK_TIMEOUT,
    lock_retry_delay: float = DEFAULT_LOCK_RETRY_DELAY,
    lock_max_retries: int = DEFAULT_LOCK_MAX_RETRIES,
    stale_while_revalidate: bool = True,
    early_refresh_fraction: float = DEFAULT_EARLY_REFRESH_FRACTION,
) -> Optional[Any]:

    # --- Check cache (with early refresh detection) ---
    cached_value, remaining_ttl = await _get_with_ttl(key)
    if cached_value is not None:
        # Check if we should proactively refresh (early refresh)
        ttl_threshold = int(ttl_seconds * early_refresh_fraction)
        if remaining_ttl is not None and remaining_ttl <= ttl_threshold and remaining_ttl > 0:
            # Trigger background refresh - don't block the current request
            _lock_metrics.early_refreshes += 1
            asyncio.ensure_future(
                _background_refresh(key, fetch_func, ttl_seconds, lock_timeout,
                                    stale_while_revalidate)
            )
        return cached_value

    # --- Cache miss - try to acquire lock for rebuild ---
    client = await get_redis()
    lock_key = f"{key}:lock"
    token = await _acquire_lock(client, lock_key, lock_timeout)

    if token is not None:
        # We won the lock - we are the single rebuilder
        _lock_metrics.locks_acquired += 1
        try:
            data = await fetch_func()
            await set_cached(key, data, ttl_seconds)

            # Store a stale copy for future stampede protection
            if stale_while_revalidate:
                await _set_stale(key, data, ttl_seconds * 2)

            return data

        # fetch_func is arbitrary caller-supplied rebuild logic (a DB query,
        # an external API call, ...) -- it can raise anything, not just
        # RedisError/TypeError/ValueError/OSError. The whole point of
        # stale_while_revalidate is to survive that, so this must fail open
        # to "serve stale" rather than propagate (test_stale_served_on_
        # rebuild_error verifies this with a bare Exception("DB down")).
        except Exception as e:  # noqa: BLE001 - fail-open boundary, see above
            _lock_metrics.rebuild_errors += 1
            logger.warning(
                f"Error rebuilding cache for {key}: {str(e)}",
                extra={"error_type": type(e).__name__, "key": key},
            )
            # Try to serve stale if available
            if stale_while_revalidate:
                stale = await _get_stale(key)
                if stale is not None:
                    _lock_metrics.stale_serves += 1
                    return stale
            # Last resort: call fetch_func without caching
            try:
                return await fetch_func()
            except Exception as fetch_error:  # noqa: BLE001 - same rationale as above
                logger.error(
                    f"Failed to fetch data for {key}: {str(fetch_error)}",
                    extra={"error_type": type(fetch_error).__name__},
                )
                return None
        finally:
            try:
                await _release_lock(client, lock_key, token)
            except (redis.exceptions.RedisError, OSError) as e:
                logger.warning(
                    f"Failed to release lock for {key}: {str(e)}",
                    extra={"error_type": type(e).__name__},
                )
    else:
        # Another process holds the lock - wait for cache or serve stale
        _lock_metrics.locks_waited += 1
        logger.debug("Lock not acquired for %s, waiting for cache population", key)

        # Immediately try stale value first
        if stale_while_revalidate:
            stale = await _get_stale(key)
            if stale is not None:
                _lock_metrics.stale_serves += 1
                return stale

        # No stale available - poll for the fresh value
        for _ in range(lock_max_retries):
            await asyncio.sleep(lock_retry_delay)
            cached = await get_cached(key)
            if cached is not None:
                return cached

        # Timed out waiting - generate data ourselves as fallback
        _lock_metrics.locks_timed_out += 1
        logger.warning("Cache still empty after waiting for %s, generating data", key)
        try:
            data = await fetch_func()
            await set_cached(key, data, ttl_seconds)
            return data
        except (redis.exceptions.RedisError, TypeError, ValueError, OSError) as e:
            logger.error(
                f"Fallback fetch failed for {key}: {str(e)}",
                extra={"error_type": type(e).__name__},
            )
            return None


async def _background_refresh(
    key: str,
    fetch_func: Callable[[], Any],
    ttl_seconds: int,
    lock_timeout: int,
    stale_while_revalidate: bool,
) -> None:
    client = await get_redis()
    lock_key = f"{key}:lock"

    token = await _acquire_lock(client, lock_key, lock_timeout)
    if token is None:
        # Another process is already refreshing
        return

    try:
        data = await fetch_func()
        await set_cached(key, data, ttl_seconds)
        if stale_while_revalidate:
            await _set_stale(key, data, ttl_seconds * 2)
        logger.debug("Background refresh completed for %s", key)
    except (redis.exceptions.RedisError, TypeError, ValueError, OSError) as e:
        logger.warning(
            f"Background refresh failed for {key}: {str(e)}",
            extra={"error_type": type(e).__name__},
        )
    finally:
        try:
            await _release_lock(client, lock_key, token)
        except (redis.exceptions.RedisError, OSError) as e:
            logger.debug("Failed to release Redis lock %s: %s", lock_key, e)


# =============================================================================
# Redis Memory Status and Monitoring
# =============================================================================

async def get_memory_status() -> Optional[RedisMemoryStatus]:
    try:
        client = await get_redis()
        info = await client.info("memory")
        stats = await client.info("stats")

        return RedisMemoryStatus(
            used_memory=info.get("used_memory", 0),
            max_memory=info.get("maxmemory", 0),
            used_memory_human=info.get("used_memory_human", "0B"),
            evicted_keys=stats.get("evicted_keys", 0),
            memory_fragmentation_ratio=info.get("mem_fragmentation_ratio", 1.0),
            maxmemory_policy=info.get("maxmemory_policy", "noeviction"),
        )
    except (redis.exceptions.RedisError, OSError) as e:
        logger.warning(
            f"Failed to get Redis memory status: {str(e)}",
            extra={"error_type": type(e).__name__},
        )
        return None


async def check_memory_pressure() -> Dict[str, Any]:
    status = await get_memory_status()

    if status is None:
        return {
            "status": "unknown",
            "usage_percent": None,
            "evicted_keys": None,
            "message": "Unable to retrieve Redis memory status",
        }

    if status.max_memory == 0:
        return {
            "status": "warning",
            "usage_percent": None,
            "evicted_keys": status.evicted_keys,
            "message": "Redis maxmemory not configured (unlimited) - recommend setting limit",
        }

    if status.is_critical:
        return {
            "status": "critical",
            "usage_percent": status.usage_percent,
            "evicted_keys": status.evicted_keys,
            "message": f"Critical: Redis memory at {status.usage_percent:.1f}% ({status.used_memory_human})",
        }

    if status.is_warning:
        return {
            "status": "warning",
            "usage_percent": status.usage_percent,
            "evicted_keys": status.evicted_keys,
            "message": f"Warning: Redis memory at {status.usage_percent:.1f}% ({status.used_memory_human})",
        }

    return {
        "status": "ok",
        "usage_percent": status.usage_percent,
        "evicted_keys": status.evicted_keys,
        "message": f"Redis memory healthy at {status.usage_percent:.1f}% ({status.used_memory_human})",
    }


async def verify_eviction_policy() -> Dict[str, Any]:
    expected_policy = "allkeys-lru"

    try:
        client = await get_redis()
        config = await client.config_get("maxmemory-policy")
        current_policy = config.get("maxmemory-policy", "noeviction")

        is_correct = current_policy == expected_policy

        if is_correct:
            message = f"Eviction policy correctly set to {current_policy}"
        else:
            message = f"Eviction policy mismatch: got '{current_policy}', expected '{expected_policy}'"

        return {
            "configured": is_correct,
            "policy": current_policy,
            "expected": expected_policy,
            "message": message,
        }
    except (redis.exceptions.RedisError, OSError) as e:
        logger.warning(
            f"Failed to verify eviction policy: {str(e)}",
            extra={"error_type": type(e).__name__},
        )
        return {
            "configured": False,
            "policy": None,
            "expected": expected_policy,
            "message": f"Unable to verify eviction policy: {str(e)}",
        }


async def get_cache_stats() -> Dict[str, Any]:
    try:
        client = await get_redis()
        info = await client.info()

        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0.0

        return {
            "connected": True,
            "version": info.get("redis_version", "unknown"),
            "uptime_days": info.get("uptime_in_days", 0),
            "connected_clients": info.get("connected_clients", 0),
            "memory": {
                "used": info.get("used_memory_human", "0B"),
                "used_bytes": info.get("used_memory", 0),
                "max_bytes": info.get("maxmemory", 0),
                "fragmentation_ratio": info.get("mem_fragmentation_ratio", 1.0),
            },
            "keyspace": {
                "hits": hits,
                "misses": misses,
                "hit_rate_percent": round(hit_rate, 2),
            },
            "eviction": {
                "policy": info.get("maxmemory_policy", "noeviction"),
                "evicted_keys": info.get("evicted_keys", 0),
                "expired_keys": info.get("expired_keys", 0),
            },
        }
    except (redis.exceptions.RedisError, OSError) as e:
        logger.warning(
            f"Failed to get cache stats: {str(e)}",
            extra={"error_type": type(e).__name__},
        )
        return {
            "connected": False,
            "error": str(e),
        }
