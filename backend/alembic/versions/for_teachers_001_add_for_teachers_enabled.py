"""add for_teachers_enabled to organization_features

Revision ID: for_teachers_001
Revises: teacher_role_001
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "for_teachers_001"
down_revision = "reading_list_requests_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organization_features",
        sa.Column("for_teachers_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("organization_features", "for_teachers_enabled")
