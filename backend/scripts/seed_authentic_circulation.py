#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Authentic Library Circulation Patterns
Generates 6 months of realistic checkout/hold/fine data with diverse patron behaviors
"""
import asyncio
import os
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@database:5432/lsc_library")
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Patron archetypes with behavioral parameters
PATRON_ARCHETYPES = {
    "power_reader": {
        "weight": 0.15,
        "monthly_checkouts": (8, 12),
        "checkout_duration": (21, 35),
        "renewal_probability": 0.55,
        "hold_probability": 0.40,
    },
    "theme_loyalist": {
        "weight": 0.25,
        "monthly_checkouts": (4, 8),
        "checkout_duration": (14, 28),
        "renewal_probability": 0.50,
        "hold_probability": 0.25,
    },
    "casual_browser": {
        "weight": 0.35,
        "monthly_checkouts": (2, 5),
        "checkout_duration": (7, 21),
        "renewal_probability": 0.30,
        "hold_probability": 0.10,
    },
    "seasonal_user": {
        "weight": 0.15,
        "monthly_checkouts": (0, 8),  # Varies by season
        "checkout_duration": (14, 28),
        "renewal_probability": 0.40,
        "hold_probability": 0.15,
    },
    "collector": {
        "weight": 0.10,
        "monthly_checkouts": (3, 6),
        "checkout_duration": (28, 35),
        "renewal_probability": 0.60,
        "hold_probability": 0.50,
    },
}

# Theme circulation rates (% of items currently checked out)
THEME_CIRCULATION_RATES = {
    "Neurodiversity & Inclusion": 0.45,
    "Community & Connection": 0.35,
    "Creative Expression": 0.25,
    "Digital & AI Literacy": 0.35,
    "Wellness & Growth": 0.38,
    "Adventure & Escape": 0.55,
}

async def seed():
    """Generate authentic circulation patterns"""
    try:
        async with async_session() as session:
            print("📚 Seeding Authentic Circulation Patterns...")
            print("=" * 70)

            # Get existing patrons
            patrons_result = await session.execute(
                text("SELECT id FROM users WHERE role = 'PATRON' ORDER BY id")
            )
            patron_ids = [r[0] for r in patrons_result.fetchall()]

            if len(patron_ids) < 70:
                print(f"⚠️  Only {len(patron_ids)} patrons found. Need ~70 for authentic patterns.")
                print("   Creating synthetic patron activity anyway...")

            # Get items with their themes
            items_result = await session.execute(
                text("""SELECT id, subjects FROM catalog_items ORDER BY id""")
            )
            items_data = [(r[0], r[1]) for r in items_result.fetchall()]

            if not patron_ids or not items_data:
                print("❌ Insufficient data to seed circulation")
                return

            now = datetime.now(timezone.utc)
            _ = now - timedelta(days=180)

            checkouts_added = 0
            holds_added = 0
            fines_added = 0

            # Assign patrons to archetypes
            patron_archetypes = {}
            archetype_weights = list(PATRON_ARCHETYPES.items())

            for patron_id in patron_ids:
                archetype_name = random.choices(
                    [name for name, _ in archetype_weights],
                    weights=[weight["weight"] for _, weight in archetype_weights],
                    k=1
                )[0]
                patron_archetypes[patron_id] = (archetype_name, PATRON_ARCHETYPES[archetype_name])

            print("👥 Patron Distribution:")
            for archetype_name, config in PATRON_ARCHETYPES.items():
                count = sum(1 for a in patron_archetypes.values() if a[0] == archetype_name)
                print(f"   {archetype_name}: {count} patrons")

            # Generate checkouts for each patron
            for patron_id in patron_ids:
                archetype_name, archetype_config = patron_archetypes[patron_id]

                # Vary checkout count by season
                base_monthly = random.randint(*archetype_config["monthly_checkouts"])
                monthly_checkouts = int(base_monthly * random.uniform(0.8, 1.2))  # ±20% variance
                total_checkouts = monthly_checkouts * 6  # 6 months

                for _ in range(total_checkouts):
                    item_id, subjects = random.choice(items_data)

                    # Random checkout date in past 6 months
                    days_ago = random.randint(1, 180)
                    checkout_date = now - timedelta(days=days_ago)

                    # Duration varies by archetype and item type
                    duration = random.randint(*archetype_config["checkout_duration"])
                    due_date = checkout_date + timedelta(days=duration)

                    # Determine status: 70% returned, 20% active, 10% overdue
                    status_roll = random.random()
                    if status_roll < 0.70:
                        status = "returned"
                    elif status_roll < 0.90:
                        status = "active"
                    else:
                        status = "overdue"

                    # Insert checkout
                    try:
                        await session.execute(
                            text("""INSERT INTO checkouts
                            (user_id, item_id, checked_out_at, due_date, status, renewal_count, last_overdue_days_processed)
                            VALUES (:u, :i, :cd, :dd, :s, 0, 0)"""),
                            {
                                "u": patron_id,
                                "i": item_id,
                                "cd": checkout_date,
                                "dd": due_date,
                                "s": status,
                            }
                        )
                        checkouts_added += 1
                    except Exception:
                        pass  # Handle duplicate active checkouts

                    # Create holds on popular items (15% probability)
                    if random.random() < 0.15 and archetype_config["hold_probability"] > random.random():
                        hold_date = checkout_date - timedelta(days=random.randint(1, 30))
                        try:
                            await session.execute(
                                text("""INSERT INTO holds
                                (user_id, item_id, status, position, created_at)
                                VALUES (:u, :i, :s, :pos, :hd)"""),
                                {
                                    "u": patron_id,
                                    "i": item_id,
                                    "s": random.choice(["pending", "ready", "fulfilled", "cancelled", "expired"]),
                                    "pos": random.randint(1, 5),
                                    "hd": hold_date,
                                }
                            )
                            holds_added += 1
                        except Exception:
                            pass

                    # Create fines for overdue items (20% of overdue)
                    if status == "overdue" and random.random() < 0.20:
                        days_overdue = (now - due_date).days
                        amount = min(days_overdue * 0.25, 50.0)
                        fine_status = random.choices(["unpaid", "paid", "partial"], weights=[0.5, 0.35, 0.15])[0]
                        amount_paid = amount if fine_status == "paid" else (amount / 2 if fine_status == "partial" else 0)

                        try:
                            await session.execute(
                                text("""INSERT INTO fines
                                (user_id, fine_type, amount, amount_paid, description, status, created_at)
                                VALUES (:u, 'overdue', :a, :ap, 'Overdue item fine', :s, :cd)"""),
                                {
                                    "u": patron_id,
                                    "a": amount,
                                    "ap": amount_paid,
                                    "s": fine_status,
                                    "cd": checkout_date,
                                }
                            )
                            fines_added += 1
                        except Exception:
                            pass

            await session.commit()

            # Gather statistics
            checkouts_count = await session.execute(text("SELECT COUNT(*) FROM checkouts"))
            active_count = await session.execute(text("SELECT COUNT(*) FROM checkouts WHERE status = 'active'"))
            overdue_count = await session.execute(text("SELECT COUNT(*) FROM checkouts WHERE status = 'overdue'"))
            holds_count = await session.execute(text("SELECT COUNT(*) FROM holds WHERE status = 'pending'"))
            fines_count = await session.execute(text("SELECT COUNT(*) FROM fines WHERE status = 'unpaid'"))

            print("\n" + "=" * 70)
            print("✅ CIRCULATION SEEDING COMPLETE")
            print("=" * 70)
            print("📊 Statistics:")
            print(f"   Total Checkouts (6 months): {checkouts_count.scalar() or 0}")
            print(f"   Currently Active: {active_count.scalar() or 0}")
            print(f"   Overdue Items: {overdue_count.scalar() or 0}")
            print(f"   Active Holds: {holds_count.scalar() or 0}")
            print(f"   Outstanding Fines: {fines_count.scalar() or 0}")
            print("=" * 70)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(seed())
