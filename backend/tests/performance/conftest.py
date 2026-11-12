# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Pytest fixtures for performance testing.

Provides:
- Query counter middleware for N+1 detection
- Slow query logger (>100ms threshold)
- Authenticated HTTP client fixtures
- Database-seeded test environment
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Environment setup (must happen before app imports)
# ---------------------------------------------------------------------------
# Respect an already-explicit Postgres DATABASE_URL (e.g. set by the test
# recipe/CI) instead of unconditionally stomping it. Unconditional overwrite
# used to replace a valid recipe DATABASE_URL with a hardcoded stale default
# (lsc:lsc_dev_pwd@localhost -- an old project's dev creds, not this one's),
# silently breaking every test collected after this conftest imported in the
# same pytest session.
_existing_db_url = os.environ.get("DATABASE_URL", "")
if _existing_db_url and "asyncpg" in _existing_db_url:
    _postgres_url = _existing_db_url
else:
    _postgres_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://lsc:lsc_dev_pwd@localhost:5432/lsc_test",
    )
os.environ["DATABASE_URL"] = _postgres_url
os.environ.setdefault("SECRET_KEY", "perf-test-secret-key")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("LOG_FORMAT", "text")
os.environ.setdefault("SENTRY_DSN", "")
os.environ.setdefault("DEBUG", "false")

logger = logging.getLogger("perf.queries")

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "benchmarks"
SLOW_QUERY_LOG = RESULTS_DIR / "slow_queries.log"
SLOW_QUERY_THRESHOLD_MS = 100  # Log queries slower than this


# ---------------------------------------------------------------------------
# Query counter - tracks queries per request for N+1 detection
# ---------------------------------------------------------------------------

@dataclass
class QueryTracker:
    """Tracks SQL query count and timing for a request scope."""

    queries: list = field(default_factory=list)
    _active: bool = False

    def start(self) -> None:
        self.queries = []
        self._active = True

    def stop(self) -> None:
        self._active = False

    @property
    def count(self) -> int:
        return len(self.queries)

    @property
    def total_ms(self) -> float:
        return sum(q["duration_ms"] for q in self.queries)

    @property
    def slow_queries(self) -> list:
        return [q for q in self.queries if q["duration_ms"] > SLOW_QUERY_THRESHOLD_MS]

    def record(self, statement: str, duration_ms: float) -> None:
        if not self._active:
            return
        self.queries.append({
            "statement": statement[:500],  # Truncate long queries
            "duration_ms": round(duration_ms, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


# Global tracker instance (per-test isolation via start/stop)
_query_tracker = QueryTracker()


def _setup_query_tracking(engine) -> None:
    """Attach SQLAlchemy event listeners for query tracking.

    Works with the sync connection underlying asyncpg.
    """
    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _before_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info["query_start"] = time.perf_counter()

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def _after_execute(conn, cursor, statement, parameters, context, executemany):
        start = conn.info.pop("query_start", None)
        if start is not None:
            duration_ms = (time.perf_counter() - start) * 1000
            _query_tracker.record(statement, duration_ms)

            # Slow query logging
            if duration_ms > SLOW_QUERY_THRESHOLD_MS:
                logger.warning(
                    "SLOW QUERY (%.1fms): %s",
                    duration_ms,
                    statement[:200],
                )
                _log_slow_query(statement, duration_ms)


def _log_slow_query(statement: str, duration_ms: float) -> None:
    """Append slow query to persistent log file."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_ms": round(duration_ms, 2),
        "statement": statement[:1000],
    }
    with open(SLOW_QUERY_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# REMOVED: Manual event_loop fixture removed to prevent conflicts with pytest-asyncio auto mode
# pytest-asyncio with asyncio_mode = "auto" automatically manages event loops per test function
# The manual session-scoped fixture was causing "Event loop is closed" errors because:
# 1. It created a session-wide loop that could be closed while tests were still running
# 2. It conflicted with pytest-asyncio's automatic loop management
# 3. SQLite connections in background threads would try to use the closed loop during cleanup


@pytest.fixture(scope="session")
def perf_engine():
    """Create a database engine for performance tests.

    Uses same pool configuration as unit tests to ensure consistent
    resource allocation across the test suite.
    """
    from sqlalchemy.pool import NullPool

    db_url = os.environ["DATABASE_URL"]
    engine_kwargs = {"echo": False}

    if "postgresql" in db_url:
        # Increased from 10/20 to 20/30 to match main test suite
        # Provides 50 total connections for parallel performance testing
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_size"] = 20
        engine_kwargs["max_overflow"] = 30
    elif "sqlite" in db_url:
        # Use NullPool for SQLite to avoid connection issues
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        engine_kwargs["poolclass"] = NullPool

    engine = create_async_engine(db_url, **engine_kwargs)
    _setup_query_tracking(engine)
    yield engine

    # Cleanup handled by event loop finalizer


@pytest.fixture(scope="session")
def perf_session_factory(perf_engine):
    """Session factory for performance tests."""
    return async_sessionmaker(
        perf_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest.fixture
async def perf_db(perf_session_factory):
    """Per-test database session."""
    async with perf_session_factory() as session:
        yield session


@pytest.fixture
def query_tracker():
    """Provides a fresh query tracker for each test.

    Usage in tests:
        def test_endpoint(query_tracker, perf_client):
            query_tracker.start()
            response = await perf_client.get("/api/v1/catalog")
            query_tracker.stop()
            assert query_tracker.count <= 5, f"Too many queries: {query_tracker.count}"
    """
    _query_tracker.start()
    yield _query_tracker
    _query_tracker.stop()


@pytest.fixture(scope="session")
async def perf_app(perf_engine, perf_session_factory):
    """FastAPI app configured for performance testing."""
    from app.core.database import get_db
    from app.main import app

    async def _override_get_db():
        async with perf_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
async def perf_client(perf_app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for performance tests."""
    transport = ASGITransport(app=perf_app)
    async with AsyncClient(transport=transport, base_url="http://perftest") as client:
        yield client


@pytest.fixture(scope="session")
async def auth_tokens(perf_client) -> dict:
    """Obtain auth tokens for patron and staff users.

    Returns a dict with 'patron' and 'staff' bearer tokens.
    Falls back to empty dicts if auth fails (endpoints will 401 gracefully).
    """
    tokens = {"patron": {}, "staff": {}}

    for role, email in [("patron", "patron@test.com"), ("staff", "staff@test.com")]:
        resp = await perf_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "password123"},
        )
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            if token:
                tokens[role] = {"Authorization": f"Bearer {token}"}

    return tokens


def assert_query_count(tracker: QueryTracker, max_queries: int, endpoint: str = "") -> None:
    """Assert that an endpoint did not exceed the query budget.

    Raises AssertionError with detailed query listing if exceeded.
    """
    if tracker.count <= max_queries:
        return

    query_details = "\n".join(
        f"  [{i+1}] ({q['duration_ms']:.1f}ms) {q['statement'][:120]}"
        for i, q in enumerate(tracker.queries)
    )
    raise AssertionError(
        f"N+1 REGRESSION: {endpoint} executed {tracker.count} queries "
        f"(max allowed: {max_queries})\n{query_details}"
    )
