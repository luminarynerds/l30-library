# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from app.core.logging import get_logger
from datetime import datetime, date, timedelta, time as datetime_time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

# Event times below are written as the library's local wall clock (Eastern).
# Combine them in that zone and convert to UTC so the timestamptz column holds
# the correct instant and the frontend (which renders in America/New_York)
# shows the intended time instead of a ~4-5h-early one.
_LIBRARY_TZ = ZoneInfo("America/New_York")


def _eastern_combine(d: date, t: datetime_time) -> datetime:
    return datetime.combine(d, t, tzinfo=_LIBRARY_TZ).astimezone(timezone.utc)


async def seed_events_and_related_data(session: AsyncSession) -> bool:

    try:
        # Idempotency: skip if events already exist
        result = await session.execute(text("SELECT COUNT(*) FROM events"))
        if result.scalar() > 0:
            logger.info("Events already seeded, skipping.")
            return True

        # Get first user ID for created_by reference (if needed)
        result = await session.execute(text("SELECT id FROM users LIMIT 1"))
        user_id = result.scalar_one_or_none()

        if not user_id:
            logger.error("❌ No users found. Run bootstrap seed first.")
            return False

        logger.info("🌱 Starting comprehensive event seeding...")

        # Create events covering all timing scenarios
        await _seed_events(session)
        logger.info("✅ Created events")

        # Create registrations with various statuses
        await _seed_event_registrations(session)
        logger.info("✅ Created event registrations")

        # Create event reviews
        await _seed_event_reviews(session)
        logger.info("✅ Created event reviews")

        await session.commit()
        logger.info("\n✅ All event seed data committed successfully!\n")
        return True

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        await session.rollback()
        return False


