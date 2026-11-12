# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the Redis-backed category rate limit middleware."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.rate_limit_middleware import (
    CategoryRateLimitMiddleware,
    WINDOW_SECONDS,
    _KEY_PREFIX,
    _EXEMPT_PATHS,
    _redis_key,
)
from app.core.rate_limit_config import EndpointCategory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_app(redis_mock=None, enabled=True):
    """Create a minimal FastAPI app with the rate-limit middleware."""
    app = FastAPI()

    async def fake_redis_getter():
        return redis_mock

    app.add_middleware(
        CategoryRateLimitMiddleware,
        redis_getter=fake_redis_getter if redis_mock else None,
        enabled=enabled,
    )

    @app.get("/api/v1/catalog/search")
    async def catalog_search():
        return {"results": []}

    @app.post("/api/v1/auth/login")
    async def login():
        return {"token": "abc"}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/v1/staff/dashboard")
    async def staff_dashboard():
        return {"ok": True}

    @app.get("/docs")
    async def docs():
        return {"swagger": True}

    @app.get("/api/v1/catalog/covers/{item_id}")
    async def cover(item_id: int):
        return {"id": item_id}

    @app.post("/api/v1/catalog/covers/populate")
    async def populate_covers():
        return {"ok": True}

    return app


class FakeRedisPipeline:
    """Fake Redis pipeline that simulates sorted-set operations."""

    def __init__(self, current_count=0):
        self._current_count = current_count
        self._commands = []

    def zremrangebyscore(self, key, min_score, max_score):
        self._commands.append(("zremrangebyscore", key, min_score, max_score))

    def zcard(self, key):
        self._commands.append(("zcard", key))

    def zadd(self, key, mapping):
        self._commands.append(("zadd", key, mapping))

    def expire(self, key, seconds):
        self._commands.append(("expire", key, seconds))

    async def execute(self):
        # Returns: [zremrangebyscore result, zcard result, zadd result, expire result]
        return [0, self._current_count, 1, True]


