# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Family/Household registration API for reading programs.
Allows a parent to register children (COPPA-compliant)
and view family-wide reading progress.
"""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...core.shortcuts import get_or_404
from ...models.program_family import ProgramFamilyGroup, ProgramFamilyMember
from ...models.reading import (
    ReadingAchievement, ReadingLogEntry, ReadingProgram, ReadingRegistration,
)
from ...models.user import User
from ...schemas.program_family import (
    FamilyGroupCreate, FamilyGroupResponse,
    FamilyMemberCreate, FamilyMemberResponse,
    FamilyMemberProgressResponse,
    FamilyMemberRegistrationResponse,
    FamilyProgressResponse,
    FamilyRegistrationRequest, FamilyRegistrationResponse,
)
from .auth import get_current_user
from ...services.organization_features_service import OrganizationFeaturesService


async def require_reading_programs_enabled(db: AsyncSession = Depends(get_db)) -> None:
    enabled = await OrganizationFeaturesService.is_feature_enabled(db, "reading_programs_enabled")
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reading programs feature is not enabled",
        )


router = APIRouter(
    prefix="/reading-programs/family",
    tags=["reading-programs-family"],
    dependencies=[Depends(require_reading_programs_enabled)],
)


async def _get_family_group(db: AsyncSession, user_id: int) -> ProgramFamilyGroup:
    result = await db.execute(
        select(ProgramFamilyGroup)
        .options(selectinload(ProgramFamilyGroup.members))
        .where(ProgramFamilyGroup.parent_user_id == user_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No family group found. Create one first.",
        )
    return group


# ============================================================================
# Family Group CRUD
# ============================================================================


@router.post("", response_model=FamilyGroupResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_family_group(
    request: Request,
    payload: FamilyGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a family group. One per parent account."""
    existing = await db.execute(
        select(ProgramFamilyGroup).where(
            ProgramFamilyGroup.parent_user_id == current_user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a family group.",
        )

    group = ProgramFamilyGroup(
        parent_user_id=current_user.id,
        name=payload.name,
    )
    # Add parent as a member
    parent_member = ProgramFamilyMember(
        first_name=current_user.first_name or "Parent",
        age_range="13-17",  # placeholder for adult
        is_parent=True,
    )
    group.members.append(parent_member)

    db.add(group)
    await db.commit()
    await db.refresh(group, attribute_names=["members"])

    return FamilyGroupResponse.model_validate(group)


@router.get("", response_model=FamilyGroupResponse)
@limiter.limit("60/minute")
async def get_family_group(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's family group with all members."""
    group = await _get_family_group(db, current_user.id)
    return FamilyGroupResponse.model_validate(group)


# ============================================================================
# Family Members
# ============================================================================


@router.post("/{family_id}/members", response_model=FamilyMemberResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def add_family_member(
    request: Request,
    family_id: int,
    payload: FamilyMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a child member to the family group. COPPA: first name + age range only."""
    group = await _get_family_group(db, current_user.id)

    if group.id != family_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your family group.")

    # Cap at 10 children per family
    child_count = sum(1 for m in group.members if not m.is_parent)
    if child_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 children per family group.",
        )

    member = ProgramFamilyMember(
        family_group_id=group.id,
        first_name=payload.first_name,
        age_range=payload.age_range,
        is_parent=False,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    return FamilyMemberResponse.model_validate(member)


@router.delete("/{family_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def remove_family_member(
    request: Request,
    family_id: int,
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a child from the family group. Cannot remove the parent member."""
    group = await _get_family_group(db, current_user.id)

    if group.id != family_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your family group.")

    result = await db.execute(
        select(ProgramFamilyMember).where(
            and_(
                ProgramFamilyMember.id == member_id,
                ProgramFamilyMember.family_group_id == group.id,
            )
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

    if member.is_parent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the parent member.",
        )

    await db.delete(member)
    await db.commit()


# ============================================================================
# Family Program Registration
# ============================================================================


@router.post(
    "/{program_id}/register",
    response_model=FamilyRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def family_register_for_program(
    request: Request,
    program_id: int,
    payload: FamilyRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register selected family members in a reading program at once."""
    group = await _get_family_group(db, current_user.id)

    program = await get_or_404(db, ReadingProgram, program_id, "Program not found")
    if not program.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program is not active.")

    today = date.today()
    if today < program.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration opens on {program.start_date.isoformat()}",
        )
    if today > program.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This program has ended.",
        )

    # Validate all member_ids belong to this family
    member_ids_set = set(payload.member_ids)
    group_member_map = {m.id: m for m in group.members}
    invalid = member_ids_set - set(group_member_map.keys())
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Member IDs {invalid} do not belong to your family group.",
        )

    registrations = []
    for mid in payload.member_ids:
        member = group_member_map[mid]

        # Skip if already registered for this program
        if member.participant_id:
            existing_reg = await db.execute(
                select(ReadingRegistration).where(
                    and_(
                        ReadingRegistration.id == member.participant_id,
                        ReadingRegistration.program_id == program_id,
                    )
                )
            )
            if existing_reg.scalar_one_or_none():
                continue

        # For parent member, use user_id; for children, also use parent's user_id
        # (COPPA: children don't have their own accounts)
        reg = ReadingRegistration(
            user_id=current_user.id,
            program_id=program_id,
            goal_target=payload.goal_target,
        )
        db.add(reg)
        await db.flush()

        member.participant_id = reg.id
        registrations.append(
            FamilyMemberRegistrationResponse(
                member_id=member.id,
                first_name=member.first_name,
                registration_id=reg.id,
                program_id=program_id,
            )
        )

    if not registrations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All selected members are already registered for this program.",
        )

    await db.commit()

    return FamilyRegistrationResponse(
        program_id=program_id,
        program_name=program.name,
        registrations=registrations,
    )


# ============================================================================
# Family Progress Dashboard
# ============================================================================


@router.get("/progress", response_model=FamilyProgressResponse)
@limiter.limit("60/minute")
async def get_family_progress(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Family progress dashboard: all members' reading logs, badges, completion %."""
    group = await _get_family_group(db, current_user.id)

    member_progress: list[FamilyMemberProgressResponse] = []
    family_total_minutes = 0
    family_total_books = 0

    for member in group.members:
        mp = FamilyMemberProgressResponse(
            member_id=member.id,
            first_name=member.first_name,
            age_range=member.age_range,
            is_parent=member.is_parent,
            registration_id=member.participant_id,
        )

        if member.participant_id:
            # Get registration with program
            reg_result = await db.execute(
                select(ReadingRegistration)
                .options(selectinload(ReadingRegistration.program))
                .where(ReadingRegistration.id == member.participant_id)
            )
            reg = reg_result.scalar_one_or_none()

            if reg:
                mp.program_name = reg.program.name if reg.program else None

                # Reading stats
                stats_result = await db.execute(
                    select(
                        func.coalesce(func.sum(ReadingLogEntry.minutes_read), 0),
                        func.coalesce(func.sum(ReadingLogEntry.books_read), 0),
                        func.coalesce(func.sum(ReadingLogEntry.pages_read), 0),
                    ).where(ReadingLogEntry.registration_id == reg.id)
                )
                stats = stats_result.one()
                mp.total_minutes = int(stats[0])
                mp.total_books = int(stats[1])
                mp.total_pages = int(stats[2])

                # Completion %
                goal = reg.goal_target or (reg.program.reading_goal_value if reg.program else None)
                if goal and goal > 0:
                    goal_type = reg.program.reading_goal_type if reg.program else "minutes"
                    progress_val = {
                        "minutes": mp.total_minutes,
                        "books": mp.total_books,
                        "pages": mp.total_pages,
                    }.get(goal_type, mp.total_minutes)
                    mp.completion_percentage = min(100.0, round((progress_val / goal) * 100, 1))

                # Achievement count
                ach_result = await db.execute(
                    select(func.count(ReadingAchievement.id)).where(
                        and_(
                            ReadingAchievement.user_id == current_user.id,
                            ReadingAchievement.program_id == reg.program_id,
                        )
                    )
                )
                mp.achievements_count = ach_result.scalar() or 0

                family_total_minutes += mp.total_minutes
                family_total_books += mp.total_books

        member_progress.append(mp)

    return FamilyProgressResponse(
        family_id=group.id,
        family_name=group.name,
        members=member_progress,
        family_total_minutes=family_total_minutes,
        family_total_books=family_total_books,
    )
