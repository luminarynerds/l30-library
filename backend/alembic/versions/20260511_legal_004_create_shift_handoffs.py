"""create shift_handoffs table

Revision ID: legal_004
Revises: legal_003
Create Date: 2026-05-11

Note: Table was created directly in production. This migration
exists for consistency so new deployments get the table via alembic.
"""
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "legal_004"
down_revision: Union[str, None] = "legal_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS shift_handoffs (
            id SERIAL PRIMARY KEY,
            author_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.drop_table('shift_handoffs')
