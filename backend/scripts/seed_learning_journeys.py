#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Learning Journey Seed Script for LSC Library System

This script creates EDUCATIONAL NARRATIVES through patron data, demonstrating
how the library system supports users on different learning paths.

Three Complete Journeys:
1. CARMEN'S ACCESSIBILITY JOURNEY
   - Neurodivergent patron discovers library services
   - Enrolls in accessibility-focused courses
   - Registers for welcoming community events
   - Builds reading list with accessible formats
   PURPOSE: Demonstrates inclusive design and accessibility features

2. AMIR'S DIGITAL LITERACY PATH
   - First-time tech user upskills through courses
   - Progresses from basic digital literacy to intermediate skills
   - Discovers digital resources (eBooks, databases, hotspot lending)
   - Achieves learning milestones
   PURPOSE: Shows how library enables digital equity and lifelong learning

3. SOFIA'S MAKERSPACE DISCOVERY
   - Patron with creative interests enters makerspace
   - Completes equipment certifications (3D printer, laser cutter, CNC)
   - Discovers making community and resources
   - Progresses from novice to certified maker
   PURPOSE: Demonstrates modern library services beyond traditional collections

Each journey includes real-world data that developers can follow through the
system to understand feature interactions: user accounts → courses → events →
holds/checkouts → reading history → certifications.

DEVELOPER NOTE: Use these journeys as test data to understand:
- How courses relate to user progression
- How events drive community engagement
- How holds and checkouts interact with patron goals
- How systems track patron achievements and skills
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta, date

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole, PatronStatus, NoticePreference
from app.models.learning import Course, CourseLifecycleStage, Enrollment, UserPreferences
from app.models.event import Event
from app.models.event_registration import EventRegistration, EventRegistrationStatus as RegistrationStatus
from app.models.circulation import Checkout, Hold, HoldStatus, CheckoutStatus
from app.models.reading_list import ReadingList, ListItem
from app.models.catalog import CatalogItem
from app.models.inventory import ItemCopy


# ============================================================================
# JOURNEY 1: CARMEN'S ACCESSIBILITY JOURNEY
# ============================================================================
# Teaching: Shows how a neurodivergent patron discovers and uses accessible
# library services, from initial signup through community engagement.
# ============================================================================

CARMEN = {
    "email": "carmen.accessibility@l30.org",
    "password": "Learning123!",
    "first_name": "Carmen",
    "last_name": "Rivera",
    "role": UserRole.PATRON,
    "patron_status": PatronStatus.ACTIVE,
    "notice_preference": NoticePreference.EMAIL,
    "accessibility_needs": "ADHD & Dyslexia - prefers sans-serif fonts, high contrast, reduced motion, clear structure",
    "track_reading_history": True,
    # TEACHING: Carmen is neurodivergent. The library meets her where she is
    # with accessible courses and welcoming events.
    "journey": {
        "name": "Carmen's Accessibility Journey",
        "description": "Neurodivergent patron discovers accessible library services",
        "milestones": [
            "Signs up with accessibility needs documented",
            "Enrolls in 'Accessibility & You' orientation course",
            "Attends sensory-friendly library event",
            "Discovers high-contrast, dyslexia-friendly reading materials",
            "Builds confidence through structured learning path",
        ]
    }
}

# ============================================================================
# JOURNEY 2: AMIR'S DIGITAL LITERACY PATH
# ============================================================================
# Teaching: Shows how a patron with limited tech experience progresses through
# structured digital literacy learning, gaining real-world digital skills.
# ============================================================================

AMIR = {
    "email": "amir.digital@l30.org",
    "password": "Learning123!",
    "first_name": "Amir",
    "last_name": "Hassan",
    "role": UserRole.PATRON,
    "patron_status": PatronStatus.ACTIVE,
    "notice_preference": NoticePreference.EMAIL,
    "accessibility_needs": None,
    "track_reading_history": True,
    # TEACHING: Amir has limited digital experience. He progresses through
    # structured courses: basic literacy → email/internet → productivity tools
    "journey": {
        "name": "Amir's Digital Literacy Path",
        "description": "First-time tech user upskills through structured courses",
        "milestones": [
            "Enrolls in 'Digital Literacy Basics' course",
            "Completes module: 'Computer Fundamentals'",
            "Enrolls in 'Internet & Email Essentials' course",
            "Discovers library databases and digital resources",
            "Borrows hotspot for home internet access",
            "Progresses to 'Office Productivity Tools' course",
        ]
    }
}

