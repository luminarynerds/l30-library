#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed Active Checkouts - Enables check-in workflow testing

Creates example active checkouts so staff can test the check-in workflow.
Also creates some overdue checkouts for testing fine calculation.
"""
import sys, os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

DATABASE_URL = os.environ["DATABASE_URL"]  # Required - no hardcoded credentials
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def seed_active_checkouts():
    """Create active checkouts for testing check-in workflow"""
    async with async_session() as session:
        try:
            print("=" * 70)
            print("🔄 Seeding Active Checkouts")
            print("=" * 70)

            # Get users (skip admin)
            result = await session.execute(text(
                "SELECT id FROM users WHERE role IN ('PATRON', 'STAFF') LIMIT 5"
            ))
            user_ids = [row[0] for row in result.fetchall()]

            if not user_ids:
                print("❌ No patron/staff accounts found")
                return

            # Get item copies (distinct catalog_item_id to avoid unique constraint on active checkouts)
            result = await session.execute(text(
                "SELECT DISTINCT ON (catalog_item_id) id, catalog_item_id FROM item_copies ORDER BY catalog_item_id, id LIMIT 10"
            ))
            item_copies = [row for row in result.fetchall()]

            if not item_copies:
                print("❌ No item copies found. Run seed_item_copies.py first.")
                return

            checkouts_created = 0
            now = datetime.now(timezone.utc)
            default_loan_days = 21

            for idx, (item_copy_id, catalog_item_id) in enumerate(item_copies[:8]):
                user_id = user_ids[idx % len(user_ids)]

                # Skip if an active checkout already exists for this item
                existing = await session.execute(text(
                    "SELECT id FROM checkouts WHERE item_id = :iid AND status = 'active'"
                ), {"iid": catalog_item_id})
                if existing.fetchone():
                    continue

                # Mix of current and overdue
                if idx % 3 == 0:
                    # Overdue (due 5 days ago)
                    checkout_date = now - timedelta(days=26)
                    due_date = now - timedelta(days=5)
                else:
                    # Current (due in future)
                    checkout_date = now - timedelta(days=5)
                    due_date = now + timedelta(days=default_loan_days - 5)

                await session.execute(text("""
                    INSERT INTO checkouts
                    (user_id, item_id, item_copy_id, checked_out_at, due_date, status, renewal_count, last_overdue_days_processed)
                    VALUES (:user_id, :item_id, :item_copy_id, :checked_out_at, :due_date, :status, 0, 0)
                """), {
                    "user_id": user_id,
                    "item_id": catalog_item_id,
                    "item_copy_id": item_copy_id,
                    "checked_out_at": checkout_date,
                    "due_date": due_date,
                    "status": "active",
                })

                checkouts_created += 1

            await session.commit()

            # Verify
            result = await session.execute(text("SELECT COUNT(*) FROM checkouts"))
            total_checkouts = result.scalar()

            print()
            print("=" * 70)
            print("✅ SEEDING COMPLETE!")
            print("=" * 70)
            print(f"✓ Created {checkouts_created} active checkouts")
            print(f"✓ Total checkouts in system: {total_checkouts}")
            print()
            print("Checkout Status:")
            result = await session.execute(text(
                "SELECT status, COUNT(*) FROM checkouts GROUP BY status"
            ))
            for status, count in result.fetchall():
                print(f"  • {status}: {count}")

            print()
            print("Overdue Status:")
            result = await session.execute(text(
                "SELECT COUNT(*) FROM checkouts WHERE due_date < :now"
            ), {"now": now})
            overdue_count = result.scalar()
            print(f"  • Overdue checkouts: {overdue_count}")
            print(f"  • Current checkouts: {total_checkouts - overdue_count}")

            print()
            print("✅ Checkouts ready for check-in workflow testing!")
            print("   Staff can now test returning items to the library.")

        except Exception as e:
            print(f"❌ Error seeding checkouts: {e}")
            await session.rollback()
            raise

async def main():
    try:
        await seed_active_checkouts()
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
