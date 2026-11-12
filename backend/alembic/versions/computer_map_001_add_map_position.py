# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add map position columns to computers

Revision ID: computer_map_001
Revises: book_clubs_genre_001
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa

revision = "computer_map_001"
down_revision = "book_clubs_genre_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("computers", sa.Column("map_x", sa.Float(), nullable=True))
    op.add_column("computers", sa.Column("map_y", sa.Float(), nullable=True))
    op.add_column("computers", sa.Column("map_floor", sa.String(length=50), nullable=True))
    op.create_index("ix_computers_map_floor", "computers", ["map_floor"])


def downgrade() -> None:
    op.drop_index("ix_computers_map_floor", table_name="computers")
    op.drop_column("computers", "map_floor")
    op.drop_column("computers", "map_y")
    op.drop_column("computers", "map_x")
