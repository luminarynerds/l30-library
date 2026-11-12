#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive Diverse Patron Seed Data Script for LSC Library System

Creates test patrons covering all required scenarios:
- Patron in good standing (ACTIVE, no fines)
- Patron with overdue items
- Patron with fines owed
- Patron at checkout limit
- Patron with active holds
- Patron with expired holds
- SUSPENDED patron (auto-suspended for fines)
- BLOCKED patron (staff-blocked)
- Patron with reading history
- Patron enrolled in reading program
- Patron with event registrations
- Patron with course enrollments
- Child patron with guardian
- Patron with accessibility preferences
- Patron with notification preferences set
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole, PatronStatus, NoticePreference
from app.models.circulation import Checkout, Hold, HoldStatus, CheckoutStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.catalog import CatalogItem
from app.models.reading import ReadingProgram, ReadingRegistration
from app.models.event import Event
from app.models.event_registration import EventRegistration, RegistrationStatus
from app.models.learning import Enrollment, Course, UserPreferences
from app.models.inventory import ItemCopy


# Patron definitions with their specific scenarios
DIVERSE_PATRONS = [
    {
        "email": "patron.good-standing@l30.org",
        "password": "Patron123!",
        "first_name": "Grace",
        "last_name": "Standing",
        "scenario": "Patron in good standing (ACTIVE, no fines)",
        "patron_status": PatronStatus.ACTIVE,
        "notice_preference": NoticePreference.EMAIL,
        "track_reading_history": True,
        "add_circulation": False,
        "add_fines": False,
        "add_holds": False,
        "add_accessibility": False,
    },
    {
        "email": "patron.with-overdue@l30.org",
        "password": "Patron123!",
        "first_name": "Otto",
        "last_name": "Verdue",
        "scenario": "Patron with overdue items",
        "patron_status": PatronStatus.ACTIVE,
        "notice_preference": NoticePreference.EMAIL,
        "track_reading_history": True,
        "add_circulation": "overdue",
        "add_fines": False,
        "add_holds": False,
        "add_accessibility": False,
    },
    {
        "email": "patron.with-fines@l30.org",
        "password": "Patron123!",
        "first_name": "Finley",
        "last_name": "Fine",
        "scenario": "Patron with fines owed",
        "patron_status": PatronStatus.ACTIVE,
        "notice_preference": NoticePreference.EMAIL,
        "track_reading_history": True,
        "add_circulation": False,
        "add_fines": True,
        "add_holds": False,
        "add_accessibility": False,
    },
    {
        "email": "patron.at-checkout-limit@l30.org",
        "password": "Patron123!",
        "first_name": "Max",
        "last_name": "Checkout",
        "scenario": "Patron at checkout limit",
        "patron_status": PatronStatus.ACTIVE,
        "notice_preference": NoticePreference.SMS,
        "track_reading_history": True,
        "add_circulation": "at_limit",
        "add_fines": False,
        "add_holds": False,
        "add_accessibility": False,
    },
    {
        "email": "patron.with-active-holds@l30.org",
        "password": "Patron123!",
        "first_name": "Holly",
        "last_name": "Holder",
        "scenario": "Patron with active holds",
        "patron_status": PatronStatus.ACTIVE,
        "notice_preference": NoticePreference.EMAIL,
        "track_reading_history": True,
        "add_circulation": False,
        "add_fines": False,
        "add_holds": "active",
        "add_accessibility": False,
    },
    {
        "email": "patron.with-expired-holds@l30.org",
        "password": "Patron123!",
        "first_name": "Xander",
        "last_name": "Expired",
        "scenario": "Patron with expired holds",
        "patron_status": PatronStatus.ACTIVE,
        "notice_preference": NoticePreference.EMAIL,
        "track_reading_history": True,
        "add_circulation": False,
        "add_fines": False,
        "add_holds": "expired",
        "add_accessibility": False,
    },
    {
        "email": "patron.suspended@l30.org",
        "password": "Patron123!",
        "first_name": "Susy",
        "last_name": "Suspended",
        "scenario": "SUSPENDED patron (auto-suspended for fines)",
        "patron_status": PatronStatus.SUSPENDED,
        "notice_preference": NoticePreference.EMAIL,
        "track_reading_history": True,
        "add_circulation": False,
        "add_fines": True,
        "add_holds": False,
        "add_accessibility": False,
        "suspension_reason": "Auto-suspended: Fines exceeding $25.00",
        "suspended_until": datetime.now(timezone.utc) + timedelta(days=30),
    },
    {
        "email": "patron.blocked@l30.org",
        "password": "Patron123!",
        "first_name": "Blake",
        "last_name": "Blocked",
        "scenario": "BLOCKED patron (staff-blocked)",
        "patron_status": PatronStatus.BLOCKED,
        "notice_preference": NoticePreference.EMAIL,
        "track_reading_history": False,
        "add_circulation": False,
        "add_fines": False,
        "add_holds": False,
        "add_accessibility": False,
        "block_reason": "Staff block: Disruptive behavior - Please contact circulation desk",
        "blocked_at": datetime.now(timezone.utc) - timedelta(days=5),
    },
    {
        "email": "patron.reading-history@l30.org",
        "password": "Patron123!",
        "first_name": "Ryan",
        "last_name": "Reader",
        "scenario": "Patron with reading history",
        "patron_status": PatronStatus.ACTIVE,
        "notice_preference": NoticePreference.EMAIL,
        "track_reading_history": True,
        "add_circulation": "reading_history",
        "add_fines": False,
        "add_holds": False,
        "add_accessibility": False,
    },
    {
        "email": "patron.reading-program@l30.org",
        "password": "Patron123!",
        "first_name": "Priya",
        "last_name": "Program",
        "scenario": "Patron enrolled in reading program",
        "patron_status": PatronStatus.ACTIVE,
        "notice_preference": NoticePreference.EMAIL,
        "track_reading_history": True,
        "add_circulation": False,
        "add_fines": False,
        "add_holds": False,
        "add_accessibility": False,
        "add_program_enrollment": True,
    },
    {
        "email": "patron.event-registrations@l30.org",
        "password": "Patron123!",
        "first_name": "Evan",
        "last_name": "Events",
        "scenario": "Patron with event registrations",
        "patron_status": PatronStatus.ACTIVE,
        "notice_preference": NoticePreference.PRINT,
        "track_reading_history": False,
        "add_circulation": False,
        "add_fines": False,
        "add_holds": False,
        "add_accessibility": False,
        "add_event_registration": True,
    },
    {
        "email": "patron.course-enrollments@l30.org",
        "password": "Patron123!",
        "first_name": "Cora",
        "last_name": "Course",
        "scenario": "Patron with course enrollments",
        "patron_status": PatronStatus.ACTIVE,
        "notice_preference": NoticePreference.EMAIL,
        "track_reading_history": True,
        "add_circulation": False,
        "add_fines": False,
        "add_holds": False,
        "add_accessibility": False,
        "add_course_enrollment": True,
    },
    {
        "email": "guardian@l30.org",
        "password": "Guardian123!",
        "first_name": "Guardian",
        "last_name": "Adult",
        "scenario": "Guardian account (parent)",
        "patron_status": PatronStatus.ACTIVE,
        "notice_preference": NoticePreference.EMAIL,
        "track_reading_history": True,
        "add_circulation": False,
        "add_fines": False,
        "add_holds": False,
        "add_accessibility": False,
        "role": UserRole.PATRON,
    },
    {
        "email": "patron.child@l30.org",
        "password": "Child123!",
        "first_name": "Charlie",
        "last_name": "Child",
        "scenario": "Child patron with guardian",
        "patron_status": PatronStatus.ACTIVE,
        "notice_preference": NoticePreference.EMAIL,
        "track_reading_history": True,
        "add_circulation": False,
        "add_fines": False,
        "add_holds": False,
        "add_accessibility": False,
        "role": UserRole.CHILD,
        "date_of_birth": date.today() - timedelta(days=365*10),  # 10 years old
        "parent_guardian_email": "guardian@l30.org",
        "parental_consent_given": True,
    },
    {
        "email": "patron.accessibility@l30.org",
        "password": "Patron123!",
        "first_name": "Alex",
        "last_name": "Access",
        "scenario": "Patron with accessibility preferences",
        "patron_status": PatronStatus.ACTIVE,
        "notice_preference": NoticePreference.EMAIL,
        "track_reading_history": True,
        "add_circulation": False,
        "add_fines": False,
        "add_holds": False,
        "add_accessibility": True,
        "accessibility_needs": "Dyslexic - prefers sans-serif fonts and high contrast",
    },
]


