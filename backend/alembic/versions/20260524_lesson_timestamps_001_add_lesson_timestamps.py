"""add lessons.created_at + lessons.updated_at

Revision ID: lesson_timestamps_001
Revises: drop_survey_lesson_type_001
Create Date: 2026-05-24 00:00:00.000000+00:00

Wave 1 of the L30 course-authoring friction strip plan, W1-B. The nightly
stub-lesson sweep (``app.services.lesson_sweep_service``) deletes lessons
that have been empty for >24h. Without ``created_at``, the sweep has no
way to identify what's old. Module rows also lack timestamps, but the
sweep only needs lesson age, so we add the columns to ``lessons`` only.

Backfills historical rows to ``now()`` so the sweep does not mass-delete
the back-catalog of legitimate lessons on first run. (Stubs created
post-deploy will get accurate timestamps via ``server_default=func.now()``.)

Note on the NOT NULL DEFAULT now() pattern: because now() is volatile,
PostgreSQL rewrites the table on this ALTER (acquiring ACCESS EXCLUSIVE briefly).
At ~138 rows this is sub-second and safe. At larger scale prefer the three-step
pattern: add nullable column -> backfill in batches -> SET NOT NULL.

Idempotent ALTER pattern (see [[feedback_l30_init_db_vs_alembic_new_table]]):
L30's init_db.py auto-creates tables from SQLAlchemy models at startup,
so by the time alembic runs the columns may already exist with their
defaults. Each statement uses IF NOT EXISTS so re-runs are safe.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "lesson_timestamps_001"
down_revision: Union[str, None] = "drop_survey_lesson_type_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns with NOT NULL DEFAULT now() so existing rows are
    # backfilled in a single statement on Postgres.
    op.execute(
        "ALTER TABLE lessons "
        "ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ "
        "NOT NULL DEFAULT now()"
    )
    op.execute(
        "ALTER TABLE lessons "
        "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ "
        "NOT NULL DEFAULT now()"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE lessons DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE lessons DROP COLUMN IF EXISTS created_at")
