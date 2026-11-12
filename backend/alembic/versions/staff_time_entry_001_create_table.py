# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create staff_time_entries table

Revision ID: staff_time_entry_001
Revises: staff_presence_001
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa

revision = "staff_time_entry_001"
down_revision = "staff_presence_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE timeentrytype AS ENUM (clock_in, clock_out, break_start, break_end)")
    op.create_table(
        "staff_time_entries",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column(
            "entry_type",
            sa.Enum("clock_in", "clock_out", "break_start", "break_end", name="timeentrytype", create_type=False),
            nullable=False,
            index=True,
        ),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("shift_date", sa.Date(), nullable=False, index=True),
        sa.Column("staff_shift_id", sa.Integer(), sa.ForeignKey("staff_shifts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("duration_minutes", sa.Float(), nullable=True),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_time_entries_staff_date", "staff_time_entries", ["staff_id", "shift_date"])


def downgrade() -> None:
    op.drop_index("ix_time_entries_staff_date", table_name="staff_time_entries")
    op.drop_table("staff_time_entries")
    op.execute("DROP TYPE IF EXISTS timeentrytype")
