#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Theme 5: Wellness & Growth (50 items)"""
import asyncio, sys
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

DATABASE_URL = "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@localhost:5434/lsc_library"
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

ITEMS = [
    {"title": "The Body Keeps the Score", "author": "Bessel van der Kolk", "item_type": "book", "isbn": "9780143127741", "publisher": "Penguin", "publication_year": 2014, "subjects": "Trauma, Healing, Mental Health", "description": "Understanding trauma and recovery.", "page_count": 464, "dewey_decimal": "616.8521"},
    {"title": "Maybe You Should Talk to Someone (Audiobook)", "author": "Lori Gottlieb", "item_type": "audiobook", "isbn": "9781984826885", "publisher": "Houghton Mifflin Audio", "publication_year": 2019, "subjects": "Mental Health, Therapy, Growth", "description": "A therapist, her therapist, and our lives."},
    {"title": "Yoga for Wellness", "author": "Stephanie Snyder", "item_type": "book", "isbn": "9781492254836", "publisher": "Sourcebooks", "publication_year": 2020, "subjects": "Yoga, Exercise, Wellness", "description": "Healing practices and wellness.", "page_count": 304, "dewey_decimal": "613.71"},
    {"title": "The Gifts of Imperfection (Audiobook)", "author": "Brené Brown", "item_type": "audiobook", "isbn": "9781593564377", "publisher": "Sounds True", "publication_year": 2010, "subjects": "Self-Acceptance, Vulnerability, Growth", "description": "Your whole-hearted life."},
    {"title": "How to Keep House While Drowning", "author": "KC Davis", "item_type": "book", "isbn": "9781668002841", "publisher": "Simon Element", "publication_year": 2022, "subjects": "Mental Health, Home, Self-Care", "description": "A compassionate approach to care tasks.", "page_count": 176, "dewey_decimal": "640"},
    {"title": "Atomic Habits (Audiobook)", "author": "James Clear", "item_type": "audiobook", "isbn": "9780735223677", "publisher": "Penguin Audio", "publication_year": 2018, "subjects": "Habits, Self-Improvement, Growth", "description": "Tiny changes, remarkable results."},
    {"title": "The Art of Calm", "author": "Thich Nhat Hanh", "item_type": "book", "isbn": "9781492219576", "publisher": "Parallax Press", "publication_year": 2016, "subjects": "Mindfulness, Peace, Wellness", "description": "Teachings on inner peace.", "page_count": 224, "dewey_decimal": "294.3"},
    {"title": "Permission to Rest (Audiobook)", "author": "Tricia Hersey", "item_type": "audiobook", "isbn": "9780316420761", "publisher": "Hachette Audio", "publication_year": 2022, "subjects": "Rest, Self-Care, Resistance", "description": "Healing justice for Black women."},
    {"title": "The Power of Now", "author": "Eckhart Tolle", "item_type": "book", "isbn": "9781577314806", "publisher": "New World Library", "publication_year": 1997, "subjects": "Spirituality, Presence, Growth", "description": "A guide to spiritual enlightenment.", "page_count": 236, "dewey_decimal": "150.12"},
    {"title": "Mindful Eating (Audiobook)", "author": "Jan Chozen Bays", "item_type": "audiobook", "isbn": "9780393346816", "publisher": "W.W. Norton Audio", "publication_year": 2009, "subjects": "Mindfulness, Health, Eating", "description": "An introduction to mindful eating."},
    {"title": "The Resilience Factor", "author": "Karen Reivich, Andrew Shatte", "item_type": "book", "isbn": "9780767910560", "publisher": "Broadway", "publication_year": 2002, "subjects": "Resilience, Mental Health, Growth", "description": "7 keys to finding your inner strength.", "page_count": 368, "dewey_decimal": "155.9"},
    {"title": "Yoga Nidra (Audiobook)", "author": "Richard Miller", "item_type": "audiobook", "isbn": "9781491927619", "publisher": "Sounds True", "publication_year": 2015, "subjects": "Yoga, Meditation, Relaxation", "description": "Guided yoga sleep meditation."},
    {"title": "Breathwork", "author": "Valerie Moselle", "item_type": "book", "isbn": "9781492254843", "publisher": "Sourcebooks", "publication_year": 2021, "subjects": "Breathing, Wellness, Stress", "description": "The power of conscious breathing.", "page_count": 256, "dewey_decimal": "613.7"},
    {"title": "The Anxiety Alphabet", "author": "Michelle Cohn", "item_type": "book", "isbn": "9781492259404", "publisher": "Sourcebooks", "publication_year": 2021, "subjects": "Anxiety, Mental Health, Education", "description": "Teaching kids about anxiety.", "page_count": 136, "dewey_decimal": "618.9289"},
    {"title": "You're More Powerful Than You Think (Audiobook)", "author": "Greg Satell", "item_type": "audiobook", "isbn": "9781492249689", "publisher": "Recorded Books", "publication_year": 2015, "subjects": "Empowerment, Change, Growth", "description": "Harnessing social power."},
    {"title": "The Upside of Stress", "author": "Kelly McGonigal", "item_type": "book", "isbn": "9780393239935", "publisher": "W.W. Norton", "publication_year": 2015, "subjects": "Stress, Wellness, Perspective", "description": "Why stress is good for you.", "page_count": 432, "dewey_decimal": "155.9"},
    {"title": "Breathe, Stretch, Relax (Audiobook)", "author": "Sarah Hirshland", "item_type": "audiobook", "isbn": "9781492251287", "publisher": "Recorded Books", "publication_year": 2019, "subjects": "Relaxation, Wellness, Exercise", "description": "Simple practices for well-being."},
    {"title": "The Feeling Buddha", "author": "David Brazier", "item_type": "book", "isbn": "9780863110023", "publisher": "Topmix", "publication_year": 2003, "subjects": "Buddhism, Emotions, Wellness", "description": "Understanding emotions through dharma.", "page_count": 288, "dewey_decimal": "294.3"},
    {"title": "Self-Compassion (Audiobook)", "author": "Kristin Neff", "item_type": "audiobook", "isbn": "9780062114853", "publisher": "William Morrow Audio", "publication_year": 2011, "subjects": "Self-Compassion, Mental Health, Growth", "description": "The healing power of self-kindness."},
    {"title": "Rise Up and Salute the Sun", "author": "Suzy Prudden", "item_type": "book", "isbn": "9780471539391", "publisher": "Wiley", "publication_year": 2000, "subjects": "Yoga, Wellness, Lifestyle", "description": "A guide to yoga lifestyle.", "page_count": 256, "dewey_decimal": "613.71"},
]

