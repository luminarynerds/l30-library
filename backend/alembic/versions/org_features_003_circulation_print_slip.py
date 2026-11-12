# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add circulation_print_slip_enabled column to organization_features.

Revision ID: org_features_003
Revises: c3a17e9d44b1
Create Date: 2026-05-18

Adds the feature flag column for the printable + emailable post-checkout
slip. Default ON because this is a fundamental library workflow.
Idempotent via has_column guard so prods that were manually
ALTER'd do not collide.
"""
from alembic import op
import sqlalchemy as sa

revision = "org_features_003"
down_revision = "a8d4c9f72e10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().as_sql:
        existing_cols: set[str] = set()
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        existing_cols = {c["name"] for c in inspector.get_columns("organization_features")}
    if "circulation_print_slip_enabled" not in existing_cols:
        op.add_column(
            "organization_features",
            sa.Column(
                "circulation_print_slip_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )


def downgrade() -> None:
    op.drop_column("organization_features", "circulation_print_slip_enabled")
