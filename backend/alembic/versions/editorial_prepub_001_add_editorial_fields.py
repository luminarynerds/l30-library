# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add editorial provenance columns to tracker_books (source, source_url, blurb, blurb_credit, is_featured)."""
import sqlalchemy as sa
from alembic import op

revision = "editorial_prepub_001"
down_revision = "remove_beta_invites_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tracker_books",
        sa.Column("source", sa.String(length=30), nullable=False, server_default="author_scan"),
    )
    op.add_column("tracker_books", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("tracker_books", sa.Column("blurb", sa.Text(), nullable=True))
    op.add_column("tracker_books", sa.Column("blurb_credit", sa.String(length=255), nullable=True))
    op.add_column(
        "tracker_books",
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_tracker_books_source", "tracker_books", ["source"])
    op.create_index("ix_tracker_books_is_featured", "tracker_books", ["is_featured"])


def downgrade() -> None:
    op.drop_index("ix_tracker_books_is_featured", table_name="tracker_books")
    op.drop_index("ix_tracker_books_source", table_name="tracker_books")
    op.drop_column("tracker_books", "is_featured")
    op.drop_column("tracker_books", "blurb_credit")
    op.drop_column("tracker_books", "blurb")
    op.drop_column("tracker_books", "source_url")
    op.drop_column("tracker_books", "source")
