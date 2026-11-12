"""indie_author_follows table

Revision ID: indie_follow_001
Revises: df85cac32c74
Create Date: 2026-05-20 14:00:00.000000+00:00

"""
# Idempotent CREATE TABLE pattern -- L30's init_db.py also creates this table
# from the SQLAlchemy model at startup, so the alembic op must tolerate that.
from typing import Sequence, Union

from alembic import op


revision: str = "indie_follow_001"
down_revision: Union[str, None] = "df85cac32c74"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS indie_author_follows (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            indie_author_id INTEGER NOT NULL REFERENCES indie_authors(id) ON DELETE CASCADE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_indie_author_follow_user_author UNIQUE (user_id, indie_author_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_indie_author_follows_user_id ON indie_author_follows(user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_indie_author_follows_indie_author_id ON indie_author_follows(indie_author_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS indie_author_follows")