class FakeRedis:
    """Fake async Redis client for testing."""

    def __init__(self, current_count=0):
        self._current_count = current_count
        self._removed = []

    def pipeline(self, transaction=True):
        return FakeRedisPipeline(self._current_count)

    async def zrem(self, key, *members):
        self._removed.extend(members)
        return len(members)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCategoryRateLimitMiddleware:
    """Tests for the middleware behaviour."""

    @pytest.fixture(autouse=True)
    def _force_enforcing_mode(self):
        """RATE_LIMIT_OBSERVE_ONLY defaults to True (a deliberate rollout
        safety valve -- see app/core/config.py), so without overriding it
        the middleware only logs "would_block" and always calls through,
        which is what was producing 200s where every test in this class
        expects a real 429. Nothing here tests observe-only mode itself,
        so force enforcement for the whole class rather than each test.
        """
        from app.middleware import rate_limit_middleware as rlm

        original = rlm._settings.rate_limit_observe_only
        rlm._settings.rate_limit_observe_only = False
        yield
        rlm._settings.rate_limit_observe_only = original

    def test_allows_requests_under_limit(self):
        redis = FakeRedis(current_count=5)  # Well under any limit
        app = _build_app(redis_mock=redis)
        client = TestClient(app)

        response = client.get("/api/v1/catalog/search")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Category" in response.headers
        assert response.headers["X-RateLimit-Category"] == "catalog"

    def test_blocks_requests_over_limit(self):
        # Catalog read limit is 60/min; simulate being at the limit
        redis = FakeRedis(current_count=60)
        app = _build_app(redis_mock=redis)
        client = TestClient(app)

        response = client.get("/api/v1/catalog/search")
        assert response.status_code == 429
        body = response.json()
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"

    def test_auth_write_limit_is_tighter(self):
        # Auth write limit is 10/min
        redis = FakeRedis(current_count=10)
        app = _build_app(redis_mock=redis)
        client = TestClient(app)

        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 429

    def test_exempt_paths_bypass_rate_limit(self):
        redis = FakeRedis(current_count=999)  # Way over any limit
        app = _build_app(redis_mock=redis)
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200

    def test_docs_path_exempt(self):
        redis = FakeRedis(current_count=999)
        app = _build_app(redis_mock=redis)
        client = TestClient(app)

        response = client.get("/docs")
        assert response.status_code == 200

    def test_cover_image_get_is_exempt(self):
        """Cover-image GETs are static assets; a grid fetches dozens, so they
        must not count against the CATALOG read budget."""
        redis = FakeRedis(current_count=999)  # Way over the catalog limit
        app = _build_app(redis_mock=redis)
        client = TestClient(app)

        response = client.get("/api/v1/catalog/covers/1925")
        assert response.status_code == 200

    def test_cover_populate_post_still_limited(self):
        """The cover batch-populate write stays rate-limited (only the
        image-serving GET is exempt)."""
        redis = FakeRedis(current_count=999)
        app = _build_app(redis_mock=redis)
        client = TestClient(app)

        response = client.post("/api/v1/catalog/covers/populate")
        assert response.status_code == 429

    def test_non_api_paths_bypass(self):
        """Non-/api paths should skip rate limiting."""
        redis = FakeRedis(current_count=999)
        app = _build_app(redis_mock=redis)

        @app.get("/static/file.js")
        async def static_file():
            return {"file": "content"}

        client = TestClient(app)
        response = client.get("/static/file.js")
        assert response.status_code == 200

    def test_disabled_middleware_is_noop(self):
        redis = FakeRedis(current_count=999)
        app = _build_app(redis_mock=redis, enabled=False)
        client = TestClient(app)

        response = client.get("/api/v1/catalog/search")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers

    def test_no_redis_getter_is_noop(self):
        app = _build_app(redis_mock=None, enabled=True)
        client = TestClient(app)

        response = client.get("/api/v1/catalog/search")
        assert response.status_code == 200

    def test_redis_error_degrades_gracefully(self):
        """If Redis raises an exception, the request should still go through."""

        class BrokenRedis:
            def pipeline(self, transaction=True):
                raise ConnectionError("Redis is down")

        app = _build_app(redis_mock=BrokenRedis())
        client = TestClient(app)

        response = client.get("/api/v1/catalog/search")
        assert response.status_code == 200
        # The middleware now degrades to an in-memory fallback limiter
        # (InMemoryRateLimiter) instead of skipping rate-limit headers
        # entirely when Redis errors -- it still reports limit/remaining,
        # just tagged with X-RateLimit-Backend: memory so it's visible
        # this is a degraded read, not silently absent.
        assert response.headers.get("X-RateLimit-Backend") == "memory"

    def test_staff_gets_higher_read_limit(self):
        """Staff endpoints should have 120/min read limit."""
        # At count 100, should still be under 120 limit
        redis = FakeRedis(current_count=100)
        app = _build_app(redis_mock=redis)
        client = TestClient(app)

        response = client.get("/api/v1/staff/dashboard")
        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "120"

    def test_rate_limit_headers_present(self):
        redis = FakeRedis(current_count=5)
        app = _build_app(redis_mock=redis)
        client = TestClient(app)

        response = client.get("/api/v1/catalog/search")
        assert response.headers["X-RateLimit-Limit"] == "60"
        assert int(response.headers["X-RateLimit-Remaining"]) == 54  # 60 - 5 - 1
        assert response.headers["X-RateLimit-Category"] == "catalog"

    def test_429_response_includes_category(self):
        redis = FakeRedis(current_count=60)
        app = _build_app(redis_mock=redis)
        client = TestClient(app)

        response = client.get("/api/v1/catalog/search")
        body = response.json()
        assert body["error"]["category"] == "catalog"
        assert body["error"]["limit"] == 60
        assert body["error"]["window_seconds"] == WINDOW_SECONDS


class TestRedisKey:
    def test_key_format(self):
        key = _redis_key(EndpointCategory.CATALOG, "192.168.1.1")
        assert key == f"{_KEY_PREFIX}:catalog:192.168.1.1"

    def test_different_categories_different_keys(self):
        k1 = _redis_key(EndpointCategory.AUTH, "1.2.3.4")
        k2 = _redis_key(EndpointCategory.CATALOG, "1.2.3.4")
        assert k1 != k2

    def test_different_ips_different_keys(self):
        k1 = _redis_key(EndpointCategory.AUTH, "1.2.3.4")
        k2 = _redis_key(EndpointCategory.AUTH, "5.6.7.8")
        assert k1 != k2


class TestExemptPaths:
    def test_health_is_exempt(self):
        assert "/health" in _EXEMPT_PATHS

    def test_docs_is_exempt(self):
        assert "/docs" in _EXEMPT_PATHS

    def test_openapi_is_exempt(self):
        assert "/openapi.json" in _EXEMPT_PATHS


class TestClientIpExtraction:
    """Test the X-Forwarded-For header handling."""

    def test_x_forwarded_for_uses_first_ip(self):
        redis = FakeRedis(current_count=0)
        app = _build_app(redis_mock=redis)
        client = TestClient(app)

        response = client.get(
            "/api/v1/catalog/search",
            headers={"X-Forwarded-For": "10.0.0.1, 10.0.0.2, 10.0.0.3"},
        )
        assert response.status_code == 200
