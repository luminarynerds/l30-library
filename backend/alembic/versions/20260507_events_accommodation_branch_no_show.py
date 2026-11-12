# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""events accommodation, branch, no_show

Revision ID: events_accom_branch_001
Revises: board_audit_immutable_001
Create Date: 2026-05-07

Single concern: events surface accommodation + identity columns.

Schema-only, additive, prod-safe:
  * events.branch_id INTEGER NULL FK -> branches.id ON DELETE SET NULL
    so a closed branch doesn't cascade-delete historical events. Indexed
    for "events at branch X" lookups.
  * events.{wheelchair_accessible, asl_provided, captioning_provided,
    assistive_listening, sensory_friendly, large_print_available} BOOLEAN
    NOT NULL DEFAULT false — accessibility flags surfaced on the public
    event detail page.
  * events.accessibility_notes TEXT NULL — free-text per-event statement.
  * event_registrations.accommodation_requested BOOLEAN NOT NULL DEFAULT false
  * event_registrations.accommodation_details TEXT NULL — patron-supplied
    accommodation description.
  * event_registrations.accommodation_acknowledged_at TIMESTAMPTZ NULL
  * event_registrations.accommodation_acknowledged_by INTEGER NULL FK ->
    users.id ON DELETE SET NULL — staff workflow attribution.

Note on no_show: EventRegistration.status is a free-form String(20),
not a SQLEnum, so the new NO_SHOW = "no_show" enum value needs no DDL —
it just becomes a valid value the application writes.

All columns are NULLable or have server defaults so existing rows
backfill transparently and the running backend can keep writing
existing-shape rows during a rolling deploy.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "events_accom_branch_001"
down_revision: Union[str, None] = "board_audit_immutable_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- events: branch_id ---
    op.add_column(
        "events",
        sa.Column(
            "branch_id",
            sa.Integer(),
            sa.ForeignKey("branches.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_events_branch_id",
        "events",
        ["branch_id"],
        unique=False,
    )

    # --- events: accessibility flags ---
    for col in (
        "wheelchair_accessible",
        "asl_provided",
        "captioning_provided",
        "assistive_listening",
        "sensory_friendly",
        "large_print_available",
    ):
        op.add_column(
            "events",
            sa.Column(
                col,
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    op.add_column(
        "events",
        sa.Column("accessibility_notes", sa.Text(), nullable=True),
    )

    # --- event_registrations: accommodation fields ---
    op.add_column(
        "event_registrations",
        sa.Column(
            "accommodation_requested",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "event_registrations",
        sa.Column("accommodation_details", sa.Text(), nullable=True),
    )
    op.add_column(
        "event_registrations",
        sa.Column(
            "accommodation_acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "event_registrations",
        sa.Column(
            "accommodation_acknowledged_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("event_registrations", "accommodation_acknowledged_by")
    op.drop_column("event_registrations", "accommodation_acknowledged_at")
    op.drop_column("event_registrations", "accommodation_details")
    op.drop_column("event_registrations", "accommodation_requested")

    op.drop_column("events", "accessibility_notes")
    for col in (
        "large_print_available",
        "sensory_friendly",
        "assistive_listening",
        "captioning_provided",
        "asl_provided",
        "wheelchair_accessible",
    ):
        op.drop_column("events", col)

    op.drop_index("ix_events_branch_id", table_name="events")
    op.drop_column("events", "branch_id")
