"""add front_desk_enabled and serials_enabled to organization_features

Revision ID: sidebar_flags_001
Revises: 
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = "sidebar_flags_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organization_features",
        sa.Column("front_desk_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "organization_features",
        sa.Column("serials_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("organization_features", "serials_enabled")
    op.drop_column("organization_features", "front_desk_enabled")
