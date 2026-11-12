# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add family_card_enabled flag

Patron Account family tab is gated on this flag.
Defaults true so existing deployments retain the current behavior.

L30 init_db.py auto-creates tables from SQLAlchemy models at backend
startup, so the upgrade uses ADD COLUMN IF NOT EXISTS to stay idempotent
across rebuilds (see [[feedback_l30_init_db_vs_alembic_new_table]]).
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "family_card_flag_001"
down_revision: Union[str, None] = "mergepoint_20260520"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE organization_features "
        "ADD COLUMN IF NOT EXISTS family_card_enabled BOOLEAN NOT NULL DEFAULT TRUE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE organization_features DROP COLUMN IF EXISTS family_card_enabled")
