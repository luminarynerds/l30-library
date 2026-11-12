"""add clinic coordinates

Revision ID: legal_003
Revises: legal_002
Create Date: 2026-05-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "legal_003"
down_revision: Union[str, None] = "legal_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('legal_clinics', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('legal_clinics', sa.Column('longitude', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('legal_clinics', 'longitude')
    op.drop_column('legal_clinics', 'latitude')
