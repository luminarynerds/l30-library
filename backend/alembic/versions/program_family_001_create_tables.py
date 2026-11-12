# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create program_family_groups and program_family_members tables

Revision ID: program_family_001
Revises: staff_time_entry_001
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa

revision = "program_family_001"
down_revision = "indie_prefs_progress_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "program_family_groups",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("parent_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("parent_user_id", name="uq_family_group_parent"),
    )

    op.create_table(
        "program_family_members",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("family_group_id", sa.Integer(), sa.ForeignKey("program_family_groups.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("age_range", sa.String(10), nullable=False),
        sa.Column("is_parent", sa.Boolean(), default=False, nullable=False),
        sa.Column("participant_id", sa.Integer(), sa.ForeignKey("reading_registrations.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_family_members_group", "program_family_members", ["family_group_id"])


def downgrade() -> None:
    op.drop_index("ix_family_members_group", table_name="program_family_members")
    op.drop_table("program_family_members")
    op.drop_table("program_family_groups")
