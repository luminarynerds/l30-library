# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create board_minutes_amendments table.

Revision ID: board_amendments_001
Revises: ae69a285a9af
Create Date: 2026-05-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "board_amendments_001"
down_revision: Union[str, None] = "board_coi_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "board_minutes_amendments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("minutes_id", sa.Integer(), sa.ForeignKey("board_minutes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("amendment_text", sa.Text(), nullable=False),
        sa.Column("section_title", sa.String(200), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("amendment_reason", sa.Text(), nullable=False),
        sa.Column("amendment_vote_result", sa.String(200), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("board_minutes_amendments")
