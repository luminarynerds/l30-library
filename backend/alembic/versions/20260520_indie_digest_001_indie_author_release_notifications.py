"""indie_author_release_notifications table

Revision ID: indie_digest_001
Revises: indie_follow_001
Create Date: 2026-05-20 16:00:00.000000+00:00

"""
# Idempotent CREATE TABLE pattern -- L30's init_db.py also creates this table
# from the SQLAlchemy model at startup, so the alembic op must tolerate that.
from typing import Sequence, Union

from alembic import op


revision: str = "indie_digest_001"
down_revision: Union[str, None] = "indie_follow_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS indie_author_release_notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            indie_author_id INTEGER NOT NULL REFERENCES indie_authors(id) ON DELETE CASCADE,
            metislib_ebook_id INTEGER NOT NULL,
            sent_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_indie_release_notif_user_ebook UNIQUE (user_id, metislib_ebook_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_indie_release_notif_user_id "
        "ON indie_author_release_notifications(user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_indie_release_notif_indie_author_id "
        "ON indie_author_release_notifications(indie_author_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_indie_release_notif_metislib_ebook_id "
        "ON indie_author_release_notifications(metislib_ebook_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS indie_author_release_notifications")
