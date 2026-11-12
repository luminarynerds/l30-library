# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""book_club_member_imports audit table.

Creates ``book_club_member_imports`` table for the bulk member CSV import
audit log. UUID PK (gen_random_uuid()), JSONB raw_outcome blob, two indexes
on (club_id) and (imported_at).

Revision ID: book_club_member_imports_001
Revises: cg_confidential_001
Create Date: 2026-05-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "book_club_member_imports_001"
down_revision: Union[str, Sequence[str], None] = "cg_confidential_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "book_club_member_imports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "book_club_id",
            sa.Integer(),
            sa.ForeignKey("book_clubs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "imported_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("raw_outcome", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_index(
        "ix_book_club_member_imports_club",
        "book_club_member_imports",
        ["book_club_id"],
    )
    op.create_index(
        "ix_book_club_member_imports_at",
        "book_club_member_imports",
        ["imported_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_book_club_member_imports_at",
        table_name="book_club_member_imports",
    )
    op.drop_index(
        "ix_book_club_member_imports_club",
        table_name="book_club_member_imports",
    )
    op.drop_table("book_club_member_imports")
