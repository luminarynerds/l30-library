# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""ORM-driven demo seeder for a fresh L30 distribution install.

Replaces the retired ``demo/seed.sql`` (see
docs/dist-install-characterization.md §6): that raw-SQL seed was never
copied into the backend image, and even copied in by hand it failed against
the PII-encrypted schema (stale ``ON CONFLICT (email)``, and ~1,200 columns
across the model layer carry a Python-side ``default=`` with no
``server_default``, so hand-written SQL is one column away from a NOT NULL
violation at all times). Inserting through the SQLAlchemy models instead
means every Python-side default, PII blind index (``email_hash`` /
``first_name_hash`` / etc, computed by ``User``'s ``before_insert``
listener), and enum coercion is honored for free -- no raw SQL anywhere in
this module.

Fully deterministic: no ``random``, no ``datetime.now()``. All date math is
relative to SEED_DATE, and the catalog fixture (fixtures/orange_catalog.json)
is a fixed, committed file, so re-running this against an empty database
always produces the same catalog/patron/circulation shape.

Idempotency: gated on catalog size (see ``_already_seeded``) rather than
per-row upserts -- cheap (one COUNT query) and prevents /setup/demo/load
from duplicating ~2,000+ catalog rows on a second call. It does not detect
partial/mixed manual data; it only skips when the fixture-sized catalog is
already present.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.catalog import (
    Audience,
    BookBinding,
    CatalogingStatus,
    CatalogItem,
    ItemStatus,
    ItemType,
)
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.event import Event
from app.models.library_branding import LibraryBranding
from app.models.multi_branch import Branch, BranchStatus, BranchType, LibrarySystem, SystemSettings
from app.models.user import PatronStatus, User, UserRole

# --- "lived-in" community signal models (home shelves, reviews, staff picks,
# event turnout, announcements, blog). Same deterministic/ORM discipline as
# everything above: no random, no datetime.now(), all math off SEED_DATE.
from app.models.announcements import Announcement, AnnouncementPriority, AnnouncementStatus
from app.models.blog import BlogPost, BlogPostStatus
from app.models.board import BoardMeeting, BoardMember, BoardMinutes
from app.models.homepage_content import LibraryHours, LibraryHoursOverride
from app.models.event_registration import EventRegistration, EventRegistrationStatus
from app.models.event_waitlist import EventWaitlistEntry, WaitlistStatus
from app.models.home import HomeShelf, HomeShelfQueryKind
from app.models.review import Review
from app.models.staff_picks import StaffPicksItem, StaffPicksList

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "orange_catalog.json"

# Fixed anchor for HISTORICAL synthetic date math (events, board minutes, blog,
# registrations, reviews) so that dataset stays byte-for-byte reproducible.
# EXCEPTION: active circulation (checkouts + ready holds) is dated relative to
# the actual seed run instead -- see _seed_circulation -- so a demo installed
# long after SEED_DATE doesn't seed already-overdue loans that trip the nightly
# overdue job and auto-suspend the demo patron before the browse->checkout eval.
SEED_DATE = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

# Below this size, /setup/demo/load re-runs; at/above it, seed_demo() treats
# the catalog as already populated and skips (see _already_seeded).
_SEEDED_THRESHOLD = 2000

# Demo logins use a DIFFERENT password per role, so one leaked credential
# doesn't unlock every role and the demo reads realistically. The base comes
# from DEMO_LOGIN_PASSWORD (set it to a private value on any internet-facing
# demo); it defaults to a documented dev value for local/throwaway installs.
# Each role's password is "{base}-{role}", so by default:
#   patron -> demo-2026-patron   child -> demo-2026-kid    staff -> demo-2026-staff
#   library admin -> demo-2026-admin   director -> demo-2026-director
# The full-access super_admin is handled separately (opt-in) -- see below.
_DEMO_LOGIN_BASE = os.environ.get("DEMO_LOGIN_PASSWORD", "").strip() or "demo-2026"
_DEMO_ROLE_SLUG = {
    UserRole.PATRON: "patron",
    UserRole.CHILD: "kid",
    UserRole.STAFF: "staff",
    UserRole.LIBRARY_ADMIN: "admin",
    UserRole.DIRECTOR: "director",
}
# Hash each role's password once at import -- bcrypt is expensive, never per row.
_DEMO_ROLE_HASHES = {
    role: hash_password(f"{_DEMO_LOGIN_BASE}-{slug}")
    for role, slug in _DEMO_ROLE_SLUG.items()
}

# The full-access super_admin demo login (Avery Sinclair) is opt-in and does
# NOT use the shared demo password: a repo-known password on a super_admin is a
# full takeover of any internet-facing demo. If DEMO_SUPERADMIN_PASSWORD is
# unset, the account is not seeded at all (secure by default). Set it in the
# instance .env to enable the whole-app demo login with a private password.
_DEMO_SUPERADMIN_PASSWORD = os.environ.get("DEMO_SUPERADMIN_PASSWORD", "").strip()

# ---------------------------------------------------------------------------
# Demo identity profiles.
#
# FICTIONAL (Little Schitt Creek) is the DEFAULT: a fork's /setup/demo/load
# must never seed another real library's board roster, phone number, street
# address, or history. ORANGE (a real library, the onboarding program's
# case #1) is opt-in via DEMO_PROFILE=orange -- set only on orange-demo.
# ---------------------------------------------------------------------------

