# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional
from collections import deque, defaultdict

import sentry_sdk
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("app")

# HTTP 405 Method Not Allowed error tracking - thread-safe circular buffer
class HTTP405Tracker:

    MAX_EVENTS = 10000  # Keep last 10k 405 events for analysis
    MAX_STATS_ENTRIES = 5000  # Maximum entries in endpoint_errors and client_errors dicts
    ALERT_THRESHOLD = 50  # Alert when 50+ 405s in 1 hour

    def __init__(self):
        # Circular buffer of 405 errors: (timestamp, method, path, client_ip, user_agent, user_id)
        self.events: deque = deque(maxlen=self.MAX_EVENTS)
        # Track errors by endpoint for trend analysis (now bounded with LRU)
        self.endpoint_errors = defaultdict(int)
        # Track errors by client IP for pattern detection (now bounded with LRU)
        self.client_errors = defaultdict(int)
        # LRU tracking: maintain access order for eviction
        self._endpoint_access_times = {}
        self._client_access_times = {}

    def _cleanup_endpoint_stats(self) -> None:
        if len(self.endpoint_errors) <= self.MAX_STATS_ENTRIES:
            return

        # Remove 10% to avoid frequent cleanups
        entries_to_remove = len(self.endpoint_errors) - int(self.MAX_STATS_ENTRIES * 0.9)

        # Sort by access time (oldest first) and remove least recently used
        sorted_by_access = sorted(
            self._endpoint_access_times.items(),
            key=lambda x: x[1]
        )

        for endpoint_key, _ in sorted_by_access[:entries_to_remove]:
            self.endpoint_errors.pop(endpoint_key, None)
            self._endpoint_access_times.pop(endpoint_key, None)

    def _cleanup_client_stats(self) -> None:
        if len(self.client_errors) <= self.MAX_STATS_ENTRIES:
            return

        # Remove 10% to avoid frequent cleanups
        entries_to_remove = len(self.client_errors) - int(self.MAX_STATS_ENTRIES * 0.9)

        # Sort by access time (oldest first) and remove least recently used
        sorted_by_access = sorted(
            self._client_access_times.items(),
            key=lambda x: x[1]
        )

        for client_ip, _ in sorted_by_access[:entries_to_remove]:
            self.client_errors.pop(client_ip, None)
            self._client_access_times.pop(client_ip, None)

    def record_405(
        self,
        method: str,
        path: str,
        client_ip: Optional[str],
        user_agent: str,
        user_id: Optional[int] = None,
        query_params: Optional[dict] = None,
    ) -> None:
        import time
        timestamp = datetime.now(timezone.utc)
        endpoint_key = f"{method} {path}"

        event = {
            "timestamp": timestamp,
            "method": method,
            "path": path,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "user_id": user_id,
            "query_params": query_params or {},
        }

        self.events.append(event)

        # Update endpoint statistics and track access time for LRU
        self.endpoint_errors[endpoint_key] += 1
        self._endpoint_access_times[endpoint_key] = time.time()

        # Cleanup if exceeded limit
        if len(self.endpoint_errors) > self.MAX_STATS_ENTRIES:
            self._cleanup_endpoint_stats()

        # Update client statistics and track access time for LRU
        if client_ip:
            self.client_errors[client_ip] += 1
            self._client_access_times[client_ip] = time.time()

            # Cleanup if exceeded limit
            if len(self.client_errors) > self.MAX_STATS_ENTRIES:
                self._cleanup_client_stats()

    def get_errors_last_24h(self) -> list:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        return [e for e in self.events if e["timestamp"] >= cutoff]

    def get_errors_last_hour(self) -> list:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        return [e for e in self.events if e["timestamp"] >= cutoff]

    def get_top_endpoints(self, limit: int = 10) -> list:
        import time
        current_time = time.time()

        sorted_endpoints = sorted(
            self.endpoint_errors.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Update access times for returned endpoints (they're being actively used)
        for endpoint, _ in sorted_endpoints[:limit]:
            self._endpoint_access_times[endpoint] = current_time

        return [
            {"endpoint": ep, "count": count}
            for ep, count in sorted_endpoints[:limit]
        ]

    def get_top_clients(self, limit: int = 10) -> list:
        import time
        current_time = time.time()

        sorted_clients = sorted(
            self.client_errors.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Update access times for returned clients (they're being actively used)
        for client_ip, _ in sorted_clients[:limit]:
            self._client_access_times[client_ip] = current_time

        return [
            {"client_ip": ip, "count": count}
            for ip, count in sorted_clients[:limit]
        ]

    def get_error_trend(self, hours: int = 24, bucket_minutes: int = 60) -> dict:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)

        # Initialize buckets
        buckets = {}
        bucket_count = (hours * 60) // bucket_minutes
        for i in range(bucket_count):
            bucket_time = now - timedelta(minutes=bucket_minutes * (bucket_count - i - 1))
            bucket_key = bucket_time.strftime("%Y-%m-%d %H:%M")
            buckets[bucket_key] = 0

        # Count errors in each bucket
        for event in self.events:
            if event["timestamp"] >= cutoff:
                bucket_time = event["timestamp"] - timedelta(
                    minutes=event["timestamp"].minute % bucket_minutes,
                    seconds=event["timestamp"].second,
                    microseconds=event["timestamp"].microsecond
                )
                bucket_key = bucket_time.strftime("%Y-%m-%d %H:%M")
                if bucket_key in buckets:
                    buckets[bucket_key] += 1

        return buckets

    def should_alert(self) -> tuple[bool, int, int]:
        errors_last_hour = self.get_errors_last_hour()
        count = len(errors_last_hour)
        should_alert = count >= self.ALERT_THRESHOLD
        return should_alert, count, self.ALERT_THRESHOLD

# Global 405 error tracker
_405_tracker = HTTP405Tracker()

def get_405_tracker() -> HTTP405Tracker:
    return _405_tracker

# Fields that should never be logged - covers common variations
SENSITIVE_FIELDS = {
    # Authentication & passwords
    "password",
    "new_password",
    "current_password",
    "old_password",
    "password_hash",
    "hashed_password",
    # Tokens
    "token",
    "access_token",
    "refresh_token",
    "reset_token",
    "verification_token",
    "auth_token",
    "bearer",
    "jwt",
    # API keys & secrets
    "secret",
    "secret_key",
    "api_key",
    "apikey",
    "private_key",
    # Headers that may contain auth
    "authorization",
    "x-api-key",
    # Sensitive PII
    "credit_card",
    "card_number",
    "cvv",
    "ssn",
    "social_security",
    # Note: email intentionally excluded - useful for debugging
    # and not as sensitive as passwords/tokens
}

# Query parameter names that might contain sensitive data
SENSITIVE_QUERY_PARAMS = {
    "token",
    "access_token",
    "refresh_token",
    "reset_token",
    "verification_token",
    "key",
    "api_key",
    "apikey",
    "secret",
    "password",
    "code",  # OAuth codes
}


class RequestLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for health checks
        if request.url.path in ["/health", "/api/v1/health"]:
            return await call_next(request)

        # Extract request information - generate request ID if not provided
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        # Expose request_id to downstream handlers (exception handlers, services)
        # via request.state so error envelopes can surface it even when the
        # client didn't send X-Request-ID.
        request.state.request_id = request_id
        method = request.method
        path = request.url.path

        # Mask sensitive query parameters
        query_params = mask_query_params(dict(request.query_params))

        # Set Sentry context for correlation
        sentry_sdk.set_tag("request_id", request_id)
        sentry_sdk.set_context("request", {
            "request_id": request_id,
            "method": method,
            "path": path,
        })

        # Record start time
        start_time = time.time()

        # Get request body if present
        body = None
        original_body = None
        # Skip body reading for auth endpoints to avoid middleware conflicts
        if method in ["POST", "PUT", "PATCH"] and "/auth/login" not in path and "/auth/register" not in path:
            try:
                original_body = await request.body()
                body = original_body
                # Mask sensitive fields for logging only
                if body:
                    try:
                        body_data = json.loads(body)
                        body_data = mask_sensitive_data(body_data)
                        body = json.dumps(body_data).encode()
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        body = b"[binary data]"
            except (IOError, OSError, ValueError) as e:
                logger.warning(
                    f"Failed to read request body: {e}",
                    extra={
                        "error_type": type(e).__name__,
                        "method": method,
                        "path": path,
                    },
                )
                body = b"[unable to read body]"

            # Re-attach original body for actual processing
            body_sent = False
            async def receive():
                nonlocal body_sent
                if not body_sent:
                    body_sent = True
                    return {"type": "http.request", "body": original_body or b""}
                return {"type": "http.disconnect"}

            request._receive = receive

        # Log request
        logger.info(
            f"request.started",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "query_params": query_params,
                "client": request.client[0] if request.client else None,
                "user_agent": request.headers.get("user-agent", ""),
            },
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log the exception - catches all exceptions for comprehensive logging
            # This is intentionally broad since logging middleware must capture all errors
            duration = time.time() - start_time
            logger.error(
                f"request.failed",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            raise

        # Record response time
        duration = time.time() - start_time

        # Track HTTP 405 errors for monitoring and alerting
        if response.status_code == 405:
            tracker = get_405_tracker()
            user_id = None
            # Try to extract user_id from request context if available
            if hasattr(request.state, 'user_id'):
                user_id = request.state.user_id

            tracker.record_405(
                method=method,
                path=path,
                client_ip=request.client[0] if request.client else None,
                user_agent=request.headers.get("user-agent", ""),
                user_id=user_id,
                query_params=query_params,
            )

            # Log 405 errors with special attention
            logger.warning(
                "http.405.method_not_allowed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "client_ip": request.client[0] if request.client else None,
                    "user_id": user_id,
                    "user_agent": request.headers.get("user-agent", ""),
                    "status_code": 405,
                },
            )

            # Report to Sentry with 405 context
            sentry_sdk.capture_message(
                f"HTTP 405 Method Not Allowed: {method} {path}",
                level="warning",
                tags={
                    "http_status": "405",
                    "method": method,
                    "endpoint": path,
                    "client_ip": request.client[0] if request.client else "unknown",
                },
            )

            # Check if alert threshold exceeded
            should_alert, count, threshold = tracker.should_alert()
            if should_alert:
                sentry_sdk.capture_message(
                    f"HTTP 405 Alert: {count} errors in last hour (threshold: {threshold})",
                    level="error",
                    tags={
                        "alert_type": "http_405_threshold_exceeded",
                        "error_count": str(count),
                        "threshold": str(threshold),
                    },
                )

        # #21: Track response size and #22: error rates by category
        content_length = int(response.headers.get("content-length", 0))
        try:
            from ..core.metrics import increment
            # #22: Track error rates by endpoint category
            if response.status_code >= 500:
                category = _categorize_path(path)
                increment("http_error_total", {"category": category, "status": str(response.status_code)})
            # #21: Track oversized responses
            if content_length > 1_000_000:  # > 1MB
                increment("http_oversized_response_total", {"path": path[:100]})
        except Exception:  # noqa: BLE001  # observability metric emit must not break request
            logger.debug("Failed to emit HTTP metrics for %s", path)

        # Log response
        logger.info(
            f"request.completed",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "content_length": content_length,
            },
        )

        # Add performance headers (#16: propagate request ID end-to-end)
        response.headers["X-Request-ID"] = request_id
        # response.headers["X-Process-Time"] = str(duration)  # removed: timing oracle

        return response


def _categorize_path(path: str) -> str:
    path = path.lower()
    if "/auth/" in path or "/login" in path or "/register" in path:
        return "auth"
    if "/catalog" in path or "/search" in path:
        return "catalog"
    if "/checkout" in path or "/circulation" in path or "/hold" in path:
        return "circulation"
    if "/fine" in path or "/payment" in path:
        return "finance"
    if "/user" in path or "/patron" in path or "/staff" in path:
        return "users"
    if "/room" in path:
        return "rooms"
    if "/indie" in path:
        return "indie"
    return "other"


def mask_sensitive_data(data: Any) -> Any:
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            # Check if key matches any sensitive field (case-insensitive)
            key_lower = key.lower().replace("-", "_").replace(" ", "_")
            if key_lower in SENSITIVE_FIELDS:
                masked[key] = "[REDACTED]"
            else:
                masked[key] = mask_sensitive_data(value)
        return masked
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    else:
        return data


def mask_query_params(params: dict[str, Any]) -> dict[str, Any]:
    masked = {}
    for key, value in params.items():
        key_lower = key.lower().replace("-", "_").replace(" ", "_")
        if key_lower in SENSITIVE_QUERY_PARAMS:
            masked[key] = "[REDACTED]"
        else:
            masked[key] = value
    return masked
