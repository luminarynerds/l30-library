# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Database initialization utilities for tests.

Provides functions to initialize test database with schema
via SQLAlchemy table creation from models.
"""

import asyncio
import os
import sys
from pathlib import Path
from sqlalchemy import text, ARRAY, JSON, LargeBinary, MetaData, Text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB, BYTEA, TSVECTOR

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://lsc:lsc_dev_pwd@localhost:5432/lsc_test"
)
BACKEND_PATH = Path(__file__).parent.parent


def _dedup_indexes(base) -> None:
    """Drop duplicate Index objects so SQLite create_all doesn't choke.

    Models may declare both ``index=True`` on a Column and an explicit
    ``Index()`` for the same column, or reuse index names across tables.
    Postgres tolerates the duplicates; SQLite raises ``OperationalError:
    index ... already exists``. Iterate all tables, keep the first
    occurrence of each index name, discard the rest.
    """
    seen_names: set = set()
    for table in base.metadata.tables.values():
        to_remove = []
        for idx in table.indexes:
            if idx.name in seen_names:
                to_remove.append(idx)
            else:
                seen_names.add(idx.name)
        for idx in to_remove:
            table.indexes.discard(idx)


def _drop_postgres_only_indexes(base) -> None:
    """Drop indexes that use Postgres-only features so SQLite can ``create_all``.

    Test-side only. An Index is treated as Postgres-only when it carries
    any non-None ``postgresql_*`` dialect kwarg (partial-index ``where``,
    ``using gin/hnsw``, custom ``ops``, etc.) -- those are the indexes whose
    DDL won't compile or won't execute under SQLite. Production schema is
    untouched; tests just lose the index, which is fine because the unique/
    partial behaviour is enforced by Postgres in real environments.
    """
    for table in base.metadata.tables.values():
        to_remove = []
        for idx in table.indexes:
            pg_kwargs = {
                k: v for k, v in idx.dialect_kwargs.items()
                if k.startswith("postgresql_") and v is not None
            }
            if pg_kwargs:
                to_remove.append(idx)
        for idx in to_remove:
            table.indexes.discard(idx)


def _swap_sqlite_unsupported_types(base) -> None:
    """Substitute Postgres-only column types with SQLite-compatible ones.

    Mutates ``base.metadata`` in place. Safe to call only when the test run
    targets SQLite -- the swap is one-way and would break production
    semantics if applied to the real Postgres engine.

    NEVER call this from an individual test module. The mutation is
    process-global and permanent: once it runs, every Postgres-bound test
    later in the same pytest invocation compiles ARRAY/JSONB binds as JSON
    and TSVECTOR as text, failing with DatatypeMismatchError. Three indie
    test modules did exactly that and turned the 2026-07-07 deploy-gate
    full-suite run into a ~1.6k-failure cascade. A test module that needs a
    private SQLite engine should create only its own portable tables via
    ``Base.metadata.create_all(conn, tables=[...])`` instead.

    Currently swaps:
      - JSONB  -> JSON
      - ARRAY  -> JSON      (array semantics lost; tests must not rely on them)
      - BYTEA  -> LargeBinary
      - TSVECTOR -> Text    (full-text search disabled under SQLite)

    Also rewrites ``server_default=text("'...'::jsonb")`` style literals to
    drop the ``::jsonb`` cast that SQLite's parser rejects.
    """
    import re

    cast_re = re.compile(r"::\s*(jsonb|json|tsvector|bytea)\b", re.IGNORECASE)

    for table in base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
            elif isinstance(column.type, ARRAY):
                column.type = JSON()
            elif isinstance(column.type, BYTEA):
                column.type = LargeBinary()
            elif isinstance(column.type, TSVECTOR):
                column.type = Text()

            # Strip Postgres-only type casts from server_default text clauses
            sd = column.server_default
            if sd is not None and hasattr(sd, "arg"):
                try:
                    src = str(sd.arg)
                except Exception:
                    continue
                if cast_re.search(src):
                    cleaned = cast_re.sub("", src)
                    column.server_default = text(cleaned)


def sqlite_compat_metadata_clone(base) -> MetaData:
    """Deep-copy ``base.metadata`` and make the COPY SQLite-compatible.

    For test modules that need a private SQLite engine with the full schema:
    create tables from the returned MetaData (``clone.create_all``) instead of
    calling the in-place helpers above on the live metadata. The ORM keeps
    compiling statements from the untouched live metadata, so Postgres-bound
    tests running later in the same process are unaffected (see the warning
    on ``_swap_sqlite_unsupported_types``).
    """
    from types import SimpleNamespace

    clone = MetaData()
    for table in base.metadata.tables.values():
        table.to_metadata(clone)
    shim = SimpleNamespace(metadata=clone)
    _dedup_indexes(shim)
    _drop_postgres_only_indexes(shim)
    _swap_sqlite_unsupported_types(shim)
    return clone


def _ensure_enum_types(base, engine) -> None:
    """Best-effort create every Enum type used by the models (Postgres, idempotent).

    ``create_all(checkfirst=True)`` skips ``create_type=False`` enums and never
    creates types for columns added to pre-existing tables. Pre-creating them lets
    the additive column reconcile add enum-typed columns. Fail-soft per type so one
    bad enum never aborts the run.
    """
    from sqlalchemy import Enum as SAEnum

    seen: set = set()
    for table in base.metadata.tables.values():
        for col in table.columns:
            ct = col.type
            if isinstance(ct, SAEnum) and ct.name and ct.name not in seen:
                seen.add(ct.name)
                try:
                    ct.create(engine, checkfirst=True)
                except Exception as e:  # noqa: BLE001 — best-effort per type
                    print(f"   ⚠️  enum {ct.name}: {e}")


def _ensure_enum_values(base, engine) -> None:
    """Heal drift between a long-lived test DB's native enum labels and the
    current Python StrEnum members (Postgres only, additive, idempotent).

    ``_ensure_enum_types`` only *creates* a type if it's entirely missing
    (``checkfirst=True``); it no-ops for a type that already exists, even if
    that existing type predates later ``ALTER TYPE ... ADD VALUE`` migrations
    or later members added straight to the Python enum. On a shared,
    long-lived ``l30_test`` database this leaves native enums (confirmed for
    ``notificationtype`` and ``importjobtype``) stuck with a stale label set
    from whenever the type was first created, silently breaking any test that
    inserts a currently-valid-in-Python value the DB type has never heard of
    (``InvalidTextRepresentationError``). ``alembic/versions/initial_schema.sql``
    -- a pg_dump of a real, fully-migrated database -- confirms the full
    label sets used here are the actual current production shape, not a
    hypothetical/new migration. Diff DB labels vs. Python enum members per
    type and ``ALTER TYPE ... ADD VALUE IF NOT EXISTS`` for the gap. Additive
    only (never removes a label); fail-soft per type/value.
    """
    from sqlalchemy import Enum as SAEnum

    # More than one *distinct* Python enum class can map to the same native
    # Postgres type name (e.g. NotificationType in app/models/notification.py
    # and the unrelated ShiftSwapNotificationType in app/models/shift_swap.py
    # both declare name="notificationtype") -- they genuinely share one
    # physical DB type, so "want" must be the union of every Python enum's
    # values across all columns using that type name, not just the first
    # column encountered.
    want_by_type: dict = {}
    for table in base.metadata.tables.values():
        for col in table.columns:
            ct = col.type
            if isinstance(ct, SAEnum) and ct.name:
                want_by_type.setdefault(ct.name, set()).update(ct.enums)

    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        for type_name, want in want_by_type.items():
            try:
                have = {
                    row[0]
                    for row in conn.execute(
                        text(
                            "SELECT e.enumlabel FROM pg_enum e "
                            "JOIN pg_type t ON e.enumtypid = t.oid "
                            "WHERE t.typname = :name"
                        ),
                        {"name": type_name},
                    )
                }
                if not have:
                    continue  # type doesn't exist yet -- _ensure_enum_types handles it
                missing = want - have
                for value in sorted(missing):
                    # ALTER TYPE ... ADD VALUE doesn't support bind params in
                    # all drivers; `value` comes only from our own trusted
                    # Python StrEnum definitions, never external input.
                    conn.execute(
                        text(f"ALTER TYPE \"{type_name}\" ADD VALUE IF NOT EXISTS '{value}'")
                    )
                if missing:
                    print(f"   + enum {type_name}: added {sorted(missing)}")
            except Exception as e:  # noqa: BLE001 -- best-effort per type
                print(f"   [warn] enum value reconcile {type_name}: {e}")


def _reconcile_missing_columns(base, engine) -> None:
    """Additive-only heal: ``ADD COLUMN IF NOT EXISTS`` for model columns missing
    from existing tables (Postgres). Never drops or alters existing columns.

    Concurrency-safe (IF NOT EXISTS is idempotent + lock-cheap) and fast (no-op
    when current). Each ALTER runs in its own autocommit statement so one failure
    can't poison the rest. Skips NOT NULL columns without a server default — they
    can't be added to a table that already has rows; those (and type changes /
    removals) need the full scripts/rebuild_test_db.py rebuild.
    """
    from sqlalchemy import text
    from sqlalchemy.schema import CreateColumn

    dialect = engine.dialect
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        have_by_table: dict = {}
        for tname, cname in conn.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema='public'"
            )
        ):
            have_by_table.setdefault(tname, set()).add(cname)

        added = 0
        for table in base.metadata.tables.values():
            have = have_by_table.get(table.name)
            if have is None:
                continue  # wholly-new table — create_all already handled it
            for col in table.columns:
                if col.name in have:
                    continue
                if not col.nullable and col.server_default is None:
                    print(f"   ⚠️  skip {table.name}.{col.name}: NOT NULL without server default")
                    continue
                try:
                    ddl = CreateColumn(col).compile(dialect=dialect)
                    conn.execute(
                        text(f'ALTER TABLE "{table.name}" ADD COLUMN IF NOT EXISTS {ddl}')
                    )
                    added += 1
                    print(f"   + added column {table.name}.{col.name}")
                except Exception as e:  # noqa: BLE001 — best-effort per column
                    print(f"   ⚠️  {table.name}.{col.name}: {e}")
        if added:
            print(f"✅ additive reconcile added {added} missing column(s)")


def _ensure_search_tsv_trigger(engine) -> None:
    """Recreate the catalog_items.search_tsv trigger that powers FTS.

    ``search_tsv`` is a plain nullable Column in the SQLAlchemy model (see
    app/models/catalog.py) -- it is populated by a Postgres trigger defined
    only in a migration (alembic/versions/20260510_schema_sync_007_restore_search_tsv.py),
    not by any ORM-level default/Computed(). ``create_all()`` therefore
    creates the column but never the trigger that fills it in, so every
    catalog_items row inserted through the test harness gets search_tsv=NULL
    and full-text search (websearch_to_tsquery/@@) silently matches nothing.
    Recreate the same function + trigger here (idempotent: CREATE OR REPLACE
    + DROP TRIGGER IF EXISTS) so tests can exercise real FTS behavior.
    """
    from sqlalchemy import text as _text

    with engine.begin() as conn:
        conn.execute(_text("""
            CREATE OR REPLACE FUNCTION catalog_items_search_tsv_update() RETURNS trigger AS $$
            BEGIN
              NEW.search_tsv :=
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.author, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.subjects, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'D');
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        conn.execute(_text(
            "DROP TRIGGER IF EXISTS catalog_items_search_tsv_trigger ON catalog_items"
        ))
        conn.execute(_text("""
            CREATE TRIGGER catalog_items_search_tsv_trigger
              BEFORE INSERT OR UPDATE OF title, author, subjects, description
              ON catalog_items
              FOR EACH ROW
              EXECUTE FUNCTION catalog_items_search_tsv_update()
        """))


