"""staff support triage: category column + events table

Revision ID: staff_support_triage_001
Revises: cdb306acb450
Create Date: 2026-05-17 12:00:00.000000+00:00

"""
# NOTE: init_db.py auto-creates tables from SQLAlchemy models. We use
# CREATE TABLE IF NOT EXISTS and add columns with IF NOT EXISTS for idempotency.
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "staff_support_triage_001"
down_revision: Union[str, None] = "cdb306acb450"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add category column to support_tickets
    op.execute(
        "ALTER TABLE support_tickets "
        "ADD COLUMN IF NOT EXISTS category VARCHAR(64)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_support_tickets_category "
        "ON support_tickets (category)"
    )

    # Events table: append-only triage history
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS support_ticket_events (
            id SERIAL PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
            event_type VARCHAR(40) NOT NULL,
            actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            actor_identifier VARCHAR(255),
            from_value VARCHAR(255),
            to_value VARCHAR(255),
            note TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_support_ticket_events_ticket "
        "ON support_ticket_events (ticket_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_support_ticket_events_type "
        "ON support_ticket_events (event_type, created_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS support_ticket_events")
    op.execute("DROP INDEX IF EXISTS ix_support_tickets_category")
    op.execute("ALTER TABLE support_tickets DROP COLUMN IF EXISTS category")
