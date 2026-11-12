#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Board Governance Seeder for Bébé Memorial Library

Seeds comprehensive board governance data:
- Meeting minutes for past meetings
- Agenda items for all meetings
- Voting records (BoardVote + BoardVoteCast)
- Board motions
- Board documents (published, public)
- Strategic plan with goals
- Strategic milestones (completed + pending)
- Board audit log entries
- Strategic audit log entries
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@localhost:5434/lsc_library",
)
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

NOW = datetime.now(timezone.utc)


async def get_user_id(session):
    """Get an admin/staff user ID for created_by fields."""
    result = await session.execute(
        text("SELECT id FROM users WHERE role IN ('ADMIN', 'STAFF') ORDER BY id LIMIT 1")
    )
    row = result.fetchone()
    if not row:
        result = await session.execute(text("SELECT id FROM users ORDER BY id LIMIT 1"))
        row = result.fetchone()
    return row[0] if row else None


async def get_meeting_ids(session):
    """Get board meeting IDs with their titles and dates."""
    result = await session.execute(
        text("SELECT id, title, scheduled_date, is_cancelled FROM board_meetings ORDER BY scheduled_date")
    )
    return result.fetchall()


async def get_board_member_ids(session):
    """Get board member IDs."""
    result = await session.execute(
        text("SELECT id, full_name, position FROM board_members WHERE is_current = true ORDER BY id")
    )
    return result.fetchall()


async def seed_agenda_items(session, user_id):
    """Seed agenda items for all meetings."""
    print("\n--- Seeding Agenda Items ---")

    meetings = await get_meeting_ids(session)
    if not meetings:
        print("  No meetings found. Run seed_board_meetings.py first.")
        return

    # Check if agenda items already exist
    result = await session.execute(text("SELECT COUNT(*) FROM agenda_items"))
    count = result.scalar()
    if count and count > 0:
        print(f"  Agenda items already exist ({count}), skipping")
        return

    added = 0
    for meeting in meetings:
        meeting_id, title, scheduled_date, is_cancelled = meeting

        if is_cancelled:
            continue

        is_past = scheduled_date < NOW

        # Standard agenda template
        items = [
            {
                "item_number": "1",
                "title": "Call to Order",
                "description": "Board President calls the meeting to order.",
                "presenter": "Board President",
                "estimated_duration_minutes": 2,
                "sort_order": 1,
                "requires_action": False,
                "action_type": "information",
            },
            {
                "item_number": "2",
                "title": "Roll Call and Establishment of Quorum",
                "description": "Secretary records attendance and confirms quorum.",
                "presenter": "Board Secretary",
                "estimated_duration_minutes": 3,
                "sort_order": 2,
                "requires_action": False,
                "action_type": "information",
            },
            {
                "item_number": "3",
                "title": "Public Comment Period",
                "description": "Members of the public may address the board. Each speaker is limited to 3 minutes.",
                "presenter": None,
                "estimated_duration_minutes": 15,
                "sort_order": 3,
                "requires_action": False,
                "action_type": "discussion",
            },
            {
                "item_number": "4",
                "title": "Approval of Previous Meeting Minutes",
                "description": "Review and approve minutes from the previous regular meeting.",
                "presenter": "Board Secretary",
                "estimated_duration_minutes": 5,
                "sort_order": 4,
                "requires_action": True,
                "action_type": "vote",
                "action_taken": "Approved unanimously" if is_past else None,
                "vote_result": "7-0" if is_past else None,
            },
        ]

        # Add meeting-specific items
        if "December" in title:
            items.extend([
                {
                    "item_number": "5",
                    "title": "Q4 Budget Review",
                    "description": "Treasurer presents Q4 financial report and year-end projections.",
                    "presenter": "David Chen, Treasurer",
                    "estimated_duration_minutes": 20,
                    "sort_order": 5,
                    "requires_action": True,
                    "action_type": "vote",
                    "action_taken": "Accepted as presented" if is_past else None,
                    "vote_result": "7-0" if is_past else None,
                },
                {
                    "item_number": "6",
                    "title": "2026 Strategic Priorities Discussion",
                    "description": "Board discusses strategic priorities and goals for the upcoming year.",
                    "presenter": "Board President",
                    "estimated_duration_minutes": 25,
                    "sort_order": 6,
                    "requires_action": False,
                    "action_type": "discussion",
                },
                {
                    "item_number": "7",
                    "title": "Library Director's Report",
                    "description": "Monthly report from the Library Director on operations, programs, and staffing.",
                    "presenter": "Library Director",
                    "estimated_duration_minutes": 15,
                    "sort_order": 7,
                    "requires_action": False,
                    "action_type": "information",
                },
            ])
        elif "January" in title:
            items.extend([
                {
                    "item_number": "5",
                    "title": "2026 Budget Approval",
                    "description": "Final review and vote on the 2026 annual operating budget.",
                    "presenter": "David Chen, Treasurer",
                    "estimated_duration_minutes": 30,
                    "sort_order": 5,
                    "requires_action": True,
                    "action_type": "vote",
                    "action_taken": "Approved with amendments" if is_past else None,
                    "vote_result": "6-1" if is_past else None,
                },
                {
                    "item_number": "6",
                    "title": "Holiday Circulation Statistics Review",
                    "description": "Review of circulation data from November-December period.",
                    "presenter": "Library Director",
                    "estimated_duration_minutes": 10,
                    "sort_order": 6,
                    "requires_action": False,
                    "action_type": "information",
                },
                {
                    "item_number": "7",
                    "title": "Summer Reading Program Planning",
                    "description": "Discussion of 2026 summer reading program themes, budget, and timeline.",
                    "presenter": "Youth Services Coordinator",
                    "estimated_duration_minutes": 20,
                    "sort_order": 7,
                    "requires_action": False,
                    "action_type": "discussion",
                },
            ])
        elif "February" in title:
            items.extend([
                {
                    "item_number": "5",
                    "title": "January Circulation Report",
                    "description": "Monthly circulation statistics and trends analysis.",
                    "presenter": "Library Director",
                    "estimated_duration_minutes": 10,
                    "sort_order": 5,
                    "requires_action": False,
                    "action_type": "information",
                },
                {
                    "item_number": "6",
                    "title": "Technology Upgrade Proposal",
                    "description": "Presentation on proposed public computer and WiFi infrastructure upgrades. Includes vendor quotes and timeline.",
                    "presenter": "IT Coordinator",
                    "estimated_duration_minutes": 25,
                    "sort_order": 6,
                    "requires_action": True,
                    "action_type": "vote",
                },
                {
                    "item_number": "7",
                    "title": "Elmdale Branch Renovation Update",
                    "description": "Progress report on the Elmdale Branch renovation project. Includes contractor timeline and budget status.",
                    "presenter": "Facilities Manager",
                    "estimated_duration_minutes": 15,
                    "sort_order": 7,
                    "requires_action": False,
                    "action_type": "information",
                },
            ])
        elif "Strategic" in title:
            items.extend([
                {
                    "item_number": "5",
                    "title": "Strategic Plan Progress Review",
                    "description": "Comprehensive review of progress toward all strategic goals in the 2025-2028 plan.",
                    "presenter": "Library Director",
                    "estimated_duration_minutes": 30,
                    "sort_order": 5,
                    "requires_action": False,
                    "action_type": "discussion",
                },
                {
                    "item_number": "6",
                    "title": "Community Feedback on Strategic Priorities",
                    "description": "Extended public input session on library strategic direction.",
                    "presenter": "Board President",
                    "estimated_duration_minutes": 30,
                    "sort_order": 6,
                    "requires_action": False,
                    "action_type": "discussion",
                },
            ])
        else:
            # Generic items for other meetings
            items.extend([
                {
                    "item_number": "5",
                    "title": "Old Business",
                    "description": "Follow-up items from previous meetings.",
                    "presenter": "Board President",
                    "estimated_duration_minutes": 15,
                    "sort_order": 5,
                    "requires_action": False,
                    "action_type": "discussion",
                },
                {
                    "item_number": "6",
                    "title": "New Business",
                    "description": "New items for board consideration.",
                    "presenter": "Board President",
                    "estimated_duration_minutes": 20,
                    "sort_order": 6,
                    "requires_action": False,
                    "action_type": "discussion",
                },
            ])

        # Add adjournment as last item
        last_num = str(len(items) + 1)
        items.append({
            "item_number": last_num,
            "title": "Adjournment",
            "description": "Motion to adjourn the meeting.",
            "presenter": "Board President",
            "estimated_duration_minutes": 2,
            "sort_order": len(items) + 1,
            "requires_action": True,
            "action_type": "vote",
            "action_taken": "Meeting adjourned" if is_past else None,
            "vote_result": "Unanimous" if is_past else None,
        })

        for item in items:
            await session.execute(
                text("""
                    INSERT INTO agenda_items
                    (meeting_id, item_number, title, description, presenter,
                     estimated_duration_minutes, sort_order, requires_action,
                     action_type, action_taken, vote_result, created_by_id)
                    VALUES
                    (:meeting_id, :item_number, :title, :description, :presenter,
                     :duration, :sort_order, :requires_action,
                     :action_type, :action_taken, :vote_result, :created_by_id)
                """),
                {
                    "meeting_id": meeting_id,
                    "item_number": item["item_number"],
                    "title": item["title"],
                    "description": item["description"],
                    "presenter": item.get("presenter"),
                    "duration": item["estimated_duration_minutes"],
                    "sort_order": item["sort_order"],
                    "requires_action": item["requires_action"],
                    "action_type": item.get("action_type"),
                    "action_taken": item.get("action_taken"),
                    "vote_result": item.get("vote_result"),
                    "created_by_id": user_id,
                },
            )
            added += 1

    await session.commit()
    print(f"  Added {added} agenda items across {len(meetings)} meetings")


