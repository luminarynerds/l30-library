# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Pytest configuration and fixtures for L30 Library tests.
"""

import asyncio
import os
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

# Set test environment variables BEFORE importing app modules
# Derive test DB URL from the app's DATABASE_URL (just swap the database name)
_app_db_url = os.environ.get("DATABASE_URL", "")
# True when the caller (a deploy/test recipe, CI, a dev's shell) explicitly
# pointed DATABASE_URL at a real Postgres instance -- as opposed to running
# pytest with no DATABASE_URL at all (bare local dev convenience path).
_dev_db_url_explicit = bool(_app_db_url) and "asyncpg" in _app_db_url
if _dev_db_url_explicit:
    # Replace the production database name with the test database name
    _postgres_url = _app_db_url.rsplit("/", 1)[0] + "/l30_test"
else:
    _postgres_url = os.environ.get("TEST_DATABASE_URL", "postgresql+asyncpg://l30:l30@database:5432/l30_test")
TEST_DATABASE_URL = _postgres_url
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("LOG_FORMAT", "text")
os.environ.setdefault("SENTRY_DSN", "")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("STORAGE_LOCAL_PATH", "/tmp/l30_test_uploads")
os.environ.setdefault("TRUSTED_HOSTS", "localhost,test,testserver")
# MetisLib integration - enable with mock client for tests
os.environ.setdefault("METISLIB_ENABLED", "true")
os.environ.setdefault("METISLIB_MOCK", "true")
os.environ.setdefault("METISLIB_BASE_URL", "http://localhost:8803")
os.environ.setdefault("METISLIB_API_KEY", "test-metislib-key")
os.environ.setdefault("METISLIB_LIBRARY_ID", "l30_test")
os.environ.setdefault("METISLIB_TIMEOUT_SECONDS", "5")


def _check_database_availability_sync(db_url: str) -> bool:
    """Check if a database is available (synchronous version)."""
    if db_url.startswith("sqlite"):
        return True

    try:
        # SQLAlchemy 2.1 defaults bare PostgreSQL URLs to psycopg 3.
        # This project declares psycopg2-binary, so select it explicitly.
        sync_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace("+aiosqlite", "")
        from sqlalchemy import create_engine, text
        engine = create_engine(sync_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception as e:
        print(f"\n⚠️  PostgreSQL connection failed: {e}")
        return False


def _get_working_database_url():
    """Get a working database URL, falling back to SQLite if PostgreSQL unavailable."""
    # Try PostgreSQL first
    if _check_database_availability_sync(_postgres_url):
        return _postgres_url
    # Refuse to silently fall back when a real Postgres run is required. A silent
    # SQLite fallback yields a misleading inventory (SQLite != Postgres behavior)
    # -- e.g. SQLite returns naive datetimes where Postgres returns tz-aware
    # ones, cascading into hundreds of unrelated-looking failures. Required
    # whenever TEST_REQUIRE_POSTGRES is set explicitly, OR whenever the caller
    # already gave us an explicit Postgres DATABASE_URL (_dev_db_url_explicit):
    # a transient connectivity hiccup there (bad password, DB not yet
    # migrated, network blip) must fail loud, not quietly degrade a whole
    # multi-hour run into SQLite-flavored noise.
    if os.environ.get("TEST_REQUIRE_POSTGRES") or _dev_db_url_explicit:
        target = _postgres_url.rsplit("@", 1)[-1]
        raise RuntimeError(
            "PostgreSQL is unreachable at "
            f"{target} but an explicit Postgres DATABASE_URL was provided "
            "(or TEST_REQUIRE_POSTGRES is set). Refusing to silently fall "
            "back to SQLite -- fix the connection (check the password, "
            "confirm the target database exists) instead of ignoring this."
        )
    # Fall back to SQLite with file-based storage
    sqlite_url = "sqlite+aiosqlite:////tmp/lsc_test.db"
    print("\n⚠️  PostgreSQL unavailable, falling back to SQLite file-based database")
    return sqlite_url


# Global variable for actual database URL (set by pytest_configure)
_actual_database_url = TEST_DATABASE_URL


def pytest_configure(config):
    """Initialize database configuration at pytest startup."""
    global _actual_database_url
    # Use a simple approach: just try the default URL first
    # The actual database URL detection happens lazily in pytest_sessionstart
    _actual_database_url = TEST_DATABASE_URL
    os.environ["DATABASE_URL"] = _actual_database_url


def pytest_sessionstart(session):
    """Initialize database at session start."""
    global _actual_database_url
    # Use synchronous database URL detection to avoid event loop issues
    _actual_database_url = _get_working_database_url()
    os.environ["DATABASE_URL"] = _actual_database_url


# Shared engine and session factory - created lazily
_engine = None
_session_factory = None
_tables_created = False


def get_engine():
    global _engine
    if _engine is None:
        from sqlalchemy.pool import NullPool

        engine_kwargs = {
            "echo": False,
            "future": True,
        }

        if _actual_database_url.startswith("sqlite"):
            # SQLite-specific configuration: use NullPool to avoid connection issues
            # SQLite doesn't support concurrent connections well, so we use NullPool
            # which creates a new connection for each request and doesn't pool them
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            engine_kwargs["poolclass"] = NullPool
        else:
            # PostgreSQL: use NullPool so each operation gets a fresh connection.
            # pytest-asyncio uses a fresh event loop per test, but a
            # pooled connection binds to the loop that opened it. Reusing it on a
            # later test raises "Event loop is closed". NullPool opens a fresh
            # connection per checkout, mirroring the SQLite branch above.
            engine_kwargs["poolclass"] = NullPool

        _engine = create_async_engine(_actual_database_url, **engine_kwargs)

        if _actual_database_url.startswith("sqlite"):
            from sqlalchemy import event

            @event.listens_for(_engine.sync_engine, "connect")
            def _register_icu_collation(dbapi_connection, connection_record):
                # Catalog search orders with COLLATE "und-x-icu" (a PostgreSQL
                # ICU collation). SQLite has no such collation, so register a
                # plain binary-comparison stand-in on every connection.
                # dbapi_connection is SQLAlchemy's aiosqlite adapter, which has
                # no create_collation passthrough; reach the raw sqlite3
                # connection at ._connection._conn (the same access path the
                # dialect itself uses for isolation_level). Safe cross-thread
                # because connect_args sets check_same_thread=False.
                raw_conn = dbapi_connection._connection._conn
                raw_conn.create_collation(
                    "und-x-icu", lambda a, b: (a > b) - (a < b)
                )
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
        _session_factory = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


async def ensure_tables_created():
    global _tables_created
    if not _tables_created:
        # For SQLite test databases, clean up old database file to ensure fresh start
        if _actual_database_url.startswith("sqlite"):
            import os
            # Extract file path from sqlite URL
            db_path = _actual_database_url.replace("sqlite+aiosqlite://", "")
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                    print(f"✅ Removed old SQLite test database: {db_path}")
                except Exception as e:
                    print(f"⚠️  Could not remove old database: {e}")

        # Try to use Alembic migrations if available, otherwise use raw table creation
        from tests.database_setup import initialize_test_database

        if not await initialize_test_database(_actual_database_url, use_alembic=True):
            raise RuntimeError("Test database schema initialization failed; see setup output.")
        _tables_created = True


@pytest.fixture
async def test_db():
    """Create a test database session with cleanup between tests.

    Ensures proper resource management to prevent connection pool exhaustion
    when running 195+ tests in parallel.
    """
    await ensure_tables_created()

    SessionLocal = get_session_factory()
    session = SessionLocal()

    try:
        yield session
    finally:
        # Ensure all pending transactions are rolled back before closing
        # This prevents connection leaks when tests fail or don't clean up
        try:
            await session.rollback()
        except Exception:
            # Ignore rollback errors - connection may already be in a bad state
            pass

        # Clean up test data BEFORE closing the session to avoid creating new connections
        # during event loop shutdown. This prevents "Event loop is closed" errors with
        # SQLite's NullPool where threads may try to use a closed event loop.
        try:
            from sqlalchemy import text
            from app.core.database import Base

            # Disable FK constraints temporarily (SQLite only)
            if _actual_database_url.startswith("sqlite"):
                await session.execute(text('PRAGMA foreign_keys = OFF'))

            if _actual_database_url.startswith("sqlite"):
                # Delete from all tables in reverse order (respecting FK dependencies)
                for table in reversed(Base.metadata.sorted_tables):
                    try:
                        await session.execute(text(f'DELETE FROM "{table.name}"'))
                    except Exception:
                        # Individual table cleanup failures shouldn't break tests
                        pass
            else:
                # PostgreSQL: per-table DELETE silently fails on FK violations
                # (exceptions swallowed), leaking rows (e.g. users) into the
                # next test. TRUNCATE-all needs one lock per table and blows
                # max_locks_per_transaction, so instead skip FK checks for the
                # cleanup (superuser only; falls back to plain deletes).
                # Any statement error (missing table, FK violation) aborts the
                # whole PG transaction and silently kills every later DELETE,
                # so: skip tables that don't exist, and disable FK checks.
                res = await session.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                )
                existing = {row[0] for row in res}
                await session.execute(text("SET session_replication_role = replica"))
                for table in reversed(Base.metadata.sorted_tables):
                    if table.name in existing:
                        await session.execute(text(f'DELETE FROM "{table.name}"'))
                await session.execute(text("SET session_replication_role = DEFAULT"))

            # Re-enable FK constraints (SQLite only)
            if _actual_database_url.startswith("sqlite"):
                await session.execute(text('PRAGMA foreign_keys = ON'))

            # Commit the cleanup operations
            await session.commit()
        except Exception:
            # Cleanup errors shouldn't break tests, but attempt rollback
            try:
                await session.rollback()
            except Exception:
                pass

        # Close the session to return connection to the pool
        # This is critical for preventing connection exhaustion
        try:
            await session.close()
        except Exception:
            # Ignore close errors - connection cleanup is best-effort
            pass


@pytest.fixture
async def client(test_db):
    """Create an async test client with overridden database dependency.

    Ensures proper cleanup of test client resources to prevent connection leaks.
    """
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        """Override database dependency to use test session."""
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    # Bypass FirstBootMiddleware: tests use an empty DB with no admin users,
    # which would otherwise trip the setup-required check and return 503 on
    # every request. Endpoint tests assume the app is past first-boot.
    app.state.setup_complete = True

    try:
        # Create AsyncClient with ASGITransport to connect to FastAPI app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as test_client:
            yield test_client
    finally:
        # Ensure dependency overrides are cleared even if test fails
        # This prevents contamination of subsequent tests
        try:
            app.dependency_overrides.clear()
        except Exception:
            pass


@pytest.fixture
async def db(test_db):
    """Alias for test_db fixture for compatibility with async tests."""
    return test_db


@pytest.fixture
async def db_session(test_db):
    """Alias for test_db fixture - used by strategic planning and other tests."""
    return test_db


@pytest.fixture
def test_user_data():
    return {
        "email": "testuser@example.com",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.fixture
def test_staff_data():
    return {
        "email": "staff@example.com",
        "password": "StaffPassword123!",
        "first_name": "Staff",
        "last_name": "Member",
    }


@pytest.fixture
def test_admin_data():
    return {
        "email": "admin@example.com",
        "password": "AdminPassword123!",
        "first_name": "Admin",
        "last_name": "User",
    }


@pytest.fixture
async def test_patron(test_db, test_user_data):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email=test_user_data["email"],
        password_hash=hash_password(test_user_data["password"]),
        first_name=test_user_data["first_name"],
        last_name=test_user_data["last_name"],
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_staff(test_db, test_staff_data):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email=test_staff_data["email"],
        password_hash=hash_password(test_staff_data["password"]),
        first_name=test_staff_data["first_name"],
        last_name=test_staff_data["last_name"],
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_admin(test_db, test_admin_data):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email=test_admin_data["email"],
        password_hash=hash_password(test_admin_data["password"]),
        first_name=test_admin_data["first_name"],
        last_name=test_admin_data["last_name"],
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_catalog_item(test_db):
    from app.models.catalog import CatalogItem, ItemStatus

    item = CatalogItem(
        title="Test Book",
        author="Test Author",
        isbn="978-0-123456-78-9",
        description="A test book for unit testing",
        status=ItemStatus.available,
        call_number="TEST-001",
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def test_item_copy(test_db, test_catalog_item):
    from app.models.inventory import ItemCopy

    copy = ItemCopy(
        catalog_item_id=test_catalog_item.id,
        barcode="COPY-001",
        condition="excellent",
    )
    test_db.add(copy)
    await test_db.commit()
    await test_db.refresh(copy)
    return copy


@pytest.fixture
async def test_checkout(test_db, test_patron, test_catalog_item):
    from app.models.circulation import Checkout, CheckoutStatus

    checkout = Checkout(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=21),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


@pytest.fixture
async def test_hold(test_db, test_patron, test_catalog_item):
    from app.models.circulation import Hold, HoldStatus

    hold = Hold(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.pending,
        position=1,
        created_at=datetime.now(),
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)
    return hold


@pytest.fixture
async def test_fine(test_db, test_patron):
    from app.models.fine import Fine, FineStatus, FineType

    fine = Fine(
        user_id=test_patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("10.00"),
        amount_paid=Decimal("0.00"),
        description="Late return fine",
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)
    return fine


# ==================== Board-Specific User Fixtures ====================
# These fixtures are for board-related tests


@pytest.fixture
async def staff_user(test_db):
    """Create a staff user for board audit logging tests."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="staff.board@example.com",
        password_hash=hash_password("StaffPassword123!"),
        first_name="Board",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def board_member(test_db):
    """Create a board member user for attendance and voting tests."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="member.board@example.com",
        password_hash=hash_password("MemberPassword123!"),
        first_name="Board",
        last_name="Member",
        role=UserRole.PATRON,  # Board members can be regular patrons
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def admin_user(test_db):
    """Create an admin user for administrative board operations."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="admin.board@example.com",
        password_hash=hash_password("AdminPassword123!"),
        first_name="Board",
        last_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


