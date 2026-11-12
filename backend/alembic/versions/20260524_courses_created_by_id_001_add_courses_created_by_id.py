"""add courses.created_by_id

Revision ID: courses_created_by_id_001
Revises: d530b5a403bd
Create Date: 2026-05-24 00:00:00.000000+00:00

Wave 1 of the L30 course-authoring friction strip plan. Adds a nullable
FK ``courses.created_by_id`` -> ``users.id`` (ON DELETE SET NULL) so the
upcoming sweep emails (W1-B) know whom to notify and the import endpoint
(W1-D) can carry creator attribution forward.

Historical courses (12 rows at time of writing) stay NULL — no backfill
is possible without provenance data.

Idempotent ALTER pattern (see [[feedback_l30_init_db_vs_alembic_new_table]]):
L30's init_db.py auto-creates tables from SQLAlchemy models at startup,
so by the time alembic runs the column may already exist with the inline
FK. Each statement uses IF NOT EXISTS so re-runs are safe.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "courses_created_by_id_001"
down_revision: Union[str, None] = "d530b5a403bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ADD COLUMN IF NOT EXISTS with inline REFERENCES creates an unnamed FK
    # if the column is being added now; if init_db.py already created the
    # column from the model, the statement is a no-op (column + FK already
    # present). Postgres ≥ 9.6 supports IF NOT EXISTS on ADD COLUMN.
    op.execute(
        "ALTER TABLE courses "
        "ADD COLUMN IF NOT EXISTS created_by_id INTEGER "
        "REFERENCES users(id) ON DELETE SET NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_courses_created_by_id "
        "ON courses (created_by_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_courses_created_by_id")
    op.execute("ALTER TABLE courses DROP COLUMN IF EXISTS created_by_id")
