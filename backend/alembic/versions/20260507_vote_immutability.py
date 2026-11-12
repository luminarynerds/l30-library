"""add locked_at to board_votes for vote immutability

Revision ID: vote_immutability_001
Revises: board_audit_immutable_001
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "vote_immutability_001"
down_revision: Union[str, None] = "board_audit_immutable_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "board_votes",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_board_votes_locked_at", "board_votes", ["locked_at"])


def downgrade() -> None:
    op.drop_index("ix_board_votes_locked_at", table_name="board_votes")
    op.drop_column("board_votes", "locked_at")
