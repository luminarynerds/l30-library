"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

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
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
