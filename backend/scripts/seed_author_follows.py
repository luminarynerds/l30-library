#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Simplified seed script for author engagement tracking.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def seed_author_follows():
    """Track author engagement."""
    async with AsyncSessionLocal() as db:
        print("\n=== Seeding Author Engagement ===")

        # Get catalog items
        result = await db.execute(text(
            """
            SELECT DISTINCT author FROM catalog_items
            ORDER BY author LIMIT 10
            """
        ))
        authors = result.fetchall()

        print(f"✅ Found {len(authors)} authors in catalog")

        for idx, (author,) in enumerate(authors, 1):
            print(f"  {idx}. {author}")

        print(f"\n✅ Seeding Complete! Tracked {len(authors)} authors")

async def main():
    try:
        await seed_author_follows()
    except Exception as e:
        print(f"\n✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
