# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""board_recusal: recusal declarations, is_chair, tally_recusal

Revision ID: board_recusal_001
Revises: board_audit_immutable_001
Create Date: 2026-05-07

Legal-defensibility fix: board members with conflicts of interest must be
prevented from voting. This adds the table for tracking recusal declarations
and the is_chair column for future tie-breaking logic.

Schema-only, additive, prod-safe:
  * Creates board_recusal_declarations table
  * Adds is_chair column to board_members (default false)
  * Adds final_tally_recusal column to board_votes (default 0)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "board_recusal_001"
down_revision: Union[str, None] = "board_audit_immutable_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotency check
    if not op.get_context().as_sql:
        bind = op.get_bind()
        result = bind.execute(
            sa.text("SELECT 1 FROM information_schema.tables WHERE table_name='board_recusal_declarations'")
        )
        if result.fetchone():
            return

    op.create_table(
        "board_recusal_declarations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("board_member_id", sa.Integer(), sa.ForeignKey("board_members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vote_id", sa.Integer(), sa.ForeignKey("board_votes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("motion_id", sa.Integer(), sa.ForeignKey("board_motions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("topic_description", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("declared_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("withdrawn_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_board_recusal_declarations_board_member_id", "board_recusal_declarations", ["board_member_id"])
    op.create_index("ix_board_recusal_declarations_vote_id", "board_recusal_declarations", ["vote_id"])
    op.create_index("ix_board_recusal_declarations_motion_id", "board_recusal_declarations", ["motion_id"])
    op.create_index("ix_board_recusal_declarations_is_active", "board_recusal_declarations", ["is_active"])

    # Add is_chair to board_members
    op.add_column("board_members", sa.Column("is_chair", sa.Boolean(), server_default=sa.text("false"), nullable=False))

    # Add final_tally_recusal to board_votes
    op.add_column("board_votes", sa.Column("final_tally_recusal", sa.Integer(), server_default=sa.text("0"), nullable=False))


def downgrade() -> None:
    op.drop_column("board_votes", "final_tally_recusal")
    op.drop_column("board_members", "is_chair")
    op.drop_index("ix_board_recusal_declarations_is_active", table_name="board_recusal_declarations")
    op.drop_index("ix_board_recusal_declarations_motion_id", table_name="board_recusal_declarations")
    op.drop_index("ix_board_recusal_declarations_vote_id", table_name="board_recusal_declarations")
    op.drop_index("ix_board_recusal_declarations_board_member_id", table_name="board_recusal_declarations")
    op.drop_table("board_recusal_declarations")
