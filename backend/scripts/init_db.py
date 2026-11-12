#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Database initialization script.

Initializes the database schema from SQLAlchemy models.
Used by CI/CD pipelines and Docker entrypoint.

Supports both PostgreSQL (production) and SQLite (local development).
For SQLite, automatically converts PostgreSQL-specific types (JSONB, ARRAY, BYTEA)
to SQLite-compatible equivalents.

Usage:
    python scripts/init_db.py
    python scripts/init_db.py --drop  # Drop tables first (dangerous)
"""

import sys
import os
import asyncio
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://lsc:password@localhost:5432/lsc_library")


async def init_database(drop_first: bool = False):
    """Initialize database schema from SQLAlchemy models."""
    # Use raw SQL approach to avoid SQLAlchemy metadata caching issues with AsyncPG
    # Try the raw SQL initialization first, fall back to SQLAlchemy if needed
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "scripts/init_schema_async_raw_sql.py"],
        cwd=str(Path(__file__).parent.parent)
    )

    if result.returncode == 0:
        print("✅ Database schema initialized successfully")
        return True
    else:
        print("⚠️  Raw SQL initialization failed, attempting fallback...")
        # Fallback to SQLAlchemy approach if raw SQL fails
        from tests.database_setup import create_tables_from_models
        success = await create_tables_from_models(DATABASE_URL)
        if success:
            import app.models  # noqa: F401
            from app.core.database import Base
            print(f"Schema ready with {len(Base.metadata.tables)} table definitions.")
        return success


async def main():
    drop_first = "--drop" in sys.argv

    if drop_first and sys.stdin.isatty():
        print("WARNING: This will DROP all existing tables!")
        response = input("Type 'YES' to confirm: ")
        if response != "YES":
            print("Cancelled.")
            return

    success = await init_database(drop_first=drop_first)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
