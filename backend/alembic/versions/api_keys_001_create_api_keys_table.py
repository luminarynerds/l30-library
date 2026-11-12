# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create api_keys table for vendor integrations

Revision ID: api_keys_001
Revises: nudges_002
Create Date: 2026-05-06 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "api_keys_001"
down_revision: Union[str, None] = "board_seal_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key_hash", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("vendor_name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allowed_ips", sa.Text(), nullable=True),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=True, server_default="100"),
    )


def downgrade() -> None:
    op.drop_table("api_keys")
