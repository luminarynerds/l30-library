#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed Data Verification Script

This script checks if critical seeded data exists in the database and warns
when data appears to be missing. Run this after container restarts, deployments,
or when you suspect data loss.

Usage:
    python scripts/verify_seed_data.py
    python scripts/verify_seed_data.py --fix  # Re-run seeds if data is missing
"""
import sys
import os
import asyncio
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@database:5432/lsc_library")
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Expected minimum counts for critical seed data
EXPECTED_SEED_DATA = {
    "catalog_items": {
        "min_count": 20,
        "description": "Library catalog items (books, DVDs, etc.)",
        "seed_script": "seed_comprehensive.py",
    },
    "events": {
        "min_count": 5,
        "description": "Upcoming library events",
        "seed_script": "seed_comprehensive.py",
    },
    "announcements": {
        "min_count": 1,
        "description": "Library announcements",
        "seed_script": "seed_comprehensive.py",
    },
    "staff_bios": {
        "min_count": 3,
        "description": "Staff biography entries",
        "seed_script": "seed_lsc_features.py",
    },
    "courses": {
        "min_count": 2,
        "description": "Learning/training courses",
        "seed_script": "seed_comprehensive.py or seed_staff_training.py",
    },
    "users": {
        "min_count": 5,
        "description": "Test user accounts",
        "seed_script": "seed_test_accounts.py",
    },
}


async def check_table_exists(session: AsyncSession, table_name: str) -> bool:
    """Check if a table exists in the database."""
    result = await session.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table_name
        )
    """), {"table_name": table_name})
    return result.scalar()


async def get_table_count(session: AsyncSession, table_name: str) -> int:
    """Get the row count for a table."""
    try:
        result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar() or 0
    except Exception:
        return -1


async def verify_seed_data():
    """Verify that all expected seed data exists."""
    print("=" * 70)
    print("LSC Library - Seed Data Verification")
    print("=" * 70)
    print()

    issues_found = []
    warnings_found = []

    async with async_session() as session:
        # First, check if database has any tables at all
        result = await session.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
        """))
        total_tables = result.scalar()

        if total_tables == 0:
            print("CRITICAL: Database has NO tables!")
            print("This indicates the database was dropped or never initialized.")
            print()
            print("To fix: Run the entrypoint script or docker-compose up")
            return False

        print(f"Database contains {total_tables} tables")
        print()
        print("Checking seed data...")
        print("-" * 70)

        for table_name, config in EXPECTED_SEED_DATA.items():
            exists = await check_table_exists(session, table_name)

            if not exists:
                status = "MISSING TABLE"
                issues_found.append(f"Table '{table_name}' does not exist")
                print(f"  {table_name}: {status}")
                continue

            count = await get_table_count(session, table_name)
            min_count = config["min_count"]

            if count == 0:
                status = "EMPTY (DATA LOST?)"
                issues_found.append(
                    f"Table '{table_name}' is empty - expected at least {min_count} rows. "
                    f"Re-run: python scripts/{config['seed_script']}"
                )
            elif count < min_count:
                status = f"LOW ({count}/{min_count})"
                warnings_found.append(
                    f"Table '{table_name}' has {count} rows (expected {min_count}+). "
                    f"Consider re-running: python scripts/{config['seed_script']}"
                )
            else:
                status = f"OK ({count} rows)"

            print(f"  {table_name}: {status}")

        print("-" * 70)
        print()

        # Check for signs of recent data loss
        print("Checking for data loss indicators...")
        print("-" * 70)

        # Check if alembic version is current
        try:
            result = await session.execute(text(
                "SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1"
            ))
            version = result.scalar()
            if version:
                print(f"  Alembic migration version: {version[:12]}...")
            else:
                warnings_found.append("No Alembic migration version found - migrations may not have run")
                print("  Alembic migration version: NOT SET (warning)")
        except Exception:
            print("  Alembic migration version: Unable to check")

        # Check for recent activity
        try:
            result = await session.execute(text("""
                SELECT
                    MAX(created_at) as last_user,
                    COUNT(*) as total_users
                FROM users
            """))
            row = result.fetchone()
            if row and row.total_users > 0:
                print(f"  Users table: {row.total_users} users, last created: {row.last_user}")
            else:
                print("  Users table: Empty or no timestamps")
        except Exception:
            print("  Users table: Unable to check activity")

        print("-" * 70)
        print()

        # Summary
        if issues_found:
            print("ISSUES FOUND:")
            for issue in issues_found:
                print(f"  - {issue}")
            print()

        if warnings_found:
            print("WARNINGS:")
            for warning in warnings_found:
                print(f"  - {warning}")
            print()

        if not issues_found and not warnings_found:
            print("All seed data verified successfully!")
            return True

        print("=" * 70)
        print("RECOMMENDED ACTIONS:")
        print("=" * 70)

        if issues_found:
            print()
            print("To restore missing seed data, run:")
            print("  cd /opt/l30/backend")
            print("  python scripts/seed_comprehensive.py")
            print("  python scripts/seed_test_accounts.py")
            print("  python scripts/seed_lsc_features.py")
            print()
            print("Common causes of data loss:")
            print("  1. Running 'docker compose down -v' (removes volumes)")
            print("  2. Running 'alembic downgrade' (rolls back migrations)")
            print("  3. Running rollback.sh with full database restore")
            print("  4. Database container recreated without persistent volume")
            print()

        return len(issues_found) == 0


async def run_seeds_if_missing():
    """Re-run seed scripts if data is missing."""
    print("Checking if seeds need to be re-run...")

    # Import and run seed scripts
    import subprocess

    scripts_dir = Path(__file__).parent
    seed_scripts = [
        "seed_comprehensive.py",
        "seed_test_accounts.py",
    ]

    for script in seed_scripts:
        script_path = scripts_dir / script
        if script_path.exists():
            print(f"Running {script}...")
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(scripts_dir.parent),
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"  Error running {script}: {result.stderr}")
            else:
                print(f"  {script} completed")
        else:
            print(f"  Script not found: {script}")


async def main():
    fix_mode = "--fix" in sys.argv

    success = await verify_seed_data()

    if not success and fix_mode:
        print()
        print("=" * 70)
        print("Running seed scripts to restore data...")
        print("=" * 70)
        await run_seeds_if_missing()
        print()
        print("Re-verifying...")
        await verify_seed_data()
    elif not success:
        print()
        print("Tip: Run with --fix flag to automatically re-seed missing data:")
        print("  python scripts/verify_seed_data.py --fix")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
