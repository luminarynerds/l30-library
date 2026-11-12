# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fatten indie_ebooks into an owned catalog record (Phase 1).

Adds owned metadata + local EPUB file_path columns so L30 can stop proxying
MetisLib at display time. All columns nullable / defaulted -> additive and safe
to apply with patrons online. No data backfill here; the importer populates.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "indie_own_data_001"
down_revision: Union[str, Sequence[str], None] = "branding_nd_access_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("indie_ebooks", sa.Column("title", sa.String(500), nullable=True))
    op.add_column("indie_ebooks", sa.Column("author_pen_name", sa.String(255), nullable=True))
    op.add_column("indie_ebooks", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("indie_ebooks", sa.Column("cover_url", sa.String(1024), nullable=True))
    op.add_column("indie_ebooks", sa.Column("genre", sa.String(255), nullable=True))
    op.add_column("indie_ebooks", sa.Column("language", sa.String(16), nullable=True))
    op.add_column("indie_ebooks", sa.Column("publication_year", sa.Integer(), nullable=True))
    op.add_column("indie_ebooks", sa.Column("file_format", sa.String(32), nullable=True))
    op.add_column("indie_ebooks", sa.Column("content_warnings", sa.Text(), nullable=True))
    op.add_column("indie_ebooks", sa.Column("copies_owned", sa.Integer(), server_default="0", nullable=False))
    op.add_column("indie_ebooks", sa.Column("copies_available", sa.Integer(), server_default="0", nullable=False))
    op.add_column("indie_ebooks", sa.Column("price_per_copy", sa.Numeric(10, 2), nullable=True))
    op.add_column("indie_ebooks", sa.Column("file_path", sa.String(1024), nullable=True))
    op.add_column("indie_ebooks", sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("indie_ebooks", sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for col in (
        "imported_at", "source_updated_at", "file_path", "price_per_copy",
        "copies_available", "copies_owned", "content_warnings", "file_format",
        "publication_year", "language", "genre", "cover_url", "description",
        "author_pen_name", "title",
    ):
        op.drop_column("indie_ebooks", col)
