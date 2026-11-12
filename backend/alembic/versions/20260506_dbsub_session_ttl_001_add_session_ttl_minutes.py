# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add session_ttl_minutes to database_subscriptions

Revision ID: dbsub_session_ttl_001
Revises: board_retention_001
Create Date: 2026-05-06
"""
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "dbsub_session_ttl_001"
down_revision: Union[str, None] = "board_retention_001"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "database_subscriptions",
        sa.Column("session_ttl_minutes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("database_subscriptions", "session_ttl_minutes")