async def get_or_create_catalog_items(db, count: int = 20):
    """Get existing catalog items or create new ones."""
    result = await db.execute(select(CatalogItem).limit(count))
    items = result.scalars().all()

    if len(items) >= count:
        return items[:count]

    print(f"  ⚠️  Warning: Only {len(items)} catalog items found")
    return items


async def get_or_create_item_copies(db, count: int = 20):
    """Get existing item copies, deduplicated by catalog_item_id and excluding items with active checkouts."""
    from sqlalchemy import text as sa_text

    # Get catalog_item_ids that already have active checkouts
    result = await db.execute(sa_text(
        "SELECT item_id FROM checkouts WHERE status = 'active'"
    ))
    active_checkout_item_ids = {row[0] for row in result.fetchall()}

    result = await db.execute(select(ItemCopy))
    all_items = result.scalars().all()

    # Deduplicate by catalog_item_id and exclude already-checked-out items
    seen_catalog_ids = set()
    items = []
    for item in all_items:
        if item.catalog_item_id not in seen_catalog_ids and item.catalog_item_id not in active_checkout_item_ids:
            seen_catalog_ids.add(item.catalog_item_id)
            items.append(item)

    if len(items) >= count:
        return items[:count]

    print(f"  ⚠️  Warning: Only {len(items)} available unique catalog item copies found (need {count})")
    return items


