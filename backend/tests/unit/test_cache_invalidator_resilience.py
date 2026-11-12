# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""A Redis hiccup during report-cache invalidation must never propagate.

Cache invalidation is best-effort: if it raised, it would 500 the circulation
operation that triggered it (checkout / renew / return).
"""
from redis.exceptions import RedisError

from app.services.reports import cache_invalidator


class _BoomRedis:
    """Stand-in redis whose scan fails like a real connection hiccup."""

    def scan_iter(self, *args, **kwargs):
        raise RedisError("connection reset")

    async def delete(self, *args, **kwargs):  # pragma: no cover - never reached
        return 0


async def test_scan_failure_does_not_propagate(monkeypatch):
    async def fake_get_redis():
        return _BoomRedis()

    monkeypatch.setattr(cache_invalidator, "get_redis", fake_get_redis)

    # Must not raise; returns the count invalidated so far (0).
    result = await cache_invalidator.invalidate_report_cache("circulation")
    assert result == 0


async def test_redis_unavailable_returns_zero(monkeypatch):
    async def none_get_redis():
        return None

    monkeypatch.setattr(cache_invalidator, "get_redis", none_get_redis)

    assert await cache_invalidator.invalidate_report_cache("circulation") == 0
