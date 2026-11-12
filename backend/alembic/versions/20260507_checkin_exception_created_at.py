# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add created_at to check_in_exceptions and merge heads

Revision ID: checkin_exception_001
Revises: catalog_lccn_oclc_001, board_amendments_001
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "checkin_exception_001"
down_revision: Union[str, Sequence[str], None] = ("catalog_lccn_oclc_001", "board_amendments_001")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "check_in_exceptions",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("check_in_exceptions", "created_at")
