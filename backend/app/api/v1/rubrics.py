# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API endpoints for reusable assessment rubrics."""

from app.core.logging import get_logger
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.rubric import Rubric, RubricAssessment, RubricCriterion
from ...models.user import User, UserRole
from ...schemas.rubric import (
    RubricAssessmentCreate,
    RubricAssessmentResponse,
    RubricAssessmentUpdate,
    RubricAssessmentWithRubric,
    RubricBulkCriteriaCreate,
    RubricCreate,
    RubricCriterionCreate,
    RubricCriterionResponse,
    RubricCriterionUpdate,
    RubricListItem,
    RubricResponse,
    RubricUpdate,
    RubricUsageStats,
    RubricWithCriteria,
)
from .auth import get_current_user, get_current_user_optional
from app.core.datetime_utils import utc_now
from .dependencies import is_admin

logger = get_logger(__name__)
router = APIRouter(prefix="/rubrics", tags=["rubrics"])


def _ensure_admin_or_staff(current_user: User) -> None:
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or staff access required",
        )


# ===== PUBLIC ENDPOINTS =====


@router.get("", response_model=List[RubricListItem])
async def list_rubrics(
    db: AsyncSession = Depends(get_db),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_featured: Optional[bool] = Query(None, description="Filter featured rubrics"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    List published rubrics.

    - Public users see only published patron-level rubrics
    - Staff see published staff and patron rubrics
    - Admins see all rubrics (published and unpublished)
    """
    query = select(Rubric).options(selectinload(Rubric.criteria))

    # Apply visibility filters based on user role
    if not current_user:
        query = query.where(Rubric.is_published == True, Rubric.access_level == "patron")
    elif current_user.role == UserRole.ADMIN:
        pass  # Admins see all
    elif current_user.role == UserRole.STAFF:
        query = query.where(
            Rubric.is_published == True,
            Rubric.access_level.in_(["patron", "staff"])
        )
    else:
        query = query.where(Rubric.is_published == True, Rubric.access_level == "patron")

    # Apply optional filters
    if category:
        query = query.where(Rubric.category == category)
    if is_featured is not None:
        query = query.where(Rubric.is_featured == is_featured)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (Rubric.title.ilike(search_term)) | (Rubric.description.ilike(search_term))
        )

    query = query.order_by(Rubric.is_featured.desc(), Rubric.title).offset(skip).limit(limit)

    result = await db.execute(query)
    rubrics = result.scalars().unique().all()

    # Build response with criteria count
    return [
        RubricListItem(
            **RubricResponse.model_validate(rubric).model_dump(),
            criteria_count=len(rubric.criteria)
        )
        for rubric in rubrics
    ]


@router.get("/categories", response_model=List[str])
async def list_rubric_categories(
    db: AsyncSession = Depends(get_db),
):
    """Get list of all unique rubric categories."""
    query = select(Rubric.category).where(
        Rubric.is_published == True,
        Rubric.category.isnot(None)
    ).distinct()

    result = await db.execute(query)
    categories = [row[0] for row in result.fetchall() if row[0]]
    return sorted(categories)


@router.get("/{rubric_id}", response_model=RubricWithCriteria)
async def get_rubric(
    rubric_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get a rubric with all criteria."""
    query = select(Rubric).options(
        selectinload(Rubric.criteria)
    ).where(Rubric.id == rubric_id)

    result = await db.execute(query)
    rubric = result.scalar_one_or_none()

    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rubric not found"
        )

    # Check visibility
    if not current_user:
        if not rubric.is_published or rubric.access_level != "patron":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rubric not found"
            )
    elif current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.STAFF]:
        if not rubric.is_published or rubric.access_level != "patron":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rubric not found"
            )
    elif current_user.role == UserRole.STAFF:
        if not rubric.is_published or rubric.access_level == "admin":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rubric not found"
            )

    return RubricWithCriteria.model_validate(rubric)


# ===== ADMIN ENDPOINTS =====