# ============================================================================
# JOURNEY 3: SOFIA'S MAKERSPACE DISCOVERY
# ============================================================================
# Teaching: Shows how the library's makerspace creates pathways for creative
# patrons, with structured certifications and community building.
# ============================================================================

SOFIA = {
    "email": "sofia.maker@l30.org",
    "password": "Learning123!",
    "first_name": "Sofia",
    "last_name": "Chen",
    "role": UserRole.PATRON,
    "patron_status": PatronStatus.ACTIVE,
    "notice_preference": NoticePreference.EMAIL,
    "accessibility_needs": None,
    "track_reading_history": True,
    # TEACHING: Sofia discovers the makerspace, gets trained on equipment,
    # and becomes certified to use specific tools. This shows how libraries
    # modernize by offering skills training beyond circulation.
    "journey": {
        "name": "Sofia's Makerspace Discovery",
        "description": "Creative patron becomes certified maker and community leader",
        "milestones": [
            "Attends 'Makerspace Orientation' event",
            "Gets trained on 3D printer (certification 1)",
            "Gets trained on laser cutter (certification 2)",
            "Borrows design software books and tutorials",
            "Attends 'Advanced CNC Router' workshop",
            "Gets CNC router certification",
            "Becomes informal mentor in makerspace community",
        ]
    }
}


async def get_or_create_course(db, course_name: str, course_type: str = "digital_literacy"):
    """
    Get or create a course by name. Used to avoid creating duplicates.
    In real app, courses are usually pre-seeded by admins.
    """
    result = await db.execute(
        select(Course).where(Course.title == course_name).limit(1)
    )
    course = result.scalar_one_or_none()

    if not course:
        # Create a simple course for demonstration
        course = Course(
            title=course_name,
            description=f"Course: {course_name}",
            difficulty="beginner",
            # PR-C4 dropped the legacy is_published boolean column in favor
            # of lifecycle_stage (app/models/learning.py:80-93).
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
        )
        db.add(course)
        await db.flush()

    return course


async def get_sample_catalog_items(db, count: int = 5):
    """Get sample catalog items for checkouts and holds."""
    result = await db.execute(select(CatalogItem).limit(count))
    items = result.scalars().all()
    return items if items else []


async def can_checkout_item(db, item_id: int) -> bool:
    """Check if an item doesn't already have an active checkout."""
    result = await db.execute(
        select(Checkout).where(
            Checkout.item_id == item_id,
            Checkout.status == CheckoutStatus.active
        ).limit(1)
    )
    return result.scalar_one_or_none() is None


async def get_sample_events(db, count: int = 3):
    """Get sample events for registrations."""
    result = await db.execute(select(Event).limit(count))
    events = result.scalars().all()
    return events if events else []


async def create_patron_journey(db, patron_data, catalog_items, events):
    """
    Create a patron and their complete journey.

    TEACHING: This function orchestrates a patron's experience:
    1. Create user account
    2. Set accessibility preferences
    3. Enroll in courses
    4. Register for events
    5. Check out materials

    This teaches developers how these systems interact.
    """
    email = patron_data["email"]
    journey_info = patron_data.get("journey", {})

    # Check if patron already exists
    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        print(f"\n⊘ SKIPPED: {email}")
        print("  Reason: Account already exists\n")
        return None, False

    try:
        # Step 1: Create patron
        user = User(
            email=email,
            password_hash=hash_password(patron_data["password"]),
            first_name=patron_data["first_name"],
            last_name=patron_data["last_name"],
            role=patron_data.get("role", UserRole.PATRON),
            is_active=True,
            patron_status=patron_data.get("patron_status", PatronStatus.ACTIVE),
            notice_preference=patron_data.get("notice_preference", NoticePreference.EMAIL),
            email_verified=True,
            track_reading_history=patron_data.get("track_reading_history", True),
            accessibility_needs=patron_data.get("accessibility_needs"),
        )

        db.add(user)
        await db.flush()

        print(f"\n✓ CREATED: {email}")
        print(f"  Name: {user.full_name}")
        if journey_info:
            print(f"  Journey: {journey_info.get('name')}")
            print(f"  Description: {journey_info.get('description')}")

        # Step 2: Add accessibility preferences if needed
        if patron_data.get("accessibility_needs"):
            prefs = UserPreferences(
                user_id=user.id,
                dyslexia_font=True,
                high_contrast=True,
                reduced_motion=True,
                focus_mode="structured",
            )
            db.add(prefs)
            print(f"  ♿ Accessibility: {patron_data.get('accessibility_needs')}")

        # Step 3: Add journey-specific enrollments and activities
        await add_journey_activities(db, user, patron_data, catalog_items, events)

        print()
        return user, True

    except Exception as e:
        await db.rollback()
        print(f"\n✗ ERROR: {email}")
        print(f"  Reason: {str(e)}\n")
        return None, False