async def get_admin_user(db):
    """Get the admin user for block/suspend operations."""
    result = await db.execute(
        select(User).where((User.role == UserRole.ADMIN) | (User.role == UserRole.STAFF))
    )
    admin = result.scalars().first()
    return admin


async def seed_diverse_patrons():
    """Seed diverse patron test data."""
    async with AsyncSessionLocal() as db:
        print("\n" + "=" * 80)
        print("SEEDING DIVERSE PATRON TEST DATA")
        print("=" * 80 + "\n")

        created_count = 0
        skipped_count = 0
        _ = None

        # Get catalog items and item copies for circulation
        catalog_items = await get_or_create_catalog_items(db, 50)
        item_copies = await get_or_create_item_copies(db, 50)
        admin_user = await get_admin_user(db)

        if not catalog_items or not item_copies:
            print("❌ ERROR: Catalog items or item copies not found.")
            print("   Please run seed_comprehensive.py and seed_item_copies.py first.\n")
            return 0, skipped_count

        # Get or create reading programs
        result = await db.execute(select(ReadingProgram).limit(1))
        reading_program = result.scalars().first()

        # Get or create events
        result = await db.execute(select(Event).limit(3))
        events = result.scalars().all()

        # Get or create courses
        result = await db.execute(select(Course).limit(2))
        courses = result.scalars().all()

        item_idx = 0  # Track which item_copies have been used

        for patron_data in DIVERSE_PATRONS:
            email = patron_data["email"]
            role = patron_data.get("role", UserRole.PATRON)

            # Check if patron already exists
            result = await db.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"⊘ SKIPPED: {email}")
                print("  Reason: Account already exists\n")
                skipped_count += 1
                continue

            # Create patron
            try:
                dob = patron_data.get("date_of_birth")
                user = User(
                    email=email,
                    password_hash=hash_password(patron_data["password"]),
                    first_name=patron_data["first_name"],
                    last_name=patron_data["last_name"],
                    role=role,
                    is_active=True,
                    patron_status=patron_data.get("patron_status", PatronStatus.ACTIVE),
                    notice_preference=patron_data.get("notice_preference", NoticePreference.EMAIL),
                    email_verified=True,
                    track_reading_history=patron_data.get("track_reading_history", False),
                    accessibility_needs=patron_data.get("accessibility_needs"),
                    date_of_birth=dob,
                )

                # Add suspension info if suspended
                if patron_data.get("patron_status") == PatronStatus.SUSPENDED:
                    user.suspension_reason = patron_data.get("suspension_reason")
                    user.suspended_at = datetime.now(timezone.utc)
                    user.suspended_until = patron_data.get("suspended_until")

                # Add block info if blocked
                if patron_data.get("patron_status") == PatronStatus.BLOCKED:
                    user.block_reason = patron_data.get("block_reason")
                    user.blocked_at = patron_data.get("blocked_at", datetime.now(timezone.utc))
                    if admin_user:
                        user.blocked_by_id = admin_user.id

                db.add(user)
                await db.flush()

                print(f"✓ CREATED: {email}")
                print(f"  Name: {user.full_name}")
                print(f"  Role: {user.role.value}")
                print(f"  Status: {user.patron_status.value}")
                print(f"  Scenario: {patron_data['scenario']}\n")

                # Handle guardian relationship for child patron
                if patron_data.get("parent_guardian_email"):
                    parent_email = patron_data["parent_guardian_email"]
                    result = await db.execute(
                        select(User).where(User.email == parent_email)
                    )
                    parent = result.scalar_one_or_none()
                    if parent:
                        user.parent_guardian_id = parent.id
                        user.parental_consent_given = patron_data.get("parental_consent_given", False)
                        user.parental_consent_date = datetime.now(timezone.utc)
                        print(f"  👨‍👩‍👧 Guardian: {parent.full_name}\n")

                # Remember guardian for later child associations
                if role == UserRole.PATRON and "guardian" in email:
                    _ = user

                created_count += 1

                # Add circulation data if specified (use offset items to avoid unique constraint)
                if patron_data.get("add_circulation"):
                    circ_type = patron_data.get("add_circulation")
                    # Allocate items based on what each type needs
                    if circ_type == "overdue":
                        needed = 1
                    elif circ_type == "at_limit":
                        needed = min(10, len(item_copies) - item_idx)
                    elif circ_type == "reading_history":
                        needed = min(5, len(item_copies) - item_idx)
                    else:
                        needed = min(5, len(item_copies) - item_idx)
                    patron_items = item_copies[item_idx:item_idx + needed]
                    patron_catalog = catalog_items[item_idx:item_idx + needed] if item_idx < len(catalog_items) else []
                    if patron_items:
                        await add_circulation_data(
                            db, user, patron_catalog, patron_items, circ_type
                        )
                        # Only advance index for active checkouts (returned ones don't conflict)
                        if circ_type in ("overdue", "at_limit"):
                            item_idx += len(patron_items)
                    else:
                        print("  ⚠️  No items available for circulation data")

                # Add fines if specified
                if patron_data.get("add_fines"):
                    await add_fines(db, user)

                # Add holds if specified
                if patron_data.get("add_holds"):
                    await add_holds(
                        db, user, catalog_items, patron_data.get("add_holds")
                    )

                # Add reading program enrollment
                if patron_data.get("add_program_enrollment") and reading_program:
                    await add_program_enrollment(db, user, reading_program)

                # Add event registration
                if patron_data.get("add_event_registration") and events:
                    await add_event_registration(db, user, events)

                # Add course enrollment
                if patron_data.get("add_course_enrollment") and courses:
                    await add_course_enrollment(db, user, courses)

                # Add accessibility preferences
                if patron_data.get("add_accessibility"):
                    await add_accessibility_preferences(db, user)

            except Exception as e:
                await db.rollback()
                print(f"✗ ERROR: {email}")
                print(f"  Reason: {str(e)}\n")
                continue

        # Commit all changes
        try:
            await db.commit()
            print("=" * 80)
            print(f"SEED COMPLETE: {created_count} created, {skipped_count} skipped")
            print("=" * 80 + "\n")
            return created_count, skipped_count
        except Exception as e:
            await db.rollback()
            print(f"\n✗ COMMIT FAILED: {str(e)}\n")
            raise


