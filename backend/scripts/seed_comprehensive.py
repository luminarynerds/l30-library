#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive LSC Library Data Seeder - 2026 Edition
Seeds high-impact data for immediate visual impact
"""
import sys, os, json
from pathlib import Path
from datetime import datetime, timedelta, timezone, date, time
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Environment variable required: LSC_WIFI_PASSWORD

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.models.event import Event
from app.models.announcements import Announcement
from app.models.ai_tools import AITool
from app.models.community import StaffBio

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@database:5432/lsc_library")
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 2026 Diverse Catalog - Showcasing variety
CATALOG_ITEMS = [
    # Contemporary Fiction - Diverse Authors
    {"title": "The Ministry of Time", "author": "Kaliane Bradley", "item_type": "book", "isbn": "9781668049495",
     "publisher": "Avid Reader Press", "publication_year": 2024, "subjects": "Science Fiction, Time Travel, LGBTQ+",
     "description": "A time-travel romance exploring colonialism and queer identity.", "page_count": 368, "dewey_decimal": "823.92"},

    {"title": "All Fours", "author": "Miranda July", "item_type": "book", "isbn": "9780593732595",
     "publisher": "Riverhead Books", "publication_year": 2024, "subjects": "Fiction, Women's Fiction",
     "description": "A woman upends her life in a roadside motel.", "page_count": 320, "dewey_decimal": "813.6"},

    {"title": "The Serviceberry", "author": "Robin Wall Kimmerer", "item_type": "book", "isbn": "9781982187866",
     "publisher": "Scribner", "publication_year": 2024, "subjects": "Nature, Indigenous Knowledge, Philosophy",
     "description": "From gift economies to reciprocity with the natural world.", "page_count": 160, "dewey_decimal": "304.2"},

    # Neurodivergent Perspectives (LSC specialty)
    {"title": "Unmasking Autism", "author": "Devon Price", "item_type": "book", "isbn": "9780593235232",
     "publisher": "Harmony", "publication_year": 2022, "subjects": "Autism, Neurodiversity, Mental Health",
     "description": "Discovering the new faces of neurodiversity.", "page_count": 288, "dewey_decimal": "616.8588"},

    {"title": "A Different Kind of Normal", "author": "Abigail Balfe", "item_type": "book", "isbn": "9781787636170",
     "publisher": "Icon Books", "publication_year": 2023, "subjects": "ADHD, Neurodiversity, Memoir",
     "description": "Understanding ADHD from personal experience.", "page_count": 256, "dewey_decimal": "616.8589"},

    # Mystery & Thriller
    {"title": "The Women", "author": "Kristin Hannah", "item_type": "book", "isbn": "9781250178633",
     "publisher": "St. Martin's Press", "publication_year": 2024, "subjects": "Historical Fiction, Vietnam War, Women",
     "description": "Women who served in Vietnam and came home to silence.", "page_count": 480, "dewey_decimal": "813.54"},

    {"title": "The Housemaid", "author": "Freida McFadden", "item_type": "book", "isbn": "9781538742570",
     "publisher": "Grand Central", "publication_year": 2022, "subjects": "Thriller, Mystery, Suspense",
     "description": "A psychological thriller about secrets and survival.", "page_count": 336, "dewey_decimal": "813.6"},

    # Audiobooks - Popular Titles
    {"title": "Tomorrow, and Tomorrow, and Tomorrow", "author": "Gabrielle Zevin", "item_type": "audiobook",
     "isbn": "9780593470961", "publisher": "Random House Audio", "publication_year": 2022,
     "subjects": "Fiction, Gaming, Friendship", "description": "Two game designers navigate love and creativity."},

    {"title": "Demon Copperhead", "author": "Barbara Kingsolver", "item_type": "audiobook", "isbn": "9780063251939",
     "publisher": "Harper Audio", "publication_year": 2022, "subjects": "Fiction, Appalachia, Coming-of-age",
     "description": "Pulitzer Prize winner about a boy in foster care."},

    # Non-Fiction - Timely Topics
    {"title": "The Anxious Generation", "author": "Jonathan Haidt", "item_type": "book", "isbn": "9780593655030",
     "publisher": "Penguin Press", "publication_year": 2024, "subjects": "Psychology, Technology, Youth Mental Health",
     "description": "How phone-based childhood is harming young people.", "page_count": 400, "dewey_decimal": "155.5"},

    {"title": "The Wager", "author": "David Grann", "item_type": "book", "isbn": "9780385534260",
     "publisher": "Doubleday", "publication_year": 2023, "subjects": "History, Maritime, Adventure",
     "description": "A shipwreck, mutiny, and murder in the 18th century.", "page_count": 352, "dewey_decimal": "910.4"},

    # Graphic Novels & Comics
    {"title": "Gender Queer", "author": "Maia Kobabe", "item_type": "book", "isbn": "9781549303005",
     "publisher": "Oni Press", "publication_year": 2019, "subjects": "Memoir, LGBTQ+, Gender Identity, Graphic Novel",
     "description": "A memoir exploring gender identity and sexuality.", "page_count": 240, "dewey_decimal": "741.5"},

    {"title": "The Magic Fish", "author": "Trung Le Nguyen", "item_type": "book", "isbn": "9781984851598",
     "publisher": "Random House Graphic", "publication_year": 2020, "subjects": "Graphic Novel, LGBTQ+, Immigration",
     "description": "A boy uses fairy tales to come out to his parents.", "page_count": 224, "dewey_decimal": "741.5"},

    # DVDs - Educational & Entertainment
    {"title": "Everything Everywhere All at Once", "author": "Daniels", "item_type": "dvd", "publisher": "A24",
     "publication_year": 2022, "subjects": "Film, Science Fiction, Family Drama",
     "description": "Oscar winner exploring multiverse and family."},

    {"title": "Autism in Love", "author": "Matt Fuller", "item_type": "dvd", "publisher": "Kino Lorber",
     "publication_year": 2015, "subjects": "Documentary, Autism, Relationships",
     "description": "Four adults on the autism spectrum navigate love."},

    # Canadian Authors
    {"title": "The Strangest Thing", "author": "Tessa McWatt", "item_type": "book", "isbn": "9780735245433",
     "publisher": "Viking", "publication_year": 2023, "subjects": "Canadian Fiction, Identity, Science",
     "description": "A woman explores her multiracial identity through genetics.", "dewey_decimal": "813.6"},

    # Children's & YA
    {"title": "A Kind of Spark", "author": "Elle McNicoll", "item_type": "book", "isbn": "9781524773571",
     "publisher": "Crown Books", "publication_year": 2020, "subjects": "Middle Grade, Autism, Historical Fiction",
     "description": "An autistic girl campaigns for a memorial to accused witches.", "page_count": 240, "dewey_decimal": "823.92"},

    {"title": "The Poet X", "author": "Elizabeth Acevedo", "item_type": "book", "isbn": "9780062662804",
     "publisher": "HarperTeen", "publication_year": 2018, "subjects": "YA, Poetry, Dominican American, Coming-of-age",
     "description": "A girl finds her voice through slam poetry.", "page_count": 357, "dewey_decimal": "811.6"},

    # Local Interest / Small Town Life
    {"title": "The Pull of the Stars", "author": "Emma Donoghue", "item_type": "book", "isbn": "9780316499019",
     "publisher": "Little, Brown", "publication_year": 2020, "subjects": "Historical Fiction, Pandemic, Ireland",
     "description": "A nurse during the 1918 flu pandemic.", "page_count": 304, "dewey_decimal": "813.6"},

    # Indigenous Authors
    {"title": "The Marrow Thieves", "author": "Cherie Dimaline", "item_type": "book", "isbn": "9781770864863",
     "publisher": "DCB", "publication_year": 2017, "subjects": "YA, Indigenous, Dystopian, Canadian",
     "description": "Indigenous people hunted for their bone marrow in a dystopian future.", "dewey_decimal": "813.6"},

    # Wellness & Self-Help
    {"title": "How to Keep House While Drowning", "author": "KC Davis", "item_type": "book", "isbn": "9781668002841",
     "publisher": "Simon Element", "publication_year": 2022, "subjects": "Self-Help, Mental Health, Home Management",
     "description": "Gentle approach to care tasks for those struggling.", "page_count": 176, "dewey_decimal": "640"},

    # Poetry
    {"title": "The Carrying", "author": "Ada Limón", "item_type": "book", "isbn": "9781571315199",
     "publisher": "Milkweed", "publication_year": 2018, "subjects": "Poetry, Nature, Women",
     "description": "National Book Critics Circle Award winner.", "page_count": 112, "dewey_decimal": "811.6"},

    # Business & Technology
    {"title": "The Age of AI", "author": "Henry Kissinger, Eric Schmidt, Daniel Huttenlocher", "item_type": "book",
     "isbn": "9780316273800", "publisher": "Little, Brown", "publication_year": 2021,
     "subjects": "Technology, Artificial Intelligence, Future", "page_count": 272, "dewey_decimal": "006.3"},

    # Cookbooks
    {"title": "Salt, Fat, Acid, Heat", "author": "Samin Nosrat", "item_type": "book", "isbn": "9781476753836",
     "publisher": "Simon & Schuster", "publication_year": 2017, "subjects": "Cooking, Food Science",
     "description": "Mastering the elements of good cooking.", "page_count": 480, "dewey_decimal": "641.5"},

    # Games
    {"title": "Wingspan", "author": "Elizabeth Hargrave", "item_type": "game", "publisher": "Stonemaier Games",
     "publication_year": 2019, "subjects": "Board Game, Birds, Strategy",
     "description": "Award-winning bird-themed engine-building game."},
]

# Helper: create a UTC datetime from a desired US Central display time.
# Input hour/minute is the intended Central Time. Stored as UTC (CT + 5h in CDT, +6h in CST).
# Using +5 for CDT (summer) since most library events are spring/summer.
_today = date.today()
def _event_dt(days_offset: int, hour: int, minute: int = 0) -> datetime:
    """Create event datetime from Central Time input, stored as UTC."""
    target_date = _today + timedelta(days=days_offset)
    utc_hour = hour + 5  # CDT is UTC-5
    return datetime.combine(target_date, time(0, minute), tzinfo=timezone.utc) + timedelta(hours=utc_hour)

EVENTS = [
    {"title": "Neurodivergent Book Club: Unmasking Autism Discussion", "event_type": "book_club",
     "start_time": _event_dt(7, 18, 30),
     "end_time": _event_dt(7, 20, 0),
     "location": "Main Branch Meeting Room", "max_participants": 15,
     "description": "Monthly discussion group for neurodivergent adults. This month: Devon Price's Unmasking Autism.",
     "image_url": "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=600&h=400&fit=crop&sig=1",
     "is_published": True, "requires_registration": True},

    {"title": "Friday Cookie Social @ Elmdale", "event_type": "social",
     "start_time": _event_dt(4, 14, 0),
     "end_time": _event_dt(4, 16, 0),
     "location": "Elmdale Branch", "max_participants": 50,
     "description": "Donna Fay's famous Friday cookies! This week: double chocolate chip. Come for treats, stay for community.",
     "image_url": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=600&h=400&fit=crop&sig=2",
     "is_published": True, "requires_registration": False},

    {"title": "Tech Help Tuesday: AI Literacy", "event_type": "workshop",
     "start_time": _event_dt(9, 14, 0),
     "end_time": _event_dt(9, 16, 0),
     "location": "Main Branch Computer Lab", "max_participants": 12,
     "description": "Learn about AI tools, ChatGPT, and how to use them safely. Beginner-friendly!",
     "image_url": "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=600&h=400&fit=crop&sig=3",
     "is_published": True, "requires_registration": True},

    {"title": "Story Time: Sensory-Friendly Session", "event_type": "children",
     "start_time": _event_dt(5, 10, 30),
     "end_time": _event_dt(5, 11, 15),
     "location": "Main Branch Children's Area", "max_participants": 20,
     "description": "Stories, songs, and activities in a calm environment. Lights dimmed, volume low, movement welcome.",
     "image_url": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=600&h=400&fit=crop&sig=4",
     "is_published": True, "requires_registration": False},

    {"title": "Board Game Night", "event_type": "social",
     "start_time": _event_dt(12, 18, 0),
     "end_time": _event_dt(12, 21, 0),
     "location": "Main Branch", "max_participants": 30,
     "description": "Try games from our collection! This week featuring Wingspan, Catan, and Ticket to Ride.",
     "image_url": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=600&h=400&fit=crop&sig=5",
     "is_published": True, "requires_registration": False},

    {"title": "Writers Circle", "event_type": "workshop",
     "start_time": _event_dt(14, 18, 30),
     "end_time": _event_dt(14, 20, 0),
     "location": "Main Branch", "max_participants": 15,
     "description": "Share your work and get supportive feedback. All genres welcome.",
     "image_url": "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=600&h=400&fit=crop&sig=6",
     "is_published": True, "requires_registration": True},

    # AI Tools Class Series - linked from Digital Resources page
    {"title": "AI Tools Class: Introduction to ChatGPT", "event_type": "workshop",
     "start_time": _event_dt(10, 14, 0),
     "end_time": _event_dt(10, 16, 0),
     "location": "Main Branch Computer Lab", "max_participants": 12,
     "description": "Learn the basics of ChatGPT and how to write effective prompts. No experience necessary. We'll cover what AI can and can't do, privacy considerations, and hands-on practice.",
     "image_url": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=600&h=400&fit=crop&sig=7",
     "is_published": True, "requires_registration": True,
     "series_id": "ai-tools-class", "series_name": "AI Tools Class"},

    {"title": "AI Tools Class: Building Custom GPTs", "event_type": "workshop",
     "start_time": _event_dt(17, 14, 0),
     "end_time": _event_dt(17, 16, 0),
     "location": "Main Branch Computer Lab", "max_participants": 12,
     "description": "Create your own custom ChatGPT assistants for specific tasks. Build a research helper, writing coach, or any tool you need. Bring your ideas!",
     "image_url": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=600&h=400&fit=crop&sig=8",
     "is_published": True, "requires_registration": True,
     "series_id": "ai-tools-class", "series_name": "AI Tools Class"},

    {"title": "AI Tools Class: AI for Job Seekers", "event_type": "workshop",
     "start_time": _event_dt(24, 14, 0),
     "end_time": _event_dt(24, 16, 0),
     "location": "Main Branch Computer Lab", "max_participants": 12,
     "description": "Use AI tools to polish your resume, prepare for interviews, and research companies. Practical skills for your job search. Bring your resume if you have one.",
     "image_url": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=600&h=400&fit=crop&sig=9",
     "is_published": True, "requires_registration": True,
     "series_id": "ai-tools-class", "series_name": "AI Tools Class"},

    {"title": "AI Tools Class: Fact-Checking and AI Literacy", "event_type": "workshop",
     "start_time": _event_dt(31, 14, 0),
     "end_time": _event_dt(31, 16, 0),
     "location": "Main Branch Computer Lab", "max_participants": 12,
     "description": "Learn to spot AI-generated content, verify information, and use AI responsibly. Essential skills for navigating the modern information landscape.",
     "image_url": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=600&h=400&fit=crop&sig=10",
     "is_published": True, "requires_registration": True,
     "series_id": "ai-tools-class", "series_name": "AI Tools Class"},

    # Sports Cards & WNBA Events
    {"title": "Sports Cards Collectors Meetup", "event_type": "social", "category": "Sports Cards",
     "start_time": _event_dt(3, 15, 0),
     "end_time": _event_dt(3, 17, 0),
     "location": "Main Branch Community Room", "max_participants": 40,
     "audience": "All Ages",
     "description": "Connect with other sports card collectors! Buy, sell, and trade cards. Bring your collections and negotiate your best deals. No professional dealers please.",
     "image_url": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=600&h=400&fit=crop&sig=11",
     "is_published": True, "requires_registration": False},

    {"title": "WNBA Watch Party: Championship Game", "event_type": "social", "category": "WNBA",
     "start_time": _event_dt(8, 19, 0),
     "end_time": _event_dt(8, 22, 0),
     "location": "Main Branch Theater", "max_participants": 100,
     "audience": "Adults",
     "description": "Join us for the WNBA Championship game! Snacks provided. Come early for good seating. Let's celebrate the best basketball on earth!",
     "image_url": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=600&h=400&fit=crop&sig=12",
     "is_published": True, "requires_registration": False},

    {"title": "Sports Card Grading Workshop", "event_type": "workshop", "category": "Sports Cards",
     "start_time": _event_dt(15, 14, 0),
     "end_time": _event_dt(15, 16, 0),
     "location": "Main Branch Meeting Room", "max_participants": 20,
     "audience": "Adults",
     "description": "Learn the basics of card grading! Understand condition grades (PSA, Beckett standards) and how they affect card value. Bring cards to evaluate.",
     "image_url": "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=600&h=400&fit=crop&sig=13",
     "is_published": True, "requires_registration": True},

    {"title": "WNBA Trivia Night", "event_type": "social", "category": "WNBA",
     "start_time": _event_dt(22, 18, 0),
     "end_time": _event_dt(22, 20, 0),
     "location": "Main Branch", "max_participants": 50,
     "audience": "All Ages",
     "description": "Test your WNBA knowledge! Teams compete for prizes. Hosted by a librarian who's been watching since the league began. All skill levels welcome.",
     "image_url": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=600&h=400&fit=crop&sig=14",
     "is_published": True, "requires_registration": True},
]

ANNOUNCEMENTS = [
    {"title": "Extended Sunday Hours!", "content": "Great news! Main branch now open Sundays 12-5pm. Elmdale branch adding Thursday evening hours 6-8pm.",
     "priority": "urgent", "is_published": True, "start_date": datetime.now(timezone.utc),
     "end_date": datetime.now(timezone.utc) + timedelta(days=30)},

    {"title": "Seed Library Now Open at Elmdale", "content": "Spring planting season! Borrow seeds, grow plants, save seeds, return. Zone 5b varieties available now.",
     "priority": "important", "is_published": True, "start_date": datetime.now(timezone.utc),
     "end_date": datetime.now(timezone.utc) + timedelta(days=90)},

    {"title": "Wi-Fi Upgrade Complete", "content": "Faster speeds throughout the building! Network name unchanged (LSC-Public), same password (use the password shown on the circulation desk or ask staff).",
     "priority": "normal", "is_published": True, "start_date": datetime.now(timezone.utc) - timedelta(days=2),
     "end_date": datetime.now(timezone.utc) + timedelta(days=14)},
]

AI_TOOLS = [
    {"tool_id": "ernie", "name": "Ask Ernie", "description": "Chat with Ernie, the library cat",
     "system_prompt": "You are Ernie, the orange library cat at Bébé Memorial Library. You're helpful but aloof. Use cat mannerisms. Know basic library info but suggest asking staff for complex questions.",
     "temperature": 0.8, "max_tokens": 500, "enabled": True, "in_library_only": False,
     "icon": "cat", "category": "general", "sort_order": 1},

    {"tool_id": "reader", "name": "What Should I Read Next?", "description": "Get personalized book recommendations",
     "system_prompt": "You are a reader's advisory assistant. Ask about mood, not just genre. Consider the whole person. Suggest 3-5 options.",
     "temperature": 0.7, "max_tokens": 800, "enabled": True, "in_library_only": False,
     "icon": "book-open", "category": "books", "sort_order": 2},
]

STAFF_BIOS = [
    {"staff_name": "Marlene", "role": "Library Director", "years_of_service": 20, "is_visible": True, "sort_order": 1,
     "bio": "Marlene believes libraries are about people, not just books. She champions programs serving the whole community.",
     "fun_fact": "Once found a $500 bill being used as a bookmark (returned it!)", "favorite_book": "To Kill a Mockingbird"},

    {"staff_name": "Patty", "role": "Reference Librarian", "years_of_service": 40, "is_visible": True, "sort_order": 2,
     "bio": "Patty can match any patron with their perfect book. She's a walking encyclopedia of reader's advisory.",
     "fun_fact": "Has read over 10,000 books (she keeps a list)", "favorite_book": "Lonesome Dove"},

    {"staff_name": "Donna Fay", "role": "Elmdale Branch Manager", "years_of_service": 15, "is_visible": True, "sort_order": 3,
     "bio": "Famous for Friday cookies. She believes a library should feel like home, and at Elmdale, it does.",
     "fun_fact": "Her snickerdoodle recipe won the county fair three years running", "favorite_book": "The Guernsey Literary and Potato Peel Pie Society"},
]

async def seed_all():
    print("=" * 70)
    print("🌱 LSC Library Comprehensive Seeder - 2026 Edition")
    print("=" * 70)

    try:
        # Catalog Items
        print("\n📚 Seeding Catalog Items...")
        async with async_session() as session:
            added = 0
            for idx, item in enumerate(CATALOG_ITEMS, 1):
                r = await session.execute(text("SELECT id FROM catalog_items WHERE title = :t"), {"t": item["title"]})
                if r.fetchone():
                    continue

                await session.execute(text(
                    "INSERT INTO catalog_items (title, author, item_type, status, isbn, publisher, publication_year, description, subjects, page_count, dewey_decimal, location, barcode, cataloging_status, share_count, sensitivity_level, total_checkouts) "
                    "VALUES (:t, :a, :it, 'available', :i, :pb, :y, :d, :s, :p, :dw, 'Main Branch', :b, 'cataloged', 0, 'public', 0)"
                ), {
                    "t": item["title"],
                    "a": item.get("author"),
                    "it": item["item_type"],
                    "i": item.get("isbn"),
                    "pb": item.get("publisher"),
                    "y": item.get("publication_year"),
                    "d": item.get("description"),
                    "s": item.get("subjects"),
                    "p": item.get("page_count"),
                    "dw": item.get("dewey_decimal"),
                    "b": f"LSC{1000 + idx:06d}"
                })
                added += 1
            await session.commit()
            print(f"  ✅ Added {added} catalog items")

        # Events
        print("\n📅 Seeding Events...")
        async with async_session() as session:
            added = 0
            for event_data in EVENTS:
                r = await session.execute(text("SELECT id FROM events WHERE title = :t"), {"t": event_data["title"]})
                if r.fetchone():
                    continue

                await session.execute(text(
                    "INSERT INTO events (title, description, start_time, end_time, location, audience, category, event_type, max_attendees, registration_required, is_published, series_id, series_name, share_count, image_url) "
                    "VALUES (:t, :d, :st, :et, :l, :a, :c, :etype, :m, :r, true, :sid, :sn, 0, :img)"
                ), {
                    "t": event_data["title"],
                    "d": event_data["description"],
                    "st": event_data["start_time"],
                    "et": event_data["end_time"],
                    "l": event_data["location"],
                    "a": event_data.get("audience", "All Ages"),
                    "c": event_data.get("category", event_data["event_type"]),  # Use category field if provided, otherwise use event_type
                    "etype": event_data["event_type"],  # events.event_type is NOT NULL at the DB level
                    "m": event_data["max_participants"],
                    "r": event_data.get("requires_registration", False),
                    "sid": event_data.get("series_id"),
                    "sn": event_data.get("series_name"),
                    "img": event_data.get("image_url")
                })
                added += 1
            await session.commit()
            print(f"  ✅ Added {added} events")

        # Announcements
        print("\n📢 Seeding Announcements...")
        async with async_session() as session:
            added = 0
            for ann_data in ANNOUNCEMENTS:
                r = await session.execute(text("SELECT id FROM announcements WHERE title = :t"), {"t": ann_data["title"]})
                if r.fetchone():
                    continue

                await session.execute(text(
                    "INSERT INTO announcements (title, content, category, priority, status, active, pinned, starts_at, ends_at, show_on_homepage, show_banner, dismissible) "
                    "VALUES (:t, :c, :cat, :p, :st, true, false, :sd, :ed, true, :sb, true)"
                ), {
                    "t": ann_data["title"],
                    "c": ann_data["content"],
                    "cat": ann_data.get("category", "general"),
                    "p": ann_data["priority"],
                    # announcements.category/status/pinned are NOT NULL with
                    # no DB-level default (only an ORM-level
                    # Column(default=...), which a raw SQL INSERT bypasses)
                    # -- publish immediately so seeded announcements
                    # actually show up.
                    "st": ann_data.get("status", "published"),
                    "sd": ann_data.get("start_date"),
                    "ed": ann_data.get("end_date"),
                    "sb": ann_data["priority"] in ["urgent", "important"]
                })
                added += 1
            await session.commit()
            print(f"  ✅ Added {added} announcements")

        # AI Tools, Staff Bios, and Community Features
        # Skipped here - will be seeded by seed_lsc_features.py
        print("\n⏭️ Skipping AI Tools, Staff Bios, and Community Features (use seed_lsc_features.py)")

        # Learning/Training Courses
        print("\n📖 Seeding Learning Courses...")
        learning_courses_added = 0
        async with async_session() as session:
            # Check if courses already exist
            r = await session.execute(text("SELECT COUNT(*) FROM courses"))
            existing_count = r.scalar() or 0

            if existing_count == 0:
                # Seed Staff Training Course - Library Essentials
                await session.execute(text("""
                    INSERT INTO courses (title, description, access_level, lifecycle_stage, estimated_minutes, difficulty, sensory_warning, xp_reward)
                    VALUES (
                        'Library Essentials',
                        'A comprehensive introduction to working at Bébé Memorial Library. This course covers our values, daily operations, and patron service - all designed with neurodivergent-friendly practices in mind.',
                        'staff',
                        'published',
                        90,
                        'beginner',
                        'This course contains text-based content only. No flashing images, auto-playing videos, or sudden sounds. Take breaks as needed.',
                        250
                    )
                """))

                # Get course id
                r = await session.execute(text("SELECT id FROM courses WHERE title = 'Library Essentials'"))
                staff_course_id = r.scalar()

                # Module 1
                await session.execute(text("""
                    INSERT INTO modules (course_id, title, description, sort_order)
                    VALUES (:cid, 'Welcome to Bébé Memorial Library', 'Learn about our library''s mission, values, and commitment to neurodivergent-friendly service.', 1)
                """), {"cid": staff_course_id})

                r = await session.execute(text("SELECT id FROM modules WHERE course_id = :cid AND sort_order = 1"), {"cid": staff_course_id})
                mod1_id = r.scalar()

                # Module 1 Lessons
                await session.execute(text("""
                    INSERT INTO lessons (module_id, title, lesson_type, content, estimated_minutes, sensory_notes, xp_reward, sort_order)
                    VALUES (:mid, 'Our Library Values', 'article', '{"markdown": "# Our Library Values\\n\\nWelcome to the Bébé Memorial Library team. We are glad you are here.\\n\\n## Our Core Values\\n\\n### 1. Accessibility First\\nEvery decision we make considers accessibility.\\n\\n### 2. Patience is a Practice\\nWe do not rush patrons. Everyone processes information differently.\\n\\n### 3. Sensory Awareness\\nOur library considers sensory needs.\\n\\n### 4. Celebrating Different Minds\\nNeurodivergence is not a problem to solve - it is a valuable perspective we welcome."}'::jsonb, 10, 'Text only. Clear structure with headings.', 15, 1)
                """), {"mid": mod1_id})

                await session.execute(text("""
                    INSERT INTO lessons (module_id, title, lesson_type, content, estimated_minutes, sensory_notes, xp_reward, sort_order)
                    VALUES (:mid, 'Neurodivergent-Friendly Service', 'article', '{"markdown": "# Neurodivergent-Friendly Service\\n\\nPractical guidance for serving all patrons well.\\n\\n## Communication Best Practices\\n\\n### Be Clear and Direct\\nSay what you mean. Avoid idioms when possible.\\n\\n### Offer Choices, Not Open Questions\\nInstead of: How can I help you?\\nTry: Are you looking for a book, a computer, or something else?\\n\\n### Give Processing Time\\nPause after speaking. Do not fill silence immediately."}'::jsonb, 15, 'Text only. Structured format.', 20, 2)
                """), {"mid": mod1_id})

                # Module 2
                await session.execute(text("""
                    INSERT INTO modules (course_id, title, description, sort_order)
                    VALUES (:cid, 'Managing Your Workday', 'Practical strategies for time management, task prioritization, and maintaining your energy throughout shifts.', 2)
                """), {"cid": staff_course_id})

                r = await session.execute(text("SELECT id FROM modules WHERE course_id = :cid AND sort_order = 2"), {"cid": staff_course_id})
                mod2_id = r.scalar()

                await session.execute(text("""
                    INSERT INTO lessons (module_id, title, lesson_type, content, estimated_minutes, sensory_notes, xp_reward, sort_order)
                    VALUES (:mid, 'Time Management Strategies', 'article', '{"markdown": "# Time Management Strategies\\n\\nManaging time at work can be challenging. Here are concrete strategies.\\n\\n## The Two-Minute Rule\\nIf a task takes less than two minutes, do it now.\\n\\n## Task Batching\\nGroup similar tasks together for efficiency."}'::jsonb, 12, 'Text-based with clear structure.', 15, 1)
                """), {"mid": mod2_id})

                await session.execute(text("""
                    INSERT INTO lessons (module_id, title, lesson_type, content, estimated_minutes, sensory_notes, xp_reward, sort_order)
                    VALUES (:mid, 'Taking Effective Breaks', 'article', '{"markdown": "# Taking Effective Breaks\\n\\nBreaks are not optional. They make you better at your job.\\n\\n## Types of Breaks\\n\\n### Micro-breaks (30 seconds - 2 minutes)\\nLook away from the screen, stretch your hands.\\n\\n### Short breaks (5-15 minutes)\\nLeave your desk area. Go outside if possible.\\n\\n## Sensory Reset Breaks\\nIf feeling overwhelmed, find a quiet space and reduce input."}'::jsonb, 12, 'Calm, supportive tone.', 15, 2)
                """), {"mid": mod2_id})

                learning_courses_added += 1

                # Seed Patron Course - Digital Literacy Basics
                await session.execute(text("""
                    INSERT INTO courses (title, description, access_level, lifecycle_stage, estimated_minutes, difficulty, sensory_warning, xp_reward)
                    VALUES (
                        'Digital Literacy Basics',
                        'Learn essential digital skills for navigating the internet, using email, and staying safe online. Perfect for beginners or anyone wanting to refresh their knowledge.',
                        'patron',
                        'published',
                        60,
                        'beginner',
                        'This course contains text-based content with some example screenshots. No auto-playing media or flashing content.',
                        150
                    )
                """))

                r = await session.execute(text("SELECT id FROM courses WHERE title = 'Digital Literacy Basics'"))
                patron_course1_id = r.scalar()

                # Module
                await session.execute(text("""
                    INSERT INTO modules (course_id, title, description, sort_order)
                    VALUES (:cid, 'Getting Started with Computers', 'Basic computer skills including using a mouse, keyboard, and understanding the desktop.', 1)
                """), {"cid": patron_course1_id})

                r = await session.execute(text("SELECT id FROM modules WHERE course_id = :cid"), {"cid": patron_course1_id})
                patron_mod1_id = r.scalar()

                await session.execute(text("""
                    INSERT INTO lessons (module_id, title, lesson_type, content, estimated_minutes, sensory_notes, xp_reward, sort_order)
                    VALUES (:mid, 'Understanding Your Computer', 'article', '{"markdown": "# Understanding Your Computer\\n\\nWelcome! This lesson introduces you to basic computer concepts.\\n\\n## Parts of a Computer\\n\\n### The Screen (Monitor)\\nThis is where you see everything.\\n\\n### The Keyboard\\nUsed for typing text.\\n\\n### The Mouse\\nA device you move with your hand to control a pointer."}'::jsonb, 10, 'Text only. Clear structure.', 10, 1)
                """), {"mid": patron_mod1_id})

                await session.execute(text("""
                    INSERT INTO lessons (module_id, title, lesson_type, content, estimated_minutes, sensory_notes, xp_reward, sort_order)
                    VALUES (:mid, 'Using the Internet', 'article', '{"markdown": "# Using the Internet\\n\\nThe internet is a network that connects computers around the world.\\n\\n## What Are Websites?\\nWebsites are pages of information stored on the internet.\\n\\n## How to Search\\n1. Go to a search engine (like google.com)\\n2. Type what you are looking for\\n3. Press Enter\\n4. Look through the results"}'::jsonb, 15, 'Informational content. Calm tone.', 15, 2)
                """), {"mid": patron_mod1_id})

                learning_courses_added += 1

                # Seed Patron Course - Library Tour
                await session.execute(text("""
                    INSERT INTO courses (title, description, access_level, lifecycle_stage, estimated_minutes, difficulty, sensory_warning, xp_reward)
                    VALUES (
                        'Library Tour: Getting Started',
                        'A gentle introduction to using the Bébé Memorial Library. Learn about our services, how to find books, and what resources are available to you.',
                        'patron',
                        'published',
                        30,
                        'beginner',
                        'Text-based course with calm pacing. No multimedia. Self-paced - take breaks as needed.',
                        100
                    )
                """))

                r = await session.execute(text("SELECT id FROM courses WHERE title = 'Library Tour: Getting Started'"))
                patron_course2_id = r.scalar()

                await session.execute(text("""
                    INSERT INTO modules (course_id, title, description, sort_order)
                    VALUES (:cid, 'Welcome to the Library', 'Learn about library services and how to get a library card.', 1)
                """), {"cid": patron_course2_id})

                r = await session.execute(text("SELECT id FROM modules WHERE course_id = :cid"), {"cid": patron_course2_id})
                patron_mod2_id = r.scalar()

                await session.execute(text("""
                    INSERT INTO lessons (module_id, title, lesson_type, content, estimated_minutes, sensory_notes, xp_reward, sort_order)
                    VALUES (:mid, 'Welcome to Bébé Memorial Library', 'article', '{"markdown": "# Welcome to Bébé Memorial Library\\n\\nWelcome! We are glad you are here.\\n\\n## What Is a Library?\\n\\nA library is:\\n- A place to borrow books, audiobooks, movies, and more\\n- A quiet space to read or work\\n- A source of free programs and resources\\n- A welcoming community space\\n\\n**Everything is free.** You do not pay to borrow materials or use our services."}'::jsonb, 8, 'Welcoming, calm tone.', 10, 1)
                """), {"mid": patron_mod2_id})

                await session.execute(text("""
                    INSERT INTO lessons (module_id, title, lesson_type, content, estimated_minutes, sensory_notes, xp_reward, sort_order)
                    VALUES (:mid, 'Getting Your Library Card', 'article', '{"markdown": "# Getting Your Library Card\\n\\nYour library card is your key to using library services.\\n\\n## How to Get a Library Card\\n\\n### What You Need:\\n1. Proof of identity (drivers license, ID, passport)\\n2. Proof of address (utility bill, bank statement)\\n\\n### Steps:\\n1. Come to the library\\n2. Go to the front desk\\n3. Tell staff you want a library card\\n4. Show your ID and proof of address\\n5. You get your card right away!"}'::jsonb, 10, 'Step-by-step process.', 10, 2)
                """), {"mid": patron_mod2_id})

                await session.execute(text("""
                    INSERT INTO lessons (module_id, title, lesson_type, content, estimated_minutes, sensory_notes, xp_reward, sort_order)
                    VALUES (:mid, 'Finding and Borrowing Books', 'article', '{"markdown": "# Finding and Borrowing Books\\n\\n## How Books Are Organized\\n\\n### Fiction Books (Made-up Stories)\\nOrganized alphabetically by authors last name.\\n\\n### Non-Fiction Books (True Information)\\nOrganized by topic using the Dewey Decimal System.\\n\\n## Checking Out Books\\n\\n1. Bring your books and library card to the front desk\\n2. Staff will scan your card and the books\\n3. You will be told when they are due back\\n4. Take your books and enjoy!"}'::jsonb, 12, 'Practical instructions.', 15, 3)
                """), {"mid": patron_mod2_id})

                learning_courses_added += 1

                await session.commit()
                print(f"  ✅ Added {learning_courses_added} learning courses (1 staff, 2 patron)")
            else:
                print(f"  ℹ️  {existing_count} courses already exist, skipping")

        print("\n" + "=" * 70)
        print("✅ Seeding Complete!")
        print("=" * 70)
        print(f"""
Summary:
  📚 {len(CATALOG_ITEMS)} catalog items (books, audiobooks, DVDs, games)
  📅 {len(EVENTS)} upcoming events
  📢 {len(ANNOUNCEMENTS)} announcements
  📖 {learning_courses_added} learning courses

Note: AI tools, staff bios, and community features will be seeded by seed_lsc_features.py
      Patron courses will be seeded by seed_patron_courses.py

Your library catalog and events are now populated! 🎉
        """)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(seed_all())
