# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger

from redis.exceptions import RedisError
from typing import Any, Optional

logger = get_logger(__name__)


class SearchCache:

    def __init__(self, redis_client: Optional[Any] = None):
        self.redis = redis_client
        self.enabled = redis_client is not None

        # Cache configuration
        self.ttl_suggestions = 300  # 5 minutes for catalog suggestions
        self.ttl_patron_search = 120  # 2 minutes for patron search
        self.ttl_popular_queries = 3600  # 1 hour for popular queries

    async def get_suggestions(
        self,
        query: str,
        limit: int,
    ) -> Optional[list[dict[str, Any]]]:
        if not self.enabled:
            return None

        try:
            cache_key = self._make_suggestions_key(query, limit)
            cached = await self.redis.get(cache_key)

            if cached:
                logger.debug(f"Cache hit: {cache_key}")
                return json.loads(cached)
        except (RedisError, json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Cache read failed: {e}")
            # Fall through to None return

        return None

    async def set_suggestions(
        self,
        query: str,
        suggestions: list[dict[str, Any]],
        limit: int,
    ) -> bool:
        if not self.enabled:
            return False

        try:
            cache_key = self._make_suggestions_key(query, limit)
            await self.redis.setex(
                cache_key,
                self.ttl_suggestions,
                json.dumps(suggestions),
            )
            logger.debug(f"Cache set: {cache_key} (TTL: {self.ttl_suggestions}s)")
            return True
        except RedisError as e:
            logger.warning(f"Cache write failed: {e}")
            return False

    async def get_patron_search(
        self,
        query: str,
        limit: int,
        offset: int,
    ) -> Optional[dict[str, Any]]:
        if not self.enabled:
            return None

        try:
            cache_key = self._make_patron_search_key(query, limit, offset)
            cached = await self.redis.get(cache_key)

            if cached:
                logger.debug(f"Cache hit: {cache_key}")
                return json.loads(cached)
        except (RedisError, json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Cache read failed: {e}")

        return None

    async def set_patron_search(
        self,
        query: str,
        limit: int,
        offset: int,
        results: dict[str, Any],
    ) -> bool:
        if not self.enabled:
            return False

        try:
            cache_key = self._make_patron_search_key(query, limit, offset)
            await self.redis.setex(
                cache_key,
                self.ttl_patron_search,
                json.dumps(results),
            )
            logger.debug(f"Cache set: {cache_key} (TTL: {self.ttl_patron_search}s)")
            return True
        except RedisError as e:
            logger.warning(f"Cache write failed: {e}")
            return False

    async def invalidate_suggestions(self, pattern: str = "*") -> int:
        if not self.enabled:
            return 0

        try:
            key_pattern = f"suggestions:{pattern}" if not pattern.startswith("*") else pattern
            keys = await self.redis.keys(key_pattern)
            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(f"Invalidated {deleted} suggestion cache keys")
                return deleted
        except RedisError as e:
            logger.warning(f"Cache invalidation failed: {e}")

        return 0

    async def invalidate_patron_search(self) -> int:
        if not self.enabled:
            return 0

        try:
            keys = await self.redis.keys("patron_search:*")
            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(f"Invalidated {deleted} patron search cache keys")
                return deleted
        except RedisError as e:
            logger.warning(f"Cache invalidation failed: {e}")

        return 0

    async def invalidate_all(self) -> int:
        if not self.enabled:
            return 0

        count = await self.invalidate_suggestions()
        count += await self.invalidate_patron_search()
        return count

    async def get_cache_stats(self) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "message": "Cache disabled"}

        try:
            info = await self.redis.info("stats")
            keys_count = await self.redis.dbsize()

            return {
                "enabled": True,
                "keys": keys_count,
                "hit_ratio": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
            }
        except RedisError as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"enabled": True, "error": str(e)}

    # =========================================================================
    # Private helpers
    # =========================================================================

    @staticmethod
    def _make_suggestions_key(query: str, limit: int) -> str:
        return f"suggestions:{query.lower().strip()}:{limit}"

    @staticmethod
    def _make_patron_search_key(query: str, limit: int, offset: int) -> str:
        return f"patron_search:{query.lower().strip()}:{limit}:{offset}"


# Singleton cache instance (initialized on startup)
_cache: Optional[SearchCache] = None


def get_search_cache() -> SearchCache:
    global _cache
    if _cache is None:
        _cache = SearchCache(None)  # No Redis, caching disabled
    return _cache


def init_search_cache(redis_client: Any) -> SearchCache:
    global _cache
    _cache = SearchCache(redis_client)
    logger.info("Search cache initialized with Redis")
    return _cache
