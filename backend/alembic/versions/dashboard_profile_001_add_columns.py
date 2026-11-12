# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add dashboard_functions and dashboard_tone to users

Revision ID: dashboard_profile_001
Revises: schema_sync_006
Create Date: 2026-05-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "dashboard_profile_001"
down_revision: Union[str, None] = "schema_sync_006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("dashboard_functions", sa.JSON(), nullable=True, server_default=None))
    op.add_column("users", sa.Column("dashboard_tone", sa.String(20), nullable=False, server_default="standard"))


def downgrade() -> None:
    op.drop_column("users", "dashboard_tone")
    op.drop_column("users", "dashboard_functions")
