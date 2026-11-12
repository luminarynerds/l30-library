# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Navigation API endpoints for role-based navigation filtering.

Provides:
- GET /api/v1/navigation: Returns navigation items for current user's role
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User, UserRole
from app.api.v1.auth import get_current_user
from app.schemas.navigation import NavigationResponse
from app.services.navigation_service import (
    get_navigation_for_user,
    can_access_admin_pages,
    can_access_staff_pages,
)

router = APIRouter(prefix="/navigation", tags=["navigation"])


@router.get(
    "",
    response_model=NavigationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get role-based navigation",
    description="Returns navigation items filtered by the current user's role",
    responses={
        200: {
            "description": "Navigation items for user's role",
            "content": {
                "application/json": {
                    "example": {
                        "sections": [
                            {
                                "id": "staff_main",
                                "label": "Staff Operations",
                                "items": [
                                    {
                                        "id": "staff_home",
                                        "label": "Staff Home",
                                        "path": "/staff",
                                        "icon": "Briefcase",
                                        "description": "Staff dashboard",
                                        "requiresAuth": True,
                                        "roles": ["STAFF", "ADMIN", "SUPER_ADMIN"],
                                    }
                                ],
                            }
                        ],
                        "role": "STAFF",
                        "canAccessAdmin": False,
                        "canAccessStaff": True,
                    }
                }
            },
        },
        401: {"description": "Unauthorized - user not authenticated"},
    },
)
async def get_navigation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NavigationResponse:
    """
    Get navigation structure for the current user.

    Returns only navigation items that the user is authorized to see based on their role:
    - STAFF: Sees staff operations (circulation, patrons, catalog, acquisition)
    - ADMIN: Sees staff + admin settings (features, site settings, users, roles, audit)
    - SUPER_ADMIN: Sees everything including system administration

    The endpoint enforces role-based access control. Direct URL access to restricted
    pages should be blocked by the frontend and validated by individual route handlers.
    """
    navigation = get_navigation_for_user(current_user)
    return navigation


@router.get(
    "/check-access/{path:path}",
    status_code=status.HTTP_200_OK,
    summary="Check if user can access a path",
    description="Validates if the current user can access a given path based on their role",
    responses={
        200: {
            "description": "Access check result",
            "content": {
                "application/json": {
                    "example": {
                        "allowed": True,
                        "role": "STAFF",
                        "path": "/staff/circulation",
                        "requiredRoles": ["STAFF", "ADMIN", "SUPER_ADMIN"],
                    }
                }
            },
        },
        401: {"description": "Unauthorized - user not authenticated"},
    },
)
async def check_access(
    path: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Check if the current user has access to a specific path.

    This is a validation endpoint for the frontend to check access before
    attempting to navigate to a route. The backend also enforces access control
    on individual route handlers.

    Args:
        path: The path to check access for (e.g., "/staff/circulation", "/admin/features")

    Returns:
        Dictionary with:
        - allowed: bool - whether user can access the path
        - role: str - user's current role
        - path: str - the path being checked
        - canAccessStaff: bool - whether user can access staff pages
        - canAccessAdmin: bool - whether user can access admin pages
    """
    # Path-based role mapping for validation.
    # FastAPI captures a {path:path} param WITHOUT its leading slash
    # ("admin/features", not "/admin/features"), so matching it against the
    # "/admin/"-style prefixes below was ALWAYS False and every caller fell
    # through to allowed=True regardless of role. Normalize first.
    path_lower = "/" + path.lower().lstrip("/")

    can_access_admin = can_access_admin_pages(current_user)
    can_access_staff = can_access_staff_pages(current_user)

    # Determine if path requires admin access
    admin_paths = [
        "/admin/",
        "/admin",
    ]
    requires_admin = any(path_lower.startswith(ap) for ap in admin_paths)

    # Determine if path requires staff access
    staff_paths = [
        "/staff/",
        "/staff",
    ]
    requires_staff = any(path_lower.startswith(sp) for sp in staff_paths)

    # Determine access
    allowed = True
    if requires_admin:
        allowed = can_access_admin
    elif requires_staff:
        allowed = can_access_staff

    return {
        "allowed": allowed,
        "role": str(current_user.role),
        "path": path,
        "canAccessStaff": can_access_staff,
        "canAccessAdmin": can_access_admin,
        "requiredAdmin": requires_admin,
        "requiredStaff": requires_staff,
    }
