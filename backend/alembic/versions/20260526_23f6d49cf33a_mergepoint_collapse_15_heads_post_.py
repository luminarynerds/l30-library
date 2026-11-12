"""mergepoint: collapse 15 heads post parent-onboarding wave

Revision ID: 23f6d49cf33a
Revises: board_retention_002, backfill_course_stage_transitions_001, childcare_checkin_001, home_visit_day_plan_001, home_visit_mutations_001, parent_resource_verify_001, po_session_handouts_001, pr_translations_001, blog_author_fk_001, blog_post_bookmarks_001, blog_soft_delete_001, cg_lifecycle_001, family_snapshot_001, fix_recurring_program_dow_001, parent_onboarding_export_log_001
Create Date: 2026-05-26 10:13:29.232544+00:00

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
revision: str = '23f6d49cf33a'
down_revision: Union[str, None] = ('board_retention_002', 'backfill_course_stage_transitions_001', 'childcare_checkin_001', 'home_visit_day_plan_001', 'home_visit_mutations_001', 'parent_resource_verify_001', 'po_session_handouts_001', 'pr_translations_001', 'blog_author_fk_001', 'blog_post_bookmarks_001', 'blog_soft_delete_001', 'cg_lifecycle_001', 'family_snapshot_001', 'fix_recurring_program_dow_001', 'parent_onboarding_export_log_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