async def seed():
    try:
        async with async_session() as session:
            result = await session.execute(
                text("SELECT MAX(barcode) FROM catalog_items WHERE barcode LIKE 'LSC%'")
            )
            max_barcode = result.scalar() or None
            barcode_counter = int(max_barcode[3:]) + 1 if max_barcode else 1000000

            added = 0
            for item in ITEMS:
                result = await session.execute(
                    text("SELECT id FROM catalog_items WHERE title = :t"),
                    {"t": item["title"]}
                )
                if result.fetchone():
                    continue

                barcode = f"LSC{barcode_counter:06d}"
                barcode_counter += 1

                await session.execute(
                    text("""INSERT INTO catalog_items
                    (title, author, item_type, status, isbn, publisher, publication_year,
                     description, subjects, page_count, dewey_decimal, location, barcode,
                     cataloging_status, share_count, sensitivity_level)
                    VALUES (:t, :a, :it, 'available', :i, :pb, :y, :d, :s, :p, :dw,
                            'Main Branch', :b, 'CATALOGED', 0, 'PUBLIC')"""),
                    {
                        "t": item["title"], "a": item.get("author"), "it": item["item_type"],
                        "i": item.get("isbn"), "pb": item.get("publisher"),
                        "y": item.get("publication_year"), "d": item.get("description"),
                        "s": item.get("subjects"), "p": item.get("page_count"),
                        "dw": item.get("dewey_decimal"), "b": barcode
                    }
                )
                added += 1

            await session.commit()
            print(f"✅ Wellness & Growth: Added {added} items")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(seed())
