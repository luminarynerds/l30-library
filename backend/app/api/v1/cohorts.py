# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from enum import StrEnum
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.cohort import (Cohort, CohortMember, CohortMemberRole,
                              CohortMemberStatus, CohortTraining)
from ...models.learning import Course
from ...models.user import User, UserRole
from .auth import get_current_user

router = APIRouter(prefix="/cohorts", tags=["cohorts"])


# ============ SCHEMAS ============


class CohortMemberRoleEnum(StrEnum):
    member = "member"
    lead = "lead"
    admin = "admin"


class CohortMemberStatusEnum(StrEnum):
    active = "active"
    inactive = "inactive"
    pending = "pending"


class CohortCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    tags: List[str] = []


class CohortUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class MemberInfo(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    email: str
    role: str
    status: str
    joined_at: datetime

    class Config:
        from_attributes = True


class TrainingInfo(BaseModel):
    id: int
    course_id: int
    course_title: str
    due_date: Optional[datetime]
    assigned_at: datetime

    class Config:
        from_attributes = True


class CohortResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    tags: List[str]
    created_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class CohortDetailResponse(CohortResponse):
    member_count: int
    training_count: int
    members: List[MemberInfo]
    trainings: List[TrainingInfo]


class CohortListResponse(CohortResponse):
    member_count: int
    training_count: int


class AddMemberRequest(BaseModel):
    user_id: int
    role: CohortMemberRoleEnum = CohortMemberRoleEnum.member


class AddTrainingRequest(BaseModel):
    course_id: int
    due_date: Optional[datetime] = None


# ============ HELPERS ============


def is_staff_or_admin(user: User) -> bool:
    return user.role in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]


def require_staff_or_admin(user: User):
    if not is_staff_or_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or admin access required",
        )


# ============ ENDPOINTS ============


