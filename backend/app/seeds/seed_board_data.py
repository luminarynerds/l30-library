# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.board import (
    BoardMember, BoardPosition,
    BoardMeeting, BoardMeetingType,
    AgendaItem,
    BoardMinutes, MinutesStatus,
    BoardMotion, MotionType, MotionStatus,
    BoardVote, VoteType, VoteStatus,
    BoardVoteCast, VoteChoice,
    MeetingAttendance, AttendanceStatus, RSVPStatus,
    MeetingActionItem, ActionItemStatus, ActionItemPriority,
    Committee, CommitteeType, CommitteeStatus,
    CommitteeMember, CommitteeMemberRole,
    BoardDocument, DocumentType, DocumentStatus,
    BoardResolution, ResolutionStatus,
    PublicComment, CommentType, CommentStatus,
)

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


def _future(days_ahead: int) -> datetime:
    return datetime.now(utc) + timedelta(days=days_ahead)


def _third_tuesday(year: int, month: int) -> datetime:
    first_day = datetime(year, month, 1, 18, 0, tzinfo=utc)
    # Find first Tuesday (weekday 1)
    days_until_tuesday = (1 - first_day.weekday()) % 7
    first_tuesday = first_day + timedelta(days=days_until_tuesday)
    return first_tuesday + timedelta(weeks=2)


def _at_time(date, hour: int, minute: int = 0) -> datetime:
    if isinstance(date, datetime):
        return date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return datetime(date.year, date.month, date.day, hour, minute, tzinfo=utc)


# ── Board member profiles ──────────────────────────────────────────

BOARD_MEMBERS = [
    {
        "full_name": "Margaret Thompson",
        "position": BoardPosition.PRESIDENT,
        "bio": "Retired educator with 30 years of teaching experience. Passionate about literacy and lifelong learning. Serving her second term on the board.",
        "public_email": "mthompson@library.board",
        "office_hours": "First Monday of each month, 2-4 PM",
        "term_years_ago": 4,
    },
    {
        "full_name": "David Okonkwo",
        "position": BoardPosition.VICE_PRESIDENT,
        "bio": "Local business owner and community organizer. Advocates for expanded digital services and technology access programs.",
        "public_email": "dokonkwo@library.board",
        "office_hours": "By appointment",
        "term_years_ago": 3,
    },
    {
        "full_name": "Susan Park",
        "position": BoardPosition.SECRETARY,
        "bio": "Attorney specializing in municipal law. Ensures board proceedings comply with open meeting laws and proper governance protocols.",
        "public_email": "spark@library.board",
        "office_hours": "Wednesdays 10 AM - 12 PM",
        "term_years_ago": 2,
    },
    {
        "full_name": "Robert Fitzgerald",
        "position": BoardPosition.TREASURER,
        "bio": "CPA with expertise in nonprofit financial management. Oversees library budget and fiscal accountability.",
        "public_email": "rfitzgerald@library.board",
        "office_hours": "By appointment",
        "term_years_ago": 3,
    },
    {
        "full_name": "Maria Santos",
        "position": BoardPosition.MEMBER,
        "bio": "Youth services advocate and parent volunteer. Champions children's programming and early literacy initiatives.",
        "public_email": "msantos@library.board",
        "office_hours": "Second Thursday, 3-5 PM",
        "term_years_ago": 1,
    },
    {
        "full_name": "James Whitfield",
        "position": BoardPosition.MEMBER,
        "bio": "Retired IT director. Provides guidance on technology infrastructure, cybersecurity, and digital transformation.",
        "public_email": "jwhitfield@library.board",
        "office_hours": "By appointment",
        "term_years_ago": 2,
    },
    {
        "full_name": "Angela Brooks",
        "position": BoardPosition.MEMBER,
        "bio": "Librarian emerita and ALA fellow. Brings deep institutional knowledge and professional expertise to board deliberations.",
        "public_email": "abrooks@library.board",
        "office_hours": "Fridays 1-3 PM",
        "term_years_ago": 5,
    },
]

