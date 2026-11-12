# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""event-attendance credit for reading programs

Revision ID: rp_event_credit_001
Revises: rp_log_format_001
Create Date: 2026-05-12

Adds the ``event_reading_program_credits`` mapping table and two new
idempotency columns on ``reading_log_entries`` (``source``,
``source_event_id``) plus a unique constraint that prevents the
event-credit grant path from double-crediting on repeat check-ins.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "rp_event_credit_001"
down_revision: Union[str, Sequence[str], None] = "rp_log_format_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_reading_program_credits",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "program_id",
            sa.Integer(),
            sa.ForeignKey("reading_programs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "minutes_credit", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "books_credit", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "pages_credit", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "event_id", "program_id", name="uq_event_program_credit_pair"
        ),
    )

    op.add_column(
        "reading_log_entries",
        sa.Column("source", sa.String(length=50), nullable=True),
    )
    op.create_index(
        "ix_reading_log_entries_source",
        "reading_log_entries",
        ["source"],
    )
    op.add_column(
        "reading_log_entries",
        sa.Column(
            "source_event_id",
            sa.Integer(),
            sa.ForeignKey("events.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_reading_log_entries_source_event_id",
        "reading_log_entries",
        ["source_event_id"],
    )
    # NULL source_event_id values are treated as distinct in PG uniques, so
    # this only constrains rows that actually originated from an event grant.
    op.create_unique_constraint(
        "uq_reading_log_entry_registration_source_event",
        "reading_log_entries",
        ["registration_id", "source_event_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_reading_log_entry_registration_source_event",
        "reading_log_entries",
        type_="unique",
    )
    op.drop_index(
        "ix_reading_log_entries_source_event_id",
        table_name="reading_log_entries",
    )
    op.drop_column("reading_log_entries", "source_event_id")
    op.drop_index(
        "ix_reading_log_entries_source", table_name="reading_log_entries"
    )
    op.drop_column("reading_log_entries", "source")
    op.drop_table("event_reading_program_credits")
