#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Extended i18n Seed Data for LSC Library System

Adds comprehensive internationalization content:
- Items with special characters (é, ñ, ü)
- RTL text content (Arabic, Hebrew)
- Extended emoji in various content fields
- Bilingual descriptions and notes
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal

# Extended i18n Seed Data
I18N_CATALOG_ITEMS = [
    {
        "title": "Café au Lait: French Literature",
        "title_sort": "Cafe au Lait French Literature",
        "description": "A collection of French literary works with accented characters: café, naïve, résumé, élève. Perfect for language learners exploring the nuances of French spelling.",
        "item_type": "book",
        "isbn": "978-3-16-148410-0",
        "author": "François Müller",
        "language": "fre",
    },
    {
        "title": "Mañana: Spanish Short Stories",
        "title_sort": "Manana Spanish Short Stories",
        "description": "Colección de cuentos en español: mañana, niño, señor, año. Featuring traditional Spanish narratives with authentic diacritics and special characters.",
        "item_type": "book",
        "isbn": "978-84-XXX-XXXX-X",
        "author": "María García Rodríguez",
        "language": "spa",
    },
    {
        "title": "Schüler und Schule: German Grammar",
        "title_sort": "Schuler und Schule German Grammar",
        "description": "Comprehensive German learning materials with authentic umlauts: Schüler, Größe, Köln, Müller. Learn German orthography with precision.",
        "item_type": "book",
        "isbn": "978-3-XXX-XXXX-X",
        "author": "Klaus Hoffmann",
        "language": "ger",
    },
    {
        "title": "مكتبة الفنون 🎨 (Art Library - Arabic Edition)",
        "title_sort": "Maktabat al-Funun Art Library Arabic",
        "description": "مكتبة شاملة عن الفنون الإسلامية والعصرية. هذا الكتاب يغطي التاريخ، التقنيات، والأساليس الفنية. Arabic RTL text. 📚 Art history encyclopedia covering Islamic and contemporary art.",
        "item_type": "book",
        "isbn": "978-961-XXX-XXXX-X",
        "author": "أحمد محمود",
        "language": "ara",
        "reading_direction": "rtl",
    },
    {
        "title": "עברית: לימוד השפה 📖 (Hebrew: Language Learning)",
        "title_sort": "Ivrit Limud ha-Safa Hebrew Language",
        "description": "למידת העברית עם דוגמאות מהחיים היומיומים. Hebrew RTL text. Learn modern Hebrew with everyday examples. Includes 100+ vocabulary words with emoji helpers: 🏠 (bayit-house), 🍎 (tapuach-apple), 📚 (sefer-book).",
        "item_type": "book",
        "isbn": "978-965-XXX-XXXX-X",
        "author": "יוסף כהן",
        "language": "heb",
        "reading_direction": "rtl",
    },
]

I18N_PATRON_NOTES = [
    {
        "name": "Ahmed Al-Rashid",
        "email": "ahmed.rashid@l30.org",
        "note": "Prefers reading in Arabic (العربية) and English. Has accessibility needs for dyslexia.",
        "language_preference": "ara",
    },
    {
        "name": "Sarah Okonkwo",
        "email": "sarah.okonkwo@l30.org",
        "note": "Interested in African literature. Reading Mañana series next. 📖",
        "language_preference": "eng",
    },
    {
        "name": "François Leblanc",
        "email": "francois.leblanc@l30.org",
        "note": "Préfère les livres en français. Looking for café & cuisine publications. ☕",
        "language_preference": "fre",
    },
    {
        "name": "Klaus Hoffmann",
        "email": "klaus.hoffmann@l30.org",
        "note": "Deutsche Bücher nur. Schüler und Literatur sind meine Leidenschaft. 🎓",
        "language_preference": "ger",
    },
    {
        "name": "David Cohen",
        "email": "david.cohen@l30.org",
        "note": "עברית וגם אנגלית. Interested in both Hebrew and English materials. 📚",
        "language_preference": "heb",
    },
]

async def seed_extended_i18n():
    """Seed extended i18n catalog items."""
    print("🌍 Seeding Extended i18n Catalog Items...\n")

    async with AsyncSessionLocal() as db:
        added_count = 0

        for item_data in I18N_CATALOG_ITEMS:
            # Check if item already exists
            result = await db.execute(
                text("SELECT id FROM catalog_items WHERE title = :title"),
                {"title": item_data["title"]}
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"⊘ SKIPPED: {item_data['title']} (already exists)")
                continue

            try:
                # Insert catalog item
                await db.execute(
                    text("""
                        INSERT INTO catalog_items
                        (title, description, item_type, isbn, author, status, cataloging_status, sensitivity_level, share_count, total_checkouts, created_at, updated_at)
                        VALUES (:title, :description, :item_type, :isbn, :author, :status, :cataloging_status, :sensitivity_level, 0, 0, now(), now())
                    """),
                    {
                        "title": item_data["title"],
                        "description": item_data["description"],
                        "item_type": item_data["item_type"],
                        "isbn": item_data.get("isbn"),
                        "author": item_data.get("author"),
                        "status": "available",
                        "cataloging_status": "CATALOGED",
                        "sensitivity_level": "PUBLIC",
                    }
                )

                added_count += 1
                print(f"✅ Added: {item_data['title']}")
                print(f"   Author: {item_data.get('author')}")
                if item_data.get('language'):
                    print(f"   Language: {item_data.get('language', 'eng').upper()}")

                # Show sample of special characters
                if any(c in item_data["title"] for c in "éèêêñüö"):
                    chars = set(c for c in item_data["title"] if c in "éèêêñüö")
                    print(f"   Special chars: {chars}")

                if "🎨" in item_data["title"] or "🎯" in item_data["description"]:
                    print("   Contains emoji: ✓")

                print()

            except Exception as e:
                print(f"✗ ERROR: {item_data['title']}")
                print(f"  Reason: {str(e)}\n")
                continue

        await db.commit()

        print("=" * 80)
        print(f"Extended i18n Seeding Complete: {added_count} items added")
        print("=" * 80 + "\n")

        return added_count