# ==================== Token Helper Functions ====================
# These helpers are used in tests to get authentication tokens


async def get_admin_token(client, test_admin_data):
    """Helper to get admin authentication token."""
    login_data = {
        "username": test_admin_data["email"],
        "password": test_admin_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


async def get_staff_token(client, test_staff_data):
    """Helper to get staff authentication token."""
    login_data = {
        "username": test_staff_data["email"],
        "password": test_staff_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


async def get_patron_token(client, test_patron_data):
    """Helper to get patron authentication token."""
    login_data = {
        "username": test_patron_data["email"],
        "password": test_patron_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


# ==================== Lexile Test Fixtures ====================


@pytest.fixture
async def staff_client(test_db, test_staff):
    """Async HTTP client authenticated as a staff user."""
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return test_staff

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def public_client(test_db):
    """Async HTTP client with no authentication (public access)."""
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_optional_user
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_optional_user():
        return None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_optional_user] = override_get_optional_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_optional_user, None)


@pytest.fixture
async def sample_book_with_lexile(test_db):
    """A catalog item pre-loaded with lexile data (AD650L, numeric 650)."""
    from app.models.catalog import CatalogItem, ItemStatus, CatalogingStatus

    item = CatalogItem(
        title="Frog and Toad Are Friends",
        author="Arnold Lobel",
        status=ItemStatus.available,
        lexile_measure="AD650L",
        lexile_number=650,
        cataloging_status=CatalogingStatus.CATALOGED,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def books_across_lexile_range(test_db):
    """Five books with lexile_number 200, 500, 600, 800, 1100."""
    from app.models.catalog import CatalogItem, ItemStatus, CatalogingStatus

    books_data = [
        ("Low Lexile Book", "200L", 200),
        ("Mid-Low Lexile Book", "500L", 500),
        ("Mid Lexile Book", "600L", 600),
        ("High Lexile Book", "800L", 800),
        ("Very High Lexile Book", "1100L", 1100),
    ]
    items = []
    for title, measure, number in books_data:
        item = CatalogItem(
            title=title,
            author="Test Author",
            status=ItemStatus.available,
            lexile_measure=measure,
            lexile_number=number,
            cataloging_status=CatalogingStatus.CATALOGED,
        )
        test_db.add(item)
        items.append(item)
    await test_db.commit()
    for item in items:
        await test_db.refresh(item)
    return items


# ==================== Import Advanced Fixtures ====================
# Import composite fixtures from fixtures.py to make them available
# to all tests without explicit imports
# NOTE: pytest_plugins moved to root conftest.py to avoid deprecation warning

# Import external service mocking fixtures
pytest_plugins = ["tests.fixtures.external_services"]


@pytest.fixture
async def books_with_isbns(test_db):
    """Three books with known ISBNs and no lexile data, for bulk-import tests."""
    from app.models.catalog import CatalogItem, ItemStatus, CatalogingStatus

    books_data = [
        ("Bulk Test 1", "9780000000001"),
        ("Bulk Test 2", "9780000000002"),
        ("Bulk Test 3", "9780000000003"),
    ]
    items = []
    for title, isbn in books_data:
        item = CatalogItem(
            title=title,
            author="Test Author",
            isbn=isbn,
            status=ItemStatus.available,
            lexile_measure=None,
            lexile_number=None,
            cataloging_status=CatalogingStatus.CATALOGED,
        )
        test_db.add(item)
        items.append(item)
    await test_db.commit()
    for item in items:
        await test_db.refresh(item)
    return items


# ---------------------------------------------------------------------------
# Reset the loop-bound async redis singleton between tests.
#
# app/core/cache.py caches `redis_client` at module level; the first test that
# touches it binds the client (and its connection pool) to that test's event
# loop. pytest-asyncio gives every test a fresh loop, so any later test that
# hits redis crosses loops: "got Future attached to a different loop" /
# "Event loop is closed", and some redis reads block until timeout. Closing
# and clearing the singleton in teardown keeps client and loop aligned.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
async def _reset_async_redis_singleton():
    yield
    import app.core.cache as _cache

    client = _cache.redis_client
    if client is not None:
        try:
            await client.aclose()
        except AttributeError:
            try:
                await client.close()
            except Exception:
                pass
        except Exception:
            pass
        _cache.redis_client = None


# ---------------------------------------------------------------------------
# Dispose the production AsyncSessionLocal/engine connection pool between
# tests.
#
# app/core/database.py's module-level `engine` (created once at import time)
# is a real pooled engine with pool_pre_ping=True -- unlike this file's own
# get_engine(), it is NOT NullPool. Scheduler jobs that open their own session
# via `async with AsyncSessionLocal() as db:` (calculate_daily_overdue_fines,
# expire_old_holds, send_hold_expiration_reminders, ...) bind a pooled
# connection to whichever event loop was running when it was checked out.
# pytest-asyncio hands every test a fresh loop, so a later test that reuses
# the pooled connection fails the pre-ping health check with "Event loop is
# closed" (raised from asyncpg during connection checkout). Disposing the
# pool after each test forces the next one to open fresh connections on its
# own loop. Same rationale as _reset_async_redis_singleton above.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
async def _reset_production_db_engine_pool():
    yield
    from app.core.database import engine as _prod_engine

    try:
        await _prod_engine.dispose()
    except Exception:
        pass