@router.post("", response_model=RubricWithCriteria, status_code=status.HTTP_201_CREATED)
async def create_rubric(
    rubric_data: RubricCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new rubric (admin/staff only)."""
    _ensure_admin_or_staff(current_user)

    # Create rubric
    rubric = Rubric(
        title=rubric_data.title,
        description=rubric_data.description,
        source_url=rubric_data.source_url,
        source_attribution=rubric_data.source_attribution,
        max_score=rubric_data.max_score,
        min_score=rubric_data.min_score,
        level_labels=rubric_data.level_labels,
        category=rubric_data.category,
        tags=rubric_data.tags,
        access_level=rubric_data.access_level,
        course_id=rubric_data.course_id,
        lesson_id=rubric_data.lesson_id,
        created_by_id=current_user.id,
    )
    db.add(rubric)
    await db.flush()

    # Create criteria if provided
    for idx, criterion_data in enumerate(rubric_data.criteria):
        criterion = RubricCriterion(
            rubric_id=rubric.id,
            name=criterion_data.name,
            description=criterion_data.description,
            levels=criterion_data.levels,
            weight=criterion_data.weight,
            sort_order=criterion_data.sort_order or idx,
        )
        db.add(criterion)

    await db.commit()
    await db.refresh(rubric)

    # Reload with criteria
    query = select(Rubric).options(
        selectinload(Rubric.criteria)
    ).where(Rubric.id == rubric.id)
    result = await db.execute(query)
    rubric = result.scalar_one()

    logger.info(f"Rubric created: {rubric.id} by user {current_user.id}")
    return RubricWithCriteria.model_validate(rubric)


@router.put("/{rubric_id}", response_model=RubricWithCriteria)
async def update_rubric(
    rubric_id: int,
    rubric_data: RubricUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a rubric (admin/staff only)."""
    _ensure_admin_or_staff(current_user)

    query = select(Rubric).options(
        selectinload(Rubric.criteria)
    ).where(Rubric.id == rubric_id)
    result = await db.execute(query)
    rubric = result.scalar_one_or_none()

    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rubric not found"
        )

    # Update fields
    update_data = rubric_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rubric, field, value)

    await db.commit()
    await db.refresh(rubric)

    logger.info(f"Rubric updated: {rubric.id} by user {current_user.id}")
    return RubricWithCriteria.model_validate(rubric)


