# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create patron_categories + User.patron_category_id FK + seed canonical 6 codes.

Revision ID: patron_category_001
Revises: enum_overflow_001
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa


revision = "patron_category_001"
down_revision = "enum_overflow_001"
branch_labels = None
depends_on = None


CANONICAL_CATEGORIES = [
    ("ADULT", "Adult"),
    ("JUVENILE", "Juvenile"),
    ("SENIOR", "Senior"),
    ("STUDENT", "Student"),
    ("TEACHER", "Teacher"),
    ("NONRES", "Non-Resident"),
]


def upgrade() -> None:
    """Create patron_categories table, add User FK, seed canonical rows."""
    # Table -- idempotent across re-runs of this migration. IF NOT EXISTS guards
    # protect against alembic stamp/upgrade quirks where the upgrade transaction
    # is partially applied and retried.
    op.execute("""
        CREATE TABLE IF NOT EXISTS patron_categories (
            id SERIAL PRIMARY KEY,
            code VARCHAR(20) NOT NULL,
            label VARCHAR(100) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_patron_categories_code UNIQUE (code)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_patron_categories_code "
        "ON patron_categories(code)"
    )

    # FK column on users -- idempotent via IF NOT EXISTS
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "patron_category_id INTEGER REFERENCES patron_categories(id) ON DELETE SET NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_users_patron_category_id "
        "ON users(patron_category_id)"
    )

    # Seed canonical categories (idempotent via ON CONFLICT DO NOTHING)
    conn = op.get_bind()
    for code, label in CANONICAL_CATEGORIES:
        conn.execute(
            sa.text(
                "INSERT INTO patron_categories (code, label, is_active) "
                "VALUES (:code, :label, TRUE) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {"code": code, "label": label},
        )


def downgrade() -> None:
    """Drop FK, drop column, drop table."""
    if op.get_context().as_sql:
        user_cols = {"patron_category_id"}
        existing_tables = {"patron_categories"}
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        user_cols = {c["name"] for c in inspector.get_columns("users")}
        existing_tables = set(inspector.get_table_names())

    if "patron_category_id" in user_cols:
        op.execute(
            "DROP INDEX IF EXISTS ix_users_patron_category_id"
        )
        op.execute("ALTER TABLE users DROP COLUMN IF EXISTS patron_category_id")

    if "patron_categories" in existing_tables:
        op.execute(
            "DROP INDEX IF EXISTS ix_patron_categories_code"
        )
        op.drop_table("patron_categories")
