# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create parent_onboarding_export_log table

One row per weekly-summary export. Used to answer "who downloaded
patron data and when" if a privacy concern is raised.

Revision ID: parent_onboarding_export_log_001
Revises: patron_category_001
Create Date: 2026-05-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision = "parent_onboarding_export_log_001"
down_revision: Union[str, Sequence[str], None] = "patron_category_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parent_onboarding_export_log",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "exported_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "exported_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("format", sa.String(8), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("coordinator_id", sa.Integer(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "format IN ('csv', 'pdf')",
            name="ck_parent_onboarding_export_log_format",
        ),
    )
    op.create_index(
        "ix_parent_onboarding_export_log_exported_at",
        "parent_onboarding_export_log",
        ["exported_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_parent_onboarding_export_log_exported_at",
        table_name="parent_onboarding_export_log",
    )
    op.drop_table("parent_onboarding_export_log")
