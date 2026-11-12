# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

utc = timezone.utc

def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("+00", "+00:00"))

def _d(s: str) -> date:
    return date.fromisoformat(s)


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


async def seed_batch_community(session: AsyncSession) -> bool:

    # Grab reusable IDs
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]

    if not patron_ids or not staff_ids:
        print("  Skipping community batch — no users found")
        return False


    # Helper: pick IDs from a query, return empty list if table missing
    async def _ids(query):
        try:
            r = await session.execute(text(query))
            return [row[0] for row in r.fetchall()]
        except SQLAlchemyError:
            return []

    catalog_item_ids = await _ids("SELECT id FROM catalog_items ORDER BY id LIMIT 20")
    branch_ids = await _ids("SELECT id FROM branches ORDER BY id")
    lesson_ids = await _ids("SELECT id FROM lessons ORDER BY id LIMIT 20")
    ebook_ids = await _ids("SELECT id FROM indie_ebooks ORDER BY id LIMIT 30")
    partner_ids = await _ids("SELECT id FROM outreach_partners ORDER BY id LIMIT 5")
    teen_vol_ids = await _ids("SELECT id FROM teen_volunteers ORDER BY id LIMIT 5")
    room_ids = await _ids("SELECT id FROM rooms ORDER BY id LIMIT 30")
    reservation_ids = await _ids("SELECT id FROM computer_reservations ORDER BY id LIMIT 30")
    session_ids_comp = await _ids("SELECT id FROM computer_sessions ORDER BY id LIMIT 10")
    found_item_ids = await _ids("SELECT id FROM found_items ORDER BY id LIMIT 10")
    lost_item_ids = await _ids("SELECT id FROM lost_item_records ORDER BY id LIMIT 10")
    welcome_packet_ids = await _ids("SELECT id FROM welcome_packets ORDER BY id LIMIT 10")

    # We need at least 6 staff for the seed data references
    # Map specific staff by position in the list
    s = staff_ids
    p = patron_ids

    # ════════════════════════════════════════════════════════════════
    # 1. READING ACTIVITIES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM reading_activities"))
    if r.scalar() == 0:
        print("  Seeding reading_activities...")
        ci_31 = 31 if 31 in catalog_item_ids else catalog_item_ids[0] if catalog_item_ids else None
        ci_2074 = 2074 if 2074 in catalog_item_ids else None
        ci_2075 = 2075 if 2075 in catalog_item_ids else None
        ci_2080 = 2080 if 2080 in catalog_item_ids else None
        ci_2084 = 2084 if 2084 in catalog_item_ids else None
        ci_2088 = 2088 if 2088 in catalog_item_ids else None

        activities = [
            (p[0] if len(p) > 0 else all_ids[0], ci_31, "pages_read", "Read chapters 1-3 of Yellowface",
             "{pages: 45, duration_minutes: 62}", datetime(2026, 4, 1, 18, 30, tzinfo=utc)),
            (p[1] if len(p) > 1 else all_ids[1], ci_31, "pages_read", "Finished Yellowface",
             "{pages: 120, duration_minutes: 180}", datetime(2026, 4, 2, 14, 0, tzinfo=utc)),
            (p[2] if len(p) > 2 else all_ids[2], ci_2074, "session", "Played Codenames at game night",
             "{duration_minutes: 45, players: 6}", datetime(2026, 3, 28, 22, 30, tzinfo=utc)),
            (p[3] if len(p) > 3 else all_ids[3], ci_2075, "session", "Played Azul during lunch break",
             "{duration_minutes: 30, players: 2}", datetime(2026, 3, 29, 16, 15, tzinfo=utc)),
            (p[4] if len(p) > 4 else all_ids[4], ci_31, "pages_read", "Started Yellowface for book club",
             "{pages: 25, duration_minutes: 35}", datetime(2026, 4, 3, 13, 0, tzinfo=utc)),
            (p[5] if len(p) > 5 else all_ids[5], ci_2080, "session", "Weekly Scrabble meetup",
             "{duration_minutes: 90, score: 312}", datetime(2026, 3, 30, 18, 0, tzinfo=utc)),
            (p[6] if len(p) > 6 else all_ids[6], None, "pages_read", "Read magazine in periodicals section",
             "{pages: 15, duration_minutes: 20}", datetime(2026, 4, 1, 15, 0, tzinfo=utc)),
            (p[7] if len(p) > 7 else all_ids[7], ci_2084, "session", "Clue with kids after school",
             "{duration_minutes: 40, players: 4}", datetime(2026, 4, 2, 19, 30, tzinfo=utc)),
            (p[8] if len(p) > 8 else all_ids[8], ci_31, "pages_read", "Listening to Yellowface audiobook",
             "{pages: 60, duration_minutes: 90, format: audiobook}", datetime(2026, 4, 3, 12, 0, tzinfo=utc)),
            (p[9] if len(p) > 9 else all_ids[9], ci_2088, "session", "Exploding Kittens at teen game night",
             "{duration_minutes: 25, players: 5}", datetime(2026, 4, 1, 21, 0, tzinfo=utc)),
        ]
        for uid, cid, atype, summary, meta, occurred in activities:
            await session.execute(text("""
                INSERT INTO reading_activities (user_id, catalog_item_id, activity_type, summary, metadata_json, occurred_at)
                VALUES (:uid, :cid, :atype, :summary, :meta, :occurred)
            """), {"uid": uid, "cid": cid, "atype": atype, "summary": summary, "meta": meta, "occurred": occurred})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 2. READING MILESTONES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM reading_milestones"))
    if r.scalar() == 0:
        print("  Seeding reading_milestones...")
        milestones = [
            (p[0] if len(p) > 0 else all_ids[0], "books_read", "books_read_5", "Bookworm Beginner",
             "Read 5 books this year", _past(45), False),
            (p[0] if len(p) > 0 else all_ids[0], "books_read", "books_read_10", "Avid Reader",
             "Read 10 books this year", _past(10), False),
            (p[1] if len(p) > 1 else all_ids[1], "books_read", "books_read_5", "Bookworm Beginner",
             "Read 5 books this year", _past(30), False),
            (p[2] if len(p) > 2 else all_ids[2], "books_read", "books_read_5", "Bookworm Beginner",
             "Read 5 books this year", _past(60), True),
            (p[2] if len(p) > 2 else all_ids[2], "streak", "weekly_streak_4", "Month-Long Streak",
             "Visited the library 4 weeks in a row", _past(20), False),
            (p[3] if len(p) > 3 else all_ids[3], "genre", "genre_diversity_3", "Genre Explorer",
             "Read from 3 different genres", _past(15), False),
            (p[4] if len(p) > 4 else all_ids[4], "books_read", "books_read_5", "Bookworm Beginner",
             "Read 5 books this year", _past(7), False),
            (p[5] if len(p) > 5 else all_ids[5], "summer_reading", "summer_2025_complete", "Summer Reader 2025",
             "Completed the Summer Reading Challenge", _past(91), False),
        ]
        for uid, mtype, mkey, title, desc, earned, dismissed in milestones:
            await session.execute(text("""
                INSERT INTO reading_milestones (user_id, milestone_type, milestone_key, title, description, earned_at, dismissed)
                VALUES (:uid, :mtype, :mkey, :title, :desc, :earned, :dismissed)
            """), {"uid": uid, "mtype": mtype, "mkey": mkey, "title": title, "desc": desc,
                   "earned": earned, "dismissed": dismissed})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 3. READING PROGRESS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM reading_progress"))
    if r.scalar() == 0 and catalog_item_ids:
        print("  Seeding reading_progress...")
        ci_31 = 31 if 31 in catalog_item_ids else catalog_item_ids[0]
        ci_2074 = 2074 if 2074 in catalog_item_ids else catalog_item_ids[1] if len(catalog_item_ids) > 1 else ci_31
        ci_2075 = 2075 if 2075 in catalog_item_ids else ci_31
        ci_2079 = 2079 if 2079 in catalog_item_ids else ci_31
        ci_2080 = 2080 if 2080 in catalog_item_ids else ci_31

        progress = [
            (p[0] if len(p) > 0 else all_ids[0], ci_31, 180, 320, 56,
             "Really picking up after chapter 12", _past(2)),
            (p[0] if len(p) > 0 else all_ids[0], ci_2080, None, None, 100,
             "Finished! Great family game night pick", _past(14)),
            (p[1] if len(p) > 1 else all_ids[1], ci_31, 320, 320, 100,
             "Incredible ending, did not see it coming", _past(5)),
            (p[2] if len(p) > 2 else all_ids[2], ci_2074, None, None, 75,
             "Played three rounds so far, love the deduction mechanic", _past(3)),
            (p[3] if len(p) > 3 else all_ids[3], ci_2075, None, None, 100,
             "Beautiful tile placement game", _past(10)),
            (p[4] if len(p) > 4 else all_ids[4], ci_31, 45, 320, 14,
             "Just started, interesting premise", _past(1)),
            (p[5] if len(p) > 5 else all_ids[5], ci_2079, None, None, 100,
             "So fun telling stories with the pictures", _past(20)),
        ]
        for uid, cid, cur_pg, tot_pg, pct, note, logged in progress:
            await session.execute(text("""
                INSERT INTO reading_progress (user_id, catalog_item_id, current_page, total_pages, percent, note, logged_at)
                VALUES (:uid, :cid, :cur_pg, :tot_pg, :pct, :note, :logged)
            """), {"uid": uid, "cid": cid, "cur_pg": cur_pg, "tot_pg": tot_pg,
                   "pct": pct, "note": note, "logged": logged})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 4. (removed) Patron reading lists + items
    # ════════════════════════════════════════════════════════════════
    # Previously seeded `patron_reading_lists` and `reading_list_items`
    # tables. Both were dropped by `schema_sync_003` in favor of the
    # current `reading_lists` / `list_items` schema (see
    # app/models/reading_list.py and app/api/v1/patron_reading_lists.py).
    # Seed data for the new schema should live in its own block when
    # someone needs it.

    # ════════════════════════════════════════════════════════════════
    # 5. QUIZ ATTEMPTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM quiz_attempts"))
    if r.scalar() == 0 and lesson_ids:
        print("  Seeding quiz_attempts...")
        # Use actual lesson IDs from the DB
        lid = lesson_ids
        attempts = [
            (p[0] if len(p) > 0 else all_ids[0], lid[0] if len(lid) > 0 else lid[0], 90, True,
             '[{"answer": "a", "correct": true, "question_id": 1}, {"answer": "b", "correct": true, "question_id": 2}]',
             _dt("2026-03-25 14:00:00+00"), _dt("2026-03-25 14:15:00+00")),
            (p[1] if len(p) > 1 else all_ids[1], lid[0] if len(lid) > 0 else lid[0], 80, True,
             '[{"answer": "a", "correct": true, "question_id": 1}, {"answer": "c", "correct": false, "question_id": 2}]',
             _dt("2026-03-26 18:00:00+00"), _dt("2026-03-26 18:12:00+00")),
            (p[2] if len(p) > 2 else all_ids[2], lid[1] if len(lid) > 1 else lid[0], 70, True,
             '[{"answer": "b", "correct": true, "question_id": 1}]',
             _dt("2026-03-27 13:30:00+00"), _dt("2026-03-27 13:45:00+00")),
            (p[3] if len(p) > 3 else all_ids[3], lid[2] if len(lid) > 2 else lid[0], 100, True,
             '[{"answer": "a", "correct": true, "question_id": 1}, {"answer": "b", "correct": true, "question_id": 2}]',
             _dt("2026-03-28 15:00:00+00"), _dt("2026-03-28 15:10:00+00")),
            (p[4] if len(p) > 4 else all_ids[4], lid[0] if len(lid) > 0 else lid[0], 40, False,
             '[{"answer": "c", "correct": false, "question_id": 1}, {"answer": "d", "correct": false, "question_id": 2}]',
             _dt("2026-03-29 20:00:00+00"), _dt("2026-03-29 20:08:00+00")),
            (p[4] if len(p) > 4 else all_ids[4], lid[0] if len(lid) > 0 else lid[0], 80, True,
             '[{"answer": "a", "correct": true, "question_id": 1}, {"answer": "b", "correct": true, "question_id": 2}]',
             _dt("2026-03-30 14:00:00+00"), _dt("2026-03-30 14:14:00+00")),
            (p[5] if len(p) > 5 else all_ids[5], lid[3] if len(lid) > 3 else lid[0], 90, True,
             '[{"answer": "a", "correct": true, "question_id": 1}]',
             _dt("2026-03-31 17:00:00+00"), _dt("2026-03-31 17:20:00+00")),
            (p[6] if len(p) > 6 else all_ids[6], lid[4] if len(lid) > 4 else lid[0], 60, False,
             '[{"answer": "b", "correct": false, "question_id": 1}]',
             _dt("2026-04-01 14:30:00+00"), _dt("2026-04-01 14:42:00+00")),
            (p[9] if len(p) > 9 else all_ids[9], lid[5] if len(lid) > 5 else lid[0], 85, True,
             '[{"answer": "a", "correct": true, "question_id": 1}]',
             _dt("2026-04-02 13:00:00+00"), _dt("2026-04-02 13:18:00+00")),
            (p[10] if len(p) > 10 else all_ids[0], lid[6] if len(lid) > 6 else lid[0], 75, True,
             '[{"answer": "a", "correct": true, "question_id": 1}]',
             _dt("2026-04-03 18:30:00+00"), _dt("2026-04-03 18:45:00+00")),
        ]
        for uid, lesid, score, passed, answers, started, completed in attempts:
            await session.execute(text("""
                INSERT INTO quiz_attempts (user_id, lesson_id, score, passed, answers, started_at, completed_at)
                VALUES (:uid, :lid, :score, :passed, cast(:answers as jsonb), :started, :completed)
            """), {"uid": uid, "lid": lesid, "score": score, "passed": passed,
                   "answers": answers, "started": started, "completed": completed})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 6. READING AMBASSADOR CERTIFICATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM reading_ambassador_certifications"))
    if r.scalar() == 0 and partner_ids:
        print("  Seeding reading_ambassador_certifications...")
        certs = [
            (p[0] if len(p) > 0 else all_ids[0], partner_ids[0], "bronze", "Reading Ambassador - Bronze",
             3, 3, _dt("2026-03-01 14:00:00+00"), _dt("2027-03-01 14:00:00+00"), _dt("2026-12-01 14:00:00+00"), True),
            (p[1] if len(p) > 1 else all_ids[1], partner_ids[1] if len(partner_ids) > 1 else partner_ids[0],
             "silver", "Reading Ambassador - Silver",
             6, 6, _dt("2026-02-15 18:00:00+00"), _dt("2027-02-15 18:00:00+00"), _dt("2026-11-15 18:00:00+00"), True),
            (p[2] if len(p) > 2 else all_ids[2], partner_ids[0], "gold", "Reading Ambassador - Gold",
             10, 10, _dt("2026-01-10 13:00:00+00"), _dt("2027-01-10 13:00:00+00"), _dt("2026-10-10 13:00:00+00"), True),
            (p[3] if len(p) > 3 else all_ids[3], partner_ids[2] if len(partner_ids) > 2 else partner_ids[0],
             "bronze", "Reading Ambassador - Bronze",
             2, 3, None, None, None, False),
            (p[4] if len(p) > 4 else all_ids[4], partner_ids[3] if len(partner_ids) > 3 else partner_ids[0],
             "silver", "Reading Ambassador - Silver",
             6, 6, _dt("2026-03-20 15:00:00+00"), _dt("2027-03-20 15:00:00+00"), _dt("2026-12-20 15:00:00+00"), True),
        ]
        for uid, pid, level, name, completed, total, cert_at, exp_at, renew_at, active in certs:
            await session.execute(text("""
                INSERT INTO reading_ambassador_certifications
                    (user_id, partner_id, certification_level, certification_name,
                     required_modules_completed, total_modules_required,
                     certified_at, expires_at, renewal_eligible_at, is_active)
                VALUES (:uid, :pid, :level, :name, :completed, :total, :cert_at, :exp_at, :renew_at, :active)
            """), {"uid": uid, "pid": pid, "level": level, "name": name,
                   "completed": completed, "total": total,
                   "cert_at": cert_at, "exp_at": exp_at, "renew_at": renew_at, "active": active})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 7. MENTORSHIP PAIRINGS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM mentorship_pairings"))
    if r.scalar() == 0 and len(teen_vol_ids) >= 5:
        print("  Seeding mentorship_pairings...")
        tv = teen_vol_ids
        pairings = [
            (tv[0], tv[1], "active", _dt("2026-03-01 14:00:00+00"), s[2] if len(s) > 2 else s[0],
             "Experienced volunteer paired with new member",
             ["leadership development", "shelving proficiency"],
             "3 months", ["circulation", "customer service"], "weekly", "afternoon", "Teen Lounge"),
            (tv[0], tv[2], "completed", _dt("2025-12-01 13:00:00+00"), s[2] if len(s) > 2 else s[0],
             "Training on reference desk procedures",
             ["reference skills", "database searching"],
             "2 months", ["reference", "technology"], "biweekly", "morning", "Reference Desk"),
            (tv[1], tv[3], "active", _dt("2026-03-15 18:00:00+00"), s[3] if len(s) > 3 else s[0],
             "Summer reading program preparation",
             ["program planning", "event setup"],
             "2 months", ["programs", "outreach"], "weekly", "afternoon", "Meeting Room A"),
            (tv[2], tv[4], "pending_match", None, s[4] if len(s) > 4 else s[0],
             "New volunteer needs orientation buddy",
             ["orientation", "library basics"],
             "1 month", ["general", "shelving"], "weekly", "morning", "Main Hall"),
            (tv[3], tv[4], "paused", _dt("2026-02-01 14:00:00+00"), s[2] if len(s) > 2 else s[0],
             "Paired for teen advisory board work",
             ["advocacy", "community engagement"],
             "6 months", ["teen advisory", "programming"], "monthly", "evening", "Teen Lounge"),
        ]
        for mentor, mentee, status, paired, paired_by, reason, goals, dur, focus, freq, time, loc in pairings:
            await session.execute(text("""
                INSERT INTO mentorship_pairings
                    (mentor_id, mentee_id, status, paired_date, paired_by_id,
                     pairing_reason, goals, expected_duration, focus_areas,
                     meeting_frequency, preferred_meeting_time, meeting_location)
                VALUES (:mentor, :mentee, :status, :paired, :paired_by,
                        :reason, :goals, :dur, :focus, :freq, :time, :loc)
            """), {"mentor": mentor, "mentee": mentee, "status": status,
                   "paired": paired, "paired_by": paired_by, "reason": reason,
                   "goals": goals, "dur": dur, "focus": focus,
                   "freq": freq, "time": time, "loc": loc})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 8. PARENT CONNECTION GROUPS + MEMBERS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM parent_connection_groups"))
    if r.scalar() == 0 and branch_ids:
        print("  Seeding parent_connection_groups...")
        b1 = branch_ids[0]
        b2 = branch_ids[1] if len(branch_ids) > 1 else b1
        groups = [
            ("New Parents Circle", "Support group for parents of newborns and infants",
             s[2] if len(s) > 2 else s[0], b1, "support", 12, "weekly", "Tuesday", "10:00",
             "Meeting Room A", ["English"], True),
            ("Bilingual Families", "Spanish-English bilingual family reading and activities",
             s[4] if len(s) > 4 else s[0], b1, "activity", 15, "biweekly", "Thursday", "18:00",
             "Main Hall", ["English", "Spanish"], True),
            ("Toddler Tales", "Storytime and play for ages 1-3 with caregivers",
             s[3] if len(s) > 3 else s[0], b1, "activity", 20, "weekly", "Wednesday", "10:30",
             "Main Hall", ["English"], True),
            ("Homeschool Connect", "Resources and community for homeschooling families",
             s[5] if len(s) > 5 else s[0], b2, "education", 10, "monthly", "Friday", "13:00",
             "Meeting Room B", ["English"], True),
            ("Single Parents Network", "Peer support for single-parent households",
             s[2] if len(s) > 2 else s[0], b1, "support", 8, "biweekly", "Saturday", "09:00",
             "Meeting Room A", ["English"], True),
            ("Grandparents Raising Kids", "Support for grandparents as primary caregivers",
             s[6] if len(s) > 6 else s[0], b1, "support", 10, "monthly", "Monday", "14:00",
             "Meeting Room B", ["English"], False),
        ]
        group_ids = []
        for name, desc, fac, bid, gtype, maxm, freq, dow, mtime, loc, langs, active in groups:
            r2 = await session.execute(text("""
                INSERT INTO parent_connection_groups
                    (name, description, facilitator_id, branch_id, group_type,
                     max_members, meeting_frequency, meeting_day_of_week,
                     meeting_time, location, languages, is_active)
                VALUES (:name, :desc, :fac, :bid, :gtype, :maxm, :freq, :dow,
                        :mtime, :loc, :langs, :active)
                RETURNING id
            """), {"name": name, "desc": desc, "fac": fac, "bid": bid, "gtype": gtype,
                   "maxm": maxm, "freq": freq, "dow": dow, "mtime": mtime,
                   "loc": loc, "langs": langs, "active": active})
            group_ids.append(r2.scalar())
        await session.flush()

        # Group members
        print("  Seeding parent_connection_group_members...")
        members = [
            (group_ids[0], p[0] if len(p) > 0 else all_ids[0], "active", _d("2026-01-15"), None, 12),
            (group_ids[0], p[5] if len(p) > 5 else all_ids[5], "active", _d("2026-02-01"), None, 8),
            (group_ids[0], p[9] if len(p) > 9 else all_ids[9], "active", _d("2026-03-01"), None, 4),
            (group_ids[1], p[2] if len(p) > 2 else all_ids[2], "active", _d("2026-01-10"), None, 6),
            (group_ids[1], p[8] if len(p) > 8 else all_ids[8], "active", _d("2026-02-20"), None, 3),
            (group_ids[2], p[7] if len(p) > 7 else all_ids[7], "active", _d("2026-01-05"), None, 13),
            (group_ids[2], p[2] if len(p) > 2 else all_ids[2], "active", _d("2026-03-10"), None, 2),
            (group_ids[3], p[3] if len(p) > 3 else all_ids[3], "active", _d("2026-02-01"), None, 2),
            (group_ids[4], p[10] if len(p) > 10 else all_ids[0], "active", _d("2026-03-01"), None, 3),
            (group_ids[4], p[11] if len(p) > 11 else all_ids[1], "inactive", _d("2025-11-01"), _d("2026-02-15"), 5),
        ]
        for gid, pid, status, joined, left, att in members:
            await session.execute(text("""
                INSERT INTO parent_connection_group_members
                    (group_id, patron_id, status, joined_date, left_date, attendance_count)
                VALUES (:gid, :pid, :status, :joined, :left, :att)
            """), {"gid": gid, "pid": pid, "status": status, "joined": joined,
                   "left": left, "att": att})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 9. PARENT ONBOARDING SESSIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM parent_onboarding_sessions"))
    if r.scalar() == 0 and branch_ids:
        print("  Seeding parent_onboarding_sessions...")
        b1 = branch_ids[0]
        b2 = branch_ids[1] if len(branch_ids) > 1 else b1
        wp = welcome_packet_ids

        sessions_data = [
            (p[0] if len(p) > 0 else all_ids[0], s[2] if len(s) > 2 else s[0], b1, "completed",
             _dt("2026-01-10 14:00:00+00"), _dt("2026-01-10 15:00:00+00"), 3, ["English"],
             "First-time parent, very engaged",
             '["early literacy materials", "baby storytime info"]',
             '["pediatric clinic", "WIC office"]',
             wp[0] if len(wp) > 0 else None),
            (p[5] if len(p) > 5 else all_ids[5], s[3] if len(s) > 3 else s[0], b1, "completed",
             _dt("2026-02-05 18:00:00+00"), _dt("2026-02-05 19:00:00+00"), 8, ["English", "Hindi"],
             "Multilingual household, looking for bilingual resources",
             '["bilingual books", "ESL classes"]',
             '["language tutoring center"]',
             wp[1] if len(wp) > 1 else None),
            (p[9] if len(p) > 9 else all_ids[9], s[4] if len(s) > 4 else s[0], b1, "completed",
             _dt("2026-02-20 14:00:00+00"), _dt("2026-02-20 14:45:00+00"), 14, ["English", "Spanish"],
             "Single mother, needs flexible scheduling",
             '["toddler programs", "parenting books"]',
             '["community action center", "food bank"]',
             wp[2] if len(wp) > 2 else None),
            (p[7] if len(p) > 7 else all_ids[7], s[2] if len(s) > 2 else s[0], b1, "completed",
             _dt("2026-03-01 13:00:00+00"), _dt("2026-03-01 14:00:00+00"), 6, ["English"],
             "Stay-at-home parent with two kids",
             '["sibling activities", "storytime schedule"]',
             None,
             wp[3] if len(wp) > 3 else None),
            (p[2] if len(p) > 2 else all_ids[2], s[5] if len(s) > 5 else s[0], b2, "scheduled",
             _dt("2026-04-08 14:00:00+00"), None, 2, ["English"],
             None, None, None, None),
            (p[10] if len(p) > 10 else all_ids[0], s[6] if len(s) > 6 else s[0], b1, "scheduled",
             _dt("2026-04-10 18:00:00+00"), None, 5, ["English", "Urdu"],
             "Extended family household", None, None, None),
            (p[2] if len(p) > 2 else all_ids[2], s[2] if len(s) > 2 else s[0], b1, "cancelled",
             _dt("2026-03-15 14:00:00+00"), None, 18, ["English", "Spanish"],
             "Rescheduled due to weather", None, None, None),
            (p[8] if len(p) > 8 else all_ids[8], s[3] if len(s) > 3 else s[0], b1, "completed",
             _dt("2026-03-25 15:00:00+00"), _dt("2026-03-25 16:00:00+00"), 10, ["English"],
             "Interested in STEM activities for baby",
             '["sensory play materials", "STEM baby books"]',
             None,
             wp[4] if len(wp) > 4 else None),
        ]
        onboarding_ids = []
        for patron, staff, bid, status, sched, comp, age, langs, notes, needs, svc, wpid in sessions_data:
            r2 = await session.execute(text("""
                INSERT INTO parent_onboarding_sessions
                    (patron_id, staff_id, branch_id, status, scheduled_at, completed_at,
                     baby_age_months, languages_spoken, family_situation_notes,
                     needs_identified, services_referred, welcome_packet_id)
                VALUES (:patron, :staff, :bid, :status, :sched, :comp, :age, :langs,
                        :notes, cast(:needs as jsonb), cast(:svc as jsonb), :wpid)
                RETURNING id
            """), {"patron": patron, "staff": staff, "bid": bid, "status": status,
                   "sched": sched, "comp": comp, "age": age, "langs": langs,
                   "notes": notes, "needs": needs, "svc": svc, "wpid": wpid})
            onboarding_ids.append(r2.scalar())
        await session.flush()

        # ════════════════════════════════════════════════════════════
        # 10. PARENT HOME VISITS
        # ════════════════════════════════════════════════════════════
        r = await session.execute(text("SELECT COUNT(*) FROM parent_home_visits"))
        if r.scalar() == 0:
            print("  Seeding parent_home_visits...")
            visits = [
                (p[0] if len(p) > 0 else all_ids[0], s[2] if len(s) > 2 else s[0], onboarding_ids[0],
                 "welcome", "completed", _d("2026-01-20"), "10:00",
                 _dt("2026-01-20 14:05:00+00"), _dt("2026-01-20 14:45:00+00"),
                 "123 Elm St, Somewhere Up North",
                 "Delivered welcome packet and early literacy kit",
                 '["welcome packet", "board books", "library card application"]',
                 '["storytime schedule", "baby lap-sit program"]', False, None),
                (p[5] if len(p) > 5 else all_ids[5], s[3] if len(s) > 3 else s[0], onboarding_ids[1],
                 "follow_up", "completed", _d("2026-02-20"), "14:00",
                 _dt("2026-02-20 18:10:00+00"), _dt("2026-02-20 18:50:00+00"),
                 "456 Oak Ave, Somewhere Up North",
                 "Family settling in well, connected with Hindi book collection",
                 '["bilingual book list", "library card"]',
                 '["ESL resources", "cultural programs"]', True, _d("2026-04-20")),
                (p[9] if len(p) > 9 else all_ids[9], s[4] if len(s) > 4 else s[0], onboarding_ids[2],
                 "welcome", "completed", _d("2026-03-05"), "10:00",
                 _dt("2026-03-05 14:00:00+00"), _dt("2026-03-05 14:40:00+00"),
                 "789 Maple Dr, Somewhere Up North",
                 "Mom very interested in toddler programs",
                 '["welcome packet", "toddler activity guide"]',
                 '["toddler tales group", "food assistance"]', True, _d("2026-04-15")),
                (p[7] if len(p) > 7 else all_ids[7], s[2] if len(s) > 2 else s[0], onboarding_ids[3],
                 "follow_up", "completed", _d("2026-03-20"), "09:00",
                 _dt("2026-03-20 13:00:00+00"), _dt("2026-03-20 13:35:00+00"),
                 "321 Pine Ln, Somewhere Up North",
                 "Both kids loving storytime, older child interested in summer reading",
                 '["summer reading flyer"]',
                 '["summer reading program", "sibling activities"]', False, None),
                (p[2] if len(p) > 2 else all_ids[2], s[5] if len(s) > 5 else s[0], onboarding_ids[4],
                 "welcome", "scheduled", _d("2026-04-15"), "10:00",
                 None, None, "555 Birch Rd, Somewhere Up North", None, None, None, False, None),
                (p[10] if len(p) > 10 else all_ids[0], s[6] if len(s) > 6 else s[0], onboarding_ids[5],
                 "welcome", "scheduled", _d("2026-04-18"), "14:00",
                 None, None, "678 Cedar Way, Somewhere Up North", None, None, None, False, None),
                (p[8] if len(p) > 8 else all_ids[8], s[3] if len(s) > 3 else s[0], onboarding_ids[7],
                 "follow_up", "completed", _d("2026-04-02"), "11:00",
                 _dt("2026-04-02 15:00:00+00"), _dt("2026-04-02 15:30:00+00"),
                 "234 Spruce St, Somewhere Up North",
                 "Baby enjoying sensory play materials, parent asking about baby sign language class",
                 '["STEM activity cards"]',
                 '["baby sign language", "sensory play"]', True, _d("2026-05-01")),
                (p[2] if len(p) > 2 else all_ids[2], s[2] if len(s) > 2 else s[0], None,
                 "assessment", "cancelled", _d("2026-03-18"), "10:00",
                 None, None, "890 Willow Ct, Somewhere Up North",
                 "Cancelled due to illness, to be rescheduled",
                 None, None, True, _d("2026-04-20")),
            ]
            for patron, visitor, psid, purpose, status, sdate, stime, astart, aend, addr, notes, items, svc, follow, nxt in visits:
                await session.execute(text("""
                    INSERT INTO parent_home_visits
                        (patron_id, visitor_id, parent_session_id, purpose, status,
                         scheduled_date, scheduled_time, actual_start, actual_end,
                         address, visit_notes, items_brought, services_discussed,
                         follow_up_needed, next_visit_date)
                    VALUES (:patron, :visitor, :psid, :purpose, :status,
                            :sdate, :stime, :astart, :aend, :addr, :notes,
                            cast(:items as jsonb), cast(:svc as jsonb), :follow, :nxt)
                """), {"patron": patron, "visitor": visitor, "psid": psid, "purpose": purpose,
                       "status": status, "sdate": sdate, "stime": stime, "astart": astart,
                       "aend": aend, "addr": addr, "notes": notes, "items": items,
                       "svc": svc, "follow": follow, "nxt": nxt})
            await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 11. OVERFLOW PURCHASES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM overflow_purchases"))
    if r.scalar() == 0:
        print("  Seeding overflow_purchases...")
        purchases = [
            (p[0] if len(p) > 0 else all_ids[0], 101, "The Quiet Ones", "Marguerite Holloway",
             "cs_seed_001", "pi_seed_001", 999, 59, 100, 600, 10, "completed", _dt("2026-03-15 14:05:00+00"), None),
            (p[1] if len(p) > 1 else all_ids[1], 102, "Salt and Citrus", "Nina Delgado-Ruiz",
             "cs_seed_002", "pi_seed_002", 1299, 68, 130, 780, 10, "completed", _dt("2026-03-18 18:20:00+00"), None),
            (p[4] if len(p) > 4 else all_ids[4], 103, "The Griot's Algorithm", "Kofi Asante",
             "cs_seed_003", "pi_seed_003", 1499, 74, 150, 900, 10, "completed", _dt("2026-03-22 13:30:00+00"), None),
            (p[5] if len(p) > 5 else all_ids[5], 104, "Banchan for One", "Ji-Yeon Park",
             "cs_seed_004", "pi_seed_004", 899, 56, 90, 540, 10, "completed", _dt("2026-03-25 20:00:00+00"), None),
            (p[8] if len(p) > 8 else all_ids[8], 105, "Due Date", "Tamara Washington",
             "cs_seed_005", "pi_seed_005", 1199, 65, 120, 720, 10, "completed", _dt("2026-03-28 15:15:00+00"), None),
            (p[10] if len(p) > 10 else all_ids[0], 106, "Quiet Hours", "Lena Bjork",
             "cs_seed_006", "pi_seed_006", 999, 59, 100, 600, 10, "pending", None, None),
            (p[3] if len(p) > 3 else all_ids[3], 107, "Rain Check", "Devon Mills",
             "cs_seed_007", "pi_seed_007", 1099, 62, 110, 660, 10, "completed", _dt("2026-04-01 17:45:00+00"), None),
            (p[6] if len(p) > 6 else all_ids[6], 108, "The Hollow Season", "Ruth Evers",
             "cs_seed_008", "pi_seed_008", 799, 53, 80, 480, 10, "refunded", _dt("2026-03-30 14:00:00+00"), None),
        ]
        for uid, eid, title, author, cs, pi, price, fee, kick, royalty, pct, status, comp, refund in purchases:
            await session.execute(text("""
                INSERT INTO overflow_purchases
                    (user_id, metislib_ebook_id, ebook_title, ebook_author,
                     stripe_checkout_session_id, stripe_payment_intent_id,
                     sale_price_cents, stripe_fee_cents, library_kickback_cents,
                     author_royalty_cents, library_kickback_percent, currency, status,
                     completed_at, refunded_at)
                VALUES (:uid, :eid, :title, :author, :cs, :pi, :price, :fee, :kick,
                        :royalty, :pct, 'USD', :status, :comp, :refund)
            """), {"uid": uid, "eid": eid, "title": title, "author": author,
                   "cs": cs, "pi": pi, "price": price, "fee": fee, "kick": kick,
                   "royalty": royalty, "pct": pct, "status": status,
                   "comp": comp, "refund": refund})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 12. FOUND ITEM MATCHES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM found_item_matches"))
    if r.scalar() == 0 and found_item_ids and lost_item_ids:
        print("  Seeding found_item_matches...")
        matches = [
            (found_item_ids[0], lost_item_ids[0], "high", 92.50,
             '["color match", "brand match", "location match"]', '["size uncertain"]',
             True, "Patron confirmed this is their Hydro Flask", True, _dt("2026-03-20 14:00:00+00"), s[2] if len(s) > 2 else s[0]),
            (found_item_ids[1], lost_item_ids[1], "high", 88.00,
             '["description match", "location match"]', '["frame color slightly different in report"]',
             True, "Patron picked up glasses, confirmed match", True, _dt("2026-03-21 18:30:00+00"), s[3] if len(s) > 3 else s[0]),
            (found_item_ids[2], lost_item_ids[2], "medium", 72.00,
             '["color match", "material match"]', '["pattern not specified in lost report"]',
             False, None, True, _dt("2026-03-25 13:00:00+00"), None),
            (found_item_ids[3], lost_item_ids[3], "high", 95.00,
             '["brand match", "case description match", "area found matches"]', None,
             True, "Patron unlocked phone to verify ownership", True, _dt("2026-03-22 15:00:00+00"), s[4] if len(s) > 4 else s[0]),
            (found_item_ids[4] if len(found_item_ids) > 4 else found_item_ids[0],
             lost_item_ids[4] if len(lost_item_ids) > 4 else lost_item_ids[0],
             "medium", 68.50,
             '["key type match"]', '["fob color uncertain", "number of keys different"]',
             None, None, True, _dt("2026-03-28 20:00:00+00"), None),
            (found_item_ids[5] if len(found_item_ids) > 5 else found_item_ids[0],
             lost_item_ids[5] if len(lost_item_ids) > 5 else lost_item_ids[0],
             "high", 91.00,
             '["exact description match", "name on lunchbox"]', None,
             True, "Name label inside matches patron child", True, _dt("2026-03-26 14:30:00+00"), s[2] if len(s) > 2 else s[0]),
            (found_item_ids[7] if len(found_item_ids) > 7 else found_item_ids[0],
             lost_item_ids[6] if len(lost_item_ids) > 6 else lost_item_ids[0],
             "low", 45.00,
             '["general category match"]', '["color mismatch", "size mismatch"]',
             False, "Patron says this is not their stuffed animal", True, _dt("2026-04-01 18:00:00+00"), s[3] if len(s) > 3 else s[0]),
            (found_item_ids[6] if len(found_item_ids) > 6 else found_item_ids[0],
             lost_item_ids[7] if len(lost_item_ids) > 7 else lost_item_ids[0],
             "medium", 75.00,
             '["color match", "type match"]', '["brand not specified"]',
             None, None, False, None, None),
        ]
        for fid, lid, conf, score, mf, nmf, confirmed, notes, notified, notified_at, confirmed_by in matches:
            await session.execute(text("""
                INSERT INTO found_item_matches
                    (found_item_id, lost_item_record_id, confidence_level, match_score,
                     matching_factors, non_matching_factors, is_confirmed,
                     confirmation_notes, patron_notified, patron_notified_at, confirmed_by_id)
                VALUES (:fid, :lid, :conf, :score,
                        cast(:mf as jsonb), cast(:nmf as jsonb), :confirmed,
                        :notes, :notified, :notified_at, :confirmed_by)
            """), {"fid": fid, "lid": lid, "conf": conf, "score": score,
                   "mf": mf, "nmf": nmf, "confirmed": confirmed, "notes": notes,
                   "notified": notified, "notified_at": notified_at, "confirmed_by": confirmed_by})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 13. ROOM WAITLIST
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM room_waitlist"))
    if r.scalar() == 0 and room_ids:
        print("  Seeding room_waitlist...")
        waitlist = [
            (room_ids[0] if len(room_ids) > 0 else room_ids[0], p[0] if len(p) > 0 else all_ids[0],
             _dt("2026-04-07 14:00:00+00"), _dt("2026-04-07 16:00:00+00"), "pending", None, _dt("2026-04-07 13:00:00+00")),
            (room_ids[0] if len(room_ids) > 0 else room_ids[0], p[1] if len(p) > 1 else all_ids[1],
             _dt("2026-04-07 14:00:00+00"), _dt("2026-04-07 15:00:00+00"), "pending", None, _dt("2026-04-07 13:00:00+00")),
            (room_ids[1] if len(room_ids) > 1 else room_ids[0], p[4] if len(p) > 4 else all_ids[4],
             _dt("2026-04-08 18:00:00+00"), _dt("2026-04-08 20:00:00+00"), "notified", _dt("2026-04-04 14:00:00+00"), _dt("2026-04-08 17:00:00+00")),
            (room_ids[2] if len(room_ids) > 2 else room_ids[0], p[5] if len(p) > 5 else all_ids[5],
             _dt("2026-04-05 13:00:00+00"), _dt("2026-04-05 15:00:00+00"), "expired", None, _dt("2026-04-04 12:00:00+00")),
            (room_ids[3] if len(room_ids) > 3 else room_ids[0], p[10] if len(p) > 10 else all_ids[0],
             _dt("2026-04-09 17:00:00+00"), _dt("2026-04-09 19:00:00+00"), "pending", None, _dt("2026-04-09 16:00:00+00")),
            (room_ids[7] if len(room_ids) > 7 else room_ids[0], p[3] if len(p) > 3 else all_ids[3],
             _dt("2026-04-10 22:00:00+00"), _dt("2026-04-11 00:00:00+00"), "pending", None, _dt("2026-04-10 21:00:00+00")),
            (room_ids[8] if len(room_ids) > 8 else room_ids[0], p[2] if len(p) > 2 else all_ids[2],
             _dt("2026-04-06 19:00:00+00"), _dt("2026-04-06 21:00:00+00"), "notified", _dt("2026-04-03 20:00:00+00"), _dt("2026-04-06 18:00:00+00")),
            (room_ids[9] if len(room_ids) > 9 else room_ids[0], p[6] if len(p) > 6 else all_ids[6],
             _dt("2026-04-11 14:00:00+00"), _dt("2026-04-11 16:00:00+00"), "pending", None, _dt("2026-04-11 13:00:00+00")),
        ]
        for rid, pid, dstart, dend, status, notified, expires in waitlist:
            await session.execute(text("""
                INSERT INTO room_waitlist
                    (room_id, patron_id, desired_start_time, desired_end_time,
                     status, notified_at, expires_at)
                VALUES (:rid, :pid, :dstart, :dend, :status, :notified, :expires)
            """), {"rid": rid, "pid": pid, "dstart": dstart, "dend": dend,
                   "status": status, "notified": notified, "expires": expires})
        await session.flush()

    # ════════════════════════════════════════════════════════════════
    # 14. SESSION EXTENSION REQUESTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM session_extension_requests"))
    if r.scalar() == 0 and reservation_ids and session_ids_comp:
        print("  Seeding session_extension_requests...")
        res = reservation_ids
        ses = session_ids_comp
        extensions = [
            (res[0] if len(res) > 0 else res[0], ses[0] if len(ses) > 0 else ses[0], 30, "approved",
             _dt("2026-03-25 18:30:00+00"), _dt("2026-03-25 18:32:00+00"), s[2] if len(s) > 2 else s[0], None),
            (res[1] if len(res) > 1 else res[0], ses[1] if len(ses) > 1 else ses[0], 15, "approved",
             _dt("2026-03-26 15:00:00+00"), _dt("2026-03-26 15:05:00+00"), s[3] if len(s) > 3 else s[0], None),
            (res[2] if len(res) > 2 else res[0], ses[2] if len(ses) > 2 else ses[0], 30, "denied",
             _dt("2026-03-27 19:45:00+00"), None, s[4] if len(s) > 4 else s[0],
             "Computer lab closing in 20 minutes, not enough time for extension"),
            (res[3] if len(res) > 3 else res[0], ses[3] if len(ses) > 3 else ses[0], 15, "approved",
             _dt("2026-03-28 14:30:00+00"), _dt("2026-03-28 14:31:00+00"), s[2] if len(s) > 2 else s[0], None),
            (res[4] if len(res) > 4 else res[0], ses[4] if len(ses) > 4 else ses[0], 30, "expired",
             _dt("2026-03-29 20:00:00+00"), None, None, None),
            (res[5] if len(res) > 5 else res[0], ses[5] if len(ses) > 5 else ses[0], 15, "pending",
             _dt("2026-04-03 18:00:00+00"), None, None, None),
            (res[6] if len(res) > 6 else res[0], ses[6] if len(ses) > 6 else ses[0], 30, "approved",
             _dt("2026-04-01 15:15:00+00"), _dt("2026-04-01 15:18:00+00"), s[5] if len(s) > 5 else s[0], None),
            (res[7] if len(res) > 7 else res[0], ses[7] if len(ses) > 7 else ses[0], 15, "denied",
             _dt("2026-04-02 20:30:00+00"), None, s[3] if len(s) > 3 else s[0],
             "Patron already used maximum extensions for today"),
        ]
        for resid, sesid, mins, status, req_at, app_at, app_by, denial in extensions:
            await session.execute(text("""
                INSERT INTO session_extension_requests
                    (reservation_id, session_id, extension_minutes, status,
                     requested_at, approved_at, approved_by, denial_reason)
                VALUES (:resid, :sesid, :mins, :status, :req_at, :app_at, :app_by, :denial)
            """), {"resid": resid, "sesid": sesid, "mins": mins, "status": status,
                   "req_at": req_at, "app_at": app_at, "app_by": app_by, "denial": denial})
        await session.flush()

    # FIX SEQUENCES
    seq_tables = [
        "reading_activities", "reading_milestones", "reading_progress",
        "quiz_attempts",
        "reading_ambassador_certifications", "mentorship_pairings",
        "parent_connection_groups", "parent_connection_group_members",
        "parent_onboarding_sessions", "parent_home_visits",
        "overflow_purchases", "found_item_matches", "room_waitlist",
        "session_extension_requests",
    ]
    for table in seq_tables:
        try:
            async with session.begin_nested():
                await session.execute(text(
                    f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                ))
        except SQLAlchemyError:
            pass

    await session.flush()
    print("  Community batch seeding complete!")
    return True
