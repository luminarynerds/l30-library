#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Board Meetings Seeder for Bébé Memorial Library
Seeds board meeting data for the public board pages
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@database:5432/lsc_library")
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def get_board_meetings():
    """Generate board meetings - past and upcoming."""
    now = datetime.now(timezone.utc)

    # Helper to create meeting datetime at specific time
    def meeting_time(days_offset, hour=18, minute=0):
        base = now + timedelta(days=days_offset)
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0)

    meetings = [
        # Past meetings (completed)
        {
            "meeting_type": "regular",
            "title": "Regular Board Meeting - December 2025",
            "description": "Monthly board meeting. Agenda includes budget review for Q4, discussion of 2026 strategic priorities, and library director's report.",
            "scheduled_date": meeting_time(-45),
            "start_time": meeting_time(-45, 18, 0),
            "end_time": meeting_time(-45, 20, 0),
            "location": "Main Branch - Community Room",
            "is_virtual": True,
            "virtual_meeting_url": "https://zoom.us/j/example",
            "is_cancelled": False,
        },
        {
            "meeting_type": "regular",
            "title": "Regular Board Meeting - January 2026",
            "description": "Monthly board meeting. Agenda includes approval of 2026 budget, review of holiday circulation stats, and discussion of summer reading program planning.",
            "scheduled_date": meeting_time(-14),
            "start_time": meeting_time(-14, 18, 0),
            "end_time": meeting_time(-14, 20, 0),
            "location": "Main Branch - Community Room",
            "is_virtual": True,
            "virtual_meeting_url": "https://zoom.us/j/example",
            "is_cancelled": False,
        },
        # Upcoming meetings
        {
            "meeting_type": "regular",
            "title": "Regular Board Meeting - February 2026",
            "description": "Monthly board meeting. Agenda includes review of January circulation, technology upgrade proposal, and Elmdale Branch renovation update.",
            "scheduled_date": meeting_time(12),
            "start_time": meeting_time(12, 18, 0),
            "end_time": meeting_time(12, 20, 0),
            "location": "Main Branch - Community Room",
            "is_virtual": True,
            "virtual_meeting_url": "https://zoom.us/j/example",
            "is_cancelled": False,
        },
        {
            "meeting_type": "regular",
            "title": "Regular Board Meeting - March 2026",
            "description": "Monthly board meeting. Agenda to be posted 48 hours in advance.",
            "scheduled_date": meeting_time(40),
            "start_time": meeting_time(40, 18, 0),
            "end_time": meeting_time(40, 20, 0),
            "location": "Main Branch - Community Room",
            "is_virtual": True,
            "virtual_meeting_url": "https://zoom.us/j/example",
            "is_cancelled": False,
        },
        # Special meetings
        {
            "meeting_type": "special",
            "title": "Special Meeting: Strategic Plan Review",
            "description": "Special session to review and discuss the library's 5-year strategic plan progress. Public input welcome.",
            "scheduled_date": meeting_time(25),
            "start_time": meeting_time(25, 17, 0),
            "end_time": meeting_time(25, 19, 0),
            "location": "Main Branch - Community Room",
            "is_virtual": True,
            "virtual_meeting_url": "https://zoom.us/j/example",
            "is_cancelled": False,
        },
        {
            "meeting_type": "committee",
            "title": "Finance Committee Meeting",
            "description": "Finance Committee review of Q1 expenditures and grant opportunities.",
            "scheduled_date": meeting_time(8),
            "start_time": meeting_time(8, 16, 0),
            "end_time": meeting_time(8, 17, 30),
            "location": "Main Branch - Conference Room A",
            "is_virtual": False,
            "virtual_meeting_url": None,
            "is_cancelled": False,
        },
        {
            "meeting_type": "workshop",
            "title": "Board Workshop: Community Needs Assessment Results",
            "description": "Workshop to review results of the 2025 community needs assessment survey. No formal votes will be taken.",
            "scheduled_date": meeting_time(18),
            "start_time": meeting_time(18, 14, 0),
            "end_time": meeting_time(18, 16, 0),
            "location": "Elmdale Branch - Meeting Room",
            "is_virtual": True,
            "virtual_meeting_url": "https://zoom.us/j/example",
            "is_cancelled": False,
        },
        # Cancelled meeting example
        {
            "meeting_type": "regular",
            "title": "Regular Board Meeting - November 2025",
            "description": "Monthly board meeting.",
            "scheduled_date": meeting_time(-75),
            "start_time": meeting_time(-75, 18, 0),
            "end_time": meeting_time(-75, 20, 0),
            "location": "Main Branch - Community Room",
            "is_virtual": True,
            "virtual_meeting_url": "https://zoom.us/j/example",
            "is_cancelled": True,
            "cancellation_reason": "Cancelled due to inclement weather. Rescheduled items added to December meeting agenda.",
        },
    ]

    return meetings


