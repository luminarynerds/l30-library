# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Any, Callable, List, Optional

from .cache import get_cached, set_cached, invalidate_cache, make_cache_key  # noqa: F401

logger = get_logger(__name__)

DASHBOARD_PREFIX = "dashboard"


async def get_cached_or_compute(
    key: str,
    ttl: int,
    compute_fn: Callable[[], Any],
) -> Any:
    cached = await get_cached(key)
    if cached is not None:
        return cached

    result = await compute_fn()

    # Pydantic models need to be serialised to dicts for JSON storage
    serializable = _to_serializable(result)
    await set_cached(key, serializable, ttl_seconds=ttl)
    return result


async def invalidate_dashboard_cache(patterns: List[str]) -> int:
    total = 0
    for pattern in patterns:
        full_pattern = f"{DASHBOARD_PREFIX}:{pattern}" if not pattern.startswith(DASHBOARD_PREFIX) else pattern
        total += await invalidate_cache(full_pattern)
    return total


def _to_serializable(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "dict"):  # Pydantic v1 fallback
        return obj.dict()
    if isinstance(obj, list):
        return [_to_serializable(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    return obj
