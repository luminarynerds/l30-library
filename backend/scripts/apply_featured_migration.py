#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Apply the featured books migration directly via SQL

SECURITY: Database credentials must be provided via environment variables.
Set DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and DB_NAME before running.
"""
import asyncio
import os
import sys

import asyncpg


async def apply_migration():
    # SECURITY: Get database credentials from environment variables only
    db_password = os.environ.get('DB_PASSWORD')
    if not db_password:
        print("ERROR: DB_PASSWORD environment variable is required")
        print("Usage: DB_PASSWORD=<password> python apply_featured_migration.py")
        sys.exit(1)

    conn = await asyncpg.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', '5432')),
        user=os.environ.get('DB_USER', 'lsc'),
        password=db_password,
        database=os.environ.get('DB_NAME', 'lsc_library')
    )

    try:
        # Check if columns already exist
        result = await conn.fetchval("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'indie_ebooks'
            AND column_name = 'is_featured'
        """)

        if result > 0:
            print("Migration already applied - columns exist")
            return

        print("Applying migration: adding featured and staff picks fields...")

        # Add featured fields
        await conn.execute("""
            ALTER TABLE indie_ebooks
            ADD COLUMN is_featured BOOLEAN NOT NULL DEFAULT FALSE
        """)
        print("  - Added is_featured column")

        await conn.execute("""
            ALTER TABLE indie_ebooks
            ADD COLUMN featured_at TIMESTAMP WITH TIME ZONE
        """)
        print("  - Added featured_at column")

        await conn.execute("""
            ALTER TABLE indie_ebooks
            ADD COLUMN featured_until TIMESTAMP WITH TIME ZONE
        """)
        print("  - Added featured_until column")

        await conn.execute("""
            ALTER TABLE indie_ebooks
            ADD COLUMN featured_order INTEGER
        """)
        print("  - Added featured_order column")

        # Add staff picks fields
        await conn.execute("""
            ALTER TABLE indie_ebooks
            ADD COLUMN is_staff_pick BOOLEAN NOT NULL DEFAULT FALSE
        """)
        print("  - Added is_staff_pick column")

        await conn.execute("""
            ALTER TABLE indie_ebooks
            ADD COLUMN staff_pick_at TIMESTAMP WITH TIME ZONE
        """)
        print("  - Added staff_pick_at column")

        # Create indexes
        await conn.execute("""
            CREATE INDEX ix_indie_ebooks_is_featured ON indie_ebooks (is_featured)
        """)
        print("  - Created index on is_featured")

        await conn.execute("""
            CREATE INDEX ix_indie_ebooks_is_staff_pick ON indie_ebooks (is_staff_pick)
        """)
        print("  - Created index on is_staff_pick")

        print("\nMigration completed successfully!")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migration())