async def _seed_events(session: AsyncSession) -> None:

    today = date.today()

    # Define event data: each entry includes all variations needed
    events_data = [
        # ==================== PAST EVENTS ====================
        {
            "title": "Spring Reading Challenge 2025 Wrap-up",
            "description": "Celebration of all the amazing reads from our spring challenge. Patrons share their favorite books.",
            "start_time": _eastern_combine(today - timedelta(days=30), datetime_time(14, 0)),
            "end_time": _eastern_combine(today - timedelta(days=30), datetime_time(16, 0)),
            "location": "Main Branch - Community Room",
            "is_virtual": False,
            "category": "Book clubs",
            "audience": "All ages",
            "tags": ["reading", "celebration", "community"],
            "max_attendees": 40,
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
        },
        {
            "title": "STEMcraft Workshop: Build Your Own Circuit Board",
            "description": "Hands-on workshop for teens to learn electronics basics and build a simple circuit.",
            "start_time": _eastern_combine(today - timedelta(days=20), datetime_time(15, 0)),
            "end_time": _eastern_combine(today - timedelta(days=20), datetime_time(17, 0)),
            "location": "Main Branch - Makerspace",
            "is_virtual": False,
            "category": "STEM programs",
            "audience": "Teen programs",
            "tags": ["STEM", "electronics", "hands-on"],
            "max_attendees": 20,
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
        },
        {
            "title": "Virtual Author Talk: Mystery Writer Jane Smith",
            "description": "Join bestselling mystery author Jane Smith as she discusses her latest book and writing process.",
            "start_time": _eastern_combine(today - timedelta(days=15), datetime_time(19, 0)),
            "end_time": _eastern_combine(today - timedelta(days=15), datetime_time(20, 30)),
            "location": None,
            "is_virtual": True,
            "virtual_link": "https://zoom.us/j/123456789",
            "category": "Author visits",
            "audience": "Adults",
            "tags": ["author", "mystery", "literature"],
            "max_attendees": 200,
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
        },
        {
            "title": "Kids Movie Night: Animated Adventures",
            "description": "Family-friendly animated feature with popcorn and snacks.",
            "start_time": _eastern_combine(today - timedelta(days=10), datetime_time(18, 0)),
            "end_time": _eastern_combine(today - timedelta(days=10), datetime_time(19, 45)),
            "location": "Elmdale Branch - Meeting Room",
            "is_virtual": False,
            "category": "Movie screenings",
            "audience": "Children's programs",
            "tags": ["movie", "family", "entertainment"],
            "max_attendees": 60,
            "registration_required": False,
            "is_published": True,
            "is_featured": False,
        },

        # ==================== TODAY'S EVENTS ====================
        {
            "title": "Story Time: Tales from Around the World",
            "description": "Interactive storytime featuring folktales from different cultures.",
            "start_time": _eastern_combine(today, datetime_time(10, 30)),
            "end_time": _eastern_combine(today, datetime_time(11, 15)),
            "location": "Main Branch - Children's Section",
            "is_virtual": False,
            "category": "Children's programs",
            "audience": "Children's programs",
            "tags": ["storytime", "interactive", "cultural"],
            "max_attendees": 30,
            "registration_required": False,
            "is_published": True,
            "is_featured": True,
        },
        {
            "title": "Business Networking Lunch & Learn",
            "description": "Monthly networking event for local business professionals with light lunch and speaker.",
            "start_time": _eastern_combine(today, datetime_time(12, 0)),
            "end_time": _eastern_combine(today, datetime_time(13, 30)),
            "location": "Main Branch - Community Room",
            "is_virtual": False,
            "category": "Community meetings",
            "audience": "Adults",
            "tags": ["networking", "business", "lunch"],
            "max_attendees": 50,
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
        },

        # ==================== THIS WEEK EVENTS ====================
        {
            "title": "Hybrid Book Club: Historical Fiction Discussion",
            "description": "Join us in-person or online to discuss this month's book selection.",
            "start_time": _eastern_combine(today + timedelta(days=2), datetime_time(19, 0)),
            "end_time": _eastern_combine(today + timedelta(days=2), datetime_time(20, 30)),
            "location": "Elmdale Branch - Meeting Room",
            "is_virtual": True,
            "virtual_link": "https://zoom.us/j/987654321",
            "category": "Book clubs",
            "audience": "Adults",
            "tags": ["book club", "hybrid", "discussion"],
            "max_attendees": 40,
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
        },
        {
            "title": "Crafts & Conversations: Make Holiday Decorations",
            "description": "Create beautiful decorations while socializing with fellow community members.",
            "start_time": _eastern_combine(today + timedelta(days=3), datetime_time(14, 0)),
            "end_time": _eastern_combine(today + timedelta(days=3), datetime_time(16, 0)),
            "location": "Jamie Chick Community Annex - Activity Room",
            "is_virtual": False,
            "category": "Crafts and maker events",
            "audience": "All ages",
            "tags": ["crafts", "social", "decorations"],
            "max_attendees": 25,
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
        },
        {
            "title": "Teen Gaming Tournament",
            "description": "Friendly competition in popular video games. Prizes for winners!",
            "start_time": _eastern_combine(today + timedelta(days=4), datetime_time(15, 30)),
            "end_time": _eastern_combine(today + timedelta(days=4), datetime_time(18, 0)),
            "location": "Main Branch - Computer Lab",
            "is_virtual": False,
            "category": "Teen programs",
            "audience": "Teen programs",
            "tags": ["gaming", "tournament", "competition"],
            "max_attendees": 30,
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
        },

        # ==================== THIS MONTH EVENTS ====================
        {
            "title": "Author Workshop: Writing Your First Novel",
            "description": "Multi-day workshop with renowned author teaching the craft of novel writing.",
            "start_time": _eastern_combine(today + timedelta(days=10), datetime_time(10, 0)),
            "end_time": _eastern_combine(today + timedelta(days=12), datetime_time(16, 0)),
            "location": "Main Branch - Community Room",
            "is_virtual": False,
            "category": "Author visits",
            "audience": "Adults",
            "tags": ["writing", "author", "workshop", "multi-day"],
            "max_attendees": 20,
            "registration_required": True,
            "is_published": True,
            "is_featured": True,
        },
        {
            "title": "Science Exploration Series - Part 1: Physics",
            "description": "First in a series of 4 monthly STEM programs. Hands-on physics experiments.",
            "start_time": _eastern_combine(today + timedelta(days=15), datetime_time(15, 0)),
            "end_time": _eastern_combine(today + timedelta(days=15), datetime_time(17, 0)),
            "location": "Elmdale Branch - Meeting Room",
            "is_virtual": False,
            "category": "STEM programs",
            "audience": "Teen programs",
            "tags": ["STEM", "physics", "series", "experiments"],
            "max_attendees": 35,
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
            "series_id": "STEM-2026-Q1",
            "series_name": "Science Exploration Series 2026",
        },
        {
            "title": "Science Exploration Series - Part 2: Chemistry",
            "description": "Second in a series of 4 monthly STEM programs. Fun chemistry demonstrations.",
            "start_time": _eastern_combine(today + timedelta(days=15 + 28), datetime_time(15, 0)),
            "end_time": _eastern_combine(today + timedelta(days=15 + 28), datetime_time(17, 0)),
            "location": "Elmdale Branch - Meeting Room",
            "is_virtual": False,
            "category": "STEM programs",
            "audience": "Teen programs",
            "tags": ["STEM", "chemistry", "series", "demonstrations"],
            "max_attendees": 35,
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
            "series_id": "STEM-2026-Q1",
            "series_name": "Science Exploration Series 2026",
        },
        {
            "title": "Community Movie Night: Classic Films",
            "description": "Watch a beloved classic film outdoors with the community.",
            "start_time": _eastern_combine(today + timedelta(days=20), datetime_time(19, 0)),
            "end_time": _eastern_combine(today + timedelta(days=20), datetime_time(21, 0)),
            "location": "Main Branch - Outdoor Courtyard",
            "is_virtual": False,
            "category": "Movie screenings",
            "audience": "All ages",
            "tags": ["movie", "outdoor", "community"],
            "max_attendees": 100,
            "registration_required": False,
            "is_published": True,
            "is_featured": False,
        },

        # ==================== DRAFT EVENT (NOT VISIBLE) ====================
        {
            "title": "Coming Soon: Summer Reading Kickoff Party",
            "description": "Details coming soon for our annual summer reading celebration.",
            "start_time": _eastern_combine(today + timedelta(days=45), datetime_time(14, 0)),
            "end_time": _eastern_combine(today + timedelta(days=45), datetime_time(16, 0)),
            "location": "Main Branch - Outdoor Courtyard",
            "is_virtual": False,
            "category": "All-ages events",
            "audience": "All ages",
            "tags": ["reading", "summer", "celebration"],
            "max_attendees": 150,
            "registration_required": True,
            "is_published": False,  # Draft - not visible to public
            "is_featured": False,
        },

        # ==================== FULL/AT CAPACITY EVENTS ====================
        {
            "title": "Master Class: Advanced Photography Techniques",
            "description": "Limited spots! Professional photographer teaching advanced techniques.",
            "start_time": _eastern_combine(today + timedelta(days=7), datetime_time(18, 0)),
            "end_time": _eastern_combine(today + timedelta(days=7), datetime_time(20, 0)),
            "location": "Main Branch - Photo Studio",
            "is_virtual": False,
            "category": "Crafts and maker events",
            "audience": "Adults",
            "tags": ["photography", "masterclass", "advanced"],
            "max_attendees": 12,  # Small class
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
        },

        # ==================== CANCELLED EVENT ====================
        {
            "title": "[CANCELLED] Spring Concert Series - Jazz Night",
            "description": "Due to unforeseen circumstances, this event has been cancelled. We apologize for any inconvenience.",
            "start_time": _eastern_combine(today + timedelta(days=25), datetime_time(19, 0)),
            "end_time": _eastern_combine(today + timedelta(days=25), datetime_time(21, 0)),
            "location": "Main Branch - Auditorium",
            "is_virtual": False,
            "category": "Community meetings",
            "audience": "All ages",
            "tags": ["music", "concert", "entertainment"],
            "max_attendees": 200,
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
        },

        # ==================== COURT DOCUMENTS SERIES ====================
        {
            "title": "Introduction to Finding Court Documents Online",
            "description": "New to legal research? This beginner-friendly workshop covers the basics of finding court documents online. Learn about the different types of court records, where they are stored, and how to access them for free or at low cost. Topics include federal vs. state court systems, case law databases, and tips for effective searches.",
            "start_time": _eastern_combine(today + timedelta(days=14), datetime_time(18, 0)),
            "end_time": _eastern_combine(today + timedelta(days=14), datetime_time(19, 30)),
            "location": "Main Branch - Computer Lab",
            "is_virtual": False,
            "category": "Workshop",
            "audience": "Adults",
            "tags": ["legal", "court documents", "research", "beginner"],
            "max_attendees": 25,
            "registration_required": True,
            "is_published": True,
            "is_featured": True,
            "series_id": "COURT-DOCS-2026",
            "series_name": "Finding Court Documents Online Series",
        },
        {
            "title": "Navigating PACER: Accessing Federal Court Records",
            "description": "Hands-on workshop teaching participants how to use PACER (Public Access to Court Electronic Records) to find federal court documents. We will walk through creating a PACER account, searching for cases by party name or case number, understanding docket entries, and downloading filings. Bring your laptop to follow along!",
            "start_time": _eastern_combine(today + timedelta(days=21), datetime_time(18, 0)),
            "end_time": _eastern_combine(today + timedelta(days=21), datetime_time(19, 30)),
            "location": "Main Branch - Computer Lab",
            "is_virtual": False,
            "category": "Workshop",
            "audience": "Adults",
            "tags": ["legal", "court documents", "PACER", "federal", "hands-on"],
            "max_attendees": 20,
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
            "series_id": "COURT-DOCS-2026",
            "series_name": "Finding Court Documents Online Series",
        },
        {
            "title": "State Court Records: Free Online Resources",
            "description": "Discover how to find state and local court records without spending a dime. This session covers free court record portals, county clerk websites, state judiciary databases, and other publicly available resources. We will also discuss what types of records are typically available online vs. those that require an in-person visit.",
            "start_time": _eastern_combine(today + timedelta(days=28), datetime_time(18, 0)),
            "end_time": _eastern_combine(today + timedelta(days=28), datetime_time(19, 30)),
            "location": "Main Branch - Computer Lab",
            "is_virtual": True,
            "virtual_link": "https://zoom.us/j/court-docs-state",
            "category": "Workshop",
            "audience": "Adults",
            "tags": ["legal", "court documents", "state courts", "free resources", "hybrid"],
            "max_attendees": 40,
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
            "series_id": "COURT-DOCS-2026",
            "series_name": "Finding Court Documents Online Series",
        },
        {
            "title": "Virtual Workshop: Using Google Scholar for Court Opinions",
            "description": "Did you know Google Scholar has a powerful case law search feature? Join this virtual workshop to learn how to use Google Scholar to find court opinions, track case citations, and research legal precedents. Perfect for anyone who wants to access court documents without a paid subscription. No legal background required!",
            "start_time": _eastern_combine(today + timedelta(days=35), datetime_time(19, 0)),
            "end_time": _eastern_combine(today + timedelta(days=35), datetime_time(20, 30)),
            "location": None,
            "is_virtual": True,
            "virtual_link": "https://zoom.us/j/court-docs-scholar",
            "category": "Workshop",
            "audience": "Adults",
            "tags": ["legal", "court documents", "Google Scholar", "virtual", "case law"],
            "max_attendees": 50,
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
            "series_id": "COURT-DOCS-2026",
            "series_name": "Finding Court Documents Online Series",
        },
        {
            "title": "Legal Research for Non-Lawyers: Court Documents & Public Records",
            "description": "This comprehensive wrap-up session brings together everything from our court documents series. Learn how to combine PACER, state databases, Google Scholar, and other tools into an effective research strategy. We will also cover public records beyond court documents, including property records, business filings, and government databases. A local attorney will be available for a brief Q&A.",
            "start_time": _eastern_combine(today + timedelta(days=42), datetime_time(14, 0)),
            "end_time": _eastern_combine(today + timedelta(days=42), datetime_time(16, 0)),
            "location": "Main Branch - Community Room",
            "is_virtual": True,
            "virtual_link": "https://zoom.us/j/court-docs-finale",
            "category": "Workshop",
            "audience": "Adults",
            "tags": ["legal", "court documents", "public records", "research", "hybrid"],
            "max_attendees": 50,
            "registration_required": True,
            "is_published": True,
            "is_featured": True,
            "series_id": "COURT-DOCS-2026",
            "series_name": "Finding Court Documents Online Series",
        },

        # ==================== FUTURE EVENTS (NEXT MONTH+) ====================
        {
            "title": "Summer Reading Challenge 2026",
            "description": "Read 10 books this summer and win amazing prizes!",
            "start_time": _eastern_combine(today + timedelta(days=120), datetime_time(10, 0)),
            "end_time": _eastern_combine(today + timedelta(days=150), datetime_time(17, 0)),
            "location": "All Branches",
            "is_virtual": False,
            "category": "Children's programs",
            "audience": "Children's programs",
            "tags": ["reading", "summer", "challenge", "prize"],
            "max_attendees": None,  # Unlimited
            "registration_required": True,
            "is_published": True,
            "is_featured": True,
        },
        {
            "title": "Teen Coding Bootcamp: Web Development",
            "description": "4-week intensive course teaching HTML, CSS, and JavaScript.",
            "start_time": _eastern_combine(today + timedelta(days=90), datetime_time(16, 0)),
            "end_time": _eastern_combine(today + timedelta(days=120), datetime_time(18, 0)),
            "location": "Main Branch - Computer Lab",
            "is_virtual": False,
            "category": "STEM programs",
            "audience": "Teen programs",
            "tags": ["coding", "bootcamp", "web", "technology"],
            "max_attendees": 25,
            "registration_required": True,
            "is_published": True,
            "is_featured": True,
        },
        {
            "title": "Fall Author Fest 2026",
            "description": "Annual festival featuring 15+ authors, book signings, and literary discussions.",
            "start_time": _eastern_combine(today + timedelta(days=200), datetime_time(10, 0)),
            "end_time": _eastern_combine(today + timedelta(days=201), datetime_time(17, 0)),
            "location": "Main Branch - All Areas",
            "is_virtual": False,
            "category": "Author visits",
            "audience": "All ages",
            "tags": ["authors", "festival", "books", "multi-day"],
            "max_attendees": None,  # Unlimited
            "registration_required": False,
            "is_published": True,
            "is_featured": True,
        },
        {
            "title": "Virtual Book Discussion Series - Science Fiction",
            "description": "Monthly online discussions of classic and contemporary sci-fi literature.",
            "start_time": _eastern_combine(today + timedelta(days=80), datetime_time(19, 0)),
            "end_time": _eastern_combine(today + timedelta(days=80), datetime_time(20, 30)),
            "location": None,
            "is_virtual": True,
            "virtual_link": "https://zoom.us/j/sci-fi-book-club",
            "category": "Book clubs",
            "audience": "Adults",
            "tags": ["virtual", "book club", "sci-fi"],
            "max_attendees": 100,
            "registration_required": True,
            "is_published": True,
            "is_featured": False,
        },
    ]

    # Insert events (skip if title already exists to prevent duplicates on re-seed)
    for event_data in events_data:
        exists = await session.execute(
            text("SELECT 1 FROM events WHERE title = :title LIMIT 1"),
            {"title": event_data["title"]},
        )
        if exists.scalar_one_or_none():
            continue
        await session.execute(text("""
            INSERT INTO events
            (title, description, start_time, end_time, location, is_virtual, virtual_link,
             audience, category, tags, max_attendees, registration_required, image_url,
             is_published, is_featured, series_id, series_name, share_count, created_at, updated_at)
            VALUES
            (:title, :description, :start_time, :end_time, :location, :is_virtual, :virtual_link,
             :audience, :category, :tags, :max_attendees, :registration_required, :image_url,
             :is_published, :is_featured, :series_id, :series_name, :share_count, NOW(), NOW())
        """), {
            "title": event_data["title"],
            "description": event_data["description"],
            "start_time": event_data["start_time"],
            "end_time": event_data["end_time"],
            "location": event_data["location"],
            "is_virtual": event_data["is_virtual"],
            "virtual_link": event_data.get("virtual_link"),
            "audience": event_data["audience"],
            "category": event_data["category"],
            "tags": event_data["tags"],
            "max_attendees": event_data.get("max_attendees"),
            "registration_required": event_data["registration_required"],
            "image_url": None,
            "is_published": event_data["is_published"],
            "is_featured": event_data.get("is_featured", False),
            "series_id": event_data.get("series_id"),
            "series_name": event_data.get("series_name"),
            "share_count": 0,
        })