async def seed_meeting_minutes(session, user_id):
    """Seed meeting minutes for past meetings."""
    print("\n--- Seeding Meeting Minutes ---")

    meetings = await get_meeting_ids(session)
    members = await get_board_member_ids(session)

    if not meetings:
        print("  No meetings found.")
        return

    result = await session.execute(text("SELECT COUNT(*) FROM board_minutes"))
    count = result.scalar()
    if count and count > 0:
        print(f"  Minutes already exist ({count}), skipping")
        return

    added = 0
    for meeting in meetings:
        meeting_id, title, scheduled_date, is_cancelled = meeting

        # Only create minutes for past, non-cancelled meetings
        if is_cancelled or scheduled_date >= NOW:
            continue

        members_present = []
        members_absent = []
        for m in members:
            member_info = {"id": m[0], "name": m[1], "title": m[2].replace("_", " ").title()}
            # Make most members present; one excused
            if m[2] == "member" and len(members_present) >= 5:
                members_absent.append(member_info)
            else:
                members_present.append(member_info)

        quorum_count = f"{len(members_present)} of {len(members)} members present"

        # Build sections
        call_to_order_time = scheduled_date.replace(hour=18, minute=2)
        adjourn_time = scheduled_date.replace(hour=19, minute=45)

        sections = []
        if "December" in title:
            sections = [
                {"title": "Call to Order", "content": "Board President Peggy Thompson called the meeting to order at 6:02 PM.", "order": 1},
                {"title": "Roll Call", "content": f"Secretary Rosa Martinez conducted roll call. {quorum_count}. Quorum established.", "order": 2},
                {"title": "Public Comment", "content": "Two community members addressed the board. Sarah Johnson spoke in favor of extended weekend hours. Mike Peters requested consideration of additional programming for teens.", "order": 3},
                {"title": "Approval of November Minutes", "content": "Motion to approve November meeting minutes made by Bill Okonkwo, seconded by Helen Kowalski. Approved 7-0.", "order": 4},
                {"title": "Q4 Budget Review", "content": "Treasurer David Chen presented the Q4 financial report. Total expenditures are 2% under budget. Grant revenue exceeded projections by $12,000 due to the successful state literacy grant. The board accepted the financial report as presented.", "order": 5},
                {"title": "2026 Strategic Priorities", "content": "The board discussed priorities for 2026 including: technology infrastructure upgrades, expanded digital literacy programs, Elmdale Branch renovation, and community partnerships. Board directed staff to prepare detailed proposals for the January meeting.", "order": 6},
                {"title": "Library Director's Report", "content": "Director reported 15,234 items circulated in November, a 3% increase over the same period last year. The new self-checkout kiosks have been well received. Holiday programming saw record attendance with 450 participants across all branches.", "order": 7},
                {"title": "Adjournment", "content": "Motion to adjourn by David Chen, seconded by Jimmy Redbird. Meeting adjourned at 7:45 PM.", "order": 8},
            ]
        elif "January" in title:
            sections = [
                {"title": "Call to Order", "content": "Board President Peggy Thompson called the meeting to order at 6:00 PM.", "order": 1},
                {"title": "Roll Call", "content": f"Secretary Rosa Martinez conducted roll call. {quorum_count}. Quorum established.", "order": 2},
                {"title": "Public Comment", "content": "Three community members provided public comments. Topics included support for the summer reading program expansion and a request for additional Spanish-language materials.", "order": 3},
                {"title": "Approval of December Minutes", "content": "Motion to approve December meeting minutes made by Trish O'Brien, seconded by Helen Kowalski. Approved unanimously.", "order": 4},
                {"title": "2026 Budget Approval", "content": "Treasurer David Chen presented the proposed 2026 operating budget of $2.4 million. Key items include $150,000 for technology upgrades, $85,000 for the summer reading program, and $200,000 for the Elmdale Branch renovation match. After discussion, Bill Okonkwo moved to approve the budget with an amendment to increase the digital resources line by $10,000, funded from reserves. Helen Kowalski seconded. Approved 6-1.", "order": 5},
                {"title": "Holiday Circulation Statistics", "content": "Director presented circulation data: November-December saw 31,456 total items circulated, up 4.5% year-over-year. E-book checkouts increased 12%. Children's materials had the highest growth at 8%.", "order": 6},
                {"title": "Summer Reading Program Planning", "content": "Youth Services Coordinator presented preliminary plans for 'Explore the Unknown' summer reading theme. Budget request of $85,000 includes performer fees, prizes, and materials. Board directed staff to finalize vendor contracts and return with update at February meeting.", "order": 7},
                {"title": "Adjournment", "content": "Motion to adjourn by Rosa Martinez, seconded by Bill Okonkwo. Meeting adjourned at 7:48 PM.", "order": 8},
            ]

        await session.execute(
            text("""
                INSERT INTO board_minutes
                (meeting_id, status, sections, meeting_called_to_order_at,
                 meeting_adjourned_at, members_present, members_absent,
                 members_excused, guests_present, quorum_met, quorum_count,
                 approved, approved_at, approved_by_id, approval_vote_result,
                 notes, prepared_by_id, prepared_at, created_by_id)
                VALUES
                (:meeting_id, :status, :sections, :called_to_order,
                 :adjourned_at, :members_present, :members_absent,
                 :members_excused, :guests, :quorum_met, :quorum_count,
                 :approved, :approved_at, :approved_by_id, :approval_vote_result,
                 :notes, :prepared_by_id, :prepared_at, :created_by_id)
            """),
            {
                "meeting_id": meeting_id,
                "status": "published",
                "sections": json.dumps(sections),
                "called_to_order": call_to_order_time,
                "adjourned_at": adjourn_time,
                "members_present": json.dumps(members_present),
                "members_absent": json.dumps(members_absent),
                "members_excused": json.dumps([]),
                "guests": json.dumps([
                    {"name": "Library Director", "title": "Staff"},
                    {"name": "Members of the public", "title": "Community"},
                ]),
                "quorum_met": True,
                "quorum_count": quorum_count,
                "approved": True,
                "approved_at": scheduled_date + timedelta(days=30),
                "approved_by_id": user_id,
                "approval_vote_result": "Approved unanimously",
                "notes": "These minutes were approved at the following regular board meeting.",
                "prepared_by_id": user_id,
                "prepared_at": scheduled_date + timedelta(days=3),
                "created_by_id": user_id,
            },
        )
        added += 1
        print(f"  Added minutes for '{title}'")

    await session.commit()
    print(f"  Total: {added} meeting minutes created")


