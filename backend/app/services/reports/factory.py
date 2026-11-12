# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import hashlib
import json
from app.core.logging import get_logger
import uuid
from enum import StrEnum
from typing import Any, Dict, Optional, Type

import redis.asyncio as aioredis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from .base import (
    OutputFormat,
    ReportBuilder,
    ReportFilters,
    ReportProgress,
    ReportResult,
)
from .builders import (
    CirculationReportBuilder,
    CollectionReportBuilder,
    ComplianceReportBuilder,
    FinancialReportBuilder,
    PatronActivityReportBuilder,
    CommunityOutcomesReportBuilder,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Report type registry
# ---------------------------------------------------------------------------

class ReportType(StrEnum):
    CIRCULATION = "circulation"
    FINANCIAL = "financial"
    PATRON_ACTIVITY = "patron_activity"
    COLLECTION = "collection"
    COMPLIANCE = "compliance"
    COMMUNITY_OUTCOMES = "community_outcomes"


_BUILDER_REGISTRY: Dict[ReportType, Type[ReportBuilder]] = {
    ReportType.CIRCULATION: CirculationReportBuilder,
    ReportType.FINANCIAL: FinancialReportBuilder,
    ReportType.PATRON_ACTIVITY: PatronActivityReportBuilder,
    ReportType.COLLECTION: CollectionReportBuilder,
    ReportType.COMPLIANCE: ComplianceReportBuilder,
    ReportType.COMMUNITY_OUTCOMES: CommunityOutcomesReportBuilder,
}


# ---------------------------------------------------------------------------
# Default TTLs per report type (seconds)
# ---------------------------------------------------------------------------

DEFAULT_CACHE_TTL: Dict[ReportType, int] = {
    ReportType.CIRCULATION: 300,       # 5 min  - semi-volatile
    ReportType.FINANCIAL: 300,         # 5 min  - matches existing cache
    ReportType.PATRON_ACTIVITY: 600,   # 10 min - moderate volatility
    ReportType.COLLECTION: 900,        # 15 min - changes infrequently
    ReportType.COMPLIANCE: 14400,      # 4 hr   - annual data
    ReportType.COMMUNITY_OUTCOMES: 600,   # 10 min - community metrics
}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class ReportFactory:

    def __init__(
        self,
        db: AsyncSession,
        redis: Optional[aioredis.Redis] = None,
    ):
        self.db = db
        self.redis = redis
        self._progress: Dict[str, ReportProgress] = {}

    # -- public API --------------------------------------------------------

    def get_builder(self, report_type: ReportType) -> ReportBuilder:
        builder_cls = _BUILDER_REGISTRY.get(report_type)
        if builder_cls is None:
            raise ValueError(f"Unknown report type: {report_type}")
        return builder_cls(self.db)

    async def generate(
        self,
        report_type: ReportType,
        filters: ReportFilters,
        output: OutputFormat = OutputFormat.JSON,
        *,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
    ) -> bytes:
        data, _ = await self.generate_with_meta(
            report_type, filters, output, use_cache=use_cache, cache_ttl=cache_ttl
        )
        return data

    async def generate_with_meta(
        self,
        report_type: ReportType,
        filters: ReportFilters,
        output: OutputFormat = OutputFormat.JSON,
        *,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
    ) -> tuple[bytes, bool]:
        cache_key = self._cache_key(report_type, filters, output)

        if use_cache and self.redis:
            cached = await self._cache_get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for %s", cache_key)
                return cached, True

        builder = self.get_builder(report_type)
        result = await builder.generate(filters, output)

        if use_cache and self.redis:
            ttl = cache_ttl or DEFAULT_CACHE_TTL.get(report_type, 300)
            await self._cache_set(cache_key, result, ttl)

        return result, False

    async def generate_async(
        self,
        report_type: ReportType,
        filters: ReportFilters,
        output: OutputFormat = OutputFormat.JSON,
        *,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
    ) -> str:
        report_id = str(uuid.uuid4())
        progress = ReportProgress(report_id=report_id)
        self._progress[report_id] = progress

        # Store progress in Redis for distributed access
        if self.redis:
            await self.redis.setex(
                f"lsc:report:progress:{report_id}",
                3600,
                json.dumps(progress.to_dict()),
            )

        asyncio.create_task(
            self._run_async(report_id, report_type, filters, output, use_cache, cache_ttl)
        )

        return report_id

    async def get_progress(self, report_id: str) -> Optional[Dict[str, Any]]:
        # Check in-memory first
        if report_id in self._progress:
            return self._progress[report_id].to_dict()

        # Fall back to Redis
        if self.redis:
            data = await self.redis.get(f"lsc:report:progress:{report_id}")
            if data:
                return json.loads(data)

        return None

    async def get_async_result(self, report_id: str) -> Optional[bytes]:
        if self.redis:
            data = await self.redis.get(f"lsc:report:result:{report_id}")
            if data is None:
                return None
            if isinstance(data, str):
                import base64
                return base64.b64decode(data)
            return data
        return None

    async def invalidate_cache(
        self,
        report_type: Optional[ReportType] = None,
    ) -> int:
        if not self.redis:
            return 0

        if report_type:
            pattern = f"lsc:report:cache:{report_type.value}:*"
        else:
            pattern = "lsc:report:cache:*"

        count = 0
        async for key in self.redis.scan_iter(match=pattern, count=200):
            await self.redis.delete(key)
            count += 1

        logger.info("Invalidated %d cached reports (pattern=%s)", count, pattern)
        return count

    # -- internal ----------------------------------------------------------

    async def _run_async(
        self,
        report_id: str,
        report_type: ReportType,
        filters: ReportFilters,
        output: OutputFormat,
        use_cache: bool,
        cache_ttl: Optional[int],
    ):
        progress = self._progress.get(report_id)
        try:
            if progress:
                progress.status = "running"
                progress.total_steps = 3
                await self._sync_progress(report_id, progress)

            builder = self.get_builder(report_type)

            # Phase 1: query
            if progress:
                progress.advance("Querying data")
                await self._sync_progress(report_id, progress)
            raw = await builder.query_data(filters)

            # Phase 2: aggregate
            if progress:
                progress.advance("Aggregating results")
                await self._sync_progress(report_id, progress)
            result = await builder.aggregate(raw, filters)

            # Phase 3: format
            if progress:
                progress.advance("Formatting output")
                await self._sync_progress(report_id, progress)
            formatted = builder.format(result, output)

            # Store result
            if self.redis:
                import base64
                encoded = base64.b64encode(formatted).decode("ascii")
                await self.redis.setex(
                    f"lsc:report:result:{report_id}",
                    3600,
                    encoded,
                )

            # Also cache for reuse
            if use_cache and self.redis:
                cache_key = self._cache_key(report_type, filters, output)
                ttl = cache_ttl or DEFAULT_CACHE_TTL.get(report_type, 300)
                await self._cache_set(cache_key, formatted, ttl)

            if progress:
                progress.status = "completed"
                await self._sync_progress(report_id, progress)

        except Exception as exc:
            logger.error("Async report %s failed: %s", report_id, exc, exc_info=True)
            if progress:
                progress.status = "failed"
                progress.error = str(exc)
                await self._sync_progress(report_id, progress)

    async def _sync_progress(self, report_id: str, progress: ReportProgress):
        if self.redis:
            await self.redis.setex(
                f"lsc:report:progress:{report_id}",
                3600,
                json.dumps(progress.to_dict()),
            )

    # -- cache helpers -----------------------------------------------------

    def _cache_key(
        self,
        report_type: ReportType,
        filters: ReportFilters,
        output: OutputFormat,
    ) -> str:
        raw = f"{report_type.value}|{output.value}|{filters.cache_key_fragment}"
        digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return f"lsc:report:cache:{report_type.value}:{digest}"

    async def _cache_get(self, key: str) -> Optional[bytes]:
        try:
            data = await self.redis.get(key)
            if data is None:
                return None
            # Redis with decode_responses=True returns str; convert back
            if isinstance(data, str):
                import base64
                return base64.b64decode(data)
            return data
        except RedisError as exc:
            logger.warning("Redis cache get failed: %s", exc)
            return None

    async def _cache_set(self, key: str, value: bytes, ttl: int):
        try:
            # Redis with decode_responses=True needs str; base64 encode bytes
            import base64
            encoded = base64.b64encode(value).decode("ascii")
            await self.redis.setex(key, ttl, encoded)
        except RedisError as exc:
            logger.warning("Redis cache set failed: %s", exc)
