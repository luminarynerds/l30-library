"""unite heads pre book-club-archive

Revision ID: bc_archive_merge_001
Revises: orgfeat_mergepoint_20260519, cg_enroll_001, course_lifecycle_001
Create Date: 2026-05-19 12:32:11.281213+00:00

"""
# NOTE: When adding new tables, use
#   op.execute("CREATE TABLE IF NOT EXISTS ...")
# instead of op.create_table(). L30's init_db.py auto-creates tables from
# SQLAlchemy models at backend startup, so by the time alembic runs the
# table may already exist and op.create_table() raises DuplicateTableError.
#
# The same trap applies to renames: op.rename_table(old, new) collides with
# init_db's pre-created destination table. Use raw SQL instead:
#   op.execute('DROP TABLE IF EXISTS "<new>"')
#   op.execute('ALTER TABLE "<old>" RENAME TO "<new>"')
#
# See backend/scripts/check_alembic_idempotent.py and
# [[feedback_l30_init_db_vs_alembic_new_table]].
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc_archive_merge_001'
down_revision: Union[str, None] = ('orgfeat_mergepoint_20260519', 'cg_enroll_001', 'course_lifecycle_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
