# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Literacy Learner Management API Routes.

Endpoints for:
- Learner intake and registration
- Assessment management
- Learner profile updates
- Progress tracking
"""

from app.core.logging import get_logger

logger = get_logger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.models.literacy_learner import (
    LiteracyLearner, AssessmentType, LearnerAssessmentLevel
)
from app.services.literacy_learner_service import LiteraryLearnerService
from app.schemas.literacy import (
    LearnerIntakeRequest, LearnerResponse, AssessmentRequest,
    ProgressResponse, GoalRequest, GoalResponse
)
from .dependencies import require_staff
from fastapi import Depends
from ...models.user import User

router = APIRouter(prefix="/literacy/learners", tags=["literacy_learners"])


@router.post("", response_model=LearnerResponse)
async def create_learner(
    request: LearnerIntakeRequest,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """
    Create a new learner intake record.

    Registers a user as a literacy program learner with initial assessment data.
    """
    service = LiteraryLearnerService(db)

    learner = await service.intake_learner(
        user_id=request.user_id,
        program_id=request.program_id,
        demographics={
            "age": request.age,
            "date_of_birth": request.date_of_birth,
            "native_language": request.native_language,
            "languages_spoken": request.languages_spoken,
            "education_background": request.education_background,
            "employment_status": request.employment_status,
            "income_level": request.income_level,
            "barriers_to_literacy": request.barriers_to_literacy,
            "health_notes": request.health_notes,
            "accessibility_needs": request.accessibility_needs,
            "transportation_needs": request.transportation_needs,
            "childcare_needed": request.childcare_needed,
            "notes": request.notes
        },
        referred_from=request.referred_from
    )

    await db.commit()
    return LearnerResponse.model_validate(learner)


@router.get("/{learner_id}", response_model=LearnerResponse)
async def get_learner(
    learner_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get learner details."""
    service = LiteraryLearnerService(db)
    learner = await service.get_learner(learner_id)

    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    return LearnerResponse.model_validate(learner)


@router.get("", response_model=dict)
async def list_learners(
    program_id: int = Query(...),
    status: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """
    List learners in a program with optional filtering.

    Supports filtering by status and proficiency level.
    """
    service = LiteraryLearnerService(db)

    learners, total = await service.list_learners(
        program_id=program_id,
        limit=limit,
        offset=offset
    )

    return {
        "learners": [LearnerResponse.model_validate(l) for l in learners],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/{learner_id}/assessments")
async def create_assessment(
    learner_id: int,
    request: AssessmentRequest,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Record a literacy assessment for a learner."""
    service = LiteraryLearnerService(db)

    assessment = await service.assess_learner(
        learner_id=learner_id,
        assessor_id=request.assessor_id,
        assessment_type=request.assessment_type,
        score=request.score,
        level=request.level,
        assessment_data={
            "percentage": request.percentage,
            "reading_speed_wpm": request.reading_speed_wpm,
            "comprehension_percentage": request.comprehension_percentage,
            "assessment_tool_used": request.assessment_tool_used,
            "location": request.location,
            "notes": request.notes,
            "total_points": request.total_points
        }
    )

    await db.commit()

    return {
        "id": assessment.id,
        "assessment_type": str(assessment.assessment_type),
        "level": str(assessment.level),
        "score": float(assessment.score),
        "assessment_date": assessment.assessment_date.isoformat()
    }


@router.get("/{learner_id}/progress")
async def get_progress(
    learner_id: int,
    db: AsyncSession = Depends(get_db)
) -> ProgressResponse:
    """Get learner progress summary."""
    from app.services.literacy_progress_service import ProgressTrackingService

    service = ProgressTrackingService(db)
    progress = await service.calculate_progress(learner_id)

    if not progress:
        raise HTTPException(status_code=404, detail="Learner not found")

    return ProgressResponse(**progress)


@router.put("/{learner_id}")
async def update_learner(
    learner_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Update learner profile information."""
    service = LiteraryLearnerService(db)
    learner = await service.update_learner_profile(learner_id, request)

    await db.commit()
    return LearnerResponse.model_validate(learner)


@router.post("/{learner_id}/goals")
async def create_goal(
    learner_id: int,
    request: GoalRequest,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Create a new learning goal for a learner."""
    from app.models.literacy_learner import LiteracyGoal

    goal = LiteracyGoal(
        learner_id=learner_id,
        goal_type=request.goal_type,
        goal_statement=request.goal_statement,
        target_level=request.target_level,
        target_date=request.target_date,
        notes=request.notes
    )
    db.add(goal)
    await db.commit()

    return GoalResponse.model_validate(goal)


@router.get("/{learner_id}/goals")
async def list_learner_goals(
    learner_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all goals for a learner."""
    from app.models.literacy_learner import LiteracyGoal
    from sqlalchemy import select

    goals = await db.scalars(
        select(LiteracyGoal).where(LiteracyGoal.learner_id == learner_id)
    )

    return [GoalResponse.model_validate(g) for g in goals]
