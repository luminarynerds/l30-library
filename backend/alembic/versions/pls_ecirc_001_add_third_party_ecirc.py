# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add third-party electronic circulation columns to annual_reports

PLS electronic circulation must fold in vendor e-platform usage (OverDrive/Libby,
Hoopla, e-audio). L30 only computes native ebook checkouts, so add columns to
capture the staff-entered third-party total and its per-platform breakdown.

Revision ID: pls_ecirc_001
Revises: pls_finance_flag_001
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "pls_ecirc_001"
down_revision = "pls_finance_flag_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "annual_reports",
        sa.Column("third_party_electronic_circulation", sa.Integer(), nullable=True),
    )
    op.add_column(
        "annual_reports",
        sa.Column("electronic_circulation_by_platform", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("annual_reports", "electronic_circulation_by_platform")
    op.drop_column("annual_reports", "third_party_electronic_circulation")
