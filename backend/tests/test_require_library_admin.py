# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the require_library_admin FastAPI dependency.

These tests exercise the dependency function directly (no app, no DB,
no HTTP) so they remain fast and isolated. End-to-end coverage of
401 behavior comes from the upstream get_current_user dep, which the
existing auth test suite already covers; here we just verify that
require_library_admin gates correctly on a given User.
"""
import pytest
from fastapi import HTTPException

from app.api.v1.dependencies import require_library_admin
from app.models.user import User, UserRole


def _user(role: UserRole) -> User:
    """Build a minimal User for dep evaluation. No DB session involved."""
    return User(
        email=f"{role.value}@example.com",
        password_hash="x",
        first_name="T",
        last_name="User",
        role=role,
        is_active=True,
        email_verified=True,
    )


@pytest.mark.asyncio
async def test_library_admin_passes():
    user = _user(UserRole.LIBRARY_ADMIN)
    result = await require_library_admin(current_user=user)
    assert result is user


@pytest.mark.asyncio
async def test_staff_is_forbidden():
    user = _user(UserRole.STAFF)
    with pytest.raises(HTTPException) as exc_info:
        await require_library_admin(current_user=user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "library_admin role required"


@pytest.mark.asyncio
async def test_patron_is_forbidden():
    user = _user(UserRole.PATRON)
    with pytest.raises(HTTPException) as exc_info:
        await require_library_admin(current_user=user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "library_admin role required"


@pytest.mark.asyncio
async def test_admin_is_forbidden():
    """ADMIN is a SYSTEM admin, not a LIBRARY admin. The dep is strict by
    design — feature routes that want both can compose deps."""
    user = _user(UserRole.ADMIN)
    with pytest.raises(HTTPException) as exc_info:
        await require_library_admin(current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_enum_value_is_lowercase():
    """L30 convention: all UserRole enum *values* must be lowercase strings.
    Catches typos like 'LibraryAdmin' or 'LIBRARY_ADMIN' as the value."""
    assert UserRole.LIBRARY_ADMIN.value == "library_admin"