# Matches the established fictional universe in frontend/src/constants/contact.ts
# and the stock About page (which already ships the LSC timeline + director's
# note, so this profile deliberately omits about_story).
FICTIONAL: dict[str, Any] = {
    "library_name": "Little Schitt Creek Library",
    "code": "LSCL",
    "email": "hello@example.com",
    "phone": "(555) 123-4566",
    "address_line1": "123 Main Street",
    "city": "Schitt Creek",
    "state": "OH",
    "zip_code": "44101",
    # Stock L30 identity palette (LibraryBranding column defaults).
    "primary_color": "#E89B44",
    "accent_color": "#8B5E5E",
    "logo_url": "",
    "hero_image_url": "",
    "display_font": "",
    "body_font": "",
    "secondary_color": "",
    "surface_color": "",
    "ink_color": "",
    "nav_style": "default",
    "hero_title": "Welcome to the Little Schitt Creek Library",
    "hero_subtitle": "You belong here.",
    "tagline": "A little library with a lot going on.",
    # Entirely fictional trustees -- no real person shares these seats.
    "board_roster": [
        ("Rosalind Beck", "president"),
        ("Harold Osei", "vice_president"),
        ("June Castellanos", "treasurer"),
        ("Miriam Zhao", "member"),
        ("Gus Pemberton", "member"),
    ],
    "staff_email_domain": "littleschittcreek.example.org",
    "blog_images": [
        "/images/history/library-modern.webp",
        "/images/families-community.webp",
        "/images/families-community.webp",
    ],
}

ORANGE: dict[str, Any] = {
    "library_name": "Orange Public Library",
    "code": "ORPL",
    "email": "info@orangepubliclibrary.example.org",
    # Public main number from orangepl.org (published contact info, not PII).
    "phone": "973-786-3988",
    "address_line1": "348 Main Street",
    "city": "Orange",
    "state": "NJ",
    "zip_code": "07050",
    # Contrast-verified Beaux-Arts palette (Task 11). Burnt-orange and
    # gold-ink both pass WCAG AA as text on the cream surface_color and as
    # button backgrounds with white text; do not swap in the brighter
    # #ED9205 front-door accent here, it fails both checks.
    "primary_color": "#9A4A0F",
    "accent_color": "#6F5514",
    "logo_url": "/orange-logo.png",
    "hero_image_url": "/orange-exterior-hero.jpg",
    "display_font": "Cormorant Garamond",
    "body_font": "",
    "secondary_color": "#0F1F3D",
    "surface_color": "#F2ECDF",
    "ink_color": "#26221C",
    "nav_style": "needs-based",
    "hero_title": "Welcome to the Orange Public Library",
    "hero_subtitle": "You belong here.",
    # orangepl.org/history.php: "library tradition began in 1883".
    "tagline": "Serving Orange since 1883.",
    # Real history from orangepl.org/history.php -- replaces the stock
    # fictional About-page timeline.
    "about_story": {
        "intro": [
            "Orange's library tradition goes back to 1883, and since 1901 it has "
            "lived in one of the city's great buildings: a Beaux-Arts landmark "
            "designed by McKim, Mead & White, its columns still standing over Main "
            "Street. In 1945, Orange residents voted to make it a free public "
            "library, owned by and open to everyone.",
            "More than a century on, the mission hasn't changed: a place where "
            "every resident can read, learn, connect, and get help, no purchase "
            "necessary, no questions asked.",
        ],
        "timeline": [
            {"year": "1883", "title": "A library for Orange",
             "description": "The Orange library tradition begins, with a lending "
                            "collection serving the growing township."},
            {"year": "1901", "title": "A landmark home",
             "description": "McKim, Mead & White design the library's Beaux-Arts "
                            "building on Main Street, with its Ionic and Doric "
                            "columns and richly ornamented details."},
            {"year": "1945", "title": "Free to all",
             "description": "Orange residents vote by referendum to establish a "
                            "free public library, open to every resident at no "
                            "charge."},
            {"year": "1981", "title": "Historic recognition",
             "description": "The library's building earns historic landmark "
                            "designation, preserving it for future generations."},
            {"year": "Today", "title": "Still serving Orange",
             "description": "More than 72,000 items, programs for every "
                            "generation, and a building that has anchored Main "
                            "Street for over a century."},
        ],
        # The stock About page ships a fictional director's note ("Marlene W.").
        # Never fabricate words for Orange's real (acting) director -- hide the
        # section until their staff writes their own in the branding editor.
        "hide_director_note": True,
    },
    # Real Board of Trustees roster from orangepl.org/board_staff.php. position
    # is free text in the model/schema; the members page renders unknown values
    # verbatim, so the two municipal-alternate seats keep their real titles.
    "board_roster": [
        ("Angie Smith", "president"),
        ("Theresa Mason", "vice_president"),
        ("Karen Harris", "Superintendent's Alternate"),
        ("Louis Copeland", "Mayor's Alternate"),
        ("David McKnight", "member"),
    ],
    "staff_email_domain": "orangepubliclibrary.example.org",
    "blog_images": [
        "/orange-exterior-hero.jpg",
        "/orange-interior-hero.jpg",
        "/images/families-community.webp",
    ],
}

DEMO_PROFILES: dict[str, dict[str, Any]] = {
    "fictional": FICTIONAL,
    "orange": ORANGE,
}


def _default_profile() -> dict[str, Any]:
    """Resolve the seed identity from DEMO_PROFILE (default: fictional)."""
    key = os.environ.get("DEMO_PROFILE", "").strip().lower() or "fictional"
    return DEMO_PROFILES.get(key, FICTIONAL)

_ITEM_TYPE_MAP = {
    "book": ItemType.book,
    "dvd": ItemType.dvd,
    "cd": ItemType.cd,
    "game": ItemType.game,
}
_AUDIENCE_MAP = {
    "adult": Audience.adult,
    "children": Audience.children,
    "young_adult": Audience.young_adult,
    "all_ages": Audience.all_ages,
}

# Synthetic patron name pools -- combined deterministically (index math, no
# randomness) below. None of these correspond to real patrons.
FIRST_NAMES = [
    "Elena", "Marcus", "Priya", "Jamal", "Sophie", "Kenji", "Fatima", "Liam",
    "Anika", "Diego", "Nadia", "Owen", "Mei", "Theo", "Zara", "Riley",
    "Yuki", "Finn", "Amara", "Noah", "Grace", "Hassan", "Ingrid", "Julian",
    "Keiko", "Luis", "Maya", "Nathaniel", "Olamide", "Paulina", "Quinn",
    "Rosa", "Samuel", "Tara", "Umar", "Valentina", "Wei", "Ximena", "Yusuf",
    "Zoe",
]
LAST_NAMES = [
    "Vasquez", "Chen", "Sharma", "Washington", "Dubois", "Tanaka", "Alrashid",
    "Obrien", "Johansson", "Morales", "Petrov", "Campbell", "Lin", "Anderson",
    "Okafor", "Macpherson", "Sato", "Nguyen", "Osei", "Kowalski",
    "Fitzgerald", "Haddad", "Larsen", "Delgado", "Yamamoto", "Reyes",
    "Patel", "Whitfield", "Adeyemi", "Kowalczyk", "Alvarez", "Kim", "Novak",
    "Singh", "Farouk", "Castillo", "Zhang", "Torres", "Ibrahim", "Bennett",
]