# ── Committee definitions ───────────────────────────────────────────

COMMITTEES = [
    {
        "name": "Finance & Budget Committee",
        "committee_type": CommitteeType.STANDING,
        "description": "Oversees the library's financial health, reviews the annual budget, and monitors expenditures.",
        "purpose": "Ensure fiscal responsibility and transparency in all library financial operations.",
        "responsibilities": "Budget review, audit oversight, financial policy recommendations, grant funding review.",
        "meeting_schedule": "First Monday of each month at 5:00 PM",
        "min_members": 2,
        "max_members": 4,
    },
    {
        "name": "Policy & Governance Committee",
        "committee_type": CommitteeType.STANDING,
        "description": "Reviews and recommends updates to library policies, bylaws, and governance procedures.",
        "purpose": "Maintain clear, equitable, and up-to-date policies governing library operations.",
        "responsibilities": "Policy drafts, bylaw amendments, governance best practices, compliance review.",
        "meeting_schedule": "Second Wednesday of each month at 4:30 PM",
        "min_members": 2,
        "max_members": 4,
    },
    {
        "name": "Friends of the Library Liaison Committee",
        "committee_type": CommitteeType.AD_HOC,
        "description": "Coordinates between the Board of Trustees and the Friends of the Library organization.",
        "purpose": "Strengthen the partnership between the library board and its volunteer support group.",
        "responsibilities": "Joint event planning, fundraising coordination, volunteer recognition.",
        "meeting_schedule": "Quarterly",
        "min_members": 1,
        "max_members": 3,
    },
]

# ── Meeting agenda templates ────────────────────────────────────────

REGULAR_AGENDA = [
    ("Call to Order", "President calls the meeting to order.", False, 2),
    ("Roll Call and Establishment of Quorum", "Secretary records attendance and confirms quorum.", False, 3),
    ("Approval of Previous Meeting Minutes", "Board reviews and approves minutes from the prior meeting.", True, 5),
    ("Public Comment Period", "Members of the public may address the board on any topic.", False, 15),
    ("Treasurer's Report", "Treasurer presents the monthly financial summary.", True, 10),
    ("Director's Report", "Library Director provides an operational update.", False, 15),
    ("Committee Reports", "Standing and ad-hoc committees report on recent activities.", False, 15),
    ("Old Business", "Discussion of previously tabled or ongoing items.", True, 20),
    ("New Business", "Introduction and discussion of new agenda items.", True, 20),
    ("Announcements", "Board members share upcoming events and dates.", False, 5),
    ("Adjournment", "President adjourns the meeting.", False, 1),
]

# ── Motion templates for realistic meeting content ──────────────────

MOTION_TEMPLATES = [
    {
        "title": "Approve Previous Meeting Minutes",
        "text": "I move to approve the minutes of the previous regular board meeting as presented.",
        "rationale": "Minutes have been reviewed and found accurate.",
    },
    {
        "title": "Accept Monthly Financial Report",
        "text": "I move to accept the Treasurer's monthly financial report and file it for audit.",
        "rationale": "Financial report has been reviewed by the Finance Committee.",
    },
    {
        "title": "Approve Summer Reading Program Budget",
        "text": "I move to approve a budget allocation of $4,500 for the 2026 Summer Reading Program materials and prizes.",
        "rationale": "The program serves over 200 youth participants annually and promotes early literacy.",
    },
    {
        "title": "Authorize HVAC System Repair",
        "text": "I move to authorize the Director to contract HVAC repairs not to exceed $8,000 from the maintenance reserve.",
        "rationale": "The main branch HVAC system requires immediate repair to maintain comfortable patron conditions.",
    },
    {
        "title": "Adopt Updated Internet Use Policy",
        "text": "I move to adopt the revised Internet Use Policy as recommended by the Policy Committee.",
        "rationale": "The current policy has not been updated in three years and does not address current cybersecurity best practices.",
    },
    {
        "title": "Approve Collection Development Plan",
        "text": "I move to approve the 2026 Collection Development Plan as presented by the Director.",
        "rationale": "The plan aligns with community needs assessment findings and strategic goals.",
    },
    {
        "title": "Approve Meeting Room Fee Schedule",
        "text": "I move to approve the updated meeting room fee schedule effective next quarter.",
        "rationale": "Fee schedule has been benchmarked against comparable library systems.",
    },
    {
        "title": "Accept Donation from Friends of the Library",
        "text": "I move to accept a donation of $2,000 from the Friends of the Library for children's programming.",
        "rationale": "Donation supports board-approved strategic priority of youth services.",
    },
    {
        "title": "Approve Staff Training Budget",
        "text": "I move to approve $3,200 for staff attendance at the state library conference.",
        "rationale": "Professional development is essential for maintaining quality service.",
    },
    {
        "title": "Extend Library Hours Pilot",
        "text": "I move to extend the Sunday hours pilot program through the end of the fiscal year.",
        "rationale": "Usage data shows strong community demand for Sunday hours.",
    },
]

