# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add structured sensory fields to events

Events review enhancement #2: lighting, noise level, crowd size, and
quiet-space availability so sensory-sensitive patrons can pre-assess an
event without having to email staff. All columns are nullable / defaulted
so existing rows are unaffected.

L30 init_db.py auto-creates tables from SQLAlchemy models at backend
startup, so the upgrade uses ADD COLUMN IF NOT EXISTS to stay idempotent
across rebuilds (see [[feedback_l30_init_db_vs_alembic_new_table]]).
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "events_sensory_fields_001"
down_revision: Union[str, None] = "family_card_flag_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE events "
        "ADD COLUMN IF NOT EXISTS lighting VARCHAR(20), "
        "ADD COLUMN IF NOT EXISTS noise_level VARCHAR(20), "
        "ADD COLUMN IF NOT EXISTS crowd_size VARCHAR(20), "
        "ADD COLUMN IF NOT EXISTS quiet_space_available BOOLEAN NOT NULL DEFAULT FALSE"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE events "
        "DROP COLUMN IF EXISTS lighting, "
        "DROP COLUMN IF EXISTS noise_level, "
        "DROP COLUMN IF EXISTS crowd_size, "
        "DROP COLUMN IF EXISTS quiet_space_available"
    )
