# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Free-preview lessons: add lessons.is_preview and seed the first lesson of each course.

Additive + safe to apply with patrons online: the column is NOT NULL with a
server_default of false, so existing rows get false. The data step then flags
the first lesson (by module order, then lesson order) of every course as a free
preview, so anonymous / unenrolled patrons can read one lesson per course.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "lesson_preview_001"
down_revision: Union[str, Sequence[str], None] = "indie_own_data_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column(
            "is_preview",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    # Seed: first lesson of each course (lowest module sort_order, then lowest
    # lesson sort_order) becomes the free preview.
    op.execute(
        """
        UPDATE lessons SET is_preview = true
        WHERE id IN (
            SELECT DISTINCT ON (m.course_id) l.id
            FROM lessons l
            JOIN modules m ON l.module_id = m.id
            ORDER BY m.course_id, m.sort_order, m.id, l.sort_order, l.id
        )
        """
    )


def downgrade() -> None:
    op.drop_column("lessons", "is_preview")
