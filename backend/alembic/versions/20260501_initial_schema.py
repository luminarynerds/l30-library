# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Initial schema baseline from production

Revision ID: 0001_initial
Revises: None
Create Date: 2026-05-01

This migration creates the full L30 schema from a production dump.
On existing databases that already have the schema, stamp this revision
without running it: alembic stamp 0001_initial
"""
from pathlib import Path

from alembic import op


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    sql_file = Path(__file__).parent / "initial_schema.sql"
    sql = sql_file.read_text()
    # Strip psql meta-commands (e.g. \\restrict, \\unrestrict) emitted by
    # pg_dump v16+. These are interpreted by the psql client, not by the
    # PostgreSQL server, so feeding them through SQLAlchemy/asyncpg
    # raises a syntax error.
    sql = "\n".join(
        line for line in sql.splitlines()
        if not line.lstrip().startswith(("\\restrict", "\\unrestrict"))
    )
    # Execute the full schema SQL
    op.execute(sql)


def downgrade():
    # Cannot downgrade from initial schema
    raise RuntimeError("Cannot downgrade from initial schema. Restore from backup.")
