# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add reading_list_requests

Revision ID: reading_list_requests_001
Revises: teacher_role_001
Create Date: 2026-05-14 20:00:00.000000

Adds the reading_list_requests table backing the teacher Reading Lists page
(frontend/src/pages/TeacherReadingListsPage.tsx). A teacher submits a request
for copies of a SharedReadingList for their classroom; staff approve, fulfill,
or reject; teachers can cancel their own pending/approved requests.

Single table - status discriminates pending/approved/fulfilled/rejected/cancelled.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "reading_list_requests_001"
down_revision: Union[str, None] = "teacher_role_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reading_list_requests",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "school_id",
            sa.Integer(),
            sa.ForeignKey("outreach_partners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reading_list_id",
            sa.Integer(),
            sa.ForeignKey("shared_reading_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "teacher_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("copies", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "fulfilled_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_reading_list_requests_school_id",
        "reading_list_requests",
        ["school_id"],
    )
    op.create_index(
        "ix_reading_list_requests_reading_list_id",
        "reading_list_requests",
        ["reading_list_id"],
    )
    op.create_index(
        "ix_reading_list_requests_teacher_user_id",
        "reading_list_requests",
        ["teacher_user_id"],
    )
    op.create_index(
        "ix_reading_list_requests_status",
        "reading_list_requests",
        ["status"],
    )
    op.create_index(
        "ix_reading_list_requests_school_status",
        "reading_list_requests",
        ["school_id", "status"],
    )
    op.create_index(
        "ix_reading_list_requests_teacher_school",
        "reading_list_requests",
        ["teacher_user_id", "school_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reading_list_requests_teacher_school",
        table_name="reading_list_requests",
    )
    op.drop_index(
        "ix_reading_list_requests_school_status",
        table_name="reading_list_requests",
    )
    op.drop_index(
        "ix_reading_list_requests_status",
        table_name="reading_list_requests",
    )
    op.drop_index(
        "ix_reading_list_requests_teacher_user_id",
        table_name="reading_list_requests",
    )
    op.drop_index(
        "ix_reading_list_requests_reading_list_id",
        table_name="reading_list_requests",
    )
    op.drop_index(
        "ix_reading_list_requests_school_id",
        table_name="reading_list_requests",
    )
    op.drop_table("reading_list_requests")
