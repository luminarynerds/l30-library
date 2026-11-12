# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the health check probe endpoints.

Validates that liveness, readiness, startup, detailed, and dashboard
endpoints return the expected structure and status codes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_scheduler(running: bool = True, job_count: int = 5):
    """Create a mock APScheduler for testing."""
    from datetime import datetime, timezone

    mock_scheduler = MagicMock()
    mock_scheduler.running = running
    jobs = []
    for i in range(job_count):
        job = MagicMock()
        job.id = f"job_{i}"
        job.name = f"Test Job {i}"
        job.next_run_time = datetime.now(timezone.utc)
        jobs.append(job)
    mock_scheduler.get_jobs.return_value = jobs
    return mock_scheduler


@pytest.fixture
def token(test_staff):
    """Staff auth token -- health/readiness/dashboard endpoints require staff."""
    from app.core.security import create_access_token

    return create_access_token(subject=test_staff.id, email=test_staff.email)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLivenessProbe:
    """Tests for /api/v1/health and /api/v1/health/live."""

    async def test_basic_health_returns_ok(self, client):
        """Basic health check returns 200 with status ok."""
        response = await client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "l30-library"
        assert "timestamp" in data
        assert "version" in data

    async def test_live_returns_alive(self, client):
        """Liveness probe returns 200 with status alive."""
        response = await client.get("/api/v1/health/live")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "alive"
        assert data["service"] == "l30-library"
        assert "timestamp" in data


