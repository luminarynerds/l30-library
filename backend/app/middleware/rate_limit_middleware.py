# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import time
from typing import Optional

from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from ..core.rate_limit_config import (
    EndpointCategory,
    CATEGORY_LIMITS,
    READ_METHODS,
    classify_route,
    get_rate_limit,
)
from ..core.in_memory_rate_limiter import InMemoryRateLimiter
from ..core.config import get_settings
from ..core.rate_limit import client_ip

logger = get_logger(__name__)

# Sliding window size in seconds.
WINDOW_SECONDS = 60

# Redis key prefix for rate-limit sorted sets.
_KEY_PREFIX = "rl:cat"

# Paths that are exempt from category-based rate limiting (health checks, etc.)
_EXEMPT_PATHS = frozenset({
    "/health",
    "/api/v1/health",
    "/api/v1/health/db",
    "/status",
    "/docs",
    "/redoc",
    "/openapi.json",
})

# Module-level in-memory fallback, shared across requests within a worker
_settings = get_settings()
_in_memory_fallback = InMemoryRateLimiter(
    fallback_multiplier=_settings.rate_limit_fallback_multiplier
)


def _redis_key(category: EndpointCategory, client_ip: str) -> str:
    return f"{_KEY_PREFIX}:{category.value}:{client_ip}"