async def seed_board_meetings():
    """Seed board meetings for public pages."""
    print("=" * 70)
    print("📅 LSC Library Board Meetings Seeder")
    print("=" * 70)

    meetings = get_board_meetings()

    try:
        # First, get a valid user ID for created_by_id (required field)
        async with async_session() as session:
            result = await session.execute(
                text("SELECT id FROM users WHERE role IN ('ADMIN', 'STAFF') LIMIT 1")
            )
            row = result.fetchone()
            if not row:
                # Try to get any user
                result = await session.execute(text("SELECT id FROM users LIMIT 1"))
                row = result.fetchone()

            if not row:
                print("  ⚠️  No users found in database. Creating a placeholder admin user...")
                # Create a minimal admin user for seeding purposes
                await session.execute(
                    text("""
                        INSERT INTO users (email, hashed_password, role, is_active, created_at)
                        VALUES ('admin@lsclibrary.org', 'placeholder', 'ADMIN', true, NOW())
                        ON CONFLICT (email) DO NOTHING
                    """)
                )
                await session.commit()
                result = await session.execute(
                    text("SELECT id FROM users WHERE email = 'admin@lsclibrary.org'")
                )
                row = result.fetchone()

            created_by_id = row[0] if row else 1

            added = 0
            for meeting in meetings:
                # Check if meeting already exists
                result = await session.execute(
                    text("SELECT id FROM board_meetings WHERE title = :title AND scheduled_date = :date"),
                    {"title": meeting["title"], "date": meeting["scheduled_date"]}
                )
                if result.fetchone():
                    print(f"  ℹ️  '{meeting['title']}' already exists, skipping")
                    continue

                # Insert meeting
                await session.execute(
                    text("""
                        INSERT INTO board_meetings
                        (meeting_type, title, description, scheduled_date, start_time, end_time,
                         location, is_virtual, virtual_meeting_url, is_cancelled, cancellation_reason,
                         created_by_id)
                        VALUES
                        (:meeting_type, :title, :description, :scheduled_date, :start_time, :end_time,
                         :location, :is_virtual, :virtual_meeting_url, :is_cancelled, :cancellation_reason,
                         :created_by_id)
                    """),
                    {
                        "meeting_type": meeting["meeting_type"],
                        "title": meeting["title"],
                        "description": meeting["description"],
                        "scheduled_date": meeting["scheduled_date"],
                        "start_time": meeting["start_time"],
                        "end_time": meeting["end_time"],
                        "location": meeting["location"],
                        "is_virtual": meeting["is_virtual"],
                        "virtual_meeting_url": meeting.get("virtual_meeting_url"),
                        "is_cancelled": meeting["is_cancelled"],
                        "cancellation_reason": meeting.get("cancellation_reason"),
                        "created_by_id": created_by_id,
                    }
                )
                added += 1
                status = "🚫 CANCELLED" if meeting["is_cancelled"] else meeting["meeting_type"].upper()
                print(f"  ✅ Added '{meeting['title']}' [{status}]")

            await session.commit()
            print(f"\n{'=' * 70}")
            print(f"✅ Seeding Complete! Added {added} board meetings")
            print(f"{'=' * 70}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(seed_board_meetings())
