# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add library_visit_requests

Revision ID: library_visits_001
Revises: widen_recipient_hint_001
Create Date: 2026-05-14 19:00:00.000000

Adds the library_visit_requests table backing the teacher Library Visit
Scheduling page (frontend/src/pages/LibraryVisitSchedulingPage.tsx).
Single table - status discriminates pending/scheduled/rejected/cancelled.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "library_visits_001"
down_revision: Union[str, None] = "widen_recipient_hint_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "library_visit_requests",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "school_id",
            sa.Integer(),
            sa.ForeignKey("outreach_partners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "teacher_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("teacher_name", sa.String(length=200), nullable=False),
        sa.Column("requested_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("number_of_students", sa.Integer(), nullable=False),
        sa.Column("grade_level", sa.String(length=100), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "approved_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_library_visit_requests_school_id",
        "library_visit_requests",
        ["school_id"],
    )
    op.create_index(
        "ix_library_visit_requests_teacher_user_id",
        "library_visit_requests",
        ["teacher_user_id"],
    )
    op.create_index(
        "ix_library_visit_requests_status",
        "library_visit_requests",
        ["status"],
    )
    op.create_index(
        "ix_library_visit_requests_school_status",
        "library_visit_requests",
        ["school_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_library_visit_requests_school_status",
        table_name="library_visit_requests",
    )
    op.drop_index(
        "ix_library_visit_requests_status",
        table_name="library_visit_requests",
    )
    op.drop_index(
        "ix_library_visit_requests_teacher_user_id",
        table_name="library_visit_requests",
    )
    op.drop_index(
        "ix_library_visit_requests_school_id",
        table_name="library_visit_requests",
    )
    op.drop_table("library_visit_requests")
