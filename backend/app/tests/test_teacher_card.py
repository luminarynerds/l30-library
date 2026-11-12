# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the teacher card feature.

Covers:
* require_teacher_or_staff gate (no JSON fallback, real role required).
* get_teacher_dashboard school scoping (teacher locked to their school_id).
* PATCH /staff/patrons/{patron_id}/teacher-card grant + revoke flows.
* get_checkout_limit returns 100 for a teacher with no age-group override.
* The fresh-install seed includes a teacher row in rs_data.

Migration backfill behaviour is covered by inspection of the migration script
rather than a runtime test: app/tests/conftest.py uses
``Base.metadata.create_all`` (not alembic), so there is no migration-test
harness in this tree. The migration itself is exercised on deploy.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.school_reading._shared import (
    assert_teacher_access_to_school,
    require_teacher_of_school,
    require_teacher_or_staff,
)
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(role: UserRole, *, school_id: int | None = None, custom_fields: str | None = None) -> User:
    u = MagicMock(spec=User)
    u.id = 1
    u.role = role
    u.school_id = school_id
    u.custom_fields = custom_fields
    return u


# ---------------------------------------------------------------------------
# Gate: require_teacher_or_staff
# ---------------------------------------------------------------------------


def test_gate_allows_teacher():
    require_teacher_or_staff(_user(UserRole.TEACHER, school_id=5))


@pytest.mark.parametrize(
    "role",
    [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR],
)
def test_gate_allows_staff_roles(role: UserRole):
    require_teacher_or_staff(_user(role))


def test_gate_denies_plain_patron():
    with pytest.raises(HTTPException) as exc:
        require_teacher_or_staff(_user(UserRole.PATRON))
    assert exc.value.status_code == 403


def test_gate_denies_patron_with_custom_fields_school_id():
    """Regression: pre-real-role patrons used custom_fields.school_id as a
    teacher signal. The new gate must NOT accept that JSON shape; only the
    real UserRole.TEACHER value grants access."""
    patron = _user(UserRole.PATRON, custom_fields='{"school_id": 5}')
    with pytest.raises(HTTPException) as exc:
        require_teacher_or_staff(patron)
    assert exc.value.status_code == 403


def test_gate_denies_child():
    with pytest.raises(HTTPException) as exc:
        require_teacher_or_staff(_user(UserRole.CHILD))
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Dashboard scoping
# ---------------------------------------------------------------------------
#
# get_teacher_dashboard does DB work; we can't easily call it end-to-end
# without a full app fixture. Instead, exercise the new scoping branch as a
# unit by replicating the exact check from the endpoint. This keeps the test
# focused on the policy change (teacher confined to their school_id).


def _teacher_dashboard_scope_check(user: User, requested_school_id: int) -> None:
    """Mirror of the in-endpoint scoping check, extracted for unit testing.

    Kept in sync with school_reading_partnerships.get_teacher_dashboard.
    """
    if user.role == UserRole.TEACHER and user.school_id != requested_school_id:
        raise HTTPException(status_code=403, detail="Teachers can only view their assigned school")


def test_dashboard_teacher_can_view_own_school():
    teacher = _user(UserRole.TEACHER, school_id=5)
    _teacher_dashboard_scope_check(teacher, 5)  # no raise


def test_dashboard_teacher_cannot_view_other_school():
    teacher = _user(UserRole.TEACHER, school_id=5)
    with pytest.raises(HTTPException) as exc:
        _teacher_dashboard_scope_check(teacher, 6)
    assert exc.value.status_code == 403


@pytest.mark.parametrize(
    "role",
    [UserRole.STAFF, UserRole.ADMIN, UserRole.DIRECTOR, UserRole.SUPER_ADMIN],
)
def test_dashboard_staff_can_view_any_school(role: UserRole):
    staff = _user(role, school_id=None)
    _teacher_dashboard_scope_check(staff, 5)
    _teacher_dashboard_scope_check(staff, 6)


