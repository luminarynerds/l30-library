# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add aggregate-trending flag + patron opt-out.

Revision ID: discover_trending_001
Revises: df85cac32c74
Create Date: 2026-05-20

Adds:
- organization_features.aggregate_trending_enabled (default TRUE) -- system
  kill-switch for the /discover trending rails.
- users.aggregate_recommendations_opt_out (default FALSE) -- per-patron
  opt-out from contributing checkout activity to aggregate trending counts.

Both are column adds, so init_db.py won't pre-create anything. Idempotent
via has_column guard so re-runs are safe.
"""
from alembic import op
import sqlalchemy as sa

revision = "discover_trending_001"
down_revision = "df85cac32c74"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().as_sql:
        org_cols: set[str] = set()
        user_cols: set[str] = set()
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        org_cols = {c["name"] for c in inspector.get_columns("organization_features")}
        user_cols = {c["name"] for c in inspector.get_columns("users")}

    if "aggregate_trending_enabled" not in org_cols:
        op.add_column(
            "organization_features",
            sa.Column(
                "aggregate_trending_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )

    if "aggregate_recommendations_opt_out" not in user_cols:
        op.add_column(
            "users",
            sa.Column(
                "aggregate_recommendations_opt_out",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    op.drop_column("users", "aggregate_recommendations_opt_out")
    op.drop_column("organization_features", "aggregate_trending_enabled")
