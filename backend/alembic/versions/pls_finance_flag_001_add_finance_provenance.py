# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add finance provenance columns to annual_reports

Promotes the director-entered finance signal from the brittle
data_sources["financial"]="manual" JSONB key to first-class, audited,
queryable columns that back the PLS completeness gate.

Revision ID: pls_finance_flag_001
Revises: 8ac7702b829a
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "pls_finance_flag_001"
down_revision = "8ac7702b829a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "annual_reports",
        sa.Column("finance_source", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "annual_reports",
        sa.Column("finance_entered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "annual_reports",
        sa.Column(
            "finance_entered_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("annual_reports", "finance_entered_by_id")
    op.drop_column("annual_reports", "finance_entered_at")
    op.drop_column("annual_reports", "finance_source")