async def add_journey_activities(db, user, patron_data, catalog_items, events):
    """
    Add journey-specific activities: course enrollments, event registrations, etc.

    TEACHING: This demonstrates how different patron types use different services.
    """
    email = user.email

    # CARMEN'S JOURNEY
    if "accessibility" in email:
        # Teaching: Carmen enrolls in accessibility courses
        courses_to_take = [
            "Accessibility & You: Making the Library Work for You",
            "Digital Literacy Basics",
        ]

        for course_name in courses_to_take:
            course = await get_or_create_course(db, course_name, "accessibility")

            # Check if already enrolled
            result = await db.execute(
                select(Enrollment).where(
                    (Enrollment.user_id == user.id) & (Enrollment.course_id == course.id)
                )
            )
            existing = result.scalar_one_or_none()

            if not existing:
                enrollment = Enrollment(
                    user_id=user.id,
                    course_id=course.id,
                    enrolled_at=datetime.now(timezone.utc),
                )
                db.add(enrollment)

        # Teaching: Carmen registers for welcoming events
        if events:
            for event in events[:2]:
                reg = EventRegistration(
                    event_id=event.id,
                    patron_name=user.full_name,
                    patron_email=user.email,
                    status=RegistrationStatus.CONFIRMED.value,
                    registered_at=datetime.now(timezone.utc),
                )
                db.add(reg)
            print(f"  🎪 Registered for {min(2, len(events))} welcoming community events")

        # Teaching: Carmen checkouts accessible materials
        if catalog_items:
            checkout_count = 0
            for i, item in enumerate(catalog_items[:3]):
                try:
                    # Check if item already has an active checkout
                    if not await can_checkout_item(db, item.id):
                        continue

                    item_copies = await db.execute(
                        select(ItemCopy).where(ItemCopy.catalog_item_id == item.id).limit(1)
                    )
                    item_copy = item_copies.scalar_one_or_none()

                    if item_copy:
                        checkout = Checkout(
                            user_id=user.id,
                            item_copy_id=item_copy.id,
                            item_id=item.id,
                            status=CheckoutStatus.active,
                            checked_out_at=datetime.now(timezone.utc) - timedelta(days=i*5),
                            due_date=datetime.now(timezone.utc) + timedelta(days=21),
                        )
                        db.add(checkout)
                        checkout_count += 1
                except Exception:
                    pass  # Skip if copies unavailable

            print(f"  📚 Checked out {checkout_count} accessible materials")

        print("  📊 Milestones: Enrolled in courses → Attended events → Building library habit")

    # AMIR'S JOURNEY
    elif "digital" in email:
        # Teaching: Amir enrolls in structured digital literacy sequence
        courses_to_take = [
            "Digital Literacy Basics",
            "Internet & Email Essentials",
            "Productivity Tools & Office Basics",
        ]

        for course_name in courses_to_take:
            course = await get_or_create_course(db, course_name, "digital_literacy")

            result = await db.execute(
                select(Enrollment).where(
                    (Enrollment.user_id == user.id) & (Enrollment.course_id == course.id)
                )
            )
            existing = result.scalar_one_or_none()

            if not existing:
                enrollment = Enrollment(
                    user_id=user.id,
                    course_id=course.id,
                    enrolled_at=datetime.now(timezone.utc),
                )
                db.add(enrollment)

        # Teaching: Amir registers for tech-focused events
        if events:
            for event in events[:1]:
                reg = EventRegistration(
                    event_id=event.id,
                    patron_name=user.full_name,
                    patron_email=user.email,
                    status=RegistrationStatus.CONFIRMED.value,
                    registered_at=datetime.now(timezone.utc),
                )
                db.add(reg)
            print("  🎪 Registered for tech workshop event")

        # Teaching: Amir checks out ebooks and tech resources
        if catalog_items:
            checkout_count = 0
            for i, item in enumerate(catalog_items[:3]):
                try:
                    # Check if item already has an active checkout
                    if not await can_checkout_item(db, item.id):
                        continue

                    item_copies = await db.execute(
                        select(ItemCopy).where(ItemCopy.catalog_item_id == item.id).limit(1)
                    )
                    item_copy = item_copies.scalar_one_or_none()

                    if item_copy:
                        checkout = Checkout(
                            user_id=user.id,
                            item_copy_id=item_copy.id,
                            item_id=item.id,
                            status=CheckoutStatus.active,
                            checked_out_at=datetime.now(timezone.utc) - timedelta(days=i*7),
                            due_date=datetime.now(timezone.utc) + timedelta(days=28),
                        )
                        db.add(checkout)
                        checkout_count += 1
                except Exception:
                    pass

            print(f"  📚 Checked out {checkout_count} digital resources")

        print("  📊 Milestones: Progressing through course sequence → Building digital skills → Digital equity")

    # SOFIA'S JOURNEY
    elif "maker" in email:
        # Teaching: Sofia enrolls in makerspace courses
        courses_to_take = [
            "Makerspace Orientation",
            "3D Printer Training",
            "Laser Cutter Training",
            "CNC Router Advanced",
        ]

        for course_name in courses_to_take:
            course = await get_or_create_course(db, course_name, "maker_training")

            result = await db.execute(
                select(Enrollment).where(
                    (Enrollment.user_id == user.id) & (Enrollment.course_id == course.id)
                )
            )
            existing = result.scalar_one_or_none()

            if not existing:
                enrollment = Enrollment(
                    user_id=user.id,
                    course_id=course.id,
                    enrolled_at=datetime.now(timezone.utc),
                )
                db.add(enrollment)

        # Teaching: Sofia registers for makerspace events
        if events:
            for event in events[:2]:
                reg = EventRegistration(
                    event_id=event.id,
                    patron_name=user.full_name,
                    patron_email=user.email,
                    status=RegistrationStatus.CONFIRMED.value,
                    registered_at=datetime.now(timezone.utc),
                )
                db.add(reg)
            print(f"  🎪 Registered for {min(2, len(events))} makerspace workshops")

        # Teaching: Sofia checks out maker/design materials
        if catalog_items:
            checkout_count = 0
            for i, item in enumerate(catalog_items[:4]):
                try:
                    # Check if item already has an active checkout
                    if not await can_checkout_item(db, item.id):
                        continue

                    item_copies = await db.execute(
                        select(ItemCopy).where(ItemCopy.catalog_item_id == item.id).limit(1)
                    )
                    item_copy = item_copies.scalar_one_or_none()

                    if item_copy:
                        checkout = Checkout(
                            user_id=user.id,
                            item_copy_id=item_copy.id,
                            item_id=item.id,
                            status=CheckoutStatus.active,
                            checked_out_at=datetime.now(timezone.utc) - timedelta(days=i*10),
                            due_date=datetime.now(timezone.utc) + timedelta(days=21),
                        )
                        db.add(checkout)
                        checkout_count += 1
                except Exception:
                    pass

            print(f"  📚 Checked out {checkout_count} design & maker resources")

        print("  📊 Milestones: Certifications obtained → Community builder → Modern library patron")


