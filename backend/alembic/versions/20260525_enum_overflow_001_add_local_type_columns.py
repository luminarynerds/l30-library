# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add local_type / local_fine_type overflow columns.

Revision ID: enum_overflow_001
Revises: pickup_auth_001
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "enum_overflow_001"
down_revision = "pickup_auth_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add nullable local_type to catalog_items + local_fine_type to fines.

    Both columns preserve source-ILS taxonomy labels when the import path
    collapses to enum 'other'. Nullable; no backfill needed (existing rows
    fit the canonical enums by construction).
    """
    if op.get_context().as_sql:
        catalog_cols: set[str] = set()
        fines_cols: set[str] = set()
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        catalog_cols = {c["name"] for c in inspector.get_columns("catalog_items")}
        fines_cols = {c["name"] for c in inspector.get_columns("fines")}

    if "local_type" not in catalog_cols:
        op.add_column(
            "catalog_items",
            sa.Column("local_type", sa.String(length=50), nullable=True),
        )

    if "local_fine_type" not in fines_cols:
        op.add_column(
            "fines",
            sa.Column("local_fine_type", sa.String(length=50), nullable=True),
        )


def downgrade() -> None:
    """Remove the two overflow columns.

    Operator-level: downgrading is destructive of import-preserved labels,
    so prefer rolling forward in production.
    """
    if op.get_context().as_sql:
        catalog_cols = {"local_type"}
        fines_cols = {"local_fine_type"}
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        catalog_cols = {c["name"] for c in inspector.get_columns("catalog_items")}
        fines_cols = {c["name"] for c in inspector.get_columns("fines")}

    if "local_fine_type" in fines_cols:
        op.drop_column("fines", "local_fine_type")

    if "local_type" in catalog_cols:
        op.drop_column("catalog_items", "local_type")
