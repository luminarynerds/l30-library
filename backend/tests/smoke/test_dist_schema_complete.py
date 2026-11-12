# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Smoke test: dist install schema completeness (Task 4).

Two independent defects from Task 1's characterization
(docs/dist-install-characterization.md), both exercised against a real
pgvector-capable Postgres, starting from an empty, throwaway database (a
fresh install):

1. §3 -- `_patch_create_table_sql`'s FK-strip comma bug silently dropped 22
   non-deferred tables with `syntax error at or near "FOREIGN"` (18 direct
   failures cascading to 4 more via "relation ... does not exist" on tables
   that FK to them).
2. §4/§5 -- `deferred_tables.txt` deferred 14 tables that a feature
   (semantic search, cover images) or a background scheduler/retention job
   needs unconditionally, even though nothing prevents creating them.

Requires a real Postgres reachable at TEST_SCHEMA_DATABASE_URL (or
DATABASE_URL) with the pgvector extension's shared library present (the dist
compose's pgvector/pgvector:pg16 image, or an equivalent disposable
container) -- skips loudly (does not silently pass) if unreachable. Mirrors
the `vector_conn` pattern in test_init_extension.py: raw asyncpg against the
init script's own functions, decoupled from the app's ORM/alembic/SQLite-
fallback `test_db` fixture in tests/conftest.py, since this is specifically
testing the raw-SQL fresh-install path (not the already-migrated app test
DB).

