# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add cohort_enabled column to organization_features.

Revision ID: org_features_006
Revises: lp_cohort_001
Create Date: 2026-05-20

Feature flag for learning-path cohorts V1 (opt-in pair-up + shared
discussion wall). Default OFF: ships dark, opt-in per library while
the feature bakes in. Existing prod rows are backfilled FALSE via
server_default, matching the prompt directive not to enable for any
existing org.

Idempotent via has_column guard so prods that were ALTER-fixed by hand
or stamped forward don't fail the upgrade.
"""
from alembic import op
import sqlalchemy as sa

revision = "org_features_006"
down_revision = "lp_cohort_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().as_sql:
        existing_cols: set[str] = set()
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        existing_cols = {c["name"] for c in inspector.get_columns("organization_features")}
    if "cohort_enabled" not in existing_cols:
        op.add_column(
            "organization_features",
            sa.Column(
                "cohort_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    op.drop_column("organization_features", "cohort_enabled")
