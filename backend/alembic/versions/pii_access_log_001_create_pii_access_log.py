# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create pii_access_log table (and merge home_page_001 + acquisition_rationales_001 heads)

Revision ID: pii_access_log_001
Revises: home_page_001, acquisition_rationales_001
Create Date: 2026-05-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision = "pii_access_log_001"
down_revision: Union[str, Sequence[str], None] = (
    "home_page_001",
    "acquisition_rationales_001",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not op.get_context().as_sql:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        if "pii_access_log" in inspector.get_table_names():
            return

    op.create_table(
        "pii_access_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("user_role", sa.String(length=50), nullable=False),
        sa.Column("endpoint", sa.String(length=500), nullable=False),
        sa.Column("fields_accessed", sa.JSON(), nullable=False),
        sa.Column("fields_redacted", sa.JSON(), nullable=False),
        sa.Column("patron_ids_accessed", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("additional_context", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_pii_access_log_timestamp", "pii_access_log", ["timestamp"]
    )
    op.create_index(
        "ix_pii_access_log_user_id", "pii_access_log", ["user_id"]
    )
    op.create_index(
        "ix_pii_access_log_user_role", "pii_access_log", ["user_role"]
    )
    op.create_index("ix_pii_access_log_id", "pii_access_log", ["id"])


def downgrade() -> None:
    op.drop_index("ix_pii_access_log_id", table_name="pii_access_log")
    op.drop_index("ix_pii_access_log_user_role", table_name="pii_access_log")
    op.drop_index("ix_pii_access_log_user_id", table_name="pii_access_log")
    op.drop_index("ix_pii_access_log_timestamp", table_name="pii_access_log")
    op.drop_table("pii_access_log")
