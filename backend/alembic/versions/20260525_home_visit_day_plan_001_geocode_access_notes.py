"""home-visit day-plan tables + columns + feature flag

Revision ID: home_visit_day_plan_001
Revises: patron_category_001
Create Date: 2026-05-25 22:00:00.000000+00:00

Adds infrastructure for the staff "Today's route" view at
/staff/parent-onboarding/home-visits/today:

1. ``home_visit_geocode_cache`` -- address-hash keyed cache of lat/lng so we
   never ask Nominatim twice for the same address. Lookup is by sha256
   hash, not raw text, so capitalization/whitespace variants collapse.
   ``provider='manual'`` entries are staff overrides and never auto-expire;
   ``'nominatim'`` entries get re-geocoded lazily after 90 days.

2. ``home_visit_access_notes`` -- per-patron residence notes (steps, dog,
   primary language, parking, buzzer). Keyed on ``patron_id`` (not
   ``visit_id``) because the notes describe the *home*, not the visit:
   three visits to the same family in a month should share one set of
   accessibility notes. UNIQUE on ``patron_id`` is the upsert key.

3. New nullable columns on ``parent_home_visits``:
     - ``geocoded_lat``        Numeric(9,6)  -- copied from cache on read
     - ``geocoded_lng``        Numeric(9,6)  -- copied from cache on read
     - ``day_plan_sort_index`` Integer       -- NULL = auto-by-scheduled_time

4. ``home_visit_day_plan_enabled`` boolean on ``organization_features``
   (default false -- opt-in once the library validates a real day plan).

down_revision = ``patron_category_001`` (chosen from 8 current heads as the
most recent main commit on 2026-05-25). A follow-up mergepoint will unify
this back into the rest of the branch graph; see ``feedback_l30_alembic_multi_head_deploy``.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "home_visit_day_plan_001"
down_revision: Union[str, None] = "patron_category_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Geocode cache. address_hash is the PK so reads are an index
    # lookup, not a sequence scan over address text. Raw text is kept
    # only for staff-debug ("why did this address geocode to X?").
    # ------------------------------------------------------------------
    op.create_table(
        "home_visit_geocode_cache",
        sa.Column("address_hash", sa.CHAR(length=64), primary_key=True),
        sa.Column("address_raw", sa.Text(), nullable=False),
        sa.Column("lat", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("lng", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column(
            "geocoded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("provider", sa.String(length=20), nullable=False),
    )
    op.create_check_constraint(
        "ck_home_visit_geocode_cache_provider",
        "home_visit_geocode_cache",
        "provider IN ('nominatim', 'manual')",
    )

    # ------------------------------------------------------------------
    # 2. Per-patron residence access notes.
    # ------------------------------------------------------------------
    op.create_table(
        "home_visit_access_notes",
        # Integer rather than BigInteger so SQLite (used by the test
        # conftest) autoincrements; PG promotes to BIGSERIAL ergonomically
        # via ALTER if scale ever demands it. Residence-notes scale is
        # bounded by patron count so 32-bit is comfortable.
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("patron_id", sa.Integer(), nullable=False),
        sa.Column("has_steps", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("has_elevator", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("multi_floor", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dog_on_premises", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dog_safety_note", sa.Text(), nullable=True),
        sa.Column("primary_language", sa.String(length=20), nullable=True),
        sa.Column("needs_interpreter", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("buzzer_or_intercom", sa.Text(), nullable=True),
        sa.Column("parking_notes", sa.Text(), nullable=True),
        sa.Column("other_notes", sa.Text(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["patron_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("patron_id", name="uq_home_visit_access_notes_patron_id"),
    )

    # ------------------------------------------------------------------
    # 3. New columns on parent_home_visits.
    # ------------------------------------------------------------------
    op.add_column(
        "parent_home_visits",
        sa.Column("geocoded_lat", sa.Numeric(precision=9, scale=6), nullable=True),
    )
    op.add_column(
        "parent_home_visits",
        sa.Column("geocoded_lng", sa.Numeric(precision=9, scale=6), nullable=True),
    )
    op.add_column(
        "parent_home_visits",
        sa.Column("day_plan_sort_index", sa.Integer(), nullable=True),
    )

    # ------------------------------------------------------------------
    # 4. Feature flag column on organization_features.
    # ------------------------------------------------------------------
    op.add_column(
        "organization_features",
        sa.Column(
            "home_visit_day_plan_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("organization_features", "home_visit_day_plan_enabled")
    op.drop_column("parent_home_visits", "day_plan_sort_index")
    op.drop_column("parent_home_visits", "geocoded_lng")
    op.drop_column("parent_home_visits", "geocoded_lat")
    op.drop_table("home_visit_access_notes")
    op.drop_constraint(
        "ck_home_visit_geocode_cache_provider",
        "home_visit_geocode_cache",
        type_="check",
    )
    op.drop_table("home_visit_geocode_cache")
