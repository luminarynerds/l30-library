# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Smoke test: schema init creates the pgvector 'vector' extension.

Fork-forward fix — the dist compose now runs `pgvector/pgvector:pg16` (not
plain `postgres:16-alpine`) so embedding tables can build. This asserts the
raw-SQL init path (`scripts/init_schema_async_raw_sql.py`) actually issues
`CREATE EXTENSION IF NOT EXISTS vector` against a real Postgres, independent
of the full ORM/alembic-backed app test DB.

Requires a pgvector-capable Postgres reachable at DATABASE_URL (or
TEST_VECTOR_DATABASE_URL as an override) — the extension's shared library
must be present in the image, which plain postgres:16-alpine lacks. Skips
loudly (does not silently pass) if no such database is reachable.
"""
import os

import asyncpg
import pytest

from scripts.init_schema_async_raw_sql import ensure_vector_extension, _parse_db_url

pytestmark = pytest.mark.smoke

VECTOR_DATABASE_URL = os.environ.get("TEST_VECTOR_DATABASE_URL") or os.environ.get(
    "DATABASE_URL", ""
)


@pytest.fixture
async def vector_conn():
    if not VECTOR_DATABASE_URL:
        pytest.skip(
            "No TEST_VECTOR_DATABASE_URL or DATABASE_URL set; cannot reach a "
            "pgvector-capable Postgres for this smoke test."
        )
    conn_kwargs = _parse_db_url(VECTOR_DATABASE_URL)
    try:
        conn = await asyncpg.connect(**conn_kwargs, timeout=10)
    except Exception as e:
        pytest.skip(f"Could not connect to test Postgres for vector smoke test: {e}")
        return
    try:
        # Start from a clean slate so this test proves creation, not reuse.
        # If the extension has dependent objects (embedding columns/tables), we
        # are pointed at a real/shared database, not an isolated CI vector DB.
        # Refuse the destructive drop and skip loudly rather than CASCADE away
        # production embeddings. Point TEST_VECTOR_DATABASE_URL at a dedicated
        # pgvector database to actually exercise this path.
        try:
            await conn.execute("DROP EXTENSION IF EXISTS vector")
        except asyncpg.exceptions.DependentObjectsStillExistError:
            pytest.skip(
                "pgvector extension has dependent objects on this database; "
                "refusing a destructive DROP on a shared/real DB. Set "
                "TEST_VECTOR_DATABASE_URL to an isolated pgvector database to run "
                "this smoke test."
            )
        yield conn
    finally:
        await conn.close()


async def test_init_creates_vector_extension(vector_conn):
    exists_before = await vector_conn.fetchval(
        "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
    )
    assert exists_before is None, "test setup failed to drop pre-existing extension"

    await ensure_vector_extension(vector_conn)

    exists_after = await vector_conn.fetchval(
        "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
    )
    assert exists_after == 1


async def test_init_creates_vector_extension_is_idempotent(vector_conn):
    await ensure_vector_extension(vector_conn)
    # Second call must not raise even though the extension now exists.
    await ensure_vector_extension(vector_conn)

    exists = await vector_conn.fetchval(
        "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
    )
    assert exists == 1
