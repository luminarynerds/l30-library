# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.learning import (
    QuizAttempt, QuizQuestion, Lesson, LessonProgress, ProgressStatus,
    Course
)
from app.schemas.learning import (
    QuizAnswer, QuizResult, QuizSubmitResponse
)


class QuizService:

    @staticmethod
    async def get_lesson_quiz_questions(
        db: AsyncSession,
        lesson_id: int
    ) -> List[QuizQuestion]:
        result = await db.execute(
            select(QuizQuestion)
            .where(QuizQuestion.lesson_id == lesson_id)
            .order_by(QuizQuestion.sort_order)
        )
        return result.scalars().all()

    @staticmethod
    async def grade_quiz_answers(
        answers: List[QuizAnswer],
        questions: List[QuizQuestion],
        passing_threshold: int = 70
    ) -> Tuple[int, int, float, bool, List[Dict[str, Any]]]:
        if not questions:
            return 0, 0, 0.0, False, []

        # Create a mapping of question_id to question for quick lookup
        questions_map = {q.id: q for q in questions}

        score = 0
        feedback = []

        # Grade each answer
        for answer in answers:
            question = questions_map.get(answer.question_id)
            if not question:
                continue

            is_correct = False

            # Check if the selected option is correct
            if question.options and answer.selected_option_index < len(question.options):
                selected_option = question.options[answer.selected_option_index]
                is_correct = selected_option.get("is_correct", False)

            if is_correct:
                score += 1

            # Build feedback for this question
            correct_option_text = None
            correct_option_index = None

            if question.options:
                for idx, option in enumerate(question.options):
                    if option.get("is_correct", False):
                        correct_option_text = option.get("text", "")
                        correct_option_index = idx
                        break

            feedback.append({
                "question_id": answer.question_id,
                "question_text": question.question_text,
                "selected_option_index": answer.selected_option_index,
                "is_correct": is_correct,
                "correct_option_index": correct_option_index,
                "correct_option_text": correct_option_text,
                "explanation": question.explanation
            })

        # Calculate percentage and pass status
        total_questions = len(questions)
        percentage = (score / total_questions * 100) if total_questions > 0 else 0.0
        passed = percentage >= passing_threshold

        return score, total_questions, round(percentage, 2), passed, feedback

    @staticmethod
    async def create_quiz_attempt(
        db: AsyncSession,
        user_id: int,
        lesson_id: int,
        answers: List[QuizAnswer],
        score: int,
        passed: bool
    ) -> QuizAttempt:
        # Format answers with correctness (needs to be filled by grading)
        formatted_answers = [
            {
                "question_id": a.question_id,
                "selected_option_index": a.selected_option_index
            }
            for a in answers
        ]

        attempt = QuizAttempt(
            user_id=user_id,
            lesson_id=lesson_id,
            score=score,
            passed=passed,
            answers=formatted_answers,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )

        db.add(attempt)
        return attempt

    @staticmethod
    async def get_lesson_progress(
        db: AsyncSession,
        user_id: int,
        lesson_id: int
    ) -> Optional[LessonProgress]:
        result = await db.execute(
            select(LessonProgress)
            .where(
                and_(
                    LessonProgress.user_id == user_id,
                    LessonProgress.lesson_id == lesson_id
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_or_create_lesson_progress(
        db: AsyncSession,
        user_id: int,
        lesson_id: int,
        quiz_score: Optional[int] = None,
        passed: bool = False
    ) -> LessonProgress:
        progress = await QuizService.get_lesson_progress(db, user_id, lesson_id)

        if progress:
            # Update existing progress
            progress.status = ProgressStatus.COMPLETED if passed else ProgressStatus.IN_PROGRESS
            progress.quiz_score = quiz_score
            progress.completed_at = datetime.now(timezone.utc)
        else:
            # Create new progress
            progress = LessonProgress(
                user_id=user_id,
                lesson_id=lesson_id,
                status=ProgressStatus.COMPLETED if passed else ProgressStatus.IN_PROGRESS,
                quiz_score=quiz_score,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
            )
            db.add(progress)

        return progress

    @staticmethod
    async def get_quiz_attempts_for_lesson(
        db: AsyncSession,
        user_id: int,
        lesson_id: int
    ) -> List[QuizAttempt]:
        result = await db.execute(
            select(QuizAttempt)
            .where(
                and_(
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.lesson_id == lesson_id
                )
            )
            .order_by(QuizAttempt.completed_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_best_attempt(
        db: AsyncSession,
        user_id: int,
        lesson_id: int
    ) -> Optional[QuizAttempt]:
        result = await db.execute(
            select(QuizAttempt)
            .where(
                and_(
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.lesson_id == lesson_id
                )
            )
            .order_by(QuizAttempt.score.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_lesson_with_quiz(
        db: AsyncSession,
        lesson_id: int
    ) -> Optional[Lesson]:
        result = await db.execute(
            select(Lesson)
            .options(
                selectinload(Lesson.quiz_questions)
            )
            .where(Lesson.id == lesson_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_lesson_passing_score(
        db: AsyncSession,
        lesson_id: int
    ) -> int:
        result = await db.execute(
            select(Course.quiz_passing_threshold)
            .join(Lesson.module)
            .join(Course, Course.id == Lesson.module.course_id)
            .where(Lesson.id == lesson_id)
        )
        threshold = result.scalar_one_or_none()
        return threshold or 70

    @staticmethod
    async def get_attempt_history(
        db: AsyncSession,
        user_id: int,
        lesson_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        attempts = await QuizService.get_quiz_attempts_for_lesson(db, user_id, lesson_id)

        history = []
        for attempt in attempts[:limit]:
            total_questions = len(attempt.answers)
            history.append({
                "attempt_id": attempt.id,
                "score": attempt.score,
                "total_questions": total_questions,
                "percentage": (attempt.score / total_questions * 100) if total_questions > 0 else 0,
                "passed": attempt.passed,
                "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None
            })

        return history