async def seed_board_documents(session, user_id):
    """Seed board documents."""
    print("\n--- Seeding Board Documents ---")

    result = await session.execute(text("SELECT COUNT(*) FROM board_documents"))
    count = result.scalar()
    if count and count > 0:
        print(f"  Documents already exist ({count}), skipping")
        return

    meetings = await get_meeting_ids(session)
    meeting_map = {m[1]: m[0] for m in meetings}  # title -> id

    documents = [
        # Meeting agendas
        {
            "meeting_title": "Regular Board Meeting - December 2025",
            "document_type": "agenda",
            "title": "December 2025 Board Meeting Agenda",
            "description": "Official agenda for the December 2025 regular board meeting.",
            "filename": "agenda_december_2025.pdf",
            "file_path": "/documents/board/agendas/agenda_december_2025.pdf",
            "file_size_bytes": 145000,
            "mime_type": "application/pdf",
            "status": "published",
            "is_public": True,
            "keywords": ["agenda", "december", "2025", "regular meeting"],
        },
        {
            "meeting_title": "Regular Board Meeting - January 2026",
            "document_type": "agenda",
            "title": "January 2026 Board Meeting Agenda",
            "description": "Official agenda for the January 2026 regular board meeting.",
            "filename": "agenda_january_2026.pdf",
            "file_path": "/documents/board/agendas/agenda_january_2026.pdf",
            "file_size_bytes": 152000,
            "mime_type": "application/pdf",
            "status": "published",
            "is_public": True,
            "keywords": ["agenda", "january", "2026", "regular meeting"],
        },
        {
            "meeting_title": "Regular Board Meeting - February 2026",
            "document_type": "agenda",
            "title": "February 2026 Board Meeting Agenda",
            "description": "Official agenda for the February 2026 regular board meeting.",
            "filename": "agenda_february_2026.pdf",
            "file_path": "/documents/board/agendas/agenda_february_2026.pdf",
            "file_size_bytes": 138000,
            "mime_type": "application/pdf",
            "status": "published",
            "is_public": True,
            "keywords": ["agenda", "february", "2026", "regular meeting"],
        },
        # Meeting minutes documents
        {
            "meeting_title": "Regular Board Meeting - December 2025",
            "document_type": "minutes",
            "title": "December 2025 Board Meeting Minutes",
            "description": "Approved minutes from the December 2025 regular board meeting.",
            "filename": "minutes_december_2025.pdf",
            "file_path": "/documents/board/minutes/minutes_december_2025.pdf",
            "file_size_bytes": 234000,
            "mime_type": "application/pdf",
            "status": "published",
            "is_public": True,
            "keywords": ["minutes", "december", "2025", "approved"],
        },
        {
            "meeting_title": "Regular Board Meeting - January 2026",
            "document_type": "minutes",
            "title": "January 2026 Board Meeting Minutes",
            "description": "Approved minutes from the January 2026 regular board meeting.",
            "filename": "minutes_january_2026.pdf",
            "file_path": "/documents/board/minutes/minutes_january_2026.pdf",
            "file_size_bytes": 267000,
            "mime_type": "application/pdf",
            "status": "published",
            "is_public": True,
            "keywords": ["minutes", "january", "2026", "approved"],
        },
        # Board packets
        {
            "meeting_title": "Regular Board Meeting - February 2026",
            "document_type": "packet",
            "title": "February 2026 Board Packet",
            "description": "Complete board packet including agenda, reports, and supporting documents for the February meeting.",
            "filename": "board_packet_february_2026.pdf",
            "file_path": "/documents/board/packets/board_packet_february_2026.pdf",
            "file_size_bytes": 1250000,
            "mime_type": "application/pdf",
            "status": "published",
            "is_public": True,
            "keywords": ["packet", "february", "2026", "reports"],
        },
        # Financial reports
        {
            "meeting_title": None,
            "document_type": "financial_report",
            "title": "Q4 2025 Financial Report",
            "description": "Quarterly financial report covering October-December 2025. Includes revenue, expenditures, and fund balances.",
            "filename": "q4_2025_financial_report.pdf",
            "file_path": "/documents/board/financial/q4_2025_financial_report.pdf",
            "file_size_bytes": 890000,
            "mime_type": "application/pdf",
            "status": "published",
            "is_public": True,
            "keywords": ["financial", "quarterly", "q4", "2025", "budget"],
        },
        {
            "meeting_title": None,
            "document_type": "financial_report",
            "title": "2026 Approved Annual Budget",
            "description": "Board-approved operating budget for fiscal year 2026. Total budget: $2.4 million.",
            "filename": "2026_approved_budget.pdf",
            "file_path": "/documents/board/financial/2026_approved_budget.pdf",
            "file_size_bytes": 445000,
            "mime_type": "application/pdf",
            "status": "published",
            "is_public": True,
            "keywords": ["budget", "2026", "annual", "approved"],
        },
        # Policies
        {
            "meeting_title": None,
            "document_type": "policy",
            "title": "Collection Development Policy (2025 Revision)",
            "description": "Updated collection development policy including digital resources guidelines and diversity criteria.",
            "filename": "collection_development_policy_2025.pdf",
            "file_path": "/documents/board/policies/collection_development_policy_2025.pdf",
            "file_size_bytes": 320000,
            "mime_type": "application/pdf",
            "status": "published",
            "is_public": True,
            "keywords": ["policy", "collection", "development", "diversity"],
        },
        {
            "meeting_title": None,
            "document_type": "policy",
            "title": "Public Meeting Room Use Policy",
            "description": "Guidelines and procedures for public use of library meeting rooms and community spaces.",
            "filename": "meeting_room_policy.pdf",
            "file_path": "/documents/board/policies/meeting_room_policy.pdf",
            "file_size_bytes": 198000,
            "mime_type": "application/pdf",
            "status": "published",
            "is_public": True,
            "keywords": ["policy", "meeting room", "community", "spaces"],
        },
        # Presentations
        {
            "meeting_title": "Regular Board Meeting - January 2026",
            "document_type": "presentation",
            "title": "2026 Budget Presentation",
            "description": "Treasurer's presentation of the proposed 2026 operating budget to the board.",
            "filename": "2026_budget_presentation.pptx",
            "file_path": "/documents/board/presentations/2026_budget_presentation.pptx",
            "file_size_bytes": 2100000,
            "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "status": "published",
            "is_public": True,
            "keywords": ["budget", "2026", "presentation", "treasurer"],
        },
        # Resolution
        {
            "meeting_title": None,
            "document_type": "resolution",
            "title": "Resolution 2025-008: Commitment to Digital Equity",
            "description": "Board resolution affirming the library's commitment to bridging the digital divide through expanded technology access and digital literacy programs.",
            "filename": "resolution_2025_008_digital_equity.pdf",
            "file_path": "/documents/board/resolutions/resolution_2025_008_digital_equity.pdf",
            "file_size_bytes": 175000,
            "mime_type": "application/pdf",
            "status": "published",
            "is_public": True,
            "keywords": ["resolution", "digital equity", "technology", "access"],
        },
    ]

    added = 0
    for doc in documents:
        meeting_id = None
        if doc["meeting_title"] and doc["meeting_title"] in meeting_map:
            meeting_id = meeting_map[doc["meeting_title"]]

        published_date = NOW - timedelta(days=5)

        await session.execute(
            text("""
                INSERT INTO board_documents
                (meeting_id, document_type, title, description, filename,
                 file_path, file_size_bytes, mime_type, version_number,
                 is_current_version, status, published_date, published_by_id,
                 is_public, is_confidential, keywords, created_by_id)
                VALUES
                (:meeting_id, :document_type, :title, :description, :filename,
                 :file_path, :file_size_bytes, :mime_type, 1,
                 true, :status, :published_date, :published_by_id,
                 :is_public, false, :keywords, :created_by_id)
            """),
            {
                "meeting_id": meeting_id,
                "document_type": doc["document_type"],
                "title": doc["title"],
                "description": doc["description"],
                "filename": doc["filename"],
                "file_path": doc["file_path"],
                "file_size_bytes": doc["file_size_bytes"],
                "mime_type": doc["mime_type"],
                "status": doc["status"],
                "published_date": published_date,
                "published_by_id": user_id,
                "is_public": doc["is_public"],
                "keywords": doc["keywords"],
                "created_by_id": user_id,
            },
        )
        added += 1
        print(f"  Added document: '{doc['title']}'")

    await session.commit()
    print(f"  Total: {added} documents created")


