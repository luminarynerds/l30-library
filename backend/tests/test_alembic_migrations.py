# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Idempotency tests for alembic migrations that add new tables.

L30's ``init_db.py`` auto-creates new tables from SQLAlchemy models at backend
startup, so any new alembic migration must use ``CREATE TABLE IF NOT EXISTS``
(via ``op.execute``) rather than ``op.create_table``. These tests assert that
running the migration's new-table SQL twice does not error.
"""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text


VERSIONS_DIR = (
    Path(__file__).resolve().parent.parent / "alembic" / "versions"
)
EVENTS_PHASE2_MIGRATION = (
    VERSIONS_DIR
    / "20260515_events_phase2_recurrence_presenter_partner_photo_release_age_range.py"
)


def _sync_postgres_url() -> str | None:
    """Return a sync psycopg2 URL derived from DATABASE_URL, or None if unavailable."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return None
    # Strip asyncpg, swap DB name to a per-test database
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")
    # Use a dedicated DB for this test so we don't collide with the main test DB
    base, _, _name = url.rpartition("/")
    return f"{base}/l30_test_alembic_idempotent"


def _extract_op_execute_statements(path: Path) -> list[str]:
    """Return the string argument of every ``op.execute("...")`` in ``upgrade()``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    statements: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "upgrade":
            continue
        for sub in ast.walk(node):
            if (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and sub.func.attr == "execute"
                and isinstance(sub.func.value, ast.Name)
                and sub.func.value.id == "op"
                and sub.args
                and isinstance(sub.args[0], ast.Constant)
                and isinstance(sub.args[0].value, str)
            ):
                statements.append(sub.args[0].value)
    return statements


class TestEventsPhase2MigrationIdempotent:
    """The events_phase2 migration must use IF NOT EXISTS for its new table.

    Background: ``init_db.py`` (scripts/init_schema_async_raw_sql.py) creates
    ``event_partner_organizations`` at backend startup from the SQLAlchemy
    model. The migration must therefore not fail if the table already exists.
    """

    def test_migration_file_uses_create_table_if_not_exists(self):
        """Static check: the migration uses raw-SQL IF NOT EXISTS."""
        source = EVENTS_PHASE2_MIGRATION.read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS event_partner_organizations" in source
        assert "CREATE INDEX IF NOT EXISTS ix_event_partner_organizations_is_active" in source

    def test_migration_file_does_not_call_op_create_table_for_new_table(self):
        """The migration must not call op.create_table('event_partner_organizations', ...)."""
        tree = ast.parse(EVENTS_PHASE2_MIGRATION.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "create_table"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "op"
            ):
                first_arg = node.args[0] if node.args else None
                table_name = (
                    first_arg.value
                    if isinstance(first_arg, ast.Constant)
                    else None
                )
                pytest.fail(
                    f"events_phase2 migration calls op.create_table"
                    f"({table_name!r}) at line {node.lineno}; "
                    f"use op.execute('CREATE TABLE IF NOT EXISTS ...') instead."
                )

    def test_new_table_sql_is_idempotent_on_postgres(self):
        """Running the new-table CREATE statements twice must succeed.

        This isolates the IF NOT EXISTS behavior from the rest of the
        migration chain (which depends on prior migrations having created
        ``events`` etc). Skipped if no PostgreSQL DATABASE_URL is configured.
        """
        sync_url = _sync_postgres_url()
        if not sync_url:
            pytest.skip("No PostgreSQL DATABASE_URL configured")

        # Connect to the default 'postgres' admin DB to create/drop our test DB.
        admin_url = sync_url.rsplit("/", 1)[0] + "/postgres"
        try:
            admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
            with admin_engine.connect() as conn:
                # Drop if exists (clean slate), then create.
                conn.execute(text("DROP DATABASE IF EXISTS l30_test_alembic_idempotent"))
                conn.execute(text("CREATE DATABASE l30_test_alembic_idempotent"))
            admin_engine.dispose()
        except Exception as e:  # pragma: no cover — environment-dependent
            pytest.skip(f"PostgreSQL unavailable for idempotency test: {e}")

        try:
            engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")
            statements = _extract_op_execute_statements(EVENTS_PHASE2_MIGRATION)
            new_table_stmts = [
                s
                for s in statements
                if re.search(
                    r"event_partner_organizations", s, flags=re.IGNORECASE
                )
            ]
            assert new_table_stmts, (
                "No event_partner_organizations CREATE statements found in migration"
            )

            # First run: creates the table + indexes
            with engine.connect() as conn:
                for stmt in new_table_stmts:
                    conn.execute(text(stmt))

            insp = inspect(engine)
            assert "event_partner_organizations" in insp.get_table_names()

            # Second run: must NOT error (idempotency)
            with engine.connect() as conn:
                for stmt in new_table_stmts:
                    conn.execute(text(stmt))

            engine.dispose()
        finally:
            try:
                admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
                with admin_engine.connect() as conn:
                    conn.execute(
                        text("DROP DATABASE IF EXISTS l30_test_alembic_idempotent")
                    )
                admin_engine.dispose()
            except Exception:  # pragma: no cover
                pass
