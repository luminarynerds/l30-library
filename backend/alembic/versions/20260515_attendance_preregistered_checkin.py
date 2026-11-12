# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""attendance pre_registered check-in: registration_id FK

Revision ID: attendance_preregistered_001
Revises: events_phase2_001
Create Date: 2026-05-15

Single concern: attribution link from an AttendanceCheckIn back to the
EventRegistration it satisfies, so the staff Roster's "Mark attended"
action no longer has to fall back to a synthetic walk-in row.

Schema-only, additive, prod-safe:
  * attendance_check_ins.registration_id INTEGER NULL FK ->
    event_registrations.id ON DELETE SET NULL. Nullable because the
    column does not apply to walk-ins, QR scans, head counts, or
    library-card scans — only to the new pre_registered check-in path.
    Indexed for "all check-ins for a registration" lookups (idempotency
    guard + audit). ON DELETE SET NULL so historical attendance stats
    survive cancellation/deletion of a registration row.

Note on CheckInMethod: CheckInMethod is a Python str-Enum but the
backing column attendance_check_ins.check_in_method is a free-form
String(50) (not a Postgres enum type), so adding the new
PRE_REGISTERED = "pre_registered" value needs NO DDL — it is already
written by the model layer once the enum member exists. This migration
only handles the FK column.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "attendance_preregistered_001"
down_revision: Union[str, None] = "events_phase2_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attendance_check_ins",
        sa.Column(
            "registration_id",
            sa.Integer(),
            sa.ForeignKey("event_registrations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_attendance_check_ins_registration_id",
        "attendance_check_ins",
        ["registration_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_attendance_check_ins_registration_id",
        table_name="attendance_check_ins",
    )
    op.drop_column("attendance_check_ins", "registration_id")