async def seed_voting_records(session, user_id):
    """Seed board votes and motions for past meetings."""
    print("\n--- Seeding Voting Records & Motions ---")

    result = await session.execute(text("SELECT COUNT(*) FROM board_votes"))
    count = result.scalar()
    if count and count > 0:
        print(f"  Votes already exist ({count}), skipping")
        return

    meetings = await get_meeting_ids(session)
    members = await get_board_member_ids(session)

    if not meetings or not members:
        print("  No meetings or members found.")
        return

    past_meetings = [(m[0], m[1], m[2]) for m in meetings if m[2] < NOW and not m[3]]

    added_votes = 0
    added_motions = 0
    added_casts = 0

    for meeting_id, title, scheduled_date in past_meetings:
        # Define votes for this meeting
        votes_data = []
        if "December" in title:
            votes_data = [
                {
                    "title": "Approval of November 2025 Meeting Minutes",
                    "description": "Motion to approve the minutes of the November 2025 regular board meeting as presented.",
                    "vote_type": "simple_majority",
                    "passed": True,
                    "tally_yes": 7,
                    "tally_no": 0,
                    "tally_abstain": 0,
                    "motion_number": "2025-DEC-001",
                    "motion_text": "I move to approve the minutes of the November 2025 regular board meeting as presented.",
                },
                {
                    "title": "Accept Q4 Financial Report",
                    "description": "Motion to accept the Q4 2025 financial report as presented by the Treasurer.",
                    "vote_type": "simple_majority",
                    "passed": True,
                    "tally_yes": 7,
                    "tally_no": 0,
                    "tally_abstain": 0,
                    "motion_number": "2025-DEC-002",
                    "motion_text": "I move to accept the Q4 2025 financial report as presented.",
                },
            ]
        elif "January" in title:
            votes_data = [
                {
                    "title": "Approval of December 2025 Meeting Minutes",
                    "description": "Motion to approve the minutes of the December 2025 regular board meeting.",
                    "vote_type": "simple_majority",
                    "passed": True,
                    "tally_yes": 7,
                    "tally_no": 0,
                    "tally_abstain": 0,
                    "motion_number": "2026-JAN-001",
                    "motion_text": "I move to approve the minutes of the December 2025 regular board meeting as presented.",
                },
                {
                    "title": "Approve 2026 Annual Operating Budget",
                    "description": "Motion to approve the 2026 annual operating budget of $2.4 million with amendment to increase digital resources allocation by $10,000.",
                    "vote_type": "simple_majority",
                    "passed": True,
                    "tally_yes": 6,
                    "tally_no": 1,
                    "tally_abstain": 0,
                    "motion_number": "2026-JAN-002",
                    "motion_text": "I move to approve the 2026 annual operating budget of $2.4 million as presented, with the amendment to increase the digital resources line item by $10,000 from general reserves.",
                    "rationale": "The proposed budget supports our strategic priorities while maintaining fiscal responsibility. The digital resources amendment reflects growing community demand for e-books and online databases.",
                },
                {
                    "title": "Budget Amendment: Digital Resources Increase",
                    "description": "Amendment to increase digital resources budget line by $10,000 from reserves.",
                    "vote_type": "simple_majority",
                    "passed": True,
                    "tally_yes": 5,
                    "tally_no": 2,
                    "tally_abstain": 0,
                    "motion_number": "2026-JAN-003",
                    "motion_text": "I move to amend the budget motion to increase the digital resources allocation by $10,000, funded from general reserves.",
                    "is_amendment": True,
                },
            ]

        for vote_data in votes_data:
            vote_opens = scheduled_date.replace(hour=18, minute=30)
            vote_closes = scheduled_date.replace(hour=18, minute=35)

            # Insert vote
            result = await session.execute(
                text("""
                    INSERT INTO board_votes
                    (meeting_id, title, description, vote_type, opens_at, closes_at,
                     status, quorum_required, passed, final_tally_yes, final_tally_no,
                     final_tally_abstain, closed_by_id, closed_at_actual, created_by_id)
                    VALUES
                    (:meeting_id, :title, :description, :vote_type, :opens_at, :closes_at,
                     'closed', 4, :passed, :tally_yes, :tally_no,
                     :tally_abstain, :closed_by_id, :closed_at, :created_by_id)
                    RETURNING id
                """),
                {
                    "meeting_id": meeting_id,
                    "title": vote_data["title"],
                    "description": vote_data["description"],
                    "vote_type": vote_data["vote_type"],
                    "opens_at": vote_opens,
                    "closes_at": vote_closes,
                    "passed": vote_data["passed"],
                    "tally_yes": vote_data["tally_yes"],
                    "tally_no": vote_data["tally_no"],
                    "tally_abstain": vote_data["tally_abstain"],
                    "closed_by_id": user_id,
                    "closed_at": vote_closes,
                    "created_by_id": user_id,
                },
            )
            vote_id = result.scalar()
            added_votes += 1

            # Insert individual vote casts
            yes_count = 0
            no_count = 0
            for member in members:
                member_id = member[0]
                if yes_count < vote_data["tally_yes"]:
                    choice = "yes"
                    yes_count += 1
                elif no_count < vote_data["tally_no"]:
                    choice = "no"
                    no_count += 1
                else:
                    choice = "abstain"

                await session.execute(
                    text("""
                        INSERT INTO board_votes_cast
                        (vote_id, board_member_id, choice, cast_at)
                        VALUES (:vote_id, :member_id, :choice, :cast_at)
                    """),
                    {
                        "vote_id": vote_id,
                        "member_id": member_id,
                        "choice": choice,
                        "cast_at": vote_closes - timedelta(minutes=1),
                    },
                )
                added_casts += 1

            # Insert corresponding motion
            mover = members[0] if members else None
            seconder = members[1] if len(members) > 1 else None

            if mover:
                await session.execute(
                    text("""
                        INSERT INTO board_motions
                        (meeting_id, motion_type, status, motion_number, title,
                         motion_text, rationale, moved_by_id, moved_at,
                         seconded_by_id, seconded_at, discussion_opened_at,
                         discussion_closed_at, vote_id, vote_called_at,
                         outcome_recorded_at, created_by_id)
                        VALUES
                        (:meeting_id, :motion_type, :status, :motion_number, :title,
                         :motion_text, :rationale, :moved_by_id, :moved_at,
                         :seconded_by_id, :seconded_at, :discussion_opened_at,
                         :discussion_closed_at, :vote_id, :vote_called_at,
                         :outcome_recorded_at, :created_by_id)
                    """),
                    {
                        "meeting_id": meeting_id,
                        "motion_type": "amendment" if vote_data.get("is_amendment") else "main",
                        "status": "passed" if vote_data["passed"] else "failed",
                        "motion_number": vote_data["motion_number"],
                        "title": vote_data["title"],
                        "motion_text": vote_data["motion_text"],
                        "rationale": vote_data.get("rationale"),
                        "moved_by_id": mover[0],
                        "moved_at": vote_opens - timedelta(minutes=5),
                        "seconded_by_id": seconder[0] if seconder else None,
                        "seconded_at": vote_opens - timedelta(minutes=4),
                        "discussion_opened_at": vote_opens - timedelta(minutes=3),
                        "discussion_closed_at": vote_opens,
                        "vote_id": vote_id,
                        "vote_called_at": vote_opens,
                        "outcome_recorded_at": vote_closes,
                        "created_by_id": user_id,
                    },
                )
                added_motions += 1

    await session.commit()
    print(f"  Added {added_votes} votes, {added_motions} motions, {added_casts} individual vote casts")