async def add_circulation_data(db, user, catalog_items, item_copies, circulation_type):
    """Add circulation data to patron."""
    now = datetime.now(timezone.utc)

    if circulation_type == "overdue":
        # Create an overdue checkout
        if item_copies:
            checkout = Checkout(
                user_id=user.id,
                item_copy_id=item_copies[0].id,
                item_id=item_copies[0].catalog_item_id,
                status=CheckoutStatus.active,
                checked_out_at=now - timedelta(days=30),
                due_date=now - timedelta(days=5),
            )
            db.add(checkout)
            print(f"  📚 Added overdue checkout (due {5} days ago)")

    elif circulation_type == "at_limit":
        # Create active checkouts up to available items (typical checkout limit is 10)
        checkout_count = min(10, len(item_copies))
        for i in range(checkout_count):
            checkout = Checkout(
                user_id=user.id,
                item_copy_id=item_copies[i].id,
                item_id=item_copies[i].catalog_item_id,
                status=CheckoutStatus.active,
                checked_out_at=now - timedelta(days=5),
                due_date=now + timedelta(days=16),
            )
            db.add(checkout)
        print(f"  📚 Added {checkout_count} active checkouts (at/near checkout limit)")

    elif circulation_type == "reading_history":
        # Create multiple checkouts showing reading history
        for i in range(5):
            if i < len(item_copies):
                checkout = Checkout(
                    user_id=user.id,
                    item_copy_id=item_copies[i].id,
                    item_id=item_copies[i].catalog_item_id,
                    status=CheckoutStatus.returned,
                    checked_out_at=now - timedelta(days=60 - i * 10),
                    due_date=now - timedelta(days=50 - i * 10),
                    returned_at=now - timedelta(days=45 - i * 10),
                )
                db.add(checkout)
        print("  📚 Added 5 completed checkouts (reading history)")


