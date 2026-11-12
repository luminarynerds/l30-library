# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import random
from datetime import datetime, date, timedelta, timezone
from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


def _past_date(days_ago: int) -> date:
    return (datetime.now(utc) - timedelta(days=days_ago)).date()


def _future_date(days_ahead: int) -> date:
    return (datetime.now(utc) + timedelta(days=days_ahead)).date()


async def seed_learning_content(session: AsyncSession) -> bool:

    # Get reusable IDs
    users_r = await session.execute(text("SELECT id, role FROM users LIMIT 200"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    all_user_ids = [u[0] for u in users]

    if not staff_ids:
        print("  ⚠ No staff users found. Skipping learning content seed.")
        return False

    print(f"  → Found {len(staff_ids)} staff users, {len(all_user_ids)} total users")

    now = datetime.now(utc)

    # Check if already seeded
    courses_count = await session.execute(text("SELECT COUNT(*) FROM courses"))
    if courses_count.scalar() > 0:
        print("  → Learning content already seeded. Skipping.")
        return True

    print("  Seeding TIER 1: Courses, Modules, Lessons, Resources...")

    # COURSES (17 courses)
    courses_data = [
        ("Library Systems Fundamentals", "Introduction to library operations, circulation, and basic ILS concepts", "staff", "beginner", 120, 200),
        ("Customer Service Excellence", "Core principles of patron service, communication, and conflict resolution", "staff", "beginner", 90, 150),
        ("Library Policies & Procedures", "Comprehensive guide to library policies, conduct standards, and best practices", "staff", "intermediate", 150, 200),
        ("New Staff Onboarding Program", "Complete first-week orientation for new library employees", "staff", "beginner", 240, 300),
        ("Emergency Procedures & Safety", "Fire safety, evacuation procedures, and emergency protocols", "staff", "intermediate", 75, 180),
        ("ADA Accessibility Requirements", "Americans with Disabilities Act compliance and accessibility standards", "staff", "intermediate", 100, 200),
        ("Data Privacy & Security", "Patron privacy, data protection, and information security protocols", "staff", "advanced", 120, 250),
        ("ILS Training: Cataloging Basics", "Integrated Library System cataloging fundamentals and MARC records", "staff", "intermediate", 180, 250),
        ("Digital Resources Management", "Ebooks, audiobooks, databases, and digital collection platforms", "staff", "intermediate", 150, 220),
        ("RFID Technology & Inventory", "RFID tag use, self-checkout systems, and inventory management", "staff", "intermediate", 100, 180),
        ("Technology Troubleshooting", "Common tech issues, device support, and WiFi assistance", "staff", "advanced", 120, 200),
        ("Advanced Cataloging & Classification", "Dewey Decimal System, subject headings, and advanced cataloging", "staff", "advanced", 200, 300),
        ("Reference Services & Reader's Advisory", "Research assistance, reader's advisory techniques, and collection knowledge", "staff", "intermediate", 130, 220),
        ("Programming & Community Engagement", "Event planning, program evaluation, and community partnership development", "staff", "intermediate", 110, 200),
        ("Supervision & Staff Management", "Leadership skills, performance management, and team building", "staff", "advanced", 140, 280),
        ("Collection Development for All Ages", "Building diverse collections: children, YA, adult, and special formats", "staff", "intermediate", 140, 220),
        ("Meeting Community Needs", "Inclusive services, multicultural programming, and outreach strategies", "staff", "intermediate", 100, 180),
    ]

    course_ids = []
    for title, desc, access, difficulty, minutes, xp in courses_data:
        r = await session.execute(text("""
            INSERT INTO courses (title, description, access_level, difficulty, estimated_minutes, xp_reward, lifecycle_stage, quiz_passing_threshold)
            VALUES (:title, :desc, :access, :difficulty, :minutes, :xp, 'published', 70)
            RETURNING id
        """), {"title": title, "desc": desc, "access": access, "difficulty": difficulty, "minutes": minutes, "xp": xp})
        course_ids.append(r.scalar())

    print(f"    ✓ Created {len(course_ids)} courses")

    # MODULES (3-5 per course, ~70 total)
    module_ids = []
    modules_by_course = {}

    module_templates = {
        "Library Systems Fundamentals": ["What is a Library?", "ILS Overview", "Collections & Organization", "Circulation Basics"],
        "Customer Service Excellence": ["Active Listening & Communication", "Handling Difficult Situations", "Accessibility & Inclusion", "Professional Behavior"],
        "Library Policies & Procedures": ["Code of Conduct", "Library Hours & Services", "Patron Rights & Responsibilities", "Staff Handbook Overview", "Incident Reporting"],
        "New Staff Onboarding Program": ["First Day Orientation", "System Logins & Security", "Tour & Facility Familiarization", "Meet Your Team", "First Week Tasks"],
        "Emergency Procedures & Safety": ["Fire Safety & Evacuation", "Medical Emergencies", "Active Threat Response", "Severe Weather Procedures", "Reporting & Documentation"],
        "ADA Accessibility Requirements": ["ADA Overview & Rights", "Physical Accessibility", "Digital Accessibility (WCAG)", "Service Animals & Accommodations", "Reasonable Accommodations Process"],
        "Data Privacy & Security": ["FERPA & COPPA Overview", "Patron Records Protection", "Password Security", "Incident Response", "Compliance Best Practices"],
        "ILS Training: Cataloging Basics": ["MARC Records 101", "Creating Catalog Records", "Subject Headings & Classification", "Item Records & Holdings", "Quality Control"],
        "Digital Resources Management": ["Ebook Platforms", "Audiobook Services", "Database Access & Troubleshooting", "License Compliance", "User Support"],
        "RFID Technology & Inventory": ["RFID System Overview", "Self-Checkout Operation", "Inventory Management", "Tag Maintenance", "Troubleshooting"],
        "Technology Troubleshooting": ["Computer Basics", "Printer & Scanner Issues", "WiFi Connectivity", "Device Support", "When to Escalate"],
        "Advanced Cataloging & Classification": ["Dewey Decimal Deep Dive", "RDA & Cataloging Standards", "Complex Formats", "Authority Control", "Batch Cataloging"],
        "Reference Services & Reader's Advisory": ["Reference Interview Techniques", "Research Strategies", "Reader's Advisory Methods", "Collection Recommendations", "Avoiding Censorship Issues"],
        "Programming & Community Engagement": ["Program Planning & Assessment", "Inclusive Programming", "Community Partnerships", "Marketing & Outreach", "Budget & Resources"],
        "Supervision & Staff Management": ["Leadership Fundamentals", "Performance Management", "Conflict Resolution", "Diversity & Inclusion", "Team Development"],
        "Collection Development for All Ages": ["Collection Policies", "Children's Collections", "YA Materials & Services", "Adult Collections", "Special Formats"],
        "Meeting Community Needs": ["Multicultural Services", "Accessibility & Inclusion", "Marginalized Communities", "Outreach Strategies", "Evaluation & Feedback"],
    }

    course_idx = 0
    for course_id in course_ids:
        course_title = courses_data[course_idx][0]
        module_titles = module_templates.get(course_title, ["Module 1", "Module 2", "Module 3"])
        course_modules = []

        for sort_order, module_title in enumerate(module_titles):
            r = await session.execute(text("""
                INSERT INTO modules (course_id, title, description, sort_order)
                VALUES (:course_id, :title, '', :order)
                RETURNING id
            """), {"course_id": course_id, "title": module_title, "order": sort_order})
            module_id = r.scalar()
            module_ids.append(module_id)
            course_modules.append(module_id)

        modules_by_course[course_id] = course_modules
        course_idx += 1

    print(f"    ✓ Created {len(module_ids)} modules")

    # LESSONS (2-4 per module, ~200 total)
    lesson_ids = []
    lessons_by_module = {}
    lesson_types = ["article", "video", "quiz"]

    for module_id in module_ids:
        module_lessons = []
        for lesson_order in range(random.randint(2, 4)):
            lesson_type = random.choice(lesson_types)
            content = json.dumps({"format": lesson_type, "data": f"Content for {lesson_type}"})

            r = await session.execute(text("""
                INSERT INTO lessons (module_id, title, lesson_type, content, estimated_minutes, sort_order, summary)
                VALUES (:module_id, :title, :lesson_type, :content, :minutes, :order, :summary)
                RETURNING id
            """), {
                "module_id": module_id,
                "title": f"Lesson {lesson_order + 1}",
                "lesson_type": lesson_type,
                "content": content,
                "minutes": random.randint(10, 30),
                "order": lesson_order,
                "summary": "This lesson covers important concepts in the module.",
            })
            lesson_id = r.scalar()
            lesson_ids.append(lesson_id)
            module_lessons.append(lesson_id)

        lessons_by_module[module_id] = module_lessons

    print(f"    ✓ Created {len(lesson_ids)} lessons")

    # QUIZ QUESTIONS (3-5 per module, ~250 total)
    for module_id in module_ids:
        module_lessons = lessons_by_module.get(module_id, [])
        if not module_lessons:
            continue

        for question_order in range(random.randint(3, 5)):
            lesson_id = random.choice(module_lessons)
            options = json.dumps([
                {"text": "Correct answer", "is_correct": True},
                {"text": "Incorrect option 1", "is_correct": False},
                {"text": "Incorrect option 2", "is_correct": False},
                {"text": "Incorrect option 3", "is_correct": False},
            ])

            await session.execute(text("""
                INSERT INTO quiz_questions (lesson_id, question_text, question_type, options, explanation, sort_order)
                VALUES (:lesson_id, :question, 'multiple_choice', :options, :explanation, :order)
            """), {
                "lesson_id": lesson_id,
                "question": f"Question {question_order + 1}: What is the correct answer?",
                "options": options,
                "explanation": "This is the correct answer because...",
                "order": question_order,
            })

    print(f"    ✓ Created quiz questions")

    # LEARNING PATHS (5-6 paths)
    learning_paths_data = [
        ("New Hire Orientation", "Complete onboarding for new library staff members", "beginner", ["onboarding", "required"], [0, 1, 2, 3]),
        ("Circulation Professional", "Master circulation, patron services, and customer service", "intermediate", ["circulation", "patron-facing"], [0, 1, 8]),
        ("Technology Specialist", "Deep dive into library technology and digital resources", "advanced", ["technology", "digital"], [8, 9, 10, 11]),
        ("Programming Expert", "Plan and execute engaging library programs and events", "intermediate", ["programming", "community"], [13, 16, 17]),
        ("Leadership Track", "Develop supervisory and management skills", "advanced", ["leadership", "management"], [1, 14]),
        ("Compliance & Safety", "Master safety, privacy, and regulatory compliance", "intermediate", ["safety", "compliance"], [4, 5, 6]),
    ]

    path_ids = []
    admin_user_id = staff_ids[0] if staff_ids else None

    for title, desc, difficulty, tags, course_positions in learning_paths_data:
        r = await session.execute(text("""
            INSERT INTO learning_paths (title, description, status, is_public, difficulty, tags, enforce_prerequisites, created_by_id)
            VALUES (:title, :desc, 'published', true, :difficulty, :tags, true, :created_by)
            RETURNING id
        """), {
            "title": title,
            "desc": desc,
            "difficulty": difficulty,
            "tags": json.dumps(tags),
            "created_by": admin_user_id,
        })
        path_ids.append(r.scalar())

    print(f"    ✓ Created {len(path_ids)} learning paths")

    # PATH COURSES
    for path_idx, path_id in enumerate(path_ids):
        course_positions = learning_paths_data[path_idx][4]
        for sort_order, course_idx in enumerate(course_positions):
            if course_idx < len(course_ids):
                await session.execute(text("""
                    INSERT INTO path_courses (learning_path_id, course_id, sort_order, is_required, prerequisite_course_ids)
                    VALUES (:path_id, :course_id, :order, true, '[]')
                """), {"path_id": path_id, "course_id": course_ids[course_idx], "order": sort_order})

    print(f"    ✓ Linked courses to learning paths")

    # ENROLLMENTS (user → course)
    for staff_id in staff_ids[:100]:
        num_courses = random.randint(2, 8)
        courses_to_enroll = random.sample(course_ids, min(num_courses, len(course_ids)))

        for course_id in courses_to_enroll:
            await session.execute(text("""
                INSERT INTO enrollments (user_id, course_id, enrolled_at, completed_at)
                VALUES (:user_id, :course_id, :enrolled_at, :completed_at)
            """), {
                "user_id": staff_id,
                "course_id": course_id,
                "enrolled_at": _past(random.randint(1, 180)),
                "completed_at": _past(random.randint(1, 90)) if random.random() > 0.6 else None,
            })

    print(f"    ✓ Created course enrollments")

    # PATH ENROLLMENTS
    for staff_id in random.sample(staff_ids, min(80, len(staff_ids))):
        num_paths = random.randint(1, 3)
        paths_to_enroll = random.sample(path_ids, min(num_paths, len(path_ids)))

        for path_id in paths_to_enroll:
            status = random.choice(["not_started", "in_progress", "completed"])
            progress = 0 if status == "not_started" else (100 if status == "completed" else random.randint(10, 90))

            await session.execute(text("""
                INSERT INTO path_enrollments (user_id, learning_path_id, status, progress_percentage, enrolled_at, started_at, completed_at, completed_course_ids)
                VALUES (:user_id, :path_id, :status, :progress, :enrolled_at, :started_at, :completed_at, '[]')
            """), {
                "user_id": staff_id,
                "path_id": path_id,
                "status": status,
                "progress": progress,
                "enrolled_at": _past(random.randint(1, 180)),
                "started_at": _past(random.randint(1, 180)) if status != "not_started" else None,
                "completed_at": _past(random.randint(1, 90)) if status == "completed" else None,
            })

    print(f"    ✓ Created path enrollments")

    # LESSON PROGRESS
    for staff_id in random.sample(staff_ids, min(150, len(staff_ids))):
        lessons_to_complete = random.sample(lesson_ids, min(random.randint(3, 15), len(lesson_ids)))

        for lesson_id in lessons_to_complete:
            status = random.choice(["not_started", "in_progress", "completed"])
            quiz_score = random.randint(60, 100) if status in ("in_progress", "completed") else None

            await session.execute(text("""
                INSERT INTO lesson_progress (user_id, lesson_id, status, quiz_score, scroll_position, started_at, completed_at, variants_viewed)
                VALUES (:user_id, :lesson_id, :status, :score, :scroll, :started_at, :completed_at, '[]')
                ON CONFLICT (user_id, lesson_id) DO NOTHING
            """), {
                "user_id": staff_id,
                "lesson_id": lesson_id,
                "status": status,
                "score": quiz_score,
                "scroll": random.uniform(0, 100) if status != "not_started" else None,
                "started_at": _past(random.randint(1, 120)) if status != "not_started" else None,
                "completed_at": _past(random.randint(1, 60)) if status == "completed" else None,
            })

    print(f"    ✓ Created lesson progress records")

    # CERTIFICATES
    for staff_id in random.sample(staff_ids, min(150, len(staff_ids))):
        courses_to_certificate = random.sample(course_ids, min(random.randint(1, 5), len(course_ids)))

        for course_id in courses_to_certificate:
            cert_num = f"CERT-{staff_id}-{course_id}-{random.randint(10000, 99999)}"

            await session.execute(text("""
                INSERT INTO certificates (user_id, course_id, certificate_number, issued_at)
                VALUES (:user_id, :course_id, :cert_num, :issued_at)
                ON CONFLICT DO NOTHING
            """), {
                "user_id": staff_id,
                "course_id": course_id,
                "cert_num": cert_num,
                "issued_at": _past(random.randint(1, 90)),
            })

    print(f"    ✓ Created certificates")

    # BADGES (12 badges)
    badges_data = [
        ("First Course", "Completed your first course", "achievement", "common", 50, {"courses_completed": 1}),
        ("Quick Learner", "Completed 5 courses", "achievement", "uncommon", 150, {"courses_completed": 5}),
        ("Safety Star", "Completed all safety and compliance courses", "skill", "uncommon", 200, {"courses": [4, 5, 6]}),
        ("Tech Whiz", "Master of library technology", "skill", "rare", 300, {"courses": [8, 9, 10, 11]}),
        ("7-Day Streak", "Maintained a 7-day learning streak", "streak", "uncommon", 100, {"streak_days": 7}),
        ("30-Day Streak", "Maintained a 30-day learning streak", "streak", "rare", 300, {"streak_days": 30}),
        ("Quiz Master", "Passed 10 quizzes with 90%+ score", "achievement", "rare", 250, {"quiz_passes": 10, "min_score": 90}),
        ("Onboarding Champion", "Completed the full New Hire Orientation path", "milestone", "uncommon", 200, {"path_id": path_ids[0] if path_ids else 0}),
        ("Knowledge Keeper", "Viewed 50 knowledge base articles", "achievement", "common", 75, {"articles_viewed": 50}),
        ("Community Builder", "Completed Programming Expert path", "milestone", "rare", 250, {"path_id": path_ids[3] if len(path_ids) > 3 else 0}),
        ("Learning Legend", "Earned 10 badges", "special", "epic", 500, {"badges_earned": 10}),
        ("Leader in the Making", "Completed Leadership Track", "milestone", "epic", 400, {"path_id": path_ids[4] if len(path_ids) > 4 else 0}),
    ]

    badge_ids = []
    for name, desc, badge_type, rarity, xp, criteria in badges_data:
        r = await session.execute(text("""
            INSERT INTO learning_badges (name, description, badge_type, rarity, criteria, xp_value, is_active, is_secret)
            VALUES (:name, :desc, :type, :rarity, :criteria, :xp, true, false)
            ON CONFLICT (name) DO UPDATE SET description = :desc
            RETURNING id
        """), {
            "name": name,
            "desc": desc,
            "type": badge_type,
            "rarity": rarity,
            "criteria": json.dumps(criteria),
            "xp": xp,
        })
        badge_ids.append(r.scalar())

    print(f"    ✓ Created {len(badge_ids)} badges")

    # USER BADGES
    for staff_id in random.sample(staff_ids, min(120, len(staff_ids))):
        badges_to_award = random.sample(badge_ids, min(random.randint(1, 8), len(badge_ids)))

        for badge_id in badges_to_award:
            await session.execute(text("""
                INSERT INTO learning_user_badges (user_id, badge_id, earned_at, is_showcased)
                VALUES (:user_id, :badge_id, :earned_at, :showcased)
                ON CONFLICT (user_id, badge_id, earned_at) DO NOTHING
            """), {
                "user_id": staff_id,
                "badge_id": badge_id,
                "earned_at": _past(random.randint(1, 150)),
                "showcased": random.random() > 0.5,
            })

    print(f"    ✓ Created user badge awards")

    # LEARNING STREAKS
    for staff_id in random.sample(staff_ids, min(80, len(staff_ids))):
        await session.execute(text("""
            INSERT INTO learning_streaks (user_id, current_streak, longest_streak, last_activity_date, freeze_count, total_active_days)
            VALUES (:user_id, :current, :longest, :last_activity, :freeze, :total_days)
            ON CONFLICT (user_id) DO NOTHING
        """), {
            "user_id": staff_id,
            "current": random.randint(0, 45),
            "longest": random.randint(5, 150),
            "last_activity": _past_date(random.randint(0, 30)),
            "freeze": random.randint(0, 2),
            "total_days": random.randint(10, 200),
        })

    print(f"    ✓ Created learning streaks")

    # COURSE FEEDBACK
    feedback_types = ["helpful", "not_helpful", "content_error", "accessibility"]
    feedback_statuses = ["pending", "reviewed", "resolved"]

    for _ in range(100):
        user_id = random.choice(staff_ids) if staff_ids else None
        course_id = random.choice(course_ids) if course_ids else None

        if user_id and course_id:
            await session.execute(text("""
                INSERT INTO course_feedback (user_id, course_id, feedback_type, rating, comment, status)
                VALUES (:user_id, :course_id, :type, :rating, :comment, :status)
            """), {
                "user_id": user_id,
                "course_id": course_id,
                "type": random.choice(feedback_types),
                "rating": random.uniform(1, 5),
                "comment": "Great content!" if random.random() > 0.5 else "Could improve",
                "status": random.choice(feedback_statuses),
            })

    print(f"    ✓ Created course feedback")

    await session.commit()

    # VERIFICATION
    print("  Verifying seed completion...")

    verification_queries = [
        ("courses", "SELECT COUNT(*) FROM courses"),
        ("modules", "SELECT COUNT(*) FROM modules"),
        ("lessons", "SELECT COUNT(*) FROM lessons"),
        ("quiz_questions", "SELECT COUNT(*) FROM quiz_questions"),
        ("enrollments", "SELECT COUNT(*) FROM enrollments"),
        ("path_enrollments", "SELECT COUNT(*) FROM path_enrollments"),
        ("lesson_progress", "SELECT COUNT(*) FROM lesson_progress"),
        ("certificates", "SELECT COUNT(*) FROM certificates"),
        ("learning_badges", "SELECT COUNT(*) FROM learning_badges"),
        ("learning_user_badges", "SELECT COUNT(*) FROM learning_user_badges"),
        ("learning_streaks", "SELECT COUNT(*) FROM learning_streaks"),
        ("course_feedback", "SELECT COUNT(*) FROM course_feedback"),
    ]

    print("  ✓ Seed counts:")
    for table_name, query in verification_queries:
        result = await session.execute(text(query))
        count = result.scalar()
        print(f"    {table_name:40s} {count:6d} rows")

    print("  ✓ Learning content seed completed successfully!")
    return True
