# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = get_logger(__name__)

# Health check endpoints to exclude from tracking
EXCLUDED_ENDPOINTS = {
    "/health",
    "/api/v1/health",
    "/api/v1/health/db",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class EndpointStats:

    __slots__ = ("method", "path", "hit_count", "last_accessed", "status_codes")

    def __init__(self, method: str, path: str) -> None:
        self.method = method
        self.path = path
        self.hit_count = 0
        self.last_accessed: Optional[datetime] = None
        # Track status codes: {code: count}
        self.status_codes: Dict[int, int] = {}

    def record_hit(self, status_code: int) -> None:
        self.hit_count += 1
        self.last_accessed = datetime.now(timezone.utc)
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "path": self.path,
            "hit_count": self.hit_count,
            "last_accessed": (
                self.last_accessed.isoformat() if self.last_accessed else None
            ),
            "status_codes": self.status_codes,
        }


class EndpointTracker:
    """Uses asyncio locks rather than threading.Lock - FastAPI is async, and threading locks
    would block the event loop."""

    MAX_TRACKED_ENDPOINTS = 1000  # Keep last 1000 endpoints for analysis

    def __init__(self) -> None:
        self._stats: Dict[str, EndpointStats] = {}
        self._lock = asyncio.Lock()
        self._startup_time = datetime.now(timezone.utc)
        # LRU tracking: maintain access order for eviction
        self._access_times: Dict[str, float] = {}

    def _cleanup_stale_endpoints(self) -> None:
        if len(self._stats) <= self.MAX_TRACKED_ENDPOINTS:
            return

        # Remove 50% to avoid frequent cleanups
        entries_to_remove = len(self._stats) - int(self.MAX_TRACKED_ENDPOINTS * 0.5)

        # Sort by access time (oldest first) and remove least recently used
        sorted_by_access = sorted(
            self._access_times.items(),
            key=lambda x: x[1]
        )

        for endpoint_key, _ in sorted_by_access[:entries_to_remove]:
            self._stats.pop(endpoint_key, None)
            self._access_times.pop(endpoint_key, None)

    async def record_endpoint(
        self, method: str, path: str, status_code: int
    ) -> None:
        key = f"{method} {path}"

        async with self._lock:
            if key not in self._stats:
                self._stats[key] = EndpointStats(method, path)
            self._stats[key].record_hit(status_code)

            # Update access time for LRU tracking
            self._access_times[key] = time.time()

            # Cleanup if exceeded limit
            if len(self._stats) > self.MAX_TRACKED_ENDPOINTS:
                self._cleanup_stale_endpoints()

    async def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        async with self._lock:
            return {key: stats.to_dict() for key, stats in self._stats.items()}

    async def get_endpoint_stats(self, method: str, path: str) -> Optional[Dict[str, Any]]:
        key = f"{method} {path}"
        async with self._lock:
            stats = self._stats.get(key)
            return stats.to_dict() if stats else None

    async def get_accessed_endpoints(self) -> Dict[str, Dict[str, Any]]:
        all_stats = await self.get_all_stats()
        return {
            key: stats for key, stats in all_stats.items() if stats["hit_count"] > 0
        }

    async def get_orphaned_endpoints(
        self, all_registered_routes: Dict[str, str]
    ) -> Dict[str, str]:
        accessed = await self.get_accessed_endpoints()
        accessed_keys = set(accessed.keys())

        orphaned = {}
        for path, method in all_registered_routes.items():
            key = f"{method} {path}"
            if key not in accessed_keys:
                orphaned[path] = method

        return orphaned

    def get_uptime(self) -> Dict[str, Any]:
        uptime_seconds = (datetime.now(timezone.utc) - self._startup_time).total_seconds()
        return {
            "uptime_seconds": round(uptime_seconds, 2),
            "startup_time": self._startup_time.isoformat(),
        }

    async def clear_stats(self) -> None:
        async with self._lock:
            self._stats.clear()
        self._startup_time = datetime.now(timezone.utc)
        logger.info("Endpoint tracking statistics cleared")


# Global tracker instance
_endpoint_tracker = EndpointTracker()


def get_endpoint_tracker() -> EndpointTracker:
    return _endpoint_tracker


class EndpointTrackerMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.tracker = get_endpoint_tracker()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip tracking for excluded endpoints
        if request.url.path in EXCLUDED_ENDPOINTS:
            return await call_next(request)

        # Process the request
        response = await call_next(request)

        # Record the endpoint hit asynchronously (fire and forget)
        # We don't await this to avoid adding latency to request processing
        asyncio.create_task(
            self.tracker.record_endpoint(
                request.method, request.url.path, response.status_code
            )
        )

        return response