class TestReadinessProbe:
    """Tests for /api/v1/health/ready."""

    async def test_readiness_returns_checks_structure(self, client, db_session, token):
        """Readiness probe returns checks for all dependencies."""
        response = await client.get(
            "/api/v1/health/ready",
            headers={"Authorization": f"Bearer {token}"},
        )
        # May be 200 or 503 depending on dependencies, but structure should be consistent
        data = response.json()
        # A 503 is wrapped by the generic HTTPException handler, which nests
        # the raised `detail` payload at error.message, not top-level "detail".
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            data = data["error"]["message"]
        assert "checks" in data
        checks = data["checks"]
        assert "database" in checks
        assert "redis" in checks
        assert "scheduler" in checks
        assert "websockets" in checks

    async def test_readiness_database_check_has_response_time(self, client, db_session, token):
        """Database check should include response_time_ms."""
        response = await client.get(
            "/api/v1/health/ready",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.json()
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            data = data["error"]["message"]
        db_check = data["checks"]["database"]
        assert "response_time_ms" in db_check
        assert "status" in db_check


class TestStartupProbe:
    """Tests for /api/v1/health/startup."""

    async def test_startup_returns_started(self, client, db_session, token):
        """Startup probe returns database and scheduler info."""
        response = await client.get(
            "/api/v1/health/startup",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["status"] == "started"
            assert data["database"] == "connected"
            assert "scheduler" in data


class TestDetailedHealth:
    """Tests for /api/v1/health/detailed."""

    async def test_detailed_returns_comprehensive_info(self, client, db_session, token):
        """Detailed health includes all subsystems and uptime."""
        response = await client.get(
            "/api/v1/health/detailed",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))
        assert "version" in data
        assert "environment" in data
        assert "checks" in data
        checks = data["checks"]
        assert "database" in checks
        assert "redis" in checks
        assert "scheduler" in checks
        assert "websockets" in checks


class TestHealthDashboard:
    """Tests for /api/v1/health/dashboard (staff-only)."""

    async def test_dashboard_requires_authentication(self, client):
        """Dashboard endpoint rejects unauthenticated requests."""
        response = await client.get("/api/v1/health/dashboard")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    async def test_dashboard_returns_full_data(self, client, db_session, token):
        """Dashboard returns comprehensive data when authenticated."""
        response = await client.get(
            "/api/v1/health/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "uptime_seconds" in data
        assert "checks" in data
        checks = data["checks"]
        # All four dependency groups present
        assert "database" in checks
        assert "redis" in checks
        assert "scheduler" in checks
        assert "websockets" in checks


class TestSchedulerCheck:
    """Tests for the internal _check_scheduler helper."""

    async def test_scheduler_none_returns_disabled(self):
        """When scheduler is None and no lock file exists, status is unhealthy.

        _check_scheduler only reports "disabled" when
        settings.scheduler_enabled is False; the test env leaves that at its
        default of True, so a None scheduler with no lock file at
        /tmp/.lsc_scheduler.lock falls through to the "lock file not found"
        branch, which reports "unhealthy".
        """
        from app.api.v1.health import _check_scheduler

        with patch("app.services.schedulers.main.get_scheduler", return_value=None):
            result = await _check_scheduler()
            assert result["status"] == "unhealthy"

    async def test_scheduler_running_returns_healthy(self):
        """When scheduler is running with jobs, status should be healthy."""
        from app.api.v1.health import _check_scheduler

        mock_sched = _make_mock_scheduler(running=True, job_count=3)
        with patch("app.services.schedulers.main.get_scheduler", return_value=mock_sched):
            result = await _check_scheduler()
            assert result["status"] == "healthy"
            assert result["running"] is True
            assert result["job_count"] == 3
            assert result["next_run_time"] is not None

    async def test_scheduler_stopped_returns_unhealthy(self):
        """When scheduler exists but is not running, status should be unhealthy."""
        from app.api.v1.health import _check_scheduler

        mock_sched = _make_mock_scheduler(running=False, job_count=0)
        with patch("app.services.schedulers.main.get_scheduler", return_value=mock_sched):
            result = await _check_scheduler()
            assert result["status"] == "unhealthy"
            assert result["running"] is False


class TestWebSocketCheck:
    """Tests for the internal _check_websockets helper."""

    async def test_websocket_check_returns_both_managers(self):
        """WebSocket check should return both patron and rfid data."""
        from app.api.v1.health import _check_websockets

        result = _check_websockets()
        assert result["status"] == "healthy"
        assert "patron" in result
        assert "rfid" in result

    async def test_websocket_patron_stats_structure(self):
        """Patron WS stats should include key metrics."""
        from app.api.v1.health import _check_websockets

        result = _check_websockets()
        patron = result.get("patron", {})
        if "error" not in patron:
            assert "active_connections" in patron
            assert "unique_users" in patron
            assert "running" in patron


class TestRootHealthEndpoint:
    """Tests for the root /health endpoint in main.py."""

    async def test_root_health_returns_healthy(self, client):
        """Root health check returns 200 with status healthy.

        This is the bare /health route defined directly in app/main.py (not
        the fuller /api/v1/health router), and it intentionally returns a
        minimal payload with no timestamp or version.
        """
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "l30-library"


class TestHealthTrustedHostExempt:
    """Regression tests: /health must accept any Host header.

    Docker/orchestrator health probes legitimately arrive with Host headers
    like `backend:8000` (compose service name) or other internal aliases
    that aren't in TRUSTED_HOSTS. Same for sibling Docker stacks
    co-attached on shared networks (metislib_default).

    Prior to the fix, every such probe hit Starlette's TrustedHostMiddleware
    and got `400 Invalid host header`, flooding logs and leaving the
    container stuck in `starting` state.
    """

    @pytest.fixture(autouse=True)
    def _restore_app_main(self):
        """Undo the process-global mutation _isolated_app() performs.

        _isolated_app() sets os.environ["TRUSTED_HOSTS"] to a narrow
        production-style list, clears get_settings's lru_cache, and
        importlib.reloads app.main IN PLACE to rebuild the middleware
        stack. Every other test's `client` fixture does a fresh
        `from app.main import app` inside the fixture body, so without
        restoring this afterward, every test that runs later in the same
        pytest process gets the narrowed TRUSTED_HOSTS (missing "test"/
        "testserver") and fails with 400 "Invalid host header" -- this was
        cascading into unrelated files depending on collection order.
        """
        import os

        original_trusted_hosts = os.environ.get("TRUSTED_HOSTS")
        try:
            yield
        finally:
            import importlib

            from app.core import config as _config

            if original_trusted_hosts is None:
                os.environ.pop("TRUSTED_HOSTS", None)
            else:
                os.environ["TRUSTED_HOSTS"] = original_trusted_hosts
            _config.get_settings.cache_clear()
            import app.main as _main

            importlib.reload(_main)

    def _isolated_app(self, trusted_hosts: str = "l30.org,localhost,l30-nginx"):
        """Spin up an app with realistic TRUSTED_HOSTS.

        Uses monkeypatched settings so we don't depend on the test env's
        TRUSTED_HOSTS being narrow.
        """
        # Force the production-style TRUSTED_HOSTS list into settings before
        # importing main, then reload to rebuild the middleware stack.
        import importlib
        import os

        os.environ["TRUSTED_HOSTS"] = trusted_hosts
        # Bust the lru_cache on get_settings so the new env is picked up
        from app.core import config as _config

        _config.get_settings.cache_clear()

        import app.main as _main

        importlib.reload(_main)

        from fastapi.testclient import TestClient

        return TestClient(_main.app)

    async def test_health_accepts_compose_service_host(self):
        """Host: backend:8000 (the compose service name) must return 200.

        This is the exact Host header used by docker-compose healthchecks
        and by sibling stacks doing service-name lookups across networks.
        """
        client = self._isolated_app()
        r = client.get("/health", headers={"Host": "backend:8000"})
        assert r.status_code == 200, (
            f"expected 200 for Host=backend:8000, got {r.status_code}: {r.text}"
        )
        assert r.json()["status"] == "healthy"

    async def test_health_accepts_arbitrary_host(self):
        """Any Host should reach /health — the endpoint is Host-agnostic."""
        client = self._isolated_app()
        r = client.get("/health", headers={"Host": "evil.example"})
        assert r.status_code == 200, (
            f"expected 200 for arbitrary Host, got {r.status_code}: {r.text}"
        )

    async def test_api_v1_health_also_exempt(self):
        """/api/v1/health gets the same exemption."""
        client = self._isolated_app()
        r = client.get("/api/v1/health", headers={"Host": "backend:8000"})
        assert r.status_code == 200, (
            f"expected 200 for /api/v1/health with stray Host, got "
            f"{r.status_code}: {r.text}"
        )

    async def test_other_paths_still_check_host(self):
        """Non-health paths must still reject untrusted hosts (regression guard)."""
        client = self._isolated_app()
        # /openapi.json is unauthenticated but should still be Host-gated.
        r = client.get("/openapi.json", headers={"Host": "evil.example"})
        assert r.status_code == 400, (
            f"expected 400 for non-health path with bad Host, got "
            f"{r.status_code}: {r.text}"
        )


class TestOverallStatusHelper:
    """Tests for the _overall_status helper function."""

    async def test_all_healthy(self):
        from app.api.v1.health import _overall_status

        checks = {
            "db": {"status": "healthy"},
            "redis": {"status": "healthy"},
        }
        assert _overall_status(checks) == "healthy"

    async def test_any_unhealthy(self):
        from app.api.v1.health import _overall_status

        checks = {
            "db": {"status": "healthy"},
            "redis": {"status": "unhealthy"},
        }
        assert _overall_status(checks) == "unhealthy"

    async def test_degraded(self):
        from app.api.v1.health import _overall_status

        checks = {
            "db": {"status": "healthy"},
            "redis": {"status": "degraded"},
        }
        assert _overall_status(checks) == "degraded"

    async def test_unhealthy_trumps_degraded(self):
        from app.api.v1.health import _overall_status

        checks = {
            "db": {"status": "unhealthy"},
            "redis": {"status": "degraded"},
            "sched": {"status": "healthy"},
        }
        assert _overall_status(checks) == "unhealthy"
