# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""rooms accommodation, accessibility, buffers, policy ack, repeat-cap, rejection enum

Revision ID: rooms_accom_buffers_001
Revises: events_accom_branch_001
Create Date: 2026-05-07

Single concern: rooms surface — accommodation/accessibility metadata,
setup/teardown buffers, structured rejection categories, meeting-room
policy acknowledgement, per-patron rolling 30-day booking cap.

Schema-only, additive, prod-safe:
  * rooms.{wheelchair_accessible, hearing_loop, accessible_restroom_nearby}
    BOOLEAN NOT NULL DEFAULT false — accessibility flags surfaced to
    patrons on the room detail page.
  * rooms.accessibility_notes TEXT NULL — free-text accessibility statement.
  * rooms.{setup_buffer_minutes, teardown_buffer_minutes} INTEGER NOT NULL
    DEFAULT 0 — staff-configurable per-room buffers; conflict detection
    expands the occupied window when either is > 0. Behavior is unchanged
    for rooms that don't opt in (both 0).
  * rooms.max_bookings_per_patron_per_month INTEGER NULL — opt-in rolling
    30-day cap; NULL means unlimited.
  * room_reservations.accommodation_requested BOOLEAN NOT NULL DEFAULT false
  * room_reservations.accommodation_details TEXT NULL — patron-supplied
    accommodation description.
  * room_reservations.accommodation_acknowledged_at TIMESTAMPTZ NULL
  * room_reservations.accommodation_acknowledged_by INTEGER NULL FK ->
    users.id ON DELETE SET NULL — staff workflow attribution.
  * room_reservations.policy_acknowledged BOOLEAN NOT NULL DEFAULT false
  * room_reservations.policy_acknowledged_at TIMESTAMPTZ NULL — when the
    patron acknowledged the meeting-room policy at booking time.
  * rejectionreason ENUM TYPE — controlled, content-neutral denial
    categories. Lowercase values match the Python enum.
  * room_reservations.rejection_reason_code rejectionreason NULL — the
    free-text rejection_reason column remains as supplementary notes.

All columns are NULLable or have server defaults so existing rows
backfill transparently and the running backend can keep writing
existing-shape rows during a rolling deploy.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "rooms_accom_buffers_001"
down_revision: Union[str, None] = "events_accom_branch_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


REJECTION_REASON_VALUES = (
    "schedule_conflict",
    "capacity_exceeded",
    "incomplete_information",
    "prior_policy_violation",
    "fee_unpaid",
    "out_of_hours",
    "other",
)


def upgrade() -> None:
    # --- Create rejectionreason enum type (lowercase values) ---
    rejection_reason_enum = postgresql.ENUM(
        *REJECTION_REASON_VALUES,
        name="rejectionreason",
        create_type=False,
    )
    rejection_reason_enum.create(op.get_bind(), checkfirst=True)

    # --- rooms: accessibility metadata ---
    for col in ("wheelchair_accessible", "hearing_loop", "accessible_restroom_nearby"):
        op.add_column(
            "rooms",
            sa.Column(
                col,
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    op.add_column(
        "rooms",
        sa.Column("accessibility_notes", sa.Text(), nullable=True),
    )

    # --- rooms: setup/teardown buffers ---
    op.add_column(
        "rooms",
        sa.Column(
            "setup_buffer_minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "rooms",
        sa.Column(
            "teardown_buffer_minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # --- rooms: per-patron rolling 30-day cap (NULL = unlimited) ---
    op.add_column(
        "rooms",
        sa.Column(
            "max_bookings_per_patron_per_month",
            sa.Integer(),
            nullable=True,
        ),
    )

    # --- room_reservations: accommodation fields ---
    op.add_column(
        "room_reservations",
        sa.Column(
            "accommodation_requested",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "room_reservations",
        sa.Column("accommodation_details", sa.Text(), nullable=True),
    )
    op.add_column(
        "room_reservations",
        sa.Column(
            "accommodation_acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "room_reservations",
        sa.Column(
            "accommodation_acknowledged_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # --- room_reservations: policy acknowledgement ---
    op.add_column(
        "room_reservations",
        sa.Column(
            "policy_acknowledged",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "room_reservations",
        sa.Column(
            "policy_acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # --- room_reservations: structured rejection category ---
    op.add_column(
        "room_reservations",
        sa.Column(
            "rejection_reason_code",
            postgresql.ENUM(
                *REJECTION_REASON_VALUES,
                name="rejectionreason",
                create_type=False,
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("room_reservations", "rejection_reason_code")
    op.drop_column("room_reservations", "policy_acknowledged_at")
    op.drop_column("room_reservations", "policy_acknowledged")
    op.drop_column("room_reservations", "accommodation_acknowledged_by")
    op.drop_column("room_reservations", "accommodation_acknowledged_at")
    op.drop_column("room_reservations", "accommodation_details")
    op.drop_column("room_reservations", "accommodation_requested")

    op.drop_column("rooms", "max_bookings_per_patron_per_month")
    op.drop_column("rooms", "teardown_buffer_minutes")
    op.drop_column("rooms", "setup_buffer_minutes")
    op.drop_column("rooms", "accessibility_notes")
    for col in ("accessible_restroom_nearby", "hearing_loop", "wheelchair_accessible"):
        op.drop_column("rooms", col)

    rejection_reason_enum = postgresql.ENUM(
        *REJECTION_REASON_VALUES,
        name="rejectionreason",
        create_type=False,
    )
    rejection_reason_enum.drop(op.get_bind(), checkfirst=True)
