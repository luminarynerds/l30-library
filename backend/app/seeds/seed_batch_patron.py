# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
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


async def seed_batch_patron(session: AsyncSession) -> bool:

    # ── Grab reusable IDs ──────────────────────────────────────────
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]

    branches_r = await session.execute(text("SELECT id FROM branches"))
    branch_ids = [r[0] for r in branches_r.fetchall()]

    now = datetime.now(utc)

    # ════════════════════════════════════════════════════════════════
    # 1. PATRON READING HISTORY
    #    FK: user_id->users, bibframe_work_id->bibframe_works
    #    Unique: (user_id, bibframe_work_id)
    # ════════════════════════════════════════════════════════════════
    bw_r = await session.execute(text("SELECT COUNT(*) FROM bibframe_works"))
    bw_count = bw_r.scalar()

    r = await session.execute(text("SELECT COUNT(*) FROM patron_reading_history"))
    if r.scalar() == 0 and bw_count > 0:
        print("  Seeding patron_reading_history...")
        bw_ids_r = await session.execute(text("SELECT id FROM bibframe_works"))
        bw_ids = [row[0] for row in bw_ids_r.fetchall()]

        formats = ["physical", "ebook", "audiobook", "large_print"]
        sources = ["catalog", "interlibrary_loan", "recommendation", "browsing", "book_club"]
        mini_reviews = [
            "Loved the characters and setting. A real page-turner.",
            "Good but the pacing slowed down in the middle chapters.",
            "Wonderful audiobook narration. Will listen again.",
            "My book club picked this and it sparked great discussion.",
            "Not my usual genre but I was pleasantly surprised.",
            "Beautifully written. Made me think about life differently.",
            "A solid read for a rainy weekend. Nothing groundbreaking.",
            "Couldn't put it down! Finished in two days.",
            "I appreciated the research behind this one.",
            "Perfect comfort read. Like visiting old friends.",
            None, None, None, None, None,  # Many entries have no review
        ]

        count = 0
        used = set()
        sample_patrons = random.sample(patron_ids, min(len(patron_ids), 40))
        for uid in sample_patrons:
            num_entries = random.randint(1, 3)
            for _ in range(num_entries):
                if count >= 50:
                    break
                bwid = random.choice(bw_ids)
                if (uid, bwid) in used:
                    continue
                used.add((uid, bwid))

                days_ago = random.randint(7, 400)
                started = _past(days_ago)
                is_completed = random.random() < 0.75
                completed = started + timedelta(days=random.randint(3, 30)) if is_completed else None
                dnf = not is_completed and random.random() < 0.3
                rating = round(random.uniform(2.0, 5.0), 1) if is_completed else None
                review = random.choice(mini_reviews) if is_completed and random.random() < 0.4 else None

                await session.execute(text("""
                    INSERT INTO patron_reading_history
                        (user_id, bibframe_work_id, started_date, completed_date,
                         is_completed, rating, review, favorite, did_not_finish,
                         format_read, source)
                    VALUES (:uid, :bwid, :started, :completed, :is_completed,
                            :rating, :review, :fav, :dnf, :fmt, :src)
                """), {
                    "uid": uid, "bwid": bwid, "started": started,
                    "completed": completed, "is_completed": is_completed,
                    "rating": rating, "review": review,
                    "fav": is_completed and random.random() < 0.2,
                    "dnf": dnf,
                    "fmt": random.choice(formats),
                    "src": random.choice(sources),
                })
                count += 1
            if count >= 50:
                break
        print(f"    Created {count} reading history entries")
        await session.commit()
    elif bw_count == 0:
        print("  Skipping patron_reading_history — no bibframe_works data")

    # ════════════════════════════════════════════════════════════════
    # 2. PATRON PREFERENCES
    #    FK: patron_id->users (unique), set_by_id->users
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM patron_preferences"))
    if r.scalar() == 0:
        print("  Seeding patron_preferences...")
        notes_pool = [
            "Prefers quiet study areas near the windows.",
            "Enjoys mystery and thriller genres primarily.",
            "Has difficulty with small text; always offer large print options.",
            "Visits every Tuesday and Thursday afternoon.",
            "Appreciates recommendations for historical fiction.",
            "Uses a wheelchair; needs ground-floor access only.",
            "Interested in audiobooks for commute listening.",
            "Requests Braille materials when available.",
            "Prefers self-checkout to minimize wait times.",
            "ESL learner; benefits from bilingual materials.",
            None, None, None, None, None, None,
        ]

        sample_patrons = random.sample(patron_ids, min(len(patron_ids), 30))
        for uid in sample_patrons:
            large_print = random.random() < 0.15
            audio = random.random() < 0.2
            braille = random.random() < 0.05
            fragile = random.random() < 0.1
            mobility = random.random() < 0.08
            extra_time = random.random() < 0.1

            await session.execute(text("""
                INSERT INTO patron_preferences
                    (patron_id, prefers_large_print, prefers_audio_format,
                     prefers_braille, handle_fragile_items_with_care,
                     limited_mobility_assistance_needed,
                     needs_extra_time_checkout, preference_notes,
                     set_by_id, created_at)
                VALUES (:pid, :lp, :audio, :braille, :fragile,
                        :mobility, :extra, :notes, :set_by, :created)
            """), {
                "pid": uid,
                "lp": large_print, "audio": audio, "braille": braille,
                "fragile": fragile, "mobility": mobility, "extra": extra_time,
                "notes": random.choice(notes_pool),
                "set_by": random.choice(staff_ids),
                "created": _past(random.randint(30, 365)),
            })
        print(f"    Created {len(sample_patrons)} patron preference records")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 3. NOTIFICATION PREFERENCES (large table — many boolean cols)
    #    FK: user_id->users (unique)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM notification_preferences"))
    if r.scalar() == 0:
        print("  Seeding notification_preferences...")
        sample_users = random.sample(all_ids, min(len(all_ids), 40))
        for uid in sample_users:
            await session.execute(text("""
                INSERT INTO notification_preferences
                    (user_id,
                     email_checkout_receipt, email_due_date_reminder,
                     email_overdue_notice, email_hold_ready,
                     email_hold_expiring, email_hold_cancelled,
                     email_fine_notice, due_date_reminder_days,
                     hold_expiring_reminder_days, overdue_notice_intervals,
                     email_training_new_course, email_training_course_completed,
                     email_training_milestone, email_training_certificate,
                     email_training_streak_reminder, email_training_new_content,
                     email_training_skill_assessment, email_training_weekly_digest,
                     streak_reminder_days,
                     sms_notifications_enabled, sms_phone_verified,
                     sms_checkout_receipt, sms_due_date_reminder,
                     sms_overdue_notice, sms_hold_ready,
                     sms_hold_expiring, sms_hold_cancelled,
                     sms_fine_notice, sms_event_reminder,
                     sms_due_date_reminder_days, sms_event_reminder_hours,
                     email_review_response,
                     email_board_meeting_scheduled, email_board_agenda_published,
                     email_board_vote_reminder, email_board_motion_updates,
                     email_board_resolution_adopted, email_board_action_item_due,
                     email_board_action_item_assigned, email_board_document_published,
                     email_board_public_comment_received, email_board_comment_period_alerts,
                     email_board_committee_appointment, email_board_committee_meeting,
                     board_meeting_reminder_days, board_vote_reminder_hours,
                     board_action_item_reminder_days,
                     email_staff_daily_alert, staff_daily_alert_time,
                     staff_daily_alert_days,
                     created_at, updated_at)
                VALUES (:uid,
                        :e_checkout, :e_due, :e_overdue, :e_hold_ready,
                        :e_hold_exp, :e_hold_cancel, :e_fine, :due_days,
                        :hold_exp_days, cast(:overdue_intervals as json),
                        :e_train_new, :e_train_done, :e_train_mile,
                        :e_train_cert, :e_train_streak, :e_train_content,
                        :e_train_skill, :e_train_digest, :streak_days,
                        :sms_enabled, :sms_verified,
                        :s_checkout, :s_due, :s_overdue, :s_hold_ready,
                        :s_hold_exp, :s_hold_cancel, :s_fine, :s_event,
                        :s_due_days, :s_event_hours,
                        :e_review,
                        :e_board_meet, :e_board_agenda, :e_board_vote,
                        :e_board_motion, :e_board_resolution, :e_board_action_due,
                        :e_board_action_assign, :e_board_doc, :e_board_comment,
                        :e_board_comment_period, :e_board_committee, :e_board_committee_meet,
                        :board_meet_days, :board_vote_hours, :board_action_days,
                        :e_staff_daily, :staff_time, cast(:staff_days as json),
                        :created, :updated)
            """), {
                "uid": uid,
                "e_checkout": random.random() < 0.8,
                "e_due": random.random() < 0.85,
                "e_overdue": True,
                "e_hold_ready": True,
                "e_hold_exp": random.random() < 0.7,
                "e_hold_cancel": random.random() < 0.6,
                "e_fine": True,
                "due_days": random.choice([2, 3, 5]),
                "hold_exp_days": random.choice([1, 2, 3]),
                "overdue_intervals": json.dumps([1, 7, 14, 30]),
                "e_train_new": random.random() < 0.5,
                "e_train_done": random.random() < 0.6,
                "e_train_mile": random.random() < 0.4,
                "e_train_cert": random.random() < 0.7,
                "e_train_streak": random.random() < 0.3,
                "e_train_content": random.random() < 0.4,
                "e_train_skill": random.random() < 0.3,
                "e_train_digest": random.random() < 0.5,
                "streak_days": random.choice([3, 5, 7]),
                "sms_enabled": random.random() < 0.3,
                "sms_verified": False,
                "s_checkout": False,
                "s_due": random.random() < 0.2,
                "s_overdue": random.random() < 0.25,
                "s_hold_ready": random.random() < 0.3,
                "s_hold_exp": False,
                "s_hold_cancel": False,
                "s_fine": random.random() < 0.15,
                "s_event": random.random() < 0.2,
                "s_due_days": random.choice([1, 2, 3]),
                "s_event_hours": random.choice([2, 4, 24]),
                "e_review": random.random() < 0.5,
                "e_board_meet": random.random() < 0.3,
                "e_board_agenda": random.random() < 0.2,
                "e_board_vote": random.random() < 0.2,
                "e_board_motion": random.random() < 0.15,
                "e_board_resolution": random.random() < 0.2,
                "e_board_action_due": random.random() < 0.2,
                "e_board_action_assign": random.random() < 0.2,
                "e_board_doc": random.random() < 0.15,
                "e_board_comment": random.random() < 0.1,
                "e_board_comment_period": random.random() < 0.1,
                "e_board_committee": random.random() < 0.15,
                "e_board_committee_meet": random.random() < 0.15,
                "board_meet_days": random.choice([1, 3, 7]),
                "board_vote_hours": random.choice([12, 24, 48]),
                "board_action_days": random.choice([1, 3, 5]),
                "e_staff_daily": uid in staff_ids and random.random() < 0.6,
                "staff_time": random.choice(["07:00", "08:00", "09:00"]),
                "staff_days": json.dumps(["MON", "TUE", "WED", "THU", "FRI"]),
                "created": _past(random.randint(30, 365)),
                "updated": _past(random.randint(0, 29)),
            })
        print(f"    Created {len(sample_users)} notification preference records")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 3b. USER NOTIFICATION PREFERENCES (digest/quiet-hours table)
    #     FK: user_id->users (unique)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM user_notification_preferences"))
    if r.scalar() == 0:
        print("  Seeding user_notification_preferences...")
        sample_users = random.sample(all_ids, min(len(all_ids), 40))
        for uid in sample_users:
            digest_enabled = random.random() < 0.4
            quiet_enabled = random.random() < 0.3
            await session.execute(text("""
                INSERT INTO user_notification_preferences
                    (user_id, channel_preferences,
                     digest_enabled, digest_frequency,
                     digest_preferred_time, digest_preferred_day,
                     quiet_hours_enabled, quiet_hours_start,
                     quiet_hours_end, quiet_hours_days,
                     created_at, updated_at)
                VALUES (:uid, cast(:channels as json),
                        :digest, :freq, :pref_time, :pref_day,
                        :quiet, :q_start, :q_end, cast(:q_days as json),
                        :created, :updated)
            """), {
                "uid": uid,
                "channels": json.dumps({"email": True, "sms": random.random() < 0.3, "push": random.random() < 0.2}),
                "digest": digest_enabled,
                "freq": random.choice(["daily", "weekly"]) if digest_enabled else "daily",
                "pref_time": random.choice(["08:00", "09:00", "17:00", "18:00"]),
                "pref_day": random.choice([0, 1, 4, 5]),
                "quiet": quiet_enabled,
                "q_start": "21:00" if quiet_enabled else "22:00",
                "q_end": "07:00" if quiet_enabled else "08:00",
                "q_days": json.dumps([0, 1, 2, 3, 4, 5, 6]),
                "created": _past(random.randint(30, 300)),
                "updated": _past(random.randint(0, 29)),
            })
        print(f"    Created {len(sample_users)} user notification preference records")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 4. SHARED READING LISTS + ITEMS
    #    FK: partner_id->outreach_partners, program_id->reading_programs (nullable),
    #        created_by_id/updated_by_id->users
    #    Items FK: reading_list_id->shared_reading_lists, suggested_by_id->users
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM shared_reading_lists"))
    if r.scalar() == 0:
        print("  Seeding shared_reading_lists & items...")
        op_r = await session.execute(text("SELECT id FROM outreach_partners"))
        partner_ids = [row[0] for row in op_r.fetchall()]

        if not partner_ids:
            print("    Skipping — no outreach_partners data")
        else:
            lists_data = [
                ("Kindergarten Readiness", "Core books for pre-K and kindergarten readiness skills", "Common Core ELA", '["K", "1"]', '["A", "B", "C", "D"]', '["phonics", "letters", "counting"]'),
                ("3rd Grade Summer Bridge", "Prevent summer slide with these engaging reads", "State Standards ELA 3", '["3"]', '["L", "M", "N"]', '["adventure", "animals", "humor"]'),
                ("Middle School Mysteries", "Age-appropriate mystery and detective fiction", None, '["6", "7", "8"]', '["T", "U", "V"]', '["mystery", "suspense", "detective"]'),
                ("High School AP Literature", "Supplementary reading for AP English Literature", "AP English", '["11", "12"]', '["Z"]', '["classic", "literary fiction", "essays"]'),
                ("ESL Beginning Readers", "Simple texts with visual supports for new English learners", "WIDA Level 1-2", '["3", "4", "5"]', '["E", "F", "G"]', '["esl", "picture books", "simple text"]'),
                ("Black History Month", "Celebrating Black voices and stories across all ages", None, '["K", "1", "2", "3", "4", "5"]', '["A", "B", "C", "D", "E", "F", "G", "H"]', '["history", "biography", "culture"]'),
                ("STEM Explorers", "Science and technology books that inspire curiosity", "NGSS", '["4", "5", "6"]', '["O", "P", "Q"]', '["science", "technology", "engineering"]'),
                ("Family Read-Alouds", "Perfect for reading together at home", None, '["K", "1", "2"]', '["A", "B", "C"]', '["family", "read-aloud", "bedtime"]'),
                ("Teen Mental Health", "Books addressing mental health with sensitivity and care", None, '["9", "10", "11"]', '["Y", "Z"]', '["mental health", "wellbeing", "teen issues"]'),
                ("Local Authors Spotlight", "Works by authors from our community and region", None, '["3", "4", "5", "6", "7", "8"]', '["J", "K", "L", "M", "N", "O"]', '["local", "community", "regional"]'),
            ]

            list_ids = []
            for name, desc, alignment, grades, levels, topics in lists_data:
                creator = random.choice(staff_ids)
                partner = random.choice(partner_ids)
                r2 = await session.execute(text("""
                    INSERT INTO shared_reading_lists
                        (name, description, partner_id, curriculum_alignment,
                         grade_levels, reading_levels, topics,
                         is_active, created_at, updated_at,
                         created_by_id, updated_by_id)
                    VALUES (:name, :desc, :partner, :align,
                            cast(:grades as json), cast(:levels as json), cast(:topics as json),
                            true, :created, :updated, :creator, :updater)
                    RETURNING id
                """), {
                    "name": name, "desc": desc, "partner": partner,
                    "align": alignment,
                    "grades": grades, "levels": levels, "topics": topics,
                    "created": _past(random.randint(30, 200)),
                    "updated": _past(random.randint(0, 29)),
                    "creator": creator, "updater": creator,
                })
                list_ids.append(r2.scalar())

            # Items for each list
            book_pool = [
                ("978-0-06-112008-4", "To Kill a Mockingbird", "Harper Lee", "Z", "Classic novel of justice and racial inequality in the American South"),
                ("978-0-545-01022-1", "The Hunger Games", "Suzanne Collins", "V", "Dystopian tale of survival and resistance in a controlled society"),
                ("978-0-439-02348-1", "Harry Potter and the Deathly Hallows", "J.K. Rowling", "V", "Final installment of the beloved wizarding world series"),
                ("978-0-14-028329-7", "The Outsiders", "S.E. Hinton", "T", "Coming-of-age story about class conflict and loyalty"),
                ("978-0-06-093546-7", "Where the Wild Things Are", "Maurice Sendak", "B", "A picture book classic about imagination and coming home"),
                ("978-0-06-440055-8", "Charlotte's Web", "E.B. White", "L", "Timeless story of friendship between a pig and a spider"),
                ("978-0-394-80001-1", "The Cat in the Hat", "Dr. Seuss", "A", "Rhyming beginner reader about a mischievous cat"),
                ("978-0-14-240733-0", "The Giver", "Lois Lowry", "U", "Dystopian novel about a seemingly perfect society"),
                ("978-0-440-22859-6", "A Wrinkle in Time", "Madeleine L'Engle", "R", "Sci-fi adventure through space and time"),
                ("978-0-06-025665-4", "Goodnight Moon", "Margaret Wise Brown", "A", "Beloved bedtime picture book for the youngest readers"),
                ("978-0-679-72020-1", "The Color Purple", "Alice Walker", "Z", "Pulitzer Prize-winning novel of resilience and love"),
                ("978-0-385-33348-1", "Wonder", "R.J. Palacio", "S", "Heartwarming story about choosing kindness"),
                ("978-0-14-038572-4", "Brown Bear, Brown Bear, What Do You See?", "Bill Martin Jr.", "A", "Repetitive text and bold illustrations for early readers"),
                ("978-0-06-112008-4", "Esperanza Rising", "Pam Munoz Ryan", "O", "Story of immigration, resilience, and hope"),
                ("978-0-545-13285-5", "The Lightning Thief", "Rick Riordan", "Q", "Greek mythology meets modern adventure for middle grade"),
                ("978-0-316-76948-0", "The Catcher in the Rye", "J.D. Salinger", "Z", "Coming-of-age classic exploring teenage alienation"),
                ("978-0-06-447054-0", "Because of Winn-Dixie", "Kate DiCamillo", "M", "A girl and her dog discover community in a small town"),
                ("978-0-14-130670-6", "Bud, Not Buddy", "Christopher Paul Curtis", "N", "Depression-era story of a boy searching for his father"),
                ("978-0-439-02351-1", "Holes", "Louis Sachar", "P", "Humorous adventure about fate and injustice at a boys camp"),
            ]

            item_count = 0
            for lid in list_ids:
                num_items = random.randint(3, 6)
                selected = random.sample(book_pool, min(len(book_pool), num_items))
                for isbn, title, author, level, desc in selected:
                    lib_notes = random.choice([
                        "We have 3 copies in the collection — always in demand.",
                        "Great for reluctant readers. High interest, accessible text.",
                        "Award winner — pairs well with the history curriculum.",
                        "Available in audio format too. Good for ESL students.",
                        None, None, None,
                    ])
                    teacher_notes = random.choice([
                        "Students loved this last semester. Generated great essays.",
                        "Pairs well with our unit on civil rights.",
                        "Good for literature circles — multiple perspectives.",
                        None, None, None, None,
                    ])
                    await session.execute(text("""
                        INSERT INTO shared_reading_list_items
                            (reading_list_id, isbn, title, author,
                             reading_level, description, tags,
                             librarian_notes, teacher_notes,
                             suggested_by_id, created_at)
                        VALUES (:lid, :isbn, :title, :author,
                                :level, :desc, cast(:tags as json),
                                :lib_notes, :teach_notes,
                                :suggested, :created)
                    """), {
                        "lid": lid, "isbn": isbn, "title": title, "author": author,
                        "level": level, "desc": desc,
                        "tags": json.dumps(["recommended", "vetted"]),
                        "lib_notes": lib_notes, "teach_notes": teacher_notes,
                        "suggested": random.choice(staff_ids),
                        "created": _past(random.randint(5, 150)),
                    })
                    item_count += 1
            print(f"    Created {len(list_ids)} reading lists with {item_count} items")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 5. READING ACHIEVEMENTS
    #    FK: user_id->users, program_id->reading_programs
    #    reading_programs has 0 rows — skip if no programs
    # ════════════════════════════════════════════════════════════════
    rp_r = await session.execute(text("SELECT COUNT(*) FROM reading_programs"))
    rp_count = rp_r.scalar()

    r = await session.execute(text("SELECT COUNT(*) FROM reading_achievements"))
    if r.scalar() == 0 and rp_count > 0:
        print("  Seeding reading_achievements...")
        rp_ids_r = await session.execute(text("SELECT id FROM reading_programs"))
        rp_ids = [row[0] for row in rp_ids_r.fetchall()]

        badge_defs = [
            ("starter", "Getting Started", "Logged your first reading entry"),
            ("week-warrior", "Week Warrior", "Read every day for a week"),
            ("bookworm", "Bookworm", "Read 10 books in the program"),
            ("genre-hopper", "Genre Hopper", "Read from 3 different genres"),
            ("page-master", "Page Master", "Read over 1000 pages total"),
            ("marathon-reader", "Marathon Reader", "Read for 30 days straight"),
            ("completionist", "Completionist", "Finished all program milestones"),
            ("early-finisher", "Early Finisher", "Completed the program ahead of schedule"),
        ]

        count = 0
        sample_users = random.sample(all_ids, min(len(all_ids), 30))
        for uid in sample_users:
            pid = random.choice(rp_ids)
            num_badges = random.randint(1, 3)
            for badge_id, badge_name, badge_desc in random.sample(badge_defs, min(len(badge_defs), num_badges)):
                await session.execute(text("""
                    INSERT INTO reading_achievements
                        (user_id, program_id, badge_id, badge_name,
                         badge_description, unlocked_at)
                    VALUES (:uid, :pid, :bid, :bname, :bdesc, :unlocked)
                """), {
                    "uid": uid, "pid": pid, "bid": badge_id,
                    "bname": badge_name, "bdesc": badge_desc,
                    "unlocked": _past(random.randint(1, 200)),
                })
                count += 1
        print(f"    Created {count} reading achievements")
        await session.commit()
    elif rp_count == 0:
        print("  Skipping reading_achievements — no reading_programs data")

    # ════════════════════════════════════════════════════════════════
    # 6. LEADERBOARDS + ENTRIES + HISTORY
    #    leaderboards has 0 rows — seed leaderboards first, then entries
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM leaderboards"))
    if r.scalar() == 0:
        print("  Seeding leaderboards...")
        today = datetime.now(utc).date()

        leaderboards_data = [
            ("Winter Reading Challenge 2026", "Top readers for the winter reading challenge", "reading", "seasonal", "books_read",
             date(2026, 1, 1), date(2026, 3, 31), True, True, 3, 20),
            ("Monthly Minutes Leaders", "Most reading minutes logged this month", "reading", "monthly", "minutes_read",
             today.replace(day=1), (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1), True, True, 1, 10),
            ("All-Time Top Readers", "Lifetime reading leaderboard", "reading", "all_time", "books_read",
             date(2024, 1, 1), date(2026, 12, 31), True, True, 5, 50),
            ("Book Review Champions", "Most helpful book reviews written", "community", "yearly", "reviews_written",
             date(2026, 1, 1), date(2026, 12, 31), True, True, 1, 10),
            ("Youth Summer Sprint", "Kids ages 6-12 summer reading race", "reading", "seasonal", "books_read",
             date(2025, 6, 1), date(2025, 8, 31), False, True, 2, 15),
        ]

        lb_ids = []
        for name, desc, lb_type, period, metric, start, end, active, public, min_entries, top_n in leaderboards_data:
            creator = random.choice(staff_ids)
            r2 = await session.execute(text("""
                INSERT INTO leaderboards
                    (name, description, leaderboard_type, period,
                     metric, period_start, period_end,
                     is_active, is_public, min_entries_to_rank,
                     show_top_n, created_by_id, created_at, updated_at)
                VALUES (:name, :desc, :type, :period,
                        :metric, :start, :end,
                        :active, :public, :min_entries,
                        :top_n, :creator, :created, :created)
                RETURNING id
            """), {
                "name": name, "desc": desc, "type": lb_type, "period": period,
                "metric": metric, "start": start, "end": end,
                "active": active, "public": public,
                "min_entries": min_entries, "top_n": top_n,
                "creator": creator, "created": _past(random.randint(10, 200)),
            })
            lb_ids.append(r2.scalar())
        await session.commit()

        # Seed leaderboard entries
        print("  Seeding leaderboard_entries...")
        entry_count = 0
        for lb_id in lb_ids:
            sample = random.sample(all_ids, min(len(all_ids), 30))
            scores = sorted([random.randint(5, 500) for _ in sample], reverse=True)
            for rank_idx, (uid, score) in enumerate(zip(sample, scores)):
                rank = rank_idx + 1
                total = len(sample)
                percentile = int(100 * (total - rank) / total)
                await session.execute(text("""
                    INSERT INTO leaderboard_entries
                        (leaderboard_id, user_id, rank, score,
                         percentile, is_tied, is_new_entry,
                         previous_rank, rank_change,
                         is_top_10, is_top_50, is_top_100,
                         is_champion, entries_count,
                         last_entry_at, updated_at)
                    VALUES (:lb, :uid, :rank, :score,
                            :pct, :tied, :new_entry,
                            :prev_rank, :rank_change,
                            :top10, :top50, :top100,
                            :champ, :entries,
                            :last_entry, :updated)
                """), {
                    "lb": lb_id, "uid": uid, "rank": rank, "score": score,
                    "pct": percentile, "tied": False,
                    "new_entry": random.random() < 0.3,
                    "prev_rank": rank + random.choice([-2, -1, 0, 1, 2, 3]) if rank > 1 else None,
                    "rank_change": random.choice([-2, -1, 0, 1, 2]) if rank > 1 else 0,
                    "top10": rank <= 10, "top50": rank <= 50, "top100": rank <= 100,
                    "champ": rank == 1,
                    "entries": random.randint(3, 50),
                    "last_entry": _past(random.randint(0, 30)),
                    "updated": _past(random.randint(0, 7)),
                })
                entry_count += 1
        print(f"    Created {entry_count} leaderboard entries across {len(lb_ids)} leaderboards")
        await session.commit()

        # Seed leaderboard history (weekly snapshots)
        print("  Seeding leaderboard_history...")
        hist_count = 0
        for lb_id in lb_ids:
            for weeks_back in range(1, 5):
                snap_date = _past_date(weeks_back * 7)
                snap_time = _past(weeks_back * 7)
                sample = random.sample(all_ids, min(len(all_ids), 15))
                scores = sorted([random.randint(3, 400) for _ in sample], reverse=True)
                for rank_idx, (uid, score) in enumerate(zip(sample, scores)):
                    await session.execute(text("""
                        INSERT INTO leaderboard_history
                            (leaderboard_id, user_id, rank, score,
                             snapshot_date, snapshot_time)
                        VALUES (:lb, :uid, :rank, :score, :snap_date, :snap_time)
                    """), {
                        "lb": lb_id, "uid": uid, "rank": rank_idx + 1,
                        "score": score, "snap_date": snap_date,
                        "snap_time": snap_time,
                    })
                    hist_count += 1
        print(f"    Created {hist_count} leaderboard history snapshots")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 7. PATRON TAGS
    #    FK: patron_id->users (unique with tag_id), tag_id->patron_tags_definitions,
    #        assigned_by_id->users
    # ════════════════════════════════════════════════════════════════
    ptd_r = await session.execute(text("SELECT COUNT(*) FROM patron_tags_definitions"))
    ptd_count = ptd_r.scalar()

    r = await session.execute(text("SELECT COUNT(*) FROM patron_tags"))
    if r.scalar() == 0 and ptd_count > 0:
        print("  Seeding patron_tags...")
        tag_def_r = await session.execute(text("SELECT id FROM patron_tags_definitions"))
        tag_def_ids = [row[0] for row in tag_def_r.fetchall()]

        tag_notes = [
            "Enrolled during outreach visit to senior center.",
            "Self-identified during registration.",
            "Added after conversation at reference desk.",
            "Observed pattern over several visits.",
            "Requested by patron for better service.",
            "Added during program registration.",
            "Verified through volunteer coordinator.",
            None, None, None, None, None,
        ]

        count = 0
        used = set()
        sample_patrons = random.sample(patron_ids, min(len(patron_ids), 40))
        for uid in sample_patrons:
            num_tags = random.randint(1, 3)
            for tid in random.sample(tag_def_ids, min(len(tag_def_ids), num_tags)):
                if (uid, tid) in used:
                    continue
                used.add((uid, tid))
                await session.execute(text("""
                    INSERT INTO patron_tags
                        (patron_id, tag_id, assigned_at, assigned_by_id, notes)
                    VALUES (:pid, :tid, :assigned, :assigned_by, :notes)
                """), {
                    "pid": uid, "tid": tid,
                    "assigned": _past(random.randint(5, 300)),
                    "assigned_by": random.choice(staff_ids),
                    "notes": random.choice(tag_notes),
                })
                count += 1
        print(f"    Created {count} patron tag assignments")
        await session.commit()
    elif ptd_count == 0:
        print("  Skipping patron_tags — no patron_tags_definitions data")

    # ════════════════════════════════════════════════════════════════
    # 8. PATRON NOTIFICATIONS
    #    FK: patron_id->users
    #    category is enum: HOLD_AVAILABLE, HOLD_EXPIRING, HOLD_CANCELLED,
    #        CHECKOUT_RECEIPT, DUE_DATE_REMINDER, OVERDUE_NOTICE,
    #        FINE_ASSESSED, FINE_PAID, ACCOUNT_BLOCKED, ACCOUNT_UNBLOCKED
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM patron_notifications"))
    if r.scalar() == 0:
        print("  Seeding patron_notifications...")

        notif_templates = [
            ("hold_available", "Hold Ready for Pickup",
             "Your hold on \"{title}\" is now available at the main branch. Please pick it up within 7 days.",
             "hold_ready", "/account/holds", "View Holds"),
            ("hold_expiring", "Hold Expiring Soon",
             "Your hold on \"{title}\" will expire in 2 days. Please pick it up before it's returned to the shelf.",
             "hold_expiring", "/account/holds", "View Holds"),
            ("hold_cancelled", "Hold Cancelled",
             "Your hold on \"{title}\" has been cancelled because it was not picked up within the hold period.",
             "hold_cancelled", "/account/holds", "View Holds"),
            ("checkout_receipt", "Checkout Confirmation",
             "You checked out \"{title}\". It is due back on {due_date}. Enjoy your reading!",
             "checkout", "/account/checkouts", "View Checkouts"),
            ("due_date_reminder", "Item Due Soon",
             "Reminder: \"{title}\" is due back in 3 days. You can renew online or return it to any branch.",
             "due_reminder", "/account/checkouts", "Renew Items"),
            ("overdue_notice", "Overdue Notice",
             "\"{title}\" is now 7 days overdue. Please return it as soon as possible to avoid additional fees.",
             "overdue", "/account/checkouts", "View Overdue"),
            ("fine_assessed", "Fine Notice",
             "A fine of $2.50 has been assessed on your account for overdue item \"{title}\".",
             "fine_assessed", "/account/fines", "View Fines"),
            ("fine_paid", "Payment Received",
             "Thank you! Your payment of $5.00 has been applied to your account.",
             "fine_paid", "/account/fines", "View Account"),
        ]

        item_titles = [
            "The Great Gatsby", "Where the Crawdads Sing", "Atomic Habits",
            "Project Hail Mary", "The Midnight Library", "Educated",
            "The House in the Cerulean Sea", "Circe", "Becoming",
            "The Silent Patient", "Klara and the Sun", "Piranesi",
        ]

        count = 0
        sample_patrons = random.sample(patron_ids, min(len(patron_ids), 35))
        for uid in sample_patrons:
            num_notifs = random.randint(1, 3)
            for _ in range(num_notifs):
                if count >= 50:
                    break
                cat, title_tmpl, msg_tmpl, event_type, url, label = random.choice(notif_templates)
                item_title = random.choice(item_titles)
                msg = msg_tmpl.replace("{title}", item_title).replace("{due_date}", str(_past_date(-14)))

                days_ago = random.randint(0, 90)
                created = _past(days_ago)
                is_read = random.random() < 0.6
                is_dismissed = is_read and random.random() < 0.3

                await session.execute(text("""
                    INSERT INTO patron_notifications
                        (patron_id, category, title, message,
                         source_event_type, source_event_id,
                         related_item_title, action_url, action_label,
                         is_read, read_at, is_dismissed, dismissed_at,
                         created_at, updated_at)
                    VALUES (:pid, :cat, :title, :msg,
                            :event_type, :event_id,
                            :item_title, :url, :label,
                            :is_read, :read_at, :dismissed, :dismissed_at,
                            :created, :updated)
                """), {
                    "pid": uid, "cat": cat, "title": title_tmpl, "msg": msg,
                    "event_type": event_type,
                    "event_id": str(random.randint(1000, 9999)),
                    "item_title": item_title, "url": url, "label": label,
                    "is_read": is_read,
                    "read_at": created + timedelta(hours=random.randint(1, 48)) if is_read else None,
                    "dismissed": is_dismissed,
                    "dismissed_at": created + timedelta(hours=random.randint(2, 72)) if is_dismissed else None,
                    "created": created,
                    "updated": created + timedelta(hours=random.randint(0, 24)),
                })
                count += 1
            if count >= 50:
                break
        print(f"    Created {count} patron notifications")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 9. DAILY WINS + DAILY REMINDERS
    #    daily_wins FK: staff_id->users, session_id->shift_checklist_sessions (nullable)
    #    daily_wins.organization_id has no FK constraint — use 1
    #    daily_reminders FK: user_id->users, antidote_id->perfectionism_antidotes
    #    perfectionism_antidotes has 0 rows — skip daily_reminders if empty
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM daily_wins"))
    if r.scalar() == 0:
        print("  Seeding daily_wins...")
        wins_data = [
            "Helped a patron find their first job application online. They were so grateful they teared up.",
            "A regular patron brought in homemade cookies to thank us for the reading program.",
            "Successfully fixed the self-checkout printer mid-rush without anyone noticing.",
            "A child who was terrified of the library six months ago just got their own card today!",
            "Resolved a complicated interlibrary loan that three other libraries had given up on.",
            "Finished weeding the 600s section — looks amazing and browsable now.",
            "Ran storytime solo when my colleague called in sick. Kids loved the improv puppet show.",
            "A teen thanked me for recommending a book that 'finally made reading cool.'",
            "Caught a cataloging error that had been misfiling items for months. Fixed 47 records.",
            "Organized a last-minute author visit when our booked speaker cancelled. Full house!",
            "Helped an elderly patron set up their first email account. They sent a message to their grandchild.",
            "The summer reading kickoff event had record attendance — 142 kids signed up!",
            "Trained a new volunteer who shelved an entire cart perfectly on the first try.",
            "A patron returned a book 3 years overdue and paid the fine with a smile and an apology.",
            "Finished the grant application for new maker space equipment. Fingers crossed!",
            "Mediated a noise dispute in the study area calmly and both patrons thanked me after.",
            "Found a rare local history document a genealogy researcher had been hunting for years.",
            "The book club I started now has 15 regular members. We read our 20th book together.",
            "Reorganized the staff break room. Morale is measurably up.",
            "A patron told me our library is the safest place they know. That's why we do this.",
        ]
        emojis = ["star", "heart", "sparkles", "trophy", "rocket", "rainbow", "sun", "clap", "muscle", "book"]
        for i, desc in enumerate(wins_data):
            await session.execute(text("""
                INSERT INTO daily_wins
                    (organization_id, staff_id, win_description,
                     win_date, is_public, celebration_emoji)
                VALUES (1, :staff, :desc, :win_date, :public, :emoji)
            """), {
                "staff": random.choice(staff_ids),
                "desc": desc,
                "win_date": _past(random.randint(0, 120)),
                "public": random.random() < 0.7,
                "emoji": random.choice(emojis),
            })
        print(f"    Created {len(wins_data)} daily wins")
        await session.commit()

    # Daily reminders — depends on perfectionism_antidotes having data
    pa_r = await session.execute(text("SELECT COUNT(*) FROM perfectionism_antidotes"))
    pa_count = pa_r.scalar()

    r = await session.execute(text("SELECT COUNT(*) FROM daily_reminders"))
    if r.scalar() == 0 and pa_count > 0:
        print("  Seeding daily_reminders...")
        pa_ids_r = await session.execute(text("SELECT id FROM perfectionism_antidotes"))
        pa_ids = [row[0] for row in pa_ids_r.fetchall()]

        reminder_texts = [
            "Done is better than perfect. Ship it!",
            "You've spent enough time on this. Move on to the next task.",
            "Good enough is genuinely good enough.",
            "Remember: 80% of the value comes from 20% of the effort.",
            "Take imperfect action rather than no action at all.",
            "You've learned enough to start. Begin now.",
            "Celebrate what you've accomplished so far today.",
            "Balance is more important than perfection.",
            "Give yourself grace. You're human.",
            "You have permission to be imperfect today.",
        ]

        count = 0
        sample_staff = random.sample(staff_ids, min(len(staff_ids), 10))
        for uid in sample_staff:
            aid = random.choice(pa_ids)
            reminder_date = datetime.now(utc).replace(tzinfo=None) - timedelta(days=random.randint(0, 60))
            was_ack = random.random() < 0.6
            await session.execute(text("""
                INSERT INTO daily_reminders
                    (user_id, antidote_id, reminder_date, reminder_text,
                     was_acknowledged, acknowledged_at, user_reflection, created_at)
                VALUES (:uid, :aid, :rdate, :rtext,
                        :ack, :ack_at, :reflection, :created)
            """), {
                "uid": uid, "aid": aid,
                "rdate": reminder_date,
                "rtext": random.choice(reminder_texts),
                "ack": was_ack,
                "ack_at": reminder_date + timedelta(hours=random.randint(1, 8)) if was_ack else None,
                "reflection": random.choice([
                    "This helped me let go of rewriting that email for the 5th time.",
                    "Needed this today. Stopped fussing with the display and it looks fine.",
                    "Good reminder. I finished the report and moved on.",
                    None, None, None,
                ]) if was_ack else None,
                "created": reminder_date - timedelta(hours=1),
            })
            count += 1
        print(f"    Created {count} daily reminders")
        await session.commit()
    elif pa_count == 0:
        print("  Skipping daily_reminders — no perfectionism_antidotes data")

    # ════════════════════════════════════════════════════════════════
    # 10. JOY JAR ENTRIES
    #     FK: user_id->users (nullable)
    #     organization_id has no FK — use 1
    #     mood enum: DELIGHTFUL, GRATEFUL, INSPIRING, FUNNY, HEARTWARMING
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM joy_jar_entries"))
    if r.scalar() == 0:
        print("  Seeding joy_jar_entries...")
        entries = [
            ("A five-year-old asked if Ernie the cat wrote any of the books. Made my whole day.", "FUNNY", False),
            ("Overheard a grandma and grandson reading together in the children's section. Pure magic.", "HEARTWARMING", False),
            ("A patron returned a book with a handwritten thank-you note tucked inside.", "GRATEFUL", False),
            ("The teen advisory board surprised us with a thank-you poster for National Library Week.", "DELIGHTFUL", False),
            ("A regular patron brought her brand new baby to 'introduce them to the library.'", "HEARTWARMING", False),
            ("During a power outage, patrons stayed to read by the emergency lights. Dedication!", "FUNNY", True),
            ("A homeschool family told us our programs are the highlight of their week.", "INSPIRING", False),
            ("Found a patron's lost wedding ring wedged between the couch cushions. She cried happy tears.", "HEARTWARMING", False),
            ("A shy teen finally joined the D&D group after months of watching. They were the best player.", "INSPIRING", False),
            ("Someone anonymously paid off all the overdue fines for children's accounts. Angel among us.", "GRATEFUL", True),
            ("Two patrons who met at book club just announced their engagement!", "DELIGHTFUL", False),
            ("A veteran told us the library is the first place that felt like home after deployment.", "INSPIRING", False),
            ("The seed library garden produced enough tomatoes to share with the food pantry next door.", "GRATEFUL", False),
            ("A patron's kid drew a picture of the library and titled it 'My Favorite Place.'", "HEARTWARMING", False),
            ("Our summer reading program had a 94% completion rate this year. Best ever!", "DELIGHTFUL", False),
        ]
        for entry_text, mood, is_anon in entries:
            uid = None if is_anon else random.choice(all_ids)
            await session.execute(text("""
                INSERT INTO joy_jar_entries
                    (organization_id, user_id, entry_text,
                     is_anonymous, mood, created_at)
                VALUES (1, :uid, :text, :anon, :mood, :created)
            """), {
                "uid": uid, "text": entry_text,
                "anon": is_anon, "mood": mood,
                "created": _past(random.randint(1, 180)),
            })
        print(f"    Created {len(entries)} joy jar entries")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ════════════════════════════════════════════════════════════════
    seq_tables = [
        "patron_reading_history", "patron_preferences",
        "notification_preferences", "user_notification_preferences",
        "shared_reading_lists", "shared_reading_list_items",
        "reading_achievements",
        "leaderboards", "leaderboard_entries", "leaderboard_history",
        "patron_tags", "patron_notifications",
        "daily_wins", "daily_reminders", "joy_jar_entries",
    ]
    for table in seq_tables:
        try:
            async with session.begin_nested():
                await session.execute(text(
                    f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                ))
        except SQLAlchemyError:
            pass  # Some tables might not have standard sequence naming

    await session.commit()
    print("  Patron batch seeding complete!")
    return True
