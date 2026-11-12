# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""cg_lifecycle_001: archive columns + parent_connection_group_meetings.

Revision ID: cg_lifecycle_001
Revises: patron_category_001
Create Date: 2026-05-25

Adds:
  * parent_connection_groups: cohort_start_date, cohort_end_date,
    archived_at, archived_by_id (FK users SET NULL), archive_reason,
    archive_notes.
  * parent_connection_group_meetings: new table for individual meeting
    instances. Composite unique on (group_id, meeting_date), non-unique
    index on (group_id, status).

down_revision is pinned to patron_category_001 — the most recent main-branch
head at the time of this PR. Per feedback_l30_alembic_multi_head_deploy, L30
routinely runs main with multiple alembic heads; we pick one and let the
existing mergepoint workflow handle the rest. Branch labels are not used.

L30 init_db.py creates SQLAlchemy-defined tables at backend startup, so
CREATE TABLE / CREATE INDEX / ALTER TABLE ADD COLUMN are all wrapped in IF
NOT EXISTS where supported. ADD COLUMN IF NOT EXISTS keeps the migration
idempotent across rebuilds (see backend/scripts/check_alembic_idempotent.py
and feedback_l30_init_db_vs_alembic_new_table).
"""
from typing import Sequence, Union

from alembic import op


revision: str = "cg_lifecycle_001"
down_revision: Union[str, None] = "patron_category_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- ParentConnectionGroup: cohort + archive audit columns ----
    op.execute(
        """
        ALTER TABLE parent_connection_groups
            ADD COLUMN IF NOT EXISTS cohort_start_date DATE,
            ADD COLUMN IF NOT EXISTS cohort_end_date DATE,
            ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS archived_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS archive_reason VARCHAR(40),
            ADD COLUMN IF NOT EXISTS archive_notes TEXT
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parent_connection_groups_archived_by_id "
        "ON parent_connection_groups (archived_by_id)"
    )

    # ---- ParentConnectionGroupMeeting: new table ----
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS parent_connection_group_meetings (
            id SERIAL PRIMARY KEY,
            group_id INTEGER NOT NULL REFERENCES parent_connection_groups(id) ON DELETE CASCADE,
            meeting_date DATE NOT NULL,
            scheduled_time VARCHAR(5),
            location VARCHAR(300),
            status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
            cancelled_reason VARCHAR(40),
            cancelled_at TIMESTAMPTZ,
            cancelled_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            rescheduled_to_meeting_id INTEGER REFERENCES parent_connection_group_meetings(id) ON DELETE SET NULL,
            staff_notes TEXT,
            patron_message TEXT,
            email_dispatched_at TIMESTAMPTZ,
            email_dispatched_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_connection_group_meeting_date UNIQUE (group_id, meeting_date)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parent_connection_group_meetings_group_id "
        "ON parent_connection_group_meetings (group_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parent_connection_group_meetings_meeting_date "
        "ON parent_connection_group_meetings (meeting_date)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parent_connection_group_meetings_cancelled_by_id "
        "ON parent_connection_group_meetings (cancelled_by_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_connection_group_meeting_status "
        "ON parent_connection_group_meetings (group_id, status)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS parent_connection_group_meetings")
    op.execute(
        """
        ALTER TABLE parent_connection_groups
            DROP COLUMN IF EXISTS archive_notes,
            DROP COLUMN IF EXISTS archive_reason,
            DROP COLUMN IF EXISTS archived_by_id,
            DROP COLUMN IF EXISTS archived_at,
            DROP COLUMN IF EXISTS cohort_end_date,
            DROP COLUMN IF EXISTS cohort_start_date
        """
    )
