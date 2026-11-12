# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Community Features API - Staff bios."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.community import StaffBio
from ...models.user import User
from ...services.organization_features_service import OrganizationFeaturesService
from .auth import get_current_user
from .dependencies import check_staff_access, check_admin_access


async def require_community_features_enabled(db: AsyncSession = Depends(get_db)) -> None:
    enabled = await OrganizationFeaturesService.is_feature_enabled(db, "community_features_enabled")
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community features are not enabled",
        )


router = APIRouter(prefix="/community", tags=["community"])


# ============================================================================
# Schemas - Staff Bios
# ============================================================================


class StaffBioResponse(BaseModel):

    id: int
    staff_name: str
    role: str
    bio: str
    photo_url: Optional[str] = None
    fun_fact: Optional[str] = None
    favorite_book: Optional[str] = None
    years_of_service: Optional[int] = None
    sort_order: int

    class Config:
        from_attributes = True


class StaffBioCreate(BaseModel):

    staff_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., min_length=1)
    photo_url: Optional[str] = Field(default=None, max_length=500)
    fun_fact: Optional[str] = Field(default=None, max_length=500)
    favorite_book: Optional[str] = Field(default=None, max_length=200)
    years_of_service: Optional[int] = Field(default=None, ge=0)
    is_visible: bool = True
    sort_order: int = Field(default=0, ge=0)


class StaffBioUpdate(BaseModel):

    staff_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    role: Optional[str] = Field(default=None, min_length=1, max_length=100)
    bio: Optional[str] = Field(default=None, min_length=1)
    photo_url: Optional[str] = Field(default=None, max_length=500)
    fun_fact: Optional[str] = Field(default=None, max_length=500)
    favorite_book: Optional[str] = Field(default=None, max_length=200)
    years_of_service: Optional[int] = Field(default=None, ge=0)
    is_visible: Optional[bool] = None
    sort_order: Optional[int] = Field(default=None, ge=0)


class StaffBioSelfUpdate(BaseModel):

    bio: Optional[str] = Field(default=None, min_length=1)
    photo_url: Optional[str] = Field(default=None, max_length=500)
    fun_fact: Optional[str] = Field(default=None, max_length=500)
    favorite_book: Optional[str] = Field(default=None, max_length=200)


# ============================================================================
# Staff Bios Endpoints
# ============================================================================


@router.get(
    "/staff",
    response_model=List[StaffBioResponse],
    dependencies=[Depends(require_community_features_enabled)],
)
async def list_staff_bios(
    visible_only: bool = Query(default=True, description="Only show visible staff"),
    db: AsyncSession = Depends(get_db),
) -> List[StaffBioResponse]:
    """
    List all staff bios.

    - **visible_only**: Only return visible staff (default: true)
    """
    query = select(StaffBio)

    if visible_only:
        query = query.where(StaffBio.is_visible == True)

    query = query.order_by(StaffBio.sort_order, StaffBio.staff_name)

    result = await db.execute(query)
    return result.scalars().all()


# ============================================================================
# Staff Self-Service Bio Endpoints (must be before /staff/{staff_id})
# ============================================================================


@router.get(
    "/staff/me",
    response_model=StaffBioResponse,
    dependencies=[Depends(require_community_features_enabled)],
)
async def get_my_bio(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StaffBioResponse:
    """Get the current staff member's own bio."""
    result = await db.execute(
        select(StaffBio).where(StaffBio.user_id == current_user.id)
    )
    staff = result.scalar_one_or_none()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No bio found for your account. Ask an admin to create one and link it to your user.",
        )

    return staff


@router.put(
    "/staff/me",
    response_model=StaffBioResponse,
    dependencies=[Depends(require_community_features_enabled)],
)
async def update_my_bio(
    update_data: StaffBioSelfUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StaffBioResponse:
    """Update your own bio -- personality fields only (bio, photo, fun fact, favorite book)."""
    result = await db.execute(
        select(StaffBio).where(StaffBio.user_id == current_user.id)
    )
    staff = result.scalar_one_or_none()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No bio found for your account. Ask an admin to create one and link it to your user.",
        )

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(staff, field, value)

    await db.commit()
    await db.refresh(staff)

    return staff


# ============================================================================
# Public Staff Bio by ID
# ============================================================================


@router.get(
    "/staff/{staff_id}",
    response_model=StaffBioResponse,
    dependencies=[Depends(require_community_features_enabled)],
)
async def get_staff_bio(
    staff_id: int, db: AsyncSession = Depends(get_db)
) -> StaffBioResponse:
    """Get a single staff bio"""
    result = await db.execute(select(StaffBio).where(StaffBio.id == staff_id))
    staff = result.scalar_one_or_none()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Staff bio not found"
        )

    return staff


@router.post(
    "/admin/staff",
    response_model=StaffBioResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_community_features_enabled)],
)
async def create_staff_bio(
    staff_data: StaffBioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StaffBioResponse:
    """Create a staff bio (admin only)"""
    check_admin_access(current_user)

    staff = StaffBio(**staff_data.model_dump())

    db.add(staff)
    await db.commit()
    await db.refresh(staff)

    return staff


@router.get(
    "/admin/staff/{staff_id}",
    response_model=StaffBioResponse,
    dependencies=[Depends(require_community_features_enabled)],
)
async def get_staff_bio(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StaffBioResponse:
    """Get a staff bio (admin only)"""
    check_admin_access(current_user)

    result = await db.execute(select(StaffBio).where(StaffBio.id == staff_id))
    staff = result.scalar_one_or_none()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Staff bio not found"
        )

    return staff


@router.put(
    "/admin/staff/{staff_id}",
    response_model=StaffBioResponse,
    dependencies=[Depends(require_community_features_enabled)],
)
async def update_staff_bio(
    staff_id: int,
    update_data: StaffBioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StaffBioResponse:
    """Update a staff bio (admin only)"""
    check_admin_access(current_user)

    result = await db.execute(select(StaffBio).where(StaffBio.id == staff_id))
    staff = result.scalar_one_or_none()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Staff bio not found"
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(staff, field, value)

    await db.commit()
    await db.refresh(staff)

    return staff


@router.delete(
    "/admin/staff/{staff_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_community_features_enabled)],
)
async def delete_staff_bio(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a staff bio (admin only)"""
    check_admin_access(current_user)

    result = await db.execute(select(StaffBio).where(StaffBio.id == staff_id))
    staff = result.scalar_one_or_none()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Staff bio not found"
        )

    await db.delete(staff)
    await db.commit()
