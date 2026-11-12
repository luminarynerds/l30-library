# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Centralized Authorization Dependencies

This module provides standardized authentication and authorization dependencies
for all API endpoints. Use these instead of defining local authorization helpers.

Usage:
    from .dependencies import require_staff, require_admin, require_super_admin, get_age_verified_user

    @router.get("/protected")
    async def protected_endpoint(user: User = Depends(require_staff)):
        ...

"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User, UserRole

# SECURITY: Auth module must import successfully. No fallback — fail loud, not open.
from .auth import get_current_user, get_optional_user

# Alias for backward compatibility
get_current_user_optional = get_optional_user


# =============================================================================
# Role-Based Authorization Dependencies
# =============================================================================


async def require_authenticated(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


async def require_patron(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.PATRON:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patron access required",
        )
    return current_user


async def require_staff(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR, UserRole.LEGAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or admin role required",
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_director(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in [UserRole.DIRECTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Director access required",
        )
    return current_user


async def require_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user


async def require_director_or_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in [UserRole.DIRECTOR, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Director or super admin access required",
        )
    return current_user


async def require_library_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.LIBRARY_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="library_admin role required",
        )
    return current_user


# =============================================================================
# Helper Functions for In-Endpoint Authorization
# =============================================================================


def is_staff_or_admin(user: User) -> bool:
    return user.role in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR, UserRole.LEGAL]


def is_admin(user: User) -> bool:
    return user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]


def is_super_admin(user: User) -> bool:
    return user.role == UserRole.SUPER_ADMIN


def check_staff_access(user: User) -> None:
    if not is_staff_or_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or admin role required",
        )


def check_admin_access(user: User) -> None:
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


def can_access_course(user: User, course) -> bool:
    if course.access_level == "patron":
        return True
    if course.access_level == "staff" and is_staff_or_admin(user):
        return True
    if course.access_level == "admin" and is_admin(user):
        return True
    return False


