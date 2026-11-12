# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cache dashboard admin endpoints.

Provides visibility into Redis cache hit/miss rates, active keys,
memory usage, and manual eviction for administrators.

All endpoints require admin role authentication.
"""

from app.core.logging import get_logger
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.cache import (
    get_cache_metrics,
    get_cache_stats,
    get_memory_status,
    get_redis,
    invalidate_cache,
)
from ...core.database import get_db
from ...models.user import User
from .auth import get_current_user
from .dependencies import require_admin

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/cache", tags=["admin", "cache"])




# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class CacheStatsResponse(BaseModel):
    redis_stats: Dict[str, Any] = Field(
        ..., description="Global Redis statistics (hit rate, memory, eviction)"
    )
    app_metrics: Dict[str, Any] = Field(
        ..., description="Application-level cache metrics per prefix"
    )


class CacheKeyInfo(BaseModel):
    key: str
    ttl_seconds: int = Field(..., description="Remaining TTL in seconds (-1 = no expiry, -2 = key gone)")
    type: str = Field("string", description="Redis key type")


class CacheKeysResponse(BaseModel):
    keys: List[CacheKeyInfo]
    cursor: int = Field(0, description="Cursor for next page (0 = end)")
    total_scanned: int = Field(0, description="Number of keys scanned in this page")


class EvictRequest(BaseModel):
    pattern: str = Field(
        ...,
        description="Key or glob pattern to evict (e.g. 'catalog:*' or exact key name)",
        min_length=1,
    )


class EvictResponse(BaseModel):
    deleted: int = Field(..., description="Number of keys deleted")
    pattern: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=CacheStatsResponse)
async def cache_stats(
    current_user: User = Depends(require_admin),
) -> CacheStatsResponse:
    """Return cache hit/miss rates, top key prefixes, and memory usage.

    Combines Redis INFO data with the application-level CacheMetrics
    (per-prefix hit/miss counts, latency, TTL distribution).
    """
    redis_stats = await get_cache_stats()
    app_metrics = get_cache_metrics()

    return CacheStatsResponse(redis_stats=redis_stats, app_metrics=app_metrics)


@router.get("/keys", response_model=CacheKeysResponse)
async def cache_keys(
    current_user: User = Depends(require_admin),
    cursor: int = Query(0, ge=0, description="SCAN cursor for pagination"),
    count: int = Query(100, ge=1, le=1000, description="Approximate keys per page"),
    match: str = Query("*", description="Glob pattern to filter keys"),
) -> CacheKeysResponse:
    """Return a paginated list of active cache keys with their remaining TTL.

    Uses Redis SCAN for safe iteration.  The *cursor* value from the response
    should be passed back to fetch the next page.  When cursor is ``0`` in the
    response, iteration is complete.
    """
    client = await get_redis()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis unavailable",
        )

    new_cursor, raw_keys = await client.scan(cursor=cursor, match=match, count=count)

    keys_info: List[CacheKeyInfo] = []
    if raw_keys:
        # Pipeline TTL + TYPE lookups for efficiency
        pipe = client.pipeline(transaction=False)
        for k in raw_keys:
            pipe.ttl(k)
            pipe.type(k)
        results = await pipe.execute()

        for i, k in enumerate(raw_keys):
            ttl_val = results[i * 2]
            type_val = results[i * 2 + 1]
            keys_info.append(
                CacheKeyInfo(
                    key=k,
                    ttl_seconds=ttl_val,
                    type=type_val if isinstance(type_val, str) else "unknown",
                )
            )

    return CacheKeysResponse(
        keys=keys_info,
        cursor=new_cursor,
        total_scanned=len(raw_keys),
    )


@router.post("/evict", response_model=EvictResponse)
async def cache_evict(
    body: EvictRequest,
    current_user: User = Depends(require_admin),
) -> EvictResponse:
    """Manually evict a cache key or keys matching a glob pattern.

    Examples:
        - ``{"pattern": "catalog:search:*"}`` — evict all catalog search keys
        - ``{"pattern": "patron:abc123"}`` — evict a single key
    """
    deleted = await invalidate_cache(body.pattern)
    logger.info(
        "Admin cache eviction",
        extra={
            "admin_user_id": current_user.id,
            "pattern": body.pattern,
            "deleted": deleted,
        },
    )
    return EvictResponse(deleted=deleted, pattern=body.pattern)
