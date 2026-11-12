#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""User Engagement: Community Interactions (Reviews, Ratings)"""
import asyncio, sys, random
from pathlib import Path
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

DATABASE_URL = "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@localhost:5434/lsc_library"
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

REVIEW_SAMPLES = {
    5: [
        "Absolutely loved this! Changed how I think about the subject.",
        "Brilliant writing. Every page kept me engaged.",
        "This book is a masterpiece. Highly recommended!",
        "Couldn't put it down. Perfect in every way.",
        "This is the best book I've read all year!"
    ],
    4: [
        "Really good book. Minor issues but overall excellent.",
        "Great story with compelling characters.",
        "Loved it. A few slow parts but worth reading.",
        "Solid book. Would recommend to friends.",
        "Very well written. Enjoyed the journey."
    ],
    3: [
        "Decent book. Some parts worked better than others.",
        "Mixed feelings. Good premise but execution was uneven.",
        "Okay read. Didn't quite live up to the hype.",
        "It's fine. Entertaining but nothing special.",
        "Average. Some good moments, some boring ones."
    ],
    2: [
        "Didn't work for me. Couldn't finish it.",
        "Disappointed. Expected better based on reviews.",
        "Not my thing. Found it hard to connect with.",
        "Struggled through this one.",
        "Below average. Wouldn't recommend."
    ],
    1: [
        "Really didn't enjoy this.",
        "One of the worst books I've read.",
        "Not for me at all.",
        "Couldn't get into it.",
        "Waste of time for me."
    ]
}

async def seed():
    try:
        async with async_session() as session:
            # Get patrons and items
            patrons_result = await session.execute(
                text("SELECT id FROM users WHERE role = 'PATRON' ORDER BY RANDOM() LIMIT 30")
            )
            patron_ids = [r[0] for r in patrons_result.fetchall()]

            items_result = await session.execute(
                text("SELECT id FROM catalog_items ORDER BY RANDOM() LIMIT 200")
            )
            item_ids = [r[0] for r in items_result.fetchall()]

            if not patron_ids or not item_ids:
                print("❌ Not enough patrons or items")
                return

            reviews_added = 0
            now = datetime.now(timezone.utc)

            # Create 200-300 reviews with realistic distribution
            # 35% 5-star, 30% 4-star, 20% 3-star, 10% 2-star, 5% 1-star
            for item_id in item_ids:
                num_reviews = random.randint(1, 3)
                for _ in range(num_reviews):
                    patron_id = random.choice(patron_ids)

                    # Realistic rating distribution
                    roll = random.random()
                    if roll < 0.35:
                        rating = 5.0
                    elif roll < 0.65:
                        rating = 4.0
                    elif roll < 0.85:
                        rating = 3.0
                    elif roll < 0.95:
                        rating = 2.0
                    else:
                        rating = 1.0

                    review_text = random.choice(REVIEW_SAMPLES.get(int(rating), REVIEW_SAMPLES[3]))
                    review_date = now - timedelta(days=random.randint(1, 180))

                    try:
                        await session.execute(
                            text("""INSERT INTO event_reviews
                            (user_id, event_id, rating, review_text, created_at)
                            VALUES (:u, :e, :r, :t, :cd)
                            ON CONFLICT DO NOTHING"""),
                            {"u": patron_id, "e": item_id, "r": rating, "t": review_text, "cd": review_date}
                        )
                        reviews_added += 1
                    except Exception:
                        pass

            await session.commit()
            print(f"✅ Community Engagement: Added {reviews_added} reviews/ratings")
    except Exception as e:
        print(f"⚠️  Partial completion: {e}")

if __name__ == "__main__":
    asyncio.run(seed())
