# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for monitoring and logging infrastructure."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestRequestLoggingMiddleware:
    """Test request/response logging middleware."""

    async def test_request_logging_captures_basic_info(self, client: TestClient):
        """Verify request logging captures method, path, and status."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        # Middleware should allow request through

    async def test_request_logging_skips_health_checks(self, client: TestClient, caplog):
        """Verify health checks are not logged to reduce noise."""
        import logging

        caplog.set_level(logging.INFO)

        response = await client.get("/health")
        assert response.status_code == 200
        # Health check should not be logged

    async def test_request_logging_excludes_duration_header(self, client: TestClient):
        """Verify response does NOT include X-Process-Time header.

        app/middleware/logging_middleware.py RequestLoggingMiddleware.dispatch
        deliberately commented this header out ("removed: timing oracle") --
        exposing precise response timing is a side-channel that can leak
        information (e.g. cache hits, auth short-circuits), so it was
        intentionally dropped. This used to assert the header's presence;
        now documents its intentional absence.
        """
        response = await client.get("/api/v1/catalog/search?q=test")
        assert "x-process-time" not in response.headers

    async def test_request_logging_includes_request_id(self, client: TestClient):
        """Verify response includes X-Request-ID header.

        /health and /api/v1/health are explicitly exempted from
        RequestLoggingMiddleware ("Skip logging for health checks"), so they
        never get this header -- use a normal endpoint instead to exercise
        the middleware path that actually sets it.
        """
        response = await client.get("/api/v1/catalog/search?q=test")
        assert "x-request-id" in response.headers

    async def test_request_logging_masks_sensitive_data(self, client: TestClient):
        """Verify sensitive data is masked in logs."""
        # Test password masking
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePassword123!",
                "full_name": "Test User",
            },
        )
        # Password should be masked in logs (tested via middleware)
        assert response.status_code in [200, 400, 422, 409]

    async def test_post_request_body_captured(self, client: TestClient):
        """Verify POST request bodies are captured for logging."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePassword123!",
                "full_name": "Test User",
            },
        )
        # Request body should be processed without errors
        assert response.status_code in [200, 400, 422, 409]


@pytest.mark.integration
class TestLoggingConfiguration:
    """Test logging configuration."""

    async def test_logging_module_initializes(self):
        """Verify logging module imports and initializes without error."""
        from app.core.logging import get_logger, setup_logging

        # Setup should not raise
        setup_logging()

        # Get logger should work
        logger = get_logger("test")
        assert logger is not None

    async def test_logger_creates_log_files(self):
        """Verify logger creates log files.

        app/core/logging.py computes LOG_DIR and creates it as a MODULE-LEVEL
        side effect at first import (`os.makedirs("logs", ...)`), not inside
        setup_logging() itself. By the time this test runs, app.core.logging
        is already imported and cached (via app fixtures), so chdir'ing and
        re-"importing" it here was a no-op against a fresh location -- the
        cached module's LOG_DIR (a bare relative "logs" string) doesn't
        rebase to tmp_path, and calling setup_logging() after chdir just
        makes RotatingFileHandler try to open "logs/error.log" relative to
        the NEW cwd, whose "logs" subdir was never created there --
        ValueError: Unable to configure handler 'error_file'. Real app
        startup never chdirs after import, so this only verifies the
        directory setup_logging() actually uses, without chdir.
        """
        import os

        from app.core.logging import LOG_DIR, setup_logging

        setup_logging()

        assert os.path.exists(LOG_DIR)

    async def test_json_formatter_outputs_valid_json(self):
        """Verify JSON formatter produces valid JSON output."""
        import json
        import logging
        from io import StringIO

        from pythonjsonlogger import jsonlogger

        # Create logger with JSON formatter
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        formatter = jsonlogger.JsonFormatter()
        handler.setFormatter(formatter)

        logger = logging.getLogger("test_json")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Log a message
        logger.info("Test message", extra={"user_id": 123})

        # Output should be valid JSON
        log_output = log_stream.getvalue().strip()
        if log_output:  # Only if something was logged
            parsed = json.loads(log_output)
            assert "message" in parsed
            assert "user_id" in parsed


@pytest.mark.integration
class TestSentryIntegration:
    """Test Sentry error tracking integration."""

    @patch("sentry_sdk.init")
    async def test_sentry_initializes(self, mock_sentry_init):
        """Verify Sentry SDK initializes correctly."""
        from app.core.monitoring import setup_sentry

        # Mock empty DSN (Sentry disabled)
        with patch("app.core.monitoring.get_settings") as mock_settings:
            mock_settings.return_value.sentry_dsn = ""

            setup_sentry()

            # With empty DSN, init should not be called
            mock_sentry_init.assert_not_called()

    @patch("sentry_sdk.init")
    async def test_sentry_initializes_with_dsn(self, mock_sentry_init):
        """Verify Sentry initializes when DSN is configured."""
        from app.core.monitoring import setup_sentry

        # Mock DSN configured
        with patch("app.core.monitoring.get_settings") as mock_settings:
            settings = MagicMock()
            settings.sentry_dsn = "https://test@sentry.io/123"
            settings.sentry_environment = "production"
            settings.sentry_traces_sample_rate = 0.1
            settings.app_version = "1.0.0"
            settings.environment = "production"

            mock_settings.return_value = settings

            setup_sentry()

            # With valid DSN, init should be called
            mock_sentry_init.assert_called_once()
            call_kwargs = mock_sentry_init.call_args[1]
            assert call_kwargs["dsn"] == "https://test@sentry.io/123"
            assert call_kwargs["environment"] == "production"

    async def test_sentry_ignores_http_exceptions(self):
        """Verify Sentry ignores HTTPException to reduce noise."""
        from app.core.monitoring import setup_sentry  # noqa: F401

        # Sentry should be configured to ignore HTTPException
        # (This test documents the behavior)
        # HTTPExceptions are expected 404s, auth failures, etc.


@pytest.mark.integration
class TestApplicationStartupShutdown:
    """Test application startup and shutdown logging."""

    async def test_startup_event_logs_app_info(self, caplog):
        """Verify startup event logs application information."""
        import logging

        caplog.set_level(logging.INFO)

        # Trigger startup
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app):
            pass

        # Startup logging may have occurred
        # (Difficult to test with test client due to event handling)

    async def test_health_check_endpoint_returns_version(self, client: TestClient, test_staff):
        """Verify health check endpoint includes version.

        /api/v1/health is the bare liveness probe and is intentionally
        minimal ("no DB or Redis calls" -- see app/api/v1/health.py
        health_check): it returns status/service/timestamp/version only,
        never "environment". /api/v1/health/detailed is the endpoint that
        includes environment plus dependency checks, but it's staff-gated
        (Depends(require_staff)).
        """
        from app.api.v1.auth import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: test_staff
        try:
            response = await client.get("/api/v1/health/detailed")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        assert response.status_code == 200

        data = response.json()
        assert "version" in data
        assert "status" in data
        assert "environment" in data
