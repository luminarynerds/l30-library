# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""null out quiz_passing_threshold for course id=1 (Digital Literacy Basics)

Course id=1 ("Digital Literacy Basics") has 0 quiz questions, so the default
quiz_passing_threshold=70 is misleading -- there is nothing to pass. Set it
to NULL so the UI / completion logic can treat the course as quiz-less.

The column is already nullable (SQLAlchemy ``Column(Integer, default=70)``
with no ``nullable=False``), so a NULL is valid.

Idempotent: WHERE clause guards on title AND non-null threshold so re-runs
are no-ops. Title-guard protects against a re-seeded DB where id=1 might
map to a different course.

Revision ID: course1_quiz_threshold_null_001
Revises: bc_waitlist_001
Create Date: 2026-05-19 18:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = "course1_quiz_threshold_null_001"
down_revision: Union[str, None] = "drop_redundant_indexes_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE courses
           SET quiz_passing_threshold = NULL
         WHERE id = 1
           AND title = 'Digital Literacy Basics'
           AND quiz_passing_threshold IS NOT NULL
        """
    )


def downgrade() -> None:
    # Restore the application default (70) only for the same row, and only
    # if it is currently NULL -- don't clobber a hand-set value.
    op.execute(
        """
        UPDATE courses
           SET quiz_passing_threshold = 70
         WHERE id = 1
           AND title = 'Digital Literacy Basics'
           AND quiz_passing_threshold IS NULL
        """
    )