async def add_fines(db, user):
    """Add unpaid fines to patron."""
    now = datetime.now(timezone.utc)

    fines_data = [
        (Decimal("15.00"), "Overdue item - 10 days"),
        (Decimal("12.50"), "Overdue item - 8 days"),
    ]

    for amount, description in fines_data:
        fine = Fine(
            user_id=user.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=amount,
            description=description,
            created_at=now - timedelta(days=3),
        )
        db.add(fine)

    total_fines = sum(Decimal(f[0]) for f in fines_data)
    print(f"  💰 Added fines totaling ${total_fines}")


async def add_holds(db, user, catalog_items, holds_type):
    """Add holds to patron."""
    now = datetime.now(timezone.utc)

    if holds_type == "active":
        # Create active holds
        for i in range(3):
            if i < len(catalog_items):
                hold = Hold(
                    user_id=user.id,
                    item_id=catalog_items[i].id,
                    status=HoldStatus.pending,
                    position=i + 1,
                    created_at=now - timedelta(days=5),
                )
                db.add(hold)
        print("  ⏱️  Added 3 active holds (pending)")

    elif holds_type == "expired":
        # Create expired holds
        for i in range(2):
            if i < len(catalog_items):
                hold = Hold(
                    user_id=user.id,
                    item_id=catalog_items[i].id,
                    status=HoldStatus.expired,
                    position=1,
                    created_at=now - timedelta(days=45),
                    expires_at=now - timedelta(days=5),
                )
                db.add(hold)
        print("  ❌ Added 2 expired holds")


