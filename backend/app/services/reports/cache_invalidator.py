# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Optional

from redis.exceptions import RedisError

from ...core.cache import get_redis

logger = get_logger(__name__)

# Report type -> Redis key prefix mapping.  Mirrors factory._cache_key().
_REPORT_TYPE_PREFIXES = {
    "circulation": "lsc:report:cache:circulation:*",
    "financial": "lsc:report:cache:financial:*",
    "patron_activity": "lsc:report:cache:patron_activity:*",
    "collection": "lsc:report:cache:collection:*",
    "compliance": "lsc:report:cache:compliance:*",
    "community_outcomes": "lsc:report:cache:community_outcomes:*",
}


async def invalidate_report_cache(report_type: Optional[str] = None) -> int:
    try:
        redis = await get_redis()
    except RedisError:
        logger.debug("Redis unavailable; skipping report cache invalidation")
        return 0

    if redis is None:
        return 0

    if report_type:
        pattern = _REPORT_TYPE_PREFIXES.get(report_type)
        if pattern is None:
            logger.warning("Unknown report type for invalidation: %s", report_type)
            return 0
        patterns = [pattern]
    else:
        patterns = list(_REPORT_TYPE_PREFIXES.values())

    count = 0
    try:
        for pat in patterns:
            async for key in redis.scan_iter(match=pat, count=200):
                await redis.delete(key)
                count += 1
    except (RedisError, OSError, RuntimeError) as exc:
        # Best-effort: a Redis hiccup must never break the circulation operation
        # that triggered this (checkout/renew/return). Stale report cache self-
        # heals on the next write or TTL expiry.
        logger.warning(
            "Report cache invalidation failed (scope=%s): %s",
            report_type or "all", exc,
        )
        return count

    if count:
        scope = report_type or "all"
        logger.info("Invalidated %d report cache keys (scope=%s)", count, scope)
    return count


# Convenience wrappers for common event types.

async def invalidate_circulation_reports() -> int:
    return await invalidate_report_cache("circulation")


async def invalidate_financial_reports() -> int:
    return await invalidate_report_cache("financial")


async def invalidate_patron_reports() -> int:
    return await invalidate_report_cache("patron_activity")


async def invalidate_collection_reports() -> int:
    return await invalidate_report_cache("collection")
