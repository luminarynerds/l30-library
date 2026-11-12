# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add courses.duration_days and enrollments.due_at

Revision ID: course_dur_due_001
Revises: search_analytics_001
Create Date: 2026-05-03

Schema-only, additive, NULLable changes — backward-compatible with the running
backend so we can deploy this migration before rolling out new code:
  * courses.duration_days INTEGER NULL — how many days a learner has to
    complete after enrollment. NULL means no deadline.
  * enrollments.due_at TIMESTAMP WITH TIME ZONE NULL + index ix_enrollments_due_at
    — computed at enroll time from course.duration_days. Indexed because
    KPI queries (overdue / due-soon counts) filter on it.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "course_dur_due_001"
down_revision: Union[str, None] = "search_analytics_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # duration_days may already exist if added manually before this migration
    duration_days_exists = False
    if not op.get_context().as_sql:
        bind = op.get_bind()
        result = bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='courses' AND column_name='duration_days'"
            )
        )
        duration_days_exists = result.fetchone() is not None
    if not duration_days_exists:
        op.add_column(
            "courses",
            sa.Column("duration_days", sa.Integer(), nullable=True),
        )
    op.add_column(
        "enrollments",
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_enrollments_due_at",
        "enrollments",
        ["due_at"],
        unique=False,
    )

def downgrade() -> None:
    op.drop_index("ix_enrollments_due_at", table_name="enrollments")
    op.drop_column("enrollments", "due_at")
    op.drop_column("courses", "duration_days")
