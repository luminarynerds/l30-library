# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Learning - Quiz System API Endpoints

Provides endpoints for:
- Quiz submission
- Quiz attempts
- Quiz results
"""
from app.core.logging import get_logger
from datetime import datetime, timezone

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = get_logger(__name__)

from ...core.database import get_db
from ...core.exceptions import InternalServerError
from ...core.error_codes import ErrorCode
from ...models.learning import (
    Course, Enrollment, Lesson, LessonProgress, Module,
    QuizAttempt, QuizQuestion
)
from ...models.user import User, UserRole
from ...schemas.learning import (
    AdminQuizQuestionCreate,
    AdminQuizQuestionResponse,
    AdminQuizQuestionUpdate,
    QuizQuestionReorderItem,
    QuizResult,
    QuizSubmission,
)
from ...services.quiz_service import QuizService
from .auth import get_current_user
from .dependencies import (
    can_access_course, is_staff_or_admin, require_admin,
)

router = APIRouter(prefix="/learning", tags=["learning-quizzes"])


@router.post("/lessons/{lesson_id}/quiz/submit", response_model=QuizResult)
async def submit_quiz(
    lesson_id: int,
    submission: QuizSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit quiz answers and get results."""
    result = await db.execute(
        select(Lesson)
        .options(
            selectinload(Lesson.quiz_questions),
            selectinload(Lesson.module).selectinload(Module.course)
        )
        .where(Lesson.id == lesson_id, Lesson.lesson_type == "quiz")
    )
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Check course access permission
    if not can_access_course(current_user, lesson.module.course):
        raise HTTPException(
            status_code=403, detail="You don't have access to this quiz"
        )

    # Check enrollment (unless staff/admin)
    enrollment = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id == lesson.module.course_id,
        )
    )
    if not enrollment.scalar_one_or_none() and not is_staff_or_admin(current_user):
        raise HTTPException(
            status_code=403, detail="Please enroll in this course first"
        )

    # Get configurable passing threshold from course (default 70%)
    passing_threshold = 70
    if lesson.module and lesson.module.course:
        passing_threshold = lesson.module.course.quiz_passing_threshold or 70

    questions = {q.id: q for q in lesson.quiz_questions}
    correct_count = 0
    feedback = []
    answer_records: list[dict] = []

    for answer in submission.answers:
        question = questions.get(answer.question_id)
        if not question:
            continue

        options = question.options or []
        is_correct = False

        if 0 <= answer.selected_option_index < len(options):
            is_correct = options[answer.selected_option_index].get("is_correct", False)

        if is_correct:
            correct_count += 1

        feedback.append(
            {
                "question_id": answer.question_id,
                "correct": is_correct,
                "explanation": question.explanation,
            }
        )
        answer_records.append(
            {
                "question_id": answer.question_id,
                "selected_option_index": answer.selected_option_index,
                "is_correct": is_correct,
            }
        )

    # Compute weighted score from option weights (for placement surveys)
    weighted_score = 0
    for answer in submission.answers:
        question = questions.get(answer.question_id)
        if question and question.options and 0 <= answer.selected_option_index < len(question.options):
            opt = question.options[answer.selected_option_index]
            weighted_score += opt.get("weight", 0) if isinstance(opt, dict) else 0

    total = len(lesson.quiz_questions)
    percentage = (correct_count / total * 100) if total > 0 else 0
    passed = percentage >= passing_threshold

    # Persist every submission as a QuizAttempt row so retake history survives
    # regardless of LessonProgress best-score-wins behavior below. started_at is
    # set by the DB server_default; we set completed_at explicitly.
    attempt = QuizAttempt(
        user_id=current_user.id,
        lesson_id=lesson_id,
        score=correct_count,
        passed=passed,
        answers=answer_records,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(attempt)

    progress_result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id == lesson_id,
        )
    )
    progress = progress_result.scalar_one_or_none()

    if progress:
        # Best-score-wins: a retake never regresses an existing record. Keep the
        # max of (previous quiz_score, this attempt's percentage); once a lesson
        # is completed, status and completed_at are preserved across retakes.
        progress.quiz_score = max(progress.quiz_score or 0, int(percentage))
        if progress.status != "completed" and passed:
            progress.status = "completed"
            progress.completed_at = datetime.now(timezone.utc)
    else:
        progress = LessonProgress(
            user_id=current_user.id,
            lesson_id=lesson_id,
            status="completed" if passed else "in_progress",
            quiz_score=int(percentage),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc) if passed else None,
        )
        db.add(progress)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to save quiz submission")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None

    return QuizResult(
        score=correct_count,
        total_questions=total,
        percentage=round(percentage, 1),
        passed=passed,
        feedback=feedback,
        weighted_score=weighted_score,
    )


