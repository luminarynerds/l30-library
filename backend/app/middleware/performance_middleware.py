# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import time
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..core.performance_monitoring import get_monitor

logger = logging.getLogger("app")

# Endpoints to skip monitoring (health checks, metrics endpoints)
SKIP_MONITORING_PATHS = {
    "/health",
    "/api/v1/health",
    "/api/v1/health/db",
    "/metrics",
    "/api/v1/metrics",
}


class PerformanceMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip monitoring for certain paths
        if request.url.path in SKIP_MONITORING_PATHS:
            return await call_next(request)

        # Record start time
        start_time = time.perf_counter()

        # Get endpoint path and method
        endpoint = request.url.path
        method = request.method

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error = status_code >= 400

        except Exception as exc:
            # Record as error - catches all exceptions for performance tracking
            # This is intentionally broad to track metrics for all request failures
            duration_ms = (time.perf_counter() - start_time) * 1000
            monitor = get_monitor()
            monitor.record_endpoint_call(
                endpoint=endpoint,
                method=method,
                duration_ms=duration_ms,
                status_code=500,
                error=True,
            )
            # Log the error type for better debugging
            logger.debug(
                f"Request error in performance tracking: {type(exc).__name__}",
                extra={"endpoint": endpoint, "method": method, "error_type": type(exc).__name__},
            )
            raise

        # Record metrics
        duration_ms = (time.perf_counter() - start_time) * 1000
        monitor = get_monitor()
        monitor.record_endpoint_call(
            endpoint=endpoint,
            method=method,
            duration_ms=duration_ms,
            status_code=status_code,
            error=error,
        )

        return response
