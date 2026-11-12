# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""restore community_metrics_snapshots dropped by schema_sync_003

The schema_sync_003 pre-beta cleanup dropped community_metrics_snapshots
on the assumption its model was dead. The model (and supporting service,
API router, and monthly scheduler job) is in fact live. This migration
recreates the table with the same schema, indexes, and unique constraint
as the model.

Revision ID: cms_restore_001
Revises: rp_notification_types_001
Create Date: 2026-05-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "cms_restore_001"
down_revision: Union[str, Sequence[str], None] = "rp_notification_types_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "community_metrics_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("period_type", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["branch_id"], ["branches.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "period_start",
            "period_end",
            "period_type",
            "category",
            "branch_id",
            name="uq_cms_period_category_branch",
        ),
    )
    op.create_index(
        "ix_community_metrics_snapshots_id",
        "community_metrics_snapshots",
        ["id"],
    )
    op.create_index(
        "ix_cms_period",
        "community_metrics_snapshots",
        ["period_type", "period_start", "period_end"],
    )
    op.create_index(
        "ix_cms_category", "community_metrics_snapshots", ["category"]
    )
    op.create_index(
        "ix_cms_branch", "community_metrics_snapshots", ["branch_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_cms_branch", table_name="community_metrics_snapshots")
    op.drop_index("ix_cms_category", table_name="community_metrics_snapshots")
    op.drop_index("ix_cms_period", table_name="community_metrics_snapshots")
    op.drop_index(
        "ix_community_metrics_snapshots_id",
        table_name="community_metrics_snapshots",
    )
    op.drop_table("community_metrics_snapshots")
