# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create staff_presence table

Revision ID: staff_presence_001
Revises: rpt_sched_001
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa

revision = "staff_presence_001"
down_revision = "rpt_sched_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "staff_presence",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column(
            "status",
            sa.Enum("available", "on_break", "needs_help", "off_duty", name="presencestatus"),
            nullable=False,
            server_default="off_duty",
        ),
        sa.Column("status_changed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("shift_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shift_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("break_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_staff_presence_staff_status", "staff_presence", ["staff_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_staff_presence_staff_status", table_name="staff_presence")
    op.drop_table("staff_presence")
    op.execute("DROP TYPE IF EXISTS presencestatus")
