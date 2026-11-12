# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add customer_display_enabled column to organization_features.

Revision ID: org_features_005
Revises: org_features_004
Create Date: 2026-05-18

Feature flag for the patron-facing customer display (second monitor) at
the staff circulation desk. Default OFF: most desks lack a second
monitor — opt-in per library.
Idempotent via has_column guard to tolerate prods that were ALTER-fixed
by hand or stamped forward.
"""
from alembic import op
import sqlalchemy as sa

revision = "org_features_005"
down_revision = "org_features_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().as_sql:
        existing_cols: set[str] = set()
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        existing_cols = {c["name"] for c in inspector.get_columns("organization_features")}
    if "customer_display_enabled" not in existing_cols:
        op.add_column(
            "organization_features",
            sa.Column(
                "customer_display_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    op.drop_column("organization_features", "customer_display_enabled")
