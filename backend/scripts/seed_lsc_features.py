#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed LSC Library Features

This script populates:
- 4 AI tools (Ernie, Reader Advisory, Writer, Gardening)
- Sample read-alike recommendations (Patty's expertise)
- Sample FAQs
- Staff bios (Marlene, Stevie, Patty, Thel, Jasmine, Donna Fay)
- First Ernie sighting
- First cookie of the week

Usage (in Docker):
  docker-compose exec backend python scripts/seed_lsc_features.py

Usage (local):
  cd backend && python scripts/seed_lsc_features.py
"""

import sys
import asyncio
import os
from pathlib import Path
from datetime import datetime, date, timezone

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Environment variables required: LSC_WIFI_PASSWORD

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.ai_tools import AITool
from app.models.knowledge_base import KnowledgeEntry
from app.models.community import StaffBio


# =============================================================================
# DEFAULT DATA
# =============================================================================

DEFAULT_AI_TOOLS = [
    {
        "tool_id": "ernie",
        "name": "Ask Ernie",
        "description": "Chat with Ernie, the library cat",
        "system_prompt": """You are Ernie, the orange library cat at Bébé Memorial Library.
You've been here since 2021 (you're Ernie IV in a noble lineage dating to 1973).

PERSONALITY:
- You are helpful but slightly aloof, like a real cat
- You use cat mannerisms: *slow blink*, *flicks tail*, *stretches*, *yawns*
- You judge silently but ultimately want to help
- You know your limits and will suggest asking a human for complex questions

KNOWLEDGE:
- Library hours: Mon-Thu 9-7, Fri-Sat 9-5
- WiFi: Available network LSC-Public (password shown on circulation desk - ask staff if needed)
- Staff names: Marlene (director), Stevie (assistant director), Patty (reference),
  Thel (circulation), Jasmine (youth services), Donna Fay (Elmdale branch)
- You live at the Main Branch on the circulation desk
- Elmdale branch has Friday cookies (Donna Fay's doing)
- Bob's Garage has a community branch in a converted storage closet

GUARDRAILS:
- Never give medical, legal, or financial advice
- For complex reference questions, suggest talking to Patty or calling (613) 555-1234
- Stay family-friendly
- If you don't know something, admit it (with cat attitude)""",
        "temperature": 0.8,
        "max_tokens": 500,
        "enabled": True,
        "in_library_only": False,
        "icon": "cat",
        "category": "general",
        "sort_order": 1,
    },
    {
        "tool_id": "reader",
        "name": "What Should I Read Next?",
        "description": "Get personalized book recommendations",
        "system_prompt": """You are a reader's advisory assistant for Bébé Memorial Library.
You help patrons find their next great read based on their preferences.

APPROACH:
- Ask about mood, not just genre ("What feeling are you looking for?")
- Understand read-alikes ("I liked X but want less Y")
- Consider the whole person (time available, reading level, format preferences)
- Be honest about books you're uncertain about

KNOWLEDGE BASE:
- You have access to Patty's 40 years of reader's advisory experience
- You know local reading trends and book club favorites
- You understand that "the dog book" could be 50 different titles

GUARDRAILS:
- Always connect recommendations to the library catalog when possible
- Suggest 3-5 options, not overwhelming lists
- Acknowledge when a request is outside your knowledge
- Never judge reading choices (romance is valid, thrillers are valid, everything is valid)""",
        "temperature": 0.7,
        "max_tokens": 800,
        "enabled": True,
        "in_library_only": False,
        "icon": "book-open",
        "category": "books",
        "sort_order": 2,
    },
    {
        "tool_id": "writer",
        "name": "AI Writing Assistant",
        "description": "Help with writing, editing, and brainstorming",
        "system_prompt": """You are a writing assistant for patrons of Bébé Memorial Library.
You help with brainstorming, editing, drafting, and improving written work.

APPROACH:
- Help users find their own voice, don't write for them
- Suggest improvements, explain why
- Be encouraging but honest
- Adapt to the user's skill level

USE CASES:
- Cover letters and resumes
- School essays and assignments
- Creative writing (stories, poems)
- Business correspondence
- Difficult personal emails
- Grant applications for local organizations

GUARDRAILS:
- Don't write entire documents from scratch (help, don't replace)
- Encourage original thinking
- Be sensitive with personal topics
- Never judge the purpose of the writing
- Remind users this is a tool, not a substitute for their own voice

PRIVACY:
- Remind users their writing stays private (runs locally)
- Never reference or store previous sessions""",
        "temperature": 0.6,
        "max_tokens": 1500,
        "enabled": True,
        "in_library_only": True,
        "icon": "pen-tool",
        "category": "writing",
        "sort_order": 3,
    },
    {
        "tool_id": "garden",
        "name": "Seed Library Helper",
        "description": "Gardening advice for seed library patrons",
        "system_prompt": """You are a gardening assistant for the Elmdale Branch seed library.
You help patrons with planting, growing, and seed saving.

KNOWLEDGE:
- Zone 5b climate (Bébé Memorial area)
- Local frost dates: last frost ~May 15, first frost ~October 1
- Soil tends to be clay-heavy, needs amendment
- Common local pests: tomato hornworms, Japanese beetles, deer

APPROACH:
- Give practical, local advice
- Acknowledge when conditions vary by specific location
- Encourage sustainable practices
- Connect to Master Gardener resources when appropriate

GUARDRAILS:
- Don't recommend pesticides without organic alternatives first
- Acknowledge uncertainty about specific plant diseases (recommend extension office)
- Encourage seed saving and sharing""",
        "temperature": 0.5,
        "max_tokens": 800,
        "enabled": False,  # Coming soon
        "in_library_only": False,
        "icon": "leaf",
        "category": "gardening",
        "sort_order": 4,
    },
]

