# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import random
from datetime import datetime, timedelta, timezone, date
from dateutil.relativedelta import relativedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


def _future(days_ahead: int) -> datetime:
    return datetime.now(utc) + timedelta(days=days_ahead)


def _past_date(days_ago: int) -> date:
    return (datetime.now(utc) - timedelta(days=days_ago)).date()


def _third_tuesday(year: int, month: int) -> datetime:
    first = datetime(year, month, 1, 18, 0, 0, tzinfo=utc)
    # Find first Tuesday
    days_until_tuesday = (1 - first.weekday()) % 7
    first_tuesday = first + timedelta(days=days_until_tuesday)
    # Third Tuesday is 2 weeks later
    third_tuesday = first_tuesday + timedelta(weeks=2)
    return third_tuesday


async def seed_board_data_full(session: AsyncSession) -> bool:

    # Get reusable IDs
    users_r = await session.execute(text("SELECT id, first_name, last_name, email, role FROM users WHERE role IN ('staff', 'director', 'admin') ORDER BY id LIMIT 15"))
    users = users_r.fetchall()
    user_ids = [u[0] for u in users]

    now = datetime.now(utc)

    # ════════════════════════════════════════════════════════════════
    # 1. BOARD MEMBERS (8 total)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM board_members"))
    if r.scalar() == 0:
        print("  Seeding board_members...")

        board_data = [
            ("Patricia", "Chen", "patricia.chen@example.org", "(555) 0101", "president",
             "Former librarian with 25+ years in public library management. Passionate about community engagement."),
            ("Robert", "Martinez", "robert.martinez@example.org", "(555) 0102", "vice_president",
             "Business owner and philanthropist. Focuses on strategic growth and development."),
            ("Margaret", "Thompson", "margaret.thompson@example.org", "(555) 0103", "secretary",
             "Retired teacher. Dedicated to youth literacy and educational programming."),
            ("David", "Nakamura", "david.nakamura@example.org", "(555) 0104", "treasurer",
             "CPA with extensive nonprofit financial management experience."),
            ("Lisa", "Williamson", "lisa.williamson@example.org", "(555) 0105", "member",
             "University professor specializing in information sciences and technology."),
            ("James", "Rodriguez", "james.rodriguez@example.org", "(555) 0106", "member",
             "Community advocate and long-time library patron. Represents patron interests."),
            ("Catherine", "Sullivan", "catherine.sullivan@example.org", "(555) 0107", "member",
             "Marketing executive and member of the Friends of the Library board."),
            ("Michael", "Johnson", "michael.johnson@example.org", "(555) 0108", "member",
             "Healthcare administrator. Committed to diversity and accessibility initiatives."),
        ]

        for idx, (fname, lname, email, phone, position, bio) in enumerate(board_data):
            # Term: 3 years, currently in second year
            term_start = _past(days_ago=730)
            term_end = _future(days_ahead=365)

            await session.execute(text("""
                INSERT INTO board_members
                (full_name, email, phone, position, term_start_date, term_end_date, is_current, bio, public_email, user_id, created_at, updated_at)
                VALUES (:fname_lname, :email, :phone, :position, :term_start, :term_end, true, :bio, :email, :user_id, :now, :now)
            """), {
                "fname_lname": f"{fname} {lname}",
                "email": email,
                "phone": phone,
                "position": position,
                "term_start": term_start,
                "term_end": term_end,
                "bio": bio,
                "user_id": user_ids[idx % len(user_ids)] if user_ids else None,
                "now": now
            })

        await session.flush()
        print(f"    Created {len(board_data)} board members")

    # Get board member IDs
    board_r = await session.execute(text("SELECT id, user_id FROM board_members ORDER BY id"))
    _board_rows = board_r.fetchall()
    board_member_ids = [r[0] for r in _board_rows]
    board_member_user_ids = {r[0]: r[1] for r in _board_rows}

    # ════════════════════════════════════════════════════════════════
    # 2. COMMITTEES (5)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM board_committees"))
    if r.scalar() == 0:
        print("  Seeding board_committees...")

        committees_data = [
            ("Finance Committee", "standing",
             "Oversees financial planning, budgeting, and fiscal management of the library.",
             "Review annual budget, monitor revenue/expenses, manage investments, approve contracts over $50k",
             "Third Thursday of each month at 5:00 PM", 3, 5, 2),

            ("Policy Committee", "standing",
             "Develops and reviews library policies and procedures.",
             "Review existing policies, develop new policies, ensure regulatory compliance",
             "First Wednesday of each month at 10:00 AM", 3, 5, 2),

            ("Building & Grounds Committee", "standing",
             "Oversees facility maintenance, capital improvements, and expansion planning.",
             "Facility maintenance oversight, capital project planning, vendor management",
             "Fourth Monday of each month at 4:00 PM", 3, 5, 2),

            ("Personnel Committee", "standing",
             "Handles HR matters, staff development, and director evaluation.",
             "Staff compensation, benefits, professional development, director performance review",
             "Second Tuesday of each month at 3:00 PM", 3, 5, 2),

            ("Friends of the Library Liaison Committee", "standing",
             "Coordinates between board and Friends organization for fundraising and events.",
             "Annual fundraising planning, event coordination, donor relations oversight",
             "As needed, typically quarterly", 2, 4, 1),
        ]

        for name, ctype, description, responsibilities, schedule, min_members, max_members, quorum in committees_data:
            await session.execute(text("""
                INSERT INTO board_committees
                (name, committee_type, status, description, purpose, responsibilities, meeting_schedule,
                 default_meeting_location, min_members, max_members, quorum_requirement, is_public,
                 public_description, created_at, updated_at)
                VALUES (:name, :ctype, 'active', :description, :responsibilities, :responsibilities, :schedule,
                        'L30 Library', :min_members, :max_members, :quorum, true, :description, :now, :now)
            """), {
                "name": name,
                "ctype": ctype,
                "description": description,
                "responsibilities": responsibilities,
                "schedule": schedule,
                "min_members": min_members,
                "max_members": max_members,
                "quorum": quorum,
                "now": now
            })

        await session.flush()
        print(f"    Created {len(committees_data)} committees")

    # Get committee IDs
    comm_r = await session.execute(text("SELECT id FROM board_committees ORDER BY id"))
    committee_ids = [r[0] for r in comm_r.fetchall()]

    # ════════════════════════════════════════════════════════════════
    # 3. COMMITTEE MEMBERS (assign 3-4 board members to each committee)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM board_committee_members"))
    if r.scalar() == 0:
        print("  Seeding board_committee_members...")

        # Distribute board members across committees
        # Finance: Patricia, David (Treasurer), Robert → Finance Chair
        # Policy: Margaret, Patricia, Lisa
        # Building: James, Michael, David
        # Personnel: Robert, Margaret, Michael
        # Friends: Catherine, Lisa

        committee_assignments = [
            (0, [board_member_ids[0], board_member_ids[3], board_member_ids[1]], "Finance Committee"),  # ids 1,2,4 (Patricia, David, Robert)
            (1, [board_member_ids[2], board_member_ids[0], board_member_ids[4]], "Policy Committee"),     # 3,1,5 (Margaret, Patricia, Lisa)
            (2, [board_member_ids[5], board_member_ids[7], board_member_ids[3]], "Building Committee"),   # 6,8,4 (James, Michael, David)
            (3, [board_member_ids[1], board_member_ids[2], board_member_ids[7]], "Personnel Committee"),  # 2,3,8 (Robert, Margaret, Michael)
            (4, [board_member_ids[6], board_member_ids[4]], "Friends Liaison"),                          # 7,5 (Catherine, Lisa)
        ]

        count = 0
        for comm_idx, member_ids, committee_name in committee_assignments:
            for member_idx, member_id in enumerate(member_ids):
                role = "chair" if member_idx == 0 else "member"
                appointed = _past(days_ago=random.randint(90, 730))
                term_end = appointed + relativedelta(months=24)

                await session.execute(text("""
                    INSERT INTO board_committee_members
                    (committee_id, board_member_id, role, appointed_date, term_end_date, is_active, created_at, updated_at)
                    VALUES (:cid, :bid, :role, :appointed, :term_end, true, :now, :now)
                """), {
                    "cid": committee_ids[comm_idx],
                    "bid": member_id,
                    "role": role,
                    "appointed": appointed,
                    "term_end": term_end,
                    "now": now
                })
                count += 1

        await session.flush()
        print(f"    Created {count} committee member assignments")

    # ════════════════════════════════════════════════════════════════
    # 4. BOARD MEETINGS (12 total: 10 past, 2 upcoming on 3rd Tuesday)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM board_meetings"))
    if r.scalar() == 0:
        print("  Seeding board_meetings...")

        meetings = []
        current_year = now.year
        current_month = now.month

        # Create 12 meetings going back 12 months and forward 2 months
        for months_offset in range(-11, 3):
            meeting_month = current_month + months_offset
            meeting_year = current_year

            # Handle year wraparound
            while meeting_month > 12:
                meeting_month -= 12
                meeting_year += 1
            while meeting_month < 1:
                meeting_month += 12
                meeting_year -= 1

            scheduled = _third_tuesday(meeting_year, meeting_month)
            is_past = scheduled < now

            meetings.append({
                "title": f"Regular Board Meeting - {scheduled.strftime('%B %Y')}",
                "scheduled": scheduled,
                "is_past": is_past,
            })

        # Reverse to get chronological order
        meetings = sorted(meetings, key=lambda x: x["scheduled"])

        for mtg in meetings:
            start = mtg["scheduled"]
            end = start + timedelta(hours=2)

            await session.execute(text("""
                INSERT INTO board_meetings
                (meeting_type, title, description, scheduled_date, start_time, end_time, location,
                 is_virtual, notice_status, is_cancelled, quorum_met, minutes_approved, created_at, updated_at)
                VALUES ('regular', :title, 'Regular monthly board meeting', :scheduled, :start, :end,
                        'L30 Library, Main Conference Room', false, 'published', false, true, :minutes_approved, :now, :now)
            """), {
                "title": mtg["title"],
                "scheduled": mtg["scheduled"],
                "start": start,
                "end": end,
                "minutes_approved": mtg["is_past"],
                "now": now
            })

        await session.flush()
        print(f"    Created {len(meetings)} board meetings")

    # Get meeting IDs
    mtg_r = await session.execute(text("SELECT id, scheduled_date FROM board_meetings ORDER BY scheduled_date"))
    meetings_data = mtg_r.fetchall()
    meeting_ids = [m[0] for m in meetings_data]

    # ════════════════════════════════════════════════════════════════
    # 5. AGENDA ITEMS (~6 per meeting, 72 total)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM agenda_items"))
    if r.scalar() == 0:
        print("  Seeding agenda_items...")

        agenda_templates = [
            ("1", "Call to Order and Roll Call", None, None, None, 5, False, "information"),
            ("2", "Approval of Minutes from Previous Meeting", "Secretary", None, None, 10, True, "vote"),
            ("3", "Director's Report", "Director", None, None, 20, False, "discussion"),
            ("4", "Committee Reports", None, None, None, 40, False, "discussion"),
            ("4a", "Finance Committee Report", None, None, None, 10, False, "discussion"),
            ("4b", "Policy Committee Report", None, None, None, 10, False, "discussion"),
            ("4c", "Building & Grounds Report", None, None, None, 10, False, "discussion"),
            ("4d", "Personnel Committee Report", None, None, None, 10, False, "discussion"),
            ("5", "Unfinished/Old Business", None, None, None, 15, True, "discussion"),
            ("6", "New Business", None, None, None, 20, True, "discussion"),
            ("7", "Public Comment", None, None, None, 10, False, "discussion"),
            ("8", "Announcements and Upcoming Events", None, None, None, 5, False, "information"),
            ("9", "Adjournment", None, None, None, 1, False, "information"),
        ]

        count = 0
        for mtg_id in meeting_ids:
            for sort_idx, (item_num, title, presenter, desc, action, duration, requires_action, action_type) in enumerate(agenda_templates, 1):
                await session.execute(text("""
                    INSERT INTO agenda_items
                    (meeting_id, item_number, title, description, presenter, estimated_duration_minutes,
                     requires_action, action_type, sort_order, created_at, updated_at)
                    VALUES (:mtg_id, :item_num, :title, :desc, :presenter, :duration, :req_action, :action_type, :sort_ord, :now, :now)
                """), {
                    "mtg_id": mtg_id,
                    "item_num": str(item_num),
                    "sort_ord": sort_idx,
                    "title": title,
                    "desc": desc or f"See {title.lower()} agenda",
                    "presenter": presenter,
                    "duration": duration,
                    "req_action": requires_action,
                    "action_type": action_type,
                    "now": now
                })
                count += 1

        await session.flush()
        print(f"    Created {count} agenda items")

    # ════════════════════════════════════════════════════════════════
    # 6. ATTENDANCE RECORDS (for past meetings only)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM meeting_attendance"))
    if r.scalar() == 0:
        print("  Seeding meeting_attendance...")

        # Get past meetings only
        past_mtg_r = await session.execute(text("""
            SELECT id FROM board_meetings WHERE scheduled_date < :now ORDER BY scheduled_date
        """), {"now": now})
        past_meeting_ids = [m[0] for m in past_mtg_r.fetchall()]

        count = 0
        for mtg_id in past_meeting_ids:
            # Randomize which board members attend (usually 7-8 of 8)
            attending = random.randint(7, 8)
            attending_ids = random.sample(board_member_ids, attending)

            for member_id in board_member_ids:
                is_attending = member_id in attending_ids
                status = "present" if is_attending else random.choice(["absent", "excused"])
                rsvp_status = "attending" if is_attending else "not_attending"
                checked_in = (_past(random.randint(1, 350)) + timedelta(hours=random.randint(0, 2))) if is_attending else None

                await session.execute(text("""
                    INSERT INTO meeting_attendance
                    (meeting_id, user_id, rsvp_status, rsvp_at, attendance_status, checked_in_at, is_voting_member, is_guest, created_at, updated_at)
                    VALUES (:mtg_id, :user_id, :rsvp, :rsvp_at, :status, :checked_in, true, false, :now, :now)
                """), {
                    "mtg_id": mtg_id,
                    "user_id": board_member_user_ids.get(member_id) or member_id,
                    "rsvp": rsvp_status,
                    "rsvp_at": _past(random.randint(2, 7)),
                    "status": status,
                    "checked_in": checked_in,
                    "now": now
                })
                count += 1

        await session.flush()
        print(f"    Created {count} attendance records")

    # ════════════════════════════════════════════════════════════════
    # 7. BOARD MINUTES (for past meetings)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM board_minutes"))
    if r.scalar() == 0:
        print("  Seeding board_minutes...")

        past_mtg_r = await session.execute(text("""
            SELECT id, scheduled_date FROM board_meetings WHERE scheduled_date < :now ORDER BY scheduled_date
        """), {"now": now})
        past_meetings = past_mtg_r.fetchall()

        count = 0
        for mtg_id, scheduled_date in past_meetings:
            members_present = [
                {"id": random.choice(board_member_ids), "name": "Board Member", "title": "member"}
                for _ in range(random.randint(7, 8))
            ]

            sections = [
                {"title": "Call to Order", "content": f"Meeting called to order at 6:05 PM by President Patricia Chen.", "order": 1},
                {"title": "Roll Call", "content": f"{len(members_present)} members present, 1 absent.", "order": 2},
                {"title": "Approval of Minutes", "content": "Previous meeting minutes approved unanimously.", "order": 3},
                {"title": "Committee Reports", "content": "Finance: Budget under control. Policy: Two new policies approved. Building: Renovation project 90% complete.", "order": 4},
                {"title": "Director's Report", "content": "Circulation up 12% this quarter. New ebook collection launched. Partnerships expanding.", "order": 5},
                {"title": "Action Items", "content": "Director to present staffing plan by next meeting. Facilities team to complete HVAC maintenance.", "order": 6},
                {"title": "Adjournment", "content": "Meeting adjourned at 8:15 PM.", "order": 7},
            ]

            approved_at = scheduled_date + timedelta(days=random.randint(3, 10))
            called_at = scheduled_date + timedelta(hours=random.randint(0, 5), minutes=random.randint(0, 59))
            adjourned_at = called_at + timedelta(hours=2, minutes=random.randint(0, 59))

            await session.execute(text("""
                INSERT INTO board_minutes
                (meeting_id, status, sections, meeting_called_to_order_at, meeting_adjourned_at,
                 members_present, members_absent, members_excused, quorum_met, quorum_count,
                 approved, approved_at, approval_vote_result, prepared_by_id, prepared_at,
                 created_at, updated_at, created_by_id)
                VALUES (:mtg_id, 'approved', :sections, :called_at, :adjourned_at,
                        :members_present, '[]'::jsonb, '[]'::jsonb, true, '7 of 8 members present',
                        true, :approved_at, 'Approved 7-0', :user_id, :prepared_at,
                        :now, :now, :user_id)
            """), {
                "mtg_id": mtg_id,
                "sections": json.dumps(sections),
                "called_at": called_at,
                "adjourned_at": adjourned_at,
                "members_present": json.dumps([{"id": m, "name": "Member"} for m in members_present[:3]]),
                "approved_at": approved_at,
                "prepared_at": called_at + timedelta(days=1),
                "user_id": random.choice(user_ids),
                "now": now
            })
            count += 1

        await session.flush()
        print(f"    Created {count} minutes records")

    # ════════════════════════════════════════════════════════════════
    # 8. BOARD DOCUMENTS (20 total: bylaws, policies, budget reports, etc.)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM board_documents"))
    if r.scalar() == 0:
        print("  Seeding board_documents...")

        docs_data = [
            ("Library Bylaws", "bylaws", "Current bylaws and governance structure", "bylaws.pdf", "bylaws_v3.pdf", "approved"),
            ("Strategic Plan 2024-2026", "policy", "Three-year strategic plan", "strategic_plan_2024.pdf", "strategic_plan_v1.pdf", "published"),
            ("Financial Policies Manual", "policy", "Financial management and procurement policies", "financial_policies.pdf", "financial_policies_v2.pdf", "published"),
            ("Collection Development Policy", "policy", "Guidelines for book selection and collection management", "collection_dev.pdf", "collection_dev_v4.pdf", "published"),
            ("FY2024 Budget", "financial_report", "Annual budget for fiscal year 2024", "budget_fy2024.pdf", "budget_fy2024_final.pdf", "published"),
            ("FY2025 Budget", "financial_report", "Proposed annual budget for fiscal year 2025", "budget_fy2025.pdf", "budget_fy2025_draft.pdf", "under_review"),
            ("Q1 2024 Financial Report", "financial_report", "Quarterly financial performance", "q1_2024_report.pdf", "q1_2024_report.pdf", "published"),
            ("Q2 2024 Financial Report", "financial_report", "Quarterly financial performance", "q2_2024_report.pdf", "q2_2024_report.pdf", "published"),
            ("Annual Report 2023", "financial_report", "Comprehensive annual report to community", "annual_report_2023.pdf", "annual_report_2023_final.pdf", "published"),
            ("Personnel Handbook", "policy", "Employee policies and benefits", "personnel_handbook.pdf", "personnel_handbook_v3.pdf", "published"),
            ("Technology Policy", "policy", "IT security and acceptable use policies", "tech_policy.pdf", "tech_policy_v2.pdf", "published"),
            ("Public Services Guidelines", "policy", "Patron services and conduct policies", "public_services.pdf", "public_services_v3.pdf", "published"),
            ("Board Meeting Packet - March 2024", "packet", "Full packet for March board meeting", "board_packet_mar2024.pdf", "board_packet_mar2024.pdf", "published"),
            ("Board Meeting Packet - April 2024", "packet", "Full packet for April board meeting", "board_packet_apr2024.pdf", "board_packet_apr2024.pdf", "published"),
            ("Capital Campaign Proposal", "presentation", "Proposal for building expansion", "capital_campaign.pdf", "capital_campaign_v2.pdf", "under_review"),
            ("Diversity & Inclusion Action Plan", "policy", "Framework for diversity initiatives", "diversity_plan.pdf", "diversity_plan_v1.pdf", "approved"),
            ("Remote Services Strategic Plan", "policy", "Digital services expansion strategy", "remote_services.pdf", "remote_services_v2.pdf", "published"),
            ("Audit Report 2023", "financial_report", "External audit findings and recommendations", "audit_2023.pdf", "audit_2023_final.pdf", "published"),
            ("Job Descriptions - Administrative", "policy", "Administrative staff job descriptions", "job_desc_admin.pdf", "job_desc_admin_v2.pdf", "published"),
            ("Equipment & Technology Plan", "policy", "IT infrastructure and equipment refresh schedule", "tech_plan.pdf", "tech_plan_v3.pdf", "published"),
        ]

        count = 0
        for title, dtype, description, filename, filepath, status in docs_data:
            # Link some docs to recent meetings
            meeting_id = None
            if random.random() > 0.6:
                meeting_id = random.choice(meeting_ids[-6:])  # Last 6 meetings

            published = status == "published"
            published_date = _past(days_ago=random.randint(10, 300)) if published else None

            await session.execute(text("""
                INSERT INTO board_documents
                (document_type, title, description, filename, file_path, file_size_bytes, mime_type,
                 version_number, status, published_date, published_by_id, is_public, is_confidential,
                 meeting_id, created_at, updated_at, created_by_id)
                VALUES (:dtype, :title, :desc, :filename, :filepath, :size, 'application/pdf',
                        1, :status, :pub_date, :user_id, true, false,
                        :mtg_id, :now, :now, :user_id)
            """), {
                "dtype": dtype,
                "title": title,
                "desc": description,
                "filename": filename,
                "filepath": f"/documents/board/{filepath}",
                "size": random.randint(50000, 5000000),
                "status": status,
                "pub_date": published_date,
                "user_id": random.choice(user_ids) if published else None,
                "mtg_id": meeting_id,
                "now": now
            })
            count += 1

        await session.flush()
        print(f"    Created {count} board documents")

    # ════════════════════════════════════════════════════════════════
    # 9. BOARD VOTES (5 votes across past meetings)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM board_votes"))
    if r.scalar() == 0:
        print("  Seeding board_votes...")

        past_mtg_r = await session.execute(text("""
            SELECT id, scheduled_date FROM board_meetings WHERE scheduled_date < :now ORDER BY scheduled_date DESC LIMIT 8
        """), {"now": now})
        past_meetings_ids = [m[0] for m in past_mtg_r.fetchall()]

        votes_data = [
            ("Approval of FY2025 Budget", "Proposed FY2025 budget of $2.4M with 5% increase for staffing", "simple_majority", True, 7, 0, 1),
            ("Approval of Strategic Plan", "Three-year strategic plan focusing on digital services expansion", "simple_majority", True, 8, 0, 0),
            ("Director Evaluation - Positive", "Annual performance review and contract renewal for current director", "simple_majority", True, 7, 1, 0),
            ("Capital Campaign Authorization", "Authorization to launch $1M building expansion capital campaign", "two_thirds", True, 7, 1, 0),
            ("New Technology Policy", "Updated IT security and acceptable use policy", "simple_majority", True, 8, 0, 0),
        ]

        count = 0
        for title, description, vote_type, passed, yes, no, abstain in votes_data:
            if count >= len(past_meetings_ids):
                break

            mtg_id = past_meetings_ids[count]
            mtg_date_r = await session.execute(text("SELECT scheduled_date FROM board_meetings WHERE id = :id"), {"id": mtg_id})
            mtg_date = mtg_date_r.scalar()

            opens = mtg_date + timedelta(hours=1)
            closes = opens + timedelta(hours=2)
            closed_actual = closes + timedelta(minutes=random.randint(1, 30))

            await session.execute(text("""
                INSERT INTO board_votes
                (meeting_id, title, description, vote_type, opens_at, closes_at, status,
                 quorum_required, passed, final_tally_yes, final_tally_no, final_tally_abstain,
                 closed_by_id, closed_at_actual, created_at, updated_at, created_by_id)
                VALUES (:mtg_id, :title, :desc, :vote_type, :opens, :closes, 'closed',
                        5, :passed, :yes, :no, :abstain,
                        :user_id, :closed, :now, :now, :user_id)
            """), {
                "mtg_id": mtg_id,
                "title": title,
                "desc": description,
                "vote_type": vote_type,
                "opens": opens,
                "closes": closes,
                "passed": passed,
                "yes": yes,
                "no": no,
                "abstain": abstain,
                "user_id": random.choice(user_ids),
                "closed": closed_actual,
                "now": now
            })
            count += 1

        await session.flush()
        print(f"    Created {count} board votes")

    # ════════════════════════════════════════════════════════════════
    # 10. BOARD MOTIONS (8 total across recent meetings)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM board_motions"))
    if r.scalar() == 0:
        print("  Seeding board_motions...")

        past_mtg_r = await session.execute(text("""
            SELECT id, scheduled_date FROM board_meetings WHERE scheduled_date < :now ORDER BY scheduled_date DESC LIMIT 8
        """), {"now": now})
        past_meetings_ids = [(m[0], m[1]) for m in past_mtg_r.fetchall()]

        motions_data = [
            ("M-2024-001", "Approval of FY2025 Budget", "Motion to approve the FY2025 library budget as presented by the Finance Committee.", "Increased funding for digital services and staff development.", "passed", 1),
            ("M-2024-002", "Strategic Plan Adoption", "Motion to adopt the 2024-2026 Strategic Plan.", "Strategic focus on technology and community engagement.", "passed", 2),
            ("M-2024-003", "Director Contract Renewal", "Motion to renew director's contract for another year with 3% salary increase.", "Performance evaluation positive, contract renewal recommended.", "passed", 3),
            ("M-2024-004", "Capital Campaign Authorization", "Motion to authorize capital campaign for library building expansion.", "Proposed expansion will add 2,000 sq ft for teen services and technology.", "passed", 4),
            ("M-2024-005", "Technology Policy Revision", "Motion to approve revised technology acceptable use policy.", "Updated to address emerging security concerns and BYOD protocols.", "passed", 5),
            ("M-2024-006", "Bylaw Amendment", "Motion to amend bylaws to change committee term limits from 2 to 3 years.", "Provides continuity for committee work and strategic initiatives.", "tabled", 6),
            ("M-2024-007", "Personnel Policy Update", "Motion to adopt updated remote work policy for administrative staff.", "Allows flexible work arrangements while maintaining service levels.", "passed", 7),
            ("M-2024-008", "Audit Report Acceptance", "Motion to accept the 2023 external audit report.", "No material findings; one minor observation noted.", "passed", 0),
        ]

        count = 0
        for motion_num, title, motion_text, rationale, status, meeting_offset in motions_data:
            if meeting_offset >= len(past_meetings_ids):
                continue

            mtg_id, mtg_date = past_meetings_ids[meeting_offset]
            moved_by_id = random.choice(board_member_ids)
            seconded_by_id = random.choice([x for x in board_member_ids if x != moved_by_id])

            moved = mtg_date + timedelta(hours=random.randint(0, 2))
            seconded = moved + timedelta(minutes=random.randint(1, 5))
            discussion_opened = seconded + timedelta(minutes=random.randint(1, 10))
            discussion_closed = discussion_opened + timedelta(minutes=random.randint(5, 30))
            vote_called = discussion_closed + timedelta(minutes=random.randint(1, 5))
            outcome_recorded = vote_called + timedelta(minutes=random.randint(1, 10))

            await session.execute(text("""
                INSERT INTO board_motions
                (meeting_id, motion_type, status, motion_number, title, motion_text, rationale,
                 moved_by_id, moved_at, seconded_by_id, seconded_at,
                 discussion_opened_at, discussion_closed_at, vote_called_at, outcome_recorded_at,
                 created_at, updated_at, created_by_id)
                VALUES (:mtg_id, 'main', :status, :motion_num, :title, :motion_text, :rationale,
                        :moved_by, :moved, :seconded_by, :seconded,
                        :disc_open, :disc_close, :vote_called, :outcome,
                        :now, :now, :user_id)
            """), {
                "mtg_id": mtg_id,
                "status": status,
                "motion_num": motion_num,
                "title": title,
                "motion_text": motion_text,
                "rationale": rationale,
                "moved_by": moved_by_id,
                "moved": moved,
                "seconded_by": seconded_by_id,
                "seconded": seconded,
                "disc_open": discussion_opened,
                "disc_close": discussion_closed,
                "vote_called": vote_called,
                "outcome": outcome_recorded,
                "user_id": random.choice(user_ids),
                "now": now
            })
            count += 1

        await session.flush()
        print(f"    Created {count} board motions")

    # ════════════════════════════════════════════════════════════════
    # 11. BOARD RESOLUTIONS (6 total, linked to motions)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM board_resolutions"))
    if r.scalar() == 0:
        print("  Seeding board_resolutions...")

        resolutions_data = [
            ("RES-2024-001", "FY2025 Budget Adoption", "Budget",
             "WHEREAS the Board Finance Committee has thoroughly reviewed the proposed FY2025 budget;",
             "RESOLVED that the L30 Library Board of Trustees adopts the FY2025 budget as presented, with a total appropriation of $2,400,000.",
             "Annual budget approved with 5% increase for digital services expansion and staff compensation."),

            ("RES-2024-002", "Strategic Plan Endorsement", "Policy",
             "WHEREAS the Board Strategic Planning Committee has developed a comprehensive three-year strategic plan;",
             "RESOLVED that the Board endorses the 2024-2026 Strategic Plan with focus on digital transformation, community engagement, and diversity initiatives.",
             "Three-year strategic framework to guide library operations and resource allocation."),

            ("RES-2024-003", "Director Performance and Contract Renewal", "Personnel",
             "WHEREAS the director has demonstrated excellent leadership and achieved all established performance goals;",
             "RESOLVED that the director's contract is renewed for an additional year with a 3% salary adjustment effective immediately.",
             "Annual director evaluation completed with renewal recommended unanimously."),

            ("RES-2024-004", "Capital Campaign Authorization", "Policy",
             "WHEREAS the library building requires expansion to meet community needs for teen and technology services;",
             "RESOLVED that the Board authorizes a capital campaign to raise $1,000,000 for building expansion and renovation.",
             "Capital campaign approved to support $1.2M expansion project over 3 years."),

            ("RES-2024-005", "Technology Security Policy", "Policy",
             "WHEREAS cybersecurity and data protection are critical library concerns;",
             "RESOLVED that the Board adopts the updated Technology Security Policy to address emerging threats and BYOD protocols.",
             "Updated IT security policy approved to protect patron and staff data."),

            ("RES-2024-006", "Recognition of Retiring Board Member", "Policy",
             "WHEREAS John Smith has served with distinction on the Board for six years;",
             "RESOLVED that the Board expresses its gratitude for his service and designates him as Board Member Emeritus.",
             "Recognition of board member transition and acknowledgment of dedicated service."),
        ]

        count = 0
        for res_num, title, category, preamble, resolution_text, summary in resolutions_data:
            # Link to recent meetings
            mtg_id = random.choice(meeting_ids[-6:]) if meeting_ids else None
            proposed_by_id = random.choice(board_member_ids)
            proposed = _past(days_ago=random.randint(5, 60))
            adopted = proposed + timedelta(days=random.randint(1, 5))

            await session.execute(text("""
                INSERT INTO board_resolutions
                (resolution_number, title, status, preamble, resolution_text, summary,
                 category, meeting_id, proposed_date, proposed_by_id, adopted_date,
                 effective_date, is_public, published_date, created_at, updated_at, created_by_id)
                VALUES (:res_num, :title, 'adopted', :preamble, :res_text, :summary,
                        :category, :mtg_id, :proposed, :proposed_by, :adopted,
                        :adopted, true, :adopted, :now, :now, :user_id)
            """), {
                "res_num": res_num,
                "title": title,
                "preamble": preamble,
                "res_text": resolution_text,
                "summary": summary,
                "category": category,
                "mtg_id": mtg_id,
                "proposed": proposed,
                "proposed_by": proposed_by_id,
                "adopted": adopted,
                "user_id": random.choice(user_ids),
                "now": now
            })
            count += 1

        await session.flush()
        print(f"    Created {count} board resolutions")

    # ════════════════════════════════════════════════════════════════
    # 12. ACTION ITEMS (5-6 per past meeting)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM meeting_action_items"))
    if r.scalar() == 0:
        print("  Seeding meeting_action_items...")

        past_mtg_r = await session.execute(text("""
            SELECT id, scheduled_date FROM board_meetings WHERE scheduled_date < :now ORDER BY scheduled_date DESC LIMIT 6
        """), {"now": now})
        past_meetings = past_mtg_r.fetchall()

        action_items_data = [
            ("Present staffing plan", "Develop and present comprehensive staffing analysis for next meeting", 1, "high", 14),
            ("Complete HVAC maintenance", "Facility team to complete HVAC system maintenance", 0, "high", 30),
            ("Finalize capital campaign materials", "Marketing team to prepare campaign brochures and videos", 2, "high", 45),
            ("Update technology inventory", "IT to complete network and equipment audit", 0, "medium", 21),
            ("Review patron feedback", "Director to analyze Q2 patron survey and prepare summary", 1, "medium", 14),
            ("Arrange vendor bids", "Facilities to obtain three bids for expansion project", 3, "high", 30),
        ]

        count = 0
        for mtg in past_meetings:
            mtg_id, mtg_date = mtg
            # Add 4-5 action items per meeting
            for _ in range(random.randint(4, 5)):
                title, desc, assigned_idx, priority, due_days = random.choice(action_items_data)
                assigned_to = random.choice(user_ids)
                due = mtg_date + timedelta(days=due_days)

                # Some are completed
                status = random.choice(["completed", "completed", "in_progress"])
                completed_at = (due + timedelta(days=random.randint(-5, 2))) if status == "completed" else None

                await session.execute(text("""
                    INSERT INTO meeting_action_items
                    (meeting_id, title, description, assigned_to_id, assigned_by_id, status, priority,
                     due_date, completed_at, created_at, updated_at, created_by_id)
                    VALUES (:mtg_id, :title, :desc, :assigned_to, :assigned_by, :status, :priority,
                            :due_date, :completed, :now, :now, :user_id)
                """), {
                    "mtg_id": mtg_id,
                    "title": title,
                    "desc": desc,
                    "assigned_to": assigned_to,
                    "assigned_by": random.choice(user_ids),
                    "status": status,
                    "priority": priority,
                    "due_date": due.date(),
                    "completed": completed_at,
                    "user_id": random.choice(user_ids),
                    "now": now
                })
                count += 1

        await session.flush()
        print(f"    Created {count} action items")

    print("  Board governance seed completed successfully!")

    # ════════════════════════════════════════════════════════════════
    # ANALYZE TABLES
    # ════════════════════════════════════════════════════════════════
    print("  Running ANALYZE on board tables...")
    await session.execute(text("ANALYZE board_members"))
    await session.execute(text("ANALYZE board_committees"))
    await session.execute(text("ANALYZE board_committee_members"))
    await session.execute(text("ANALYZE board_meetings"))
    await session.execute(text("ANALYZE agenda_items"))
    await session.execute(text("ANALYZE meeting_attendance"))
    await session.execute(text("ANALYZE board_minutes"))
    await session.execute(text("ANALYZE board_documents"))
    await session.execute(text("ANALYZE board_votes"))
    await session.execute(text("ANALYZE board_motions"))
    await session.execute(text("ANALYZE board_resolutions"))
    await session.execute(text("ANALYZE meeting_action_items"))
    await session.flush()

    return True
