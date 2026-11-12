# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""backfill enrollments.due_at from enrolled_at + 30 days

Revision ID: enroll_due_backfill_001
Revises: course_dur_due_001
Create Date: 2026-05-04

Data-only migration (separate from the schema migration per the project's
"one concern per migration" convention).

Backfills enrollments.due_at = enrolled_at + 30 days for every existing
enrollment that has a NULL due_at. This preserves the previous (fictional)
"enrolled + 30 days" UI behavior so nothing visually shifts at deploy time;
real per-course deadlines will be set going forward via Course.duration_days.

The downgrade clears the column back to NULL — best-effort. We cannot
distinguish post-deploy real deadlines from this backfilled value, so a
downgrade after real data accumulates will lose those values. Run only on
fresh upgrades / rollbacks.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "enroll_due_backfill_001"
down_revision: Union[str, None] = "course_dur_due_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            """
            UPDATE enrollments
            SET due_at = enrolled_at + INTERVAL '30 days'
            WHERE due_at IS NULL AND enrolled_at IS NOT NULL
            """
        )
    else:
        # SQLite fallback (used by openapi spec generator)
        op.execute(
            """
            UPDATE enrollments
            SET due_at = datetime(enrolled_at, '+30 days')
            WHERE due_at IS NULL AND enrolled_at IS NOT NULL
            """
        )


def downgrade() -> None:
    # Best-effort: clears all due_at values. After real per-course deadlines
    # are set in production, this will discard them — caveat noted in module
    # docstring. Use only for clean rollbacks before real data accumulates.
    op.execute("UPDATE enrollments SET due_at = NULL")