class CategoryRateLimitMiddleware(BaseHTTPMiddleware):

    def __init__(self, app, redis_getter=None, enabled: bool = True):
        super().__init__(app)
        self._get_redis = redis_getter
        self._enabled = enabled
        self._fallback_enabled = _settings.rate_limit_fallback_enabled
        self._observe_only = _settings.rate_limit_observe_only
        self._last_warning_time = 0.0

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self._enabled or self._get_redis is None:
            return await call_next(request)

        path = request.url.path

        # Skip exempt paths
        if path in _EXEMPT_PATHS:
            return await call_next(request)

        # Cover images are static-ish assets bounded by valid item IDs. A single
        # catalog grid legitimately fetches dozens at once, which would otherwise
        # exhaust the per-IP CATALOG read budget and 429 normal browsing. Exempt
        # the image-serving GET only; /covers/populate (POST batch) stays limited.
        if request.method == "GET" and path.startswith("/api/v1/catalog/covers/"):
            return await call_next(request)

        # Skip non-API paths (static files, etc.)
        if not path.startswith("/api"):
            return await call_next(request)

        category = classify_route(path)
        method = request.method.upper()
        limit = get_rate_limit(category, method)

        # Determine client IP (respect X-Forwarded-For behind a proxy)
        client_ip = self._get_client_ip(request)
        key = _redis_key(category, client_ip)

        now_ms = int(time.time() * 1000)
        window_ms = WINDOW_SECONDS * 1000

        try:
            redis = await self._get_redis()
            if redis is None:
                raise RedisConnectionError("redis getter returned None")

            # Atomic pipeline: trim old entries, count, add new entry, set TTL
            pipe = redis.pipeline(transaction=True)
            pipe.zremrangebyscore(key, 0, now_ms - window_ms)
            pipe.zcard(key)
            pipe.zadd(key, {str(now_ms): now_ms})
            pipe.expire(key, WINDOW_SECONDS + 1)
            results = await pipe.execute()

            current_count = results[1]  # zcard result

            if current_count >= limit:
                if self._observe_only:
                    logger.warning(
                        "rate_limit would_block (observe-only, not enforced)",
                        extra={"path": path, "category": category.value,
                               "client_ip": client_ip, "count": current_count,
                               "limit": limit, "method": method},
                    )
                    return await call_next(request)
                # Over limit – remove the entry we just added and reject
                await redis.zrem(key, str(now_ms))

                remaining = 0
                retry_after = self._compute_retry_after(now_ms, window_ms, redis, key)

                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": (
                                "You're moving quickly — please slow down a moment and try again."
                            ),
                            "category": category.value,
                            "limit": limit,
                            "window_seconds": WINDOW_SECONDS,
                        }
                    },
                )
                response.headers["Retry-After"] = str(WINDOW_SECONDS)
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Category"] = category.value
                return response

            # Under limit – proceed and attach informational headers
            response = await call_next(request)
            remaining = max(0, limit - current_count - 1)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Category"] = category.value
            return response

        except (RedisError, RedisConnectionError, OSError) as exc:
            # Redis failure – use in-memory fallback if enabled, else allow through
            if self._fallback_enabled:
                return await self._handle_with_fallback(
                    request, call_next, category, client_ip, limit, exc
                )
            else:
                # Legacy behavior: fail open (allow all requests)
                logger.warning(
                    "Rate limit middleware Redis error – allowing request (fallback disabled)",
                    exc_info=True,
                    extra={
                        "path": path,
                        "category": category.value,
                        "error_type": type(exc).__name__,
                    },
                )
                try:
                    from ..core.metrics import increment
                    increment("rate_limit_bypassed_total", {"reason": "redis_unavailable"})
                except Exception:  # noqa: BLE001  # observability metric emit must not break request
                    logger.debug("Failed to emit rate_limit_bypassed metric")
                return await call_next(request)

    # ------------------------------------------------------------------
    # Fallback handler (in-memory rate limiting)
    # ------------------------------------------------------------------

    async def _handle_with_fallback(
        self,
        request: Request,
        call_next,
        category: EndpointCategory,
        client_ip: str,
        limit: int,
        redis_exc: Exception,
    ) -> Response:
        # Log warning once per minute to avoid spam
        now = time.time()
        if _in_memory_fallback.warn_once(now, interval_seconds=60.0):
            logger.warning(
                "Rate limit middleware switched to in-memory fallback",
                exc_info=True,
                extra={
                    "path": request.url.path,
                    "category": category.value,
                    "error_type": type(redis_exc).__name__,
                    "fallback_multiplier": _in_memory_fallback.fallback_multiplier,
                },
            )

        # Build a unique key for this category+IP
        key = f"{category.value}:{client_ip}"

        # Check if request is allowed
        allowed, remaining = _in_memory_fallback.is_allowed(key, limit, WINDOW_SECONDS)

        if not allowed:
            if self._observe_only:
                logger.warning(
                    "rate_limit would_block (observe-only, fallback, not enforced)",
                    extra={"path": request.url.path, "category": category.value,
                           "client_ip": client_ip, "limit": limit},
                )
                return await call_next(request)
            # Over limit – reject with 429
            response = JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": (
                            "You're moving quickly — please slow down a moment and try again."
                        ),
                        "category": category.value,
                        "limit": int(limit * _in_memory_fallback.fallback_multiplier),
                        "window_seconds": WINDOW_SECONDS,
                    }
                },
            )
            response.headers["Retry-After"] = str(WINDOW_SECONDS)
            response.headers["X-RateLimit-Limit"] = str(
                int(limit * _in_memory_fallback.fallback_multiplier)
            )
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Category"] = category.value
            response.headers["X-RateLimit-Backend"] = "memory"

            try:
                from ..core.metrics import increment
                increment("rate_limit_exceeded_total", {
                    "category": category.value,
                    "backend": "memory",
                })
            except Exception:  # noqa: BLE001  # observability metric emit must not break request
                logger.debug("Failed to emit rate_limit_exceeded metric")

            return response

        # Under limit – proceed and attach headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(
            int(limit * _in_memory_fallback.fallback_multiplier)
        )
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Category"] = category.value
        response.headers["X-RateLimit-Backend"] = "memory"

        try:
            from ..core.metrics import increment
            increment("rate_limit_allowed_total", {
                "category": category.value,
                "backend": "memory",
            })
        except Exception:  # noqa: BLE001  # observability metric emit must not break request
            logger.debug("Failed to emit rate_limit_allowed metric")

        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        # Single source of truth: prefer CF-Connecting-IP (the real client),
        # then X-Real-IP, then the socket peer -- never the spoofable
        # X-Forwarded-For. In the two-nginx prod topology X-Real-IP resolves to
        # the docker gateway (a constant), so keying on it alone lumped all
        # traffic under one bucket; CF-Connecting-IP restores per-client keys.
        return client_ip(request)

    @staticmethod
    def _compute_retry_after(
        now_ms: int, window_ms: int, redis, key: str
    ) -> int:
        return WINDOW_SECONDS
