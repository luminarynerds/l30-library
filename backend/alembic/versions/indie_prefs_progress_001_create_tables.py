# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create indie_content_preferences and indie_reading_progress tables

Revision ID: indie_prefs_progress_001
Revises: vote_immutability_001
Create Date: 2026-05-11
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision: str = "indie_prefs_progress_001"
down_revision: Union[str, None] = "schema_sync_005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "indie_content_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("hidden_warnings", JSON, nullable=False, server_default="[]"),
        sa.Column("flagged_warnings", JSON, nullable=False, server_default="[]"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "indie_reading_progress",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "ebook_id",
            sa.Integer(),
            sa.ForeignKey("indie_ebooks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_position", sa.String(500), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "ebook_id", name="uq_indie_reading_progress_user_ebook"
        ),
    )


def downgrade() -> None:
    op.drop_table("indie_reading_progress")
    op.drop_table("indie_content_preferences")
