#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Simplified seed script to create reading lists from catalog items.

Creates sample thematic reading lists (staff-curated) and inserts them
into the reading_lists and list_items tables.
"""
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def seed_reading_lists():
    """Create sample reading lists with catalog items."""
    async with AsyncSessionLocal() as db:
        print("\n=== Seeding Reading Lists ===")

        # Check if thematic lists already exist
        result = await db.execute(text(
            "SELECT COUNT(*) FROM reading_lists WHERE name IN ('Neurodivergent Voices', 'Contemporary Fiction', 'Sci-Fi Adventures')"
        ))
        existing = result.scalar() or 0
        if existing > 0:
            print(f"  Thematic reading lists already exist ({existing} found), skipping")
            return

        # Get a staff user to own the curated lists
        result = await db.execute(text(
            "SELECT id FROM users WHERE email = 'staff@l30.org' LIMIT 1"
        ))
        staff_row = result.fetchone()
        if not staff_row:
            print("  No staff user found, skipping thematic reading lists")
            return
        staff_id = staff_row[0]

        # Get catalog items
        result = await db.execute(text(
            "SELECT id, title, author FROM catalog_items ORDER BY id LIMIT 25"
        ))
        items = result.fetchall()

        if len(items) < 5:
            print(f"  Not enough catalog items ({len(items)} found, need 5+)")
            return

        # Create thematic lists using catalog items
        lists = [
            {
                "name": "Neurodivergent Voices",
                "description": "Stories exploring neurodiversity and different perspectives",
                "is_public": True,
                "books": items[0:5],
            },
            {
                "name": "Contemporary Fiction",
                "description": "Modern stories that resonate today",
                "is_public": True,
                "books": items[5:10],
            },
            {
                "name": "Sci-Fi Adventures",
                "description": "Travel to other worlds and futures",
                "is_public": True,
                "books": items[10:15],
            },
        ]

        for list_info in lists:
            # Insert reading list
            await db.execute(text(
                """
                INSERT INTO reading_lists (user_id, name, description, is_public, share_token)
                VALUES (:uid, :name, :desc, :public, :token)
                """
            ), {
                "uid": staff_id,
                "name": list_info["name"],
                "desc": list_info["description"],
                "public": list_info["is_public"],
                "token": uuid.uuid4().hex[:32],
            })

            # Get the list ID
            result = await db.execute(text(
                "SELECT id FROM reading_lists WHERE name = :n AND user_id = :uid"
            ), {"n": list_info["name"], "uid": staff_id})
            list_row = result.fetchone()
            if not list_row:
                continue
            list_id = list_row[0]

            # Add books to the list
            added = 0
            for item_id, title, author in list_info["books"]:
                await db.execute(text(
                    "INSERT INTO list_items (list_id, catalog_item_id) VALUES (:lid, :cid)"
                ), {"lid": list_id, "cid": item_id})
                added += 1

            book_titles = ", ".join([title for _, title, _ in list_info["books"]])
            print(f"  Created '{list_info['name']}' with {added} items: {book_titles[:60]}...")

        await db.commit()
        print("\n  Seeding Complete! Created 3 thematic reading lists")


async def main():
    try:
        await seed_reading_lists()
    except Exception as e:
        print(f"\n  Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
