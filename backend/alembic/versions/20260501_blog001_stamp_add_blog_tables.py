# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# add blog tables (stamped - tables already exist)
#
# Revision ID: blog001_stamp
# Revises: 0001_initial
# Create Date: 2026-05-01

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "blog001_stamp"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Blog tables already exist in the database.
    # This is a stamp-only migration to track state.
    pass


def downgrade() -> None:
    op.drop_table("blog_post_tags")
    op.drop_table("blog_posts")
    op.drop_table("blog_tags")