async def _seed_event_registrations(session: AsyncSession) -> None:

    # Get all published events (first 10 for registrations)
    result = await session.execute(text("""
        SELECT id, title, registration_required, max_attendees
        FROM events
        WHERE is_published = true
        ORDER BY start_time ASC
        LIMIT 10
    """))
    events = result.fetchall()

    registrations = []
    status_rotation = ["confirmed", "confirmed", "confirmed", "waitlisted", "cancelled"]

    for idx, event in enumerate(events):
        event_id, title, registration_required, max_attendees = event

        if not registration_required:
            continue

        # Add multiple registrations per event
        num_registrations = min(15, max_attendees or 15)

        for reg_idx in range(num_registrations):
            status = status_rotation[reg_idx % len(status_rotation)]

            registrations.append({
                "event_id": event_id,
                "patron_name": f"Patron {reg_idx + 1}",
                "patron_email": f"patron{reg_idx + 1}@example.com",
                "patron_phone": f"(555) {100 + reg_idx:03d}-{4000 + reg_idx:04d}",
                "status": status,
                "reminder_requested": reg_idx % 3 == 0,
                "registered_at": datetime.now(),
            })

    for reg in registrations:
        await session.execute(text("""
            INSERT INTO event_registrations
            (event_id, patron_name, patron_email, patron_phone, status, reminder_requested, registered_at)
            VALUES
            (:event_id, :patron_name, :patron_email, :patron_phone, :status, :reminder_requested, :registered_at)
        """), reg)


