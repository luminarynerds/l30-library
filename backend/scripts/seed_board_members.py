#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Board Members Seeder for Bébé Memorial Library
Seeds board member data for the public board pages
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

# Board Members - typical small-town library board
BOARD_MEMBERS = [
    {
        "full_name": "Margaret 'Peggy' Thompson",
        "email": "pthompson@l30.org",
        "position": "president",
        "term_start_date": datetime(2023, 1, 1, tzinfo=timezone.utc),
        "term_end_date": datetime(2027, 12, 31, tzinfo=timezone.utc),
        "is_current": True,
        "bio": "Peggy has served on the board for 12 years and has been President since 2023. A retired elementary school teacher, she's passionate about early literacy and ensuring every child in Bébé Memorial has access to books. She led the initiative to expand our children's programming.",
        "public_email": "board.president@lsclibrary.org",
        "office_hours": "First Tuesday of each month, 10am-12pm at Main Branch",
    },
    {
        "full_name": "David Chen",
        "email": "dchen@chenaccounting.com",
        "position": "treasurer",
        "term_start_date": datetime(2022, 1, 1, tzinfo=timezone.utc),
        "term_end_date": datetime(2026, 12, 31, tzinfo=timezone.utc),
        "is_current": True,
        "bio": "David is a CPA with Chen & Associates and has been managing the library's financial oversight since 2022. He ensures our budget is transparent and that every dollar serves our community. He's also a huge mystery novel fan.",
        "public_email": "board.treasurer@lsclibrary.org",
        "office_hours": "By appointment",
    },
    {
        "full_name": "Rosa Martinez",
        "email": "rosa.martinez@email.com",
        "position": "secretary",
        "term_start_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "term_end_date": datetime(2028, 12, 31, tzinfo=timezone.utc),
        "is_current": True,
        "bio": "Rosa joined the board in 2024 after years of volunteering with the Friends of the Library. She works as a paralegal and brings organizational skills that help keep our meetings running smoothly. She championed making our meeting minutes more accessible online.",
        "public_email": "board.secretary@lsclibrary.org",
        "office_hours": "Third Wednesday of each month, 2pm-4pm at Main Branch",
    },
    {
        "full_name": "William 'Bill' Okonkwo",
        "email": "bill.okonkwo@l30.org",
        "position": "vice_president",
        "term_start_date": datetime(2021, 1, 1, tzinfo=timezone.utc),
        "term_end_date": datetime(2025, 12, 31, tzinfo=timezone.utc),
        "is_current": True,
        "bio": "Bill is the principal of Bébé Memorial High School and serves as Vice President. He's been instrumental in strengthening partnerships between the library and local schools, including the summer reading programs that help prevent learning loss.",
        "public_email": "board.vicepresident@lsclibrary.org",
        "office_hours": "By appointment during school year",
    },
    {
        "full_name": "Helen Kowalski",
        "email": "helen.k@email.com",
        "position": "member",
        "term_start_date": datetime(2023, 1, 1, tzinfo=timezone.utc),
        "term_end_date": datetime(2027, 12, 31, tzinfo=timezone.utc),
        "is_current": True,
        "bio": "Helen is a retired nurse who has lived in Bébé Memorial her entire life. She brings deep community knowledge and advocates for services that support seniors and those with accessibility needs. She was instrumental in getting large-print book selection expanded.",
        "public_email": None,
        "office_hours": None,
    },
    {
        "full_name": "James 'Jimmy' Redbird",
        "email": "jredbird@email.com",
        "position": "member",
        "term_start_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "term_end_date": datetime(2028, 12, 31, tzinfo=timezone.utc),
        "is_current": True,
        "bio": "Jimmy is a member of the local Indigenous community and owns Redbird Construction. He joined the board to ensure the library serves all community members and has been leading efforts to include more Indigenous authors and perspectives in our collection.",
        "public_email": None,
        "office_hours": None,
    },
    {
        "full_name": "Patricia 'Trish' O'Brien",
        "email": "trish.obrien@email.com",
        "position": "member",
        "term_start_date": datetime(2022, 1, 1, tzinfo=timezone.utc),
        "term_end_date": datetime(2026, 12, 31, tzinfo=timezone.utc),
        "is_current": True,
        "bio": "Trish is a young professional who works remotely as a software developer. She joined the board to advocate for digital resources, faster WiFi, and technology programs. She helped establish the popular 'Tech Help Tuesday' program.",
        "public_email": None,
        "office_hours": None,
    },
]


async def seed_board_members():
    """Seed board members for public pages."""
    print("=" * 70)
    print("👥 LSC Library Board Members Seeder")
    print("=" * 70)

    try:
        async with async_session() as session:
            added = 0
            for member in BOARD_MEMBERS:
                # Check if member already exists
                result = await session.execute(
                    text("SELECT id FROM board_members WHERE full_name = :name"),
                    {"name": member["full_name"]}
                )
                if result.fetchone():
                    print(f"  ℹ️  {member['full_name']} already exists, skipping")
                    continue

                # Insert board member
                await session.execute(
                    text("""
                        INSERT INTO board_members
                        (full_name, email, position, term_start_date, term_end_date,
                         is_current, bio, public_email, office_hours)
                        VALUES
                        (:full_name, :email, :position, :term_start_date, :term_end_date,
                         :is_current, :bio, :public_email, :office_hours)
                    """),
                    {
                        "full_name": member["full_name"],
                        "email": member["email"],
                        "position": member["position"],
                        "term_start_date": member["term_start_date"],
                        "term_end_date": member["term_end_date"],
                        "is_current": member["is_current"],
                        "bio": member["bio"],
                        "public_email": member.get("public_email"),
                        "office_hours": member.get("office_hours"),
                    }
                )
                added += 1
                print(f"  ✅ Added {member['full_name']} ({member['position']})")

            await session.commit()
            print(f"\n{'=' * 70}")
            print(f"✅ Seeding Complete! Added {added} board members")
            print(f"{'=' * 70}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(seed_board_members())
