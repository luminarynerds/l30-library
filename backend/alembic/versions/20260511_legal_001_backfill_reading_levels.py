"""backfill reading levels not null

Revision ID: legal_001
Revises: merge_001
Create Date: 2026-05-11
"""
from typing import Sequence, Union

from alembic import op

revision: str = "legal_001"
down_revision: Union[str, None] = "branding_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE legal_guides SET reading_level = 'middle_school' WHERE reading_level IS NULL"
    )
    op.alter_column('legal_guides', 'reading_level', nullable=False)


def downgrade() -> None:
    op.alter_column('legal_guides', 'reading_level', nullable=True)
