# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create nudges and patron_nudge_state tables

Revision ID: nudges_001
Revises: blog_ver_001
Create Date: 2026-05-05 23:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "nudges_001"
down_revision: Union[str, None] = "trigram_idx_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nudges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("trigger_conditions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("content_title", sa.String(200), nullable=True),
        sa.Column("content_body", sa.Text(), nullable=False),
        sa.Column("content_cta_label", sa.String(100), nullable=True),
        sa.Column("content_cta_route", sa.String(200), nullable=True),
        sa.Column("delivery_type", sa.String(20), nullable=False),
        sa.Column("delivery_placement", sa.String(50), nullable=False, server_default="global"),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="5"),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="604800"),
        sa.Column("max_impressions", sa.SmallInteger(), nullable=False, server_default="3"),
        sa.Column("tags", sa.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "patron_nudge_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patron_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nudge_id", sa.Integer(), sa.ForeignKey("nudges.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="shown"),
        sa.Column("impressions", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("first_shown_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_shown_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_unique_constraint("uq_patron_nudge", "patron_nudge_state", ["patron_id", "nudge_id"])
    op.create_index("ix_patron_nudge_state_patron_status", "patron_nudge_state", ["patron_id", "status"])


def downgrade() -> None:
    op.drop_table("patron_nudge_state")
    op.drop_table("nudges")
