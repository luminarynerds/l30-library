"""seeded_at on indie_author_follows

Revision ID: indie_seeded_001
Revises: indie_digest_001
Create Date: 2026-05-20 17:00:00.000000+00:00

"""
# Idempotent ALTER pattern -- L30 init_db.py auto-creates tables from models, so by
# the time alembic runs the column may already exist.
from typing import Sequence, Union

from alembic import op


revision: str = "indie_seeded_001"
down_revision: Union[str, None] = "indie_digest_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE indie_author_follows "
        "ADD COLUMN IF NOT EXISTS seeded_at TIMESTAMP WITH TIME ZONE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE indie_author_follows DROP COLUMN IF EXISTS seeded_at")