@router.delete("/{rubric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rubric(
    rubric_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a rubric (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    query = select(Rubric).where(Rubric.id == rubric_id)
    result = await db.execute(query)
    rubric = result.scalar_one_or_none()

    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rubric not found"
        )

    await db.delete(rubric)
    await db.commit()

    logger.info(f"Rubric deleted: {rubric_id} by user {current_user.id}")


# ===== CRITERIA ENDPOINTS =====


@router.post("/{rubric_id}/criteria", response_model=RubricCriterionResponse, status_code=status.HTTP_201_CREATED)
async def add_criterion(
    rubric_id: int,
    criterion_data: RubricCriterionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a criterion to a rubric (admin/staff only)."""
    _ensure_admin_or_staff(current_user)

    # Verify rubric exists
    query = select(Rubric).where(Rubric.id == rubric_id)
    result = await db.execute(query)
    rubric = result.scalar_one_or_none()

    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rubric not found"
        )

    criterion = RubricCriterion(
        rubric_id=rubric_id,
        name=criterion_data.name,
        description=criterion_data.description,
        levels=criterion_data.levels,
        weight=criterion_data.weight,
        sort_order=criterion_data.sort_order,
    )
    db.add(criterion)
    await db.commit()
    await db.refresh(criterion)

    logger.info(f"Criterion added to rubric {rubric_id}: {criterion.id}")
    return RubricCriterionResponse.model_validate(criterion)


@router.post("/{rubric_id}/criteria/bulk", response_model=List[RubricCriterionResponse], status_code=status.HTTP_201_CREATED)
async def add_criteria_bulk(
    rubric_id: int,
    bulk_data: RubricBulkCriteriaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add multiple criteria to a rubric at once (admin/staff only)."""
    _ensure_admin_or_staff(current_user)

    # Verify rubric exists
    query = select(Rubric).where(Rubric.id == rubric_id)
    result = await db.execute(query)
    rubric = result.scalar_one_or_none()

    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rubric not found"
        )

    created_criteria = []
    for idx, criterion_data in enumerate(bulk_data.criteria):
        criterion = RubricCriterion(
            rubric_id=rubric_id,
            name=criterion_data.name,
            description=criterion_data.description,
            levels=criterion_data.levels,
            weight=criterion_data.weight,
            sort_order=criterion_data.sort_order or idx,
        )
        db.add(criterion)
        created_criteria.append(criterion)

    await db.commit()
    for criterion in created_criteria:
        await db.refresh(criterion)

    logger.info(f"Bulk criteria added to rubric {rubric_id}: {len(created_criteria)} items")
    return [RubricCriterionResponse.model_validate(c) for c in created_criteria]


@router.put("/{rubric_id}/criteria/{criterion_id}", response_model=RubricCriterionResponse)
async def update_criterion(
    rubric_id: int,
    criterion_id: int,
    criterion_data: RubricCriterionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a criterion (admin/staff only)."""
    _ensure_admin_or_staff(current_user)

    query = select(RubricCriterion).where(
        RubricCriterion.id == criterion_id,
        RubricCriterion.rubric_id == rubric_id
    )
    result = await db.execute(query)
    criterion = result.scalar_one_or_none()

    if not criterion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Criterion not found"
        )

    update_data = criterion_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(criterion, field, value)

    await db.commit()
    await db.refresh(criterion)

    logger.info(f"Criterion updated: {criterion_id}")
    return RubricCriterionResponse.model_validate(criterion)


@router.delete("/{rubric_id}/criteria/{criterion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_criterion(
    rubric_id: int,
    criterion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a criterion (admin/staff only)."""
    _ensure_admin_or_staff(current_user)

    query = select(RubricCriterion).where(
        RubricCriterion.id == criterion_id,
        RubricCriterion.rubric_id == rubric_id
    )
    result = await db.execute(query)
    criterion = result.scalar_one_or_none()

    if not criterion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Criterion not found"
        )

    await db.delete(criterion)
    await db.commit()

    logger.info(f"Criterion deleted: {criterion_id} from rubric {rubric_id}")


# ===== ASSESSMENT ENDPOINTS =====


@router.post("/{rubric_id}/assessments", response_model=RubricAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    rubric_id: int,
    assessment_data: RubricAssessmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a new assessment using a rubric."""
    # Verify rubric exists and is accessible
    query = select(Rubric).options(
        selectinload(Rubric.criteria)
    ).where(Rubric.id == rubric_id)
    result = await db.execute(query)
    rubric = result.scalar_one_or_none()

    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rubric not found"
        )

    if not rubric.is_published and current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rubric not found"
        )

    # Check for existing assessment with same target
    existing_query = select(RubricAssessment).where(
        RubricAssessment.rubric_id == rubric_id,
        RubricAssessment.user_id == current_user.id,
        RubricAssessment.target_identifier == assessment_data.target_identifier
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment already exists for this target"
        )

    # Calculate max possible score
    max_possible = sum(c.weight * rubric.max_score for c in rubric.criteria)

    assessment = RubricAssessment(
        rubric_id=rubric_id,
        user_id=current_user.id,
        target_identifier=assessment_data.target_identifier,
        target_description=assessment_data.target_description,
        scores=assessment_data.scores,
        notes=assessment_data.notes,
        overall_notes=assessment_data.overall_notes,
        max_possible_score=max_possible,
    )

    # Calculate total score if scores provided
    if assessment_data.scores:
        total = 0
        for criterion in rubric.criteria:
            criterion_score = assessment_data.scores.get(str(criterion.id), 0)
            total += criterion_score * criterion.weight
        assessment.total_score = total
        assessment.percentage = int((total / max_possible) * 100) if max_possible > 0 else 0

    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)

    logger.info(f"Assessment created: {assessment.id} for rubric {rubric_id}")
    return RubricAssessmentResponse.model_validate(assessment)


@router.get("/{rubric_id}/assessments", response_model=List[RubricAssessmentResponse])
async def list_my_assessments(
    rubric_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List current user's assessments for a rubric."""
    query = select(RubricAssessment).where(
        RubricAssessment.rubric_id == rubric_id,
        RubricAssessment.user_id == current_user.id
    ).order_by(RubricAssessment.created_at.desc())

    result = await db.execute(query)
    assessments = result.scalars().all()

    return [RubricAssessmentResponse.model_validate(a) for a in assessments]


@router.get("/{rubric_id}/assessments/{assessment_id}", response_model=RubricAssessmentWithRubric)
async def get_assessment(
    rubric_id: int,
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific assessment with rubric details."""
    query = select(RubricAssessment).options(
        selectinload(RubricAssessment.rubric).selectinload(Rubric.criteria)
    ).where(
        RubricAssessment.id == assessment_id,
        RubricAssessment.rubric_id == rubric_id
    )

    result = await db.execute(query)
    assessment = result.scalar_one_or_none()

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    # Users can only view their own assessments (unless admin)
    if assessment.user_id != current_user.id and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return RubricAssessmentWithRubric.model_validate(assessment)


@router.put("/{rubric_id}/assessments/{assessment_id}", response_model=RubricAssessmentResponse)
async def update_assessment(
    rubric_id: int,
    assessment_id: int,
    assessment_data: RubricAssessmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an assessment."""
    query = select(RubricAssessment).options(
        selectinload(RubricAssessment.rubric).selectinload(Rubric.criteria)
    ).where(
        RubricAssessment.id == assessment_id,
        RubricAssessment.rubric_id == rubric_id
    )

    result = await db.execute(query)
    assessment = result.scalar_one_or_none()

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    # Users can only update their own assessments
    if assessment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update fields
    update_data = assessment_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(assessment, field, value)

    # Recalculate scores if scores were updated
    if "scores" in update_data:
        rubric = assessment.rubric
        total = 0
        for criterion in rubric.criteria:
            criterion_score = assessment.scores.get(str(criterion.id), 0)
            total += criterion_score * criterion.weight
        assessment.total_score = total
        assessment.percentage = int((total / assessment.max_possible_score) * 100) if assessment.max_possible_score > 0 else 0

    # Handle completion
    if assessment_data.is_complete and not assessment.completed_at:
        assessment.completed_at = utc_now()

    await db.commit()
    await db.refresh(assessment)

    logger.info(f"Assessment updated: {assessment_id}")
    return RubricAssessmentResponse.model_validate(assessment)


@router.delete("/{rubric_id}/assessments/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assessment(
    rubric_id: int,
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an assessment."""
    query = select(RubricAssessment).where(
        RubricAssessment.id == assessment_id,
        RubricAssessment.rubric_id == rubric_id
    )

    result = await db.execute(query)
    assessment = result.scalar_one_or_none()

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    # Users can only delete their own assessments (unless admin)
    if assessment.user_id != current_user.id and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    await db.delete(assessment)
    await db.commit()

    logger.info(f"Assessment deleted: {assessment_id}")


# ===== STATISTICS ENDPOINT =====


@router.get("/{rubric_id}/stats", response_model=RubricUsageStats)
async def get_rubric_stats(
    rubric_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get usage statistics for a rubric (admin/staff only)."""
    _ensure_admin_or_staff(current_user)

    query = select(Rubric).where(Rubric.id == rubric_id)
    result = await db.execute(query)
    rubric = result.scalar_one_or_none()

    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rubric not found"
        )

    # Count assessments
    count_query = select(func.count(RubricAssessment.id)).where(
        RubricAssessment.rubric_id == rubric_id
    )
    total_result = await db.execute(count_query)
    total_assessments = total_result.scalar() or 0

    completed_query = select(func.count(RubricAssessment.id)).where(
        RubricAssessment.rubric_id == rubric_id,
        RubricAssessment.is_complete == True
    )
    completed_result = await db.execute(completed_query)
    completed_assessments = completed_result.scalar() or 0

    # Calculate averages
    avg_query = select(
        func.avg(RubricAssessment.total_score),
        func.avg(RubricAssessment.percentage)
    ).where(
        RubricAssessment.rubric_id == rubric_id,
        RubricAssessment.is_complete == True
    )
    avg_result = await db.execute(avg_query)
    avg_row = avg_result.fetchone()
    avg_score = float(avg_row[0]) if avg_row[0] else None
    avg_percentage = float(avg_row[1]) if avg_row[1] else None

    return RubricUsageStats(
        rubric_id=rubric_id,
        rubric_title=rubric.title,
        total_assessments=total_assessments,
        completed_assessments=completed_assessments,
        average_score=avg_score,
        average_percentage=avg_percentage,
    )
