# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Literacy Outcomes and Impact Reporting API Routes.

Endpoints for:
- Learner outcomes (GED, employment, education)
- Impact metrics and reporting
- Cohort analysis
- Program effectiveness tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.models.literacy_outcomes import (
    LiteracyOutcome, LiteracyProgramOutcomeMetrics, LiteracyCohort,
    LiteracyLearnerCohort, OutcomeType, ReportingPeriod
)
from app.models.literacy_learner import LiteracyLearner
from app.schemas.literacy import (
    OutcomeRequest, OutcomeResponse, ImpactMetricsResponse
)
from .dependencies import require_staff
from fastapi import Depends
from ...models.user import User

router = APIRouter(prefix="/literacy", tags=["literacy_outcomes"])


@router.post("/outcomes/{learner_id}/record")
async def record_outcome(
    learner_id: int,
    request: OutcomeRequest,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """
    Record a learner achievement or outcome.

    Tracks GED completion, employment gains, education advancement, etc.
    """
    learner = await db.get(LiteracyLearner, learner_id)
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    outcome = LiteracyOutcome(
        learner_id=learner_id,
        outcome_type=request.outcome_type,
        outcome_date=request.outcome_date,
        ged_score=request.ged_score,
        ged_passed=request.ged_passed,
        ged_subject_scores=request.ged_subject_scores if hasattr(request, 'ged_subject_scores') else None,
        employment_job_title=request.employment_job_title,
        employment_employer=request.employment_employer,
        education_institution=request.education_institution,
        details=request.details
    )
    db.add(outcome)
    await db.commit()
    await db.refresh(outcome)

    return {
        "id": outcome.id,
        "learner_id": outcome.learner_id,
        "outcome_type": request.outcome_type,
        "outcome_date": outcome.outcome_date.isoformat(),
        "message": f"Outcome recorded: {request.outcome_type}"
    }


@router.get("/outcomes")
async def list_outcomes(
    program_id: Optional[int] = Query(None),
    outcome_type: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    verified_only: bool = Query(False),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """
    List learner outcomes with optional filtering.

    Supports filtering by outcome type, date range, and verification status.
    """
    query = select(LiteracyOutcome)

    if outcome_type:
        query = query.where(LiteracyOutcome.outcome_type == outcome_type)

    if from_date:
        query = query.where(LiteracyOutcome.outcome_date >= from_date)

    if to_date:
        query = query.where(LiteracyOutcome.outcome_date <= to_date)

    if verified_only:
        query = query.where(LiteracyOutcome.is_verified == True)

    outcomes = await db.scalars(
        query.order_by(LiteracyOutcome.outcome_date.desc())
             .limit(limit)
             .offset(offset)
    )

    return [
        {
            "id": outcome.id,
            "learner_id": outcome.learner_id,
            "outcome_type": str(outcome.outcome_type),
            "outcome_date": outcome.outcome_date.isoformat(),
            "is_verified": outcome.is_verified,
            "details": outcome.details
        }
        for outcome in outcomes
    ]


@router.get("/outcomes/ged-completions")
async def get_ged_completions(
    program_id: Optional[int] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get GED completion statistics."""
    query = select(LiteracyOutcome).where(
        LiteracyOutcome.outcome_type == "ged_passed"
    )

    if from_date:
        query = query.where(LiteracyOutcome.outcome_date >= from_date)

    if to_date:
        query = query.where(LiteracyOutcome.outcome_date <= to_date)

    ged_outcomes = await db.scalars(query)
    outcomes = list(ged_outcomes)

    # Calculate pass rate
    total_ged_attempts = await db.scalar(
        select(func.count(LiteracyOutcome.id)).where(
            LiteracyOutcome.outcome_type.in_(["ged_passed", "ged_failed"])
        )
    )

    pass_count = len(outcomes)
    pass_rate = (pass_count / total_ged_attempts * 100) if total_ged_attempts else 0

    return {
        "ged_completions": pass_count,
        "ged_attempts": total_ged_attempts,
        "pass_rate_percentage": pass_rate,
        "average_score": sum(
            o.ged_score for o in outcomes if o.ged_score
        ) / len([o for o in outcomes if o.ged_score]) if any(o.ged_score for o in outcomes) else None
    }


@router.get("/reports/impact")
async def get_impact_metrics(
    program_id: int = Query(...),
    period_type: str = Query("annual"),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get program impact metrics and effectiveness statistics.

    Includes learners served, completions, outcomes, and retention.
    """
    # Get learners in program
    learner_count = await db.scalar(
        select(func.count(LiteracyLearner.id)).where(
            LiteracyLearner.program_id == program_id
        )
    )

    # Get GED completions
    ged_completions = await db.scalar(
        select(func.count(LiteracyOutcome.id)).where(
            LiteracyOutcome.outcome_type == "ged_passed"
        )
    )

    # Get employment outcomes
    employment = await db.scalar(
        select(func.count(LiteracyOutcome.id)).where(
            LiteracyOutcome.outcome_type == "employment_gained"
        )
    )

    # Get education advancement
    education = await db.scalar(
        select(func.count(LiteracyOutcome.id)).where(
            LiteracyOutcome.outcome_type == "college_acceptance"
        )
    )

    # Calculate retention rate
    active_learners = await db.scalar(
        select(func.count(LiteracyLearner.id)).where(
            LiteracyLearner.program_id == program_id,
            LiteracyLearner.status == "active"
        )
    )

    retention_rate = (active_learners / learner_count * 100) if learner_count else 0

    return {
        "program_id": program_id,
        "period_type": period_type,
        "learners_served": learner_count or 0,
        "active_learners": active_learners or 0,
        "ged_completions": ged_completions or 0,
        "employment_outcomes": employment or 0,
        "education_advancement": education or 0,
        "retention_rate_percentage": retention_rate,
        "total_outcomes": (ged_completions or 0) + (employment or 0) + (education or 0)
    }


@router.post("/cohorts")
async def create_cohort(
    cohort_data: dict,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Create a new learner cohort for grouped analysis."""
    cohort = LiteracyCohort(
        program_id=cohort_data['program_id'],
        cohort_name=cohort_data['cohort_name'],
        cohort_code=cohort_data.get('cohort_code'),
        start_date=cohort_data['start_date'],
        end_date=cohort_data.get('end_date'),
        target_enrollment=cohort_data.get('target_enrollment'),
        description=cohort_data.get('description')
    )
    db.add(cohort)
    await db.commit()
    await db.refresh(cohort)

    return {
        "id": cohort.id,
        "cohort_name": cohort.cohort_name,
        "cohort_code": cohort.cohort_code,
        "start_date": cohort.start_date.isoformat()
    }


@router.get("/cohorts/{cohort_id}")
async def get_cohort_analysis(
    cohort_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed analysis for a specific cohort."""
    cohort = await db.get(LiteracyCohort, cohort_id)
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    # Get cohort members
    learner_cohorts = await db.scalars(
        select(LiteracyLearnerCohort).where(
            LiteracyLearnerCohort.cohort_id == cohort_id
        )
    )

    members = list(learner_cohorts)
    member_count = len(members)

    # Get outcomes for cohort members
    learner_ids = [m.learner_id for m in members]

    if learner_ids:
        outcomes = await db.scalars(
            select(LiteracyOutcome).where(
                LiteracyOutcome.learner_id.in_(learner_ids)
            )
        )
        outcomes_list = list(outcomes)
    else:
        outcomes_list = []

    ged_completions = len([o for o in outcomes_list if o.outcome_type == "ged_passed"])
    employment = len([o for o in outcomes_list if o.outcome_type == "employment_gained"])

    return {
        "cohort_id": cohort.id,
        "cohort_name": cohort.cohort_name,
        "cohort_code": cohort.cohort_code,
        "member_count": member_count,
        "target_enrollment": cohort.target_enrollment,
        "start_date": cohort.start_date.isoformat(),
        "end_date": cohort.end_date.isoformat() if cohort.end_date else None,
        "total_outcomes": ged_completions + employment,
        "ged_completions": ged_completions,
        "employment_outcomes": employment,
        "success_rate_percentage": (
            (ged_completions + employment) / member_count * 100
        ) if member_count > 0 else 0
    }


@router.post("/cohorts/{cohort_id}/add-learner")
async def add_learner_to_cohort(
    cohort_id: int,
    learner_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Add a learner to a cohort."""
    cohort = await db.get(LiteracyCohort, cohort_id)
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    learner = await db.get(LiteracyLearner, learner_id)
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    # Check if already in cohort
    existing = await db.scalar(
        select(LiteracyLearnerCohort).where(
            LiteracyLearnerCohort.cohort_id == cohort_id,
            LiteracyLearnerCohort.learner_id == learner_id
        )
    )

    if existing:
        return {"message": "Learner already in cohort"}

    cohort_link = LiteracyLearnerCohort(
        learner_id=learner_id,
        cohort_id=cohort_id
    )
    db.add(cohort_link)

    cohort.actual_enrollment = (cohort.actual_enrollment or 0) + 1
    await db.commit()

    return {"message": "Learner added to cohort"}


@router.get("/reports/outcomes")
async def get_outcome_statistics(
    program_id: Optional[int] = Query(None),
    outcome_type: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive outcome statistics by type."""
    query = select(LiteracyOutcome)

    if outcome_type:
        query = query.where(LiteracyOutcome.outcome_type == outcome_type)

    if from_date:
        query = query.where(LiteracyOutcome.outcome_date >= from_date)

    if to_date:
        query = query.where(LiteracyOutcome.outcome_date <= to_date)

    outcomes = await db.scalars(query)
    all_outcomes = list(outcomes)

    # Count by type
    outcome_counts = {}
    for outcome in all_outcomes:
        outcome_type_str = str(outcome.outcome_type)
        outcome_counts[outcome_type_str] = outcome_counts.get(outcome_type_str, 0) + 1

    return {
        "total_outcomes": len(all_outcomes),
        "outcome_distribution": outcome_counts,
        "ged_passed": outcome_counts.get("ged_passed", 0),
        "employment_gained": outcome_counts.get("employment_gained", 0),
        "college_acceptance": outcome_counts.get("college_acceptance", 0)
    }
