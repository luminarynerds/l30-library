# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""restore beta_feedback table + enum types dropped by schema_sync_003

The schema_sync_003 pre-beta cleanup dropped beta_feedback (and its three
enum types) on the assumption it was dead. The model, API router, and
beta-feedback feature are in fact live (router registered in
app/api/v1/registry.py, guarded by require_beta_features_enabled).

This migration recreates the three enum types and the table with the
same schema as the model definition.

Revision ID: beta_feedback_restore_001
Revises: cms_restore_001
Create Date: 2026-05-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "beta_feedback_restore_001"
down_revision: Union[str, Sequence[str], None] = "cms_restore_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FEEDBACK_TYPE = postgresql.ENUM(
    "bug", "suggestion", "confusion", "praise", "other",
    name="beta_feedbacktype",
    create_type=False,
)
_FEEDBACK_STATUS = postgresql.ENUM(
    "new", "reviewed", "in_progress", "resolved", "wont_fix",
    name="feedbackstatus",
    create_type=False,
)
_FEEDBACK_PRIORITY = postgresql.ENUM(
    "low", "medium", "high", "critical",
    name="feedbackpriority",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    # Create the three enum types (idempotent)
    bind.execute(sa.text("""
        CREATE TYPE beta_feedbacktype AS ENUM (
            'bug', 'suggestion', 'confusion', 'praise', 'other'
        )
    """))
    bind.execute(sa.text("""
        CREATE TYPE feedbackstatus AS ENUM (
            'new', 'reviewed', 'in_progress', 'resolved', 'wont_fix'
        )
    """))
    bind.execute(sa.text("""
        CREATE TYPE feedbackpriority AS ENUM (
            'low', 'medium', 'high', 'critical'
        )
    """))

    op.create_table(
        "beta_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", _FEEDBACK_TYPE, nullable=False),
        sa.Column("status", _FEEDBACK_STATUS, nullable=False),
        sa.Column("priority", _FEEDBACK_PRIORITY, nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("page_url", sa.String(length=500), nullable=True),
        sa.Column("browser_info", sa.String(length=300), nullable=True),
        sa.Column("screenshot_url", sa.String(length=500), nullable=True),
        sa.Column("submitted_by_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "extra_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_beta_feedback_id", "beta_feedback", ["id"])
    op.create_index("ix_beta_feedback_type", "beta_feedback", ["type"])


def downgrade() -> None:
    op.drop_index("ix_beta_feedback_type", table_name="beta_feedback")
    op.drop_index("ix_beta_feedback_id", table_name="beta_feedback")
    op.drop_table("beta_feedback")

    bind = op.get_bind()
    bind.execute(sa.text("DROP TYPE IF EXISTS feedbackpriority"))
    bind.execute(sa.text("DROP TYPE IF EXISTS feedbackstatus"))
    bind.execute(sa.text("DROP TYPE IF EXISTS beta_feedbacktype"))
