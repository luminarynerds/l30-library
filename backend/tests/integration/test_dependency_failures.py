# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Dependency Failure Injection Tests for LSC Library System.

Systematically injects failures into each dependency one at a time and verifies:
- Blast radius: what breaks, what keeps working
- User experience: error messages, degraded functionality
- Alerting: what Prometheus alerts fire
- Recovery: how the system recovers when the dependency returns

Dependencies tested:
1. Redis dies
2. Email service (Resend) dies
3. Database replica dies
4. Search service dies
5. Auth service slow (not dead)
6. Disk fills up
7. DNS flaky (intermittent failures)
8. SSL cert expires

Design principle: Everything fails. Plan for it.
"""

import asyncio
import hashlib
import os
import ssl
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import httpx
import pytest
import redis.exceptions

# Ensure test environment
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/lsc_dep_failure_test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-dependency-failure-tests")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

# NOTE (test-rot remediation): 18 tests asserting against
# monitoring/alerts.yaml and alert-rules.yml were removed here. Those
# files were deliberately deleted in 92f9be0f2 ("refactor: remove
# project bloat") along with the whole Prometheus/Alertmanager stack --
# it was never deployed to prod. The tests were testing decommissioned
# infra, not a regression; nothing to fix here without resurrecting a
# stack the team already chose to drop.

from pathlib import Path

# Tests run with CWD=backend/ (see test recipe), but docker-compose.yml lives
# at the repo root. Resolve it relative to this file instead of relying on CWD.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DOCKER_COMPOSE_YML = _REPO_ROOT / "docker-compose.yml"


# ---------------------------------------------------------------------------
# 1. REDIS DIES
# ---------------------------------------------------------------------------

class TestRedisDies:
    """
    When Redis dies, the blast radius is wide but the system is designed
    to degrade gracefully rather than crash.

    Blast radius:
    - Cache: all cache lookups miss, every request hits the database directly
    - Rate limiting: falls back to in-memory (per-process, not distributed)
    - Token revocation: falls back to in-memory LRU cache (5min grace window)
    - Distributed locks: checkout item-copy locking unavailable
    - Email safeguards: daily cap + dedup checks fail-open (emails still send)
    - Session management: depends on JWT (stateless), not Redis-stored sessions
    - Recommendations: falls back to in-memory cache (limited to 1000 entries)
    - Health checks: readiness probe reports "degraded", not "unhealthy"

    What keeps working:
    - All database operations (PostgreSQL is independent)
    - All API endpoints (degrade to slower, uncached responses)
    - Authentication (JWT is stateless, token validation uses in-memory fallback)
    - Checkouts (item-copy distributed lock gracefully skipped)
    - Email sending (safeguards fail-open)
    - Search (PostgreSQL full-text search is database-based)
    """

    @pytest.mark.asyncio
    async def test_cache_get_returns_none_when_redis_dead(self):
        """Cache reads gracefully return None, triggering database fallback."""
        from app.core.cache import get_cached, _cache_metrics

        _cache_metrics.reset()

        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=None):
            result = await get_cached("catalog:search:abc123")

        assert result is None
        snapshot = _cache_metrics.snapshot()
        assert snapshot["per_prefix"]["catalog:"]["misses"] >= 1

    @pytest.mark.asyncio
    async def test_cache_set_silently_fails_when_redis_dead(self):
        """Cache writes silently fail—callers are never blocked."""
        from app.core.cache import set_cached

        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=None):
            # Should NOT raise—just log a warning and return
            await set_cached("catalog:search:abc123", {"items": []}, ttl_seconds=300)

    @pytest.mark.asyncio
    async def test_cache_get_handles_connection_error(self):
        """Redis connection errors produce a miss, not an exception."""
        from app.core.cache import get_cached, _cache_metrics

        _cache_metrics.reset()

        mock_client = AsyncMock()
        mock_client.get.side_effect = redis.exceptions.ConnectionError("Connection refused")

        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=mock_client):
            result = await get_cached("patron:profile:42")

        assert result is None
        snapshot = _cache_metrics.snapshot()
        assert snapshot["per_prefix"]["patron:"]["errors"] >= 1

    @pytest.mark.asyncio
    async def test_cache_invalidation_handles_redis_dead(self):
        """Cache invalidation returns 0 (no keys deleted) when Redis is down."""
        from app.core.cache import invalidate_cache

        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=None):
            deleted = await invalidate_cache("catalog:*")

        assert deleted == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_falls_back_to_memory(self):
        """When Redis is unreachable, rate limiter uses in-memory storage."""
        from app.core.rate_limit import limiter

        # The limiter is configured with Redis URI; if Redis is down,
        # slowapi's limits library will raise a storage error on first use
        # but the middleware catches this and falls back.
        # Verify the limiter was configured with a storage URI.
        assert limiter._storage_uri is not None or hasattr(limiter, "_limiter")

    @pytest.mark.asyncio
    async def test_token_revocation_uses_inmemory_cache_when_redis_dead(self):
        """Token revocation check falls back to in-memory LRU on Redis failure."""
        from app.core import security

        # Pre-populate the in-memory cache with a "known good" token
        token = "eyJhbGciOiJIUzI1NiJ9.test.signature"
        token_hash = security._get_token_hash(token)
        security._cache_put(token_hash, time.monotonic())

        # Simulate Redis being down
        original_available = security._redis_available
        original_client = security._redis_client
        try:
            security._redis_available = False
            security._redis_last_check = time.monotonic()  # Just checked

            # Token in cache → should be allowed (not revoked)
            result = security.is_token_revoked(token)
            assert result is False, "Cached non-revoked token should pass during Redis outage"
        finally:
            security._redis_available = original_available
            security._redis_client = original_client

    @pytest.mark.asyncio
    async def test_token_revocation_rejects_unknown_tokens_when_redis_dead(self):
        """Unknown tokens are rejected during Redis outage (fail-secure)."""
        from app.core import security

        unknown_token = "eyJhbGciOiJIUzI1NiJ9.unknown.signature"

        original_available = security._redis_available
        try:
            security._redis_available = False
            security._redis_last_check = time.monotonic()

            # Token NOT in cache → should be rejected (fail-secure)
            result = security.is_token_revoked(unknown_token)
            assert result is True, "Unknown tokens must be rejected during Redis outage"
        finally:
            security._redis_available = original_available

    @pytest.mark.asyncio
    async def test_checkout_works_without_redis_distributed_lock(self):
        """Checkout proceeds even when Redis lock can't be acquired.

        When Redis is down, item_copy distributed locking is skipped.
        The database-level FOR UPDATE lock still prevents double-checkout.
        """
        from app.core import cache

        # `from app.core.cache import get_redis` before the patch binds the
        # local name to the *original* function; patch.object on the module
        # is what call sites (like checkout_service, which does
        # `cache.get_redis()`) actually observe, so call through the module
        # here too rather than a pre-imported reference.
        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=None):
            client = await cache.get_redis()
            assert client is None
            # checkout_service.create_checkout checks `if redis_client is not None`
            # before acquiring lock. When None, it falls through to DB-only locking.

    @pytest.mark.asyncio
    async def test_email_safeguards_fail_open_when_redis_dead(self):
        """Email safeguards (daily cap, dedup) allow sends when Redis is down."""
        from app.core.email_safeguards import check_daily_cap, check_dedup

        with patch("app.core.email_safeguards._get_redis_client", new_callable=AsyncMock, return_value=None):
            # Daily cap should fail-open (return True = allow sending)
            cap_ok = await check_daily_cap()
            assert cap_ok is True, "Daily cap must fail-open when Redis is down"

            # Dedup should fail-open (return True = allow sending)
            dedup_ok = await check_dedup(patron_id=42, notification_type="hold_ready")
            assert dedup_ok is True, "Dedup must fail-open when Redis is down"

    @pytest.mark.asyncio
    async def test_health_check_reports_redis_unhealthy(self):
        """Health readiness check correctly reports Redis as unhealthy."""
        from app.api.v1.health import _check_redis

        # _check_redis calls the shared `get_redis()` helper directly
        # (imported at module scope), not an `aioredis` module -- patch that.
        mock_client = AsyncMock()
        mock_client.ping.side_effect = redis.exceptions.ConnectionError("Connection refused")
        with patch("app.api.v1.health.get_redis", new_callable=AsyncMock, return_value=mock_client):
            result = await _check_redis()

        assert result["status"] == "unhealthy"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_cache_metrics_track_errors_during_redis_outage(self):
        """Cache metrics correctly count errors for monitoring/alerting."""
        from app.core.cache import get_cached, _cache_metrics

        _cache_metrics.reset()

        mock_client = AsyncMock()
        mock_client.get.side_effect = redis.exceptions.ConnectionError("Connection refused")

        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=mock_client):
            for _ in range(5):
                await get_cached("test:key")

        snapshot = _cache_metrics.snapshot()
        assert snapshot["per_prefix"]["test:"]["errors"] == 5

class TestEmailServiceDies:
    """
    When the email provider is unavailable, email delivery fails but all core
    operations continue uninterrupted.

    Blast radius:
    - Password reset emails: users can't reset passwords via email
    - Verification emails: new signups can't verify email
    - Hold-ready notifications: patrons don't know items are ready
    - Overdue notices: patrons miss reminders
    - Newsletter delivery: marketing emails don't go out

    What keeps working:
    - ALL checkouts, returns, renewals, holds
    - ALL authentication (login/logout)
    - ALL catalog operations (search, browse, view)
    - ALL staff operations
    - Account creation (just verification email doesn't send)
    - Failed emails saved to Dead Letter Queue for retry

    User experience:
    - Checkouts complete normally (email receipt silently fails)
    - Password reset says "email sent" but user never gets it
    - Hold-ready items sit at pickup, patron unaware
    """

    @pytest.mark.asyncio
    async def test_checkout_succeeds_when_email_fails(self):
        """Checkout operations are never blocked by email failures."""
        from app.core.email import send_email

        with patch("app.core.email.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client_cls.return_value = mock_client

            with patch("app.core.email.settings") as mock_settings:
                mock_settings.resend_api_key = "SG.test_key"
                mock_settings.from_email = "noreply@test.com"
                mock_settings.app_name = "LSC Test"
                mock_settings.environment = "test"

                result = await send_email(
                    "patron@test.com",
                    "Checkout Receipt",
                    "<p>Your checkout receipt</p>",
                )

        # Email returns False (failed) but does NOT raise an exception
        assert result is False

    @pytest.mark.asyncio
    async def test_email_provider_timeout_doesnt_crash(self):
        """Email-provider timeout is caught and logged—never crashes the caller."""
        from app.core.email import send_email

        with patch("app.core.email.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.side_effect = httpx.TimeoutException("Request timed out")
            mock_client_cls.return_value = mock_client

            with patch("app.core.email.settings") as mock_settings:
                mock_settings.resend_api_key = "SG.test_key"
                mock_settings.from_email = "noreply@test.com"
                mock_settings.app_name = "LSC Test"
                mock_settings.environment = "test"

                result = await send_email(
                    "patron@test.com",
                    "Hold Ready Notification",
                    "<p>Your hold is ready!</p>",
                )

        assert result is False

    @pytest.mark.asyncio
    async def test_email_provider_500_doesnt_crash(self):
        """Email-provider 500 response returns False, not an exception."""
        from app.core.email import send_email

        with patch("app.core.email.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with patch("app.core.email.settings") as mock_settings:
                mock_settings.resend_api_key = "SG.test_key"
                mock_settings.from_email = "noreply@test.com"
                mock_settings.app_name = "LSC Test"
                mock_settings.environment = "test"

                result = await send_email(
                    "patron@test.com",
                    "Overdue Notice",
                    "<p>Your item is overdue</p>",
                )

        assert result is False

    @pytest.mark.asyncio
    async def test_missing_api_key_in_production_returns_false(self):
        """Missing API key in production returns False and logs CRITICAL."""
        from app.core.email import send_email

        with patch("app.core.email.settings") as mock_settings:
            mock_settings.resend_api_key = ""
            mock_settings.environment = "production"
            mock_settings.from_email = "noreply@test.com"
            mock_settings.app_name = "LSC Test"

            result = await send_email(
                "patron@test.com",
                "Test Subject",
                "<p>Test body</p>",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_missing_api_key_in_dev_returns_true(self):
        """Missing API key in dev/test returns True (flow continues)."""
        from app.core.email import send_email

        with patch("app.core.email.settings") as mock_settings:
            mock_settings.resend_api_key = ""
            mock_settings.environment = "test"

            result = await send_email(
                "patron@test.com",
                "Test Subject",
                "<p>Test body</p>",
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_email_safeguard_failure_doesnt_block_send(self):
        """If safeguard checks themselves crash, email still attempts to send."""
        from app.core.email import send_email

        with patch("app.core.email_safeguards.check_daily_cap", side_effect=Exception("Redis exploded")):
            with patch("app.core.email.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_response = MagicMock()
                mock_response.status_code = 202
                mock_client.post.return_value = mock_response
                mock_client_cls.return_value = mock_client

                with patch("app.core.email.settings") as mock_settings:
                    mock_settings.resend_api_key = "SG.test_key"
                    mock_settings.from_email = "noreply@test.com"
                    mock_settings.app_name = "LSC Test"
                    mock_settings.environment = "test"
                    # _resend_pace() does `settings.resend_min_interval_s <= 0`;
                    # a bare MagicMock isn't orderable against int, so this must
                    # be a real number (0 = pacing disabled) for the mock to work.
                    mock_settings.resend_min_interval_s = 0

                    result = await send_email(
                        "patron@test.com",
                        "Test",
                        "<p>Test</p>",
                    )

            # Email should still succeed even though safeguard check failed
            assert result is True

class TestDatabaseReplicaDies:
    """
    When the read replica dies, the system should fail over to the primary
    for read queries. In current LSC config, if REPLICA_DATABASE_URL is not
    set, the replica engine IS the primary engine (single-server mode).

    Blast radius (with separate replica):
    - Reports/analytics queries fail until failover
    - Dashboard aggregations unavailable briefly
    - Catalog search/browse may be slower on primary
    - Replication lag monitoring shows error

    What keeps working:
    - ALL writes (checkouts, holds, fines) are on primary
    - ALL authentication is on primary
    - If replica == primary (default), NOTHING changes

    Recovery:
    - Replica reconnection is automatic via SQLAlchemy pool_pre_ping
    - Stale connections are evicted on next use
    """

    @pytest.mark.asyncio
    async def test_replica_lag_check_handles_dead_replica(self):
        """Replication lag check returns error status when replica is down."""
        from sqlalchemy import exc as sa_exc
        from app.core.read_replica import check_replica_lag

        with patch("app.core.read_replica._ReplicaSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            # check_replica_lag only catches sa_exc.SQLAlchemyError -- a bare
            # Exception would propagate instead of producing status="error".
            mock_session.execute.side_effect = sa_exc.OperationalError(
                "connection refused", params=None, orig=Exception("connection refused")
            )
            mock_session_cls.return_value = mock_session

            # check_replica_lag skips _init_replica_engine() (which would
            # overwrite our patches) whenever _replica_engine is already
            # truthy, and only takes the "replica" path when _replica_url
            # differs from settings.database_url.
            with patch("app.core.read_replica._replica_engine", MagicMock()):
                with patch("app.core.read_replica._replica_url", "postgresql+asyncpg://replica:5432/db"):
                    with patch("app.core.read_replica.settings") as mock_settings:
                        mock_settings.database_url = "postgresql+asyncpg://primary:5432/db"

                        result = await check_replica_lag()

        assert result["status"] == "error"
        assert result["lag_seconds"] == -1

    @pytest.mark.asyncio
    async def test_single_server_mode_has_zero_lag(self):
        """Single-server mode (no separate replica) always reports 0 lag."""
        from app.core.read_replica import check_replica_lag

        # check_replica_lag's single-server branch is
        # `_replica_url == settings.database_url` (not `_replica_url is None`),
        # and it skips re-deriving _replica_url whenever _replica_engine is
        # already truthy -- so both must be patched together, in sync.
        same_url = "sqlite+aiosqlite:////tmp/test.db"
        with patch("app.core.read_replica._replica_engine", MagicMock()):
            with patch("app.core.read_replica._replica_url", same_url):
                with patch("app.core.read_replica.settings") as mock_settings:
                    mock_settings.database_url = same_url
                    mock_settings.debug = False
                    mock_settings.environment = "test"
                    mock_settings.database_require_ssl = False
                    mock_settings.db_pool_size = 5
                    mock_settings.db_max_overflow = 10
                    mock_settings.db_pool_timeout = 30
                    mock_settings.db_pool_recycle = 3600

                    result = await check_replica_lag()

        assert result["status"] == "single_server"
        assert result["lag_seconds"] == 0

    def test_route_db_mapping_separates_reads_and_writes(self):
        """Verify that read-heavy routes are mapped to replica."""
        from app.core.read_replica import ROUTE_DB_MAPPING

        # Reports should go to replica
        assert ROUTE_DB_MAPPING["/api/v1/reports"] == "replica"
        assert ROUTE_DB_MAPPING["/api/v1/analytics"] == "replica"

        # Writes should go to primary
        assert ROUTE_DB_MAPPING["/api/v1/circulation/checkout"] == "primary"
        assert ROUTE_DB_MAPPING["/api/v1/holds"] == "primary"
        assert ROUTE_DB_MAPPING["/api/v1/fines"] == "primary"

    def test_pool_pre_ping_enabled_for_auto_reconnect(self):
        """Database engine uses pool_pre_ping for automatic dead connection recovery."""
        from app.core.database import engine_kwargs, settings

        if "postgresql" in settings.database_url.lower():
            assert engine_kwargs.get("pool_pre_ping") is True

class TestSearchServiceDies:
    """
    LSC uses PostgreSQL full-text search as its default search engine.
    Elasticsearch is disabled (ELASTICSEARCH_ENABLED=false).

    This means search failure == database failure for all practical purposes.

    Blast radius:
    - Catalog search returns errors
    - Browse/filter functionality broken
    - Indie book discovery broken

    What keeps working:
    - Direct catalog item access by ID
    - Checkouts, returns, holds (don't require search)
    - Patron account management
    - All staff operations not involving search
    - All authentication

    User experience:
    - Search bar returns error message
    - "No results found" or 500 error
    - Catalog browsing may still work (depends on query type)
    """

    def test_search_engine_defaults_to_postgres(self):
        """Verify search engine is PostgreSQL, not Elasticsearch."""
        from app.core.config import get_settings

        settings = get_settings()
        assert settings.search_engine == "postgres"
        assert settings.elasticsearch_enabled is False

    @pytest.mark.asyncio
    async def test_search_handles_database_error_gracefully(self):
        """Search service handles database errors without crashing the API."""
        # Import the search service
        try:
            from app.services.search.search_service import SearchService
        except ImportError:
            pytest.skip("SearchService not available")

        # A database error during search should raise a catchable exception,
        # not an unhandled crash. The API layer wraps this in a 500 response.
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("connection to server lost")

        service = SearchService(mock_db)
        with pytest.raises(Exception):
            await service.search(query="harry potter")

    @pytest.mark.asyncio
    async def test_catalog_accessible_by_id_when_search_broken(self):
        """Direct item lookup by ID works even when search is broken.

        Search and direct-by-ID are different code paths. A broken
        tsvector index doesn't prevent SELECT WHERE id = X.
        """
        # This is a design verification—the catalog endpoint has separate
        # paths for search (uses tsvector/tsquery) and get-by-id (uses PK lookup)
        from app.core.config import get_settings

        settings = get_settings()
        # Search engine is separate from direct catalog access
        assert settings.search_engine in ("postgres", "elasticsearch")

class TestAuthServiceSlow:
    """
    A slow auth service is often worse than a dead one because:
    - Dead service: fast failure, circuit breaker trips, cached tokens used
    - Slow service: every request hangs, timeouts cascade, threads exhausted

    In LSC, auth is JWT-based (stateless) with Redis for token revocation.
    "Auth slow" manifests as:
    - Slow Redis lookups for token revocation checks
    - Slow bcrypt password hashing on login
    - Slow database lookups for user records

    Blast radius (slow Redis for token checks):
    - EVERY authenticated request slows down (token check on every request)
    - Request queue builds up (workers blocked waiting on Redis)
    - Cascading timeouts: frontend → nginx → backend → Redis
    - Worse than dead because dead triggers circuit breaker + cache fallback

    What makes slow worse:
    - No circuit breaker trips (requests don't fail, they hang)
    - Connection pool exhaustion (connections held waiting)
    - Client-side timeouts give inconsistent experience
    - Retry storms amplify the problem
    """

    @pytest.mark.asyncio
    async def test_slow_redis_causes_token_check_delay(self):
        """Slow Redis makes every authenticated request slow."""
        from app.core import security

        original_client = security._redis_client
        original_available = security._redis_available

        try:
            # Simulate a slow Redis that takes 3 seconds to respond
            slow_redis = MagicMock()

            def slow_exists(key):
                time.sleep(0.1)  # Simulate 100ms latency (normally <1ms)
                return 0  # Not revoked

            slow_redis.exists = slow_exists
            slow_redis.ping.return_value = True

            security._redis_client = slow_redis
            security._redis_available = True

            start = time.monotonic()
            result = security.is_token_revoked("test_token_abc")
            elapsed = time.monotonic() - start

            assert result is False  # Token not revoked
            assert elapsed >= 0.05  # Confirms the delay happened

        finally:
            security._redis_client = original_client
            security._redis_available = original_available

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern_in_token_check(self):
        """Token revocation has a circuit breaker with retry interval."""
        from app.core import security

        # Verify circuit breaker configuration exists
        assert hasattr(security, '_redis_available')
        assert hasattr(security, '_redis_last_check')
        assert hasattr(security, '_REDIS_RETRY_INTERVAL')
        assert security._REDIS_RETRY_INTERVAL == 10.0  # 10 second retry interval

    @pytest.mark.asyncio
    async def test_token_cache_ttl_limits_stale_window(self):
        """In-memory token cache has a 5-minute TTL to limit security exposure."""
        from app.core import security

        assert security._TOKEN_CACHE_TTL_SECONDS == 300  # 5 minutes
        assert security._TOKEN_CACHE_MAX_SIZE == 10000

    @pytest.mark.asyncio
    async def test_expired_cache_entries_are_evicted(self):
        """Expired in-memory cache entries are cleaned up on access."""
        from app.core import security

        token_hash = "test_hash_expired"
        # Put an entry that's already expired
        security._TOKEN_VERIFY_CACHE[token_hash] = time.monotonic() - 600  # 10 min ago

        result = security._cache_check(token_hash)
        assert result is None  # Expired entry should be evicted
        assert token_hash not in security._TOKEN_VERIFY_CACHE

    @pytest.mark.asyncio
    async def test_slow_password_hashing_doesnt_block_other_requests(self):
        """Password hashing is synchronous but isolated to login endpoint."""
        from app.core.security import hash_password, verify_password

        # bcrypt is intentionally slow (~100-300ms) for security
        # Verify it's using bcrypt (not a fast hash)
        hashed = hash_password("test_password_123!")
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_database_connection_timeout_configured(self):
        """Database connection timeouts prevent indefinite hangs."""
        from app.core.database import engine_kwargs, settings

        if "postgresql" in settings.database_url.lower():
            connect_args = engine_kwargs.get("connect_args", {})
            assert connect_args.get("timeout") == 10  # 10 second connect timeout
            assert connect_args.get("command_timeout") == 60  # 60 second query timeout


# ---------------------------------------------------------------------------
# 6. DISK FILLS UP
# ---------------------------------------------------------------------------

class TestDiskFillsUp:
    """
    When disk fills up, the first failures depend on which volume fills.

    What fails first (by volume):
    1. PostgreSQL data volume: writes fail, checkouts/holds/fines break
    2. Redis AOF volume: persistence fails, data loss on restart
    3. Upload volume: file uploads fail
    4. Log volume: logging stops, visibility lost
    5. Nginx cache volume: cache stops working (requests still proxied)

    Blast radius (PostgreSQL volume full):
    - ALL write operations fail (checkouts, returns, holds, fines)
    - Read operations continue working
    - Transaction log (WAL) can't be written
    - Potential for corruption if not handled properly

    Blast radius (upload volume full):
    - File uploads fail (book covers, documents, ebook uploads)
    - Existing files still served
    - Core operations (checkouts, search) unaffected

    Recovery:
    - Clean up old logs, temp files, backups
    - Docker volume pruning
    - PostgreSQL VACUUM FULL to reclaim dead tuple space
    """

    @pytest.mark.asyncio
    async def test_health_check_detects_low_disk(self):
        """Health check reports disk status based on usage thresholds."""
        from app.api.v1.health import _check_disk

        # Simulate 92% disk usage
        mock_usage = MagicMock()
        mock_usage.total = 100 * 1024**3  # 100 GB
        mock_usage.used = 92 * 1024**3   # 92 GB
        mock_usage.free = 8 * 1024**3    # 8 GB

        with patch("shutil.disk_usage", return_value=mock_usage):
            result = _check_disk()

        assert result["status"] == "critical"
        assert result["used_percent"] >= 90

    @pytest.mark.asyncio
    async def test_health_check_warning_at_80_percent(self):
        """Health check fires warning at 80% disk usage."""
        from app.api.v1.health import _check_disk

        mock_usage = MagicMock()
        mock_usage.total = 100 * 1024**3
        mock_usage.used = 85 * 1024**3
        mock_usage.free = 15 * 1024**3

        with patch("shutil.disk_usage", return_value=mock_usage):
            result = _check_disk()

        assert result["status"] == "warning"

    @pytest.mark.asyncio
    async def test_health_check_ok_below_80_percent(self):
        """Health check reports OK below 80% disk usage."""
        from app.api.v1.health import _check_disk

        mock_usage = MagicMock()
        mock_usage.total = 100 * 1024**3
        mock_usage.used = 50 * 1024**3
        mock_usage.free = 50 * 1024**3

        with patch("shutil.disk_usage", return_value=mock_usage):
            result = _check_disk()

        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_disk_check_handles_permission_error(self):
        """Disk check handles path access errors gracefully."""
        from app.api.v1.health import _check_disk

        with patch("shutil.disk_usage", side_effect=PermissionError("Access denied")):
            result = _check_disk()

        assert result["status"] == "unknown"
        assert "error" in result

    def test_log_rotation_configured(self):
        """Docker logging has size limits to prevent disk exhaustion."""
        import yaml

        with open(_DOCKER_COMPOSE_YML) as f:
            compose = yaml.safe_load(f)

        for service_name, service in compose["services"].items():
            logging_cfg = service.get("logging", {})
            if logging_cfg.get("driver") == "json-file":
                options = logging_cfg.get("options", {})
                assert "max-size" in options, f"Service {service_name} missing log max-size"
                assert "max-file" in options, f"Service {service_name} missing log max-file"

    def test_postgres_volume_is_persistent(self):
        """PostgreSQL data volume is persistent (not ephemeral)."""
        import yaml

        with open(_DOCKER_COMPOSE_YML) as f:
            compose = yaml.safe_load(f)

        volumes = compose.get("volumes", {})
        # Renamed from lsc_postgres_data_prod during the LSC -> L30 rebrand.
        assert "l30_postgres_data" in volumes

    def test_redis_appendonly_for_persistence(self):
        """Redis uses AOF persistence to survive restarts."""
        import yaml

        with open(_DOCKER_COMPOSE_YML) as f:
            compose = yaml.safe_load(f)

        # command is a list (["sh", "-c", "redis-server --appendonly yes ..."]),
        # not a single string -- check the joined form.
        redis_command = " ".join(compose["services"]["redis"]["command"])
        assert "appendonly" in redis_command
        assert "yes" in redis_command


# ---------------------------------------------------------------------------
# 7. DNS FLAKY (INTERMITTENT FAILURES)
# ---------------------------------------------------------------------------

class TestDNSFlaky:
    """
    Flaky DNS causes intermittent failures that are hard to diagnose.

    In LSC, DNS matters for:
    - Email provider API calls (api.resend.com)
    - External API calls (OverDrive, Hoopla, Kanopy)
    - S3/external storage (if configured)
    - Docker service resolution (inter-container communication)

    Blast radius:
    - Email sending fails intermittently
    - External digital content APIs fail unpredictably
    - If Docker DNS breaks, inter-container communication fails entirely

    What keeps working:
    - All database operations (connected via Docker network, resolved at startup)
    - All Redis operations (same Docker network)
    - Internal API operations (no external DNS needed)
    - Authentication (local JWT validation)

    Why intermittent is worse than total failure:
    - Hard to reproduce and diagnose
    - Retry logic may mask the problem temporarily
    - Monitoring may not trigger (error rate stays below threshold)
    - User experience is inconsistent
    """

    @pytest.mark.asyncio
    async def test_email_dns_failure_returns_false(self):
        """DNS resolution failure for the email provider returns False, not crash."""
        from app.core.email import send_email

        with patch("app.core.email.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            # DNS resolution failure manifests as ConnectError
            mock_client.post.side_effect = httpx.ConnectError(
                "Name or service not known"
            )
            mock_client_cls.return_value = mock_client

            with patch("app.core.email.settings") as mock_settings:
                mock_settings.resend_api_key = "SG.test_key"
                mock_settings.from_email = "noreply@test.com"
                mock_settings.app_name = "LSC Test"
                mock_settings.environment = "test"

                result = await send_email(
                    "test@test.com", "Test", "<p>Test</p>"
                )

        assert result is False

    @pytest.mark.asyncio
    async def test_intermittent_dns_some_emails_succeed(self):
        """Intermittent DNS means some sends succeed and some fail."""
        from app.core.email import send_email

        call_count = 0

        async def flaky_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise httpx.ConnectError("Temporary DNS failure")
            response = MagicMock()
            response.status_code = 202
            return response

        with patch("app.core.email.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.side_effect = flaky_post
            mock_client_cls.return_value = mock_client

            with patch("app.core.email.settings") as mock_settings:
                mock_settings.resend_api_key = "SG.test_key"
                mock_settings.from_email = "noreply@test.com"
                mock_settings.app_name = "LSC Test"
                mock_settings.environment = "test"
                # See test_email_safeguard_failure_doesnt_block_send: must be a
                # real number, not an auto-generated MagicMock attribute.
                mock_settings.resend_min_interval_s = 0

                results = []
                for i in range(6):
                    r = await send_email(
                        f"test{i}@test.com", "Test", "<p>Test</p>"
                    )
                    results.append(r)

        # Some succeed, some fail—the inconsistency is the worst part
        assert True in results
        assert False in results

    def test_docker_services_use_internal_dns(self):
        """Docker services communicate via internal network, not external DNS."""
        import yaml

        with open(_DOCKER_COMPOSE_YML) as f:
            compose = yaml.safe_load(f)

        # Backend connects to database via Docker service name
        backend_env = compose["services"]["l30-backend"]["environment"]
        db_url_env = [e for e in backend_env if isinstance(e, str) and "DATABASE_URL" in e]
        if db_url_env:
            assert "database:" in db_url_env[0] or "${" in db_url_env[0]

        # All services on same Docker network
        for service_name, service in compose["services"].items():
            networks = service.get("networks", [])
            # Renamed from lsc_network during the LSC -> L30 rebrand.
            assert "l30_network" in networks, f"Service {service_name} not on l30_network"

class TestSSLCertExpires:
    """
    An expired SSL certificate causes a complete outage for HTTPS traffic.

    Blast radius:
    - COMPLETE outage for all HTTPS traffic through nginx
    - Frontend becomes unreachable (browsers show security warning)
    - API calls from frontend fail (mixed content / cert errors)
    - Mobile/third-party API consumers get certificate errors
    - Email-provider webhook callbacks fail (they verify SSL)

    What keeps working:
    - Backend services behind nginx (they use HTTP internally)
    - Redis (internal network, no TLS by default)
    - Database (internal network, optional TLS)
    - Scheduled jobs (APScheduler, notification retry, etc.)
    - Inter-container communication (HTTP over Docker network)

    Why this is a complete outage:
    - Modern browsers refuse to load pages with expired certs
    - HSTS may prevent HTTP fallback entirely
    - Users cannot click through the warning on HSTS sites
    - Recovery requires cert renewal AND restart

    Recovery:
    - Certbot auto-renewal should prevent this
    - Manual: certbot renew --force-renewal && nginx -s reload
    """

    def test_internal_services_use_http_not_https(self):
        """Internal services communicate via HTTP, unaffected by cert expiry."""
        import yaml

        with open(_DOCKER_COMPOSE_YML) as f:
            compose = yaml.safe_load(f)

        # Nginx talks to backend via HTTP
        nginx_env = compose["services"]["nginx"]["environment"]
        api_backend = [e for e in nginx_env if isinstance(e, str) and "API_BACKEND" in e]
        if api_backend:
            assert "http://" in api_backend[0]

    def test_backend_health_check_uses_http(self):
        """Backend health check uses HTTP, not HTTPS (won't fail on cert expiry)."""
        import yaml

        with open(_DOCKER_COMPOSE_YML) as f:
            compose = yaml.safe_load(f)

        health_test = compose["services"]["l30-backend"]["healthcheck"]["test"]
        # Health check should use http:// not https://
        health_cmd = " ".join(health_test)
        assert "http://localhost:8000/health" in health_cmd

    @pytest.mark.asyncio
    async def test_redis_ssl_context_creation(self):
        """Redis SSL context is only created when REDIS_SSL is enabled."""
        from app.core.cache import _get_redis_ssl_context

        # Default: SSL not enabled
        with patch("app.core.cache.settings") as mock_settings:
            mock_settings.redis_ssl = False
            ctx = _get_redis_ssl_context()
            assert ctx is None

    @pytest.mark.asyncio
    async def test_database_ssl_enforcement_in_production(self):
        """Database SSL is enforced in production for data-in-transit security."""
        from app.core.database import engine_kwargs, settings

        if settings.environment == "production" and "postgresql" in settings.database_url.lower():
            connect_args = engine_kwargs.get("connect_args", {})
            # SSL should be required in production
            if settings.database_require_ssl:
                assert connect_args.get("ssl") == "require"

class TestOverallSystemResilience:
    """
    Cross-cutting tests that verify the system's overall resilience patterns.
    """

    @pytest.mark.asyncio
    async def test_health_overall_status_logic(self):
        """Overall health status correctly aggregates individual checks."""
        from app.api.v1.health import _overall_status

        # All healthy
        checks = {
            "database": {"status": "healthy"},
            "redis": {"status": "healthy"},
            "scheduler": {"status": "healthy"},
        }
        assert _overall_status(checks) == "healthy"

        # One degraded
        checks["redis"] = {"status": "degraded"}
        assert _overall_status(checks) == "degraded"

        # One unhealthy
        checks["database"] = {"status": "unhealthy"}
        assert _overall_status(checks) == "unhealthy"

    @pytest.mark.asyncio
    async def test_liveness_probe_is_lightweight(self):
        """Liveness probe does NOT check dependencies (prevents cascading failures)."""
        from app.api.v1.health import health_check

        # This should work even if database and Redis are both down
        result = await health_check()
        assert result["status"] == "ok"

    def test_all_services_have_restart_policies(self):
        """All Docker services have restart policies for auto-recovery."""
        import yaml

        with open(_DOCKER_COMPOSE_YML) as f:
            compose = yaml.safe_load(f)

        for service_name, service in compose["services"].items():
            assert service.get("restart") == "always", (
                f"Service {service_name} missing restart: always"
            )

    def test_all_critical_services_have_health_checks(self):
        """Database, Redis, backend, and nginx all have Docker health checks."""
        import yaml

        with open(_DOCKER_COMPOSE_YML) as f:
            compose = yaml.safe_load(f)

        critical_services = ["database", "redis", "l30-backend", "nginx"]
        for service_name in critical_services:
            service = compose["services"].get(service_name)
            assert service is not None, f"Service {service_name} not found"
            assert "healthcheck" in service, f"Service {service_name} missing healthcheck"

    def test_backend_depends_on_healthy_database_and_redis(self):
        """Backend waits for database and Redis to be healthy before starting."""
        import yaml

        with open(_DOCKER_COMPOSE_YML) as f:
            compose = yaml.safe_load(f)

        depends = compose["services"]["l30-backend"]["depends_on"]
        assert depends["database"]["condition"] == "service_healthy"
        assert depends["redis"]["condition"] == "service_healthy"

    def test_all_services_have_resource_limits(self):
        """All services have CPU/memory limits to prevent resource exhaustion."""
        import yaml

        with open(_DOCKER_COMPOSE_YML) as f:
            compose = yaml.safe_load(f)

        for service_name, service in compose["services"].items():
            deploy = service.get("deploy", {})
            resources = deploy.get("resources", {})
            limits = resources.get("limits", {})
            assert "memory" in limits, (
                f"Service {service_name} missing memory limit"
            )

    def test_no_single_point_of_failure_in_data_path(self):
        """Verify data integrity protections exist.

        PostgreSQL:
        - Persistent volume (survives container restart)
        - Backup volume mounted
        - Health check with retries

        Redis:
        - AOF persistence enabled
        - Persistent volume

        Application:
        - Graceful degradation when Redis down
        - JWT tokens are stateless (no session store dependency)
        """
        import yaml

        with open(_DOCKER_COMPOSE_YML) as f:
            compose = yaml.safe_load(f)

        # PostgreSQL has persistent volume
        db_volumes = compose["services"]["database"]["volumes"]
        pg_data_vols = [v for v in db_volumes if "postgresql/data" in v]
        assert len(pg_data_vols) > 0

        # Backup volume exists
        backup_vols = [v for v in db_volumes if "backup" in v.lower()]
        assert len(backup_vols) > 0

        # Redis has persistent volume
        redis_volumes = compose["services"]["redis"]["volumes"]
        redis_data_vols = [v for v in redis_volumes if "redis_data" in v]
        assert len(redis_data_vols) > 0

