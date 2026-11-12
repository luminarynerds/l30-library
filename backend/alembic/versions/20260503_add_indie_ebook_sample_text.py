# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add sample_text column to indie_ebooks for book preview feature.

Revision ID: indie_sample_001
Revises: course_skills_001
Create Date: 2026-05-03

Additive, prod-safe. Adds a nullable TEXT column for storing
preview/sample text that patrons can read before borrowing.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "indie_sample_001"
down_revision: Union[str, None] = "course_skills_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("indie_ebooks", sa.Column("sample_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("indie_ebooks", "sample_text")