async def create_tables_from_models(database_url: str = DATABASE_URL):
    """
    Create tables directly from SQLAlchemy models.

    For SQLite, creates tables using synchronous engine to bypass async type compilation issues.
    """
    import app.models  # noqa: F401
    from app.core.database import Base

    # For SQLite, swap Postgres-only column types and dedup indexes before
    # create_all (Postgres tolerates both; SQLite doesn't).
    if database_url.startswith("sqlite"):
        # Convert async URL to sync URL for type replacement
        sync_url = database_url.replace("sqlite+aiosqlite://", "sqlite:///")

        _swap_sqlite_unsupported_types(Base)
        _drop_postgres_only_indexes(Base)
        _dedup_indexes(Base)

        # Create tables using synchronous engine
        engine = None
        try:
            engine = create_engine(sync_url)
            # Drop all existing tables first for a clean start
            import sqlite3
            conn = sqlite3.connect(sync_url.replace("sqlite:///", ""))
            conn.execute("PRAGMA writable_schema = ON")
            # Get all table names and drop them
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables_to_drop = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence']
            for tname in tables_to_drop:
                conn.execute(f'DROP TABLE IF EXISTS "{tname}"')
            # Drop all indexes too
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes_to_drop = [row[0] for row in cursor.fetchall()]
            for iname in indexes_to_drop:
                try:
                    conn.execute(f'DROP INDEX IF EXISTS "{iname}"')
                except Exception:
                    pass
            conn.execute("PRAGMA writable_schema = OFF")
            conn.commit()
            conn.close()

            # Create all tables fresh
            Base.metadata.create_all(engine)
            print("✅ Tables created from SQLAlchemy models")
            return True
        except Exception as e:
            print(f"⚠️  Initial table creation failed: {e}")
            print("   Attempting to create only missing tables...")

            # If that fails due to index conflicts, try creating individual tables
            try:
                from sqlalchemy import inspect
                inspector = inspect(engine)
                existing_tables = set(inspector.get_table_names())

                # Create only missing tables, suppressing index conflicts
                failed_tables = []
                for table in Base.metadata.tables.values():
                    if table.name not in existing_tables:
                        try:
                            table.create(engine, checkfirst=True)
                        except Exception as te:
                            # Log but don't fail on individual table creation errors
                            if "already exists" not in str(te):
                                print(f"   ⚠️  Error creating table {table.name}: {te}")
                                failed_tables.append(table.name)

                if len(existing_tables) > 50:  # If most tables exist, consider it success
                    print("✅ Database already initialized with most tables")
                    return True
                elif len(failed_tables) == 0:
                    print("✅ Missing tables created from SQLAlchemy models")
                    return True
                else:
                    print(f"⚠️  Some tables failed to create: {failed_tables}")
                    return True  # Still return True as partial success
            except Exception as e2:
                print(f"❌ Critical error during table creation: {e2}")
                return False
            finally:
                try:
                    if engine:
                        engine.dispose()
                except Exception:
                    pass
    else:
        # For PostgreSQL, use SYNCHRONOUS engine to avoid AsyncPG prepared statement caching issues
        # Keep schema creation on the declared psycopg2 driver, matching
        # conftest's availability check even with SQLAlchemy 2.1 defaults.
        sync_url = database_url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)

        # Postgres tolerates duplicate index *definitions* across models but
        # `create_all` still emits two `CREATE INDEX` statements with the same
        # name, which trips `DuplicateTable`. Dedup at the metadata layer.
        _dedup_indexes(Base)

        engine = None
        try:
            engine = create_engine(sync_url)

            # Models using create_type=False expect their PostgreSQL enums to
            # exist before the first table is created, even on a fresh CI DB.
            _ensure_enum_types(Base, engine)
            _ensure_enum_values(Base, engine)

            # Create only missing tables (never drop existing data)
            with engine.begin() as conn:
                Base.metadata.create_all(conn, checkfirst=True)

            print("✅ Tables created from SQLAlchemy models (using synchronous driver)")

            # create_all(checkfirst) only creates *missing tables* — it never ALTERs
            # existing ones, so a long-lived shared test DB drifts (newly-added
            # columns/enums on pre-existing tables never land). Additively heal that
            # drift: never drops, IF-NOT-EXISTS so it's idempotent and concurrency-
            # safe, fail-soft per object. Type changes / column removals still need
            # the manual scripts/rebuild_test_db.py full rebuild.
            try:
                _reconcile_missing_columns(Base, engine)
            except Exception as e:  # noqa: BLE001 — heal is best-effort, never fatal
                print(f"⚠️  additive schema reconcile skipped: {e}")

            try:
                _ensure_search_tsv_trigger(engine)
            except Exception as e:  # noqa: BLE001 — best-effort, never fatal
                print(f"⚠️  search_tsv trigger reconcile skipped: {e}")

            return True
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if engine:
                engine.dispose()