async def seed_strategic_plan(session, user_id):
    """Seed strategic plan with goals and milestones."""
    print("\n--- Seeding Strategic Plan, Goals & Milestones ---")

    result = await session.execute(text("SELECT COUNT(*) FROM strategic_plans"))
    count = result.scalar()
    if count and count > 0:
        print(f"  Strategic plans already exist ({count}), skipping")
        return

    # Create the strategic plan
    result = await session.execute(
        text("""
            INSERT INTO strategic_plans
            (title, description, period_start, period_end, mission, vision,
             values, status, last_reviewed, next_review,
             story_intro, history_timeline, created_by_id)
            VALUES
            (:title, :description, :period_start, :period_end, :mission, :vision,
             :values, 'active', :last_reviewed, :next_review,
             :story_intro, :history_timeline, :created_by_id)
            RETURNING id
        """),
        {
            "title": "Building Tomorrow's Library: Strategic Plan 2025-2028",
            "description": "A comprehensive four-year strategic plan focused on expanding community access, embracing technology, and strengthening the library as a community hub for Bébé Memorial.",
            "period_start": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "period_end": datetime(2028, 12, 31, tzinfo=timezone.utc),
            "mission": "The Bébé Memorial Library connects our community with the knowledge, resources, and programs they need to learn, grow, and thrive.",
            "vision": "A vibrant, inclusive library that serves as the heart of our community - where everyone can discover, create, and connect.",
            "values": json.dumps([
                "Equitable Access",
                "Intellectual Freedom",
                "Community Connection",
                "Innovation",
                "Lifelong Learning",
                "Fiscal Responsibility",
            ]),
            "last_reviewed": NOW - timedelta(days=30),
            "next_review": NOW + timedelta(days=60),
            "story_intro": "Since 1952, the Bébé Memorial Library has been at the heart of our community. From our humble beginnings in a single room at Town Hall to our current three-branch system, we've grown alongside the people we serve. Our strategic plan charts the course for the next chapter of that story.",
            "history_timeline": json.dumps([
                {"year": 1952, "title": "Library Founded", "description": "Established with a collection of 500 donated books in a room at Town Hall."},
                {"year": 1968, "title": "First Permanent Building", "description": "Main Branch opened on Main Street with 5,000 square feet of space."},
                {"year": 1985, "title": "Elmdale Branch Opens", "description": "Second branch opened to serve the growing Elmdale neighborhood."},
                {"year": 2001, "title": "Digital Catalog Launch", "description": "Library transitions to electronic catalog and introduces first public internet computers."},
                {"year": 2015, "title": "Main Branch Expansion", "description": "Major renovation doubles Main Branch to 10,000 square feet with community room."},
                {"year": 2023, "title": "Makerspace Opens", "description": "State-of-the-art makerspace with 3D printers, laser cutter, and recording studio."},
            ]),
            "created_by_id": user_id,
        },
    )
    plan_id = result.scalar()
    print(f"  Created strategic plan (id={plan_id})")

    # Goals
    goals = [
        {
            "title": "Expand Digital Access & Literacy",
            "description": "Bridge the digital divide by providing expanded technology access, digital literacy programs, and modern equipment across all branches.",
            "public_description": "We're working to ensure every community member has access to technology and the skills to use it effectively.",
            "category": "Technology",
            "department": "Technical Services",
            "target_date": datetime(2027, 6, 30, tzinfo=timezone.utc),
            "progress": 35,
            "status": "on_track",
            "priority": 1,
            "metrics": [
                {"name": "Public computers upgraded", "current": 14, "target": 40, "unit": "computers"},
                {"name": "Digital literacy class participants", "current": 450, "target": 1200, "unit": "participants/year"},
                {"name": "WiFi coverage", "current": 75, "target": 100, "unit": "%"},
            ],
            "updates": [
                {"date": "2025-03-15", "progress": 10, "note": "Completed needs assessment and vendor evaluation."},
                {"date": "2025-06-30", "progress": 20, "note": "First 8 computers upgraded at Main Branch. WiFi assessment complete."},
                {"date": "2025-12-15", "progress": 30, "note": "14 total computers upgraded. Digital literacy class series launched with strong enrollment."},
                {"date": "2026-01-20", "progress": 35, "note": "WiFi upgrade RFP issued. 450 participants in digital literacy classes to date."},
            ],
        },
        {
            "title": "Strengthen Youth & Family Services",
            "description": "Expand programming for children, teens, and families including summer reading, STEAM activities, and early literacy initiatives.",
            "public_description": "We're growing our programs for kids, teens, and families to support learning and fun at every age.",
            "category": "Community Engagement",
            "department": "Youth Services",
            "target_date": datetime(2027, 12, 31, tzinfo=timezone.utc),
            "progress": 45,
            "status": "on_track",
            "priority": 1,
            "metrics": [
                {"name": "Youth program attendance", "current": 3200, "target": 5000, "unit": "participants/year"},
                {"name": "Summer reading enrollment", "current": 850, "target": 1200, "unit": "children"},
                {"name": "Teen volunteer hours", "current": 320, "target": 600, "unit": "hours/year"},
            ],
            "updates": [
                {"date": "2025-04-01", "progress": 15, "note": "New teen advisory board established with 12 members."},
                {"date": "2025-08-30", "progress": 30, "note": "Summer reading program saw 850 enrollments, up 15% from 2024."},
                {"date": "2025-12-15", "progress": 40, "note": "STEAM Saturday series launched. Teen maker workshops averaging 18 participants."},
                {"date": "2026-01-15", "progress": 45, "note": "Year-end totals: 3,200 youth program participants. Planning 2026 summer theme."},
            ],
        },
        {
            "title": "Renovate Elmdale Branch",
            "description": "Complete renovation of the Elmdale Branch to improve accessibility, expand meeting space, and modernize the facility.",
            "public_description": "The Elmdale Branch is getting a makeover to better serve our growing neighborhood.",
            "category": "Facilities",
            "department": "Administration",
            "target_date": datetime(2026, 12, 31, tzinfo=timezone.utc),
            "progress": 25,
            "status": "on_track",
            "priority": 2,
            "metrics": [
                {"name": "Project completion", "current": 25, "target": 100, "unit": "%"},
                {"name": "ADA compliance items", "current": 3, "target": 12, "unit": "items resolved"},
                {"name": "Square footage added", "current": 0, "target": 2000, "unit": "sq ft"},
            ],
            "updates": [
                {"date": "2025-06-01", "progress": 10, "note": "Architectural plans finalized. Building permits submitted."},
                {"date": "2025-10-15", "progress": 20, "note": "Permits approved. Contractor selected through competitive bidding."},
                {"date": "2026-01-10", "progress": 25, "note": "Demolition phase complete. Foundation work underway."},
            ],
        },
        {
            "title": "Build Community Partnerships",
            "description": "Develop strategic partnerships with schools, nonprofits, and local businesses to extend library services and impact.",
            "public_description": "We're teaming up with local organizations to bring you more services and programs.",
            "category": "Community Engagement",
            "department": "Administration",
            "target_date": datetime(2028, 6, 30, tzinfo=timezone.utc),
            "progress": 40,
            "status": "on_track",
            "priority": 2,
            "metrics": [
                {"name": "Active partnerships", "current": 8, "target": 20, "unit": "partnerships"},
                {"name": "Joint programs offered", "current": 12, "target": 30, "unit": "programs/year"},
                {"name": "Outreach events", "current": 15, "target": 40, "unit": "events/year"},
            ],
            "updates": [
                {"date": "2025-03-01", "progress": 15, "note": "Partnership framework and MOU template developed."},
                {"date": "2025-07-15", "progress": 25, "note": "5 new partnerships signed including school district and food bank."},
                {"date": "2025-12-20", "progress": 40, "note": "8 active partnerships. 12 joint programs delivered. Strong community response."},
            ],
        },
        {
            "title": "Diversify Collection & Resources",
            "description": "Expand and diversify the library collection to better represent our community, including multilingual materials, Indigenous perspectives, and digital resources.",
            "public_description": "We're expanding our collection to include more diverse voices and formats.",
            "category": "Collections",
            "department": "Technical Services",
            "target_date": datetime(2027, 12, 31, tzinfo=timezone.utc),
            "progress": 30,
            "status": "on_track",
            "priority": 3,
            "metrics": [
                {"name": "Diverse titles added", "current": 1200, "target": 5000, "unit": "titles"},
                {"name": "Spanish-language materials", "current": 350, "target": 1000, "unit": "items"},
                {"name": "E-book catalog growth", "current": 8500, "target": 15000, "unit": "titles"},
            ],
            "updates": [
                {"date": "2025-05-01", "progress": 10, "note": "Collection diversity audit completed. Gaps identified in Indigenous, Spanish-language, and large-print materials."},
                {"date": "2025-09-15", "progress": 20, "note": "1,200 new diverse titles acquired. Partnership with Indigenous authors collective established."},
                {"date": "2026-01-10", "progress": 30, "note": "Spanish-language collection up to 350 items. E-book catalog grew to 8,500 titles."},
            ],
        },
        {
            "title": "Improve Staff Development & Retention",
            "description": "Invest in staff through professional development, competitive compensation, and a positive workplace culture.",
            "public_description": "We're investing in our team so they can better serve you.",
            "category": "Workforce",
            "department": "Administration",
            "target_date": datetime(2028, 12, 31, tzinfo=timezone.utc),
            "progress": 20,
            "status": "at_risk",
            "priority": 3,
            "metrics": [
                {"name": "Staff retention rate", "current": 82, "target": 95, "unit": "%"},
                {"name": "Training hours per staff", "current": 18, "target": 40, "unit": "hours/year"},
                {"name": "Staff satisfaction score", "current": 3.6, "target": 4.5, "unit": "/5.0"},
            ],
            "updates": [
                {"date": "2025-04-01", "progress": 10, "note": "Staff satisfaction survey conducted. Results analyzed and improvement plan drafted."},
                {"date": "2025-11-01", "progress": 20, "note": "New professional development program launched. Retention down to 82% - budget constraints affecting compensation competitiveness."},
            ],
        },
    ]

    goal_ids = []
    for goal in goals:
        result = await session.execute(
            text("""
                INSERT INTO strategic_goals
                (plan_id, title, description, public_description, category,
                 department, target_date, progress, status, metrics,
                 updates, priority, is_public, staff_can_update,
                 display_order, approval_status)
                VALUES
                (:plan_id, :title, :description, :public_description, :category,
                 :department, :target_date, :progress, :status, :metrics,
                 :updates, :priority, true, true,
                 :display_order, 'approved')
                RETURNING id
            """),
            {
                "plan_id": plan_id,
                "title": goal["title"],
                "description": goal["description"],
                "public_description": goal["public_description"],
                "category": goal["category"],
                "department": goal["department"],
                "target_date": goal["target_date"],
                "progress": goal["progress"],
                "status": goal["status"],
                "metrics": json.dumps(goal["metrics"]),
                "updates": json.dumps(goal["updates"]),
                "priority": goal["priority"],
                "display_order": goal["priority"],
            },
        )
        goal_id = result.scalar()
        goal_ids.append((goal_id, goal["title"]))
        print(f"  Added goal: '{goal['title']}' ({goal['progress']}% - {goal['status']})")

    # Milestones
    milestones = [
        # Completed milestones
        {
            "goal_index": 0,
            "title": "Digital Needs Assessment Complete",
            "description": "Comprehensive technology needs assessment across all branches completed and presented to board.",
            "achieved_date": datetime(2025, 3, 15, tzinfo=timezone.utc),
            "celebration_text": "Our digital future starts with understanding where we are. Assessment complete!",
            "impact_story": "The assessment surveyed 400+ community members and identified key gaps in public computer access, WiFi coverage, and digital skills training needs.",
            "milestone_type": "achievement",
            "is_public": True,
            "is_featured": False,
            "display_order": 1,
        },
        {
            "goal_index": 0,
            "title": "First Computer Lab Upgrade Complete",
            "description": "Main Branch computer lab fully upgraded with 8 new workstations.",
            "achieved_date": datetime(2025, 6, 30, tzinfo=timezone.utc),
            "celebration_text": "8 brand new computers are ready for you at the Main Branch!",
            "impact_story": "The new workstations feature faster processors, larger screens, and assistive technology software. Usage has increased 40% since the upgrade.",
            "milestone_type": "achievement",
            "is_public": True,
            "is_featured": True,
            "display_order": 2,
        },
        {
            "goal_index": 1,
            "title": "Teen Advisory Board Established",
            "description": "12-member teen advisory board formed to guide youth programming decisions.",
            "achieved_date": datetime(2025, 4, 1, tzinfo=timezone.utc),
            "celebration_text": "Our teens now have a seat at the table! Welcome to the Teen Advisory Board!",
            "impact_story": "The board meets monthly and has already influenced programming decisions including a new gaming tournament series and study space redesign.",
            "milestone_type": "launch",
            "is_public": True,
            "is_featured": True,
            "display_order": 3,
        },
        {
            "goal_index": 1,
            "title": "Record Summer Reading Enrollment",
            "description": "2025 Summer Reading Program saw 850 children enrolled, a 15% increase over 2024.",
            "achieved_date": datetime(2025, 8, 30, tzinfo=timezone.utc),
            "celebration_text": "850 young readers joined our summer adventure - a new record!",
            "impact_story": "Children who completed the program read an average of 22 books over the summer. 94% of parents reported their children maintained or improved reading skills.",
            "milestone_type": "achievement",
            "is_public": True,
            "is_featured": True,
            "display_order": 4,
        },
        {
            "goal_index": 3,
            "title": "School District Partnership Signed",
            "description": "Formal partnership agreement signed with Bébé Memorial School District.",
            "achieved_date": datetime(2025, 5, 15, tzinfo=timezone.utc),
            "celebration_text": "Stronger together! Our schools and library are officially partners.",
            "impact_story": "The partnership includes shared programming, school library card program for all students, and coordinated summer learning initiatives.",
            "milestone_type": "achievement",
            "is_public": True,
            "is_featured": False,
            "display_order": 5,
        },
        {
            "goal_index": 4,
            "title": "Collection Diversity Audit Complete",
            "description": "First comprehensive diversity audit of the entire library collection.",
            "achieved_date": datetime(2025, 5, 1, tzinfo=timezone.utc),
            "celebration_text": "Understanding our collection is the first step to making it better for everyone.",
            "impact_story": "The audit revealed our collection underrepresented Indigenous perspectives, Spanish-language materials, and contemporary diverse voices. A targeted acquisition plan was developed.",
            "milestone_type": "achievement",
            "is_public": True,
            "is_featured": False,
            "display_order": 6,
        },
        {
            "goal_index": 2,
            "title": "Elmdale Renovation Plans Approved",
            "description": "Board approved final architectural plans for the Elmdale Branch renovation.",
            "achieved_date": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "celebration_text": "The plans are in! Elmdale Branch is getting a beautiful makeover.",
            "impact_story": "The renovation will add 2,000 square feet, create a new community meeting room, and bring the facility into full ADA compliance.",
            "milestone_type": "achievement",
            "is_public": True,
            "is_featured": False,
            "display_order": 7,
        },
        # Pending milestones (no achieved_date)
        {
            "goal_index": 0,
            "title": "All-Branch WiFi Upgrade Complete",
            "description": "WiFi infrastructure upgraded to provide full coverage and higher speeds at all branches.",
            "achieved_date": None,
            "celebration_text": "Fast, free WiFi everywhere in the library - connecting our community!",
            "impact_story": None,
            "milestone_type": "achievement",
            "is_public": True,
            "is_featured": False,
            "display_order": 8,
        },
        {
            "goal_index": 1,
            "title": "1,000 Summer Readers",
            "description": "Summer reading program reaches 1,000 enrolled participants.",
            "achieved_date": None,
            "celebration_text": None,
            "impact_story": None,
            "milestone_type": "achievement",
            "is_public": True,
            "is_featured": False,
            "display_order": 9,
        },
        {
            "goal_index": 2,
            "title": "Elmdale Branch Grand Reopening",
            "description": "Renovated Elmdale Branch opens to the public with community celebration.",
            "achieved_date": None,
            "celebration_text": None,
            "impact_story": None,
            "milestone_type": "event",
            "is_public": True,
            "is_featured": False,
            "display_order": 10,
        },
        {
            "goal_index": 3,
            "title": "20 Active Community Partnerships",
            "description": "Reach the goal of 20 active partnership agreements with community organizations.",
            "achieved_date": None,
            "celebration_text": None,
            "impact_story": None,
            "milestone_type": "achievement",
            "is_public": True,
            "is_featured": False,
            "display_order": 11,
        },
    ]

    added_milestones = 0
    for ms in milestones:
        goal_id = goal_ids[ms["goal_index"]][0] if ms["goal_index"] < len(goal_ids) else None
        await session.execute(
            text("""
                INSERT INTO strategic_milestones
                (plan_id, goal_id, title, description, achieved_date,
                 celebration_text, impact_story, is_public, is_featured,
                 display_order, milestone_type, approval_status, created_by_id)
                VALUES
                (:plan_id, :goal_id, :title, :description, :achieved_date,
                 :celebration_text, :impact_story, :is_public, :is_featured,
                 :display_order, :milestone_type, 'approved', :created_by_id)
            """),
            {
                "plan_id": plan_id,
                "goal_id": goal_id,
                "title": ms["title"],
                "description": ms["description"],
                "achieved_date": ms["achieved_date"],
                "celebration_text": ms["celebration_text"],
                "impact_story": ms["impact_story"],
                "is_public": ms["is_public"],
                "is_featured": ms["is_featured"],
                "display_order": ms["display_order"],
                "milestone_type": ms["milestone_type"],
                "created_by_id": user_id,
            },
        )
        added_milestones += 1
        status = "COMPLETED" if ms["achieved_date"] else "PENDING"
        print(f"  Added milestone: '{ms['title']}' [{status}]")

    await session.commit()
    print(f"  Total: 1 plan, {len(goal_ids)} goals, {added_milestones} milestones")