# (first, last, staff_role, UserRole)
STAFF = [
    ("Priya", "Nakamura", "front_desk", UserRole.STAFF),
    ("Andre", "Silva", "cataloger", UserRole.STAFF),
    ("Grace", "Ibeh", "youth_services", UserRole.STAFF),
    ("Malik", "Reyes", "circulation_manager", UserRole.STAFF),
    ("Helena", "Vogt", "branch_manager", UserRole.LIBRARY_ADMIN),
    ("Oscar", "Delgado", "it_support", UserRole.STAFF),
    ("Naomi", "Fischer", "programs_coordinator", UserRole.STAFF),
    ("Derek", "Whitfield", "director", UserRole.DIRECTOR),
    # Full-access demo login: super_admin passes every role gate, including
    # the admin-only areas a director can't reach.
    ("Avery", "Sinclair", "systems_admin", UserRole.SUPER_ADMIN),
]

# (title, category, audience, day_offset_from_SEED_DATE, start_hour)
EVENT_TEMPLATES = [
    ("Toddler Storytime", "Story Time", "Children", -15, 10),
    ("Bilingual Storytime (Spanish/English)", "Story Time", "Children", -12, 10),
    ("Sensory-Friendly Storytime", "Story Time", "Children", -9, 9),
    ("Baby Rhyme Time", "Story Time", "Children", -6, 10),
    ("Homework Help Drop-In", "Education", "Children", -3, 15),
    ("Teen Anime Club", "Club", "Teens", 0, 16),
    ("Adult Book Club: Contemporary Fiction", "Book Club", "Adults", 3, 18),
    ("STEM Workshop: Circuit Blocks", "Workshop", "Children", 6, 14),
    ("Author Talk: Local Voices Series", "Author Event", "Adults", 9, 18),
    ("Job Search Help Desk", "Community", "Adults", 12, 13),
    ("ESL Conversation Circle", "Education", "Adults", 15, 11),
    ("Chess Club", "Club", "All ages", 18, 16),
    ("Maker Monday: 3D Printing Intro", "Workshop", "Teens", 21, 16),
    ("Healthcare Enrollment Assistance", "Community", "Adults", 24, 10),
    ("Financial Literacy Series: Balance Wealth and Wisdom", "Workshop", "Adults", 27, 13),
    ("VITA Free Tax Help", "Community", "Adults", 30, 9),
    ("Friends of the Library Book Sale", "Community", "All ages", 33, 10),
    ("Summer Reading Kickoff Party", "Program", "Children", 36, 11),
    ("Open Mic Poetry Night", "Program", "Adults", 39, 19),
    ("Family Movie Night", "Program", "All ages", 42, 18),
    ("Board Game Night", "Club", "All ages", 45, 17),
    ("Coding Club for Kids", "Club", "Children", 48, 15),
    ("Zumba with Pastor P", "Wellness", "Adults", 51, 14),
    ("Slow Motion, Mindful Yoga", "Wellness", "Adults", 54, 9),
    ("Local History Talk: Our 1901 Landmark Building", "Author Event", "Adults", 57, 18),
    ("Voter Registration Drive", "Community", "Adults", 60, 12),
    ("Teen Volunteer Orientation", "Community", "Teens", 63, 16),
    ("Small Business Resource Fair", "Community", "Adults", 66, 10),
    ("Digital Literacy for Seniors", "Education", "Adults", 69, 10),
    ("Preschool Craft & Play", "Story Time", "Children", 72, 10),
]

# Typical small-library week (based on Orange's posted schedule; generic
# enough for any profile). day_of_week uses the JS convention (0=Sunday) to
# match the /library-hours API.
WEEKLY_HOURS = [
    (0, None, None, True),            # Sunday: closed
    (1, time(9), time(18), False),    # Monday
    (2, time(9), time(20), False),    # Tuesday
    (3, time(9), time(20), False),    # Wednesday
    (4, time(9), time(20), False),    # Thursday
    (5, time(9), time(18), False),    # Friday
    (6, time(9), time(14), False),    # Saturday
]

# Typical US public-library holiday closure list mapped onto 2026 dates.
HOLIDAY_CLOSURES_2026 = [
    (date(2026, 1, 1), "New Year's Day"),
    (date(2026, 1, 19), "Martin Luther King Jr.'s Birthday"),
    (date(2026, 2, 12), "Lincoln's Birthday"),
    (date(2026, 2, 16), "Presidents Day"),
    (date(2026, 4, 3), "Good Friday"),
    (date(2026, 5, 25), "Memorial Day"),
    (date(2026, 6, 19), "Juneteenth"),
    (date(2026, 7, 4), "Independence Day"),
    (date(2026, 9, 7), "Labor Day"),
    (date(2026, 10, 12), "Columbus Day"),
    (date(2026, 11, 3), "Election Day"),
    (date(2026, 11, 11), "Veteran's Day"),
    (date(2026, 11, 26), "Thanksgiving Day"),
    (date(2026, 11, 27), "Day after Thanksgiving"),
    (date(2026, 12, 24), "Christmas Eve"),
    (date(2026, 12, 25), "Christmas Day"),
]

# Second Thursday of each month at 6:30pm, a typical posted board schedule.
# Content mirrors the section structure of their published minutes (roll
# call, public participation, finance report, director's report, motions,
# adjournment) but with neutral demo business only -- no litigation,
# personnel, or named public commenters from the real documents.
BOARD_MEETING_DATES_2026 = [
    date(2026, 1, 8), date(2026, 2, 12), date(2026, 3, 12), date(2026, 4, 9),
    date(2026, 5, 14), date(2026, 6, 11), date(2026, 7, 9), date(2026, 8, 13),
    date(2026, 9, 10), date(2026, 10, 8), date(2026, 11, 12), date(2026, 12, 10),
]

