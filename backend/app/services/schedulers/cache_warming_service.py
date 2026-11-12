# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from ...core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CacheRefreshResult:
    cache_name: str
    success: bool
    duration_ms: float = 0.0
    error: str = ""


@dataclass
class CacheRefreshStatus:
    results: List[CacheRefreshResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


async def refresh_caches() -> CacheRefreshStatus:
    start = datetime.now(timezone.utc)
    logger.debug("Cache refresh: no caches configured, skipping")
    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
    return CacheRefreshStatus(
        results=[],
        total_duration_ms=elapsed,
        started_at=start,
    )
