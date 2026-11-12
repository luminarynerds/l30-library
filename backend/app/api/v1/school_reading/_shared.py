# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared helpers for the school_reading sub-routers.

Extracted from the former monolith ``school_reading_partnerships.py`` so that
each sub-router (lists_and_badges, programs, tiers, family_engagement) can
import the same authorization gate and patron-PII scrub without circular
imports.
"""

from fastapi import Depends, HTTPException, status

from ..auth import get_current_user
from ....models.user import User, UserRole

# Roles that may view any school's data (no per-school binding).
_STAFF_LEVEL_ROLES = frozenset({
    UserRole.STAFF,
    UserRole.ADMIN,
    UserRole.SUPER_ADMIN,
    UserRole.DIRECTOR,
})


def require_teacher_or_staff(user: User):
    if user.role in _STAFF_LEVEL_ROLES or user.role == UserRole.TEACHER:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Teacher or staff access required",
    )


def assert_teacher_access_to_school(user: User, school_id: int) -> None:
    require_teacher_or_staff(user)
    if user.role == UserRole.TEACHER and user.school_id != school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teachers can only access their assigned school",
        )


async def require_teacher_of_school(
    school_id: int,
    current_user: User = Depends(get_current_user),
) -> User:
    assert_teacher_access_to_school(current_user, school_id)
    return current_user


# --------------------------------------------------------------------------
# Data isolation boundary for student/patron data.
# Teachers see aggregate metrics only.  Any dict returned to a teacher-facing
# endpoint MUST pass through _strip_patron_identifiers() so that individual
# student records can never leak, even if the upstream query or serialization
# changes.  This is a defense-in-depth measure -- do not rely on the query or
# Pydantic schema alone to enforce this.
# --------------------------------------------------------------------------

_PATRON_ID_FIELDS = frozenset({
    "user_id", "patron_id", "patron_name", "email", "library_card",
    "barcode", "parent_user_id", "child_user_id", "requestor_email",
    "requestor_phone",
})


def _strip_patron_identifiers(data):
    if isinstance(data, dict):
        return {
            k: _strip_patron_identifiers(v)
            for k, v in data.items()
            if k not in _PATRON_ID_FIELDS
        }
    if isinstance(data, list):
        return [_strip_patron_identifiers(item) for item in data]
    return data
