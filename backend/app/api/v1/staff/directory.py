# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Directory Endpoints

Provides endpoints for:
- Staff member listing and search
- Staff member details view
- Staff profiles with contact information
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User, UserRole, name_or_email_clause
from ....schemas.user import UserResponse
from ..dependencies import require_staff

router = APIRouter(prefix="/staff", tags=["staff-directory"])


class StaffMemberResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    created_at: str | None = None

    class Config:
        from_attributes = True


class StaffDirectoryResponse(BaseModel):
    staff_members: list[StaffMemberResponse]
    total: int
    page: int
    per_page: int
    pages: int


@router.get("/directory", response_model=StaffDirectoryResponse)
async def list_staff_directory(
    q: Optional[str] = Query(None, description="Search by name, email, or role"),
    role: Optional[str] = Query(None, description="Filter by role (staff or admin)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    List staff members in the directory with search and filtering.

    Staff can search by:
    - Name (first_name, last_name)
    - Email address
    - Role (staff or admin)
    - Active status

    Returns paginated results with staff member details.
    """
    # Base query: only staff and admin roles
    query = select(User).where(User.role.in_([UserRole.STAFF, UserRole.ADMIN]))
    count_query = select(func.count(User.id)).where(
        User.role.in_([UserRole.STAFF, UserRole.ADMIN])
    )

    # Apply search filter
    if q:
        # Names + email encrypted: blind-index match (exact/last-prefix names,
        # exact email), not substring.
        search_filter = name_or_email_clause(q)
        if search_filter is not None:
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

    # Apply role filter
    if role:
        role_upper = role.upper()
        if role_upper in [UserRole.STAFF, UserRole.ADMIN]:
            query = query.where(User.role == role_upper)
            count_query = count_query.where(User.role == role_upper)

    # Apply active status filter
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(User.first_name, User.last_name)

    # Fetch results
    result = await db.execute(query)
    staff_members = result.scalars().all()

    # Convert to response models
    pages = (total + per_page - 1) // per_page if total > 0 else 1

    return StaffDirectoryResponse(
        staff_members=[
            StaffMemberResponse(
                id=member.id,
                email=member.email,
                first_name=member.first_name,
                last_name=member.last_name,
                role=member.role,
                is_active=member.is_active,
                created_at=member.created_at.isoformat() if member.created_at else None,
            )
            for member in staff_members
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/directory/{staff_id}", response_model=StaffMemberResponse)
async def get_staff_member(
    staff_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get details for a specific staff member.

    Returns staff member profile information including:
    - Contact information (email, name)
    - Role and status
    - Account creation date
    """
    result = await db.execute(
        select(User).where(
            User.id == staff_id, User.role.in_([UserRole.STAFF, UserRole.ADMIN])
        )
    )
    staff_member = result.scalar_one_or_none()

    if not staff_member:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Staff member not found")

    return StaffMemberResponse(
        id=staff_member.id,
        email=staff_member.email,
        first_name=staff_member.first_name,
        last_name=staff_member.last_name,
        role=staff_member.role,
        is_active=staff_member.is_active,
        created_at=staff_member.created_at.isoformat()
        if staff_member.created_at
        else None,
    )


# =============================================================================
# Legacy staff listing endpoints
# Moved from staff/main.py during package-split refactor. These predate the
# /directory/ endpoints above and are still consumed by older staff UI views.
# NOTE: declared AFTER /directory/* so the literal /directory path wins; the
# typed /{staff_id:int} converter limits collisions to integer-only segments.
# =============================================================================


class StaffListResponse(BaseModel):
    staff: list[UserResponse]
    total_count: int


@router.get("", response_model=StaffListResponse)
async def list_staff(
    search: Optional[str] = Query(None, description="Search by name or email"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all staff members (STAFF, ADMIN, SUPER_ADMIN, DIRECTOR roles)."""
    query = select(User).where(User.role.in_([UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]))
    count_query = select(func.count(User.id)).where(User.role.in_([UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]))

    if search:
        search_filter = name_or_email_clause(search)
        if search_filter is not None:
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(User.last_name, User.first_name).offset(offset).limit(limit)
    )
    staff = result.scalars().all()

    return StaffListResponse(
        staff=[UserResponse.model_validate(s) for s in staff],
        total_count=total_count,
    )


@router.get("/{staff_id:int}", response_model=UserResponse)
async def get_staff_member(
    staff_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get specific staff member information."""
    from fastapi import HTTPException
    result = await db.execute(
        select(User).where(
            User.id == staff_id,
            User.role.in_([UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN])
        )
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
    return staff
