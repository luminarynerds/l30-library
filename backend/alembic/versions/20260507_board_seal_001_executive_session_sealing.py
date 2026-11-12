# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""board_seal: executive session sealing columns and FK change

Revision ID: board_seal_001
Revises: board_recusal_001
Create Date: 2026-05-07

Legal-defensibility fix: executive session minutes must be encrypted at rest
and access-controlled. Approved minutes must not be cascade-deleted when
meetings are deleted.

Schema-only, additive, prod-safe:
  * Adds sealing columns to board_minutes (is_sealed, sealed_at, etc.)
  * Adds is_permanent column (default true)
  * Changes board_minutes.meeting_id FK from CASCADE to RESTRICT
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "board_seal_001"
down_revision: Union[str, None] = "board_recusal_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotency: check if column already exists
    if not op.get_context().as_sql:
        bind = op.get_bind()
        result = bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='board_minutes' AND column_name='is_sealed'"
            )
        )
        if result.fetchone():
            return

    # Sealing columns
    op.add_column("board_minutes", sa.Column("is_sealed", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("board_minutes", sa.Column("sealed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("board_minutes", sa.Column("sealed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("board_minutes", sa.Column("unsealed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("board_minutes", sa.Column("unsealed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("board_minutes", sa.Column("unseal_reason", sa.Text(), nullable=True))
    op.add_column("board_minutes", sa.Column("sealed_sections_encrypted", sa.Text(), nullable=True))

    # Retention column
    op.add_column("board_minutes", sa.Column("is_permanent", sa.Boolean(), server_default=sa.text("true"), nullable=False))

    # Index on is_sealed
    op.create_index("ix_board_minutes_is_sealed", "board_minutes", ["is_sealed"])

    # Change FK from CASCADE to RESTRICT
    op.drop_constraint("board_minutes_meeting_id_fkey", "board_minutes", type_="foreignkey")
    op.create_foreign_key(
        "board_minutes_meeting_id_fkey",
        "board_minutes",
        "board_meetings",
        ["meeting_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # Restore CASCADE FK
    op.drop_constraint("board_minutes_meeting_id_fkey", "board_minutes", type_="foreignkey")
    op.create_foreign_key(
        "board_minutes_meeting_id_fkey",
        "board_minutes",
        "board_meetings",
        ["meeting_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_index("ix_board_minutes_is_sealed", table_name="board_minutes")
    op.drop_column("board_minutes", "is_permanent")
    op.drop_column("board_minutes", "sealed_sections_encrypted")
    op.drop_column("board_minutes", "unseal_reason")
    op.drop_column("board_minutes", "unsealed_by_id")
    op.drop_column("board_minutes", "unsealed_at")
    op.drop_column("board_minutes", "sealed_by_id")
    op.drop_column("board_minutes", "sealed_at")
    op.drop_column("board_minutes", "is_sealed")
