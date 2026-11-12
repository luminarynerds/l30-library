# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from .config import get_settings


def setup_sentry() -> None:
    settings = get_settings()

    if not settings.sentry_dsn:
        return  # Sentry not configured

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        # Performance monitoring: sample 1% of transactions in production
        profiles_sample_rate=0.1 if settings.environment == "production" else 1.0,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
            LoggingIntegration(
                level=None,  # Capture info level and above
                event_level=None,  # Send error level logs as events
            ),
        ],
        # Capture HTTP request/response for debugging
        send_default_pii=False,
        attach_stacktrace=True,
        # Release tracking for better error correlation
        release=settings.app_version,
        # Ignore common non-critical errors
        ignore_errors=[
            "starlette.exceptions.HTTPException",
            "fastapi.exceptions.RequestValidationError",
        ],
        # Custom before_send hook for processing events
        before_send=_before_send_sentry,
    )


def _before_send_sentry(event, hint):
    # Check if this is a 405 event
    if event.get("tags", {}).get("http_status") == "405":
        # Add custom fingerprint for 405 grouping by endpoint
        endpoint = event.get("tags", {}).get("endpoint", "unknown")
        event["fingerprint"] = ["http_405", endpoint]

        # Ensure 405 errors route to correct alerts
        event.setdefault("tags", {})["alert_routing"] = "http_405_errors"

    # Check for 405 alert threshold exceeded
    if event.get("tags", {}).get("alert_type") == "http_405_threshold_exceeded":
        # Mark as critical for alert routing
        event["level"] = "error"
        event.setdefault("tags", {})["alert_routing"] = "http_405_critical"
        event.setdefault("tags", {})["alert_severity"] = "critical"

    return event