# ── Public comment examples ─────────────────────────────────────────

PUBLIC_COMMENTS = [
    {
        "commenter_name": "Patricia Hawkins",
        "subject": "Thank You for Extended Hours",
        "comment_text": "I want to thank the board for the extended evening hours. As a working parent, the later closing time has made it possible for my family to visit the library regularly. My children have checked out more books this year than ever before.",
        "is_resident": True,
    },
    {
        "commenter_name": "Tom Richardson",
        "subject": "Request for More Large Print Materials",
        "comment_text": "Our senior center book group has noticed the large print collection is quite limited. We'd appreciate the board considering additional funding for large print materials, especially popular fiction and mysteries.",
        "is_resident": True,
        "organization": "Oakdale Senior Center",
    },
    {
        "commenter_name": "Dr. Amira Hassan",
        "subject": "ESL Program Expansion",
        "comment_text": "The library's ESL conversation circles have been wonderful for our community. I'm here to request the board consider expanding the program to include additional languages and evening sessions.",
        "is_resident": True,
        "organization": "Community Literacy Coalition",
    },
    {
        "commenter_name": "Kevin Murphy",
        "subject": "Parking Lot Safety Concern",
        "comment_text": "The lighting in the south parking lot is inadequate, especially during winter months when it gets dark early. I'd like the board to consider upgrading the lighting for patron safety.",
        "is_resident": True,
    },
]


