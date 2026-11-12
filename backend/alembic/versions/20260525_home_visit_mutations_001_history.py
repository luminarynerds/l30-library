# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""home visit status mutations: history table + new lifecycle columns

Revision ID: home_visit_mutations_001
Revises: rp_entry_date_001
Create Date: 2026-05-25

Adds the missing lifecycle columns to ``parent_home_visits`` (so completion
outcomes, cancellation reasons, and reschedule back-links are first-class
fields instead of being silently dropped at the API boundary), and a new
``home_visit_status_history`` table that records every status transition
with the actor, timestamp, optional reason, and a JSON snapshot of any
side-data (outcomes / resources / new visit id).

The existing ``visit_notes`` / ``items_brought`` / ``next_visit_date``
columns are intentionally retained for back-compat; new code writes to the
new columns, and existing rows continue to load unchanged.

Down-revision chains off ``rp_entry_date_001`` (the home-visits family
head as of 2026-05-25). Seven other alembic heads exist in parallel;
they will be merged separately. This revision is purely additive so it
does not collide with any other in-flight head.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "home_visit_mutations_001"
down_revision = "rp_entry_date_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New lifecycle columns on parent_home_visits.
    op.add_column(
        "parent_home_visits",
        sa.Column("outcomes", sa.Text(), nullable=True),
    )
    op.add_column(
        "parent_home_visits",
        sa.Column(
            "resources_delivered",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "parent_home_visits",
        sa.Column("follow_up_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "parent_home_visits",
        sa.Column("cancelled_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "parent_home_visits",
        sa.Column("rescheduled_to_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_parent_home_visits_rescheduled_to_id",
        "parent_home_visits",
        "parent_home_visits",
        ["rescheduled_to_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Status history audit table.
    op.create_table(
        "home_visit_status_history",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "visit_id",
            sa.Integer(),
            sa.ForeignKey("parent_home_visits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column(
            "changed_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_home_visit_status_history_visit_changed",
        "home_visit_status_history",
        ["visit_id", "changed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_home_visit_status_history_visit_changed",
        table_name="home_visit_status_history",
    )
    op.drop_table("home_visit_status_history")

    op.drop_constraint(
        "fk_parent_home_visits_rescheduled_to_id",
        "parent_home_visits",
        type_="foreignkey",
    )
    op.drop_column("parent_home_visits", "rescheduled_to_id")
    op.drop_column("parent_home_visits", "cancelled_reason")
    op.drop_column("parent_home_visits", "follow_up_date")
    op.drop_column("parent_home_visits", "resources_delivered")
    op.drop_column("parent_home_visits", "outcomes")