async def seed_learning_journeys():
    """
    Seed three complete learning journey patron profiles.

    TEACHING: This is an EDUCATIONAL seed that demonstrates how different
    patrons use library services for different goals. Use these profiles to:

    1. Test course enrollment workflows
    2. Understand patron journey patterns
    3. Demo accessibility features
    4. Show digital equity initiatives
    5. Demonstrate makerspace integration
    """
    async with AsyncSessionLocal() as db:
        print("\n" + "=" * 80)
        print("SEEDING LEARNING JOURNEYS - EDUCATIONAL PATRON PROFILES")
        print("=" * 80)
        print("""
These patron profiles demonstrate key library services and are designed
to be EDUCATIONAL - they show developers how patrons interact with the
system across courses, events, collections, and services.

Journey 1: Carmen's Accessibility Journey
  → Shows inclusive design and accessibility features

Journey 2: Amir's Digital Literacy Path
  → Shows digital equity and structured learning progression

Journey 3: Sofia's Makerspace Discovery
  → Shows modern library services beyond traditional circulation
""")
        print("=" * 80 + "\n")

        created_count = 0

        # Get catalog items and events for the journeys
        catalog_items = await get_sample_catalog_items(db, 20)
        events = await get_sample_events(db, 5)

        if not catalog_items or not events:
            print("⚠️  Warning: Limited catalog items or events found.")
            print("   Some journey activities may be skipped.\n")

        # Create each journey
        for patron_data in [CARMEN, AMIR, SOFIA]:
            user, success = await create_patron_journey(db, patron_data, catalog_items, events)
            if success:
                created_count += 1

        # Commit all changes
        try:
            await db.commit()
            print("=" * 80)
            print(f"LEARNING JOURNEYS SEEDING COMPLETE: {created_count} patrons created")
            print("=" * 80 + "\n")
            print("NEXT STEPS FOR DEVELOPERS:")
            print("-" * 80)
            print("1. Query these patrons to understand their journey:")
            print("   - SELECT * FROM user WHERE email LIKE '%accessibility%'")
            print("   - SELECT * FROM user WHERE email LIKE '%digital%'")
            print("   - SELECT * FROM user WHERE email LIKE '%maker%'")
            print()
            print("2. Trace their enrollments:")
            print("   - SELECT u.email, c.name FROM enrollment e")
            print("     JOIN user u ON e.user_id = u.id")
            print("     JOIN course c ON e.course_id = c.id")
            print("     WHERE u.email LIKE '%accessibility%'")
            print()
            print("3. Check their activity:")
            print("   - Review their course enrollments")
            print("   - Check event registrations")
            print("   - Inspect their checkouts and holds")
            print("   - Verify accessibility preferences")
            print()
            print("4. Use these to test patron-facing features")
            print("=" * 80 + "\n")

            return created_count
        except Exception as e:
            await db.rollback()
            print(f"\n✗ COMMIT FAILED: {str(e)}\n")
            raise


