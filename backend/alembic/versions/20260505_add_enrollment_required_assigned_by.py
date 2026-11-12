# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add enrollments.is_required and enrollments.assigned_by_id

Revision ID: enroll_req_assign_001
Revises: enroll_due_backfill_001
Create Date: 2026-05-05

Wave 4 — required vs recommended split + manager assignment workflow.

Schema-only, additive, prod-safe:
  * enrollments.is_required BOOLEAN NOT NULL DEFAULT false (server-level
    default so existing rows transparently become "recommended" without a
    data migration). Indexed — the new staff trainings UI splits the table
    into Required / Recommended sections and filters on this column.
  * enrollments.assigned_by_id INTEGER NULL FK -> users.id ON DELETE SET NULL
    so a deleted manager doesn't cascade-delete the enrollment, just drops
    the attribution. Indexed for "who did manager X assign?" lookups.

The columns are NULLable / have server defaults so the running backend can
keep writing existing-shape Enrollment rows during the rolling deploy
window — backward-compatible with code that hasn't yet learned about the
new fields.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "enroll_req_assign_001"
down_revision: Union[str, None] = "enroll_due_backfill_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "enrollments",
        sa.Column(
            "is_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "enrollments",
        sa.Column(
            "assigned_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_enrollments_is_required",
        "enrollments",
        ["is_required"],
        unique=False,
    )
    op.create_index(
        "ix_enrollments_assigned_by_id",
        "enrollments",
        ["assigned_by_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_enrollments_assigned_by_id", table_name="enrollments")
    op.drop_index("ix_enrollments_is_required", table_name="enrollments")
    op.drop_column("enrollments", "assigned_by_id")
    op.drop_column("enrollments", "is_required")
