#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Reading Programs Seeder for Bébé Memorial Library
Seeds reading programs data for the public reading programs pages using ORM models.
"""

import sys
import asyncio
from pathlib import Path
from datetime import date

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.models.reading import (
    ReadingProgram,
    ReadingProgramType,
    ReadingRegistration,
    ReadingLogEntry,
    ReadingAchievement,
)
from app.models.user import User, UserRole


def get_reading_programs():
    """Generate reading programs for different audiences and seasons."""
    today = date.today()
    current_year = today.year

    programs = [
        {
            "name": f"Summer Reading Challenge {current_year - 1}-{current_year} - Kids",
            "description": "Read your way through summer! Log books and minutes to earn prizes and badges.",
            "program_type": "summer",
            "age_group": "Children",
            "target_age_min": 0,
            "target_age_max": 12,
            "start_date": date(current_year - 1, 6, 1),
            "end_date": date(current_year, 8, 15),
            "reading_goal_type": "books",
            "reading_goal_value": 20,
            "is_active": True,
        },
        {
            "name": f"Summer Reading Challenge {current_year - 1}-{current_year} - Teens",
            "description": "Level up your summer with books! Track your reading, unlock achievements, and compete with friends.",
            "program_type": "summer",
            "age_group": "Teens",
            "target_age_min": 13,
            "target_age_max": 18,
            "start_date": date(current_year - 1, 6, 1),
            "end_date": date(current_year, 8, 15),
            "reading_goal_type": "books",
            "reading_goal_value": 10,
            "is_active": True,
        },
        {
            "name": f"Summer Reading Challenge {current_year - 1}-{current_year} - Adults",
            "description": "Rediscover the joy of reading this summer! Join our adult summer reading program.",
            "program_type": "summer",
            "age_group": "Adults",
            "target_age_min": 18,
            "target_age_max": None,
            "start_date": date(current_year - 1, 6, 1),
            "end_date": date(current_year, 8, 15),
            "reading_goal_type": "books",
            "reading_goal_value": 5,
            "is_active": True,
        },
        {
            "name": "Cozy Winter Reading Challenge 2026",
            "description": "Beat the winter blues with books! Track your reading during the cold months.",
            "program_type": "winter",
            "age_group": "All Ages",
            "target_age_min": None,
            "target_age_max": None,
            "start_date": date(current_year, 1, 1),
            "end_date": date(current_year, 2, 28),
            "reading_goal_type": "minutes",
            "reading_goal_value": 500,
            "is_active": True,
        },
        {
            "name": "1000 Books Before Kindergarten",
            "description": "Start your child's reading journey early! Track 1,000 books read aloud.",
            "program_type": "year_round",
            "age_group": "Children",
            "target_age_min": 0,
            "target_age_max": 5,
            "start_date": date(current_year, 1, 1),
            "end_date": date(current_year + 2, 12, 31),
            "reading_goal_type": "books",
            "reading_goal_value": 1000,
            "is_active": True,
        },
        {
            "name": "Read to Reduce",
            "description": "Log reading minutes to pay down a virtual reading balance.",
            "program_type": "year_round",
            "age_group": "Children",
            "target_age_min": 5,
            "target_age_max": 14,
            "start_date": date(current_year, 1, 1),
            "end_date": date(current_year, 12, 31),
            "reading_goal_type": "minutes",
            "reading_goal_value": 1200,
            "is_active": True,
        },
        {
            "name": "Adult Book Bingo 2026",
            "description": "Challenge yourself to read outside your comfort zone!",
            "program_type": "year_round",
            "age_group": "Adults",
            "target_age_min": 18,
            "target_age_max": None,
            "start_date": date(current_year, 1, 1),
            "end_date": date(current_year, 12, 31),
            "reading_goal_type": "books",
            "reading_goal_value": 25,
            "is_active": True,
        },
        {
            "name": "March is Reading Month Challenge",
            "description": "A special month-long reading challenge for families.",
            "program_type": "special",
            "age_group": "All Ages",
            "target_age_min": None,
            "target_age_max": None,
            "start_date": date(current_year, 3, 1),
            "end_date": date(current_year, 3, 31),
            "reading_goal_type": "minutes",
            "reading_goal_value": 450,
            "is_active": True,
        },
        {
            "name": "Indigenous Authors Spotlight",
            "description": "Celebrating Indigenous authors and stories throughout November.",
            "program_type": "special",
            "age_group": "All Ages",
            "target_age_min": None,
            "target_age_max": None,
            "start_date": date(current_year, 11, 1),
            "end_date": date(current_year, 11, 30),
            "reading_goal_type": "books",
            "reading_goal_value": 3,
            "is_active": True,
        },
        {
            "name": "Spooky Season Reading Challenge",
            "description": "Get into the Halloween spirit with spooky reads!",
            "program_type": "special",
            "age_group": "Teens",
            "target_age_min": 13,
            "target_age_max": None,
            "start_date": date(current_year, 10, 1),
            "end_date": date(current_year, 10, 31),
            "reading_goal_type": "books",
            "reading_goal_value": 4,
            "is_active": True,
        },
    ]

    return programs


async def seed_reading_programs():
    """Seed reading programs using ORM models."""
    print("\n" + "=" * 70)
    print("LSC Reading Programs Seeder")
    print("=" * 70 + "\n")

    programs = get_reading_programs()

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(User).where(User.role.in_([UserRole.ADMIN, UserRole.STAFF])).limit(1)
            )
            created_by_user = result.scalar_one_or_none()
            created_by_id = created_by_user.id if created_by_user else None

            added = 0
            for program_data in programs:
                result = await session.execute(
                    select(ReadingProgram).where(ReadingProgram.name == program_data["name"])
                )
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"  SKIPPED: '{program_data['name']}'")
                    continue

                try:
                    program = ReadingProgram(
                        name=program_data["name"],
                        description=program_data["description"],
                        program_type=ReadingProgramType(program_data["program_type"]),
                        age_group=program_data["age_group"],
                        target_age_min=program_data["target_age_min"],
                        target_age_max=program_data["target_age_max"],
                        start_date=program_data["start_date"],
                        end_date=program_data["end_date"],
                        reading_goal_type=program_data["reading_goal_type"],
                        reading_goal_value=program_data["reading_goal_value"],
                        is_active=program_data["is_active"],
                        created_by_id=created_by_id,
                        is_school_program=False,
                        grade_levels=[],
                        reading_levels=[],
                    )

                    session.add(program)
                    await session.flush()
                    added += 1

                    goal_display = (
                        f"{program_data['reading_goal_value']} {program_data['reading_goal_type']}"
                    )
                    print(f"  CREATED: {program_data['name']}")
                    print(f"  Goal: {goal_display}, ID: {program.id}\n")

                except Exception as e:  # noqa: BLE001
                    await session.rollback()
                    print(f"  ERROR: {str(e)}\n")

            await session.commit()
            print("=" * 70)
            print(f"SEEDED: {added} programs")
            print("=" * 70 + "\n")
            return added

        except Exception as e:  # noqa: BLE001
            print(f"ERROR: {str(e)}\n")
            raise


async def seed_reading_registrations():
    """Seed reading registrations."""
    print("\n" + "=" * 70)
    print("LSC Reading Registrations Seeder")
    print("=" * 70 + "\n")

    async with AsyncSessionLocal() as session:
        try:
            programs_result = await session.execute(select(ReadingProgram))
            programs = programs_result.scalars().all()

            users_result = await session.execute(
                select(User).where(User.role == UserRole.PATRON).limit(10)
            )
            patrons = users_result.scalars().all()

            if not programs or not patrons:
                print("  WARNING: No programs or patrons found\n")
                return 0

            added = 0
            for program in programs[:3]:
                for patron in patrons[:5]:
                    result = await session.execute(
                        select(ReadingRegistration).where(
                            (ReadingRegistration.user_id == patron.id)
                            & (ReadingRegistration.program_id == program.id)
                        )
                    )
                    if result.scalar_one_or_none():
                        continue

                    try:
                        reg = ReadingRegistration(
                            user_id=patron.id,
                            program_id=program.id,
                            goal_target=program.reading_goal_value,
                        )
                        session.add(reg)
                        await session.flush()
                        added += 1

                        print(f"  CREATED: {patron.first_name} -> {program.name}")
                        print(f"  Registration ID: {reg.id}\n")

                    except Exception as e:  # noqa: BLE001
                        await session.rollback()
                        print(f"  ERROR: {str(e)}\n")

            await session.commit()
            print("=" * 70)
            print(f"SEEDED: {added} registrations")
            print("=" * 70 + "\n")
            return added

        except Exception as e:  # noqa: BLE001
            print(f"ERROR: {str(e)}\n")
            raise


async def seed_reading_log_entries():
    """Seed reading log entries."""
    print("\n" + "=" * 70)
    print("LSC Reading Log Entries Seeder")
    print("=" * 70 + "\n")

    async with AsyncSessionLocal() as session:
        try:
            registrations_result = await session.execute(select(ReadingRegistration))
            registrations = registrations_result.scalars().all()

            if not registrations:
                print("  WARNING: No registrations found\n")
                return 0

            added = 0
            for reg in registrations:
                for i in range(3):
                    try:
                        entry = ReadingLogEntry(
                            registration_id=reg.id,
                            books_read=i + 1,
                            minutes_read=(i + 1) * 30,
                            pages_read=(i + 1) * 50,
                            title=f"Sample Book {i + 1}",
                            author=f"Author {i + 1}",
                            notes=f"Read on day {i + 1}",
                            rating=4 + (i % 2),
                        )
                        session.add(entry)
                        await session.flush()
                        added += 1

                        print(f"  CREATED: Log entry for registration {reg.id}")
                        print(f"  Books: {entry.books_read}, Minutes: {entry.minutes_read}\n")

                    except Exception as e:  # noqa: BLE001
                        await session.rollback()
                        print(f"  ERROR: {str(e)}\n")

            await session.commit()
            print("=" * 70)
            print(f"SEEDED: {added} log entries")
            print("=" * 70 + "\n")
            return added

        except Exception as e:  # noqa: BLE001
            print(f"ERROR: {str(e)}\n")
            raise


async def seed_reading_achievements():
    """Seed reading achievements."""
    print("\n" + "=" * 70)
    print("LSC Reading Achievements Seeder")
    print("=" * 70 + "\n")

    templates = [
        {
            "badge_id": "first-book",
            "badge_name": "First Book Reader",
            "badge_description": "Read your first book!",
        },
        {"badge_id": "bookworm", "badge_name": "Bookworm", "badge_description": "Read 10 books!"},
        {
            "badge_id": "speed-reader",
            "badge_name": "Speed Reader",
            "badge_description": "Read 500+ minutes!",
        },
        {
            "badge_id": "goal-achiever",
            "badge_name": "Goal Achiever",
            "badge_description": "Reached your goal!",
        },
    ]

    async with AsyncSessionLocal() as session:
        try:
            registrations_result = await session.execute(select(ReadingRegistration))
            registrations = registrations_result.scalars().all()

            if not registrations:
                print("  WARNING: No registrations found\n")
                return 0

            added = 0
            for reg in registrations:
                for i in range(2):
                    template = templates[i % len(templates)]

                    result = await session.execute(
                        select(ReadingAchievement).where(
                            (ReadingAchievement.user_id == reg.user_id)
                            & (ReadingAchievement.program_id == reg.program_id)
                            & (ReadingAchievement.badge_id == template["badge_id"])
                        )
                    )
                    if result.scalar_one_or_none():
                        continue

                    try:
                        achievement = ReadingAchievement(
                            user_id=reg.user_id,
                            program_id=reg.program_id,
                            badge_id=template["badge_id"],
                            badge_name=template["badge_name"],
                            badge_description=template["badge_description"],
                        )
                        session.add(achievement)
                        await session.flush()
                        added += 1

                        print(f"  CREATED: {template['badge_name']}")
                        print(f"  User ID: {reg.user_id}, Program ID: {reg.program_id}\n")

                    except Exception as e:  # noqa: BLE001
                        await session.rollback()
                        print(f"  ERROR: {str(e)}\n")

            await session.commit()
            print("=" * 70)
            print(f"SEEDED: {added} achievements")
            print("=" * 70 + "\n")
            return added

        except Exception as e:  # noqa: BLE001
            print(f"ERROR: {str(e)}\n")
            raise


async def main():
    """Main entry point."""
    try:
        print("\n" + "=" * 70)
        print("READING PROGRAM DATA SEEDING - ORM VERSION")
        print("=" * 70)

        programs_added = await seed_reading_programs()
        registrations_added = await seed_reading_registrations()
        log_entries_added = await seed_reading_log_entries()
        achievements_added = await seed_reading_achievements()

        print("\n" + "=" * 70)
        print("SEEDING COMPLETE - SUMMARY")
        print("=" * 70)
        print(f"""
Programs: {programs_added}
Registrations: {registrations_added}
Log Entries: {log_entries_added}
Achievements: {achievements_added}

Total: {programs_added + registrations_added + log_entries_added + achievements_added} records
        """)
        print("=" * 70 + "\n")
        return 0

    except Exception as e:  # noqa: BLE001
        print(f"FATAL ERROR: {str(e)}\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