async def seed_audit_logs(session, user_id):
    """Seed audit log entries for board activities and strategic planning."""
    print("\n--- Seeding Audit Log Entries ---")

    # Check board audit logs
    try:
        result = await session.execute(text("SELECT COUNT(*) FROM board_audit_logs"))
        board_count = result.scalar()
    except Exception:
        await session.rollback()
        print("  ⏭️  board_audit_logs table does not exist, skipping audit logs")
        return

    try:
        result = await session.execute(text("SELECT COUNT(*) FROM strategic_audit_logs"))
        strategic_count = result.scalar()
    except Exception:
        await session.rollback()
        print("  ⏭️  strategic_audit_logs table does not exist, skipping audit logs")
        return

    if (board_count and board_count > 0) and (strategic_count and strategic_count > 0):
        print(f"  Audit logs already exist (board: {board_count}, strategic: {strategic_count}), skipping")
        return

    meetings = await get_meeting_ids(session)

    # Board audit log entries
    if not board_count or board_count == 0:
        board_logs = []

        for meeting in meetings:
            meeting_id, title, scheduled_date, is_cancelled = meeting

            # Meeting creation
            board_logs.append({
                "action": "MEETING_CREATED",
                "entity_type": "Meeting",
                "entity_id": meeting_id,
                "meeting_id": meeting_id,
                "details": json.dumps({
                    "new_values": {"title": title, "meeting_type": "regular"},
                    "result": "success",
                }),
                "notes": f"Board meeting '{title}' created.",
                "created_at": scheduled_date - timedelta(days=30),
            })

            # Agenda published
            board_logs.append({
                "action": "MEETING_AGENDA_PUBLISHED",
                "entity_type": "Meeting",
                "entity_id": meeting_id,
                "meeting_id": meeting_id,
                "details": json.dumps({
                    "result": "success",
                    "agenda_items_count": 8,
                }),
                "notes": f"Agenda published for '{title}'.",
                "created_at": scheduled_date - timedelta(days=3),
            })

            if is_cancelled:
                board_logs.append({
                    "action": "MEETING_CANCELLED",
                    "entity_type": "Meeting",
                    "entity_id": meeting_id,
                    "meeting_id": meeting_id,
                    "details": json.dumps({
                        "reason": "Inclement weather",
                        "result": "success",
                    }),
                    "notes": f"Meeting '{title}' cancelled due to inclement weather.",
                    "created_at": scheduled_date - timedelta(days=1),
                })

            if not is_cancelled and scheduled_date < NOW:
                # Minutes created + approved
                board_logs.append({
                    "action": "MINUTES_CREATED",
                    "entity_type": "Minutes",
                    "entity_id": meeting_id,
                    "meeting_id": meeting_id,
                    "details": json.dumps({"result": "success"}),
                    "notes": f"Minutes drafted for '{title}'.",
                    "created_at": scheduled_date + timedelta(days=3),
                })
                board_logs.append({
                    "action": "MINUTES_APPROVED",
                    "entity_type": "Minutes",
                    "entity_id": meeting_id,
                    "meeting_id": meeting_id,
                    "details": json.dumps({
                        "result": "success",
                        "approval_vote": "Approved unanimously",
                    }),
                    "notes": f"Minutes approved for '{title}'.",
                    "created_at": scheduled_date + timedelta(days=30),
                })
                board_logs.append({
                    "action": "MINUTES_PUBLISHED",
                    "entity_type": "Minutes",
                    "entity_id": meeting_id,
                    "meeting_id": meeting_id,
                    "details": json.dumps({"result": "success"}),
                    "notes": f"Minutes published for '{title}'.",
                    "created_at": scheduled_date + timedelta(days=31),
                })

        # Document publication logs
        result = await session.execute(
            text("SELECT id, title FROM board_documents WHERE status = 'published' LIMIT 10")
        )
        docs = result.fetchall()
        for doc in docs:
            board_logs.append({
                "action": "DOCUMENT_PUBLISHED",
                "entity_type": "Document",
                "entity_id": doc[0],
                "meeting_id": None,
                "details": json.dumps({
                    "result": "success",
                    "title": doc[1],
                }),
                "notes": f"Document '{doc[1]}' published.",
                "created_at": NOW - timedelta(days=5),
            })

        # Vote logs
        result = await session.execute(
            text("SELECT id, title, meeting_id, passed FROM board_votes LIMIT 10")
        )
        votes = result.fetchall()
        for vote in votes:
            board_logs.append({
                "action": "VOTE_CREATED",
                "entity_type": "Vote",
                "entity_id": vote[0],
                "meeting_id": vote[2],
                "details": json.dumps({
                    "result": "success",
                    "title": vote[1],
                }),
                "notes": f"Vote created: '{vote[1]}'.",
                "created_at": NOW - timedelta(days=15),
            })
            board_logs.append({
                "action": "VOTE_CLOSED",
                "entity_type": "Vote",
                "entity_id": vote[0],
                "meeting_id": vote[2],
                "details": json.dumps({
                    "result": "success",
                    "passed": vote[3],
                }),
                "notes": f"Vote closed: '{vote[1]}' - {'Passed' if vote[3] else 'Failed'}.",
                "created_at": NOW - timedelta(days=14),
            })

        # Board member creation logs
        members = await get_board_member_ids(session)
        for member in members:
            board_logs.append({
                "action": "BOARD_MEMBER_CREATED",
                "entity_type": "BoardMember",
                "entity_id": member[0],
                "meeting_id": None,
                "details": json.dumps({
                    "result": "success",
                    "name": member[1],
                    "position": member[2],
                }),
                "notes": f"Board member '{member[1]}' ({member[2]}) added.",
                "created_at": NOW - timedelta(days=365),
            })

        added_board = 0
        for log in board_logs:
            # Merge notes into details JSON
            details_str = log["details"]
            await session.execute(
                text("""
                    INSERT INTO board_audit_logs
                    (user_id, action, entity_type, entity_id,
                     details, created_at)
                    VALUES
                    (:user_id, :action, :entity_type, :entity_id,
                     :details, :created_at)
                """),
                {
                    "user_id": user_id,
                    "action": log["action"],
                    "entity_type": log["entity_type"],
                    "entity_id": log["entity_id"],
                    "details": details_str,
                    "created_at": log["created_at"],
                },
            )
            added_board += 1

        print(f"  Added {added_board} board audit log entries")

    # Strategic audit log entries
    if not strategic_count or strategic_count == 0:
        result = await session.execute(text("SELECT id FROM strategic_plans LIMIT 1"))
        plan_row = result.fetchone()
        plan_id = plan_row[0] if plan_row else 1

        result = await session.execute(
            text("SELECT id, title FROM strategic_goals WHERE plan_id = :plan_id ORDER BY id"),
            {"plan_id": plan_id},
        )
        goals = result.fetchall()

        result = await session.execute(
            text("SELECT id, title FROM strategic_milestones WHERE plan_id = :plan_id ORDER BY id"),
            {"plan_id": plan_id},
        )
        milestones = result.fetchall()

        strategic_logs = []

        # Plan creation
        strategic_logs.append({
            "entity_type": "plan",
            "entity_id": plan_id,
            "action": "create",
            "changes": json.dumps({"new_values": {"title": "Building Tomorrow's Library: Strategic Plan 2025-2028", "status": "active"}}),
            "created_at": datetime(2024, 11, 15, tzinfo=timezone.utc),
        })

        # Goal creation and updates
        for goal in goals:
            strategic_logs.append({
                "entity_type": "goal",
                "entity_id": goal[0],
                "action": "create",
                "changes": json.dumps({"new_values": {"title": goal[1], "status": "not_started"}}),
                "created_at": datetime(2025, 1, 5, tzinfo=timezone.utc),
            })
            strategic_logs.append({
                "entity_type": "goal",
                "entity_id": goal[0],
                "action": "update",
                "changes": json.dumps({"old_values": {"status": "not_started"}, "new_values": {"status": "on_track"}}),
                "created_at": datetime(2025, 4, 1, tzinfo=timezone.utc),
            })

        # Milestone creation
        for ms in milestones:
            strategic_logs.append({
                "entity_type": "milestone",
                "entity_id": ms[0],
                "action": "create",
                "changes": json.dumps({"new_values": {"title": ms[1]}}),
                "created_at": datetime(2025, 1, 10, tzinfo=timezone.utc),
            })

        added_strategic = 0
        for log in strategic_logs:
            await session.execute(
                text("""
                    INSERT INTO strategic_audit_logs
                    (entity_type, entity_id, action, changes,
                     user_id, ip_address)
                    VALUES
                    (:entity_type, :entity_id, :action, :changes,
                     :user_id, '127.0.0.1')
                """),
                {
                    "entity_type": log["entity_type"],
                    "entity_id": log["entity_id"],
                    "action": log["action"],
                    "changes": log["changes"],
                    "user_id": user_id,
                },
            )
            added_strategic += 1

        print(f"  Added {added_strategic} strategic audit log entries")

    await session.commit()


async def main():
    """Run all governance seed functions."""
    print("=" * 70)
    print("LSC Library Board Governance Seeder")
    print("Seeds: agenda items, minutes, documents, votes, motions,")
    print("       strategic plan, goals, milestones, and audit logs")
    print("=" * 70)

    try:
        async with async_session() as session:
            user_id = await get_user_id(session)
            if not user_id:
                print("No users found in database. Run seed_test_accounts.py first.")
                return

            print(f"Using user_id={user_id} for created_by fields")

            await seed_agenda_items(session, user_id)
            await seed_meeting_minutes(session, user_id)
            await seed_board_documents(session, user_id)
            await seed_voting_records(session, user_id)
            await seed_strategic_plan(session, user_id)
            await seed_audit_logs(session, user_id)

        print("\n" + "=" * 70)
        print("Board Governance Seeding Complete!")
        print("=" * 70)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