@router.post("/lessons/{lesson_id}/quiz/start")
async def start_quiz_attempt(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a new quiz attempt for a lesson."""
    result = await db.execute(
        select(Lesson)
        .options(
            selectinload(Lesson.quiz_questions),
            selectinload(Lesson.module).selectinload(Module.course),
        )
        .where(Lesson.id == lesson_id)
    )
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    if lesson.lesson_type != "quiz" and not lesson.quiz_questions:
        raise HTTPException(status_code=400, detail="This lesson does not have a quiz")

    if not can_access_course(current_user, lesson.module.course):
        raise HTTPException(
            status_code=403, detail="You don't have access to this quiz"
        )

    enrollment = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id == lesson.module.course_id,
        )
    )
    if not enrollment.scalar_one_or_none() and not is_staff_or_admin(current_user):
        raise HTTPException(
            status_code=403, detail="Please enroll in this course first"
        )

    attempt = QuizAttempt(
        user_id=current_user.id, lesson_id=lesson_id, score=0, passed=False, answers=[]
    )
    db.add(attempt)
    try:
        await db.commit()
        await db.refresh(attempt)
    except Exception:
        await db.rollback()
        logger.exception("Failed to start quiz attempt")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None

    questions = []
    for q in lesson.quiz_questions:
        options = []
        for opt in q.options or []:
            options.append({"text": opt.get("text", "")})
        questions.append(
            {
                "id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": options,
                "sort_order": q.sort_order,
            }
        )

    questions.sort(key=lambda x: x["sort_order"])

    # Get configurable passing threshold from course (default 70%)
    passing_threshold = 70
    if lesson.module and lesson.module.course:
        passing_threshold = lesson.module.course.quiz_passing_threshold or 70

    return {
        "attempt_id": attempt.id,
        "questions": questions,
        "total_questions": len(questions),
        "passing_score": passing_threshold,
    }

@router.get("/lessons/{lesson_id}/quiz/start", response_model=dict)
async def get_lessons__lesson_id__quiz_start_status(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check eligibility to start a quiz."""
    lesson_result = await db.execute(
        select(Lesson)
        .options(
            selectinload(Lesson.quiz_questions),
            selectinload(Lesson.module).selectinload(Module.course),
        )
        .where(Lesson.id == lesson_id)
    )
    lesson = lesson_result.scalar_one_or_none()

    if not lesson:
        return {"eligible": False, "reason": "Lesson not found"}

    if lesson.lesson_type != "quiz" and not lesson.quiz_questions:
        return {"eligible": False, "reason": "This lesson does not have a quiz"}

    if not can_access_course(current_user, lesson.module.course):
        return {"eligible": False, "reason": "You don't have access to this quiz"}

    if not is_staff_or_admin(current_user):
        enrollment = await db.execute(
            select(Enrollment).where(
                Enrollment.user_id == current_user.id,
                Enrollment.course_id == lesson.module.course_id,
            )
        )
        if not enrollment.scalar_one_or_none():
            return {"eligible": False, "reason": "Please enroll in this course first"}

    return {"eligible": True, "reason": None}



@router.get("/lessons/{lesson_id}/quiz/submit", response_model=dict)
async def get_lessons__lesson_id__quiz_submit(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get quiz submission results for a lesson."""
    progress_result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id == lesson_id,
        )
    )
    progress = progress_result.scalar_one_or_none()

    if not progress or progress.quiz_score is None:
        raise HTTPException(status_code=404, detail="No quiz submission found for this lesson")

    return {
        "lesson_id": lesson_id,
        "quiz_score": progress.quiz_score,
        "status": progress.status,
        "completed_at": progress.completed_at,
        "started_at": progress.started_at,
    }

# ── Admin authoring (Wave 1 / W1-C) ──────────────────────────────────────
# Lesson-scoped POST/PUT/DELETE/reorder for quiz_questions. Previously
# the table existed but had no admin write path - questions were only
# authorable via DB seeder. Guards:
#   - DELETE returns 409 if quiz_attempts exist for the lesson (coarse).
#   - PUT warn-logs (does not block) on options reorder when attempts
#     exist; instructors legitimately fix typos.


@router.post(
    "/admin/lessons/{lesson_id}/quiz-questions",
    response_model=AdminQuizQuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_quiz_question(
    lesson_id: int,
    body: AdminQuizQuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new quiz question scoped to a lesson."""
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    question = QuizQuestion(
        lesson_id=lesson_id,
        question_text=body.question_text,
        question_type=body.question_type,
        options=[opt.model_dump() for opt in body.options],
        explanation=body.explanation,
        sort_order=body.sort_order,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return question


@router.put(
    "/admin/lessons/{lesson_id}/quiz-questions/{question_id}",
    response_model=AdminQuizQuestionResponse,
)
async def admin_update_quiz_question(
    lesson_id: int,
    question_id: int,
    body: AdminQuizQuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Full-replace update of a quiz question.

    Warn-logs (does not block) when ``options`` changes while
    quiz_attempts already reference this lesson, because historical
    score correctness may degrade. Instructors legitimately fix typos,
    so blocking is wrong; logging gives ops a paper trail.
    """
    question = await db.get(QuizQuestion, question_id)
    if not question or question.lesson_id != lesson_id:
        raise HTTPException(status_code=404, detail="Question not found")

    new_options = [opt.model_dump() for opt in body.options]
    if new_options != (question.options or []):
        attempts_exist = await db.scalar(
            select(QuizAttempt.id)
            .where(QuizAttempt.lesson_id == lesson_id)
            .limit(1)
        )
        if attempts_exist:
            logger.warning(
                "quiz_question options changed for lesson_id=%s "
                "question_id=%s while quiz_attempts exist (historical "
                "score correctness may degrade)",
                lesson_id,
                question_id,
            )

    question.question_text = body.question_text
    question.question_type = body.question_type
    question.options = new_options
    question.explanation = body.explanation
    question.sort_order = body.sort_order
    await db.commit()
    await db.refresh(question)
    return question


@router.delete(
    "/admin/lessons/{lesson_id}/quiz-questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_delete_quiz_question(
    lesson_id: int,
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a quiz question. 409 if quiz_attempts exist for the lesson.

    Coarse guard (lesson-level, not question-level) because
    QuizAttempt.answers stores per-question selections inside JSONB so
    there is no FK we can lean on. No override flag this round; if an
    admin truly needs to delete despite attempts, they archive the
    lesson instead.
    """
    question = await db.get(QuizQuestion, question_id)
    if not question or question.lesson_id != lesson_id:
        raise HTTPException(status_code=404, detail="Question not found")

    attempts_count = await db.scalar(
        select(func.count(QuizAttempt.id))
        .where(QuizAttempt.lesson_id == lesson_id)
    )
    if attempts_count and attempts_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete: {attempts_count} quiz_attempts "
                f"reference this lesson."
            ),
        )
    await db.delete(question)
    await db.commit()


@router.patch("/admin/lessons/{lesson_id}/quiz-questions/reorder")
async def admin_reorder_quiz_questions(
    lesson_id: int,
    body: List[QuizQuestionReorderItem],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Bulk sort_order update for a lesson's questions, one transaction.

    Silently skips items whose ``question_id`` either doesn't exist or
    belongs to a different lesson — the lesson_id WHERE clause prevents
    cross-lesson reorders. Returns a count of rows actually touched so
    the caller can detect drift.
    """
    ids = [item.question_id for item in body]
    if not ids:
        return {"reordered": 0}

    result = await db.execute(
        select(QuizQuestion).where(
            QuizQuestion.id.in_(ids),
            QuizQuestion.lesson_id == lesson_id,
        )
    )
    by_id = {q.id: q for q in result.scalars().all()}
    for item in body:
        target = by_id.get(item.question_id)
        if target is not None:
            target.sort_order = item.sort_order
    await db.commit()
    return {"reordered": len(by_id)}
