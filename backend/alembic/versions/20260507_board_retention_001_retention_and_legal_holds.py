# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""board_retention: retention schedules, legal holds, disposition tracking

Revision ID: board_retention_001
Revises: board_seal_001
Create Date: 2026-05-07

Legal-defensibility fix: board records need configurable retention schedules,
legal hold suspension, and disposition documentation.

Schema-only, additive, prod-safe:
  * Creates board_record_retention_schedules table
  * Creates board_legal_holds table
  * Creates board_record_dispositions table
  * Adds is_permanent column to board_resolutions (default true)
  * Seeds default retention schedules for minutes, resolutions, motions, documents
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "board_retention_001"
down_revision: Union[str, None] = "board_seal_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not op.get_context().as_sql:
        bind = op.get_bind()
        result = bind.execute(
            sa.text("SELECT 1 FROM information_schema.tables WHERE table_name='board_record_retention_schedules'")
        )
        if result.fetchone():
            return

    op.create_table(
        "board_record_retention_schedules",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("record_type", sa.String(50), nullable=False, unique=True),
        sa.Column("retention_years", sa.Integer(), nullable=True),
        sa.Column("is_permanent", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("legal_authority", sa.String(500), nullable=True),
        sa.Column("configured_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("configured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_board_record_retention_schedules_record_type", "board_record_retention_schedules", ["record_type"], unique=True)

    op.create_table(
        "board_legal_holds",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("date_range_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_range_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("placed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False),
        sa.Column("placed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("released_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_reason", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_board_legal_holds_is_active", "board_legal_holds", ["is_active"])

    op.create_table(
        "board_record_dispositions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("retention_schedule_id", sa.Integer(), sa.ForeignKey("board_record_retention_schedules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("performed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("record_metadata", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_board_record_dispositions_entity_type", "board_record_dispositions", ["entity_type"])
    op.create_index("ix_board_record_dispositions_entity_id", "board_record_dispositions", ["entity_id"])

    # Add is_permanent to board_resolutions
    op.add_column("board_resolutions", sa.Column("is_permanent", sa.Boolean(), server_default=sa.text("true"), nullable=False))

    # Seed default retention schedules
    schedules_table = sa.table(
        "board_record_retention_schedules",
        sa.column("record_type", sa.String),
        sa.column("retention_years", sa.Integer),
        sa.column("is_permanent", sa.Boolean),
        sa.column("description", sa.Text),
        sa.column("legal_authority", sa.String),
    )
    op.bulk_insert(
        schedules_table,
        [
            {"record_type": "minutes", "retention_years": None, "is_permanent": True, "description": "Board meeting minutes are permanent public records", "legal_authority": "State library General Records Schedule"},
            {"record_type": "resolution", "retention_years": None, "is_permanent": True, "description": "Board resolutions are permanent public records", "legal_authority": "State library General Records Schedule"},
            {"record_type": "motion", "retention_years": 7, "is_permanent": False, "description": "Board motions retained for 7 years after meeting date", "legal_authority": "State library General Records Schedule"},
            {"record_type": "document", "retention_years": 7, "is_permanent": False, "description": "Board documents retained for 7 years unless marked permanent", "legal_authority": "State library General Records Schedule"},
        ],
    )


def downgrade() -> None:
    op.drop_column("board_resolutions", "is_permanent")
    op.drop_index("ix_board_record_dispositions_entity_id", table_name="board_record_dispositions")
    op.drop_index("ix_board_record_dispositions_entity_type", table_name="board_record_dispositions")
    op.drop_table("board_record_dispositions")
    op.drop_index("ix_board_legal_holds_is_active", table_name="board_legal_holds")
    op.drop_table("board_legal_holds")
    op.drop_index("ix_board_record_retention_schedules_record_type", table_name="board_record_retention_schedules")
    op.drop_table("board_record_retention_schedules")