async def _seed_event_reviews(session: AsyncSession) -> None:

    # Get past events (events that have already occurred)
    result = await session.execute(text("""
        SELECT id, title
        FROM events
        WHERE start_time < NOW()
        AND is_published = true
        LIMIT 5
    """))
    past_events = result.fetchall()

    review_data = [
        {
            "rating": 5,
            "comment": "Absolutely amazing event! The presenter was knowledgeable and engaging. Can't wait for the next one!",
            "moderation_status": "approved",
            "moderated_by": "staff@library.org",
        },
        {
            "rating": 4,
            "comment": "Great event overall. A bit crowded but well organized.",
            "moderation_status": "approved",
            "moderated_by": "staff@library.org",
        },
        {
            "rating": 3,
            "comment": "It was okay. Could have had better materials and more time for questions.",
            "moderation_status": "approved",
            "moderated_by": "staff@library.org",
        },
        {
            "rating": 5,
            "comment": "Perfect event for our family! Kids loved it and we learned so much.",
            "moderation_status": "pending",
            "moderated_by": None,
        },
        {
            "rating": 2,
            "comment": "Didn't meet my expectations. The location was hard to find.",
            "moderation_status": "pending",
            "moderated_by": None,
        },
    ]

    for event_idx, (event_id, event_title) in enumerate(past_events):
        # Add 3-5 reviews per past event
        for review_idx in range(3 + (event_idx % 2)):
            review = review_data[review_idx % len(review_data)]

            await session.execute(text("""
                INSERT INTO event_reviews
                (event_id, patron_email, rating, comment, moderation_status, moderated_by, moderated_at, is_removed)
                VALUES
                (:event_id, :patron_email, :rating, :comment, :moderation_status, :moderated_by, :moderated_at, :is_removed)
            """), {
                "event_id": event_id,
                "patron_email": f"reviewer{event_idx}_{review_idx}@example.com",
                "rating": review["rating"],
                "comment": review["comment"],
                "moderation_status": review["moderation_status"],
                "moderated_by": review["moderated_by"],
                "moderated_at": datetime.now() if review["moderation_status"] == "approved" else None,
                "is_removed": 0,
            })


async def main():
    async with AsyncSessionLocal() as session:
        await seed_events_and_related_data(session)


if __name__ == "__main__":
    asyncio.run(main())
