#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed Program and ProgramRegistration tables with realistic library program data.

This script creates:
- Diverse library programs across different types and audiences
- Program registrations with realistic attendance patterns
- Demographics data for compliance reporting
- Historical and upcoming program schedules
"""

import asyncio
import sys
from datetime import datetime, date, time, timedelta
from pathlib import Path
from random import choice, randint, sample

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.program import (
    Program, ProgramRegistration,
    ProgramType, ProgramAudience, ProgramStatus, RegistrationStatus
)
from app.models.user import User, UserRole


# ==================== PROGRAM TEMPLATES ====================

PROGRAM_TEMPLATES = {
    ProgramType.STORYTIME: {
        ProgramAudience.CHILDREN: [
            ("Toddler Time", "Interactive storytime for ages 0-3 with songs and movement"),
            ("Preschool Adventures", "Stories, crafts, and activities for ages 3-5"),
            ("Baby & Me", "Lap-sit program for babies and caregivers"),
            ("Pajama Storytime", "Evening stories in PJs before bedtime"),
        ],
        ProgramAudience.FAMILY: [
            ("Family Storytime", "Stories and activities for the whole family"),
            ("Bilingual Storytime", "Stories in English and Spanish"),
        ]
    },
    ProgramType.BOOK_CLUB: {
        ProgramAudience.ADULT: [
            ("Mystery Lovers Book Club", "Monthly discussion of mystery novels"),
            ("Classics Reading Group", "Exploring literary classics together"),
            ("Non-Fiction Book Club", "Discussing current events and biographies"),
        ],
        ProgramAudience.TEEN: [
            ("YA Book Club", "Young adult fiction discussion group"),
            ("Graphic Novel Club", "Exploring visual storytelling"),
        ],
        ProgramAudience.SENIOR: [
            ("Silver Readers", "Book discussion for seniors with large print options"),
        ]
    },
    ProgramType.TECHNOLOGY: {
        ProgramAudience.ADULT: [
            ("Smartphone Basics", "Introduction to smartphone features and apps"),
            ("Social Media Safety", "Protecting your privacy online"),
            ("Resume Building Workshop", "Creating professional resumes digitally"),
        ],
        ProgramAudience.SENIOR: [
            ("Tech Help for Seniors", "One-on-one technology assistance"),
            ("Video Calling Made Easy", "Connect with family via Zoom/FaceTime"),
            ("Email Basics", "Setting up and using email safely"),
        ]
    },
    ProgramType.ARTS_CRAFTS: {
        ProgramAudience.CHILDREN: [
            ("Mini Makers", "Art projects for little hands ages 5-8"),
            ("LEGO Building Challenge", "Creative construction competition"),
        ],
        ProgramAudience.TEEN: [
            ("Teen Art Studio", "Painting, drawing, and mixed media"),
            ("DIY Crafts", "Upcycling and creative projects"),
        ],
        ProgramAudience.ADULT: [
            ("Adult Coloring Club", "Relaxing coloring with supplies provided"),
            ("Knitting Circle", "Learn to knit or bring your own project"),
        ]
    },
    ProgramType.STEM: {
        ProgramAudience.CHILDREN: [
            ("Science Explorers", "Hands-on science experiments ages 8-12"),
            ("Coding for Kids", "Introduction to programming with Scratch"),
        ],
        ProgramAudience.TEEN: [
            ("Robotics Workshop", "Build and program simple robots"),
            ("Chemistry Lab", "Safe experiments and demonstrations"),
        ]
    },
    ProgramType.WORKSHOP: {
        ProgramAudience.ADULT: [
            ("Job Search Strategies", "Resume, interviews, and networking"),
            ("Home Budgeting Basics", "Personal finance management"),
            ("Gardening 101", "Starting your first vegetable garden"),
            ("Genealogy Research", "Tracing your family history"),
        ]
    },
    ProgramType.PERFORMANCE: {
        ProgramAudience.ALL_AGES: [
            ("Magic Show Spectacular", "Professional magician performance"),
            ("Puppet Theater", "Interactive puppet show"),
            ("Local Author Reading", "Meet local writers"),
        ]
    },
    ProgramType.LECTURE: {
        ProgramAudience.ADULT: [
            ("Local History Talk", "Historical society presentation"),
            ("Health & Wellness Seminar", "Nutrition and exercise tips"),
            ("Travel Photography", "Tips from professional photographers"),
        ]
    }
}


async def create_programs(session: AsyncSession, facilitator_ids: list[int]) -> list[Program]:
    """Create diverse library programs."""
    programs = []
    today = date.today()

    print("\n📚 Creating library programs...")

    # Generate programs across different time periods
    for offset_weeks in range(-12, 8):  # 12 weeks past, 8 weeks future
        program_date = today + timedelta(weeks=offset_weeks)

        # Skip if not a weekday for most programs
        if program_date.weekday() >= 5:  # Weekend
            # Only create a few weekend programs
            if randint(1, 3) != 1:
                continue

        # Create 1-3 programs per week
        for _ in range(randint(1, 3)):
            # Pick random program type and audience
            prog_type = choice(list(PROGRAM_TEMPLATES.keys()))
            audiences = list(PROGRAM_TEMPLATES[prog_type].keys())
            audience = choice(audiences)

            # Pick template
            templates = PROGRAM_TEMPLATES[prog_type][audience]
            title, description = choice(templates)

            # Generate time slots
            hour = choice([10, 11, 14, 15, 18, 19])  # Morning, afternoon, evening
            start = time(hour=hour, minute=choice([0, 30]))
            end_hour = hour + randint(1, 2)
            end = time(hour=min(end_hour, 21), minute=choice([0, 30]))

            # Determine status based on date
            if program_date < today - timedelta(days=1):
                status = ProgramStatus.COMPLETED
            elif program_date < today:
                status = choice([ProgramStatus.COMPLETED, ProgramStatus.IN_PROGRESS])
            elif program_date == today:
                status = choice([ProgramStatus.SCHEDULED, ProgramStatus.IN_PROGRESS])
            else:
                status = ProgramStatus.SCHEDULED

            # Capacity varies by program type
            if prog_type in [ProgramType.STORYTIME, ProgramType.ARTS_CRAFTS]:
                max_capacity = randint(15, 25)
            elif prog_type in [ProgramType.BOOK_CLUB, ProgramType.TECHNOLOGY]:
                max_capacity = randint(10, 20)
            elif prog_type in [ProgramType.LECTURE, ProgramType.WORKSHOP]:
                max_capacity = randint(30, 50)
            else:
                max_capacity = randint(20, 40)

            # Create program
            program = Program(
                title=title,
                description=description,
                program_type=prog_type,
                audience=audience,
                program_date=program_date,
                start_time=start,
                end_time=end,
                location_name=choice([
                    "Community Room A",
                    "Children's Story Corner",
                    "Teen Zone",
                    "Computer Lab",
                    "Main Meeting Room",
                    "Quiet Reading Room"
                ]),
                is_virtual=choice([True, False]) if program_date > today else False,
                virtual_link=f"https://zoom.us/j/{randint(1000000000, 9999999999)}" if choice([True, False]) else None,
                max_capacity=max_capacity,
                registration_required=prog_type not in [ProgramType.STORYTIME, ProgramType.PERFORMANCE],
                expected_attendance=randint(int(max_capacity * 0.6), max_capacity),
                actual_attendance=0,  # Will be set based on registrations
                status=status,
                facilitator_id=choice(facilitator_ids) if facilitator_ids else None,
                facilitator_name=choice([
                    "Sarah Johnson", "Michael Chen", "Emily Rodriguez",
                    "David Kim", "Jessica Martinez", "Robert Taylor"
                ]),
                registered_count=0,  # Will be updated
                attended_count=0,  # Will be updated
                notes="Generated seed data for testing and demonstration",
            )

            programs.append(program)

    # Bulk insert
    session.add_all(programs)
    await session.flush()  # Get IDs

    print(f"✅ Created {len(programs)} programs")
    return programs


async def create_registrations(session: AsyncSession, programs: list[Program], patron_ids: list[int]):
    """Create program registrations with realistic patterns."""
    registrations = []

    print("\n👥 Creating program registrations...")

    for program in programs:
        # Skip if registration not required
        if not program.registration_required:
            # For drop-in programs, just set attendance
            if program.status == ProgramStatus.COMPLETED:
                program.actual_attendance = randint(
                    int(program.max_capacity * 0.3),
                    int(program.max_capacity * 0.9)
                )
            continue

        # Determine number of registrations
        if program.status == ProgramStatus.COMPLETED:
            # Past programs have actual registrations
            num_registered = randint(
                int(program.max_capacity * 0.5),
                min(program.max_capacity, len(patron_ids))
            )
        elif program.status in [ProgramStatus.SCHEDULED, ProgramStatus.IN_PROGRESS]:
            # Upcoming programs may not be full yet
            num_registered = randint(
                int(program.max_capacity * 0.3),
                int(program.max_capacity * 0.8)
            )
        else:
            num_registered = 0

        # Select random patrons (avoid duplicates)
        if num_registered > 0:
            selected_patrons = sample(
                patron_ids,
                min(num_registered, len(patron_ids))
            )

            for patron_id in selected_patrons:
                # Determine registration status
                if program.status == ProgramStatus.COMPLETED:
                    # Past programs - mix of attended and no-shows
                    reg_status = choice([
                        RegistrationStatus.ATTENDED,
                        RegistrationStatus.ATTENDED,
                        RegistrationStatus.ATTENDED,
                        RegistrationStatus.NO_SHOW,
                    ])
                    attended = reg_status == RegistrationStatus.ATTENDED
                    attended_at = datetime.combine(program.program_date, program.start_time) if attended else None
                else:
                    # Future programs
                    reg_status = RegistrationStatus.REGISTERED
                    attended = False
                    attended_at = None

                # Demographics for reporting
                age_group = choice([
                    "child_0_5", "child_6_12", "teen_13_18",
                    "adult_19_64", "senior_65_plus"
                ])

                registration = ProgramRegistration(
                    program_id=program.id,
                    patron_id=patron_id,
                    status=reg_status,
                    attended=attended,
                    attended_at=attended_at,
                    age_group=age_group,
                    resident_status=choice(["resident", "non_resident", "reciprocal"]),
                    demographics_data={
                        "age_group": age_group,
                        "first_time": choice([True, False]),
                        "returning": choice([True, False]),
                    }
                )
                registrations.append(registration)

            # Update program counts
            program.registered_count = len(selected_patrons)
            if program.status == ProgramStatus.COMPLETED:
                program.attended_count = sum(1 for r in registrations if r.program_id == program.id and r.attended)
                program.actual_attendance = program.attended_count

    # Bulk insert registrations
    if registrations:
        session.add_all(registrations)
        await session.flush()

    print(f"✅ Created {len(registrations)} program registrations")


async def main():
    """Seed program data."""
    print("=" * 60)
    print("PROGRAM SEEDING SCRIPT")
    print("=" * 60)

    async with async_session_maker() as session:
        try:
            # Get staff users for facilitators
            staff_result = await session.execute(
                select(User.id).where(User.role.in_([UserRole.STAFF, UserRole.ADMIN]))
            )
            facilitator_ids = [row[0] for row in staff_result.fetchall()]

            if not facilitator_ids:
                print("⚠️  No staff users found - creating programs without facilitators")
                facilitator_ids = []
            else:
                print(f"✅ Found {len(facilitator_ids)} staff users for facilitators")

            # Get patrons for registrations
            patron_result = await session.execute(
                select(User.id).where(User.role == UserRole.PATRON).limit(100)
            )
            patron_ids = [row[0] for row in patron_result.fetchall()]

            if not patron_ids:
                print("⚠️  No patrons found - programs will have no registrations")
                print("   Run seed_test_accounts.py first to create patron accounts")
                patron_ids = []
            else:
                print(f"✅ Found {len(patron_ids)} patrons for registrations")

            # Create programs
            programs = await create_programs(session, facilitator_ids)

            # Create registrations
            await create_registrations(session, programs, patron_ids)

            # Commit all changes
            await session.commit()

            print("\n" + "=" * 60)
            print("✅ PROGRAM SEEDING COMPLETE!")
            print("=" * 60)
            print("\nSummary:")
            print(f"  - Programs created: {len(programs)}")
            print(f"  - Date range: {min(p.program_date for p in programs)} to {max(p.program_date for p in programs)}")
            print(f"  - Program types: {len(set(p.program_type for p in programs))}")
            print(f"  - Audiences: {len(set(p.audience for p in programs))}")

            # Count by status
            completed = sum(1 for p in programs if p.status == ProgramStatus.COMPLETED)
            scheduled = sum(1 for p in programs if p.status == ProgramStatus.SCHEDULED)
            in_progress = sum(1 for p in programs if p.status == ProgramStatus.IN_PROGRESS)

            print("\n  Status breakdown:")
            print(f"    - Completed: {completed}")
            print(f"    - Scheduled: {scheduled}")
            print(f"    - In Progress: {in_progress}")

            print(f"\n  Total registrations: {sum(p.registered_count for p in programs)}")
            print(f"  Total attendance: {sum(p.attended_count for p in programs)}")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error seeding programs: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