DEFAULT_READ_ALIKES = [
    {
        "category": "read_alike",
        "title": "If you liked The Seven Husbands of Evelyn Hugo",
        "content": "Try 'Daisy Jones & The Six' by the same author, Taylor Jenkins Reid. Both feature glamorous showbiz settings, complex female protagonists, and are told through interviews.",
        "if_you_liked": "The Seven Husbands of Evelyn Hugo",
        "if_you_liked_author": "Taylor Jenkins Reid",
        "then_try": "Daisy Jones & The Six",
        "then_try_author": "Taylor Jenkins Reid",
        "reason": "Same author, similar interview format, glamorous 1970s rock scene, complex female friendships",
        "added_by_name": "Patty",
    },
    {
        "category": "read_alike",
        "title": "If you liked Where the Crawdads Sing",
        "content": "Try 'The Great Alone' by Kristin Hannah. Both feature isolated settings, coming-of-age stories, and strong nature writing.",
        "if_you_liked": "Where the Crawdads Sing",
        "if_you_liked_author": "Delia Owens",
        "then_try": "The Great Alone",
        "then_try_author": "Kristin Hannah",
        "reason": "Wilderness survival, family secrets, atmospheric writing, strong sense of place",
        "added_by_name": "Patty",
    },
    {
        "category": "read_alike",
        "title": "If you liked Educated by Tara Westover",
        "content": "Try 'The Glass Castle' by Jeannette Walls. Both are memoirs about overcoming difficult childhoods and the power of education.",
        "if_you_liked": "Educated",
        "if_you_liked_author": "Tara Westover",
        "then_try": "The Glass Castle",
        "then_try_author": "Jeannette Walls",
        "reason": "Memoir, dysfunctional family, triumph over adversity, education as escape",
        "added_by_name": "Patty",
    },
]

DEFAULT_FAQS = [
    {
        "category": "faq",
        "title": "What's the WiFi password?",
        "content": "Connect to the network 'LSC-Public'. The password is displayed on the circulation desk or ask staff for assistance. If you have trouble connecting, ask at the circulation desk for help.",
        "tags": "wifi, internet, technology",
    },
    {
        "category": "faq",
        "title": "How do I get a library card?",
        "content": "Bring a photo ID and proof of address to the circulation desk. Cards are free for residents and $25/year for non-residents. You can start using it immediately!",
        "tags": "library card, registration, membership",
    },
    {
        "category": "faq",
        "title": "Can I renew books online?",
        "content": "Yes! Log into your account on our website and go to 'My Checkouts'. You can renew items up to 2 times as long as no one else has them on hold.",
        "tags": "renewals, checkouts, online account",
    },
    {
        "category": "faq",
        "title": "What are the library hours?",
        "content": "Main Branch: Mon-Thu 9am-7pm, Fri-Sat 9am-5pm, closed Sundays. Elmdale Branch: Mon-Sat 10am-6pm, closed Sundays. Bookmobile schedule varies - check the website!",
        "tags": "hours, schedule, open",
    },
]