@router.get("", response_model=List[CohortListResponse])
async def list_cohorts(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all cohorts with member and training counts."""
    require_staff_or_admin(current_user)

    offset = (page - 1) * per_page
    result = await db.execute(
        select(Cohort).order_by(Cohort.created_at.desc()).offset(offset).limit(per_page)
    )
    cohorts = result.scalars().all()

    cohort_list = []
    for cohort in cohorts:
        # Count members
        member_result = await db.execute(
            select(func.count(CohortMember.id)).where(
                CohortMember.cohort_id == cohort.id
            )
        )
        member_count = member_result.scalar() or 0

        # Count trainings
        training_result = await db.execute(
            select(func.count(CohortTraining.id)).where(
                CohortTraining.cohort_id == cohort.id
            )
        )
        training_count = training_result.scalar() or 0

        cohort_list.append(
            CohortListResponse(
                id=cohort.id,
                name=cohort.name,
                description=cohort.description,
                tags=cohort.tags or [],
                created_by=cohort.created_by,
                created_at=cohort.created_at,
                member_count=member_count,
                training_count=training_count,
            )
        )

    return cohort_list


@router.post("", response_model=CohortResponse, status_code=status.HTTP_201_CREATED)
async def create_cohort(
    data: CohortCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new cohort."""
    require_staff_or_admin(current_user)

    cohort = Cohort(
        name=data.name,
        description=data.description,
        tags=data.tags,
        created_by=current_user.id,
    )
    db.add(cohort)
    await db.commit()
    await db.refresh(cohort)

    return CohortResponse(
        id=cohort.id,
        name=cohort.name,
        description=cohort.description,
        tags=cohort.tags or [],
        created_by=cohort.created_by,
        created_at=cohort.created_at,
    )


@router.get("/{cohort_id}", response_model=CohortDetailResponse)
async def get_cohort(
    cohort_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get cohort details with members and trainings."""
    require_staff_or_admin(current_user)

    result = await db.execute(
        select(Cohort)
        .options(selectinload(Cohort.members).selectinload(CohortMember.user))
        .options(selectinload(Cohort.trainings).selectinload(CohortTraining.course))
        .where(Cohort.id == cohort_id)
    )
    cohort = result.scalar_one_or_none()

    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found"
        )

    # Build member list
    members = [
        MemberInfo(
            id=m.id,
            user_id=m.user_id,
            first_name=m.user.first_name,
            last_name=m.user.last_name,
            email=m.user.email,
            role=str(m.role),
            status=str(m.status),
            joined_at=m.joined_at,
        )
        for m in cohort.members
    ]

    # Build training list
    trainings = [
        TrainingInfo(
            id=t.id,
            course_id=t.course_id,
            course_title=t.course.title if t.course else "Unknown",
            due_date=t.due_date,
            assigned_at=t.assigned_at,
        )
        for t in cohort.trainings
    ]

    return CohortDetailResponse(
        id=cohort.id,
        name=cohort.name,
        description=cohort.description,
        tags=cohort.tags or [],
        created_by=cohort.created_by,
        created_at=cohort.created_at,
        member_count=len(members),
        training_count=len(trainings),
        members=members,
        trainings=trainings,
    )


@router.put("/{cohort_id}", response_model=CohortResponse)
async def update_cohort(
    cohort_id: int,
    data: CohortUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update cohort details."""
    require_staff_or_admin(current_user)

    result = await db.execute(select(Cohort).where(Cohort.id == cohort_id))
    cohort = result.scalar_one_or_none()

    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found"
        )

    if data.name is not None:
        cohort.name = data.name
    if data.description is not None:
        cohort.description = data.description
    if data.tags is not None:
        cohort.tags = data.tags

    await db.commit()
    await db.refresh(cohort)

    return CohortResponse(
        id=cohort.id,
        name=cohort.name,
        description=cohort.description,
        tags=cohort.tags or [],
        created_by=cohort.created_by,
        created_at=cohort.created_at,
    )


@router.delete("/{cohort_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cohort(
    cohort_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a cohort."""
    require_staff_or_admin(current_user)

    result = await db.execute(select(Cohort).where(Cohort.id == cohort_id))
    cohort = result.scalar_one_or_none()

    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found"
        )

    await db.delete(cohort)
    await db.commit()


@router.post(
    "/{cohort_id}/members",
    response_model=MemberInfo,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    cohort_id: int,
    data: AddMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a member to a cohort."""
    require_staff_or_admin(current_user)

    # Check cohort exists
    result = await db.execute(select(Cohort).where(Cohort.id == cohort_id))
    cohort = result.scalar_one_or_none()
    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found"
        )

    # Check user exists
    result = await db.execute(select(User).where(User.id == data.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check not already a member
    result = await db.execute(
        select(CohortMember).where(
            CohortMember.cohort_id == cohort_id, CohortMember.user_id == data.user_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this cohort",
        )

    member = CohortMember(
        cohort_id=cohort_id,
        user_id=data.user_id,
        role=CohortMemberRole(str(data.role)),
        status=CohortMemberStatus.ACTIVE,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    return MemberInfo(
        id=member.id,
        user_id=member.user_id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=str(member.role),
        status=str(member.status),
        joined_at=member.joined_at,
    )


@router.delete("/{cohort_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    cohort_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from a cohort."""
    require_staff_or_admin(current_user)

    result = await db.execute(
        select(CohortMember).where(
            CohortMember.cohort_id == cohort_id, CohortMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in cohort"
        )

    await db.delete(member)
    await db.commit()


@router.post(
    "/{cohort_id}/trainings",
    response_model=TrainingInfo,
    status_code=status.HTTP_201_CREATED,
)
async def add_training(
    cohort_id: int,
    data: AddTrainingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assign a training course to a cohort."""
    require_staff_or_admin(current_user)

    # Check cohort exists
    result = await db.execute(select(Cohort).where(Cohort.id == cohort_id))
    cohort = result.scalar_one_or_none()
    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found"
        )

    # Check course exists
    result = await db.execute(select(Course).where(Course.id == data.course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    # Check not already assigned
    result = await db.execute(
        select(CohortTraining).where(
            CohortTraining.cohort_id == cohort_id,
            CohortTraining.course_id == data.course_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Course is already assigned to this cohort",
        )

    training = CohortTraining(
        cohort_id=cohort_id, course_id=data.course_id, due_date=data.due_date
    )
    db.add(training)
    await db.commit()
    await db.refresh(training)

    return TrainingInfo(
        id=training.id,
        course_id=training.course_id,
        course_title=course.title,
        due_date=training.due_date,
        assigned_at=training.assigned_at,
    )


@router.delete(
    "/{cohort_id}/trainings/{training_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_training(
    cohort_id: int,
    training_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a training assignment from a cohort."""
    require_staff_or_admin(current_user)

    result = await db.execute(
        select(CohortTraining).where(
            CohortTraining.id == training_id, CohortTraining.cohort_id == cohort_id
        )
    )
    training = result.scalar_one_or_none()

    if not training:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Training not found in cohort"
        )

    await db.delete(training)
    await db.commit()