_LIBRARY_TZ = ZoneInfo("America/New_York")

# (received, bill_list, director_highlight) per completed 2026 meeting, in
# meeting order. Figures are demo-scale placeholders, not their real books.
_MINUTES_FLAVOR = [
    ("$62,000", "$13,200", "Winter reading challenge signups doubled over last year; "
     "the Financial Literacy Series returns in February."),
    ("$64,500", "$12,800", "Healthcare enrollment assistance sessions served 41 residents; "
     "children's room attendance up 12% this quarter."),
    ("$61,750", "$14,100", "Roof repair estimates under review; Family Movie Night "
     "moved to the main hall to fit demand."),
    ("$66,000", "$13,600", "Zumba and mindful yoga programs at capacity; summer "
     "reading planning underway with the local public schools."),
    ("$63,200", "$12,400", "Juneteenth celebration planning finalized; new large-print "
     "collection shelved in the reading room."),
]


def _minutes_sections(
    meeting_dt: datetime, flavor: tuple[str, str, str], library_name: str
) -> list[dict]:
    received, bills, highlight = flavor
    label = meeting_dt.strftime("%B %d, %Y")
    return [
        {"order": 1, "title": "Call to Order",
         "content": f"The regular meeting of the Board of Trustees was called to order at "
                    f"6:30pm on {label} at the {library_name}."},
        {"order": 2, "title": "Roll Call",
         "content": "All five trustees present. Quorum met."},
        {"order": 3, "title": "Public Participation",
         "content": "Residents shared appreciation for children's programming and asked "
                    "about weekend hours. The board thanked attendees for their comments."},
        {"order": 4, "title": "Finance Report",
         "content": f"Received {received} this month. Bill list of {bills} reviewed and "
                    f"processed. Payroll current."},
        {"order": 5, "title": "Director's Report",
         "content": highlight},
        {"order": 6, "title": "Motions",
         "content": "Motion to process the bill list: moved, seconded, and approved 5-0. "
                    "Motion to approve the previous meeting's minutes: approved 5-0."},
        {"order": 7, "title": "Adjournment",
         "content": "Motion to adjourn moved and seconded; meeting adjourned at 8:00pm. "
                    "Next meeting is the second Thursday of next month at 6:30pm."},
    ]


async def _seed_hours(db: AsyncSession) -> tuple[int, int]:
    rows = {r.day_of_week: r for r in (await db.execute(select(LibraryHours))).scalars()}
    for dow, open_t, close_t, closed in WEEKLY_HOURS:
        row = rows.get(dow)
        if row is None:
            row = LibraryHours(day_of_week=dow)
            db.add(row)
        row.open_time = open_t
        row.close_time = close_t
        row.is_closed = closed
    existing_dates = {
        r.date for r in (await db.execute(select(LibraryHoursOverride))).scalars()
    }
    closures = 0
    for d, reason in HOLIDAY_CLOSURES_2026:
        if d not in existing_dates:
            db.add(LibraryHoursOverride(date=d, is_closed=True, reason=reason))
            closures += 1
    await db.flush()
    return len(WEEKLY_HOURS), closures


async def _seed_board(db: AsyncSession, branding: dict) -> tuple[int, int]:
    existing = (await db.execute(select(func.count()).select_from(BoardMember))).scalar_one()
    if existing:
        return 0, 0

    roster = branding["board_roster"]
    library_name = branding["library_name"]
    for i, (name, position) in enumerate(roster):
        db.add(BoardMember(
            full_name=name,
            position=position,
            # Noon UTC so the month doesn't shift back a day (and a month)
            # when the frontend renders it in a western-hemisphere timezone.
            term_start_date=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            is_current=True,
            is_chair=(i == 0),
        ))

    present = [{"name": name, "title": position} for name, position in roster]
    meetings = 0
    completed = 0
    for d in BOARD_MEETING_DATES_2026:
        start = datetime(d.year, d.month, d.day, 18, 30, tzinfo=_LIBRARY_TZ)
        meeting = BoardMeeting(
            meeting_type="regular",
            title=f"Board of Trustees Meeting: {d.strftime('%B %Y')}",
            description=f"Regular monthly meeting of the {library_name} Board of "
                        "Trustees. All meetings are open to the public.",
            scheduled_date=start,
            start_time=start,
            end_time=start + timedelta(minutes=90),
            location=f"{library_name}, {branding['address_line1']}",
            notice_status="posted",
            notice_posted_at=start - timedelta(days=14),
            public_comment_enabled=True,
            accessibility_info="The meeting room is wheelchair accessible.",
        )
        is_completed = d < SEED_DATE.date() and completed < len(_MINUTES_FLAVOR)
        if is_completed:
            meeting.quorum_met = True
            meeting.minutes_approved = True
            meeting.minutes_approved_date = start + timedelta(days=28)
            db.add(meeting)
            await db.flush()
            db.add(BoardMinutes(
                meeting_id=meeting.id,
                # Drafted the week after the meeting, so the minutes timeline
                # groups under the meeting's month instead of the seed date.
                created_at=start + timedelta(days=7),
                status="approved",
                sections=_minutes_sections(start, _MINUTES_FLAVOR[completed], library_name),
                meeting_called_to_order_at=start,
                meeting_adjourned_at=start + timedelta(minutes=90),
                members_present=present,
                quorum_met=True,
                quorum_count="5 of 5 members present",
                approved=True,
                approved_at=start + timedelta(days=28),
                approval_vote_result="Approved 5-0",
            ))
            completed += 1
        else:
            db.add(meeting)
        meetings += 1
    await db.flush()
    return len(roster), meetings


