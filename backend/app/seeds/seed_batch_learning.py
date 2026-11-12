# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import random
import datetime as _dt
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


def _past_date(days_ago: int) -> date:
    return (datetime.now(utc) - timedelta(days=days_ago)).date()


def _future_date(days_ahead: int) -> date:
    return (datetime.now(utc) + timedelta(days=days_ahead)).date()


async def seed_batch_learning(session: AsyncSession) -> bool:

    # ── Grab reusable IDs ──────────────────────────────────────────
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]

    items_r = await session.execute(text("SELECT id FROM catalog_items"))
    catalog_ids = [r[0] for r in items_r.fetchall()]

    branch_r = await session.execute(text("SELECT id FROM branches"))
    branch_ids = [r[0] for r in branch_r.fetchall()]

    course_r = await session.execute(text("SELECT id FROM courses"))
    course_ids = [r[0] for r in course_r.fetchall()]

    module_r = await session.execute(text("SELECT id FROM modules"))
    module_ids = [r[0] for r in module_r.fetchall()]

    lesson_r = await session.execute(text("SELECT id FROM lessons"))
    lesson_ids = [r[0] for r in lesson_r.fetchall()]

    program_r = await session.execute(text("SELECT id FROM programs"))
    program_ids = [r[0] for r in program_r.fetchall()]

    now = datetime.now(utc)

    # ════════════════════════════════════════════════════════════════
    # 1. LEARNING ASSESSMENTS + QUESTIONS + ATTEMPTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM learning_assessments"))
    if r.scalar() == 0:
        print("  Seeding learning_assessments, questions, attempts...")

        assessments = [
            ("Library Digital Literacy Quiz", "Test your knowledge of library digital resources", "quiz",
             30, 70.0, 3, True, True, 50, "Basic quiz on using library digital tools"),
            ("Catalog Search Skills Exam", "Comprehensive exam on catalog search techniques", "exam",
             60, 75.0, 2, False, True, 100, "Covers boolean search, filters, and advanced features"),
            ("Reference Interview Practical", "Practical assessment of reference interview skills", "practical",
             45, 80.0, 1, False, True, 150, "Role-play based assessment of patron interaction"),
            ("Information Literacy Self-Assessment", "Evaluate your own information literacy skills", "self_assessment",
             20, 60.0, 5, True, True, 25, "Honest self-reflection on research abilities"),
        ]
        assessment_ids = []
        for title, desc, atype, time_limit, passing, max_att, randomize, published, xp, instructions in assessments:
            cid = random.choice(course_ids) if course_ids else None
            mid = random.choice(module_ids) if module_ids else None
            r2 = await session.execute(text("""
                INSERT INTO learning_assessments
                    (course_id, module_id, title, description, assessment_type,
                     time_limit_minutes, passing_score, max_attempts, randomize_questions,
                     show_correct_answers, is_published, xp_reward, instructions,
                     resources_allowed, created_at, updated_at)
                VALUES (:cid, :mid, :title, :desc, :atype,
                        :time_limit, :passing, :max_att, :randomize,
                        true, :published, :xp, :instructions,
                        cast(:resources as jsonb), :now, :now)
                RETURNING id
            """), {
                "cid": cid, "mid": mid, "title": title, "desc": desc, "atype": atype,
                "time_limit": time_limit, "passing": passing, "max_att": max_att,
                "randomize": randomize, "published": published, "xp": xp,
                "instructions": instructions,
                "resources": json.dumps(["notes"]),
                "now": now,
            })
            assessment_ids.append(r2.scalar())

        # Questions for each assessment (5-8 per assessment)
        question_bank = [
            ("What does the acronym OPAC stand for?", "multiple_choice",
             json.dumps([{"text": "Online Public Access Catalog", "is_correct": True},
                         {"text": "Open Protocol Archive Center", "is_correct": False},
                         {"text": "Optical Processing And Counting", "is_correct": False}]),
             1.0, "easy", "OPAC = Online Public Access Catalog"),
            ("Boolean AND narrows search results.", "true_false",
             json.dumps({"answer": True}), 1.0, "easy", "AND requires all terms be present, narrowing results"),
            ("What is a controlled vocabulary?", "short_answer",
             json.dumps({"keywords": ["standardized", "terms", "subject headings"]}),
             2.0, "medium", "A controlled vocabulary uses standardized terms for consistent indexing"),
            ("Which database is best for medical research?", "multiple_choice",
             json.dumps([{"text": "PubMed", "is_correct": True},
                         {"text": "ERIC", "is_correct": False},
                         {"text": "JSTOR", "is_correct": False}]),
             1.0, "medium", "PubMed is the primary database for biomedical literature"),
            ("Explain the difference between primary and secondary sources.", "essay",
             json.dumps({"rubric": "Must mention original vs. analysis"}),
             3.0, "hard", "Primary sources are original materials; secondary analyze or interpret them"),
            ("The Dewey Decimal System organizes by subject.", "true_false",
             json.dumps({"answer": True}), 1.0, "easy", "DDC organizes knowledge into 10 main classes by subject"),
            ("Match the database to its primary focus.", "matching",
             json.dumps({"pairs": [{"left": "ERIC", "right": "Education"},
                                   {"left": "PubMed", "right": "Medicine"}]}),
             2.0, "medium", "ERIC covers education research, PubMed covers biomedicine"),
            ("An ISBN uniquely identifies a ____.", "fill_blank",
             json.dumps({"answer": "book", "alternatives": ["publication", "edition"]}),
             1.0, "easy", "ISBN = International Standard Book Number"),
        ]

        question_ids = []
        for aid in assessment_ids:
            num_q = random.randint(5, 8)
            selected = random.sample(question_bank, min(num_q, len(question_bank)))
            for order, (qtext, qtype, options_or_answer, points, diff, explanation) in enumerate(selected):
                if qtype == "multiple_choice" or qtype == "matching":
                    opts = options_or_answer
                    correct = None
                else:
                    opts = None
                    correct = options_or_answer
                r2 = await session.execute(text("""
                    INSERT INTO learning_assessment_questions
                        (assessment_id, question_text, question_type, options, correct_answer,
                         points, difficulty, explanation, sort_order, created_at, updated_at)
                    VALUES (:aid, :qtext, :qtype, cast(:opts as jsonb), cast(:correct as jsonb),
                            :points, :diff, :explanation, :sort_order, :now, :now)
                    RETURNING id
                """), {
                    "aid": aid, "qtext": qtext, "qtype": qtype,
                    "opts": opts, "correct": correct,
                    "points": points, "diff": diff, "explanation": explanation,
                    "sort_order": order, "now": now,
                })
                question_ids.append(r2.scalar())

        # Attempts (~20)
        attempt_count = 0
        for _ in range(20):
            uid = random.choice(all_ids)
            aid = random.choice(assessment_ids)
            score = round(random.uniform(40, 100), 1)
            max_score = 100.0
            pct = score
            passed = score >= 70.0
            started = _past(random.randint(1, 90))
            submitted = started + timedelta(minutes=random.randint(10, 55))
            await session.execute(text("""
                INSERT INTO learning_assessment_attempts
                    (user_id, assessment_id, attempt_number, started_at, submitted_at,
                     time_taken_minutes, score, max_score, percentage, passed,
                     answers, is_completed, is_graded, feedback, created_at, updated_at)
                VALUES (:uid, :aid, :att_num, :started, :submitted,
                        :time_taken, :score, :max_score, :pct, :passed,
                        cast(:answers as jsonb), true, true, :feedback, :now, :now)
            """), {
                "uid": uid, "aid": aid, "att_num": random.randint(1, 3),
                "started": started, "submitted": submitted,
                "time_taken": random.randint(10, 55),
                "score": score, "max_score": max_score, "pct": pct, "passed": passed,
                "answers": json.dumps([]),
                "feedback": "Good effort!" if passed else "Review the material and try again.",
                "now": now,
            })
            attempt_count += 1

        print(f"    Created {len(assessment_ids)} assessments, {len(question_ids)} questions, {attempt_count} attempts")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 2. LEARNING BADGES + USER BADGES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM learning_badges"))
    if r.scalar() == 0:
        print("  Seeding learning_badges & learning_user_badges...")

        badges = [
            ("First Steps", "Completed your first lesson", "achievement", "common", "#10B981",
             json.dumps({"lessons_completed": 1}), 10, False, "onboarding"),
            ("Quick Learner", "Completed 5 lessons in one day", "achievement", "uncommon", "#3B82F6",
             json.dumps({"lessons_per_day": 5}), 25, False, "productivity"),
            ("Knowledge Seeker", "Enrolled in 3 courses", "milestone", "common", "#6366F1",
             json.dumps({"enrollments": 3}), 30, False, "exploration"),
            ("Quiz Master", "Scored 100% on any quiz", "achievement", "rare", "#F59E0B",
             json.dumps({"perfect_quiz": True}), 50, False, "assessment"),
            ("Week Warrior", "Maintained a 7-day learning streak", "streak", "uncommon", "#EC4899",
             json.dumps({"streak_days": 7}), 40, False, "consistency"),
            ("Month Maven", "Maintained a 30-day learning streak", "streak", "epic", "#8B5CF6",
             json.dumps({"streak_days": 30}), 150, False, "consistency"),
            ("Community Contributor", "Posted 5 discussion responses", "community", "common", "#14B8A6",
             json.dumps({"discussion_posts": 5}), 20, False, "community"),
            ("Deep Diver", "Spent 10+ hours on a single course", "skill", "rare", "#F97316",
             json.dumps({"course_hours": 10}), 75, False, "dedication"),
            ("Pathfinder", "Completed an entire learning path", "milestone", "epic", "#A855F7",
             json.dumps({"path_completed": True}), 200, True, "achievement"),
            ("Hidden Gem", "Found the secret library easter egg", "special", "legendary", "#EF4444",
             json.dumps({"easter_egg": "library_cat"}), 500, True, "secret"),
        ]

        badge_ids = []
        for name, desc, btype, rarity, color, criteria, xp, secret, category in badges:
            r2 = await session.execute(text("""
                INSERT INTO learning_badges
                    (name, description, badge_type, rarity, color_hex, criteria, xp_value,
                     is_active, is_secret, current_awards, category, created_at, updated_at)
                VALUES (:name, :desc, :btype, :rarity, :color, cast(:criteria as jsonb), :xp,
                        true, :secret, 0, :category, :now, :now)
                RETURNING id
            """), {
                "name": name, "desc": desc, "btype": btype, "rarity": rarity,
                "color": color, "criteria": criteria, "xp": xp,
                "secret": secret, "category": category, "now": now,
            })
            badge_ids.append(r2.scalar())

        # User badges (~30)
        ub_count = 0
        used_ub = set()
        for _ in range(30):
            uid = random.choice(all_ids)
            bid = random.choice(badge_ids)
            earned = _past(random.randint(1, 180))
            key = (uid, bid, earned.isoformat()[:10])
            if key in used_ub:
                continue
            used_ub.add(key)
            await session.execute(text("""
                INSERT INTO learning_user_badges
                    (user_id, badge_id, earned_at, earned_for, is_showcased, created_at, updated_at)
                VALUES (:uid, :bid, :earned, :earned_for, :showcased, :now, :now)
            """), {
                "uid": uid, "bid": bid, "earned": earned,
                "earned_for": "Automatic award for meeting criteria",
                "showcased": random.choice([True, False]),
                "now": now,
            })
            ub_count += 1

        print(f"    Created {len(badge_ids)} badges, {ub_count} user badges")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 3. LEARNING OBJECTIVES + MILESTONES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM learning_milestones"))
    if r.scalar() == 0:
        print("  Seeding learning_milestones & learning_objectives...")

        # Fetch badge_ids for milestones
        badge_r = await session.execute(text("SELECT id FROM learning_badges LIMIT 5"))
        lb_ids = [r[0] for r in badge_r.fetchall()]

        milestones_data = [
            ("Complete First Course", "Finish any course from start to end", "course_completion",
             json.dumps({"courses_completed": 1}), 50, True, 0),
            ("Digital Skills Proficiency", "Master the digital skills learning path", "skill_mastery",
             json.dumps({"skill": "digital_literacy", "level": 5}), 100, True, 1),
            ("Earn 500 XP", "Accumulate 500 experience points", "xp_threshold",
             json.dumps({"min_xp": 500}), 75, True, 2),
            ("Module Marathon", "Complete 10 modules", "module_completion",
             json.dumps({"modules_completed": 10}), 60, True, 3),
            ("7-Day Streak", "Learn something every day for a week", "streak_achievement",
             json.dumps({"streak_days": 7}), 40, True, 4),
            ("Pass First Assessment", "Score passing marks on any formal assessment", "assessment_passed",
             json.dumps({"assessments_passed": 1}), 80, True, 5),
            ("Library Explorer", "Complete courses in 3 different categories", "custom",
             json.dumps({"unique_categories": 3}), 90, True, 6),
            ("Research Pro", "Complete the advanced research methodology course", "course_completion",
             json.dumps({"course_title": "Advanced Research Methods"}), 120, False, 7),
            ("Team Learner", "Complete 5 group activities", "custom",
             json.dumps({"group_activities": 5}), 70, True, 8),
            ("Knowledge Builder", "Complete all beginner courses", "course_completion",
             json.dumps({"difficulty": "beginner", "all": True}), 150, True, 9),
            ("Streak Legend", "Maintain a 30-day learning streak", "streak_achievement",
             json.dumps({"streak_days": 30}), 200, False, 10),
            ("Assessment Ace", "Score 90%+ on 5 assessments", "assessment_passed",
             json.dumps({"assessments_90plus": 5}), 175, True, 11),
            ("Earn 2000 XP", "Accumulate 2000 experience points", "xp_threshold",
             json.dumps({"min_xp": 2000}), 100, True, 12),
            ("Catalog Mastery", "Complete the catalog search course and assessment", "skill_mastery",
             json.dumps({"skill": "catalog_search", "level": 5}), 110, True, 13),
            ("Community Leader", "Help 10 other learners in discussions", "custom",
             json.dumps({"helpful_posts": 10}), 130, True, 14),
        ]

        milestone_ids = []
        for title, desc, mtype, criteria, xp, active, sort in milestones_data:
            bid = random.choice(lb_ids) if lb_ids and random.random() > 0.5 else None
            r2 = await session.execute(text("""
                INSERT INTO learning_milestones
                    (title, description, milestone_type, criteria, xp_reward, badge_id,
                     is_active, is_hidden, sort_order, created_at, updated_at)
                VALUES (:title, :desc, :mtype, cast(:criteria as jsonb), :xp, :bid,
                        :active, false, :sort, :now, :now)
                RETURNING id
            """), {
                "title": title, "desc": desc, "mtype": mtype,
                "criteria": criteria, "xp": xp, "bid": bid,
                "active": active, "sort": sort, "now": now,
            })
            milestone_ids.append(r2.scalar())

        # Learning objectives (10-12)
        objective_data = [
            ("Learn basic catalog searching", "Master search operators and filters", "in_progress", 45),
            ("Complete digital literacy path", "Finish all digital literacy modules", "not_started", 0),
            ("Improve reference interview skills", "Practice and assess patron interaction", "in_progress", 70),
            ("Earn the Quiz Master badge", "Score 100% on any quiz assessment", "not_started", 0),
            ("Build a 14-day streak", "Consistent daily learning for two weeks", "in_progress", 50),
            ("Complete 5 courses", "Finish five full courses to broaden skills", "in_progress", 60),
            ("Master advanced search", "Learn boolean operators and proximity search", "completed", 100),
            ("Achieve 1000 XP", "Earn experience points through various activities", "in_progress", 35),
            ("Study collection development", "Complete collection development training", "not_started", 0),
            ("Finish community engagement module", "Learn about outreach and programming", "in_progress", 80),
            ("Pass the research methods exam", "Score 80%+ on the research assessment", "not_started", 0),
            ("Read about intellectual freedom", "Study ALA intellectual freedom guidelines", "completed", 100),
        ]

        for title, desc, status, progress in objective_data:
            uid = random.choice(all_ids)
            mid = random.choice(milestone_ids) if milestone_ids and random.random() > 0.4 else None
            started = _past(random.randint(5, 120)) if status != "not_started" else None
            completed = _past(random.randint(1, 30)) if status == "completed" else None
            target = _future_date(random.randint(30, 180)) if status != "completed" else _past_date(random.randint(1, 10))
            await session.execute(text("""
                INSERT INTO learning_objectives
                    (user_id, milestone_id, title, description, status,
                     target_completion_date, started_at, completed_at,
                     progress_percentage, progress_notes, course_ids, skill_ids,
                     created_at, updated_at)
                VALUES (:uid, :mid, :title, :desc, :status,
                        :target, :started, :completed,
                        :progress, cast(:notes as jsonb), cast(:cids as jsonb), cast(:sids as jsonb),
                        :now, :now)
            """), {
                "uid": uid, "mid": mid, "title": title, "desc": desc, "status": status,
                "target": target, "started": started, "completed": completed,
                "progress": progress,
                "notes": json.dumps([]),
                "cids": json.dumps([]),
                "sids": json.dumps([]),
                "now": now,
            })

        print(f"    Created {len(milestones_data)} milestones, {len(objective_data)} objectives")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 4. LEARNING LABS + LAB COMPLETIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM learning_labs"))
    if r.scalar() == 0:
        print("  Seeding learning_labs & lab_completions...")

        labs = [
            ("rag-basics", "RAG Fundamentals Lab", "Learn to build a basic Retrieval Augmented Generation pipeline",
             json.dumps(["Set up vector store", "Index documents", "Query and retrieve", "Generate responses"]),
             "rag", 45, 75, True, 0),
            ("hallucination-detection", "Spotting AI Hallucinations", "Practice identifying when AI generates incorrect information",
             json.dumps(["Review AI outputs", "Cross-reference sources", "Flag inaccuracies", "Write corrections"]),
             "hallucination", 30, 50, True, 1),
            ("prompt-engineering", "Prompt Engineering Workshop", "Master the art of crafting effective AI prompts",
             json.dumps(["Basic prompts", "Chain-of-thought", "Few-shot examples", "System prompts", "Evaluation"]),
             "prompt", 60, 100, True, 2),
            ("agent-basics", "Building AI Agents", "Create a simple autonomous AI agent for library tasks",
             json.dumps(["Define tools", "Set up agent loop", "Implement memory", "Test with scenarios"]),
             "agent", 90, 150, True, 3),
            ("search-optimization", "Search Query Optimization Lab", "Optimize library search queries using AI techniques",
             json.dumps(["Analyze query patterns", "Implement query expansion", "Test relevance scoring"]),
             "prompt", 40, 60, False, 4),
        ]

        lab_ids = []
        for slug, title, desc, instructions, ltype, est_min, xp, published, sort in labs:
            r2 = await session.execute(text("""
                INSERT INTO learning_labs
                    (slug, title, description, instructions, lab_type,
                     estimated_minutes, xp_reward, is_published, sort_order)
                VALUES (:slug, :title, :desc, cast(:instructions as jsonb), :ltype,
                        :est_min, :xp, :published, :sort)
                RETURNING id
            """), {
                "slug": slug, "title": title, "desc": desc,
                "instructions": instructions, "ltype": ltype,
                "est_min": est_min, "xp": xp, "published": published, "sort": sort,
            })
            lab_ids.append(r2.scalar())

        # Lab completions (~20)
        comp_count = 0
        used_lc = set()
        for _ in range(20):
            uid = random.choice(all_ids)
            lid = random.choice(lab_ids)
            if (uid, lid) in used_lc:
                continue
            used_lc.add((uid, lid))
            await session.execute(text("""
                INSERT INTO lab_completions
                    (user_id, lab_id, completed_at, results)
                VALUES (:uid, :lid, :completed, cast(:results as jsonb))
            """), {
                "uid": uid, "lid": lid,
                "completed": _past(random.randint(1, 90)),
                "results": json.dumps({"score": random.randint(60, 100), "time_minutes": random.randint(15, 90)}),
            })
            comp_count += 1

        print(f"    Created {len(lab_ids)} labs, {comp_count} completions")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 5. LEARNING STREAKS + STUDY SESSIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM learning_streaks"))
    if r.scalar() == 0:
        print("  Seeding learning_streaks & learning_study_sessions...")

        # Streaks (~30, unique per user)
        streak_count = 0
        used_streak_users = set()
        for uid in random.sample(all_ids, min(len(all_ids), 30)):
            if uid in used_streak_users:
                continue
            used_streak_users.add(uid)
            current = random.randint(0, 21)
            longest = max(current, random.randint(3, 45))
            last_date = _past_date(random.randint(0, 7)) if current > 0 else _past_date(random.randint(8, 60))
            await session.execute(text("""
                INSERT INTO learning_streaks
                    (user_id, current_streak, longest_streak, last_activity_date,
                     freeze_count, max_freezes, streak_history, total_active_days,
                     created_at, updated_at)
                VALUES (:uid, :current, :longest, :last_date,
                        :freezes, 3, cast(:history as jsonb), :active_days,
                        :now, :now)
            """), {
                "uid": uid, "current": current, "longest": longest,
                "last_date": last_date,
                "freezes": random.randint(0, 2),
                "history": json.dumps([]),
                "active_days": random.randint(5, 120),
                "now": now,
            })
            streak_count += 1

        # Study sessions (~40)
        session_count = 0
        for _ in range(40):
            uid = random.choice(all_ids)
            s_date = _past_date(random.randint(0, 60))
            started = datetime(s_date.year, s_date.month, s_date.day,
                               random.randint(8, 20), random.randint(0, 59), tzinfo=utc)
            duration = random.randint(10, 120)
            ended = started + timedelta(minutes=duration)
            cid = random.choice(course_ids) if course_ids else None
            await session.execute(text("""
                INSERT INTO learning_study_sessions
                    (user_id, session_date, started_at, ended_at, duration_minutes,
                     course_id, lesson_ids, lessons_completed, quizzes_taken, xp_earned,
                     focus_mode_enabled, break_count, activities, created_at, updated_at)
                VALUES (:uid, :s_date, :started, :ended, :duration,
                        :cid, cast(:lids as jsonb), :lessons, :quizzes, :xp,
                        :focus, :breaks, cast(:activities as jsonb), :now, :now)
            """), {
                "uid": uid, "s_date": s_date, "started": started, "ended": ended,
                "duration": duration, "cid": cid,
                "lids": json.dumps([]),
                "lessons": random.randint(0, 5),
                "quizzes": random.randint(0, 2),
                "xp": random.randint(5, 80),
                "focus": random.choice([True, False]),
                "breaks": random.randint(0, 3),
                "activities": json.dumps([]),
                "now": now,
            })
            session_count += 1

        print(f"    Created {streak_count} streaks, {session_count} study sessions")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 6. USER INTERESTS + CHECKPOINTS + REPORTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM learning_user_interests"))
    if r.scalar() == 0:
        print("  Seeding learning_user_interests, checkpoints, reports...")

        # User interests
        topics = ["Digital Literacy", "Reference Services", "Children's Programming",
                  "Collection Development", "Cataloging", "Community Outreach",
                  "Technology", "Makerspace Skills", "Genealogy Research",
                  "Information Literacy", "Adult Programming", "YA Services"]
        interest_count = 0
        used_int = set()
        for uid in random.sample(all_ids, min(len(all_ids), 40)):
            for topic in random.sample(topics, random.randint(1, 4)):
                if (uid, topic) in used_int:
                    continue
                used_int.add((uid, topic))
                await session.execute(text("""
                    INSERT INTO learning_user_interests
                        (user_id, topic, interest_level, source, confidence_score,
                         related_skills, related_courses, engagement_count,
                         created_at, updated_at)
                    VALUES (:uid, :topic, :level, :source, :conf,
                            cast(:skills as jsonb), cast(:courses as jsonb), :eng_count,
                            :now, :now)
                """), {
                    "uid": uid, "topic": topic,
                    "level": random.choice(["low", "medium", "high", "very_high"]),
                    "source": random.choice(["explicit", "inferred", "behavioral"]),
                    "conf": round(random.uniform(0.3, 1.0), 2),
                    "skills": json.dumps([]),
                    "courses": json.dumps([]),
                    "eng_count": random.randint(0, 20),
                    "now": now,
                })
                interest_count += 1

        # Progress checkpoints (need course_ids & module_ids)
        checkpoint_count = 0
        checkpoint_ids = []
        if course_ids:
            cp_data = [
                ("Introduction Quiz", "Quick check on introductory material", "quiz", True, 10),
                ("Mid-Module Reflection", "Reflect on what you have learned so far", "reflection", False, 5),
                ("Peer Review Exercise", "Review a peer's work and provide feedback", "peer_review", False, 15),
                ("Module Assignment", "Complete the hands-on assignment", "assignment", True, 25),
                ("Final Project", "Submit your capstone project", "project", True, 50),
            ]
            for title, desc, cptype, required, xp in cp_data:
                cid = random.choice(course_ids)
                mid = random.choice(module_ids) if module_ids else None
                r2 = await session.execute(text("""
                    INSERT INTO learning_progress_checkpoints
                        (course_id, module_id, title, description, checkpoint_type,
                         sort_order, is_required, passing_criteria, xp_reward,
                         created_at, updated_at)
                    VALUES (:cid, :mid, :title, :desc, :cptype,
                            :sort, :required, cast(:criteria as jsonb), :xp,
                            :now, :now)
                    RETURNING id
                """), {
                    "cid": cid, "mid": mid, "title": title, "desc": desc,
                    "cptype": cptype, "sort": checkpoint_count,
                    "required": required,
                    "criteria": json.dumps({"min_score": 70}),
                    "xp": xp, "now": now,
                })
                checkpoint_ids.append(r2.scalar())
                checkpoint_count += 1

            # User checkpoints
            ucp_count = 0
            used_ucp = set()
            for _ in range(15):
                uid = random.choice(all_ids)
                cpid = random.choice(checkpoint_ids) if checkpoint_ids else None
                if cpid is None:
                    continue
                if (uid, cpid) in used_ucp:
                    continue
                used_ucp.add((uid, cpid))
                completed = random.choice([True, False])
                await session.execute(text("""
                    INSERT INTO learning_user_checkpoints
                        (user_id, checkpoint_id, is_completed, completed_at,
                         score, feedback, attempt_count, best_score,
                         created_at, updated_at)
                    VALUES (:uid, :cpid, :completed, :completed_at,
                            :score, :feedback, :attempts, :best,
                            :now, :now)
                """), {
                    "uid": uid, "cpid": cpid, "completed": completed,
                    "completed_at": _past(random.randint(1, 60)) if completed else None,
                    "score": round(random.uniform(50, 100), 1) if completed else None,
                    "feedback": "Well done!" if completed else None,
                    "attempts": random.randint(1, 3),
                    "best": round(random.uniform(60, 100), 1) if completed else None,
                    "now": now,
                })
                ucp_count += 1

        # User learning reports
        report_count = 0
        for uid in random.sample(all_ids, min(len(all_ids), 15)):
            p_start = _past_date(random.randint(7, 90))
            p_end = p_start + timedelta(days=6)
            await session.execute(text("""
                INSERT INTO learning_user_reports
                    (user_id, report_date, report_type, period_start, period_end,
                     total_time_minutes, lessons_completed, courses_completed, xp_earned, badges_earned,
                     current_streak, active_days, courses_in_progress, completion_rate,
                     assessments_taken, average_assessment_score,
                     top_courses, top_skills, achievements, recommendations,
                     goals_completed, goals_in_progress,
                     created_at, updated_at)
                VALUES (:uid, :report_date, 'weekly', :p_start, :p_end,
                        :total_min, :lessons, :courses, :xp, :badges,
                        :streak, :active, :in_progress, :comp_rate,
                        :assessments, :avg_score,
                        cast(:top_courses as jsonb), cast(:top_skills as jsonb),
                        cast(:achievements as jsonb), cast(:recs as jsonb),
                        :goals_done, :goals_ip,
                        :now, :now)
            """), {
                "uid": uid, "report_date": p_end, "p_start": p_start, "p_end": p_end,
                "total_min": random.randint(30, 600),
                "lessons": random.randint(0, 10),
                "courses": random.randint(0, 2),
                "xp": random.randint(10, 300),
                "badges": random.randint(0, 3),
                "streak": random.randint(0, 14),
                "active": random.randint(1, 7),
                "in_progress": random.randint(0, 3),
                "comp_rate": round(random.uniform(0, 100), 1),
                "assessments": random.randint(0, 3),
                "avg_score": round(random.uniform(60, 100), 1),
                "top_courses": json.dumps([]),
                "top_skills": json.dumps([]),
                "achievements": json.dumps([]),
                "recs": json.dumps([]),
                "goals_done": random.randint(0, 2),
                "goals_ip": random.randint(0, 3),
                "now": now,
            })
            report_count += 1

        print(f"    Created {interest_count} interests, {checkpoint_count} checkpoints, {report_count} reports")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 7. COURSE ANALYTICS + RECOMMENDATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM learning_course_analytics"))
    if r.scalar() == 0 and course_ids:
        print("  Seeding learning_course_analytics & recommendations...")

        analytics_count = 0
        used_ca = set()
        for cid in course_ids[:6]:
            for days_ago in range(0, 30, 7):
                adate = _past_date(days_ago)
                if (cid, adate) in used_ca:
                    continue
                used_ca.add((cid, adate))
                await session.execute(text("""
                    INSERT INTO learning_course_analytics
                        (course_id, analytics_date, total_enrollments, new_enrollments, active_enrollments,
                         completions, completion_rate, average_completion_days,
                         total_time_minutes, average_time_per_user, lessons_completed,
                         quizzes_taken, average_quiz_score, pass_rate,
                         average_rating, total_ratings,
                         created_at, updated_at)
                    VALUES (:cid, :adate, :total_enr, :new_enr, :active_enr,
                            :completions, :comp_rate, :avg_days,
                            :total_min, :avg_time, :lessons,
                            :quizzes, :avg_quiz, :pass_rate,
                            :avg_rating, :total_ratings,
                            :now, :now)
                """), {
                    "cid": cid, "adate": adate,
                    "total_enr": random.randint(10, 50),
                    "new_enr": random.randint(0, 8),
                    "active_enr": random.randint(5, 30),
                    "completions": random.randint(0, 15),
                    "comp_rate": round(random.uniform(20, 80), 1),
                    "avg_days": round(random.uniform(5, 30), 1),
                    "total_min": random.randint(100, 5000),
                    "avg_time": round(random.uniform(30, 180), 1),
                    "lessons": random.randint(10, 100),
                    "quizzes": random.randint(0, 30),
                    "avg_quiz": round(random.uniform(60, 95), 1),
                    "pass_rate": round(random.uniform(50, 95), 1),
                    "avg_rating": round(random.uniform(3.0, 5.0), 1),
                    "total_ratings": random.randint(0, 20),
                    "now": now,
                })
                analytics_count += 1

        # Course recommendations
        rec_count = 0
        used_rec = set()
        for _ in range(25):
            uid = random.choice(all_ids)
            cid = random.choice(course_ids)
            source = random.choice(["collaborative_filtering", "content_based", "skill_gap", "trending", "admin_curated"])
            if (uid, cid, source) in used_rec:
                continue
            used_rec.add((uid, cid, source))
            await session.execute(text("""
                INSERT INTO learning_course_recommendations
                    (user_id, course_id, recommendation_source, relevance_score,
                     reason, factors, is_viewed, is_dismissed, is_enrolled,
                     created_at, updated_at)
                VALUES (:uid, :cid, :source, :score,
                        :reason, cast(:factors as jsonb), :viewed, false, false,
                        :now, :now)
            """), {
                "uid": uid, "cid": cid, "source": source,
                "score": round(random.uniform(0.3, 1.0), 2),
                "reason": "Based on your learning interests and activity",
                "factors": json.dumps({"interests": [], "skills": []}),
                "viewed": random.choice([True, False]),
                "now": now,
            })
            rec_count += 1

        print(f"    Created {analytics_count} analytics records, {rec_count} recommendations")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 8. ENGAGEMENT EVENTS + PLATFORM METRICS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM learning_engagement_events"))
    if r.scalar() == 0:
        print("  Seeding learning_engagement_events & platform_metrics...")

        event_types = ["login", "course_view", "lesson_start", "lesson_complete",
                       "quiz_attempt", "resource_download", "video_watch",
                       "discussion_post", "search", "badge_earned"]
        devices = ["desktop", "mobile", "tablet"]
        browsers = ["Chrome", "Firefox", "Safari", "Edge"]

        ev_count = 0
        for _ in range(50):
            uid = random.choice(all_ids)
            ev_type = random.choice(event_types)
            ev_date = _past_date(random.randint(0, 60))
            ev_ts = datetime(ev_date.year, ev_date.month, ev_date.day,
                             random.randint(6, 22), random.randint(0, 59), tzinfo=utc)
            cid = random.choice(course_ids) if course_ids and random.random() > 0.3 else None
            lid = random.choice(lesson_ids) if lesson_ids and random.random() > 0.5 else None
            await session.execute(text("""
                INSERT INTO learning_engagement_events
                    (user_id, event_type, event_date, event_timestamp,
                     course_id, lesson_id, event_data, session_id,
                     duration_seconds, value, device_type, browser)
                VALUES (:uid, :ev_type, :ev_date, :ev_ts,
                        :cid, :lid, cast(:data as jsonb), :session_id,
                        :duration, :value, :device, :browser)
            """), {
                "uid": uid, "ev_type": ev_type, "ev_date": ev_date, "ev_ts": ev_ts,
                "cid": cid, "lid": lid,
                "data": json.dumps({}),
                "session_id": f"sess_{random.randint(10000, 99999)}",
                "duration": random.randint(5, 3600) if ev_type != "login" else None,
                "value": round(random.uniform(0, 100), 1) if ev_type == "quiz_attempt" else None,
                "device": random.choice(devices),
                "browser": random.choice(browsers),
            })
            ev_count += 1

        # Platform metrics
        metric_types = ["enrollment", "completion", "engagement", "assessment_score",
                        "time_spent", "streak", "badge_earned"]
        pm_count = 0
        used_pm = set()
        for days_ago in range(0, 30):
            mdate = _past_date(days_ago)
            for mtype in random.sample(metric_types, random.randint(2, 5)):
                if (mdate, mtype) in used_pm:
                    continue
                used_pm.add((mdate, mtype))
                val = round(random.uniform(1, 500), 1)
                prev = round(random.uniform(1, 500), 1)
                change = round(((val - prev) / prev) * 100, 1) if prev > 0 else 0
                await session.execute(text("""
                    INSERT INTO learning_platform_metrics
                        (metric_date, metric_type, value, previous_value, change_percentage,
                         period, created_at, updated_at)
                    VALUES (:mdate, :mtype, :val, :prev, :change,
                            'daily', :now, :now)
                """), {
                    "mdate": mdate, "mtype": mtype, "val": val,
                    "prev": prev, "change": change, "now": now,
                })
                pm_count += 1

        print(f"    Created {ev_count} engagement events, {pm_count} platform metrics")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 9. LITERACY LEARNERS + TUTORS + MATCHES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM literacy_learners"))
    if r.scalar() == 0 and program_ids:
        print("  Seeding literacy_learners, tutors, matches...")

        statuses = ["active", "active", "active", "active", "on_hold", "completed",
                    "intake_scheduled", "active", "active", "prospective",
                    "active", "active", "transferred", "active", "active"]
        levels = ["pre_literacy", "emergent", "beginning", "intermediate", "advanced",
                  "beginning", "emergent", "intermediate", "proficient", "beginning",
                  "intermediate", "emergent", "advanced", "beginning", "emergent"]
        languages = ["English", "Spanish", "Vietnamese", "Somali", "Arabic",
                     "English", "Mandarin", "English", "Haitian Creole", "English",
                     "English", "Korean", "English", "Portuguese", "English"]
        referrals = ["Word of mouth", "Social worker", "School referral", "Community center",
                     "Self-referred", "Partner organization", "Adult education program"]
        goal_types = ["fluency_improvement", "comprehension", "ged_preparation",
                      "employment", "digital_literacy", "family_literacy",
                      "vocabulary", "personal_fulfillment"]

        # Pick patron users for learners
        learner_users = random.sample(patron_ids, min(len(patron_ids), 15))
        learner_ids = []
        for i, uid in enumerate(learner_users):
            pid = random.choice(program_ids)
            r2 = await session.execute(text("""
                INSERT INTO literacy_learners
                    (user_id, program_id, status, age, native_language,
                     languages_spoken, education_background, employment_status,
                     accessibility_needs, transportation_needs, childcare_needed,
                     current_level, total_hours_attended, total_sessions_completed,
                     current_reading_level_wpm, primary_goal_type,
                     referred_from, notes, created_at, updated_at)
                VALUES (:uid, :pid, :status, :age, :lang,
                        :langs, :edu, :emp,
                        :access, :transport, :childcare,
                        :level, :hours, :sessions,
                        :wpm, :goal,
                        :referred, :notes, :now, :now)
                RETURNING id
            """), {
                "uid": uid, "pid": pid, "status": statuses[i % len(statuses)],
                "age": random.randint(18, 72),
                "lang": languages[i % len(languages)],
                "langs": languages[i % len(languages)],
                "edu": random.choice(["Some high school", "No formal education", "Elementary school", "High school diploma"]),
                "emp": random.choice(["employed", "unemployed", "seeking", "retired"]),
                "access": None, "transport": random.choice([True, False]),
                "childcare": random.choice([True, False]),
                "level": levels[i % len(levels)],
                "hours": Decimal(str(round(random.uniform(0, 200), 2))),
                "sessions": random.randint(0, 50),
                "wpm": random.randint(20, 180),
                "goal": goal_types[i % len(goal_types)],
                "referred": random.choice(referrals),
                "notes": None, "now": now,
            })
            learner_ids.append(r2.scalar())

        # Tutors (5-8)
        tutor_users = random.sample(staff_ids, min(len(staff_ids), 8))
        tutor_ids = []
        tutor_statuses = ["active", "active", "active", "in_training", "active",
                          "on_leave", "active", "active"]
        tutor_quals = ["bachelor_degree", "teaching_certificate", "master_degree",
                       "esol_certification", "literacy_specialist",
                       "volunteer_tutor_training", "bachelor_degree", "ged_instructor"]
        for i, uid in enumerate(tutor_users):
            r2 = await session.execute(text("""
                INSERT INTO literacy_tutors
                    (user_id, status, is_active, primary_focus, languages_spoken,
                     can_teach_ged, can_teach_esol, can_work_with_special_needs,
                     years_experience, preferred_learner_level, learner_age_preference,
                     primary_qualification, is_certified,
                     preferred_location, can_teach_remote, can_teach_in_person,
                     total_learners_taught, total_hours_taught,
                     has_completed_mandatory_training, background_check_completed,
                     confidentiality_agreement_signed,
                     bio, created_at, updated_at)
                VALUES (:uid, :status, :active, :focus, :langs,
                        :ged, :esol, :special,
                        :years, :pref_level, :age_pref,
                        :qual, :certified,
                        :location, :remote, :in_person,
                        :learners_taught, :hours_taught,
                        :mandatory, :bg_check,
                        :conf_signed,
                        :bio, :now, :now)
                RETURNING id
            """), {
                "uid": uid, "status": tutor_statuses[i % len(tutor_statuses)],
                "active": tutor_statuses[i % len(tutor_statuses)] == "active",
                "focus": random.choice(["Adult basic literacy", "GED preparation", "ESL/ESOL", "Digital literacy"]),
                "langs": random.choice(["English", "English,Spanish", "English,Vietnamese", "English,Arabic"]),
                "ged": random.choice([True, False]),
                "esol": random.choice([True, False]),
                "special": random.choice([True, False]),
                "years": random.randint(0, 15),
                "pref_level": random.choice(["beginner", "intermediate", "advanced", None]),
                "age_pref": random.choice(["adult", "all_ages", None]),
                "qual": tutor_quals[i % len(tutor_quals)],
                "certified": random.choice([True, True, False]),
                "location": random.choice(["Main Branch", "Community Room", "Remote"]),
                "remote": random.choice([True, False]),
                "in_person": True,
                "learners_taught": random.randint(0, 25),
                "hours_taught": Decimal(str(round(random.uniform(0, 500), 2))),
                "mandatory": True,
                "bg_check": True,
                "conf_signed": True,
                "bio": "Passionate about helping adults achieve literacy goals.",
                "now": now,
            })
            tutor_ids.append(r2.scalar())

        # Matches
        match_ids = []
        match_statuses = ["active", "active", "active", "ended", "paused"]
        match_reasons = ["availability", "specialization", "language", "location", "experience_level"]
        for i, lid in enumerate(learner_ids[:10]):
            tid = tutor_ids[i % len(tutor_ids)]
            mstatus = match_statuses[i % len(match_statuses)]
            start = _past_date(random.randint(30, 180))
            end = _past_date(random.randint(1, 29)) if mstatus == "ended" else None
            r2 = await session.execute(text("""
                INSERT INTO literacy_tutor_matches
                    (learner_id, tutor_id, match_date, status, reason,
                     compatibility_score, start_date, end_date,
                     sessions_completed, total_hours, match_notes,
                     created_at, updated_at)
                VALUES (:lid, :tid, :match_date, :status, :reason,
                        :score, :start, :end_date,
                        :sessions, :hours, :notes,
                        :now, :now)
                RETURNING id
            """), {
                "lid": lid, "tid": tid, "match_date": _past(random.randint(30, 180)),
                "status": mstatus, "reason": random.choice(match_reasons),
                "score": Decimal(str(round(random.uniform(0.5, 0.99), 2))),
                "start": start, "end_date": end,
                "sessions": random.randint(0, 20),
                "hours": Decimal(str(round(random.uniform(0, 60), 2))),
                "notes": "Good match based on scheduling and learning style",
                "now": now,
            })
            match_ids.append(r2.scalar())

        print(f"    Created {len(learner_ids)} learners, {len(tutor_ids)} tutors, {len(match_ids)} matches")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 10. LITERACY ASSESSMENTS + PROGRESS + OUTCOMES
    # ════════════════════════════════════════════════════════════════
    learner_r = await session.execute(text("SELECT id FROM literacy_learners"))
    learner_ids_all = [r[0] for r in learner_r.fetchall()]

    tutor_r = await session.execute(text("SELECT id FROM literacy_tutors"))
    tutor_ids_all = [r[0] for r in tutor_r.fetchall()]

    match_r = await session.execute(text("SELECT id FROM literacy_tutor_matches"))
    match_ids_all = [r[0] for r in match_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM literacy_assessments"))
    if r.scalar() == 0 and learner_ids_all:
        print("  Seeding literacy_assessments, progress, outcomes...")

        assess_types = ["initial_intake", "phonics", "comprehension", "fluency",
                        "vocabulary", "digital_literacy"]
        assess_levels = ["pre_literacy", "emergent", "beginning", "intermediate", "advanced", "proficient"]
        tools = ["TABE", "BEST Plus", "CASAS", "Custom Assessment"]

        a_count = 0
        for lid in learner_ids_all:
            for _ in range(random.randint(1, 3)):
                atype = random.choice(assess_types)
                level = random.choice(assess_levels)
                score = Decimal(str(round(random.uniform(20, 98), 2)))
                await session.execute(text("""
                    INSERT INTO literacy_assessments
                        (learner_id, assessor_id, assessment_type, assessment_date,
                         score, percentage, level, reading_speed_wpm,
                         comprehension_percentage, assessment_tool_used,
                         level_progression, notes,
                         created_at, updated_at)
                    VALUES (:lid, :assessor, :atype, :adate,
                            :score, :pct, :level, :wpm,
                            :comp_pct, :tool,
                            :progression, :notes,
                            :now, :now)
                """), {
                    "lid": lid, "assessor": random.choice(staff_ids),
                    "atype": atype, "adate": _past(random.randint(1, 180)),
                    "score": score, "pct": score,
                    "level": level, "wpm": random.randint(20, 180),
                    "comp_pct": Decimal(str(round(random.uniform(30, 95), 2))),
                    "tool": random.choice(tools),
                    "progression": random.choice(["improved", "maintained", "regressed", None]),
                    "notes": None, "now": now,
                })
                a_count += 1

        # Literacy progress
        p_count = 0
        used_prog = set()
        for lid in learner_ids_all:
            for months_ago in range(0, 4):
                p_start = _past_date(30 * months_ago + 30)
                p_end = _past_date(30 * months_ago + 1)
                if (lid, p_start) in used_prog:
                    continue
                used_prog.add((lid, p_start))
                await session.execute(text("""
                    INSERT INTO literacy_progress
                        (learner_id, period_start, period_end,
                         sessions_scheduled, sessions_completed, sessions_missed, total_hours,
                         books_read, pages_read,
                         assessment_completed, new_level_achieved,
                         attendance_rate, skills_improved,
                         created_at, updated_at)
                    VALUES (:lid, :p_start, :p_end,
                            :sched, :comp, :missed, :hours,
                            :books, :pages,
                            :assessed, :leveled,
                            :attend, :skills,
                            :now, :now)
                """), {
                    "lid": lid, "p_start": p_start, "p_end": p_end,
                    "sched": random.randint(4, 12),
                    "comp": random.randint(2, 10),
                    "missed": random.randint(0, 3),
                    "hours": Decimal(str(round(random.uniform(2, 30), 2))),
                    "books": random.randint(0, 5),
                    "pages": random.randint(0, 200),
                    "assessed": random.choice([True, False]),
                    "leveled": random.choice([True, False, False]),
                    "attend": Decimal(str(round(random.uniform(50, 100), 2))),
                    "skills": "reading fluency,vocabulary",
                    "now": now,
                })
                p_count += 1

        # Literacy outcomes
        o_count = 0
        outcome_types = ["level_advancement", "goal_completed", "employment_gained",
                         "certification_earned", "ged_passed", "family_literacy"]
        outcome_cats = ["educational", "employment", "personal_development", "family"]
        for lid in random.sample(learner_ids_all, min(len(learner_ids_all), 8)):
            otype = random.choice(outcome_types)
            await session.execute(text("""
                INSERT INTO literacy_outcomes
                    (learner_id, outcome_type, outcome_category, outcome_date,
                     is_verified, verification_method, details, notes,
                     created_at, updated_at)
                VALUES (:lid, :otype, :ocat, :odate,
                        :verified, :method, :details, :notes,
                        :now, :now)
            """), {
                "lid": lid, "otype": otype,
                "ocat": random.choice(outcome_cats),
                "odate": _past_date(random.randint(1, 120)),
                "verified": random.choice([True, False]),
                "method": random.choice(["self_reported", "partner_confirmation", "official_record", None]),
                "details": "Learner achieved significant progress",
                "notes": None, "now": now,
            })
            o_count += 1

        print(f"    Created {a_count} literacy assessments, {p_count} progress records, {o_count} outcomes")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 11. LITERACY RESOURCES + COLLECTIONS + ITEMS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM literacy_resources"))
    if r.scalar() == 0:
        print("  Seeding literacy_resources, collections, collection_items...")

        resources = [
            ("Laubach Way to Reading 1", "Introductory workbook for adult new readers", "book", "print",
             "pre_literacy", "emergent", None, "New Readers Press", "Frank Laubach", 1981, 128),
            ("Challenger Adult Reading Series", "Structured reading program for adults", "book", "print",
             "beginning", "intermediate", None, "New Readers Press", "Corea Murphy", 2010, 256),
            ("Ventures Level 1 Student Book", "ESL coursework for beginning adults", "book", "print",
             "emergent", "beginning", None, "Cambridge", "Gretchen Bitterlin", 2018, 200),
            ("Khan Academy - Reading Foundations", "Free online reading exercises", "digital_material", "digital",
             "pre_literacy", "intermediate", "fiction_general", None, None, None, None),
            ("ReadWorks Digital Library", "Curated reading passages with comprehension questions", "digital_material", "interactive",
             "beginning", "advanced", None, None, None, None, None),
            ("Phonics for Adults Worksheet Pack", "Printable phonics practice sheets", "worksheet", "print",
             "pre_literacy", "beginning", None, "Literacy Center", None, 2023, 50),
            ("GED Test Prep - Language Arts", "Comprehensive GED reading prep guide", "guide", "print",
             "intermediate", "proficient", None, "Kaplan", None, 2024, 400),
            ("Palace Project - Easy Reads Collection", "Curated ebook collection for new readers", "book", "digital",
             "emergent", "intermediate", "fiction_general", None, None, None, None),
            ("YouTube Literacy Channel", "Video series on reading fundamentals", "learning_video", "video",
             "pre_literacy", "beginning", None, None, None, None, None),
            ("Digital Skills for Daily Life", "Interactive computer basics course", "interactive_tool", "interactive",
             "pre_literacy", "proficient", None, "Digital Literacy Council", None, 2025, None),
            ("Steck-Vaughn Pre-GED", "Preparation workbook for GED readiness", "book", "print",
             "beginning", "intermediate", None, "Steck-Vaughn", None, 2019, 320),
            ("News for You", "Weekly newspaper for adult new readers", "article", "hybrid",
             "beginning", "intermediate", None, "New Readers Press", None, 2026, None),
            ("Family Literacy Activity Guide", "Activities for parents learning with children", "guide", "print",
             "emergent", "advanced", "self_help", "National Center for Families Learning", None, 2022, 80),
            ("Pronunciation Power App", "Mobile app for pronunciation practice", "interactive_tool", "interactive",
             "pre_literacy", "intermediate", None, "English Computerized Learning", None, 2024, None),
            ("Word by Word Picture Dictionary", "Visual dictionary for vocabulary building", "book", "print",
             "pre_literacy", "beginning", None, "Pearson", "Steven Molinsky", 2017, 288),
        ]

        resource_ids = []
        for title, desc, rtype, fmt, min_lev, max_lev, theme, publisher, author, year, pages in resources:
            r2 = await session.execute(text("""
                INSERT INTO literacy_resources
                    (title, description, resource_type, format, min_level, max_level,
                     theme, publisher, author, publication_year, page_count,
                     is_active, is_featured, difficulty_rating, learner_reviews, average_rating,
                     created_at, updated_at)
                VALUES (:title, :desc, :rtype, :fmt, :min_lev, :max_lev,
                        :theme, :publisher, :author, :year, :pages,
                        true, :featured, :diff, :reviews, :rating,
                        :now, :now)
                RETURNING id
            """), {
                "title": title, "desc": desc, "rtype": rtype, "fmt": fmt,
                "min_lev": min_lev, "max_lev": max_lev,
                "theme": theme, "publisher": publisher, "author": author,
                "year": year, "pages": pages,
                "featured": random.choice([True, False, False]),
                "diff": random.randint(1, 5),
                "reviews": random.randint(0, 15),
                "rating": Decimal(str(round(random.uniform(3.0, 5.0), 2))),
                "now": now,
            })
            resource_ids.append(r2.scalar())

        # Collections
        collections_data = [
            ("Beginning Reader Essentials", "Core materials for new adult readers", "level", "pre_literacy", "beginning", None),
            ("GED Prep Collection", "Materials to prepare for GED testing", "topic", "intermediate", "proficient", None),
            ("ESL Reading List", "Resources for English language learners", "theme", "emergent", "intermediate", None),
            ("Digital Literacy Starter Kit", "Resources for learning basic computer skills", "topic", "pre_literacy", "proficient", None),
            ("Family Reading Together", "Materials for parent-child literacy activities", "theme", "emergent", "advanced", "self_help"),
        ]
        collection_ids = []
        for name, desc, ctype, min_lev, max_lev, theme in collections_data:
            r2 = await session.execute(text("""
                INSERT INTO literacy_collections
                    (curator_id, name, description, collection_type, min_level, max_level,
                     theme, is_active, is_featured, item_count, created_at, updated_at)
                VALUES (:curator, :name, :desc, :ctype, :min_lev, :max_lev,
                        :theme, true, :featured, 0, :now, :now)
                RETURNING id
            """), {
                "curator": random.choice(staff_ids), "name": name, "desc": desc,
                "ctype": ctype, "min_lev": min_lev, "max_lev": max_lev,
                "theme": theme, "featured": random.choice([True, False]),
                "now": now,
            })
            collection_ids.append(r2.scalar())

        # Collection items
        ci_count = 0
        for coll_id in collection_ids:
            selected = random.sample(resource_ids, min(len(resource_ids), random.randint(3, 6)))
            for pos, rid in enumerate(selected):
                await session.execute(text("""
                    INSERT INTO literacy_collection_items
                        (collection_id, resource_id, position, created_at, updated_at)
                    VALUES (:coll, :rid, :pos, :now, :now)
                """), {"coll": coll_id, "rid": rid, "pos": pos, "now": now})
                ci_count += 1
            # Update item_count
            await session.execute(text(
                "UPDATE literacy_collections SET item_count = :cnt WHERE id = :cid"
            ), {"cnt": len(selected), "cid": coll_id})

        print(f"    Created {len(resource_ids)} resources, {len(collection_ids)} collections, {ci_count} items")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 12. LITERACY GOALS + MILESTONES + CELEBRATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM literacy_goals"))
    if r.scalar() == 0 and learner_ids_all:
        print("  Seeding literacy_goals, milestones, celebrations...")

        goal_statements = [
            ("fluency_improvement", "Increase reading speed from 60 to 100 wpm", "intermediate"),
            ("comprehension", "Understand newspaper articles independently", "intermediate"),
            ("ged_preparation", "Pass the GED Language Arts section", "advanced"),
            ("employment", "Read and fill out job applications independently", "beginning"),
            ("digital_literacy", "Learn to use email and browse the internet", "beginning"),
            ("family_literacy", "Read bedtime stories to my children", "intermediate"),
            ("vocabulary", "Learn 500 new vocabulary words", "intermediate"),
            ("personal_fulfillment", "Read my first complete novel", "advanced"),
        ]

        goal_ids = []
        for lid in learner_ids_all:
            num_goals = random.randint(1, 2)
            for gtype, statement, target_lev in random.sample(goal_statements, min(num_goals, len(goal_statements))):
                gstatus = random.choice(["active", "active", "active", "completed", "on_hold"])
                target = _future_date(random.randint(30, 365)) if gstatus != "completed" else _past_date(random.randint(1, 30))
                r2 = await session.execute(text("""
                    INSERT INTO literacy_goals
                        (learner_id, goal_type, goal_statement, target_level,
                         target_date, status, completed_date, progress_percentage,
                         notes, created_at, updated_at)
                    VALUES (:lid, :gtype, :statement, :target_lev,
                            :target, :status, :completed, :progress,
                            :notes, :now, :now)
                    RETURNING id
                """), {
                    "lid": lid, "gtype": gtype, "statement": statement,
                    "target_lev": target_lev, "target": target,
                    "status": gstatus,
                    "completed": _past(random.randint(1, 30)) if gstatus == "completed" else None,
                    "progress": 100 if gstatus == "completed" else random.randint(0, 85),
                    "notes": None, "now": now,
                })
                goal_ids.append(r2.scalar())

        # Literacy milestones
        ms_count = 0
        for gid in goal_ids:
            for j in range(random.randint(1, 3)):
                completed = random.choice([True, False])
                await session.execute(text("""
                    INSERT INTO literacy_milestones
                        (goal_id, description, target_date, is_completed,
                         completed_date, notes, created_at, updated_at)
                    VALUES (:gid, :desc, :target, :completed,
                            :comp_date, :notes, :now, :now)
                """), {
                    "gid": gid,
                    "desc": random.choice([
                        "Complete 5 reading sessions", "Pass mid-point assessment",
                        "Read 3 books at current level", "Complete all worksheets",
                        "Demonstrate improved fluency", "Master 50 new words",
                    ]),
                    "target": _future_date(random.randint(14, 120)),
                    "completed": completed,
                    "comp_date": _past(random.randint(1, 60)) if completed else None,
                    "notes": None, "now": now,
                })
                ms_count += 1

        # Celebrations
        cel_count = 0
        for gid in random.sample(goal_ids, min(len(goal_ids), 10)):
            lid = random.choice(learner_ids_all)
            await session.execute(text("""
                INSERT INTO literacy_celebrations
                    (goal_id, learner_id, achievement_date, celebration_type,
                     celebration_notes, recognition_method,
                     created_at, updated_at)
                VALUES (:gid, :lid, :adate, :ctype,
                        :notes, :method,
                        :now, :now)
            """), {
                "gid": gid, "lid": lid,
                "adate": _past(random.randint(1, 90)),
                "ctype": random.choice(["milestone_reached", "level_up", "goal_completed", "attendance_streak"]),
                "notes": "Congratulations on your achievement!",
                "method": random.choice(["certificate", "public_announcement", "small_gift", "verbal_recognition"]),
                "now": now,
            })
            cel_count += 1

        print(f"    Created {len(goal_ids)} goals, {ms_count} milestones, {cel_count} celebrations")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 13. LITERACY SESSION SCHEDULES + LOGS + NOTES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM literacy_session_logs"))
    if r.scalar() == 0 and match_ids_all:
        print("  Seeding literacy_session_logs, schedules, notes...")

        # First create session logs (they are referenced by schedules)
        attendance_statuses = ["attended", "attended", "attended", "partially_attended", "not_attended"]
        moods = ["engaged", "motivated", "tired", "distracted", "focused", "enthusiastic"]

        log_ids = []
        for _ in range(20):
            mid = random.choice(match_ids_all)
            lid = random.choice(learner_ids_all)
            tid = random.choice(tutor_ids_all) if tutor_ids_all else None
            if tid is None:
                continue
            s_date = _past_date(random.randint(1, 120))
            actual_start = datetime(s_date.year, s_date.month, s_date.day,
                                    random.choice([9, 10, 11, 13, 14, 15]), 0, tzinfo=utc)
            duration = random.randint(30, 90)
            actual_end = actual_start + timedelta(minutes=duration)
            att = random.choice(attendance_statuses)

            r2 = await session.execute(text("""
                INSERT INTO literacy_session_logs
                    (match_id, learner_id, tutor_id, session_date,
                     actual_start, actual_end, actual_duration_minutes,
                     attendance_status, learner_present, tutor_present,
                     learner_engagement, learner_focus, progress_observed,
                     location, is_remote,
                     created_at, updated_at)
                VALUES (:mid, :lid, :tid, :s_date,
                        :actual_start, :actual_end, :duration,
                        :att, :l_present, :t_present,
                        :engagement, :focus, :progress,
                        :location, :remote,
                        :now, :now)
                RETURNING id
            """), {
                "mid": mid, "lid": lid, "tid": tid, "s_date": s_date,
                "actual_start": actual_start, "actual_end": actual_end,
                "duration": duration,
                "att": att,
                "l_present": att in ("attended", "partially_attended"),
                "t_present": True,
                "engagement": random.randint(1, 5),
                "focus": random.randint(1, 5),
                "progress": random.randint(1, 5),
                "location": random.choice(["Main Branch", "Community Room", "Remote"]),
                "remote": random.choice([True, False]),
                "now": now,
            })
            log_ids.append(r2.scalar())

        # Session schedules
        sched_count = 0
        session_statuses = ["completed", "completed", "scheduled", "confirmed", "cancelled"]
        for mid in match_ids_all:
            for _ in range(random.randint(2, 5)):
                sdate = _past_date(random.randint(0, 90))
                st = time(random.choice([9, 10, 11, 13, 14, 15]), 0)
                sstatus = random.choice(session_statuses)
                log_id = random.choice(log_ids) if log_ids and sstatus == "completed" else None
                await session.execute(text("""
                    INSERT INTO literacy_session_schedules
                        (match_id, scheduled_date, start_time, duration_minutes,
                         status, location, is_remote,
                         learner_confirmed, tutor_confirmed, session_log_id,
                         notes, created_at, updated_at)
                    VALUES (:mid, :sdate, :st, :dur,
                            :status, :location, :remote,
                            :l_conf, :t_conf, :log_id,
                            :notes, :now, :now)
                """), {
                    "mid": mid, "sdate": sdate, "st": st,
                    "dur": random.choice([30, 45, 60, 90]),
                    "status": sstatus,
                    "location": random.choice(["Main Branch", "Community Room", "Remote"]),
                    "remote": random.choice([True, False]),
                    "l_conf": random.choice([True, False]),
                    "t_conf": True,
                    "log_id": log_id,
                    "notes": None, "now": now,
                })
                sched_count += 1

        # Session notes
        note_count = 0
        for log_id in log_ids:
            await session.execute(text("""
                INSERT INTO literacy_session_notes
                    (session_id, topics_covered, activities_conducted,
                     skills_practiced, progress_notes,
                     homework_assigned, next_lesson_focus,
                     learner_mood, tutor_notes,
                     created_at, updated_at)
                VALUES (:sid, :topics, :activities,
                        :skills, :progress,
                        :homework, :next_focus,
                        :mood, :tutor_notes,
                        :now, :now)
            """), {
                "sid": log_id,
                "topics": random.choice(["Phonics review, sight words", "Reading comprehension passage",
                                         "Vocabulary building, word families", "GED practice questions",
                                         "Digital literacy basics"]),
                "activities": random.choice(["Read aloud practice", "Worksheet completion",
                                             "Flashcard drills", "Partner reading",
                                             "Computer-based exercises"]),
                "skills": "reading fluency, decoding, vocabulary",
                "progress": random.choice(["Improved word recognition", "Better sentence fluency",
                                           "Expanding vocabulary", "Steady improvement"]),
                "homework": random.choice(["Read chapter 3", "Complete worksheet pages 10-12",
                                           "Practice sight words list", None]),
                "next_focus": random.choice(["Continue phonics work", "Start new reading level",
                                             "Review assessment results", "Practice writing"]),
                "mood": random.choice(moods),
                "tutor_notes": "Good session overall. Learner showing progress.",
                "now": now,
            })
            note_count += 1

        print(f"    Created {len(log_ids)} session logs, {sched_count} schedules, {note_count} notes")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 14. LITERACY COHORTS + LEARNER COHORTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM literacy_cohorts"))
    if r.scalar() == 0 and program_ids:
        print("  Seeding literacy_cohorts & learner_cohorts...")

        cohorts_data = [
            ("Spring 2026 Beginning Readers", "2026-SPR-A", "Beginning reader cohort for spring semester",
             _past_date(60), _future_date(60), 12),
            ("Winter 2025 GED Prep", "2025-WIN-GED", "GED preparation intensive group",
             _past_date(180), _past_date(30), 8),
            ("ESL Conversation Circle", "2026-ESL-CC", "English conversation practice group",
             _past_date(90), _future_date(90), 15),
            ("Digital Literacy Boot Camp", "2026-DIG-BC", "Intensive computer skills for new users",
             _past_date(30), _future_date(30), 10),
        ]

        cohort_ids = []
        for name, code, desc, start, end, target in cohorts_data:
            r2 = await session.execute(text("""
                INSERT INTO literacy_cohorts
                    (program_id, cohort_name, cohort_code, start_date, end_date,
                     target_enrollment, actual_enrollment, description,
                     created_at, updated_at)
                VALUES (:pid, :name, :code, :start, :end,
                        :target, 0, :desc,
                        :now, :now)
                RETURNING id
            """), {
                "pid": random.choice(program_ids), "name": name, "code": code,
                "start": start, "end": end, "target": target,
                "desc": desc, "now": now,
            })
            cohort_ids.append(r2.scalar())

        # Learner-cohort links
        lc_count = 0
        used_lc = set()
        for cid in cohort_ids:
            members = random.sample(learner_ids_all, min(len(learner_ids_all), random.randint(3, 6)))
            for lid in members:
                if (lid, cid) in used_lc:
                    continue
                used_lc.add((lid, cid))
                await session.execute(text("""
                    INSERT INTO literacy_learner_cohorts
                        (learner_id, cohort_id, enrollment_date)
                    VALUES (:lid, :cid, :enrolled)
                """), {
                    "lid": lid, "cid": cid,
                    "enrolled": _past(random.randint(1, 90)),
                })
                lc_count += 1
            # Update actual_enrollment
            await session.execute(text(
                "UPDATE literacy_cohorts SET actual_enrollment = :cnt WHERE id = :cid"
            ), {"cnt": len(members), "cid": cid})

        print(f"    Created {len(cohort_ids)} cohorts, {lc_count} learner-cohort links")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 15. TUTOR QUALIFICATIONS + AVAILABILITY + TRAINING RECORDS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM literacy_tutor_qualifications"))
    if r.scalar() == 0 and tutor_ids_all:
        print("  Seeding tutor qualifications, availability, training records...")

        qual_types = ["bachelor_degree", "teaching_certificate", "esol_certification",
                      "literacy_specialist", "volunteer_tutor_training", "master_degree"]
        issuers = ["State University", "Community College", "TESOL International",
                   "ProLiteracy", "Local Library System", "National Council of Teachers"]

        q_count = 0
        for tid in tutor_ids_all:
            for _ in range(random.randint(1, 3)):
                qtype = random.choice(qual_types)
                issue_date = _past_date(random.randint(365, 3650))
                await session.execute(text("""
                    INSERT INTO literacy_tutor_qualifications
                        (tutor_id, qualification_type, issuer, issue_date,
                         expiry_date, notes, created_at, updated_at)
                    VALUES (:tid, :qtype, :issuer, :issue_date,
                            :expiry, :notes, :now, :now)
                """), {
                    "tid": tid, "qtype": qtype,
                    "issuer": random.choice(issuers),
                    "issue_date": issue_date,
                    "expiry": _future_date(random.randint(180, 730)) if random.random() > 0.5 else None,
                    "notes": None, "now": now,
                })
                q_count += 1

        # Availability
        av_count = 0
        for tid in tutor_ids_all:
            for day in random.sample(range(0, 5), random.randint(2, 4)):  # Mon-Fri
                start_hour = random.choice([9, 10, 13, 14])
                await session.execute(text("""
                    INSERT INTO literacy_tutor_availability
                        (tutor_id, day_of_week, start_time, end_time,
                         location, is_active)
                    VALUES (:tid, :day, :start, :end,
                            :location, true)
                """), {
                    "tid": tid, "day": day,
                    "start": f"{start_hour:02d}:00",
                    "end": f"{start_hour + 3:02d}:00",
                    "location": random.choice(["Main Branch", "Community Room", "Remote"]),
                })
                av_count += 1

        # Training records
        tr_count = 0
        training_topics = ["adult_learning_principles", "phonics_instruction",
                           "comprehension_strategies", "cultural_competency",
                           "confidentiality_compliance", "assessment_basics",
                           "digital_literacy", "classroom_management"]
        for tid in tutor_ids_all:
            for _ in range(random.randint(1, 4)):
                await session.execute(text("""
                    INSERT INTO literacy_tutor_training_records
                        (tutor_id, trainer_id, training_topic, training_date,
                         hours_completed, training_type, training_provider,
                         is_completed, completion_date,
                         created_at, updated_at)
                    VALUES (:tid, :trainer, :topic, :tdate,
                            :hours, :ttype, :provider,
                            true, :comp_date,
                            :now, :now)
                """), {
                    "tid": tid, "trainer": random.choice(staff_ids),
                    "topic": random.choice(training_topics),
                    "tdate": _past(random.randint(30, 365)),
                    "hours": Decimal(str(round(random.uniform(1, 8), 1))),
                    "ttype": random.choice(["workshop", "online", "conference", "self-study"]),
                    "provider": random.choice(["ProLiteracy", "State Library", "ALA", "In-house"]),
                    "comp_date": _past(random.randint(1, 30)),
                    "now": now,
                })
                tr_count += 1

        print(f"    Created {q_count} qualifications, {av_count} availability slots, {tr_count} training records")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 16. IMPACT METRICS + RESOURCE RECOMMENDATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM literacy_impact_metrics"))
    if r.scalar() == 0 and program_ids:
        print("  Seeding literacy_impact_metrics & resource_recommendations...")

        resource_r = await session.execute(text("SELECT id FROM literacy_resources"))
        lit_resource_ids = [r[0] for r in resource_r.fetchall()]

        # Impact metrics
        im_count = 0
        periods = ["monthly", "quarterly"]
        for pid in program_ids[:3]:
            for months_ago in range(0, 6):
                p_start = _past_date(30 * (months_ago + 1))
                p_end = _past_date(30 * months_ago + 1)
                ptype = "monthly" if months_ago < 4 else "quarterly"
                await session.execute(text("""
                    INSERT INTO literacy_impact_metrics
                        (program_id, period_type, period_start, period_end,
                         learners_served, new_learners_enrolled, learners_completed_program,
                         total_sessions_offered, total_sessions_completed,
                         total_tutor_hours, average_hours_per_learner,
                         ged_completions, level_advancements, employment_outcomes,
                         college_acceptances, certifications_earned,
                         average_improvement, retention_rate, goal_achievement_rate,
                         satisfaction_rating,
                         created_at, updated_at)
                    VALUES (:pid, :ptype, :p_start, :p_end,
                            :served, :new_enr, :completed,
                            :offered, :sessions_comp,
                            :tutor_hours, :avg_hours,
                            :ged, :levels, :employment,
                            :college, :certs,
                            :improvement, :retention, :goal_rate,
                            :satisfaction,
                            :now, :now)
                """), {
                    "pid": pid, "ptype": ptype, "p_start": p_start, "p_end": p_end,
                    "served": random.randint(8, 25),
                    "new_enr": random.randint(0, 5),
                    "completed": random.randint(0, 3),
                    "offered": random.randint(20, 60),
                    "sessions_comp": random.randint(15, 50),
                    "tutor_hours": Decimal(str(round(random.uniform(20, 150), 2))),
                    "avg_hours": Decimal(str(round(random.uniform(5, 20), 2))),
                    "ged": random.randint(0, 2),
                    "levels": random.randint(0, 5),
                    "employment": random.randint(0, 3),
                    "college": random.randint(0, 2),
                    "certs": random.randint(0, 3),
                    "improvement": Decimal(str(round(random.uniform(5, 25), 2))),
                    "retention": Decimal(str(round(random.uniform(60, 95), 2))),
                    "goal_rate": Decimal(str(round(random.uniform(40, 80), 2))),
                    "satisfaction": Decimal(str(round(random.uniform(3.5, 5.0), 2))),
                    "now": now,
                })
                im_count += 1

        # Resource recommendations
        rr_count = 0
        if lit_resource_ids and learner_ids_all:
            for lid in learner_ids_all:
                recs = random.sample(lit_resource_ids, min(len(lit_resource_ids), random.randint(2, 4)))
                for rank, rid in enumerate(recs, 1):
                    await session.execute(text("""
                        INSERT INTO literacy_resource_recommendations
                            (learner_id, resource_id, recommended_date, recommendation_score,
                             order_rank, reason, was_accessed, was_borrowed,
                             created_at, updated_at)
                        VALUES (:lid, :rid, :rdate, :score,
                                :rank, :reason, :accessed, :borrowed,
                                :now, :now)
                    """), {
                        "lid": lid, "rid": rid,
                        "rdate": _past(random.randint(1, 60)),
                        "score": Decimal(str(round(random.uniform(0.4, 0.99), 2))),
                        "rank": rank,
                        "reason": "Matched to learner level and learning goals",
                        "accessed": random.choice([True, False]),
                        "borrowed": random.choice([True, False, False]),
                        "now": now,
                    })
                    rr_count += 1

        print(f"    Created {im_count} impact metrics, {rr_count} resource recommendations")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 17. COMPLIANCE: CONSENT + ACCESS REQUESTS + AUDIT LOGS +
    #     CONFIDENTIALITY MASKS + DATA ACCESS POLICIES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM literacy_consent_records"))
    if r.scalar() == 0 and learner_ids_all:
        print("  Seeding compliance tables (consent, access, audit, masks, policies)...")

        # Consent records
        consent_types = ["data_collection", "outcome_reporting", "partner_sharing",
                         "photo_video", "research_use", "communication"]
        consent_statuses = ["accepted", "accepted", "accepted", "declined", "pending"]
        consent_methods = ["digital_form", "paper_form", "verbal", "email"]

        cr_count = 0
        for lid in learner_ids_all:
            for ctype in random.sample(consent_types, random.randint(2, 4)):
                cstatus = random.choice(consent_statuses)
                req_date = _past(random.randint(30, 180))
                resp_date = req_date + timedelta(days=random.randint(1, 14)) if cstatus != "pending" else None
                await session.execute(text("""
                    INSERT INTO literacy_consent_records
                        (learner_id, consent_type, status,
                         requested_date, response_date, expiration_date,
                         consent_text, consent_method, notes,
                         created_at, updated_at)
                    VALUES (:lid, :ctype, :status,
                            :req_date, :resp_date, :exp_date,
                            :consent_text, :method, :notes,
                            :now, :now)
                """), {
                    "lid": lid, "ctype": ctype, "status": cstatus,
                    "req_date": req_date,
                    "resp_date": resp_date,
                    "exp_date": _past(random.randint(-365, -1)) if cstatus == "accepted" else None,
                    "consent_text": f"I consent to {ctype.replace('_', ' ')} as described in the program handbook.",
                    "method": random.choice(consent_methods) if cstatus != "pending" else None,
                    "notes": None, "now": now,
                })
                cr_count += 1

        # Access requests
        ar_count = 0
        for _ in range(10):
            lid = random.choice(learner_ids_all)
            requester = random.choice(staff_ids)
            approved = random.choice([True, True, False, None])
            approver = random.choice(staff_ids) if approved is not None else None
            await session.execute(text("""
                INSERT INTO literacy_access_requests
                    (requester_id, learner_id, request_date,
                     data_requested, access_reason, access_duration,
                     approved, approval_date, approver_id, denial_reason,
                     created_at, updated_at)
                VALUES (:requester, :lid, :req_date,
                        :data_req, :reason, :duration,
                        :approved, :approval_date, :approver, :denial,
                        :now, :now)
            """), {
                "requester": requester, "lid": lid,
                "req_date": _past(random.randint(1, 90)),
                "data_req": random.choice([
                    "Assessment history and scores",
                    "Confidential health notes",
                    "Income level and barriers information",
                    "Full learner profile for case review",
                ]),
                "reason": random.choice([
                    "Session preparation",
                    "Assessment review",
                    "Case management meeting",
                    "Annual report compilation",
                ]),
                "duration": random.choice(["one_time", "session", "project"]),
                "approved": approved,
                "approval_date": _past(random.randint(1, 30)) if approved is not None else None,
                "approver": approver,
                "denial": "Insufficient justification" if approved is False else None,
                "now": now,
            })
            ar_count += 1

        # Audit logs
        al_count = 0
        audit_actions = ["data_accessed", "assessment_viewed", "notes_viewed",
                         "confidential_field_accessed", "session_notes_viewed",
                         "record_updated", "data_exported"]
        for _ in range(25):
            uid = random.choice(staff_ids)
            lid = random.choice(learner_ids_all)
            action = random.choice(audit_actions)
            await session.execute(text("""
                INSERT INTO literacy_audit_logs
                    (user_id, learner_id, action, action_date,
                     resource_type, field_accessed, access_reason,
                     access_granted, details,
                     created_at, updated_at)
                VALUES (:uid, :lid, :action, :adate,
                        :rtype, :field, :reason,
                        :granted, cast(:details as json),
                        :now, :now)
            """), {
                "uid": uid, "lid": lid, "action": action,
                "adate": _past(random.randint(0, 60)),
                "rtype": random.choice(["learner_profile", "assessment", "session_notes", "goal"]),
                "field": "income_level" if action == "confidential_field_accessed" else None,
                "reason": "Routine case management",
                "granted": True,
                "details": json.dumps({"endpoint": "/api/literacy/learners/" + str(lid)}),
                "now": now,
            })
            al_count += 1

        # Confidentiality masks
        cm_count = 0
        mask_fields = [
            ("literacy_learners", "income_level", "admin", "personal_health_information"),
            ("literacy_learners", "barriers_to_literacy", "admin", "sensitive_personal_data"),
            ("literacy_learners", "health_notes", "director", "protected_health_information"),
            ("literacy_learners", "family_literacy_notes", "admin", "family_information"),
            ("literacy_session_notes", "behavioral_notes", "admin", "behavioral_observations"),
            ("literacy_session_notes", "concerns", "director", "safeguarding_concerns"),
        ]
        for record_type, field, access_level, reason in mask_fields:
            await session.execute(text("""
                INSERT INTO literacy_confidentiality_masks
                    (record_type, field_name, is_masked,
                     access_level_required, mask_reason, effective_date)
                VALUES (:rtype, :field, true,
                        :access_level, :reason, :eff_date)
            """), {
                "rtype": record_type, "field": field,
                "access_level": access_level, "reason": reason,
                "eff_date": _past(random.randint(30, 365)),
            })
            cm_count += 1

        # Data access policies
        dap_count = 0
        policies = [
            ("Tutor Access Policy", "Defines what data tutors can access about their assigned learners", "TUTOR",
             json.dumps(["name", "current_level", "goals", "session_history"]),
             json.dumps(["scores", "level", "assessment_date"]),
             json.dumps(["session_notes", "attendance"]),
             json.dumps([]),
             False, False, True, False, False),
            ("Staff Access Policy", "Full access for literacy program staff", "staff",
             json.dumps(["name", "current_level", "goals", "demographics", "contact"]),
             json.dumps(["scores", "level", "assessment_date", "recommendations"]),
             json.dumps(["session_notes", "attendance", "behavioral_notes"]),
             json.dumps(["income_level", "barriers_to_literacy"]),
             True, False, True, False, False),
            ("Admin Full Access Policy", "Complete data access for administrators", "admin",
             json.dumps(["*"]),
             json.dumps(["*"]),
             json.dumps(["*"]),
             json.dumps(["*"]),
             False, False, True, True, True),
            ("Director Oversight Policy", "Director-level oversight access", "director",
             json.dumps(["*"]),
             json.dumps(["*"]),
             json.dumps(["*"]),
             json.dumps(["*"]),
             False, False, True, True, True),
        ]
        for name, desc, role, learner_f, assess_f, session_f, conf_f, consent, approval, audit, export, share in policies:
            await session.execute(text("""
                INSERT INTO literacy_data_access_policies
                    (policy_name, description, applicable_role,
                     accessible_learner_fields, accessible_assessment_fields,
                     accessible_session_fields, accessible_confidential_fields,
                     requires_consent, requires_approval, audit_log_required,
                     can_export_data, can_share_with_partners, is_active,
                     created_at, updated_at)
                VALUES (:name, :desc, :role,
                        cast(:learner_f as json), cast(:assess_f as json),
                        cast(:session_f as json), cast(:conf_f as json),
                        :consent, :approval, :audit,
                        :export, :share, true,
                        :now, :now)
            """), {
                "name": name, "desc": desc, "role": role,
                "learner_f": learner_f, "assess_f": assess_f,
                "session_f": session_f, "conf_f": conf_f,
                "consent": consent, "approval": approval, "audit": audit,
                "export": export, "share": share, "now": now,
            })
            dap_count += 1

        print(f"    Created {cr_count} consent records, {ar_count} access requests, "
              f"{al_count} audit logs, {cm_count} masks, {dap_count} policies")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ════════════════════════════════════════════════════════════════
    seq_tables = [
        "learning_assessments", "learning_assessment_questions", "learning_assessment_attempts",
        "learning_badges", "learning_user_badges",
        "learning_milestones", "learning_user_milestones", "learning_objectives",
        "learning_labs", "lab_completions",
        "learning_streaks", "learning_study_sessions",
        "learning_user_interests", "learning_progress_checkpoints", "learning_user_checkpoints",
        "learning_user_reports",
        "learning_course_analytics", "learning_course_recommendations",
        "learning_engagement_events", "learning_platform_metrics",
        "literacy_learners", "literacy_tutors", "literacy_tutor_matches",
        "literacy_assessments", "literacy_progress", "literacy_outcomes",
        "literacy_resources", "literacy_collections", "literacy_collection_items",
        "literacy_goals", "literacy_milestones", "literacy_celebrations",
        "literacy_session_schedules", "literacy_session_logs", "literacy_session_notes",
        "literacy_cohorts", "literacy_learner_cohorts",
        "literacy_tutor_qualifications", "literacy_tutor_availability",
        "literacy_tutor_training_records",
        "literacy_impact_metrics", "literacy_resource_recommendations",
        "literacy_consent_records", "literacy_access_requests",
        "literacy_audit_logs", "literacy_confidentiality_masks",
        "literacy_data_access_policies",
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
    print("  Batch learning seeding complete!")
    return True
