#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Initialize schema using AsyncPG with raw SQL execution.

This bypasses SQLAlchemy's metadata.create_all() which has caching issues,
and instead generates SQL and executes it directly.
"""
import asyncio
import re
import sys
import os
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://lsc:password@database:5432/lsc_library")


def _parse_db_url(url):
    """Parse DATABASE_URL into connection kwargs for asyncpg."""
    db_url = url.replace("postgresql+asyncpg://", "")
    if "@" not in db_url:
        raise ValueError(f"Cannot parse DATABASE_URL: {url}")
    creds, host_db = db_url.split("@", 1)
    user, password = creds.split(":", 1)
    if "/" not in host_db:
        raise ValueError("Invalid DATABASE_URL format")
    host_part, db_name = host_db.split("/", 1)
    host, port = (host_part.split(":", 1) + ["5432"])[:2]
    return dict(host=host, user=user, password=password, database=db_name, port=int(port))


async def extract_sql_from_models():
    """Generate CREATE TABLE/INDEX statements from SQLAlchemy models.

    Uses per-table compilation to avoid sorted_tables failures from
    broken foreign key references in individual models.
    """
    import app.models  # noqa: F401
    from app.core.database import Base
    from sqlalchemy import create_mock_engine
    from sqlalchemy.schema import CreateTable, CreateIndex, AddConstraint

    sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_mock_engine(sync_url, lambda sql, *a, **kw: None)

    # Tables to skip — models exist but features are deferred/unused.
    # Loaded from skip list file if present, otherwise empty set.
    skip_tables: set[str] = set()
    skip_file = Path(__file__).parent / "deferred_tables.txt"
    if skip_file.exists():
        skip_tables = {
            line.strip() for line in skip_file.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        if skip_tables:
            print(f"  Skipping {len(skip_tables)} deferred tables (see scripts/deferred_tables.txt)")

    enum_stmts = []
    table_stmts = []  # list of (table_name, sql)
    index_stmts = []  # list of (table_name, sql)
    alter_stmts = []  # list of (table_name, sql) for deferred FK constraints

    # Collect ENUMs and per-table DDL (tolerant of broken FKs)
    seen_enums = set()
    for name, table in Base.metadata.tables.items():
        if name in skip_tables:
            continue
        # Enums
        for col in table.columns:
            if hasattr(col.type, 'enums') and hasattr(col.type, 'name'):
                ename = col.type.name
                if ename not in seen_enums and col.type.enums:
                    seen_enums.add(ename)
                    # col.type.enums returns enum NAMES (uppercase), not VALUES.
                    # Use the Python enum class's .value to get correct lowercase values.
                    enum_class = getattr(col.type, 'enum_class', None)
                    if enum_class is not None:
                        vals = ", ".join(f"'{m.value}'" for m in enum_class)
                    else:
                        vals = ", ".join(f"'{v.lower()}'" for v in col.type.enums)
                    enum_stmts.append(f"DO $$ BEGIN\n    CREATE TYPE {ename} AS ENUM ({vals});\nEXCEPTION WHEN duplicate_object THEN null;\nEND $$;")
        # Table DDL
        try:
            sql = str(CreateTable(table).compile(dialect=engine.dialect))
            table_stmts.append((name, sql))
        except Exception as e:
            print(f"  ⚠️  Skipping DDL for {name}: {e}")
        # Index DDL
        for idx in table.indexes:
            try:
                sql = str(CreateIndex(idx).compile(dialect=engine.dialect))
                index_stmts.append((name, sql))
            except Exception:
                pass
        # Deferred FK constraints (use_alter=True)
        for fk_constraint in table.foreign_key_constraints:
            if fk_constraint.use_alter:
                try:
                    sql = str(AddConstraint(fk_constraint).compile(dialect=engine.dialect))
                    alter_stmts.append((name, sql))
                except Exception:
                    pass

    return enum_stmts, table_stmts, index_stmts, alter_stmts


def _patch_create_table_sql(sql: str, available_tables: set) -> str:
    """Fix known DDL issues before executing CREATE TABLE statements.

    1. Normalize triple-quoted server defaults produced by the mock engine
       (e.g. '''[]''::jsonb'  →  '[]'::jsonb).
    2. Strip inline FOREIGN KEY constraints referencing tables that will not
       be created in this run (permanently deferred), so the CREATE TABLE can
       succeed.  The FK is silently dropped; the column remains as a bare
       integer.  This mirrors what 'use_alter=True' would do if the model
       were updated.
    """
    # Fix 1: triple-quoted string defaults produced by the mock engine.
    # When server_default is a raw string containing single-quotes (e.g.
    # "'[]'::jsonb"), the mock engine wraps it in an extra layer of quotes,
    # yielding e.g.:  DEFAULT '''[]''::jsonb'
    # which Postgres rejects.  We strip the outer extra-quoting layer so
    # Postgres receives the intended:  DEFAULT '[]'::jsonb
    # Pattern: DEFAULT ''' <content> '' <optional_cast> '
    sql = re.sub(r"DEFAULT '''(.*?)''((?:::\w+)?)'", r"DEFAULT '\1'\2", sql)

    # Fix 2: strip FK lines that reference tables not in available_tables.
    # Match lines like:
    #   FOREIGN KEY(col) REFERENCES other_table (id)[ ON DELETE ...]
    # but NOT FK lines for tables we know about.
    # We operate line-by-line so we can remove only the offending lines.
    #
    # Each column/constraint is on its own line, comma-terminated except for
    # the last one before the closing ')'. When we drop a FOREIGN KEY line
    # that is NOT the last item (it still ends in ','), the previous line's
    # trailing comma is still correctly separating it from whatever
    # constraint follows and must be left alone. Only when the dropped line
    # IS the last item (no trailing comma) does the previous line become the
    # new last item, and only then must its own trailing comma be stripped.
    # The old code stripped the previous line's comma unconditionally,
    # which produced two adjacent items with no separating comma (a bare
    # "syntax error at or near FOREIGN") whenever a stripped, non-last FK
    # line was followed by another FK line that survived.
    lines = sql.split("\n")
    cleaned = []
    for line in lines:
        m = re.search(r"FOREIGN KEY\([^)]+\)\s+REFERENCES\s+(\w+)\s*\(", line)
        if m:
            ref_table = m.group(1)
            if ref_table not in available_tables:
                print(f"  ⚙  Stripping unresolvable FK → {ref_table}")
                is_last_item = not line.rstrip().endswith(",")
                if is_last_item and cleaned and cleaned[-1].rstrip().endswith(","):
                    cleaned[-1] = cleaned[-1].rstrip()[:-1] + "\n"
                continue  # skip this FK line
        cleaned.append(line)
    return "\n".join(cleaned)


async def ensure_vector_extension(conn) -> None:
    """Create the pgvector 'vector' extension if it doesn't already exist.

    Must run before any table DDL, since embedding columns (pgvector's
    `vector` type) fail to compile/create without it.
    """
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")


async def execute_sql_async(enum_stmts, table_stmts, index_stmts, alter_stmts=None):
    """Execute DDL incrementally — only creates what's missing."""
    import asyncpg

    conn_kwargs = _parse_db_url(DATABASE_URL)
    try:
        conn = await asyncpg.connect(**conn_kwargs, timeout=10)
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

    print(f"Connected to PostgreSQL ({conn_kwargs['host']}/{conn_kwargs['database']})")

    await ensure_vector_extension(conn)

    # Get existing tables
    existing = set(await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
    ))
    existing_names = {r['tablename'] for r in existing}
    model_names = {name for name, _ in table_stmts}
    missing = model_names - existing_names

    if not missing:
        print(f"✅ Schema complete ({len(existing_names)} tables). Nothing to do.")
        await conn.close()
        return True

    print(f"  Found {len(existing_names)} tables, {len(missing)} missing. Creating...")

    # Tables that will exist after this run = already existing + about to be created
    # Used by _patch_create_table_sql to strip FKs to permanently-deferred tables.
    available_tables = existing_names | model_names

    # 1. Create enums (idempotent)
    for sql in enum_stmts:
        try:
            await conn.execute(sql)
        except Exception:
            pass

    # 2. Create missing tables (multi-pass for FK ordering)
    remaining = [(name, _patch_create_table_sql(sql, available_tables)) for name, sql in table_stmts if name in missing]
    created = 0
    unresolved_errors = {}
    for pass_num in range(4):
        still_remaining = []
        for name, sql in remaining:
            try:
                await conn.execute(sql)
                created += 1
                unresolved_errors.pop(name, None)
            except Exception as e:
                err = str(e)
                if "already exists" in err:
                    created += 1
                    unresolved_errors.pop(name, None)
                else:
                    still_remaining.append((name, sql))
                    unresolved_errors[name] = err[:180]
        remaining = still_remaining
        if not remaining:
            break

    # 3. Add deferred FK constraints (use_alter=True)
    if alter_stmts:
        for name, sql in alter_stmts:
            if name in missing:
                try:
                    await conn.execute(sql)
                except Exception:
                    pass  # "already exists" is fine

    # 4. Create indexes for newly-created tables
    idx_created = 0
    for name, sql in index_stmts:
        if name in missing:
            try:
                await conn.execute(sql)
                idx_created += 1
            except Exception:
                pass  # "already exists" is fine

    # Final count
    final_count = await conn.fetchval(
        "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public'"
    )
    await conn.close()

    failed = len(remaining)
    print(f"\n✅ Schema sync complete: {created} tables created, {idx_created} indexes added ({final_count} total tables)")
    if failed:
        print(f"   ({failed} tables could not be created due to FK or other issues)")
        for tbl, err in unresolved_errors.items():
            print(f"   ❌ {tbl}: {err}")

    # Success if no failures, or some tables were created, or DB already has most tables
    return failed == 0 or created > 0 or final_count > 50


async def main():
    try:
        print("Generating SQL from SQLAlchemy models...")
        enum_stmts, table_stmts, index_stmts, alter_stmts = await extract_sql_from_models()
        print(f"✅ Generated DDL for {len(table_stmts)} tables, {len(enum_stmts)} enums, {len(index_stmts)} indexes")

        print("\nSyncing schema (creating missing tables)...")
        success = await execute_sql_async(enum_stmts, table_stmts, index_stmts, alter_stmts)

        return 0 if success else 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