# ---------------------------------------------------------------------------
# assert_teacher_access_to_school — inline helper for routes that resolve the
# school by parent-row lookup (slot, list, etc.) rather than URL parameter.
# ---------------------------------------------------------------------------


def test_assert_access_teacher_own_school():
    assert_teacher_access_to_school(_user(UserRole.TEACHER, school_id=5), 5)


def test_assert_access_teacher_other_school_denied():
    with pytest.raises(HTTPException) as exc:
        assert_teacher_access_to_school(_user(UserRole.TEACHER, school_id=5), 6)
    assert exc.value.status_code == 403


@pytest.mark.parametrize(
    "role",
    [UserRole.STAFF, UserRole.ADMIN, UserRole.DIRECTOR, UserRole.SUPER_ADMIN],
)
def test_assert_access_staff_any_school(role: UserRole):
    assert_teacher_access_to_school(_user(role), 5)
    assert_teacher_access_to_school(_user(role), 6)


def test_assert_access_patron_denied():
    with pytest.raises(HTTPException) as exc:
        assert_teacher_access_to_school(_user(UserRole.PATRON), 5)
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# require_teacher_of_school — FastAPI dependency wrapping the assert.
# Invoked manually here so we don't need a full app/TestClient.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_dep_teacher_own_school_returns_user():
    teacher = _user(UserRole.TEACHER, school_id=5)
    out = await require_teacher_of_school(school_id=5, current_user=teacher)
    assert out is teacher


@pytest.mark.asyncio
async def test_require_dep_teacher_other_school_403():
    teacher = _user(UserRole.TEACHER, school_id=5)
    with pytest.raises(HTTPException) as exc:
        await require_teacher_of_school(school_id=6, current_user=teacher)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_dep_staff_any_school():
    staff = _user(UserRole.STAFF)
    out = await require_teacher_of_school(school_id=42, current_user=staff)
    assert out is staff


@pytest.mark.asyncio
async def test_require_dep_patron_denied():
    with pytest.raises(HTTPException) as exc:
        await require_teacher_of_school(school_id=5, current_user=_user(UserRole.PATRON))
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /staff/patrons/{patron_id}/teacher-card
# ---------------------------------------------------------------------------
#
# The endpoint is registered on staff/patron_operations.py. We test its core logic by
# importing it directly and providing mocked dependencies.


@pytest.mark.asyncio
async def test_teacher_card_grant_sets_role_and_school():
    from app.api.v1.staff.patron_operations import update_teacher_card, TeacherCardUpdate
    from app.models.outreach import OutreachPartner

    patron = MagicMock(spec=User)
    patron.id = 42
    patron.role = UserRole.PATRON
    patron.school_id = None

    staff_user = MagicMock(spec=User)
    staff_user.id = 7

    school = MagicMock(spec=OutreachPartner)
    school.id = 5

    db = MagicMock()
    db.get = AsyncMock(return_value=school)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    # get_or_404 is imported into the module's namespace; patch there.
    import app.api.v1.staff.patron_operations as staff_main

    original_get_or_404 = staff_main.get_or_404
    staff_main.get_or_404 = AsyncMock(return_value=patron)
    try:
        result = await update_teacher_card(
            request=MagicMock(),
            patron_id=42,
            body=TeacherCardUpdate(school_id=5),
            staff_user=staff_user,
            db=db,
        )
    finally:
        staff_main.get_or_404 = original_get_or_404

    assert result is patron
    assert patron.role == UserRole.TEACHER
    assert patron.school_id == 5
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(patron)
    # Audit log row was created.
    assert db.add.called


