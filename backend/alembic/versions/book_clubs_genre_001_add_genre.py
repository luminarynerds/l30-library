# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add genre to book_clubs

Revision ID: book_clubs_genre_001
Revises: 20260512_pay_rates
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa

revision = "book_clubs_genre_001"
down_revision = "20260512_pay_rates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("book_clubs", sa.Column("genre", sa.String(64), nullable=True))
    op.create_index("ix_book_clubs_genre", "book_clubs", ["genre"])


def downgrade() -> None:
    op.drop_index("ix_book_clubs_genre", table_name="book_clubs")
    op.drop_column("book_clubs", "genre")