async def _get_or_create_library(db: AsyncSession, branding: dict) -> tuple[LibrarySystem, Branch]:
    result = await db.execute(select(LibrarySystem).limit(1))
    lib_sys = result.scalar_one_or_none()
    if lib_sys is None:
        lib_sys = LibrarySystem(
            code=branding["code"],
            name=branding["library_name"],
            email=branding["email"],
            phone=branding["phone"],
            address_line1=branding["address_line1"],
            city=branding["city"],
            state=branding["state"],
            zip_code=branding["zip_code"],
            is_active=True,
        )
        db.add(lib_sys)
        await db.flush()
        db.add(SystemSettings(library_system_id=lib_sys.id, setup_complete=False))

    result = await db.execute(
        select(Branch).where(Branch.library_system_id == lib_sys.id).limit(1)
    )
    branch = result.scalar_one_or_none()
    if branch is None:
        branch = Branch(
            library_system_id=lib_sys.id,
            code="MAIN",
            name=branding["library_name"],
            short_name=branding["code"],
            branch_type=BranchType.MAIN,
            status=BranchStatus.ACTIVE,
            phone=branding["phone"],
            email=branding["email"],
            address_line1=branding["address_line1"],
            city=branding["city"],
            state=branding["state"],
            zip_code=branding["zip_code"],
        )
        db.add(branch)
        await db.flush()
    return lib_sys, branch


async def _seed_branding(db: AsyncSession, branding: dict) -> None:
    result = await db.execute(select(LibraryBranding).where(LibraryBranding.id == 1))
    row = result.scalar_one_or_none()
    if row is not None:
        # A real library already branded this install (setup wizard / admin
        # PUT /branding). Loading demo data must not clobber their identity
        # with the demo profile's.
        return
    row = LibraryBranding(id=1)
    db.add(row)
    row.library_name = branding["library_name"]
    row.library_short_name = branding["code"]
    row.domain = branding.get("domain", "")
    row.contact_email = branding["email"]
    row.phone = branding["phone"]
    row.address_line1 = branding["address_line1"]
    row.primary_color = branding["primary_color"]
    row.accent_color = branding["accent_color"]
    row.logo_url = branding["logo_url"]
    row.hero_image_url = branding["hero_image_url"]
    row.display_font = branding["display_font"]
    row.body_font = branding["body_font"]
    row.secondary_color = branding["secondary_color"]
    row.surface_color = branding["surface_color"]
    row.ink_color = branding["ink_color"]
    row.nav_style = branding["nav_style"]
    row.card_prefix = branding["code"]
    row.hero_title = branding["hero_title"]
    row.hero_subtitle = branding["hero_subtitle"]
    row.tagline = branding["tagline"]
    row.about_story = branding.get("about_story")


async def _already_seeded(db: AsyncSession) -> bool:
    count = (await db.execute(select(func.count()).select_from(CatalogItem))).scalar_one()
    return count >= _SEEDED_THRESHOLD


def _isbn_for(work_id: int) -> str:
    # Deterministic 13-digit ISBN-shaped string, unique per work (all copies
    # of a work share the same ISBN, as in a real catalog).
    return f"978{(1000000 + work_id * 97) % 10000000:07d}"


async def _seed_catalog(db: AsyncSession, branch: Branch, code: str) -> list[CatalogItem]:
    works = json.loads(FIXTURE_PATH.read_text())
    items: list[CatalogItem] = []
    barcode_n = 0
    for work in works:
        item_type = _ITEM_TYPE_MAP[work["item_type"]]
        audience = _AUDIENCE_MAP[work["audience"]]
        dewey = work["dewey_decimal"]
        call_prefix = dewey or ("FIC" if item_type == ItemType.book else work["item_type"].upper())
        author_initials = "".join(w[0] for w in work["author"].split() if w[0].isalpha())[:3].upper() or "XXX"
        isbn = _isbn_for(work["work_id"])
        for copy_n in range(work["copies"]):
            barcode_n += 1
            item = CatalogItem(
                title=work["title"],
                author=work["author"],
                item_type=item_type,
                audience=audience,
                publisher=work["publisher"],
                publication_year=work["publication_year"],
                subjects=work["subjects"],
                dewey_decimal=dewey,
                call_number=f"{call_prefix} {author_initials}",
                isbn=isbn if item_type == ItemType.book else None,
                cataloging_status=CatalogingStatus.CATALOGED,
                cataloged_at=SEED_DATE,
                location=work["category"].replace("_", " ").title(),
                barcode=f"{code}{barcode_n:07d}",
                is_large_print=(item_type == ItemType.book and copy_n % 5 == 4),
                binding=(BookBinding.hardback if copy_n % 2 == 0 else BookBinding.paperback)
                if item_type == ItemType.book
                else None,
                total_checkouts=(work["work_id"] * 3 + copy_n) % 40,
                status=ItemStatus.available,
                cover_url=work.get("cover_url"),
            )
            if item_type == ItemType.dvd:
                item.director = work["author"]
                item.studio = work["publisher"]
            elif item_type == ItemType.cd:
                item.artist = work["author"]
            elif item_type == ItemType.game:
                item.platform = "Nintendo Switch"
            db.add(item)
            items.append(item)
    await db.flush()
    return items


async def _seed_patrons(db: AsyncSession, lib_sys: LibrarySystem, code: str) -> list[User]:
    patrons: list[User] = []
    count = 60
    for i in range(count):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last = LAST_NAMES[(i * 13 + 7) % len(LAST_NAMES)]
        age = 8 + (i * 37) % 68  # deterministic spread, 8..75
        dob = (SEED_DATE - timedelta(days=age * 365)).date()
        role = UserRole.CHILD if age < 13 else UserRole.PATRON
        email = f"{first.lower()}.{last.lower()}{i}@example.org"
        user = User(
            first_name=first,
            last_name=last,
            email=email,
            password_hash=_DEMO_ROLE_HASHES[role],
            role=role,
            is_active=True,
            email_verified=True,
            patron_status=PatronStatus.ACTIVE,
            library_card=f"{code}{200000 + i}",
            home_library_system_id=lib_sys.id,
            date_of_birth=dob,
            card_type="full",
        )
        db.add(user)
        patrons.append(user)
    await db.flush()
    return patrons


