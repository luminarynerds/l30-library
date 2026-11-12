# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add Phase 2 gap fields to indie_ebooks (additive).

Static metadata captured from MetisLib detail so L30 renders indie detail pages
from the owned table without proxying MetisLib. All nullable -> additive, safe
to apply with patrons online; the importer backfills.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "indie_own_data_002"
down_revision: Union[str, Sequence[str], None] = "merge_acct_heads_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("indie_ebooks", sa.Column("subjects", sa.Text(), nullable=True))
    op.add_column("indie_ebooks", sa.Column("content_rating", sa.String(16), nullable=True))
    op.add_column("indie_ebooks", sa.Column("word_count", sa.Integer(), nullable=True))
    op.add_column("indie_ebooks", sa.Column("page_count", sa.Integer(), nullable=True))
    op.add_column("indie_ebooks", sa.Column("isbn", sa.String(32), nullable=True))
    op.add_column("indie_ebooks", sa.Column("author_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    for col in ("author_id", "isbn", "page_count", "word_count", "content_rating", "subjects"):
        op.drop_column("indie_ebooks", col)
