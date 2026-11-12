# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""PLS Phase 3: capital revenue (JSONB) + capital outlay on annual_reports."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "pls_capital_fields_001"
down_revision = "pls_phase2_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "annual_reports",
        sa.Column("capital_revenue", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "annual_reports",
        sa.Column("capital_outlay", sa.Numeric(15, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("annual_reports", "capital_outlay")
    op.drop_column("annual_reports", "capital_revenue")
