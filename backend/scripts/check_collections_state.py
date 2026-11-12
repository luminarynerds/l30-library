#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Check the current state of collections in the database.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine


async def check_collections_state():
    """Check if collections tables exist and their current state."""
    async with engine.connect() as conn:
        # Check current migration version
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        current_version = result.scalar()
        print(f"Current migration version: {current_version}")
        print()

        # Check if collections table exists
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'collections')"
        ))
        collections_exists = result.scalar()
        print(f"Collections table exists: {collections_exists}")

        # Check if collection_items table exists
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'collection_items')"
        ))
        items_exists = result.scalar()
        print(f"Collection_items table exists: {items_exists}")
        print()

        if collections_exists:
            # Count collections
            result = await conn.execute(text("SELECT COUNT(*) FROM collections"))
            count = result.scalar()
            print(f"Number of collections: {count}")

            if count > 0:
                # Show collections
                result = await conn.execute(text(
                    "SELECT id, name, slug, is_public, created_at FROM collections ORDER BY display_order, id"
                ))
                print("\nExisting collections:")
                for row in result:
                    print(f"  - ID {row[0]}: {row[1]} ({row[2]}) - Public: {row[3]}")

        if items_exists:
            # Count items
            result = await conn.execute(text("SELECT COUNT(*) FROM collection_items"))
            count = result.scalar()
            print(f"\nNumber of collection items: {count}")

            if count > 0:
                # Show item counts per collection
                result = await conn.execute(text("""
                    SELECT c.name, COUNT(ci.id) as item_count
                    FROM collections c
                    LEFT JOIN collection_items ci ON c.id = ci.collection_id
                    GROUP BY c.id, c.name
                    ORDER BY c.display_order, c.id
                """))
                print("\nItems per collection:")
                for row in result:
                    print(f"  - {row[0]}: {row[1]} items")


if __name__ == "__main__":
    asyncio.run(check_collections_state())
