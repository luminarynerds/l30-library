"""add blog_email_subscriptions table

Revision ID: d530b5a403bd
Revises: event_registration_cancelled_001
Create Date: 2026-05-23 14:34:56.768885+00:00

"""
# NOTE: When adding new tables, use
#   op.execute("CREATE TABLE IF NOT EXISTS ...")
# instead of op.create_table(). L30's init_db.py auto-creates tables from
# SQLAlchemy models at backend startup, so by the time alembic runs the
# table may already exist and op.create_table() raises DuplicateTableError.
# See [[feedback_l30_init_db_vs_alembic_new_table]].
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd530b5a403bd'
down_revision: Union[str, None] = 'event_registration_cancelled_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create blog_email_subscriptions table.

    Idempotent: init_db.py may have already created the table at startup
    from SQLAlchemy metadata, so use CREATE TABLE IF NOT EXISTS.
    """
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS blog_email_subscriptions (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            frequency VARCHAR(20) NOT NULL DEFAULT 'weekly',
            last_sent_at TIMESTAMPTZ NULL,
            confirmed_at TIMESTAMPTZ NULL,
            confirmation_token VARCHAR(64) NOT NULL,
            unsubscribe_token VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_blog_subscription_email_freq UNIQUE (email, frequency)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_blog_email_subscriptions_email "
        "ON blog_email_subscriptions (email)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_blog_email_subscriptions_user_id "
        "ON blog_email_subscriptions (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_blog_email_subscriptions_confirmation_token "
        "ON blog_email_subscriptions (confirmation_token)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_blog_email_subscriptions_unsubscribe_token "
        "ON blog_email_subscriptions (unsubscribe_token)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS blog_email_subscriptions")
