# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
import time
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from .cache import SearchCache, get_search_cache
from .search_service import PostgresSearchService

logger = get_logger(__name__)


class CachedPostgresSearchService(PostgresSearchService):

    def __init__(self, db: AsyncSession, cache: Optional[SearchCache] = None):
        super().__init__(db)
        self._cache = cache or get_search_cache()

    async def suggest(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if not query or len(query) < 2:
            return []

        # Step 1: Check cache
        cached_result = await self._cache.get_suggestions(query, limit)
        if cached_result:
            logger.info(f"Cache hit for suggestions: {query} (limit={limit})")
            return cached_result

        # Step 2: Query database
        start_time = time.time()
        suggestions = await super().suggest(query, limit)
        elapsed_ms = (time.time() - start_time) * 1000

        # Step 3: Cache result for future requests
        await self._cache.set_suggestions(query, suggestions, limit)

        logger.info(
            f"Suggestion query: {query} ({len(suggestions)} results, "
            f"{elapsed_ms:.2f}ms, cache miss)"
        )

        return suggestions

    async def search(
        self,
        query: str,
        *,
        item_type: Optional[str] = None,
        status: Optional[str] = None,
        language: Optional[str] = None,
        available_only: bool = False,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        location: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        include_facets: bool = True,
        hybrid: bool = False,
        semantic_weight: float = 0.4,
    ):
        # For now, full search results are delegated to parent class
        # They could be cached if needed, with appropriate key structure
        # e.g., cache_key = f"search:{query}:{item_type}:{page}:{per_page}"

        return await super().search(
            query,
            item_type=item_type,
            status=status,
            language=language,
            available_only=available_only,
            year_min=year_min,
            year_max=year_max,
            location=location,
            page=page,
            per_page=per_page,
            include_facets=include_facets,
            hybrid=hybrid,
            semantic_weight=semantic_weight,
        )

    async def clear_cache(self):
        count = await self._cache.invalidate_all()
        logger.info(f"Cleared {count} cache entries")
        return count

    async def get_cache_stats(self) -> dict[str, Any]:
        return await self._cache.get_cache_stats()


# Factory function for dependency injection
def get_cached_search_service(
    db: AsyncSession,
    cache: Optional[SearchCache] = None,
) -> CachedPostgresSearchService:
    return CachedPostgresSearchService(db, cache)
