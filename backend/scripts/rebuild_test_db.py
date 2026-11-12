# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Rebuild a TEST Postgres database to match the current SQLAlchemy models.

Why this exists: the pytest Postgres path (tests/database_setup.py) builds schema
with ``create_all(checkfirst=True)`` — it only creates *missing tables* and never
ALTERs existing ones, so a long-lived test DB drifts (newly-added columns, enum
types, and tables never land). The SQLite path drops-and-recreates each run, so it
stays fresh; the Postgres path accumulates and goes stale. This script brings a
test DB back to current by dropping all tables + user enum types (extensions are
preserved), recreating every enum type and table from the live models, and
stamping alembic at head. The result is model-derived (≈ current models), not a
migration-faithful replica — which is exactly what the pytest harness itself
builds, so tests behave identically.

SAFETY: refuses unless the target database name contains "test" and is not
l30_library, and the URL does not point at l30_library.

Usage:
  DATABASE_URL=postgresql+asyncpg://USER:PW@127.0.0.1:5434/l30_test \
  PYTHONPATH=<backend> SECRET_KEY=x PII_ENCRYPTION_ENABLED=false \
  python scripts/rebuild_test_db.py
"""
import os
import sys

from sqlalchemy import Enum as SAEnum
from sqlalchemy import create_engine, text

_LIST_TABLES = "SELECT tablename FROM pg_tables WHERE schemaname='public'"
_LIST_ENUMS = (
    "SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace "
    "WHERE n.nspname='public' AND t.typtype='e'"
)


def main() -> None:
    url = os.environ.get("DATABASE_URL", "")
    sync_url = url.replace("postgresql+asyncpg://", "postgresql://").replace("+asyncpg", "")
    if not sync_url.startswith("postgresql://"):
        sys.exit(f"REFUSING: not a postgres URL: {url!r}")
    if "/l30_library" in sync_url:
        sys.exit("REFUSING: URL points at l30_library (production)")

    import app.models  # noqa: F401  (populate Base.metadata)
    from app.core.database import Base
    from tests.database_setup import _dedup_indexes

    engine = create_engine(sync_url)
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        dbname = conn.execute(text("select current_database()")).scalar()
        # HARD GUARD — must be a test database, never production.
        if "test" not in (dbname or "") or dbname == "l30_library":
            sys.exit(f"REFUSING: target db {dbname!r} is not a test database")
        print(f"[rebuild] target database OK: {dbname}")

        # Drop each object in its OWN autocommit statement. A single DO-block
        # (one transaction) dropping ~1100 tables CASCADE exhausts
        # max_locks_per_transaction; per-statement drops don't accumulate locks.
        tables = list(conn.execute(text(_LIST_TABLES)).scalars())
        for name in tables:
            conn.execute(text(f'DROP TABLE IF EXISTS public."{name}" CASCADE'))
        enums = list(conn.execute(text(_LIST_ENUMS)).scalars())
        for name in enums:
            conn.execute(text(f'DROP TYPE IF EXISTS public."{name}" CASCADE'))
        print(
            f"[rebuild] dropped {len(tables)} tables + {len(enums)} enum types "
            "(extensions preserved)"
        )

    # Postgres tolerates duplicate index definitions but create_all emits two
    # CREATE INDEX with the same name -> DuplicateTable. Dedup at metadata layer.
    _dedup_indexes(Base)

    # Recreate every enum type first; create_all skips create_type=False enums.
    created: set = set()
    for table in Base.metadata.tables.values():
        for col in table.columns:
            ct = col.type
            if isinstance(ct, SAEnum) and ct.name and ct.name not in created:
                ct.create(engine, checkfirst=True)
                created.add(ct.name)
    print(f"[rebuild] created {len(created)} enum types")

    Base.metadata.create_all(engine, checkfirst=True)
    print("[rebuild] create_all complete")
    engine.dispose()

    # Stamp alembic at head so a later `alembic upgrade head` is a no-op rather
    # than a from-base collision. Convenience only — schema is model-derived.
    try:
        from alembic import command
        from alembic.config import Config

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg = Config(os.path.join(backend_dir, "alembic.ini"))
        command.stamp(cfg, "head")
        print("[rebuild] alembic stamped head")
    except Exception as e:  # noqa: BLE001
        print(f"[rebuild] WARNING: alembic stamp head failed ({e}); schema is built, stamp manually")

    print("[rebuild] DONE")


if __name__ == "__main__":
    main()