async def initialize_test_database(
    database_url: str = DATABASE_URL,
    use_alembic: bool = False,
) -> bool:
    """
    Initialize test database schema.

    Args:
        database_url: Database connection URL
        use_alembic: Deprecated, ignored. Kept for call-site compatibility.

    Returns:
        True if successful, False otherwise
    """
    print(f"Initializing test database: {database_url.split('@')[-1] if '@' in database_url else database_url.split('/')[-1]}")
    return await create_tables_from_models(database_url)


async def drop_all_tables(database_url: str = DATABASE_URL):
    """
    Drop all tables from the test database.

    Warning: This is destructive and should only be used in tests.
    """
    import app.models  # noqa: F401
    from app.core.database import Base

    if database_url.startswith("sqlite"):
        # For SQLite, use sync engine
        sync_url = database_url.replace("sqlite+aiosqlite://", "sqlite:///")
        engine = create_engine(sync_url)
        try:
            Base.metadata.drop_all(engine)
            print("✅ All tables dropped")
            return True
        except Exception as e:
            print(f"❌ Error dropping tables: {e}")
            return False
        finally:
            engine.dispose()
    else:
        # For PostgreSQL, use async engine
        engine = create_async_engine(database_url)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            print("✅ All tables dropped")
            return True
        except Exception as e:
            print(f"❌ Error dropping tables: {e}")
            return False
        finally:
            await engine.dispose()


