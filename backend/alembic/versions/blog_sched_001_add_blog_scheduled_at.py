# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add blog scheduled_at column and status

Revision ID: blog_sched_001
Revises: blog001_stamp
Create Date: 2026-05-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "blog_sched_001"
down_revision: Union[str, None] = "blog001_stamp"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("blog_posts", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("blog_posts", "scheduled_at")