async def add_program_enrollment(db, user, program):
    """Add reading program enrollment."""
    registration = ReadingRegistration(
        user_id=user.id,
        program_id=program.id,
        registered_at=datetime.now(timezone.utc),
    )
    db.add(registration)
    print(f"  📖 Enrolled in reading program: {program.name}")


async def add_event_registration(db, user, events):
    """Add event registrations."""
    for event in events[:2]:
        registration = EventRegistration(
            event_id=event.id,
            patron_name=user.full_name,
            patron_email=user.email,
            status=RegistrationStatus.CONFIRMED.value,
            registered_at=datetime.now(timezone.utc),
        )
        db.add(registration)
    print(f"  🎪 Registered for {min(2, len(events))} events")


async def add_course_enrollment(db, user, courses):
    """Add course enrollments."""
    for course in courses[:2]:
        # Check if enrollment already exists
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
    print(f"  🎓 Enrolled in {min(2, len(courses))} courses")


async def add_accessibility_preferences(db, user):
    """Add accessibility preferences for patron."""
    prefs = UserPreferences(
        user_id=user.id,
        dyslexia_font=True,
        high_contrast=True,
        reduced_motion=False,
        focus_mode="deep_dive",
        hide_gamification=False,
    )
    db.add(prefs)
    print("  ♿ Added accessibility preferences (dyslexia font, high contrast)")


async def verify_diverse_patrons():
    """Verify that diverse patrons were created successfully."""
    async with AsyncSessionLocal() as db:
        print("=" * 80)
        print("VERIFYING DIVERSE PATRONS")
        print("=" * 80 + "\n")

        for patron_data in DIVERSE_PATRONS:
            email = patron_data["email"]

            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if user:
                status_symbol = "✓"
                print(f"{status_symbol} VERIFIED: {email}")
                print(f"  ID: {user.id}")
                print(f"  Name: {user.full_name}")
                print(f"  Status: {user.patron_status.value}")
                print(f"  Scenario: {patron_data['scenario']}\n")
            else:
                print(f"✗ NOT FOUND: {email}\n")

        # Print summary
        result = await db.execute(
            select(User).where(
                User.email.in_([patron["email"] for patron in DIVERSE_PATRONS])
            )
        )
        patrons = result.scalars().all()

        print("=" * 80)
        print(f"VERIFICATION COMPLETE: {len(patrons)}/{len(DIVERSE_PATRONS)} patrons found")
        print("=" * 80 + "\n")

        # Detailed stats
        print("PATRON STATUS BREAKDOWN:")
        for status in PatronStatus:
            count = sum(1 for p in patrons if p.patron_status == status)
            if count > 0:
                print(f"  {status.value:12} {count} patron(s)")

        print("\nNOTICE PREFERENCE BREAKDOWN:")
        for pref in NoticePreference:
            count = sum(1 for p in patrons if p.notice_preference == pref)
            if count > 0:
                print(f"  {pref.value:8} {count} patron(s)")

        print("\nTEST CREDENTIALS:")
        print("  Base URL: http://localhost:8000/api/v1")
        print("  Each patron can log in with their email and 'Patron123!' (or variant)\n")

        return len(patrons) == len(DIVERSE_PATRONS)


async def main():
    """Main entry point for the seed script."""
    try:
        # Seed patrons
        created, skipped = await seed_diverse_patrons()

        # Verify patrons
        success = await verify_diverse_patrons()

        if success or created > 0:
            print("✓ DIVERSE PATRONS SEED SCRIPT COMPLETED SUCCESSFULLY\n")
            return 0
        else:
            print("✗ DIVERSE PATRONS SEED SCRIPT FAILED\n")
            return 1

    except Exception as e:
        print(f"\n✗ Error during seeding: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
