"""create waitlist_signups table

Patron waiting-list signups for the invite-only /register flow.

Revision ID: l30_waitlist_001
Revises: payroll_policy_001
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op

revision = "l30_waitlist_001"
down_revision = "payroll_policy_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS waitlist_signups (
            id SERIAL PRIMARY KEY,
            email VARCHAR NOT NULL,
            source VARCHAR(50) NOT NULL DEFAULT 'register',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_l30_waitlist_signups_email_lower "
        "ON waitlist_signups (lower(email))"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS waitlist_signups")
