# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""backfill course_stage_transitions for historical courses

Revision ID: backfill_course_stage_transitions_001
Revises: lesson_timestamps_001
Create Date: 2026-05-24

Wave 2 / W2-E. The ``course_stage_transitions`` table was added in
pre-Wave-1 lifecycle work but holds zero rows in prod because all 12
published courses were direct-seeded and bypassed the transition API.
Inserts one synthetic ``imported_from_pre_lifecycle`` row per published
course with no existing history. Idempotent: re-running inserts zero.

Pure data mutation; no DDL. Safe across SQLite + Postgres
(``lifecycle_stage`` is stored as varchar via ``native_enum=False``;
``from_stage`` is nullable; ``created_at`` is taken from the parent
course so the audit log timestamp sorts naturally with any future
real transitions).

The async helper at ``app.alembic_helpers.backfill_course_stage_transitions``
mirrors this logic for unit testing (3 tests in
``tests/test_backfill_course_stage_transitions.py``).
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "backfill_course_stage_transitions_001"
down_revision: Union[str, None] = "lesson_timestamps_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INSERT_SQL = """
INSERT INTO course_stage_transitions
    (course_id, from_stage, to_stage, actor_id, note, created_at)
SELECT c.id, NULL, 'published', NULL,
       'imported_from_pre_lifecycle', c.created_at
FROM courses c
WHERE c.lifecycle_stage = 'published'
  AND NOT EXISTS (
    SELECT 1 FROM course_stage_transitions cst
    WHERE cst.course_id = c.id
  )
"""


def upgrade() -> None:
    if op.get_context().as_sql:
        # Offline mode: emit the INSERT for the operator to apply. rowcount
        # reporting is online-only because execute() returns None in --sql mode.
        op.execute(_INSERT_SQL)
        return

    bind = op.get_bind()
    result = bind.execute(text(_INSERT_SQL))
    print(
        "backfill_course_stage_transitions: inserted "
        f"{result.rowcount} rows"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM course_stage_transitions "
        "WHERE note = 'imported_from_pre_lifecycle'"
    )
