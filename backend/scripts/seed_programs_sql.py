#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed Program and ProgramRegistration tables with realistic library program data.
Uses direct SQL to avoid ORM relationship issues.
"""

import asyncio
import sys
from datetime import datetime, date, time, timedelta
from pathlib import Path
from random import choice, randint, sample

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import async_session_maker


PROGRAM_TEMPLATES = [
    # Children's Programs
    ("Toddler Time", "storytime", "children", "Interactive storytime for ages 0-3"),
    ("Preschool Adventures", "storytime", "children", "Stories and crafts for ages 3-5"),
    ("LEGO Building Challenge", "arts_crafts", "children", "Creative construction"),
    ("Science Explorers", "stem", "children", "Hands-on experiments ages 8-12"),

    # Teen Programs
    ("YA Book Club", "book_club", "teen", "Young adult fiction discussion"),
    ("Teen Art Studio", "arts_crafts", "teen", "Painting and mixed media"),
    ("Robotics Workshop", "stem", "teen", "Build and program robots"),
    ("Graphic Novel Club", "book_club", "teen", "Visual storytelling"),

    # Adult Programs
    ("Mystery Lovers Book Club", "book_club", "adult", "Monthly mystery novel discussion"),
    ("Smartphone Basics", "technology", "adult", "Introduction to smartphone features"),
    ("Resume Building Workshop", "workshop", "adult", "Create professional resumes"),
    ("Knitting Circle", "arts_crafts", "adult", "Learn to knit or bring your project"),
    ("Job Search Strategies", "workshop", "adult", "Resume, interviews, networking"),

    # Senior Programs
    ("Silver Readers", "book_club", "senior", "Book discussion with large print"),
    ("Tech Help for Seniors", "technology", "senior", "One-on-one tech assistance"),
    ("Email Basics", "technology", "senior", "Setting up and using email safely"),

    # Family/All Ages
    ("Family Storytime", "storytime", "family", "Stories for the whole family"),
    ("Magic Show Spectacular", "performance", "all_ages", "Professional magician"),
    ("Local Author Reading", "performance", "all_ages", "Meet local writers"),
]

LOCATIONS = [
    "Community Room A",
    "Children's Story Corner",
    "Teen Zone",
    "Computer Lab",
    "Main Meeting Room",
]

FACILITATORS = [
    "Sarah Johnson",
    "Michael Chen",
    "Emily Rodriguez",
    "David Kim",
    "Jessica Martinez",
]


async def seed_programs():
    """Seed program data using direct SQL."""
    print("=" * 60)
    print("PROGRAM SEEDING SCRIPT (SQL)")
    print("=" * 60)

    async with async_session_maker() as session:
        try:
            # Get user IDs for facilitators and patrons
            staff_result = await session.execute(
                text("SELECT id FROM users WHERE role IN ('librarian', 'admin') LIMIT 10")
            )
            facilitator_ids = [row[0] for row in staff_result.fetchall()]

            patron_result = await session.execute(
                text("SELECT id FROM users WHERE role = 'patron' LIMIT 100")
            )
            patron_ids = [row[0] for row in patron_result.fetchall()]

            print(f"\n✅ Found {len(facilitator_ids)} staff users")
            print(f"✅ Found {len(patron_ids)} patrons")

            if not patron_ids:
                print("\n⚠️  No patrons found - programs will have no registrations")
                print("   Run: docker exec lsc-backend python3 /app/scripts/seed_test_accounts.py")

            # Generate programs
            programs_created = 0
            registrations_created = 0
            today = date.today()

            print("\n📚 Creating programs...")

            for offset_weeks in range(-12, 8):  # 12 weeks past, 8 weeks future
                program_date = today + timedelta(weeks=offset_weeks)

                # Skip most weekends
                if program_date.weekday() >= 5 and randint(1, 3) != 1:
                    continue

                # Create 1-2 programs per week
                for _ in range(randint(1, 2)):
                    title, prog_type, audience, description = choice(PROGRAM_TEMPLATES)

                    # Time slots
                    hour = choice([10, 14, 18])
                    start_time = time(hour=hour, minute=choice([0, 30]))
                    end_time = time(hour=hour + randint(1, 2), minute=choice([0, 30]))

                    # Status based on date
                    if program_date < today:
                        status = "completed"
                    elif program_date == today:
                        status = "in_progress"
                    else:
                        status = "scheduled"

                    # Capacity
                    max_capacity = randint(15, 30)

                    # Insert program
                    result = await session.execute(text("""
                        INSERT INTO programs (
                            title, description, program_type, audience, program_date,
                            start_time, end_time, location_name, is_virtual,
                            max_capacity, registration_required, expected_attendance,
                            actual_attendance, status, facilitator_name,
                            registered_count, attended_count, created_at, updated_at
                        ) VALUES (
                            :title, :desc, :type, :audience, :date,
                            :start, :end, :location, :virtual,
                            :capacity, :reg_req, :expected,
                            0, :status, :facilitator,
                            0, 0, NOW(), NOW()
                        ) RETURNING id
                    """), {
                        "title": title,
                        "desc": description,
                        "type": prog_type,
                        "audience": audience,
                        "date": program_date,
                        "start": start_time,
                        "end": end_time,
                        "location": choice(LOCATIONS),
                        "virtual": choice([True, False]),
                        "capacity": max_capacity,
                        "reg_req": prog_type != "storytime",
                        "expected": randint(int(max_capacity * 0.6), max_capacity),
                        "status": status,
                        "facilitator": choice(FACILITATORS) if facilitator_ids else "Staff",
                    })

                    program_id = result.scalar_one()
                    programs_created += 1

                    # Create registrations for completed programs
                    if status == "completed" and patron_ids and prog_type != "storytime":
                        num_reg = randint(int(max_capacity * 0.5), min(max_capacity, len(patron_ids)))
                        selected_patrons = sample(patron_ids, min(num_reg, len(patron_ids)))

                        attended_count = 0
                        for patron_id in selected_patrons:
                            attended = choice([True, True, True, False])  # 75% attendance
                            age_group = choice(["child_6_12", "teen_13_18", "adult_19_64", "senior_65_plus"])

                            await session.execute(text("""
                                INSERT INTO program_registrations (
                                    program_id, patron_id, status, attended,
                                    attended_at, age_group, resident_status,
                                    registered_at, created_at, updated_at
                                ) VALUES (
                                    :prog_id, :patron_id, :status, :attended,
                                    :attended_at, :age_group, :resident,
                                    :reg_at, NOW(), NOW()
                                )
                            """), {
                                "prog_id": program_id,
                                "patron_id": patron_id,
                                "status": "attended" if attended else "no_show",
                                "attended": attended,
                                "attended_at": datetime.combine(program_date, start_time) if attended else None,
                                "age_group": age_group,
                                "resident": choice(["resident", "non_resident"]),
                                "reg_at": program_date - timedelta(days=randint(1, 14)),
                            })

                            registrations_created += 1
                            if attended:
                                attended_count += 1

                        # Update program counts
                        await session.execute(text("""
                            UPDATE programs
                            SET registered_count = :reg, attended_count = :att, actual_attendance = :att
                            WHERE id = :id
                        """), {
                            "reg": len(selected_patrons),
                            "att": attended_count,
                            "id": program_id
                        })

            # Commit all
            await session.commit()

            print(f"\n✅ Created {programs_created} programs")
            print(f"✅ Created {registrations_created} registrations")

            # Show summary
            summary = await session.execute(text("""
                SELECT
                    status,
                    COUNT(*) as count,
                    SUM(registered_count) as total_registered,
                    SUM(attended_count) as total_attended
                FROM programs
                GROUP BY status
                ORDER BY status
            """))

            print("\n" + "=" * 60)
            print("SUMMARY BY STATUS")
            print("=" * 60)
            for row in summary:
                print(f"{row[0]:15} {row[1]:3} programs  |  {row[2] or 0:4} registered  |  {row[3] or 0:4} attended")

            print("\n✅ Program seeding complete!")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(seed_programs())
