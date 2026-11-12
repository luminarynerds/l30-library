# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add PLS circulation fields to annual_reports (total/electronic/physical circulation)."""
import sqlalchemy as sa
from alembic import op

revision = "pls_circulation_fields_001"
down_revision = "editorial_prepub_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "annual_reports",
        sa.Column("total_circulation", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "annual_reports",
        sa.Column("electronic_circulation", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "annual_reports",
        sa.Column("physical_circulation", sa.Integer(), nullable=True, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("annual_reports", "physical_circulation")
    op.drop_column("annual_reports", "electronic_circulation")
    op.drop_column("annual_reports", "total_circulation")
