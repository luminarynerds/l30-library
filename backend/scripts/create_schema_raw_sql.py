#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Generate and execute raw SQL DDL to create schema, bypassing SQLAlchemy metadata issues.

This script extracts CREATE TABLE/INDEX statements from SQLAlchemy models
and executes them as raw SQL to avoid prepared statement caching issues.
"""
import sys
import os
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://lsc:password@database:5432/lsc_library")


def extract_sql_from_models():
    """Generate CREATE TABLE statements from SQLAlchemy models."""
    import app.models  # noqa: F401
    from app.core.database import Base
    from sqlalchemy import create_engine
    from sqlalchemy.schema import CreateTable, CreateIndex

    # Use a sync engine just to generate SQL
    sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_url, strategy='mock', executor=lambda *args, **kw: None)

    sql_statements = []

    # Generate CREATE TABLE statements
    for table in Base.metadata.sorted_tables:
        sql = str(CreateTable(table).compile(engine))
        sql_statements.append(sql)

    # Generate CREATE INDEX statements separately
    for table in Base.metadata.sorted_tables:
        for index in table.indexes:
            sql = str(CreateIndex(index).compile(engine))
            sql_statements.append(sql)

    return sql_statements


def execute_sql(sql_statements):
    """Execute raw SQL statements against PostgreSQL."""
    # Parse connection string
    db_url = DATABASE_URL.replace("postgresql+asyncpg://", "").replace("postgresql://", "")
    # Extract credentials and host
    if "@" in db_url:
        creds, host_db = db_url.split("@")
        user, password = creds.split(":")
        if ":" in host_db:
            host_part, db_name = host_db.split("/")
            if ":" in host_part:
                host, port = host_part.split(":")
                port = int(port)
            else:
                host = host_part
                port = 5432
        else:
            raise ValueError("Invalid DATABASE_URL format")
    else:
        raise ValueError(f"Cannot parse DATABASE_URL: {DATABASE_URL}")

    try:
        # psycopg2 should work with container hostname "database" on the Docker network
        conn = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name,
            port=port,
            connect_timeout=10
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print(f"Connected to PostgreSQL ({host}/{db_name})")

        # First, drop all tables
        print("Dropping existing tables...")
        cursor.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename NOT LIKE 'apscheduler%') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END$$;
        """)
        print("✅ Tables dropped")

        # Execute CREATE statements
        successful = 0
        failed = 0

        for i, sql in enumerate(sql_statements, 1):
            try:
                cursor.execute(sql)
                successful += 1
                # Print first 100 chars of SQL
                sql_preview = sql[:100].replace('\n', ' ').strip()
                print(f"  [{i}/{len(sql_statements)}] ✅ {sql_preview}...")
            except Exception as e:
                failed += 1
                sql_preview = sql[:80].replace('\n', ' ').strip()
                print(f"  [{i}/{len(sql_statements)}] ⚠️  {sql_preview}... - {str(e)[:60]}")

        cursor.close()
        conn.close()

        print(f"\n✅ Schema creation complete: {successful} successful, {failed} failed")
        return failed == 0

    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False


def main():
    try:
        print("Generating SQL from SQLAlchemy models...")
        sql_statements = extract_sql_from_models()
        print(f"✅ Generated {len(sql_statements)} SQL statements")

        print("\nExecuting DDL statements...")
        success = execute_sql(sql_statements)

        return 0 if success else 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
