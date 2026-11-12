# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create circulation_policy matrix table + bookbinding enum + catalog_items.binding.

Revision ID: circulation_policy_001
Revises: for_teachers_001
Create Date: 2026-05-14

Per-format / per-audience / per-binding / per-collection circulation rules.
Sparse matrix: NULL columns mean "fall through to next level."

Idempotency contract (every op is safe to re-run):
- enum CREATE: checkfirst=True via SQLAlchemy
- table CREATE: raw SQL with IF NOT EXISTS (alembic's op.create_table cannot
  emit this, but the canonical schema source here is init_db.py via ORM
  metadata.create_all; this migration's role is to add the bits ORM can't
  express -- indexes with predicates, ALTER TABLE on existing tables, seeds)
- ADD COLUMN: IF NOT EXISTS
- CREATE INDEX: IF NOT EXISTS
- INSERT seeds: WHERE NOT EXISTS guard

The uq_circulation_policy_scope index uses NULLS NOT DISTINCT (Postgres 15+)
so NULL slots collapse cleanly without the IMMUTABLE-cast trap of
COALESCE(role::text, '').

Postgres cannot drop enum values, so downgrade leaves bookbinding type behind
and only reverses the schema + seeds.
"""
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "circulation_policy_001"
down_revision = "for_teachers_001"
branch_labels = None
depends_on = None


BOOK_BINDINGS = (
    "hardback",
    "paperback",
    "mass_market",
    "board_book",
    "spiral",
    "library_binding",
    "other",
)

# Mirrors app.models.catalog.ItemType. Listed explicitly so a future enum
# addition doesn't silently change the seed set without touching this migration.
ITEM_TYPES = (
    "book",
    "audiobook",
    "ebook",
    "dvd",
    "bluray",
    "cd",
    "vinyl",
    "magazine",
    "game",
    "equipment",
    "kit",
    "tool",
    "other",
)

# Differentiated starter policies seeded per library_system. Grouped by tier so
# a fresh install ships with meaningful circulation rules (and a working example
# of fine collection) instead of one identical clone per item_type. NULL columns
# (max_fine, grace, hold pickup, fine_free) fall through to system_settings.
# Item types not listed here (e.g. "other") get no row and fall through entirely.
# Tuple shape: (item_type, loan_period_days, max_renewals, overdue_fine_per_day)
STARTER_POLICIES = (
    ("book", 21, 2, "0.25"),
    ("audiobook", 21, 2, "0.25"),
    ("ebook", 21, 2, "0.25"),
    ("magazine", 14, 1, "0.10"),
    ("cd", 14, 1, "0.25"),
    ("vinyl", 14, 1, "0.25"),
    ("dvd", 7, 1, "1.00"),
    ("bluray", 7, 1, "1.00"),
    ("game", 7, 1, "1.00"),
    ("equipment", 7, 0, "1.00"),
    ("tool", 7, 0, "1.00"),
    ("kit", 7, 0, "1.00"),
)


def upgrade():
    bind = op.get_bind()

    # 1. bookbinding enum (idempotent via checkfirst).
    postgresql.ENUM(*BOOK_BINDINGS, name="bookbinding").create(bind, checkfirst=True)

    # 2. catalog_items.binding column + partial index.
    op.execute(
        "ALTER TABLE catalog_items ADD COLUMN IF NOT EXISTS binding bookbinding"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_catalog_items_binding "
        "ON catalog_items (binding) WHERE binding IS NOT NULL"
    )

    # 3. circulation_policy table. ORM's init_db.py may have created it
    #    already on container startup, so IF NOT EXISTS is required.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS circulation_policy (
            id                    SERIAL PRIMARY KEY,
            library_system_id     INTEGER NOT NULL REFERENCES library_systems(id) ON DELETE CASCADE,
            role                  userrole,
            item_type             itemtype,
            binding               bookbinding,
            collection_id         INTEGER REFERENCES collection(id) ON DELETE CASCADE,
            loan_period_days      INTEGER,
            max_renewals          INTEGER,
            overdue_fine_per_day  NUMERIC(10, 2),
            max_fine              NUMERIC(10, 2),
            grace_period_days     INTEGER,
            hold_pickup_days      INTEGER,
            fine_free             BOOLEAN,
            active                BOOLEAN NOT NULL DEFAULT TRUE,
            notes                 TEXT,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    # 4. Unique scope index. NULLS NOT DISTINCT (PG15+) collapses NULL slots
    #    without the function-IMMUTABLE trap that bit COALESCE(role::text, '').
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_circulation_policy_scope "
        "ON circulation_policy "
        "(library_system_id, role, item_type, binding, collection_id) "
        "NULLS NOT DISTINCT"
    )

    # 5. Resolver hot-path partial index.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_circ_policy_resolver "
        "ON circulation_policy "
        "(library_system_id, item_type, role, binding, collection_id) "
        "WHERE active = TRUE"
    )

    # 6. Seed differentiated format-only starter policies per library_system.
    #    Grouped tiers (see STARTER_POLICIES), not one clone per item_type.
    #    NULL fields (max_fine, grace, hold pickup, fine_free) fall through to
    #    system_settings. WHERE NOT EXISTS guards re-runs.
    starter_values = ", ".join(
        f"('{it}', {loan}, {renew}, {fine})"
        for it, loan, renew, fine in STARTER_POLICIES
    )
    seed_sql = """
        INSERT INTO circulation_policy (
            library_system_id, role, item_type, binding, collection_id,
            loan_period_days, max_renewals, overdue_fine_per_day,
            active, notes
        )
        SELECT
            ss.library_system_id,
            NULL::userrole,
            v.item_type::itemtype,
            NULL::bookbinding,
            NULL::integer,
            v.loan_period_days,
            v.max_renewals,
            v.overdue_fine_per_day,
            TRUE,
            'Starter policy (differentiated defaults)'
        FROM system_settings ss
        CROSS JOIN (VALUES {starter_values})
            AS v(item_type, loan_period_days, max_renewals, overdue_fine_per_day)
        WHERE NOT EXISTS (
            SELECT 1 FROM circulation_policy cp
            WHERE cp.library_system_id = ss.library_system_id
              AND cp.role IS NULL
              AND cp.item_type = v.item_type::itemtype
              AND cp.binding IS NULL
              AND cp.collection_id IS NULL
        )
    """.format(starter_values=starter_values)
    op.execute(seed_sql)

    # 7. Backfill fine_free_juvenile -> (role='child', fine_free=TRUE) row.
    op.execute(
        """
        INSERT INTO circulation_policy (
            library_system_id, role, item_type, binding, collection_id,
            fine_free, active, notes
        )
        SELECT
            ss.library_system_id,
            'child'::userrole,
            NULL::itemtype,
            NULL::bookbinding,
            NULL::integer,
            TRUE,
            TRUE,
            'Backfilled from system_settings.fine_free_juvenile'
        FROM system_settings ss
        WHERE ss.fine_free_juvenile = TRUE
          AND NOT EXISTS (
            SELECT 1 FROM circulation_policy cp
            WHERE cp.library_system_id = ss.library_system_id
              AND cp.role = 'child'::userrole
              AND cp.item_type IS NULL
              AND cp.binding IS NULL
              AND cp.collection_id IS NULL
          )
        """
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_circ_policy_resolver")
    op.execute("DROP INDEX IF EXISTS uq_circulation_policy_scope")
    op.execute("DROP TABLE IF EXISTS circulation_policy")
    op.execute("DROP INDEX IF EXISTS ix_catalog_items_binding")
    op.execute("ALTER TABLE catalog_items DROP COLUMN IF EXISTS binding")
    op.execute("DROP TYPE IF EXISTS bookbinding")
