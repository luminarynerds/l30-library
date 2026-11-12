# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create board_coi_disclosures table.

Revision ID: board_coi_001
Revises: board_compliance_001
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "board_coi_001"
down_revision = "board_compliance_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not op.get_context().as_sql:
        conn = op.get_bind()
        result = conn.execute(
            sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = 'board_coi_disclosures'")
        )
        if result.scalar():
            return

    op.create_table(
        "board_coi_disclosures",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("board_member_id", sa.Integer(), sa.ForeignKey("board_members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fiscal_year", sa.String(10), nullable=False),
        sa.Column("disclosure_text", sa.Text(), nullable=False),
        sa.Column("categories", JSONB(), server_default="[]"),
        sa.Column("keywords", JSONB(), server_default="[]"),
        sa.Column("attested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("attestation_statement", sa.String(1000), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default="true"),
        sa.Column("superseded_by_id", sa.Integer(), sa.ForeignKey("board_coi_disclosures.id", ondelete="SET NULL"), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_board_coi_disclosures_board_member_id", "board_coi_disclosures", ["board_member_id"])
    op.create_index("ix_board_coi_disclosures_fiscal_year", "board_coi_disclosures", ["fiscal_year"])
    op.create_index("ix_board_coi_disclosures_is_current", "board_coi_disclosures", ["is_current"])


def downgrade() -> None:
    op.drop_index("ix_board_coi_disclosures_is_current", table_name="board_coi_disclosures")
    op.drop_index("ix_board_coi_disclosures_fiscal_year", table_name="board_coi_disclosures")
    op.drop_index("ix_board_coi_disclosures_board_member_id", table_name="board_coi_disclosures")
    op.drop_table("board_coi_disclosures")