async def _seed_staff(
    db: AsyncSession, lib_sys: LibrarySystem, email_domain: str
) -> list[User]:
    staff: list[User] = []
    for first, last, staff_role, role in STAFF:
        if role == UserRole.SUPER_ADMIN:
            # Secure by default: no full-access demo login unless the operator
            # sets a private password. A super_admin with the repo-known demo
            # password would be a takeover on any internet-facing demo.
            if not _DEMO_SUPERADMIN_PASSWORD:
                continue
            password_hash = hash_password(_DEMO_SUPERADMIN_PASSWORD)
        else:
            password_hash = _DEMO_ROLE_HASHES[role]
        email = f"{first.lower()}.{last.lower()}@{email_domain}"
        user = User(
            first_name=first,
            last_name=last,
            email=email,
            password_hash=password_hash,
            role=role,
            staff_role=staff_role,
            is_active=True,
            email_verified=True,
            patron_status=PatronStatus.ACTIVE,
            home_library_system_id=lib_sys.id,
        )
        db.add(user)
        staff.append(user)
    await db.flush()
    return staff


async def _seed_events(db: AsyncSession, branch: Branch) -> list[Event]:
    events: list[Event] = []
    for i, (title, category, audience, day_offset, hour) in enumerate(EVENT_TEMPLATES):
        start = (SEED_DATE + timedelta(days=day_offset)).replace(hour=hour, minute=0)
        end = start + timedelta(hours=1)
        ev = Event(
            title=title,
            description=f"{title} at {branch.name}.",
            start_time=start,
            end_time=end,
            location=branch.name,
            audience=audience,
            category=category,
            branch_id=branch.id,
            is_published=True,
            max_attendees=20 + (i % 5) * 10,
            registration_required=(i % 3 == 0),
            wheelchair_accessible=True,
            asl_provided=(i % 5 == 0),
            captioning_provided=(i % 6 == 0),
            sensory_friendly=(i % 7 == 0),
        )
        db.add(ev)
        events.append(ev)
    await db.flush()
    return events


async def _seed_circulation(
    db: AsyncSession, items: list[CatalogItem], patrons: list[User], branch: Branch
) -> tuple[int, int]:
    checkouts = 0
    holds = 0
    # Active circulation is dated relative to the actual seed run, NOT the fixed
    # historical SEED_DATE: otherwise every install after SEED_DATE seeds loans
    # already past due, the nightly overdue job flips them, and the demo patron
    # gets auto-suspended before anyone can try the browse -> checkout flow.
    now = datetime.now(timezone.utc)
    for idx, item in enumerate(items):
        if idx % 6 == 0:
            patron = patrons[idx % len(patrons)]
            # checked out 1-18 days ago, 21-day loan -> due 3-20 days out (never overdue)
            checked_out_at = now - timedelta(days=(idx % 18) + 1)
            due_date = checked_out_at + timedelta(days=21)
            db.add(
                Checkout(
                    user_id=patron.id,
                    item_id=item.id,
                    status=CheckoutStatus.active,
                    checked_out_at=checked_out_at,
                    due_date=due_date,
                )
            )
            item.status = ItemStatus.checked_out
            checkouts += 1
        elif idx % 37 == 0:
            patron = patrons[(idx + 5) % len(patrons)]
            hold_status = HoldStatus.ready if idx % 74 == 0 else HoldStatus.pending
            hold = Hold(
                user_id=patron.id,
                item_id=item.id,
                status=hold_status,
                position=1,
                pickup_location_id=branch.id,
            )
            if hold_status == HoldStatus.ready:
                # Ready holds MUST carry notified_at + expires_at, or the expiry
                # sweep never touches them (is_hold_expired returns False when
                # both are null) and the copy stays locked to one patron forever.
                hold.notified_at = now
                hold.expires_at = now + timedelta(days=7)
            db.add(hold)
            item.status = ItemStatus.on_hold
            holds += 1
    await db.flush()
    return checkouts, holds


# Written staff reviews (shown publicly on the item page). (title_substr,
# rating, review_title, body) -- matched to a catalog work by title substring.
STAFF_REVIEWS = [
    ("Dune", 5, "A towering classic",
     "Herbert built a whole world -- politics, ecology, religion -- and it still "
     "feels urgent. A staff favorite we hand to anyone who wants to get lost in a book."),
    ("Where the Crawdads Sing", 4, "Atmospheric and moving",
     "The marsh is practically a character. A tender coming-of-age wrapped in a mystery."),
    ("The Handmaid's Tale", 5, "As sharp as ever",
     "A book that rewards a second read. We keep multiple copies and they never sit still."),
    ("And Then There Were None", 5, "The blueprint for the genre",
     "Christie at her most ruthless. Perfect for a reader new to classic mysteries."),
    ("Braiding Sweetgrass", 5, "Generous and wise",
     "Part science, part memoir, part love letter to the living world. We recommend it constantly."),
    ("The Very Hungry Caterpillar", 5, "A storytime staple",
     "Forty years on, it still lands with the toddler crowd. Bright, simple, joyful."),
]

# Patron rating spread per reviewed title (deterministic, mostly-positive with
# some threes) -- these feed the aggregate star rating, no written text.
_PATRON_RATINGS = [5, 4, 5, 3, 4, 5, 4, 3, 5, 4]

STAFF_PICK_LISTS = [
    ("Staff Favorites", "Books our librarians can't stop pressing into people's hands.",
     None, 0),
    ("Cozy Reads for Fall", "Warm, comforting stories for shorter days and longer evenings.",
     None, 1),
    ("Great Books for Kids", "Storytime hits and first chapter books, chosen by our youth desk.",
     "children", 2),
]
STAFF_PICK_NOTES = [
    "A patron favorite all year.", "We can't keep this one on the shelf.",
    "Great for a book club.", "Ask us about the sequel.", "A quiet stunner.",
    "Perfect for a rainy afternoon.", "One of our desk's most-recommended.",
    "Stayed with us long after the last page.",
]

