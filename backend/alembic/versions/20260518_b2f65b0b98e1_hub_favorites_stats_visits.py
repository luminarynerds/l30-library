"""hub_favorites_stats_visits

Revision ID: b2f65b0b98e1
Revises: eb50ff2536d6
Create Date: 2026-05-18 16:11:43.229945+00:00

Creates two user-scoped tables for the hub infrastructure wave:

* ``user_hub_favorites`` -- replaces localStorage-backed favorites in hub
  pages (ReportHubPage etc.) so favorites sync across devices and survive
  cache wipes. Unique on (user_id, hub_slug, item_path).

* ``user_hub_visits`` -- append-only visit log per user/hub/item. Foundation
  for usage-aware shortcuts; aggregation comes in a later wave.

L30 init_db.py auto-creates tables from SQLAlchemy models at backend
startup, so we wrap CREATE TABLE in IF NOT EXISTS to stay idempotent
across rebuilds (see backend/scripts/check_alembic_idempotent.py and
[[feedback_l30_init_db_vs_alembic_new_table]]).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2f65b0b98e1"
down_revision: Union[str, None] = "eb50ff2536d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # user_hub_favorites -- server-side replacement for localStorage favorites
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_hub_favorites (
            id UUID PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            hub_slug VARCHAR(64) NOT NULL,
            item_path VARCHAR(512) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_user_hub_favorite UNIQUE (user_id, hub_slug, item_path)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_hub_favorites_user_id "
        "ON user_hub_favorites (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_hub_favorites_hub_slug "
        "ON user_hub_favorites (hub_slug)"
    )

    # user_hub_visits -- append-only visit log (no dedup, cheap inserts)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_hub_visits (
            id UUID PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            hub_slug VARCHAR(64) NOT NULL,
            item_path VARCHAR(512) NOT NULL,
            visited_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_hub_visits_user_id "
        "ON user_hub_visits (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_hub_visits_hub_slug "
        "ON user_hub_visits (hub_slug)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_hub_visits_item_path "
        "ON user_hub_visits (item_path)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_hub_visits_visited_at "
        "ON user_hub_visits (visited_at)"
    )
    # Composite index for the wave 3 \"recent visits for user\" lookup.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_hub_visits_user_visited "
        "ON user_hub_visits (user_id, visited_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_hub_visits")
    op.execute("DROP TABLE IF EXISTS user_hub_favorites")
