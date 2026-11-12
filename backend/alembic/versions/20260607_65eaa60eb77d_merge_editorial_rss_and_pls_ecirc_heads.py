# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""merge editorial_rss and pls_ecirc heads

Revision ID: 65eaa60eb77d
Revises: editorial_rss_001, pls_ecirc_001
Create Date: 2026-06-07 20:01:30.125243+00:00

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
revision: str = '65eaa60eb77d'
down_revision: Union[str, None] = ('editorial_rss_001', 'pls_ecirc_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
