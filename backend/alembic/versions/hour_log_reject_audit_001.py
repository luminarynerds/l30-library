# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add rejected_by_id + rejected_at to general_volunteer_hour_logs.

Revision ID: hour_log_reject_audit_001
Revises: pto_balance_composite_001
Create Date: 2026-07-08

Reject audit trail: the reject_hours endpoint (#1873 follow-up) stamped
status + rejected_reason only, with no record of who rejected an hour log
or when -- the verify path has verified_by_id/verified_at for exactly this,
reject had nothing. Mirrors verified_by_id/verified_at exactly: nullable FK
to users, SET NULL on delete, tz-aware timestamp.

Idempotent: every ADD COLUMN uses IF NOT EXISTS because init_db.py at
container startup auto-creates from SQLAlchemy model metadata BEFORE
alembic runs (feedback_l30_init_db_vs_alembic_new_table).
"""
from alembic import op

revision = "hour_log_reject_audit_001"
down_revision = "pto_balance_composite_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE general_volunteer_hour_logs "
        "ADD COLUMN IF NOT EXISTS rejected_by_id INTEGER"
    )
    op.execute(
        "ALTER TABLE general_volunteer_hour_logs "
        "ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMP WITH TIME ZONE"
    )
    # Foreign key as a separate idempotent step -- pg_constraint probe so
    # re-running the migration after init_db.py created the column does
    # not 42710 "constraint already exists".
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'general_volunteer_hour_logs_rejected_by_id_fkey'
            ) THEN
                ALTER TABLE general_volunteer_hour_logs
                ADD CONSTRAINT general_volunteer_hour_logs_rejected_by_id_fkey
                FOREIGN KEY (rejected_by_id) REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        END$$;
    """)


def downgrade() -> None:
    op.execute(
        "ALTER TABLE general_volunteer_hour_logs "
        "DROP CONSTRAINT IF EXISTS general_volunteer_hour_logs_rejected_by_id_fkey"
    )
    op.execute(
        "ALTER TABLE general_volunteer_hour_logs "
        "DROP COLUMN IF EXISTS rejected_at"
    )
    op.execute(
        "ALTER TABLE general_volunteer_hour_logs "
        "DROP COLUMN IF EXISTS rejected_by_id"
    )