async def seed_board_data(session: AsyncSession) -> bool:

    r = await session.execute(text("SELECT COUNT(*) FROM board_members"))
    if r.scalar() > 0:
        print("  Board data already seeded, skipping")
        return True

    # Grab existing user IDs for FK references
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    if not users:
        print("  No users found — cannot seed board data")
        return False

    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    if not staff_ids:
        staff_ids = [u[0] for u in users]
    admin_id = staff_ids[0]

    now = datetime.now(utc)

    # ── 1. Board Members ────────────────────────────────────────────
    print("  Seeding board members...")
    board_members = []
    for i, data in enumerate(BOARD_MEMBERS):
        term_start = now - timedelta(days=data["term_years_ago"] * 365)
        member = BoardMember(
            full_name=data["full_name"],
            position=data["position"],
            bio=data["bio"],
            public_email=data["public_email"],
            office_hours=data["office_hours"],
            is_current=True,
            term_start_date=term_start.date(),
            term_end_date=(term_start + timedelta(days=3 * 365)).date(),
            user_id=staff_ids[i % len(staff_ids)],
        )
        member.created_at = term_start
        session.add(member)
        board_members.append(member)

    await session.flush()
    print(f"    Created {len(board_members)} board members")

    # ── 2. Committees ───────────────────────────────────────────────
    print("  Seeding committees...")
    committees = []
    for data in COMMITTEES:
        committee = Committee(
            name=data["name"],
            committee_type=data["committee_type"],
            status=CommitteeStatus.ACTIVE,
            description=data["description"],
            purpose=data["purpose"],
            responsibilities=data["responsibilities"],
            meeting_schedule=data["meeting_schedule"],
            min_members=data["min_members"],
            max_members=data["max_members"],
            quorum_requirement=2,
            is_public=True,
            established_date=_past(365 * 2).date(),
            created_by_id=admin_id,
        )
        committee.created_at = _past(365 * 2)
        session.add(committee)
        committees.append(committee)

    await session.flush()
    print(f"    Created {len(committees)} committees")

    # ── 3. Committee Members ────────────────────────────────────────
    print("  Seeding committee memberships...")
    # Finance: Treasurer (chair) + 2 members
    finance = committees[0]
    treasurer = board_members[3]  # Fitzgerald
    for idx, (bm, role) in enumerate([
        (treasurer, CommitteeMemberRole.CHAIR),
        (board_members[1], CommitteeMemberRole.MEMBER),  # Okonkwo
        (board_members[6], CommitteeMemberRole.MEMBER),  # Brooks
    ]):
        cm = CommitteeMember(
            committee_id=finance.id,
            board_member_id=bm.id,
            role=role,
            appointed_date=_past(300).date(),
            is_active=True,
            created_by_id=admin_id,
        )
        session.add(cm)

    # Policy: Secretary (chair) + 2 members
    policy = committees[1]
    for bm, role in [
        (board_members[2], CommitteeMemberRole.CHAIR),   # Park
        (board_members[0], CommitteeMemberRole.MEMBER),   # Chen
        (board_members[5], CommitteeMemberRole.MEMBER),   # Whitfield
    ]:
        cm = CommitteeMember(
            committee_id=policy.id,
            board_member_id=bm.id,
            role=role,
            appointed_date=_past(300).date(),
            is_active=True,
            created_by_id=admin_id,
        )
        session.add(cm)

    # Friends Liaison: 2 members
    friends = committees[2]
    for bm, role in [
        (board_members[4], CommitteeMemberRole.CHAIR),   # Santos
        (board_members[6], CommitteeMemberRole.MEMBER),   # Brooks
    ]:
        cm = CommitteeMember(
            committee_id=friends.id,
            board_member_id=bm.id,
            role=role,
            appointed_date=_past(200).date(),
            is_active=True,
            created_by_id=admin_id,
        )
        session.add(cm)

    await session.flush()
    print("    Assigned members to all committees")

    # ── 4. Past Meetings (6 months) + 1 Upcoming ───────────────────
    print("  Seeding board meetings...")
    meetings = []

    for months_ago in range(6, 0, -1):
        month = now.month - months_ago
        year = now.year
        while month <= 0:
            month += 12
            year -= 1

        meeting_date = _third_tuesday(year, month)
        meeting = BoardMeeting(
            title=f"Regular Board Meeting — {meeting_date.strftime('%B %Y')}",
            meeting_type=BoardMeetingType.REGULAR,
            scheduled_date=meeting_date.date(),
            start_time=_at_time(meeting_date, 18, 0),
            end_time=_at_time(meeting_date, 19, 30),
            location="Main Branch — Community Room A",
            is_virtual=False,
            is_cancelled=False,
            public_comment_enabled=True,
            public_comment_instructions="Members of the public may address the board for up to 3 minutes on any topic. Please sign in at the door.",
            accessibility_info="Room is wheelchair accessible. Assistive listening devices available upon request.",
            quorum_met=True,
            created_by_id=admin_id,
        )
        meeting.created_at = meeting_date - timedelta(days=14)
        session.add(meeting)
        meetings.append(meeting)

    # Upcoming meeting
    next_month = now.month + 1
    next_year = now.year
    if next_month > 12:
        next_month -= 12
        next_year += 1

    upcoming_date = _third_tuesday(next_year, next_month)
    upcoming_meeting = BoardMeeting(
        title=f"Regular Board Meeting — {upcoming_date.strftime('%B %Y')}",
        meeting_type=BoardMeetingType.REGULAR,
        scheduled_date=upcoming_date.date(),
        start_time=_at_time(upcoming_date, 18, 0),
        end_time=_at_time(upcoming_date, 19, 30),
        location="Main Branch — Community Room A",
        is_virtual=False,
        is_cancelled=False,
        public_comment_enabled=True,
        public_comment_instructions="Members of the public may address the board for up to 3 minutes on any topic. Please sign in at the door.",
        accessibility_info="Room is wheelchair accessible. Assistive listening devices available upon request.",
        quorum_met=False,
        created_by_id=admin_id,
    )
    upcoming_meeting.created_at = now - timedelta(days=7)
    session.add(upcoming_meeting)
    meetings.append(upcoming_meeting)

    await session.flush()
    print(f"    Created {len(meetings)} meetings (6 past + 1 upcoming)")

    # ── 5. Agenda Items for each past meeting ───────────────────────
    print("  Seeding agenda items...")
    for meeting in meetings[:6]:  # past meetings only
        for sort_order, (title, desc, requires_action, duration) in enumerate(REGULAR_AGENDA, 1):
            item = AgendaItem(
                meeting_id=meeting.id,
                item_number=f"{sort_order}",
                title=title,
                description=desc,
                sort_order=sort_order,
                requires_action=requires_action,
                estimated_duration_minutes=duration,
                created_by_id=admin_id,
            )
            item.created_at = meeting.created_at
            session.add(item)

    # Upcoming meeting gets agenda too
    for sort_order, (title, desc, requires_action, duration) in enumerate(REGULAR_AGENDA, 1):
        item = AgendaItem(
            meeting_id=upcoming_meeting.id,
            item_number=f"{sort_order}",
            title=title,
            description=desc,
            sort_order=sort_order,
            requires_action=requires_action,
            estimated_duration_minutes=duration,
            created_by_id=admin_id,
        )
        item.created_at = upcoming_meeting.created_at
        session.add(item)

    await session.flush()
    print(f"    Created agenda items for {len(meetings)} meetings")

    # ── 6. Attendance for past meetings ─────────────────────────────
    print("  Seeding attendance records...")
    for meeting in meetings[:6]:
        for bm in board_members:
            # Most members attend; occasionally one is absent/excused
            is_absent = random.random() < 0.1
            status = AttendanceStatus.EXCUSED if is_absent else AttendanceStatus.PRESENT

            attendance = MeetingAttendance(
                meeting_id=meeting.id,
                user_id=bm.user_id,
                rsvp_status=RSVPStatus.ATTENDING if not is_absent else RSVPStatus.NOT_ATTENDING,
                attendance_status=status,
                is_voting_member=True,
                is_guest=False,
                attended_remotely=False,
                created_by_id=admin_id,
            )
            if not is_absent:
                attendance.checked_in_at = _at_time(meeting.scheduled_date, 17, 55)
            else:
                attendance.absence_reason = random.choice([
                    "Family obligation",
                    "Out of town",
                    "Illness",
                ])

            session.add(attendance)

    await session.flush()
    print("    Created attendance for all past meetings")

    # ── 7. Motions & Votes for past meetings ────────────────────────
    print("  Seeding motions and votes...")
    motion_pool = list(MOTION_TEMPLATES)
    random.shuffle(motion_pool)
    motion_idx = 0

    for meeting in meetings[:6]:
        # 2-3 motions per meeting
        num_motions = random.randint(2, 3)
        for m_num in range(num_motions):
            template = motion_pool[motion_idx % len(motion_pool)]
            motion_idx += 1

            mover = random.choice(board_members)
            seconder = random.choice([bm for bm in board_members if bm.id != mover.id])

            meeting_dt = _at_time(meeting.scheduled_date, 18, 30)

            # Create vote first
            yes_count = random.randint(5, 7)
            no_count = 7 - yes_count if yes_count < 7 else 0
            abstain_count = 7 - yes_count - no_count

            vote = BoardVote(
                meeting_id=meeting.id,
                title=template["title"],
                description=template["text"],
                vote_type=VoteType.SIMPLE_MAJORITY,
                status=VoteStatus.CLOSED,
                quorum_required=4,
                passed=yes_count > 3,
                final_tally_yes=yes_count,
                final_tally_no=no_count,
                final_tally_abstain=abstain_count,
                opens_at=meeting_dt + timedelta(minutes=30 + m_num * 15),
                closes_at=meeting_dt + timedelta(minutes=35 + m_num * 15),
                closed_at_actual=meeting_dt + timedelta(minutes=35 + m_num * 15),
                closed_by_id=admin_id,
                created_by_id=admin_id,
            )
            session.add(vote)
            await session.flush()

            # Cast individual votes
            choices = (
                [VoteChoice.YES] * yes_count
                + [VoteChoice.NO] * no_count
                + [VoteChoice.ABSTAIN] * abstain_count
            )
            random.shuffle(choices)
            for i, bm in enumerate(board_members):
                if i < len(choices) and bm.user_id is not None:
                    cast = BoardVoteCast(
                        vote_id=vote.id,
                        board_member_id=bm.user_id,
                        choice=choices[i],
                        cast_at=vote.opens_at + timedelta(seconds=30 * i),
                    )
                    session.add(cast)

            # Create motion linked to vote
            motion = BoardMotion(
                meeting_id=meeting.id,
                motion_type=MotionType.MAIN,
                status=MotionStatus.PASSED if vote.passed else MotionStatus.FAILED,
                motion_number=f"{meeting.scheduled_date.strftime('%Y%m')}-{m_num + 1:02d}",
                title=template["title"],
                motion_text=template["text"],
                rationale=template["rationale"],
                moved_by_id=mover.id,
                moved_at=vote.opens_at - timedelta(minutes=10),
                seconded_by_id=seconder.id,
                seconded_at=vote.opens_at - timedelta(minutes=9),
                discussion_opened_at=vote.opens_at - timedelta(minutes=8),
                discussion_closed_at=vote.opens_at,
                vote_id=vote.id,
                vote_called_at=vote.opens_at,
                outcome_recorded_at=vote.closes_at,
                created_by_id=admin_id,
            )
            session.add(motion)

    await session.flush()
    print("    Created motions and votes for past meetings")

    # ── 8. Minutes for past meetings ────────────────────────────────
    print("  Seeding meeting minutes...")
    for meeting in meetings[:6]:
        present_names = [bm.full_name for bm in board_members if random.random() > 0.1]
        absent_names = [bm.full_name for bm in board_members if bm.full_name not in present_names]

        meeting_dt = _at_time(meeting.scheduled_date, 18, 0)
        adjourn_dt = _at_time(meeting.scheduled_date, 19, 25)

        minutes = BoardMinutes(
            meeting_id=meeting.id,
            status=MinutesStatus.APPROVED,
            meeting_called_to_order_at=meeting_dt,
            meeting_adjourned_at=adjourn_dt,
            members_present=present_names,
            members_absent=absent_names,
            members_excused=absent_names,
            quorum_met=True,
            quorum_count=str(len(present_names)),
            approved=True,
            approved_at=meeting_dt + timedelta(days=30),
            approved_by_id=admin_id,
            approval_vote_result="Approved unanimously",
            notes="Minutes recorded by the Secretary.",
            prepared_by_id=admin_id,
            prepared_at=meeting_dt + timedelta(days=3),
            created_by_id=admin_id,
            sections=[
                {"title": "Call to Order", "content": f"President Chen called the meeting to order at 6:00 PM."},
                {"title": "Roll Call", "content": f"Present: {', '.join(present_names)}. A quorum was established."},
                {"title": "Public Comment", "content": "The public comment period was opened. See attached comments."},
                {"title": "Reports", "content": "The Treasurer presented the monthly financial summary. The Director provided an operational update."},
                {"title": "Adjournment", "content": f"The meeting was adjourned at {adjourn_dt.strftime('%I:%M %p')}."},
            ],
        )
        minutes.created_at = meeting_dt + timedelta(days=3)
        session.add(minutes)

    await session.flush()
    print("    Created minutes for 6 past meetings")

    # ── 9. Action Items ─────────────────────────────────────────────
    print("  Seeding action items...")
    action_items_data = [
        ("Get HVAC repair quotes", "Obtain three competitive quotes for HVAC system repair.", ActionItemPriority.HIGH, ActionItemStatus.COMPLETED, 2),
        ("Draft updated internet policy", "Revise internet use policy based on committee recommendations.", ActionItemPriority.MEDIUM, ActionItemStatus.COMPLETED, 3),
        ("Prepare Summer Reading budget", "Itemize costs for 2026 Summer Reading Program.", ActionItemPriority.MEDIUM, ActionItemStatus.COMPLETED, 4),
        ("Survey large print collection", "Audit current large print holdings and identify gaps.", ActionItemPriority.LOW, ActionItemStatus.IN_PROGRESS, 1),
        ("Schedule parking lot lighting assessment", "Contact facilities to assess south lot lighting.", ActionItemPriority.HIGH, ActionItemStatus.IN_PROGRESS, 0),
        ("Research Sunday hours staffing model", "Develop sustainable staffing plan for continued Sunday hours.", ActionItemPriority.MEDIUM, ActionItemStatus.NOT_STARTED, 0),
    ]

    for title, desc, priority, status, meeting_idx in action_items_data:
        m = meetings[min(meeting_idx, len(meetings) - 2)]  # keep in past meetings
        assignee = random.choice(board_members)
        ai = MeetingActionItem(
            meeting_id=m.id,
            title=title,
            description=desc,
            assigned_to_id=assignee.user_id,
            assigned_to_name=assignee.full_name,
            assigned_by_id=admin_id,
            status=status,
            priority=priority,
            due_date=(_at_time(m.scheduled_date, 0, 0) + timedelta(days=30)).date(),
            progress_percentage=100 if status == ActionItemStatus.COMPLETED else (50 if status == ActionItemStatus.IN_PROGRESS else 0),
            requires_board_update=True,
            created_by_id=admin_id,
        )
        if status == ActionItemStatus.COMPLETED:
            ai.completed_at = _at_time(m.scheduled_date, 12) + timedelta(days=random.randint(5, 25))
        session.add(ai)

    await session.flush()
    print(f"    Created {len(action_items_data)} action items")

    # ── 10. Public Comments ─────────────────────────────────────────
    print("  Seeding public comments...")
    for i, pc_data in enumerate(PUBLIC_COMMENTS):
        target_meeting = meetings[i % 6]  # spread across past meetings
        comment = PublicComment(
            meeting_id=target_meeting.id,
            comment_type=CommentType.IN_PERSON,
            status=CommentStatus.READ_INTO_RECORD,
            commenter_name=pc_data["commenter_name"],
            subject=pc_data["subject"],
            comment_text=pc_data["comment_text"],
            is_resident=pc_data.get("is_resident", True),
            organization=pc_data.get("organization"),
            submitted_at=_at_time(target_meeting.scheduled_date, 18, 15),
            moderated_by_id=admin_id,
            moderated_at=_at_time(target_meeting.scheduled_date, 18, 10),
            include_in_minutes=True,
            redact_contact_info=True,
            time_allocated_seconds=180,
            speaker_order=i + 1,
        )
        session.add(comment)

    await session.flush()
    print(f"    Created {len(PUBLIC_COMMENTS)} public comments")

    # ── 11. Board Resolution ────────────────────────────────────────
    print("  Seeding board resolution...")
    resolution = BoardResolution(
        resolution_number="2026-001",
        title="Resolution Adopting the Updated Internet Use Policy",
        status=ResolutionStatus.ADOPTED,
        preamble="WHEREAS, the Board of Trustees recognizes the importance of providing safe and equitable internet access to all library patrons; and WHEREAS, the current Internet Use Policy has not been updated since 2023;",
        resolution_text="NOW, THEREFORE, BE IT RESOLVED that the Board of Trustees of the Bébé Memorial Library hereby adopts the Updated Internet Use Policy as presented and reviewed by the Policy & Governance Committee, effective immediately.",
        summary="Formally adopts the revised Internet Use Policy with updated cybersecurity provisions and acceptable use guidelines.",
        category="Policy",
        is_public=True,
        proposed_date=meetings[2].scheduled_date,
        proposed_by_id=board_members[2].id,  # Park (Secretary / Policy Chair)
        adopted_date=meetings[3].scheduled_date,
        effective_date=meetings[3].scheduled_date,
        meeting_id=meetings[3].id,
        committee_id=committees[1].id,  # Policy committee
        published_date=_at_time(meetings[3].scheduled_date, 12) + timedelta(days=1),
        published_by_id=admin_id,
        created_by_id=admin_id,
    )
    session.add(resolution)

    await session.flush()
    print("    Created 1 board resolution")

    # ── 12. Board Documents ─────────────────────────────────────────
    print("  Seeding board documents...")
    docs_data = [
        ("FY2026 Q1 Financial Report", DocumentType.FINANCIAL_REPORT, "Quarterly financial summary for October-December 2025.", "fy2026-q1-financial-report.pdf", meetings[1]),
        ("FY2026 Q2 Financial Report", DocumentType.FINANCIAL_REPORT, "Quarterly financial summary for January-March 2026.", "fy2026-q2-financial-report.pdf", meetings[4]),
        ("Updated Internet Use Policy - Final", DocumentType.POLICY, "Board-approved revision of the library Internet Use Policy.", "internet-use-policy-2026.pdf", meetings[3]),
        ("2026 Collection Development Plan", DocumentType.OTHER, "Annual plan for collection acquisitions and weeding.", "collection-development-plan-2026.pdf", meetings[4]),
        ("Summer Reading Program Proposal", DocumentType.PRESENTATION, "Budget and program outline for 2026 Summer Reading.", "summer-reading-proposal-2026.pdf", meetings[3]),
    ]

    for title, doc_type, desc, filename, meeting in docs_data:
        doc = BoardDocument(
            title=title,
            document_type=doc_type,
            description=desc,
            filename=filename,
            file_path=f"/uploads/board/{filename}",
            mime_type="application/pdf",
            meeting_id=meeting.id,
            status=DocumentStatus.PUBLISHED,
            is_public=True,
            is_confidential=False,
            is_current_version=True,
            version_number=1,
            published_date=_at_time(meeting.scheduled_date, 12),
            published_by_id=admin_id,
            view_count=random.randint(5, 40),
            download_count=random.randint(1, 15),
            created_by_id=admin_id,
        )
        doc.created_at = _at_time(meeting.scheduled_date, 10) - timedelta(days=3)
        session.add(doc)

    await session.flush()
    print(f"    Created {len(docs_data)} board documents")

    # ── Done ────────────────────────────────────────────────────────
    await session.commit()

    # Fix sequences
    seq_tables = [
        "board_members", "board_meetings", "agenda_items", "board_minutes",
        "board_motions", "board_votes", "board_votes_cast", "meeting_attendance",
        "meeting_action_items", "board_public_comments", "board_resolutions",
        "board_documents", "board_committees", "board_committee_members",
    ]
    for table in seq_tables:
        await session.execute(text(
            f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
        ))
    await session.commit()

    print("  Board data seeding complete!")
    return True