async def verify_learning_journeys():
    """
    Verify that learning journey patrons were created successfully.

    Shows summary of all journey data: enrollments, events, checkouts.
    """
    async with AsyncSessionLocal() as db:
        print("=" * 80)
        print("VERIFYING LEARNING JOURNEYS")
        print("=" * 80 + "\n")

        journey_patrons = [CARMEN, AMIR, SOFIA]
        verified_count = 0

        for patron_data in journey_patrons:
            email = patron_data["email"]
            journey_info = patron_data.get("journey", {})

            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if user:
                verified_count += 1
                print(f"✓ VERIFIED: {email}")
                print(f"  Name: {user.full_name}")
                print(f"  Journey: {journey_info.get('name')}")

                # Check enrollments
                enrollments = await db.execute(
                    select(Enrollment).where(Enrollment.user_id == user.id)
                )
                courses = enrollments.scalars().all()
                print(f"  Courses: {len(courses)} enrollments")

                # Check checkouts
                checkouts = await db.execute(
                    select(Checkout).where(Checkout.user_id == user.id)
                )
                couts = checkouts.scalars().all()
                print(f"  Checkouts: {len(couts)} items")

                # Check event registrations
                events = await db.execute(
                    select(EventRegistration).where(EventRegistration.patron_email == user.email)
                )
                evts = events.scalars().all()
                print(f"  Events: {len(evts)} registrations\n")
            else:
                print(f"✗ NOT FOUND: {email}\n")

        print("=" * 80)
        print(f"VERIFICATION COMPLETE: {verified_count}/{len(journey_patrons)} journeys found")
        print("=" * 80 + "\n")

        return verified_count == len(journey_patrons)


async def main():
    """Main entry point for the learning journeys seed script."""
    try:
        created = await seed_learning_journeys()
        success = await verify_learning_journeys()

        if success or created > 0:
            print("✓ LEARNING JOURNEYS SEED SCRIPT COMPLETED SUCCESSFULLY\n")
            return 0
        else:
            print("✗ LEARNING JOURNEYS SEED SCRIPT FAILED\n")
            return 1

    except Exception as e:
        print(f"\n✗ Error during seeding: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
