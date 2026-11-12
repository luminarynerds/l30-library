# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff Training Modules API Endpoints

This module provides endpoints for retrieving dynamic training module options.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.rate_limit import limiter
from ....models.onboarding import TrainingModule
from ....services.organization_features_service import OrganizationFeaturesService
from ..dependencies import require_staff


async def require_training_modules_enabled(db: AsyncSession = Depends(get_db)) -> None:
    enabled = await OrganizationFeaturesService.is_feature_enabled(db, "training_modules_enabled")
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training modules feature is not enabled",
        )


router = APIRouter(
    prefix="/staff/training",
    tags=["staff-training"],
    dependencies=[Depends(require_training_modules_enabled)],
)


# =============================================================================
# Pydantic Schemas
# =============================================================================


class TrainingModuleResponse(BaseModel):
    id: int
    title: str
    duration_minutes: int
    category: str | None = None

    class Config:
        from_attributes = True


class RatingScaleOption(BaseModel):
    key: str
    label: str
    description: str | None = None


class LessonTypeOption(BaseModel):
    key: str
    label: str
    description: str | None = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/modules", response_model=list[TrainingModuleResponse])
@limiter.limit("60/minute")
async def get_training_modules(
    request: Request,
    staff_user = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all available training modules for form population.

    Returns a list of training modules that can be assigned to staff members.
    Modules are ordered by their configured order, then by title.
    """
    result = await db.execute(
        select(TrainingModule)
        .order_by(TrainingModule.order.asc().nullslast(), TrainingModule.title)
    )
    modules = result.scalars().all()

    return [
        TrainingModuleResponse(
            id=module.id,
            title=module.title,
            duration_minutes=module.duration_minutes,
            category=module.category,
        )
        for module in modules
    ]


@router.get("/config/rating-scales", response_model=list[RatingScaleOption])
@limiter.limit("60/minute")
async def get_rating_scales(
    request: Request,
    current_user = Depends(require_staff),
):
    """Get available training quality rating scales.

    Returns configuration options for evaluating training effectiveness.
    Includes 5-point scale from Poor to Excellent.
    """
    return [
        RatingScaleOption(
            key="poor",
            label="Poor",
            description="Training quality was poor or ineffective",
        ),
        RatingScaleOption(
            key="fair",
            label="Fair",
            description="Training quality was below average",
        ),
        RatingScaleOption(
            key="good",
            label="Good",
            description="Training quality was satisfactory",
        ),
        RatingScaleOption(
            key="very_good",
            label="Very Good",
            description="Training quality was above average",
        ),
        RatingScaleOption(
            key="excellent",
            label="Excellent",
            description="Training quality was exceptional",
        ),
    ]


@router.get("/config/lesson-types", response_model=list[LessonTypeOption])
@limiter.limit("60/minute")
async def get_lesson_types(
    request: Request,
    current_user = Depends(require_staff),
):
    """Get available lesson delivery type options.

    Returns configuration options for specifying how training was delivered.
    """
    return [
        LessonTypeOption(
            key="in_person",
            label="In-Person",
            description="Training conducted face-to-face",
        ),
        LessonTypeOption(
            key="online",
            label="Online",
            description="Training conducted via video conference or online platform",
        ),
    ]