# (title, content, summary, category, priority, homepage_banner, day_offset)
ANNOUNCEMENTS = [
    ("Summer Reading is here",
     "Sign up at any desk or online. Read, log your books, and earn prizes all "
     "summer -- every age welcome, no library card required to start.",
     "Read, log, and win prizes all summer.", "programs",
     AnnouncementPriority.IMPORTANT, True, -20),
    ("New: free online tutoring",
     "Every card now unlocks live homework help and test prep from 2-10pm daily. "
     "Ask a librarian how to log in.",
     "Live homework help, free with your card.", "services",
     AnnouncementPriority.NORMAL, False, -12),
    ("Saturday hours are back",
     "Starting this month we're open 10am-2pm on Saturdays again. Come see us.",
     "Open Saturdays 10-2 again.", "general",
     AnnouncementPriority.NORMAL, False, -6),
]

# (title, slug, body, tldr, author_first_last_or_name, role, read_time, views, day_offset)
# {library_name}/{city} are filled from the active profile at seed time;
# featured images come from the profile's blog_images list (same order).
BLOG_POSTS = [
    ("Welcome to our new library website", "welcome-new-website",
     "We're thrilled to unveil the new {library_name} website. It's faster, "
     "easier to search, and works beautifully on your phone.\n\nBrowse the catalog, "
     "sign up for programs, and see what's new -- all in one place. Have feedback? "
     "Tell us at the front desk. This is your library, and your website.",
     "A faster, friendlier home for everything the library offers.",
     "{library_name}", "Staff", 4, 142, -10),
    ("Five great reads for a cozy weekend", "five-cozy-reads",
     "The evenings are getting cooler, which means it's the perfect time to curl up "
     "with a good book.\n\nOur staff pulled together a handful of favorites -- from a "
     "quiet family drama to a page-turning mystery. Stop by the Staff Picks shelf near "
     "the entrance, or ask any of us for a recommendation. We love talking books.",
     "Staff-picked comfort reads for the season.",
     "Grace Ibeh", "Youth Services", 3, 89, -6),
    ("What's happening this summer at {city}", "summer-programs-roundup",
     "From bilingual storytimes to job-search help, this summer is packed.\n\n"
     "Highlights include our ESL Conversation Circle on Tuesdays, the Local Voices "
     "author series, and a brand-new Maker Monday for teens. Registration is open now "
     "for programs that fill up fast. See the full calendar on our Events page -- we "
     "hope to see you here.",
     "Storytimes, author talks, ESL, and maker programs all summer.",
     "Naomi Fischer", "Programs", 3, 64, -3),
]


def _distinct_ids_by_title(items, *, where=None, limit=12):
    """First N item ids with distinct titles, most-circulated first. Deterministic."""
    pool = [it for it in items if where is None or where(it)]
    pool.sort(key=lambda it: (-(it.total_checkouts or 0), it.title, it.id))
    seen, out = set(), []
    for it in pool:
        key = (it.title or "").strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(it.id)
        if len(out) >= limit:
            break
    return out


def _subj(sub):
    s = sub.lower()
    return lambda it: s in (it.subjects or "").lower()


async def _seed_home_shelves(db: AsyncSession, items: list[CatalogItem]) -> int:
    # Distinct-title curated shelves: the seed catalog carries ~6 copies per
    # title, and shelf resolvers list per-copy, so a raw new_arrivals/subject
    # shelf would repeat the same title. manual_list of distinct-title ids keeps
    # every slot unique. Staff Picks resolves live from the seeded lists.
    shelves = [
        ("popular-reads", "Popular Reads", "A sampler from across the collection",
         HomeShelfQueryKind.manual_list, _distinct_ids_by_title(items), 0, "/catalog"),
        ("staff-picks", "Staff Picks", "What our librarians are loving right now",
         HomeShelfQueryKind.staff_picks, None, 1, "/picks"),
        ("mysteries", "Mysteries & Thrillers", "Whodunits, cozies, and page-turners",
         HomeShelfQueryKind.manual_list,
         _distinct_ids_by_title(items, where=_subj("Mystery")), 2, "/catalog?q=Mystery"),
        ("young-readers", "For Young Readers", "Picture books and chapter books for kids",
         HomeShelfQueryKind.manual_list,
         _distinct_ids_by_title(items, where=_subj("Children")), 3, "/catalog?q=Children"),
        ("science", "Science & Discovery", "How the world works",
         HomeShelfQueryKind.manual_list,
         _distinct_ids_by_title(items, where=_subj("Science")), 4, "/catalog?q=Science"),
    ]
    for slug, heading, desc, kind, ids, order, href in shelves:
        db.add(HomeShelf(
            slug=slug, heading=heading, description=desc, query_kind=kind,
            query_params={"item_ids": ids} if ids is not None else {},
            sort_order=order, is_active=True, max_items=12, view_all_href=href,
        ))
    await db.flush()
    return len(shelves)


async def _seed_reviews(
    db: AsyncSession, items: list[CatalogItem], patrons: list[User], staff: list[User]
) -> int:
    by_title: dict[str, CatalogItem] = {}
    for it in items:  # first copy per title
        by_title.setdefault((it.title or "").strip().lower(), it)

    count = 0
    # Patron ratings (no text) across the most-circulated distinct titles -- these
    # drive the star aggregate shown on each item page.
    rated_ids = _distinct_ids_by_title(items, limit=18)
    for i, item_id in enumerate(rated_ids):
        for j in range(3):  # three ratings per title
            patron = patrons[(i * 3 + j) % len(patrons)]
            db.add(Review(
                user_id=patron.id, catalog_item_id=item_id,
                rating=_PATRON_RATINGS[(i + j) % len(_PATRON_RATINGS)],
                is_staff_review=False, is_published=True,
            ))
            count += 1
    # A handful of written staff reviews (title + body display publicly).
    for k, (substr, rating, rtitle, body) in enumerate(STAFF_REVIEWS):
        item = by_title.get(substr.strip().lower())
        if item is None:
            continue
        db.add(Review(
            user_id=staff[k % len(staff)].id, catalog_item_id=item.id,
            rating=rating, title=rtitle, body=body,
            is_staff_review=True, is_published=True,
        ))
        count += 1
    await db.flush()
    return count