async def add_patron_language_preferences():
    """Add language preferences to existing or new patrons."""
    print("🌐 Adding Patron Language Preferences...\n")

    async with AsyncSessionLocal() as db:
        added_count = 0

        # Check if preferred_language column exists on users table
        col_check = await db.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'preferred_language'")
        )
        has_lang_col = col_check.scalar_one_or_none() is not None

        if not has_lang_col:
            print("⊘ SKIPPED: users table does not have preferred_language column yet")
            return 0

        for patron_data in I18N_PATRON_NOTES:
            # Try to find existing patron
            result = await db.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": patron_data["email"]}
            )
            patron_id = result.scalar_one_or_none()

            try:
                if patron_id:
                    # Update existing patron's language preference
                    await db.execute(
                        text("""
                            UPDATE users
                            SET preferred_language = :lang
                            WHERE id = :id
                        """),
                        {
                            "id": patron_id,
                            "lang": patron_data["language_preference"],
                        }
                    )
                    print(f"✅ Updated: {patron_data['name']}")
                    print(f"   Language: {patron_data['language_preference'].upper()}")
                    added_count += 1
                else:
                    print(f"⊘ SKIPPED: {patron_data['name']} (not found in system)")

                print()

            except Exception as e:
                print(f"✗ ERROR: {patron_data['name']}")
                print(f"  Reason: {str(e)}\n")
                continue

        await db.commit()

        if added_count > 0:
            print("=" * 80)
            print(f"Patron Preferences Added: {added_count} patrons updated")
            print("=" * 80 + "\n")

        return added_count


async def verify_extended_i18n():
    """Verify extended i18n content was seeded."""
    print("\n" + "=" * 80)
    print("VERIFICATION: Extended i18n Content")
    print("=" * 80 + "\n")

    async with AsyncSessionLocal() as db:
        # Check special character items
        print("📋 Checking Special Character Items:")
        for search_char, description in [("é", "French accents"), ("ñ", "Spanish tildes"), ("ü", "German umlauts")]:
            result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM catalog_items
                    WHERE title ILIKE :pattern OR description ILIKE :pattern
                """),
                {"pattern": f"%{search_char}%"}
            )
            count = result.scalar()
            symbol = "✅" if count > 0 else "⚠️"
            print(f"  {symbol} {description}: {count} item(s)")

        # Check RTL items
        print("\n📋 Checking RTL Content:")
        rtl_indicators = ["Arabic", "مكتبة", "Hebrew", "עברית"]
        for indicator in rtl_indicators:
            result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM catalog_items
                    WHERE title ILIKE :pattern OR description ILIKE :pattern
                """),
                {"pattern": f"%{indicator}%"}
            )
            count = result.scalar()
            if count > 0:
                print(f"  ✅ Found RTL content: {indicator} ({count} item(s))")

        # Check emoji content
        print("\n📋 Checking Emoji Content:")
        emoji_list = ["🎨", "📖", "📚", "☕", "🎓"]
        total_emoji = 0
        for emoji in emoji_list:
            result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM catalog_items
                    WHERE title ILIKE :pattern OR description ILIKE :pattern
                """),
                {"pattern": f"%{emoji}%"}
            )
            count = result.scalar()
            if count > 0:
                total_emoji += count
                print(f"  ✅ Emoji '{emoji}': {count} item(s)")

        if total_emoji > 0:
            print(f"\n  Total items with emoji: {total_emoji}")

        print("\n✓ Extended i18n content verification complete")


async def main():
    """Main entry point."""
    try:
        items_added = await seed_extended_i18n()
        prefs_added = await add_patron_language_preferences()
        await verify_extended_i18n()

        print("\n" + "=" * 80)
        print("EXTENDED i18n SEEDING SUMMARY")
        print("=" * 80)
        print(f"✅ Catalog items added: {items_added}")
        print(f"✅ Patron preferences updated: {prefs_added}")
        print("\nAll extended i18n content has been seeded successfully!")
        print("=" * 80 + "\n")

        return 0

    except Exception as e:
        print(f"\n✗ Error during seeding: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
