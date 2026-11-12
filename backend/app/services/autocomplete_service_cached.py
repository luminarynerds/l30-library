# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import time
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cache import (
    get_cached_with_lock,
    make_cache_key,
    invalidate_cache,
)
from ..core.cache_strategies import CacheTTL
from .autocomplete_service_optimized import OptimizedAutocompleteService

logger = get_logger(__name__)

# Cache configuration
AUTOCOMPLETE_CACHE_TTL = CacheTTL.MEDIUM  # 5 minutes
AUTOCOMPLETE_CACHE_PREFIX = "autocomplete"


class CachedAutocompleteService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.inner_service = OptimizedAutocompleteService(db)

    async def autocomplete(
        self,
        query: str,
        limit: int = 10,
        include_authors: bool = True,
        include_gutenberg: bool = True,
        min_similarity: float = 0.2,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        if not use_cache:
            return await self.inner_service.autocomplete(
                query=query,
                limit=limit,
                include_authors=include_authors,
                include_gutenberg=include_gutenberg,
                min_similarity=min_similarity,
            )

        # Build cache key from query parameters
        cache_key = make_cache_key(
            f"{AUTOCOMPLETE_CACHE_PREFIX}:query",
            query=query,
            limit=limit,
            include_authors=include_authors,
            include_gutenberg=include_gutenberg,
            min_similarity=min_similarity,
        )

        start_time = time.time()

        # Fetch with caching and stampede protection
        result = await get_cached_with_lock(
            key=cache_key,
            fetch_func=lambda: self.inner_service.autocomplete(
                query=query,
                limit=limit,
                include_authors=include_authors,
                include_gutenberg=include_gutenberg,
                min_similarity=min_similarity,
            ),
            ttl_seconds=AUTOCOMPLETE_CACHE_TTL,
            stale_while_revalidate=True,
        )

        elapsed_ms = (time.time() - start_time) * 1000

        if result is None:
            logger.warning(f"Autocomplete returned None for query: {query}")
            return {
                "query": query,
                "suggestions": [],
                "search_time_ms": round(elapsed_ms, 2),
                "total_suggestions": 0,
                "strategy": "error",
                "cached": False,
            }

        # Add cache information to result
        result_copy = dict(result)
        result_copy["cached_total_time_ms"] = round(elapsed_ms, 2)

        return result_copy

    async def suggest_titles(
        self,
        query: str,
        limit: int = 10,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        result = await self.autocomplete(
            query=query,
            limit=limit,
            include_authors=False,
            include_gutenberg=False,
            use_cache=use_cache,
        )

        return result.get("suggestions", [])

    async def suggest_with_authors(
        self,
        query: str,
        limit: int = 10,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        result = await self.autocomplete(
            query=query,
            limit=limit,
            include_authors=True,
            include_gutenberg=False,
            use_cache=use_cache,
        )

        return result.get("suggestions", [])

    async def invalidate_cache(self, query: Optional[str] = None) -> int:
        if query:
            # Invalidate specific query
            cache_key = make_cache_key(
                f"{AUTOCOMPLETE_CACHE_PREFIX}:query",
                query=query,
            )
            return await invalidate_cache(cache_key)
        else:
            # Invalidate all autocomplete cache
            return await invalidate_cache(f"{AUTOCOMPLETE_CACHE_PREFIX}:*")


def get_cached_autocomplete_service(
    db: AsyncSession,
) -> CachedAutocompleteService:
    return CachedAutocompleteService(db)
