# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Roles Management API Endpoints
Provides CRUD operations for roles and role-permission mappings.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...core.rate_limit import limiter
from ...models.permission import Permission, RolePermission, RoleSettings
from ...models.user import User, UserRole

from .dependencies import require_admin

router = APIRouter(prefix="/roles", tags=["roles"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class RolePermissionResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    category: str

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    permissions: List[str] = []


class RoleCreateUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


# =============================================================================
# Helper Functions
# =============================================================================


def get_role_description(role: UserRole) -> str:
    descriptions = {
        UserRole.SUPER_ADMIN: "Full system access with all permissions",
        UserRole.ADMIN: "Administrative access for managing library operations",
        UserRole.STAFF: "Staff access for daily library operations",
        UserRole.PATRON: "Standard library patron account",
        UserRole.CHILD: "Child patron account with parental controls",
        UserRole.BOOKMOBILE: "Bookmobile service patron",
        UserRole.HOMEBOND: "HomeDelivery delivery service patron",
    }
    return descriptions.get(role, "Library system role")


async def get_role_permissions(db: AsyncSession, role: UserRole) -> List[str]:
    result = await db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role == role)
    )
    return [row[0] for row in result.all()]


async def get_all_role_permissions(db: AsyncSession) -> dict[UserRole, List[str]]:
    result = await db.execute(
        select(RolePermission.role, Permission.code)
        .join(Permission, RolePermission.permission_id == Permission.id)
    )

    # Group permissions by role
    role_permissions: dict[UserRole, List[str]] = {role: [] for role in UserRole}
    for row in result.all():
        role, code = row
        if role in role_permissions:
            role_permissions[role].append(code)

    return role_permissions


# =============================================================================
# Role Endpoints
# =============================================================================


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all available roles with their permissions."""
    # Fetch all role permissions in a single query (fixes N+1)
    all_permissions = await get_all_role_permissions(db)

    roles = []
    for role in UserRole:
        roles.append(
            RoleResponse(
                id=role.value,
                name=role.value.replace("_", " ").title(),
                description=get_role_description(role),
                permissions=all_permissions.get(role, []),
            )
        )
    return roles


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific role by ID."""
    try:
        role = UserRole(role_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found") from None

    permissions = await get_role_permissions(db, role)
    return RoleResponse(
        id=role.value,
        name=role.value.replace("_", " ").title(),
        description=get_role_description(role),
        permissions=permissions,
    )


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_role(
    request: Request,
    role_data: RoleCreateUpdate,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new role.
    Note: Roles are defined as enums in the system. This endpoint
    is provided for API consistency but returns an error as custom
    roles are not supported.
    """
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Custom roles are not supported. Roles are predefined in the system.",
    )


@router.put("/{role_id}", response_model=RoleResponse)
@limiter.limit("10/minute")
async def update_role(
    request: Request,
    role_id: str,
    role_data: RoleCreateUpdate,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a role.
    Note: Role names are predefined in the system. This endpoint
    returns the existing role information.
    """
    try:
        role = UserRole(role_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found") from None

    permissions = await get_role_permissions(db, role)
    return RoleResponse(
        id=role.value,
        name=role.value.replace("_", " ").title(),
        description=role_data.description or get_role_description(role),
        permissions=permissions,
    )


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_role(
    request: Request,
    role_id: str,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a role.
    Note: Roles are predefined in the system and cannot be deleted.
    """
    try:
        UserRole(role_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found") from None

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="System roles cannot be deleted.",
    )


# =============================================================================
# Role-Permission Mapping Endpoints
# =============================================================================


@router.post("/{role_id}/permissions/{permission_id}", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def add_permission_to_role(
    request: Request,
    role_id: str,
    permission_id: int,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Add a permission to a role."""
    # Validate role
    try:
        role = UserRole(role_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found") from None

    # Validate permission
    await get_or_404(db, Permission, permission_id, "Permission not found")

    # Check if mapping already exists
    existing = await db.execute(
        select(RolePermission).where(
            RolePermission.role == role,
            RolePermission.permission_id == permission_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Permission already assigned to this role"
        )

    # Create the mapping
    role_permission = RolePermission(role=role, permission_id=permission_id)
    db.add(role_permission)
    await db.commit()

    # Return updated role
    permissions = await get_role_permissions(db, role)
    return RoleResponse(
        id=role.value,
        name=role.value.replace("_", " ").title(),
        description=get_role_description(role),
        permissions=permissions,
    )


@router.delete("/{role_id}/permissions/{permission_id}", response_model=RoleResponse)
@limiter.limit("20/minute")
async def remove_permission_from_role(
    request: Request,
    role_id: str,
    permission_id: int,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Remove a permission from a role."""
    # Validate role
    try:
        role = UserRole(role_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Role not found") from None

    # Find and delete the mapping
    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role == role,
            RolePermission.permission_id == permission_id,
        )
    )
    role_permission = result.scalar_one_or_none()
    if not role_permission:
        raise HTTPException(
            status_code=404, detail="Permission not assigned to this role"
        )

    await db.delete(role_permission)
    await db.commit()

    # Return updated role
    permissions = await get_role_permissions(db, role)
    return RoleResponse(
        id=role.value,
        name=role.value.replace("_", " ").title(),
        description=get_role_description(role),
        permissions=permissions,
    )
