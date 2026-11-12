#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed script to create catalog collections.

Creates a small set of themed collections and attaches catalog items to each.
Idempotent: collections are matched by name, so re-running adds nothing.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.catalog import CatalogItem
from app.models.collection import Collection, CollectionItem

COLLECTIONS = [
    {
        "name": "Accessibility & Neurodiversity",
        "description": "Books exploring different ways of thinking",
    },
    {
        "name": "Contemporary Voices",
        "description": "Modern authors tackling today's issues",
    },
    {
        "name": "Popular Media",
        "description": "DVDs, audiobooks, and more",
    },
]

MIN_ITEMS = 10
ITEMS_PER_COLLECTION = 5


async def seed_collections():
    """Create sample collections and attach catalog items to them."""
    async with AsyncSessionLocal() as db:
        print("\n=== Seeding Catalog Collections ===")

        result = await db.execute(select(CatalogItem.id).order_by(CatalogItem.id).limit(25))
        item_ids = list(result.scalars())

        if len(item_ids) < MIN_ITEMS:
            print(f"⚠️  Only {len(item_ids)} catalog items found (need {MIN_ITEMS}+)")
            return 1

        created = 0
        for position, spec in enumerate(COLLECTIONS):
            existing = await db.execute(select(Collection).where(Collection.name == spec["name"]))
            collection = existing.scalar_one_or_none()

            if collection is None:
                collection = Collection(
                    name=spec["name"],
                    description=spec["description"],
                    position=position,
                )
                db.add(collection)
                await db.flush()
                created += 1
                print(f"✅ Collection {position + 1}: {spec['name']}")
            else:
                print(f"↷ Collection already present: {spec['name']}")

            # Attach a slice of the catalog to this collection.
            slice_start = position * ITEMS_PER_COLLECTION
            wanted = item_ids[slice_start : slice_start + ITEMS_PER_COLLECTION]

            linked = await db.execute(
                select(CollectionItem.catalog_item_id).where(
                    CollectionItem.collection_id == collection.id
                )
            )
            already = set(linked.scalars())

            for item_position, catalog_item_id in enumerate(wanted):
                if catalog_item_id in already:
                    continue
                db.add(
                    CollectionItem(
                        collection_id=collection.id,
                        catalog_item_id=catalog_item_id,
                        position=item_position,
                    )
                )

        await db.commit()

        total = await db.execute(select(func.count(Collection.id)))
        print(f"\n✅ Seeding complete. Created {created}; {total.scalar()} total.")
        return 0


async def main():
    try:
        return await seed_collections()
    except Exception as e:  # noqa: BLE001
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
