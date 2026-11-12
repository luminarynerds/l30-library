# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive Learning Platform Seeder

Seeds all 5 phases with realistic data:
- Phase 1: Milestones and objectives
- Phase 2: Streaks, sessions, checkpoints
- Phase 3: Assessments, questions, badges
- Phase 4: Recommendations, interests
- Phase 5: Analytics data (30 days)
"""

import sys
import os
from datetime import date, datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.user import User, UserRole
from app.models.learning import Course, Module, Lesson
from app.models.learning_platform_enhanced import (
    # Phase 1
    Milestone, MilestoneType, LearningObjective, ObjectiveStatus,
    # Phase 2
    LearningStreak, StudySession, ProgressCheckpoint, CheckpointType,
    # Phase 3
    Assessment, AssessmentQuestion, AssessmentType, QuestionType,
    Badge, BadgeType, BadgeRarity,
    # Phase 4
    CourseRecommendation, UserInterest, RecommendationSource, InterestLevel,
    # Phase 5
    PlatformMetric, CourseAnalytics, UserLearningReport, EngagementEvent,
    MetricType, EventType
)

# Database connection - sync version
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@database:5432/lsc_library")
# Convert async URL to sync if needed
if "postgresql+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def seed_phase1_milestones(db: Session):
    """Seed Phase 1: Progress Tracking"""
    print("\n=== Seeding Phase 1: Progress Tracking ===")

    milestones = [
        {
            "title": "First Steps",
            "description": "Complete your first course",
            "milestone_type": MilestoneType.COURSE_COMPLETION,
            "criteria": {"courses": [1]},
            "xp_reward": 100,
            "icon_url": "/icons/first-steps.svg",
            "is_hidden": False,
            "sort_order": 1
        },
        {
            "title": "Learning Enthusiast",
            "description": "Complete 5 courses",
            "milestone_type": MilestoneType.COURSE_COMPLETION,
            "criteria": {"courses": [1, 2, 3, 4, 5]},
            "xp_reward": 500,
            "icon_url": "/icons/enthusiast.svg",
            "is_hidden": False,
            "sort_order": 2
        },
        {
            "title": "Knowledge Seeker",
            "description": "Earn 1000 XP",
            "milestone_type": MilestoneType.XP_THRESHOLD,
            "criteria": {"min_xp": 1000},
            "xp_reward": 200,
            "icon_url": "/icons/seeker.svg",
            "is_hidden": False,
            "sort_order": 3
        },
        {
            "title": "Week Warrior",
            "description": "Maintain a 7-day learning streak",
            "milestone_type": MilestoneType.STREAK_ACHIEVEMENT,
            "criteria": {"min_streak": 7},
            "xp_reward": 250,
            "icon_url": "/icons/week-warrior.svg",
            "is_hidden": False,
            "sort_order": 4
        },
        {
            "title": "Assessment Master",
            "description": "Pass 10 assessments",
            "milestone_type": MilestoneType.ASSESSMENT_PASSED,
            "criteria": {"min_assessments": 10},
            "xp_reward": 300,
            "icon_url": "/icons/assessment-master.svg",
            "is_hidden": False,
            "sort_order": 5
        },
        {
            "title": "Hidden Champion",
            "description": "Secret achievement - Complete all advanced courses",
            "milestone_type": MilestoneType.CUSTOM,
            "criteria": {"special": "all_advanced"},
            "xp_reward": 1000,
            "icon_url": "/icons/champion.svg",
            "is_hidden": True,
            "sort_order": 10
        }
    ]

    milestone_count = 0
    for milestone_data in milestones:
        existing = db.query(Milestone).filter(Milestone.title == milestone_data["title"]).first()
        if existing:
            print(f"  SKIP: {milestone_data['title']} (exists)")
            continue
        # Convert enum values to strings if needed
        data = dict(milestone_data)
        if hasattr(data.get("milestone_type"), "value"):
            data["milestone_type"] = data["milestone_type"].value
        milestone = Milestone(**data)
        db.add(milestone)
        milestone_count += 1
        print(f"  Created milestone: {milestone.title}")

    db.commit()
    print(f"✓ Created {milestone_count} milestones ({len(milestones) - milestone_count} skipped)")


def seed_phase2_engagement(db: Session):
    """Seed Phase 2: Engagement Features"""
    print("\n=== Seeding Phase 2: Engagement Features ===")

    # Get users
    users = db.query(User).limit(5).all()
    courses = db.query(Course).limit(3).all()

    if not users or not courses:
        print("  Skipping - no users or courses found")
        return

    # Create streaks
    streak_count = 0
    for user in users:
        existing = db.query(LearningStreak).filter(LearningStreak.user_id == user.id).first()
        if existing:
            continue
        streak = LearningStreak(
            user_id=user.id,
            current_streak=random.randint(0, 15),
            longest_streak=random.randint(5, 30),
            last_activity_date=date.today() - timedelta(days=random.randint(0, 2)),
            total_active_days=random.randint(10, 50),
            freeze_count=random.randint(0, 2),
            max_freezes=3
        )
        db.add(streak)
        streak_count += 1

    db.commit()
    print(f"✓ Created {streak_count} user streaks")

    # Create study sessions (last 30 days)
    session_count = 0
    for user in users:
        for i in range(random.randint(5, 20)):
            days_ago = random.randint(0, 30)
            session_date = date.today() - timedelta(days=days_ago)
            started = datetime.now() - timedelta(days=days_ago, hours=random.randint(1, 8))

            duration = random.randint(15, 120)

            session = StudySession(
                user_id=user.id,
                session_date=session_date,
                started_at=started,
                ended_at=started + timedelta(minutes=duration),
                duration_minutes=duration,
                course_id=random.choice(courses).id,
                lessons_completed=random.randint(1, 5),
                quizzes_taken=random.randint(0, 3),
                xp_earned=random.randint(10, 100),
                focus_mode_enabled=random.choice([True, False])
            )
            db.add(session)
            session_count += 1

    db.commit()
    print(f"✓ Created {session_count} study sessions")

    # Create checkpoints
    checkpoints = []
    for course in courses[:2]:
        for i in range(3):
            checkpoint = ProgressCheckpoint(
                course_id=course.id,
                title=f"Checkpoint {i+1}: {course.title}",
                description=f"Complete this checkpoint to progress in {course.title}",
                checkpoint_type=random.choice([CheckpointType.QUIZ, CheckpointType.ASSIGNMENT, CheckpointType.PROJECT]),
                sort_order=i,
                is_required=i < 2,  # First 2 are required
                passing_criteria={"min_score": 70},
                xp_reward=50,
                instructions="Complete the assigned tasks and submit your work."
            )
            db.add(checkpoint)
            checkpoints.append(checkpoint)

    db.commit()
    print(f"✓ Created {len(checkpoints)} progress checkpoints")


def seed_phase3_assessments_badges(db: Session):
    """Seed Phase 3: Assessments & Recognition"""
    print("\n=== Seeding Phase 3: Assessments & Recognition ===")

    courses = db.query(Course).limit(3).all()

    if not courses:
        print("  Skipping - no courses found")
        return

    # Create assessments
    assessment_count = 0
    for course in courses:
        for i in range(2):
            assessment = Assessment(
                course_id=course.id,
                title=f"{course.title} - Assessment {i+1}",
                description=f"Test your knowledge of {course.title}",
                assessment_type=random.choice([AssessmentType.QUIZ, AssessmentType.EXAM]),
                time_limit_minutes=random.choice([30, 45, 60]),
                passing_score=70.0,
                max_attempts=3,
                randomize_questions=True,
                show_correct_answers=True,
                is_published=True,
                xp_reward=random.randint(50, 150),
                instructions="Read each question carefully and select the best answer."
            )
            db.add(assessment)
            db.flush()

            # Add questions
            for q_num in range(random.randint(5, 10)):
                question = AssessmentQuestion(
                    assessment_id=assessment.id,
                    question_text=f"Question {q_num+1} for {course.title}",
                    question_type=QuestionType.MULTIPLE_CHOICE,
                    options=[
                        {"text": "Option A", "is_correct": True},
                        {"text": "Option B", "is_correct": False},
                        {"text": "Option C", "is_correct": False},
                        {"text": "Option D", "is_correct": False}
                    ],
                    points=1.0,
                    difficulty="intermediate",
                    explanation="This is the correct answer because...",
                    sort_order=q_num
                )
                db.add(question)

            assessment_count += 1

    db.commit()
    print(f"✓ Created {assessment_count} assessments with questions")

    # Create badges
    badges = [
        {
            "name": "First Login",
            "description": "Welcome to the learning platform!",
            "badge_type": BadgeType.ACHIEVEMENT,
            "rarity": BadgeRarity.COMMON,
            "criteria": {"action": "first_login"},
            "xp_value": 10,
            "icon_url": "/badges/first-login.svg",
            "color_hex": "#3B82F6"
        },
        {
            "name": "Quick Learner",
            "description": "Complete a course in under 2 hours",
            "badge_type": BadgeType.ACHIEVEMENT,
            "rarity": BadgeRarity.UNCOMMON,
            "criteria": {"max_hours": 2},
            "xp_value": 50,
            "icon_url": "/badges/quick-learner.svg",
            "color_hex": "#10B981"
        },
        {
            "name": "Week Streak",
            "description": "Maintain a 7-day learning streak",
            "badge_type": BadgeType.STREAK,
            "rarity": BadgeRarity.UNCOMMON,
            "criteria": {"streak_days": 7},
            "xp_value": 100,
            "icon_url": "/badges/week-streak.svg",
            "color_hex": "#F59E0B"
        },
        {
            "name": "Perfect Score",
            "description": "Score 100% on any assessment",
            "badge_type": BadgeType.ACHIEVEMENT,
            "rarity": BadgeRarity.RARE,
            "criteria": {"score": 100},
            "xp_value": 150,
            "icon_url": "/badges/perfect-score.svg",
            "color_hex": "#8B5CF6"
        },
        {
            "name": "Course Master",
            "description": "Complete 10 courses",
            "badge_type": BadgeType.MILESTONE,
            "rarity": BadgeRarity.RARE,
            "criteria": {"courses_completed": 10},
            "xp_value": 500,
            "icon_url": "/badges/course-master.svg",
            "color_hex": "#EF4444"
        },
        {
            "name": "Legendary Learner",
            "description": "Achieve the highest level of learning mastery",
            "badge_type": BadgeType.SPECIAL,
            "rarity": BadgeRarity.LEGENDARY,
            "criteria": {"total_xp": 10000},
            "xp_value": 1000,
            "icon_url": "/badges/legendary.svg",
            "color_hex": "#FFD700",
            "is_secret": True
        }
    ]

    badge_count = 0
    for badge_data in badges:
        existing = db.query(Badge).filter(Badge.name == badge_data["name"]).first()
        if existing:
            print(f"  SKIP: {badge_data['name']} (exists)")
            continue
        # Convert enum values to strings for VARCHAR columns
        data = dict(badge_data)
        if hasattr(data.get("badge_type"), "value"):
            data["badge_type"] = data["badge_type"].value
        if hasattr(data.get("rarity"), "value"):
            data["rarity"] = data["rarity"].value
        badge = Badge(**data)
        db.add(badge)
        badge_count += 1

    db.commit()
    print(f"✓ Created {badge_count} badges ({len(badges) - badge_count} skipped)")


def seed_phase4_personalization(db: Session):
    """Seed Phase 4: Personalization & Recommendations"""
    print("\n=== Seeding Phase 4: Personalization & Recommendations ===")

    users = db.query(User).limit(5).all()
    courses = db.query(Course).all()

    if not users or not courses:
        print("  Skipping - no users or courses found")
        return

    # Create user interests
    topics = [
        "Data Science", "Web Development", "Machine Learning", "Digital Libraries",
        "Information Architecture", "User Experience", "Cloud Computing",
        "Cybersecurity", "Project Management", "Leadership"
    ]

    # Check if user interests already exist
    existing_interest_count = db.query(UserInterest).count()
    if existing_interest_count > 0:
        print(f"  SKIP: User interests already seeded ({existing_interest_count} exist)")
    else:
        interest_count = 0
        for user in users:
            user_topics = random.sample(topics, random.randint(3, 6))
            for topic in user_topics:
                interest = UserInterest(
                    user_id=user.id,
                    topic=topic,
                    interest_level=random.choice([InterestLevel.MEDIUM, InterestLevel.HIGH, InterestLevel.VERY_HIGH]),
                    source="explicit",
                    confidence_score=random.uniform(0.6, 1.0),
                    engagement_count=random.randint(1, 10),
                    last_engaged_at=datetime.now() - timedelta(days=random.randint(0, 30))
                )
                db.add(interest)
                interest_count += 1

        db.commit()
        print(f"✓ Created {interest_count} user interests")

    # Create course recommendations
    existing_rec_count = db.query(CourseRecommendation).count()
    if existing_rec_count > 0:
        print(f"  SKIP: Course recommendations already seeded ({existing_rec_count} exist)")
    else:
        rec_count = 0
        for user in users:
            recommended_courses = random.sample(courses, min(5, len(courses)))
            for course in recommended_courses:
                recommendation = CourseRecommendation(
                    user_id=user.id,
                    course_id=course.id,
                    recommendation_source=random.choice([
                        RecommendationSource.PERSONALIZED,
                        RecommendationSource.SKILL_GAP,
                        RecommendationSource.TRENDING
                    ]),
                    relevance_score=random.uniform(0.5, 1.0),
                    reason=random.choice([
                        "Based on your learning history",
                        "Popular among similar learners",
                        "Matches your interests in data science",
                        "Recommended to fill skill gaps"
                    ]),
                    is_viewed=random.choice([True, False]),
                    viewed_at=datetime.now() - timedelta(days=random.randint(0, 7)) if random.random() > 0.5 else None
                )
                db.add(recommendation)
                rec_count += 1

        db.commit()
        print(f"✓ Created {rec_count} course recommendations")


def seed_phase5_analytics(db: Session):
    """Seed Phase 5: Analytics & Reporting"""
    print("\n=== Seeding Phase 5: Analytics & Reporting ===")

    users = db.query(User).limit(5).all()
    courses = db.query(Course).limit(3).all()
    lessons = db.query(Lesson).limit(10).all()

    if not users or not courses:
        print("  Skipping - no users or courses found")
        return

    # Check if analytics already seeded
    existing_metrics = db.query(PlatformMetric).count()
    if existing_metrics > 0:
        print(f"  SKIP: Analytics already seeded ({existing_metrics} metrics exist)")
        return

    # Create platform metrics for last 30 days
    metric_count = 0
    for i in range(30):
        metric_date = date.today() - timedelta(days=i)

        # Enrollment metric
        enrollment_metric = PlatformMetric(
            metric_date=metric_date,
            metric_type=MetricType.ENROLLMENT,
            value=random.randint(5, 25),
            previous_value=random.randint(5, 25),
            period="daily"
        )
        db.add(enrollment_metric)

        # Completion metric
        completion_metric = PlatformMetric(
            metric_date=metric_date,
            metric_type=MetricType.COMPLETION,
            value=random.randint(2, 10),
            previous_value=random.randint(2, 10),
            period="daily"
        )
        db.add(completion_metric)

        # Engagement metric
        engagement_metric = PlatformMetric(
            metric_date=metric_date,
            metric_type=MetricType.ENGAGEMENT,
            value=random.randint(100, 500),
            period="daily"
        )
        db.add(engagement_metric)

        metric_count += 3

    db.commit()
    print(f"✓ Created {metric_count} platform metrics (30 days)")

    # Create course analytics
    analytics_count = 0
    for course in courses:
        for i in range(30):
            analytics_date = date.today() - timedelta(days=i)

            analytics = CourseAnalytics(
                course_id=course.id,
                analytics_date=analytics_date,
                total_enrollments=random.randint(10, 100),
                new_enrollments=random.randint(0, 10),
                active_enrollments=random.randint(5, 50),
                completions=random.randint(0, 5),
                completion_rate=random.uniform(10, 60),
                average_completion_days=random.uniform(5, 30),
                total_time_minutes=random.randint(100, 1000),
                average_time_per_user=random.uniform(30, 180),
                lessons_completed=random.randint(10, 100),
                quizzes_taken=random.randint(5, 50),
                average_quiz_score=random.uniform(60, 95),
                pass_rate=random.uniform(70, 95),
                average_rating=random.uniform(3.5, 5.0),
                total_ratings=random.randint(5, 50)
            )
            db.add(analytics)
            analytics_count += 1

    db.commit()
    print(f"✓ Created {analytics_count} course analytics records")

    # Create user learning reports
    report_count = 0
    for user in users:
        # Weekly reports for last 4 weeks
        for week in range(4):
            report_date = date.today() - timedelta(weeks=week)
            period_start = report_date - timedelta(days=7)

            report = UserLearningReport(
                user_id=user.id,
                report_date=report_date,
                report_type="weekly",
                period_start=period_start,
                period_end=report_date,
                total_time_minutes=random.randint(60, 500),
                lessons_completed=random.randint(5, 30),
                courses_completed=random.randint(0, 3),
                xp_earned=random.randint(50, 500),
                badges_earned=random.randint(0, 3),
                current_streak=random.randint(0, 15),
                active_days=random.randint(3, 7),
                courses_in_progress=random.randint(1, 5),
                completion_rate=random.uniform(30, 80),
                assessments_taken=random.randint(1, 5),
                average_assessment_score=random.uniform(70, 95),
                goals_completed=random.randint(0, 3),
                goals_in_progress=random.randint(1, 5)
            )
            db.add(report)
            report_count += 1

    db.commit()
    print(f"✓ Created {report_count} user learning reports")

    # Create engagement events
    event_count = 0
    event_types = [
        EventType.LOGIN, EventType.COURSE_VIEW, EventType.LESSON_START,
        EventType.LESSON_COMPLETE, EventType.QUIZ_ATTEMPT, EventType.VIDEO_WATCH
    ]

    for user in users:
        for i in range(random.randint(20, 50)):
            days_ago = random.randint(0, 30)
            event_date = date.today() - timedelta(days=days_ago)
            event_timestamp = datetime.now() - timedelta(
                days=days_ago,
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )

            event = EngagementEvent(
                user_id=user.id,
                event_type=random.choice(event_types),
                event_date=event_date,
                event_timestamp=event_timestamp,
                course_id=random.choice(courses).id if random.random() > 0.3 else None,
                lesson_id=random.choice(lessons).id if random.random() > 0.5 else None,
                event_data={"sample": "data"},
                duration_seconds=random.randint(30, 3600) if random.random() > 0.5 else None
            )
            db.add(event)
            event_count += 1

    db.commit()
    print(f"✓ Created {event_count} engagement events")


def verify_seed_data(db: Session):
    """Verify that all data was seeded correctly"""
    print("\n=== Verifying Seed Data ===")

    # Count records in each table
    counts = {
        "Milestones": db.query(Milestone).count(),
        "Learning Objectives": db.query(LearningObjective).count(),
        "Streaks": db.query(LearningStreak).count(),
        "Study Sessions": db.query(StudySession).count(),
        "Checkpoints": db.query(ProgressCheckpoint).count(),
        "Assessments": db.query(Assessment).count(),
        "Assessment Questions": db.query(AssessmentQuestion).count(),
        "Badges": db.query(Badge).count(),
        "User Interests": db.query(UserInterest).count(),
        "Course Recommendations": db.query(CourseRecommendation).count(),
        "Platform Metrics": db.query(PlatformMetric).count(),
        "Course Analytics": db.query(CourseAnalytics).count(),
        "User Reports": db.query(UserLearningReport).count(),
        "Engagement Events": db.query(EngagementEvent).count()
    }

    for table, count in counts.items():
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {table}: {count} records")

    total_records = sum(counts.values())
    print(f"\n✓ Total records created: {total_records}")

    return total_records > 0


def main():
    """Main seeding function"""
    print("=" * 60)
    print("LEARNING PLATFORM COMPREHENSIVE SEEDER")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Seed all phases
        seed_phase1_milestones(db)
        seed_phase2_engagement(db)
        seed_phase3_assessments_badges(db)
        seed_phase4_personalization(db)
        seed_phase5_analytics(db)

        # Verify
        success = verify_seed_data(db)

        if success:
            print("\n" + "=" * 60)
            print("✓ SEEDING COMPLETED SUCCESSFULLY!")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("✗ SEEDING FAILED - No data created")
            print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
