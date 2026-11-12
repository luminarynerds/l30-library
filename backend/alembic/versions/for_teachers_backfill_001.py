"""backfill for_teachers_enabled from learning_platform_enabled

Existing deployments where the operator had disabled the broader Learning
Platform should NOT silently gain a teacher portal just because we split
the flags. Mirror the prior gate's state for rows that still hold the
server_default of true.

Revision ID: for_teachers_backfill_001
Revises: for_teachers_001
Create Date: 2026-05-14
"""
from alembic import op

revision = "for_teachers_backfill_001"
down_revision = "circulation_policy_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE organization_features "
        "SET for_teachers_enabled = learning_platform_enabled "
        "WHERE for_teachers_enabled = true "
        "  AND learning_platform_enabled = false"
    )


def downgrade() -> None:
    pass
