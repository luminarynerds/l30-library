# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Conftest for app/tests - provides database fixtures for integration tests.
Uses the same PostgreSQL test database as tests/conftest.py.
"""

import contextlib
import os

# Derive test DB URL from the app's DATABASE_URL (swap database name)
_app_db_url = os.environ.get("DATABASE_URL", "")
if _app_db_url and "asyncpg" in _app_db_url:
    _test_db_url = _app_db_url.rsplit("/", 1)[0] + "/l30_test"
else:
    _test_db_url = "postgresql+asyncpg://l30:l30@database:5432/l30_test"

os.environ["DATABASE_URL"] = _test_db_url
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("LOG_FORMAT", "text")
os.environ.setdefault("SENTRY_DSN", "")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
# TrustedHostMiddleware rejects the Host header TestClient/httpx send
# ("testserver") unless it's allow-listed here, producing a blanket
# "Invalid host header" 400 on every route for any test in this directory
# that drives a real client through the app. tests/conftest.py already
# sets this; app/tests/conftest.py never did.
os.environ.setdefault("TRUSTED_HOSTS", "localhost,test,testserver")

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_session_factory = None
_tables_created = False


def _get_engine():
    global _engine
    if _engine is None:
        # NullPool: pytest-asyncio uses a fresh event loop per test; a pooled
        # connection binds to the loop that opened it, so reuse on a later test
        # raises "Event loop is closed". NullPool opens a fresh connection per
        # checkout. Mirrors the fix in tests/conftest.py.
        from sqlalchemy.pool import NullPool
        _engine = create_async_engine(
            _test_db_url, echo=False, future=True, poolclass=NullPool,
        )
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


async def _ensure_tables():
    global _tables_created
    if not _tables_created:
        import app.models  # noqa: F401
        from app.core.database import Base
        async with _get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _tables_created = True


@pytest.fixture
async def db():
    """Provide an async database session for tests."""
    await _ensure_tables()
    session = _get_session_factory()()
    try:
        yield session
    finally:
        with contextlib.suppress(Exception):  # noqa: BLE001 - best-effort fixture cleanup
            await session.rollback()
        try:
            from sqlalchemy import text
            from app.core.database import Base
            for table in reversed(Base.metadata.sorted_tables):
                with contextlib.suppress(Exception):  # noqa: BLE001 - best-effort table truncate
                    await session.execute(text(f'DELETE FROM "{table.name}"'))
            await session.commit()
        except Exception:  # noqa: BLE001 - outer cleanup; swallow + rollback below
            with contextlib.suppress(Exception):  # noqa: BLE001 - best-effort rollback after failed commit
                await session.rollback()
        with contextlib.suppress(Exception):  # noqa: BLE001 - best-effort session close
            await session.close()


# ---------------------------------------------------------------------------
# Reset the loop-bound async redis singleton between tests.
#
# app/core/cache.py caches `redis_client` at module level; the first test that
# touches it binds the client (and its connection pool) to that test's event
# loop. pytest-asyncio gives every test a fresh loop, so any later test that
# hits redis crosses loops: "got Future attached to a different loop" /
# "Event loop is closed", and some redis reads block until timeout. Mirrors
# tests/conftest.py's fixture of the same name/purpose -- this directory has
# its own conftest.py and never inherited it.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
async def _reset_async_redis_singleton():
    yield
    import contextlib

    import app.core.cache as _cache

    client = _cache.redis_client
    if client is not None:
        # aclose() on redis>=5, close() as fallback; any failure is fine --
        # the point is just dropping the loop-bound client between tests.
        with contextlib.suppress(Exception):
            try:
                await client.aclose()
            except AttributeError:
                await client.close()
        _cache.redis_client = None
