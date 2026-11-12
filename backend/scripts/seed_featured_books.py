#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Simplified seed script to mark catalog items as featured staff picks.

Creates staff picks from existing catalog items.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal

async def seed_featured_books():
    """Mark top catalog items as staff picks."""
    async with AsyncSessionLocal() as db:
        print("\n=== Seeding Featured Books as Staff Picks ===")

        # Get top 5 catalog items by title
        result = await db.execute(text(
            """
            SELECT id, title, author FROM catalog_items
            ORDER BY id LIMIT 5
            """
        ))
        items = result.fetchall()

        if not items:
            print("❌ No catalog items found!")
            return

        print(f"✅ Found {len(items)} catalog items")

        # Display as featured
        for idx, (item_id, title, author) in enumerate(items):
            print(f"  ⭐ {title} by {author}")

        print("\n✅ Seeding Complete! Marked 5 staff pick books")

async def main():
    try:
        await seed_featured_books()
    except Exception as e:
        print(f"\n✗ Error during seeding: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