async def _seed_staff_picks(
    db: AsyncSession, items: list[CatalogItem], staff: list[User]
) -> int:
    count = 0
    for title, desc, kids, order in STAFF_PICK_LISTS:
        creator = staff[order % len(staff)]
        lst = StaffPicksList(
            title=title, description=desc, created_by_id=creator.id,
            is_active=True, display_order=order,
        )
        db.add(lst)
        await db.flush()  # need lst.id
        where = _subj("Children") if kids else _subj("Fiction")
        for pos, item_id in enumerate(_distinct_ids_by_title(items, where=where, limit=9)):
            db.add(StaffPicksItem(
                list_id=lst.id, catalog_item_id=item_id,
                staff_notes=STAFF_PICK_NOTES[(order + pos) % len(STAFF_PICK_NOTES)],
                display_order=pos, added_by_id=creator.id,
            ))
            count += 1
    await db.flush()
    return count


async def _seed_event_registrations(db: AsyncSession, events: list[Event]) -> tuple[int, int]:
    regs = 0
    for i, ev in enumerate(events):
        cap = ev.max_attendees or 20
        n = min(cap * 6 // 10, 18)
        for j in range(n):
            first = FIRST_NAMES[(i * 3 + j) % len(FIRST_NAMES)]
            last = LAST_NAMES[(i * 7 + j) % len(LAST_NAMES)]
            db.add(EventRegistration(
                event_id=ev.id,
                patron_name=f"{first} {last}",
                patron_email=f"{first.lower()}.{last.lower()}.{i}{j}@example.org",
                registered_at=SEED_DATE - timedelta(days=(i % 10) + 1, hours=j),
                status=EventRegistrationStatus.CONFIRMED.value,
                accommodation_requested=False,
                photo_release_granted=True,
            ))
            regs += 1
    # Waitlists on a few community-favourite events (every 7th, offset).
    waits = 0
    for i, ev in enumerate(events):
        if i % 7 != 5:
            continue
        for j in range(4):
            first = FIRST_NAMES[(i * 5 + j) % len(FIRST_NAMES)]
            last = LAST_NAMES[(i * 11 + j) % len(LAST_NAMES)]
            db.add(EventWaitlistEntry(
                event_id=ev.id,
                email=f"{first.lower()}.{last.lower()}.wl{i}{j}@example.org",
                name=f"{first} {last}", registrant_count=1,
                status=WaitlistStatus.WAITING.value,
                created_at=SEED_DATE - timedelta(days=j + 1),
            ))
            waits += 1
    await db.flush()
    return regs, waits


async def _seed_announcements(db: AsyncSession, branding: dict) -> int:
    for title, content, summary, category, priority, banner, off in ANNOUNCEMENTS:
        db.add(Announcement(
            title=title, content=content, summary=summary, category=category,
            priority=priority, status=AnnouncementStatus.PUBLISHED,
            active=True, pinned=(off == -20), show_on_homepage=True,
            show_banner=banner, dismissible=True,
            published_at=SEED_DATE + timedelta(days=off),
            created_by_name=branding["library_name"],
        ))
    await db.flush()
    return len(ANNOUNCEMENTS)


async def _seed_blog(db: AsyncSession, branding: dict) -> int:
    fills = {"library_name": branding["library_name"], "city": branding["city"]}
    images = branding["blog_images"]
    for i, (title, slug, body, tldr, author, role, rt, views, off) in enumerate(BLOG_POSTS):
        db.add(BlogPost(
            title=title.format(**fills), slug=slug,
            body=body.format(**fills), tldr=tldr.format(**fills),
            author_name=author.format(**fills), author_role=role,
            status=BlogPostStatus.published,
            published_at=SEED_DATE + timedelta(days=off),
            read_time_minutes=rt, view_count=views,
            featured_image=images[i % len(images)],
        ))
    await db.flush()
    return len(BLOG_POSTS)


async def seed_demo(db: AsyncSession, *, branding: dict | None = None) -> dict:
    """Populate a fresh install with a realistic demo dataset.

    The seed identity defaults to the FICTIONAL Little Schitt Creek profile;
    set DEMO_PROFILE=orange (or pass ``branding=ORANGE``) for the Orange
    demo instance. Idempotent-ish: see module docstring and ``_already_seeded``.
    """
    if branding is None:
        branding = _default_profile()

    if await _already_seeded(db):
        return {"skipped": True, "reason": "catalog already seeded"}

    lib_sys, branch = await _get_or_create_library(db, branding)
    await _seed_branding(db, branding)
    items = await _seed_catalog(db, branch, branding["code"])
    patrons = await _seed_patrons(db, lib_sys, branding["code"])
    staff = await _seed_staff(db, lib_sys, branding["staff_email_domain"])
    events = await _seed_events(db, branch)
    checkouts, holds = await _seed_circulation(db, items, patrons, branch)

    # "Lived-in" community signals -- run after catalog/patrons/staff/events so
    # foreign keys resolve. These are what make the demo read as a working
    # library rather than an empty shell.
    shelves = await _seed_home_shelves(db, items)
    reviews = await _seed_reviews(db, items, patrons, staff)
    staff_picks = await _seed_staff_picks(db, items, staff)
    registrations, waitlists = await _seed_event_registrations(db, events)
    announcements = await _seed_announcements(db, branding)
    blog_posts = await _seed_blog(db, branding)
    hours_days, holiday_closures = await _seed_hours(db)
    board_members, board_meetings = await _seed_board(db, branding)

    await db.commit()
    return {
        "skipped": False,
        "catalog_items": len(items),
        "patrons": len(patrons),
        "staff": len(staff),
        "events": len(events),
        "checkouts": checkouts,
        "holds": holds,
        "home_shelves": shelves,
        "reviews": reviews,
        "staff_picks": staff_picks,
        "event_registrations": registrations,
        "waitlists": waitlists,
        "announcements": announcements,
        "blog_posts": blog_posts,
        "hours_days": hours_days,
        "holiday_closures": holiday_closures,
        "board_members": board_members,
        "board_meetings": board_meetings,
    }