Isolation: this test creates and drops its OWN disposable database (via the
same server/credentials as TEST_SCHEMA_DATABASE_URL/DATABASE_URL) rather than
nuking the shared connection target's `public` schema. Earlier drafts did
`DROP SCHEMA public CASCADE` against the same Postgres the rest of
`tests/smoke/` shares in one `pytest -m smoke tests/smoke` run -- that only
worked by accident of alphabetical file-collection order, it dropped any
pg_trgm/pgcrypto extensions CI pre-installed on the shared test DB, and it
left un-deferred vector-typed tables (text_embeddings, author_embeddings)
behind afterward with no cleanup, which broke test_init_extension.py's
`DROP EXTENSION vector` (DependentObjectsStillExistError) whenever this file
ran first. An owned, disposable database sidesteps all three failure modes.
"""
import os
import uuid

import asyncpg
import pytest

import scripts.init_schema_async_raw_sql as init_schema_mod
from scripts.init_schema_async_raw_sql import _parse_db_url

pytestmark = pytest.mark.smoke

SCHEMA_DATABASE_URL = os.environ.get("TEST_SCHEMA_DATABASE_URL") or os.environ.get(
    "DATABASE_URL", ""
)

# §3: the 22 tables that failed via the FK-strip bug -- 18 direct
# "syntax error at or near FOREIGN" failures, plus 4 that cascade from
# engagement_surveys failing to create (their own FKs point at it).
FK_STRIP_TABLES = {
    "collection_items",
    "board_recusal_declarations",
    "board_minutes_amendments",
    "reading_list_requests",
    "library_visit_requests",
    "program_booklist",
    "course_stage_transitions",
    "legal_eligibility_thresholds",
    "engagement_surveys",
    "support_ticket_events",
    "parent_resource_guide_flags",
    "parent_connection_group_meetings",
    "home_visit_status_history",
    "parent_onboarding_followups",
    "parent_onboarding_referrals",
    "parent_onboarding_session_handouts",
    "outcome_indicators",
    "theory_of_change_claims",
    "engagement_survey_questions",
    "engagement_survey_responses",
    "engagement_user_demographics",
    "engagement_survey_outcomes",
}
assert len(FK_STRIP_TABLES) == 22

# §4/§5: minimal un-defer set (6 feature tables + 8 scheduler-stability tables,
# the latter including data_retention_policies -- queried unguarded by
# _get_legal_holds() ahead of run_all_retention_jobs()'s per-job try/except,
# so a missing table aborts the entire daily retention job).
UNDEFERRED_TABLES = {
    "text_embeddings",
    "author_embeddings",
    "hidden_gem_scores",
    "embedding_metadata",
    "semantic_search_cache",
    "catalog_images",
    "notification_queue",
    "coppa_compliance",
    "database_subscriptions",
    "indie_ebook_borrows",
    "journey_events",
    "role_settings",
    "transit_requests",
    "data_retention_policies",
}
assert len(UNDEFERRED_TABLES) == 14


def _build_db_url(conn_kwargs: dict, database: str) -> str:
    """Reassemble a postgresql+asyncpg:// URL for a given database name.

    init_schema_mod.DATABASE_URL is parsed with the asyncpg dialect prefix
    (extract_sql_from_models() does `DATABASE_URL.replace("postgresql+asyncpg://", ...)`),
    so the throwaway-database URL handed to it must match that shape.
    """
    return (
        f"postgresql+asyncpg://{conn_kwargs['user']}:{conn_kwargs['password']}"
        f"@{conn_kwargs['host']}:{conn_kwargs['port']}/{database}"
    )


@pytest.fixture
async def fresh_schema_conn():
    """Yield (conn, db_url) for a disposable database this test fully owns.

    Fresh-install: an empty, uniquely-named database so init has to create
    everything again, not just skip past tables a previous test run (or a
    concurrent smoke test against the shared test DB) already created --
    and so nothing here can step on pg_trgm/pgcrypto/other state the rest of
    `tests/smoke/` relies on in the same `pytest -m smoke` run.
    """
    if not SCHEMA_DATABASE_URL:
        pytest.skip(
            "No TEST_SCHEMA_DATABASE_URL or DATABASE_URL set; cannot reach a "
            "pgvector-capable Postgres for this schema-completeness smoke test."
        )
    admin_kwargs = _parse_db_url(SCHEMA_DATABASE_URL)
    db_name = f"l30_schema_smoke_{uuid.uuid4().hex[:12]}"

    try:
        admin_conn = await asyncpg.connect(
            **{**admin_kwargs, "database": "postgres"}, timeout=10
        )
    except Exception as e:
        pytest.skip(f"Could not connect to test Postgres for schema smoke test: {e}")
        return

    try:
        await admin_conn.execute(f'CREATE DATABASE "{db_name}"')
    except Exception as e:
        await admin_conn.close()
        pytest.skip(f"Could not create throwaway database {db_name!r}: {e}")
        return

    try:
        db_url = _build_db_url(admin_kwargs, db_name)
        conn = await asyncpg.connect(
            **{**admin_kwargs, "database": db_name}, timeout=10
        )
        try:
            yield conn, db_url
        finally:
            await conn.close()
    finally:
        await admin_conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        await admin_conn.close()


async def _run_init(fresh_schema_conn, monkeypatch):
    """Run the real init pipeline against the fresh, empty throwaway database."""
    conn, db_url = fresh_schema_conn

    # execute_sql_async() opens its own asyncpg connection using the module's
    # DATABASE_URL global, which was frozen at import time -- point it at the
    # disposable test database instead of whatever the process env had.
    monkeypatch.setattr(init_schema_mod, "DATABASE_URL", db_url)

    enum_stmts, table_stmts, index_stmts, alter_stmts = (
        await init_schema_mod.extract_sql_from_models()
    )
    model_names = {name for name, _ in table_stmts}

    success = await init_schema_mod.execute_sql_async(
        enum_stmts, table_stmts, index_stmts, alter_stmts
    )
    created = {
        r["tablename"]
        for r in await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
    }
    return model_names, success, created


async def test_fk_strip_tables_created(fresh_schema_conn, monkeypatch, capsys):
    """§3: the FK-strip comma bug no longer drops these 22 non-deferred tables."""
    _, success, created = await _run_init(fresh_schema_conn, monkeypatch)
    log = capsys.readouterr().out

    assert "syntax error" not in log.lower(), log
    assert success

    missing = FK_STRIP_TABLES - created
    assert not missing, f"FK-strip tables still missing after init: {missing}"


async def test_undeferred_tables_created(fresh_schema_conn, monkeypatch, capsys):
    """§4/§5: the 14 feature/scheduler tables are attempted and created."""
    model_names, success, created = await _run_init(fresh_schema_conn, monkeypatch)
    log = capsys.readouterr().out

    # Must actually be attempted by this run (i.e. deferred_tables.txt no
    # longer skips them) before we can assert they land.
    assert UNDEFERRED_TABLES <= model_names, (
        "Expected un-deferred tables missing from generated DDL -- "
        f"deferred_tables.txt still defers: {UNDEFERRED_TABLES - model_names}"
    )
    assert "does not exist" not in log.lower(), log
    assert success

    missing = UNDEFERRED_TABLES - created
    assert not missing, f"Un-deferred tables still missing after init: {missing}"
