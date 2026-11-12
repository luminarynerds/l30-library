#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed Item Copies (Holdings) - Makes checkouts possible

Creates 2-5 physical copies for each catalog item, enabling circulation workflows.
Without this, the checkout feature is completely broken.
"""
import sys, os
from pathlib import Path
from datetime import datetime, timezone
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.models.item_copy import ItemCopy
from app.models.catalog_item import CatalogItem

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@database:5432/lsc_library")
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

CONDITIONS = ["excellent", "good", "fair", "poor"]
LOCATIONS = ["Main Branch", "Elmdale Branch", "Reference Section", "Digital Collection"]

async def seed_item_copies():
    """Create item copies (holdings) for all catalog items"""
    async with async_session() as session:
        try:
            print("=" * 70)
            print("📚 Seeding Item Copies (Holdings)")
            print("=" * 70)

            # Get all catalog items
            result = await session.execute(text("SELECT id FROM catalog_items ORDER BY id"))
            catalog_item_ids = [row[0] for row in result.fetchall()]

            if not catalog_item_ids:
                print("❌ No catalog items found. Run seed_comprehensive.py first.")
                return

            _ = 0
            copy_count = 0

            for idx, catalog_item_id in enumerate(catalog_item_ids):
                # Create 2-5 copies per item (more for popular types)
                num_copies = 2 if idx % 3 == 0 else (3 if idx % 2 == 0 else 2)

                for copy_num in range(1, num_copies + 1):
                    condition = CONDITIONS[copy_num % len(CONDITIONS)]
                    location = LOCATIONS[idx % len(LOCATIONS)]
                    barcode = f"COPY-{catalog_item_id:04d}-{copy_num:03d}"

                    # Create item copy
                    await session.execute(text("""
                        INSERT INTO item_copies
                        (catalog_item_id, barcode, condition, location, status, created_at, updated_at)
                        VALUES (:cat_id, :barcode, :condition, :location, :status, :now, :now)
                    """), {
                        "cat_id": catalog_item_id,
                        "barcode": barcode,
                        "condition": condition,
                        "location": location,
                        "status": "available",
                        "now": datetime.now(timezone.utc)
                    })

                    copy_count += 1

                # Show progress
                if (idx + 1) % 5 == 0:
                    print(f"  ✓ Processing item {idx + 1}/{len(catalog_item_ids)}...")

            await session.commit()

            # Verify
            result = await session.execute(text("SELECT COUNT(*) FROM item_copies"))
            total = result.scalar()

            print()
            print("=" * 70)
            print("✅ SEEDING COMPLETE!")
            print("=" * 70)
            print(f"✓ Created {total} item copies across {len(catalog_item_ids)} catalog items")
            print(f"  Average copies per item: {total / len(catalog_item_ids):.1f}")
            print()
            print("Status Summary:")
            result = await session.execute(text("SELECT status, COUNT(*) FROM item_copies GROUP BY status"))
            for status, count in result.fetchall():
                print(f"  • {status}: {count}")
            print()
            print("Condition Distribution:")
            result = await session.execute(text("SELECT condition, COUNT(*) FROM item_copies GROUP BY condition"))
            for cond, count in result.fetchall():
                print(f"  • {cond}: {count}")
            print()
            print("✅ Item copies are now ready for checkout!")
            print("   Patrons can now borrow items from the catalog.")

        except Exception as e:
            print(f"❌ Error seeding item copies: {e}")
            await session.rollback()
            raise

async def main():
    try:
        await seed_item_copies()
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
