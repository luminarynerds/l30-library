"""drop staff_role from code paths (column kept for now)

Revision ID: drop_staff_role_001
Revises: sidebar_flags_001
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = "drop_staff_role_001"
down_revision = "sidebar_flags_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Column left in DB intentionally -- just documenting it's unused
    pass


def downgrade() -> None:
    pass
