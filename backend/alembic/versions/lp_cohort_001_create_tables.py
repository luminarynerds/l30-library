# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create learning_path_cohort_members + learning_path_discussion_posts

V1: opt-in cohorts for learning paths + one flat shared discussion
wall per path. Partial unique index on (learning_path_id, user_id)
WHERE deleted_at IS NULL lets a user leave and rejoin.

Revision ID: lp_cohort_001
Revises: bc_waitlist_001
Create Date: 2026-05-19
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "lp_cohort_001"
down_revision: Union[str, None] = "course1_quiz_threshold_null_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_path_cohort_members",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "learning_path_id",
            sa.Integer(),
            sa.ForeignKey("learning_paths.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opted_in_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_learning_path_cohort_members_learning_path_id",
        "learning_path_cohort_members",
        ["learning_path_id"],
    )
    op.create_index(
        "ix_learning_path_cohort_members_user_id",
        "learning_path_cohort_members",
        ["user_id"],
    )
    op.create_index(
        "ix_lp_cohort_members_path_user",
        "learning_path_cohort_members",
        ["learning_path_id", "user_id"],
    )
    # Partial unique index: a user has at most one *active* membership
    # per learning path. Soft-deleted rows are excluded so a user can
    # leave and rejoin.
    op.create_index(
        "uq_lp_cohort_members_active",
        "learning_path_cohort_members",
        ["learning_path_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "learning_path_discussion_posts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "learning_path_id",
            sa.Integer(),
            sa.ForeignKey("learning_paths.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "author_display_name",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_learning_path_discussion_posts_learning_path_id",
        "learning_path_discussion_posts",
        ["learning_path_id"],
    )
    op.create_index(
        "ix_lp_discussion_posts_path_created",
        "learning_path_discussion_posts",
        ["learning_path_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_lp_discussion_posts_path_created",
        table_name="learning_path_discussion_posts",
    )
    op.drop_index(
        "ix_learning_path_discussion_posts_learning_path_id",
        table_name="learning_path_discussion_posts",
    )
    op.drop_table("learning_path_discussion_posts")

    op.drop_index(
        "uq_lp_cohort_members_active",
        table_name="learning_path_cohort_members",
    )
    op.drop_index(
        "ix_lp_cohort_members_path_user",
        table_name="learning_path_cohort_members",
    )
    op.drop_index(
        "ix_learning_path_cohort_members_user_id",
        table_name="learning_path_cohort_members",
    )
    op.drop_index(
        "ix_learning_path_cohort_members_learning_path_id",
        table_name="learning_path_cohort_members",
    )
    op.drop_table("learning_path_cohort_members")
