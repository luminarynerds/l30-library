# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import contextlib
import random
from datetime import datetime, timedelta, timezone, date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


def _past_date(days_ago: int) -> date:
    return (datetime.now(utc) - timedelta(days=days_ago)).date()


async def seed_simple_domains(session: AsyncSession) -> bool:

    # Grab reusable IDs
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]

    items_r = await session.execute(text("SELECT id FROM catalog_items"))
    catalog_ids = [r[0] for r in items_r.fetchall()]

    vol_r = await session.execute(text("SELECT id FROM volunteers"))
    volunteer_ids = [r[0] for r in vol_r.fetchall()]

    now = datetime.now(utc)

    # ════════════════════════════════════════════════════════════════

    # ════════════════════════════════════════════════════════════════

    # ════════════════════════════════════════════════════════════════
    # 3. REVIEWS (patron book reviews)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM reviews"))
    if r.scalar() == 0 and catalog_ids:
        print("  Seeding reviews...")
        review_data = [
            (5, "Absolutely loved it", "Could not put this down. Read it in one sitting and immediately recommended it to everyone in my book club."),
            (4, "Really enjoyed", "Great story with compelling characters. The ending felt a bit rushed but overall a wonderful read."),
            (5, "A masterpiece", "This book changed how I think about the world. Beautifully written and deeply moving."),
            (3, "Decent read", "Good premise but the execution was uneven. Some chapters were brilliant, others dragged."),
            (4, "Pleasantly surprised", "Picked this up on a whim from the new arrivals shelf and was hooked from page one."),
            (2, "Not for me", "I can see why others enjoy this but the writing style just didn't click. DNF at page 150."),
            (5, "Staff pick for a reason!", "Saw this on the staff picks display and gave it a try. Now it's my favorite book of the year."),
            (4, "Great audiobook too", "Read the physical copy first, then listened to the audiobook. The narrator brings it to life."),
            (5, "Perfect for our book club", "Generated two hours of discussion. Everyone had strong opinions. Best pick we've had all year."),
            (3, "Interesting concept", "The idea was fascinating but I wished the author had explored the themes more deeply."),
            (4, "Heartwarming", "A gentle, quiet book that snuck up on me emotionally. Shed a few tears at the end."),
            (5, "Re-read material", "This is my third time reading this and I notice something new every time."),
            (1, "Disappointing", "The reviews were so positive but I found the characters shallow and the plot predictable."),
            (4, "My kid loved it", "Read this with my 10-year-old and we both got invested. Great family read."),
            (5, "Beautiful writing", "The prose alone is worth the read. Every sentence is crafted with care."),
            (3, "Mixed feelings", "Started strong but lost me in the middle third. Ending redeemed it somewhat."),
            (4, "Page-turner", "Stayed up way too late finishing this. My coworkers at the library noticed my tired eyes."),
            (5, "Life-changing", "I've bought copies for three friends. This book articulates feelings I never could."),
            (4, "Solid mystery", "Kept me guessing until the very end. Fair clues, satisfying reveal."),
            (2, "Overhyped", "Maybe I went in with too-high expectations. Felt formulaic after the first act."),
        ]
        used_combos = set()
        for rating, title, body in review_data:
            # Ensure unique user+item combos
            for _ in range(10):
                uid = random.choice(all_ids)
                cid = random.choice(catalog_ids)
                if (uid, cid) not in used_combos:
                    used_combos.add((uid, cid))
                    break
            is_staff = uid in staff_ids
            await session.execute(text("""
                INSERT INTO reviews (user_id, catalog_item_id, rating, title, body, is_staff_review, is_published, created_at, updated_at)
                VALUES (:uid, :cid, :rating, :title, :body, :is_staff, true, :created, :created)
            """), {
                "uid": uid, "cid": cid, "rating": rating, "title": title,
                "body": body, "is_staff": is_staff,
                "created": _past(random.randint(1, 365)),
            })
        print(f"    Created {len(review_data)} reviews")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 4. ACHIEVEMENTS (badge definitions)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM achievements"))
    if r.scalar() == 0:
        print("  Seeding achievements...")
        achievements = [
            ("first-checkout", "First Checkout", "Checked out your very first item", "book-open", 10, False, "reading"),
            ("bookworm-10", "Bookworm", "Read 10 books", "book", 50, False, "reading"),
            ("bibliophile-50", "Bibliophile", "Read 50 books", "books", 200, False, "reading"),
            ("centurion", "Centurion Reader", "Read 100 books", "trophy", 500, False, "reading"),
            ("genre-explorer", "Genre Explorer", "Read from 5 different genres", "compass", 75, False, "reading"),
            ("early-bird", "Early Bird", "Visited the library within the first hour of opening", "sunrise", 15, False, "engagement"),
            ("event-enthusiast", "Event Enthusiast", "Attended 10 library events", "calendar", 100, False, "engagement"),
            ("summer-reader", "Summer Reader", "Completed the Summer Reading Challenge", "sun", 150, False, "seasonal"),
            ("winter-reader", "Winter Reader", "Completed the Winter Reading Challenge", "snowflake", 150, False, "seasonal"),
            ("review-writer", "Critic's Choice", "Wrote 5 book reviews", "star", 75, False, "community"),
            ("book-club-regular", "Book Club Regular", "Attended 6 book club meetings", "users", 100, False, "community"),
            ("digital-native", "Digital Native", "Borrowed your first ebook", "tablet", 25, False, "digital"),
            ("streak-7", "Week Warrior", "Logged reading 7 days in a row", "fire", 50, False, "streaks"),
            ("streak-30", "Monthly Marvel", "Logged reading 30 days in a row", "flame", 200, False, "streaks"),
            ("night-owl", "Night Owl", "Logged reading after 11 PM", "moon", 10, True, "fun"),
            ("speed-reader", "Speed Reader", "Finished a book within 24 hours of checkout", "zap", 30, True, "fun"),
            ("overdue-zero", "Perfect Record", "Returned 50 items with zero overdue", "check-circle", 100, False, "responsibility"),
            ("volunteer-star", "Volunteer Star", "Logged 20 volunteer hours", "heart", 150, False, "community"),
            ("makerspace-maker", "Maker", "Completed your first makerspace project", "tool", 50, False, "makerspace"),
            ("genealogy-detective", "Family Detective", "Used genealogy resources for the first time", "search", 25, False, "research"),
        ]
        for slug, name, desc, icon, xp, secret, category in achievements:
            await session.execute(text("""
                INSERT INTO achievements (slug, name, description, icon, xp_value, is_secret, category)
                VALUES (:slug, :name, :desc, :icon, :xp, :secret, :cat)
            """), {
                "slug": slug, "name": name, "desc": desc,
                "icon": icon, "xp": xp, "secret": secret, "cat": category,
            })
        print(f"    Created {len(achievements)} achievements")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 5. USER ACHIEVEMENTS (earned badges)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM user_achievements"))
    ach_r = await session.execute(text("SELECT id FROM achievements"))
    ach_ids = [r[0] for r in ach_r.fetchall()]
    if r.scalar() == 0 and ach_ids:
        print("  Seeding user_achievements...")
        count = 0
        used = set()
        for uid in random.sample(all_ids, min(len(all_ids), 40)):
            num_badges = random.randint(1, 6)
            for aid in random.sample(ach_ids, min(len(ach_ids), num_badges)):
                if (uid, aid) not in used:
                    used.add((uid, aid))
                    await session.execute(text("""
                        INSERT INTO user_achievements (user_id, achievement_id, earned_at)
                        VALUES (:uid, :aid, :earned)
                    """), {"uid": uid, "aid": aid, "earned": _past(random.randint(1, 300))})
                    count += 1
        print(f"    Created {count} user achievements")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 6. STAFF BOARD POSTS & REPLIES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM staff_board_posts"))
    if r.scalar() == 0:
        print("  Seeding staff_board_posts & replies...")
        posts = [
            ("Reminder: Summer Reading kickoff is June 1!", "Please have your program displays ready by May 28. Contact Maria if you need supplies or help with setup. Volunteer sign-up sheet is in the break room.", "memo", True),
            ("New self-checkout stations installed", "The two new self-checkout kiosks are now live at the main entrance. Quick reference guide is taped to each station. Please direct patrons there for holds pickup too.", "library_happenings", False),
            ("State Library Annual Report deadline", "Just a heads up — the state annual report is due August 15 this year (moved up two weeks). I'll need circulation stats from each branch by August 1.", "state_news", False),
            ("Lost and found: mystery lunch box", "There's a blue insulated lunch box in the break room fridge that's been there since Monday. If it's yours, please claim it before Friday or it's going in the trash.", "general", False),
            ("Tip: Handling difficult patron interactions", "Attended a great webinar on de-escalation techniques. Key takeaway: acknowledge the person's frustration before offering solutions. Notes are on the shared drive under Training > 2026.", "tips_tricks", False),
            ("ALA webinar series — free registration", "ALA is offering a free 4-part webinar series on community engagement starting next month. Highly recommend it. Link in the shared calendar.", "professional_dev", False),
            ("Book drop overflow protocol", "With the nice weather, returns are up 40%. If the main book drop is full, please check it every 2 hours instead of every 4. Overflow goes to the cart in the back workroom.", "memo", True),
            ("Welcome aboard, Priya!", "Please join me in welcoming Priya Sharma to the Youth Services team! She starts Monday and will be covering the children's desk Tu/Th/Sa. Stop by and say hi!", "library_happenings", False),
            ("HVAC update — main branch", "The HVAC repair is scheduled for this Saturday. Building will be closed for the work. Sunday hours are unaffected.", "memo", False),
            ("Favorite patron interaction this week?", "I had a patron come back to tell me the book I recommended changed her life. Made my whole week. Anyone else have a feel-good moment to share?", "general", False),
            ("New database: Consumer Reports online", "We now have access to Consumer Reports digital. Great for patrons doing product research. Access through the databases page — no login needed in-library.", "library_happenings", False),
            ("Conflict resolution training — sign up by Friday", "The county is offering free conflict resolution training next month. Two spots left. Talk to David if interested.", "professional_dev", False),
        ]
        post_ids = []
        for title, content, category, pinned in posts:
            r2 = await session.execute(text("""
                INSERT INTO staff_board_posts (title, content, category, pinned, archived, author_id, created_at, updated_at)
                VALUES (:title, :content, :cat, :pinned, false, :author, :created, :created)
                RETURNING id
            """), {
                "title": title, "content": content, "cat": category,
                "pinned": pinned, "author": random.choice(staff_ids),
                "created": _past(random.randint(1, 120)),
            })
            post_ids.append(r2.scalar())

        # Add replies
        replies = [
            "Great reminder, thanks!",
            "Thanks for sharing this!",
            "Good to know. I'll pass this along to my team.",
            "Can we discuss this at the next staff meeting?",
            "Love this — exactly what we needed.",
            "I had a similar experience last week!",
            "Added to my calendar. Thanks!",
            "Is there a sign-up sheet or should we just show up?",
            "This is wonderful news! Welcome to the team!",
            "+1, really useful information.",
            "Does this apply to the branch locations too?",
            "I'll take one of those training spots!",
        ]
        reply_count = 0
        for pid in post_ids:
            num_replies = random.randint(0, 4)
            for _ in range(num_replies):
                await session.execute(text("""
                    INSERT INTO staff_board_replies (content, post_id, author_id, created_at, updated_at)
                    VALUES (:content, :pid, :author, :created, :created)
                """), {
                    "content": random.choice(replies),
                    "pid": pid, "author": random.choice(staff_ids),
                    "created": _past(random.randint(0, 60)),
                })
                reply_count += 1
        print(f"    Created {len(posts)} posts, {reply_count} replies")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 7. READING GOALS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM reading_goals"))
    if r.scalar() == 0:
        print("  Seeding reading_goals...")
        count = 0
        used = set()
        for uid in random.sample(all_ids, min(len(all_ids), 50)):
            for year in [2025, 2026]:
                if (uid, year) not in used:
                    used.add((uid, year))
                    target = random.choice([12, 20, 24, 30, 36, 48, 52])
                    await session.execute(text("""
                        INSERT INTO reading_goals (user_id, year, target_books, created_at, updated_at)
                        VALUES (:uid, :year, :target, :created, :created)
                    """), {
                        "uid": uid, "year": year, "target": target,
                        "created": datetime(year, 1, random.randint(1, 15), tzinfo=utc),
                    })
                    count += 1
        print(f"    Created {count} reading goals")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 8. READING STATS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM reading_stats"))
    if r.scalar() == 0:
        print("  Seeding reading_stats...")
        count = 0
        for uid in random.sample(all_ids, min(len(all_ids), 45)):
            streak = random.randint(0, 30)
            longest = max(streak, random.randint(5, 60))
            total_min = random.randint(500, 15000)
            submissions = random.randint(10, 150)
            books = random.randint(5, 80)
            await session.execute(text("""
                INSERT INTO reading_stats (user_id, current_streak, longest_streak, last_log_date,
                    total_approved_minutes, total_submissions, unique_books, notes_written, xp, created_at, updated_at)
                VALUES (:uid, :streak, :longest, :last_log, :mins, :subs, :books, :notes, :xp, :created, :created)
            """), {
                "uid": uid, "streak": streak, "longest": longest,
                "last_log": _past_date(random.randint(0, 14)),
                "mins": total_min, "subs": submissions, "books": books,
                "notes": random.randint(0, submissions // 3),
                "xp": random.randint(100, 5000),
                "created": _past(random.randint(30, 400)),
            })
            count += 1
        print(f"    Created {count} reading stat records")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 9. TRAINING TYPES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM training_types"))
    if r.scalar() == 0:
        print("  Seeding training_types...")
        types = [
            ("Safety & Emergency Procedures", "Annual safety training covering fire evacuation, active threat response, medical emergencies, and AED usage.", ["staff", "admin", "director"], 2.0, 12),
            ("Customer Service Excellence", "Core customer service skills including communication, de-escalation, and accessibility awareness.", ["staff", "admin"], 1.5, 24),
            ("Circulation System Training", "ILS operations: check-in/out, holds, fines, patron records, and interlibrary loan processing.", ["staff"], 3.0, None),
            ("Reference Interview Techniques", "Conducting effective reference interviews and search strategies across print and digital resources.", ["staff"], 2.0, 24),
            ("Children's Services Fundamentals", "Age-appropriate programming, early literacy practices, and child safety protocols.", ["staff"], 2.5, 12),
            ("Digital Literacy Instruction", "Teaching patrons to use computers, internet, email, and common software applications.", ["staff"], 2.0, 12),
            ("Collection Development & Weeding", "Selection criteria, weeding methodologies, and collection assessment techniques.", ["staff", "admin"], 1.5, 24),
            ("Privacy & Confidentiality", "Patron privacy rights, CIPA compliance, law enforcement request handling, and data protection.", ["staff", "admin", "director"], 1.0, 12),
            ("Diversity, Equity & Inclusion", "Cultural competency, inclusive services, and equitable access for all community members.", ["staff", "admin", "director"], 2.0, 12),
            ("New Employee Orientation", "Overview of library mission, policies, building layout, technology, and staff expectations.", ["staff"], 4.0, None),
            ("Makerspace Equipment Certification", "Safe operation of 3D printers, laser cutters, and other makerspace tools.", ["staff"], 3.0, 12),
            ("Supervisory Skills", "Managing staff, conducting evaluations, scheduling, and handling personnel issues.", ["admin", "director"], 3.0, 24),
        ]
        for name, desc, roles, hours, recurrence in types:
            roles_literal = "'{" + ",".join(roles) + "}'"
            await session.execute(text(f"""
                INSERT INTO training_types (name, description, required_for_roles, duration_hours, recurrence_months)
                VALUES (:name, :desc, {roles_literal}::varchar[], :hours, :recurrence)
            """), {
                "name": name, "desc": desc,
                "hours": hours, "recurrence": recurrence,
            })
        print(f"    Created {len(types)} training types")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 10. POLICIES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM policies"))
    if r.scalar() == 0:
        print("  Seeding policies...")
        policies = [
            ("Circulation Policy", "Governs lending, returns, renewals, fines, and patron responsibilities.", "circulation",
             "All registered patrons may borrow up to 25 items at a time. Loan periods vary by material type: books (21 days), DVDs (7 days), magazines (14 days). Items may be renewed twice unless on hold. Overdue fines are $0.25/day for standard items and $1.00/day for high-demand items. Lost items are billed at replacement cost plus a $5.00 processing fee.", "3.1", True, 2020),
            ("Internet Use Policy", "Acceptable use of library computers and WiFi.", "technology",
             "The library provides free internet access to support its educational mission. Users must not access illegal content, conduct commercial activities, or compromise network security. Filtering software is active on children's computers per CIPA requirements. Sessions are limited to 60 minutes when others are waiting. Staff may terminate a session for policy violations.", "2.4", True, 2026),
            ("Collection Development Policy", "Guides the selection, acquisition, and removal of library materials.", "collection",
             "The library selects materials to meet the informational, educational, cultural, and recreational needs of the community. Selection criteria include: community relevance, accuracy, literary merit, cost, and format availability. The library does not censor materials. Requests for reconsideration must be submitted in writing using the official form.", "4.0", True, 2024),
            ("Meeting Room Policy", "Rules for public use of library meeting spaces.", "facilities",
             "Meeting rooms are available free of charge for nonprofit community groups. Rooms may be reserved up to 30 days in advance. No admission may be charged. The library name may not be used to imply endorsement of any group's activities. Rooms must be left in the condition found. A $50 cleaning fee may be assessed for excessive mess.", "2.0", True, 2023),
            ("Privacy Policy", "Protects patron information and records.", "privacy",
             "The library protects the privacy of all patron records in accordance with state law. Circulation records, internet use logs, and reference transaction records are confidential. Information will only be released pursuant to a valid court order. Staff are trained annually on privacy obligations.", "3.0", True, 2024),
            ("Code of Conduct", "Behavioral expectations for library visitors.", "general",
             "The library welcomes all community members. To ensure a safe and comfortable environment: speak at a conversational volume, supervise children under 10, wear shoes and shirt, do not bring food into the stacks, silence cell phones in quiet areas. Disruptive behavior may result in a verbal warning, suspension of privileges, or trespass notice.", "2.2", True, 2025),
            ("Volunteer Policy", "Guidelines for library volunteer programs.", "human_resources",
             "Volunteers supplement but do not replace paid staff. All volunteers must complete an application, background check, and orientation. Minimum age for independent volunteers is 14. Volunteers may not handle patron records or financial transactions. Service hours are tracked and recognized annually.", "1.1", False, 2023),
            ("Gifts and Donations Policy", "Acceptance criteria for donated materials and funds.", "collection",
             "The library gratefully accepts donations of books and materials in good condition. Donated items become library property and may be added to the collection, sold, or recycled at the library's discretion. Tax receipts are available for monetary donations. The library cannot appraise donated materials.", "1.0", False, 2021),
        ]
        for title, desc, category, content, version, mandatory, year in policies:
            await session.execute(text("""
                INSERT INTO policies (title, description, category, content, version, is_mandatory, effective_date)
                VALUES (:title, :desc, :cat, :content, :ver, :mandatory, :eff)
            """), {
                "title": title, "desc": desc, "cat": category,
                "content": content, "ver": version, "mandatory": mandatory,
                "eff": date(year, 1, 1),
            })
        print(f"    Created {len(policies)} policies")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 11. PATRON TAG DEFINITIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM patron_tags_definitions"))
    if r.scalar() == 0:
        print("  Seeding patron_tags_definitions...")
        tags = [
            ("Homebound", "#8B5CF6", "Patron receives home delivery service", False),
            ("ESL Learner", "#3B82F6", "Enrolled in ESL/conversation circle programs", False),
            ("Book Club Member", "#10B981", "Active in one or more book clubs", False),
            ("Summer Reading", "#F59E0B", "Enrolled in current Summer Reading program", False),
            ("Volunteer", "#EC4899", "Active library volunteer", False),
            ("Teen Advisory", "#6366F1", "Member of the Teen Advisory Board", False),
            ("New Patron", "#06B6D4", "Registered within the last 90 days", False),
            ("Frequent Visitor", "#84CC16", "Visits 3+ times per week", False),
            ("Digital Only", "#64748B", "Primarily uses digital resources", True),
            ("Large Print", "#F97316", "Prefers large print materials", True),
            ("Genealogy Researcher", "#A855F7", "Active in genealogy/local history", True),
            ("Makerspace Certified", "#14B8A6", "Completed makerspace equipment training", False),
        ]
        for name, color, desc, is_custom in tags:
            await session.execute(text("""
                INSERT INTO patron_tags_definitions (name, color, description, is_custom, is_active, created_by_id)
                VALUES (:name, :color, :desc, :custom, true, :creator)
            """), {
                "name": name, "color": color, "desc": desc,
                "custom": is_custom, "creator": random.choice(staff_ids),
            })
        print(f"    Created {len(tags)} patron tag definitions")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 12. ROOM EQUIPMENT
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM room_equipment"))
    if r.scalar() == 0:
        print("  Seeding room_equipment...")
        equipment = [
            ("LCD Projector", "Epson PowerLite 1080p projector with HDMI input", "PROJ-001", 3, False, None),
            ("Portable Screen", "72-inch tripod projection screen", "SCRN-001", 2, False, None),
            ("Laptop", "Dell Latitude for presentations, pre-loaded with Office suite", "LAPT-001", 4, False, None),
            ("Whiteboard (rolling)", "4x6 ft dry erase whiteboard on wheels with markers and eraser", "WBRD-001", 3, False, None),
            ("Microphone System", "Wireless handheld + lapel microphone with portable speaker", "MIC-001", 2, True, "Check battery levels before event. Speaker pairs via Bluetooth."),
            ("Podium", "Adjustable-height wooden podium with reading light", "PODM-001", 1, False, None),
            ("Easel", "Adjustable aluminum easel for flip charts or poster boards", "EASL-001", 4, False, None),
            ("Extension Cord Pack", "Three 25-foot extension cords and one power strip", "ELEC-001", 5, False, None),
            ("Video Conferencing Kit", "Logitech Rally webcam + speakerphone for hybrid meetings", "VCONF-001", 2, True, "Connect via USB. Zoom/Teams pre-configured on the meeting room laptop."),
            ("Folding Tables", "6-foot folding tables for crafts or refreshments", "TABL-001", 8, True, "Tables stored in closet C. Staff must set up and break down."),
        ]
        for name, desc, code, qty, requires_staff, instructions in equipment:
            await session.execute(text("""
                INSERT INTO room_equipment (name, description, equipment_code, total_quantity, is_active, requires_staff_setup, setup_instructions)
                VALUES (:name, :desc, :code, :qty, true, :staff, :instructions)
            """), {
                "name": name, "desc": desc, "code": code, "qty": qty,
                "staff": requires_staff, "instructions": instructions,
            })
        print(f"    Created {len(equipment)} room equipment items")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 13. COMIC PUBLISHER IMPRINTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM comic_publisher_imprints"))
    if r.scalar() == 0:
        print("  Seeding comic_publisher_imprints...")
        imprints = [
            ("Vertigo", "DC Comics", "Mature readers imprint known for groundbreaking creator-owned series", "Adults", 1993),
            ("Image Comics", "Image Comics", "Independent publisher focused on creator-owned titles", "All Ages", 1992),
            ("Icon Comics", "Marvel", "Creator-owned imprint for established Marvel creators", "Adults", 2004),
            ("Dark Horse Comics", "Dark Horse", "Independent publisher known for licensed and original properties", "All Ages", 1986),
            ("IDW Publishing", "IDW", "Licensed comics and graphic novels", "All Ages", 1999),
            ("BOOM! Studios", "BOOM!", "Independent publisher with all-ages and mature titles", "All Ages", 2005),
            ("Oni Press", "Oni-Lion Forge", "Independent publisher of graphic novels and comics", "Young Adult", 1997),
            ("Aftershock Comics", "AfterShock", "Creator-driven comics for mature readers", "Adults", 2015),
            ("Fantagraphics", "Fantagraphics", "Publisher of literary and art comics", "Adults", 1976),
            ("Top Shelf Productions", "IDW", "Literary graphic novels and indie comics", "Adults", 1997),
        ]
        for name, parent, desc, audience, year in imprints:
            await session.execute(text("""
                INSERT INTO comic_publisher_imprints (imprint_name, parent_publisher, description, target_audience, founded_year)
                VALUES (:name, :parent, :desc, :audience, :year)
            """), {
                "name": name, "parent": parent, "desc": desc,
                "audience": audience, "year": year,
            })
        print(f"    Created {len(imprints)} comic imprints")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 14. CASH DRAWERS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM cash_drawers"))
    if r.scalar() == 0:
        print("  Seeding cash_drawers...")
        drawers = [
            ("Main Circulation Desk", 100.00, "shift_based", 5.00),
            ("Self-Checkout Area", 50.00, "day_based", 2.00),
            ("Children's Desk", 50.00, "day_based", 2.00),
            ("Makerspace Counter", 75.00, "shift_based", 3.00),
        ]
        for name, float_amt, mode, threshold in drawers:
            await session.execute(text("""
                INSERT INTO cash_drawers (name, default_float, mode, discrepancy_threshold, is_active, created_at, updated_at)
                VALUES (:name, :float, :mode, :threshold, true, :now, :now)
            """), {
                "name": name, "float": float_amt, "mode": mode,
                "threshold": threshold, "now": now,
            })
        print(f"    Created {len(drawers)} cash drawers")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 15. VOLUNTEER SKILLS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM volunteer_skills"))
    if r.scalar() == 0 and volunteer_ids:
        print("  Seeding volunteer_skills...")
        skills = [
            ("Shelving", "intermediate", 1.0, "Experienced with Dewey Decimal shelving"),
            ("Event Setup", "beginner", 0.5, "Can help with table/chair arrangement"),
            ("Computer Help", "advanced", 5.0, "Assists patrons with basic computer tasks"),
            ("Storytime Assistant", "intermediate", 2.0, "Helps with crafts and crowd management"),
            ("Book Repair", "advanced", 3.0, "Trained in basic book mending techniques"),
            ("Gardening", "intermediate", 4.0, "Maintains the seed library garden beds"),
            ("ESL Conversation", "advanced", 2.0, "Bilingual — leads conversation circles"),
            ("Teen Mentoring", "intermediate", 1.5, "Works with teen advisory board"),
            ("Photography", "beginner", 1.0, "Takes photos at library events"),
            ("Social Media", "intermediate", 3.0, "Helps manage library social accounts"),
        ]
        count = 0
        for vid in volunteer_ids:
            num_skills = random.randint(1, 4)
            for skill_name, level, years, desc in random.sample(skills, num_skills):
                await session.execute(text("""
                    INSERT INTO volunteer_skills (volunteer_id, skill_name, proficiency_level, years_of_experience, description, verified)
                    VALUES (:vid, :skill, :level, :years, :desc, :verified)
                """), {
                    "vid": vid, "skill": skill_name, "level": level,
                    "years": years, "desc": desc, "verified": random.choice([True, True, False]),
                })
                count += 1
        print(f"    Created {count} volunteer skills")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 16. KPI DASHBOARDS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM kpi_dashboards"))
    if r.scalar() == 0:
        print("  Seeding kpi_dashboards...")
        dashboards = [
            ("Director's Overview", "High-level library performance metrics", "director", True, '["admin","director"]'),
            ("Circulation Dashboard", "Daily circulation stats, hold fill rates, and overdue tracking", "staff", True, '["staff","admin","director"]'),
            ("Program Impact", "Event attendance, program registrations, and community reach", "staff", True, '["staff","admin","director"]'),
            ("Collection Health", "Turnover rates, age analysis, and format distribution", "staff", False, '["admin","director"]'),
            ("Digital Services", "Ebook usage, database access, and digital card adoption", "staff", False, '["admin","director"]'),
            ("Budget Tracker", "Revenue, expenditures, and budget utilization by category", "director", False, '["director"]'),
        ]
        for name, desc, audience, public, roles in dashboards:
            await session.execute(text("""
                INSERT INTO kpi_dashboards (name, description, audience, is_public, allowed_roles, created_by_id)
                VALUES (:name, :desc, :audience, :public, cast(:roles as jsonb), :creator)
            """), {
                "name": name, "desc": desc, "audience": audience,
                "public": public, "roles": roles,
                "creator": staff_ids[0],
            })
        print(f"    Created {len(dashboards)} KPI dashboards")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ════════════════════════════════════════════════════════════════
    seq_tables = [
        "reviews", "achievements",
        "user_achievements", "staff_board_posts", "staff_board_replies",
        "reading_goals", "reading_stats", "training_types", "policies",
        "patron_tags_definitions", "room_equipment", "comic_publisher_imprints",
        "cash_drawers", "volunteer_skills", "kpi_dashboards",
    ]
    for table in seq_tables:
        # Some tables don't have standard sequence naming; skip silently.
        with contextlib.suppress(SQLAlchemyError):
            await session.execute(text(
                f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
            ))

    await session.commit()
    print("  Simple domains seeding complete!")
    return True