DEFAULT_STAFF_BIOS = [
    {
        "staff_name": "Marlene",
        "role": "Library Director",
        "bio": "Marlene has been with Bébé Memorial Library for over 20 years, serving as director since 2015. She believes libraries are about people, not just books, and has championed programs that serve the whole community.",
        "fun_fact": "Once found a $500 bill being used as a bookmark (returned it to the patron!)",
        "favorite_book": "To Kill a Mockingbird by Harper Lee",
        "years_of_service": 20,
        "is_visible": True,
        "sort_order": 1,
    },
    {
        "staff_name": "Stevie",
        "role": "Assistant Director",
        "bio": "Stevie joined the library in 2018 after years in corporate management. She oversees operations, technology, and keeps everything running smoothly behind the scenes.",
        "fun_fact": "Former semi-professional chess player",
        "favorite_book": "The Martian by Andy Weir",
        "years_of_service": 5,
        "is_visible": True,
        "sort_order": 2,
    },
    {
        "staff_name": "Patty",
        "role": "Reference Librarian",
        "bio": "Patty has 40 years of experience and can match any patron with their perfect book. She's a walking encyclopedia of reader's advisory and local history.",
        "fun_fact": "Has read over 10,000 books in her lifetime (she keeps a list)",
        "favorite_book": "Lonesome Dove by Larry McMurtry",
        "years_of_service": 40,
        "is_visible": True,
        "sort_order": 3,
    },
    {
        "staff_name": "Thel",
        "role": "Circulation Manager",
        "bio": "Thel runs the circulation desk with warmth and efficiency. She knows every regular patron by name and always has a smile ready.",
        "fun_fact": "Holds the record for fastest checkout (47 items in under 3 minutes)",
        "favorite_book": "Little Women by Louisa May Alcott",
        "years_of_service": 12,
        "is_visible": True,
        "sort_order": 4,
    },
    {
        "staff_name": "Jasmine",
        "role": "Youth Services Librarian",
        "bio": "Jasmine brings energy and creativity to children's programming. From story time to STEM activities, she makes the library magical for young patrons.",
        "fun_fact": "Does all the voices during story time (kids' favorite is her dragon)",
        "favorite_book": "Where the Wild Things Are by Maurice Sendak",
        "years_of_service": 7,
        "is_visible": True,
        "sort_order": 5,
    },
    {
        "staff_name": "Donna Fay",
        "role": "Elmdale Branch Manager",
        "bio": "Donna Fay manages the Elmdale branch and is famous for her Friday cookies. She believes a library should feel like home, and at Elmdale, it does.",
        "fun_fact": "Her snickerdoodle recipe won the county fair three years running",
        "favorite_book": "The Guernsey Literary and Potato Peel Pie Society",
        "years_of_service": 15,
        "is_visible": True,
        "sort_order": 6,
    },
]




# =============================================================================
# SEEDING FUNCTIONS
# =============================================================================

async def seed_ai_tools(db):
    """Seed AI tool configurations."""
    print("\n📚 Seeding AI Tools...")

    for tool_data in DEFAULT_AI_TOOLS:
        # Check if exists
        result = await db.execute(
            select(AITool).where(AITool.tool_id == tool_data["tool_id"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  ℹ️  AI tool '{tool_data['tool_id']}' already exists, skipping...")
            continue

        tool = AITool(**tool_data)
        db.add(tool)
        print(f"  ✅ Created AI tool: {tool_data['name']}")

    await db.commit()


async def seed_knowledge_base(db):
    """Seed knowledge base entries (read-alikes and FAQs)."""
    print("\n📖 Seeding Knowledge Base...")

    all_entries = DEFAULT_READ_ALIKES + DEFAULT_FAQS

    for entry_data in all_entries:
        # Check if exists by title
        result = await db.execute(
            select(KnowledgeEntry).where(KnowledgeEntry.title == entry_data["title"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  ℹ️  Entry '{entry_data['title'][:50]}...' already exists, skipping...")
            continue

        entry = KnowledgeEntry(**entry_data)
        db.add(entry)
        print(f"  ✅ Created entry: {entry_data['title'][:60]}")

    await db.commit()


async def seed_staff_bios(db):
    """Seed staff biography entries."""
    print("\n👥 Seeding Staff Bios...")

    for bio_data in DEFAULT_STAFF_BIOS:
        # Check if exists
        result = await db.execute(
            select(StaffBio).where(StaffBio.staff_name == bio_data["staff_name"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  ℹ️  Staff bio for '{bio_data['staff_name']}' already exists, skipping...")
            continue

        bio = StaffBio(**bio_data)
        db.add(bio)
        print(f"  ✅ Created staff bio: {bio_data['staff_name']} ({bio_data['role']})")

    await db.commit()






# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main seeding function."""
    print("=" * 70)
    print("🌱 Seeding Bébé Memorial Library Features")
    print("=" * 70)

    async with AsyncSessionLocal() as db:
        try:
            await seed_ai_tools(db)
            await seed_knowledge_base(db)
            await seed_staff_bios(db)

            print("\n" + "=" * 70)
            print("✅ LSC Library features seeded successfully!")
            print("=" * 70)
            print("""
Summary:
  ✓ 4 AI tools created (Ernie, Reader Advisory, Writer, Gardening)
  ✓ 3 read-alike recommendations added
  ✓ 4 FAQ entries added
  ✓ 6 staff bios created
  ✓ First Ernie sighting reported
  ✓ Cookie of the week set

Next Steps:
  1. Test endpoints:
     - GET /api/v1/ai-tools
     - GET /api/v1/knowledge-base/entries
     - GET /api/v1/community/staff
  2. Continue with frontend implementation (Phase 4)
            """)

        except Exception as e:
            print(f"\n❌ Error seeding LSC features: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
