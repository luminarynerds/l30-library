# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Permissions Management API Endpoints
Provides read access to system permissions.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.permission import Permission
from ...models.user import User

from .dependencies import require_admin

router = APIRouter(prefix="/permissions", tags=["permissions"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class PermissionResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    category: str

    class Config:
        from_attributes = True


# =============================================================================
# Permission Endpoints
# =============================================================================


@router.get("", response_model=List[PermissionResponse])
async def list_permissions(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all available permissions."""
    result = await db.execute(
        select(Permission).order_by(Permission.category, Permission.name)
    )
    permissions = result.scalars().all()
    return permissions


@router.get("/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: int,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific permission by ID."""
    from fastapi import HTTPException

    permission = await get_or_404(db, Permission, permission_id, "Permission not found")
    return permission
