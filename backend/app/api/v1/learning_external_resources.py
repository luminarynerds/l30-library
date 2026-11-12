# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Learning - External Resources API Endpoints

Provides endpoints for:
- Listing and fetching external resources
- Staff CRUD for external resources
- User click tracking, completion, and rating
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.learning import ExternalResource, ExternalResourceEnrollment
from ...models.user import User, UserRole
from ...schemas.learning import (
    ExternalResourceEnrollmentResponse,
    ExternalResourceEnrollmentWithResource,
    ExternalResourceCreate,
    ExternalResourceResponse,
    ExternalResourceUpdate,
    StatusResponse,
)
from .auth import get_current_user, get_current_user_optional
from .dependencies import require_staff

router = APIRouter(prefix="/learning", tags=["learning-external-resources"])


# ============ EXTERNAL RESOURCES ============


@router.get("/external-resources", response_model=List[ExternalResourceResponse])
async def list_external_resources(
    difficulty: Optional[str] = None,
    topic: Optional[str] = None,
    featured_only: bool = False,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """List external resources with optional filtering by difficulty and topic."""
    query = select(ExternalResource)

    # Filter by access level
    if current_user is None:
        query = query.where(ExternalResource.access_level == "patron")
    elif current_user.role == UserRole.PATRON:
        query = query.where(ExternalResource.access_level == "patron")
    elif current_user.role == UserRole.STAFF:
        query = query.where(ExternalResource.access_level.in_(["patron", "staff"]))

    # Filter by difficulty
    if difficulty and difficulty != "all":
        query = query.where(ExternalResource.difficulty == difficulty)

    # Filter by topic (check if topic is in topics array)
    if topic:
        query = query.where(ExternalResource.topics.contains([topic]))

    # Filter by featured
    if featured_only:
        query = query.where(ExternalResource.is_featured == True)

    query = query.order_by(ExternalResource.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/external-resources/{resource_id}", response_model=ExternalResourceResponse)
async def get_external_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get a specific external resource."""
    resource = await get_or_404(db, ExternalResource, resource_id, "Resource not found")

    # Check access level
    if current_user is None:
        if resource.access_level != "patron":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this resource"
            )
    elif current_user.role == UserRole.PATRON:
        if resource.access_level != "patron":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this resource"
            )
    elif current_user.role == UserRole.STAFF:
        if resource.access_level not in ["patron", "staff"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this resource"
            )

    return resource


@router.post("/external-resources", response_model=ExternalResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_external_resource(
    resource_in: ExternalResourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new external resource (staff/admin only)."""
    # Check if URL already exists
    existing = await db.execute(
        select(ExternalResource).where(ExternalResource.source_url == resource_in.source_url)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resource with this URL already exists")

    resource = ExternalResource(**resource_in.model_dump())
    db.add(resource)
    await db.commit()
    await db.refresh(resource)
    return resource


@router.patch("/external-resources/{resource_id}", response_model=ExternalResourceResponse)
async def update_external_resource(
    resource_id: int,
    resource_in: ExternalResourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update an external resource (staff/admin only)."""
    resource = await get_or_404(db, ExternalResource, resource_id, "Resource not found")

    update_data = resource_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(resource, field, value)

    db.add(resource)
    await db.commit()
    await db.refresh(resource)
    return resource


@router.delete("/external-resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_external_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Delete an external resource (staff/admin only)."""
    resource = await get_or_404(db, ExternalResource, resource_id, "Resource not found")

    await db.delete(resource)
    await db.commit()


@router.post("/external-resources/{resource_id}/click", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def track_external_resource_click(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Track when a user clicks on an external resource."""
    # Check resource exists
    resource_result = await db.execute(
        select(ExternalResource).where(ExternalResource.id == resource_id)
    )
    if not resource_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    # Check if enrollment record already exists
    existing = await db.execute(
        select(ExternalResourceEnrollment).where(
            (ExternalResourceEnrollment.user_id == current_user.id) &
            (ExternalResourceEnrollment.external_resource_id == resource_id)
        )
    )
    enrollment = existing.scalar_one_or_none()

    if enrollment:
        enrollment.clicked_at = datetime.now(timezone.utc)
    else:
        enrollment = ExternalResourceEnrollment(
            user_id=current_user.id,
            external_resource_id=resource_id,
            clicked_at=datetime.now(timezone.utc)
        )

    db.add(enrollment)
    await db.commit()
    return {"status": "tracked"}


@router.post("/external-resources/{resource_id}/complete", response_model=ExternalResourceEnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def mark_external_resource_complete(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an external resource as completed."""
    # Check if enrollment record exists
    result = await db.execute(
        select(ExternalResourceEnrollment).where(
            (ExternalResourceEnrollment.user_id == current_user.id) &
            (ExternalResourceEnrollment.external_resource_id == resource_id)
        )
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        # Create new enrollment record if it doesn't exist
        resource_result = await db.execute(
            select(ExternalResource).where(ExternalResource.id == resource_id)
        )
        if not resource_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

        enrollment = ExternalResourceEnrollment(
            user_id=current_user.id,
            external_resource_id=resource_id,
            completed=True,
            completion_date=datetime.now(timezone.utc),
            clicked_at=datetime.now(timezone.utc)
        )
    else:
        enrollment.completed = True
        enrollment.completion_date = datetime.now(timezone.utc)

    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


@router.post("/external-resources/{resource_id}/rate", response_model=ExternalResourceEnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def rate_external_resource(
    resource_id: int,
    rating: int,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rate an external resource."""
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rating must be between 1 and 5")

    # Check if enrollment record exists
    result = await db.execute(
        select(ExternalResourceEnrollment).where(
            (ExternalResourceEnrollment.user_id == current_user.id) &
            (ExternalResourceEnrollment.external_resource_id == resource_id)
        )
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        # Create new enrollment record
        resource_result = await db.execute(
            select(ExternalResource).where(ExternalResource.id == resource_id)
        )
        if not resource_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

        enrollment = ExternalResourceEnrollment(
            user_id=current_user.id,
            external_resource_id=resource_id,
            rating=rating,
            notes=notes
        )
    else:
        enrollment.rating = rating
        enrollment.notes = notes

    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


@router.get("/external-resources/user/enrollments", response_model=List[ExternalResourceEnrollmentWithResource])
async def get_user_external_resource_enrollments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all external resource enrollments for the current user."""
    result = await db.execute(
        select(ExternalResourceEnrollment)
        .options(selectinload(ExternalResourceEnrollment.resource))
        .where(ExternalResourceEnrollment.user_id == current_user.id)
        .order_by(ExternalResourceEnrollment.created_at.desc())
    )
    enrollments = result.scalars().all()

    return [
        ExternalResourceEnrollmentWithResource(
            enrollment=enrollment,
            resource=enrollment.resource
        )
        for enrollment in enrollments
    ]


@router.get("/external-resources/{resource_id}/click", response_model=ExternalResourceEnrollmentResponse)
async def get_external_resources__resource_id__click(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get click tracking info for an external resource."""
    result = await db.execute(
        select(ExternalResourceEnrollment).where(
            ExternalResourceEnrollment.user_id == current_user.id,
            ExternalResourceEnrollment.external_resource_id == resource_id
        )
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(status_code=404, detail="No click tracking found for this resource")

    return enrollment


@router.get("/external-resources/{resource_id}/complete", response_model=ExternalResourceEnrollmentResponse)
async def get_external_resources__resource_id__complete(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get completion status for an external resource."""
    result = await db.execute(
        select(ExternalResourceEnrollment).where(
            ExternalResourceEnrollment.user_id == current_user.id,
            ExternalResourceEnrollment.external_resource_id == resource_id
        )
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(status_code=404, detail="No completion record found for this resource")

    return enrollment


@router.get("/external-resources/{resource_id}/rate", response_model=ExternalResourceEnrollmentResponse)
async def get_external_resources__resource_id__rate(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get rating info for an external resource."""
    result = await db.execute(
        select(ExternalResourceEnrollment).where(
            ExternalResourceEnrollment.user_id == current_user.id,
            ExternalResourceEnrollment.external_resource_id == resource_id
        )
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment or not enrollment.rating:
        raise HTTPException(status_code=404, detail="No rating found for this resource")

    return enrollment