async def reset_test_database(database_url: str = DATABASE_URL):
    """
    Reset test database: drop all tables and recreate schema.

    Useful for test isolation.
    """
    await drop_all_tables(database_url)
    return await initialize_test_database(database_url)


async def check_database_connectivity(database_url: str = DATABASE_URL) -> bool:
    """Check if database is accessible."""
    try:
        if database_url.startswith("sqlite"):
            # For SQLite, just check if we can create a connection
            engine = create_engine(database_url.replace("sqlite+aiosqlite://", "sqlite:///"))
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            print("✅ Database is accessible")
            return True
        else:
            # For PostgreSQL, use async
            engine = create_async_engine(database_url)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            print("✅ Database is accessible")
            return True
    except Exception as e:
        print(f"❌ Cannot connect to database: {e}")
        return False


if __name__ == "__main__":
    # Allow running as script for manual setup
    action = sys.argv[1] if len(sys.argv) > 1 else "init"

    if action == "init":
        asyncio.run(initialize_test_database())
    elif action == "reset":
        asyncio.run(reset_test_database())
    elif action == "drop":
        asyncio.run(drop_all_tables())
    elif action == "check":
        asyncio.run(check_database_connectivity())
    else:
        print(f"Unknown action: {action}")
        print("Available actions: init, reset, drop, check")