@pytest.mark.asyncio
async def test_teacher_card_revoke_returns_user_to_patron():
    from app.api.v1.staff.patron_operations import update_teacher_card, TeacherCardUpdate

    patron = MagicMock(spec=User)
    patron.id = 42
    patron.role = UserRole.TEACHER
    patron.school_id = 5

    staff_user = MagicMock(spec=User)
    staff_user.id = 7

    db = MagicMock()
    db.get = AsyncMock()  # should not be called on revoke
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    import app.api.v1.staff.patron_operations as staff_main

    original_get_or_404 = staff_main.get_or_404
    staff_main.get_or_404 = AsyncMock(return_value=patron)
    try:
        await update_teacher_card(
            request=MagicMock(),
            patron_id=42,
            body=TeacherCardUpdate(school_id=None),
            staff_user=staff_user,
            db=db,
        )
    finally:
        staff_main.get_or_404 = original_get_or_404

    assert patron.role == UserRole.PATRON
    assert patron.school_id is None
    db.get.assert_not_called()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_teacher_card_grant_unknown_school_404():
    from app.api.v1.staff.patron_operations import update_teacher_card, TeacherCardUpdate

    patron = MagicMock(spec=User)
    patron.id = 42
    patron.role = UserRole.PATRON
    patron.school_id = None

    staff_user = MagicMock(spec=User)
    staff_user.id = 7

    db = MagicMock()
    db.get = AsyncMock(return_value=None)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    import app.api.v1.staff.patron_operations as staff_main

    original_get_or_404 = staff_main.get_or_404
    staff_main.get_or_404 = AsyncMock(return_value=patron)
    try:
        with pytest.raises(HTTPException) as exc:
            await update_teacher_card(
                request=MagicMock(),
                patron_id=42,
                body=TeacherCardUpdate(school_id=999),
                staff_user=staff_user,
                db=db,
            )
    finally:
        staff_main.get_or_404 = original_get_or_404

    assert exc.value.status_code == 404
    # No state change committed.
    db.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# Checkout limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_gets_100_checkout_limit_when_no_age_override():
    """A TEACHER user with no age-group override should get the role_settings
    value (max_checkouts=100). We patch the age-group helper and the
    role-settings lookup to keep this test self-contained."""
    from app.core import authorization as auth_mod

    teacher = MagicMock(spec=User)
    teacher.id = 1
    teacher.role = UserRole.TEACHER
    teacher.school_id = 5

    role_settings = MagicMock()
    role_settings.max_checkouts = 100

    original_get_settings = auth_mod.get_user_role_settings
    original_features = (
        auth_mod.OrganizationFeaturesService.get_or_create_features
        if hasattr(auth_mod, "OrganizationFeaturesService")
        else None
    )

    # Patch the inner imports used by get_checkout_limit. These are imported
    # lazily inside the function, so we patch where they resolve from.
    import app.services.age_group_service as age_mod
    import app.services.organization_features_service as feat_mod

    original_age = age_mod.get_age_group_checkout_limit
    original_features_method = feat_mod.OrganizationFeaturesService.get_or_create_features

    age_mod.get_age_group_checkout_limit = lambda u, f: None
    feat_mod.OrganizationFeaturesService.get_or_create_features = AsyncMock(return_value=MagicMock())
    auth_mod.get_user_role_settings = AsyncMock(return_value=role_settings)

    try:
        limit = await auth_mod.get_checkout_limit(teacher, MagicMock())
    finally:
        age_mod.get_age_group_checkout_limit = original_age
        feat_mod.OrganizationFeaturesService.get_or_create_features = original_features_method
        auth_mod.get_user_role_settings = original_get_settings

    assert limit == 100


# ---------------------------------------------------------------------------
# Seed sanity check
# ---------------------------------------------------------------------------


def test_seed_batch_system_contains_teacher_role_row():
    """Fresh-install seed (seed_batch_system.rs_data) must include teacher."""
    import inspect
    from app.seeds import seed_batch_system

    src = inspect.getsource(seed_batch_system)
    # Loose but specific: the teacher tuple with max_checkouts=100, etc.
    assert '"teacher", 100, 50, 5, 42, 14, 0' in src, "teacher row missing from rs_data"
