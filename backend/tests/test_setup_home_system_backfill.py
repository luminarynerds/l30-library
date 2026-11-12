# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
TDD tests for two home_library_system_id gaps:
  A. save_library_info must backfill NULL home_library_system_id on all users.
  B. create_user must inherit the admin's home_library_system_id.
"""
import pytest

from app.api.v1.auth import get_current_user
from app.api.v1.setup.router import require_setup_access
from app.main import app
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Part A -- backfill
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_client_no_org(client, test_admin):
    """Admin client; test_admin starts with home_library_system_id=None."""
    app.dependency_overrides[get_current_user] = lambda: test_admin
    # Bypass require_setup_access (no SystemSettings row in test DB)
    app.dependency_overrides[require_setup_access] = lambda: None
    yield client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_setup_access, None)


@pytest.mark.asyncio
async def test_save_library_info_backfills_admin_home_library_system_id(
    admin_client_no_org, test_admin, test_db
):
    """After POST /setup/library-info creates a new system, the founding
    admin (who has home_library_system_id=None) must be updated to point
    at that new system.
    """
    # Precondition: admin has no org yet
    assert test_admin.home_library_system_id is None

    resp = await admin_client_no_org.post(
        "/api/v1/setup/library-info",
        json={"name": "Backfill Test Library", "code": "BTL"},
    )
    assert resp.status_code == 200, resp.text

    # Reload admin from DB
    await test_db.refresh(test_admin)
    assert test_admin.home_library_system_id is not None, (
        "save_library_info must backfill home_library_system_id for users with NULL org"
    )


@pytest.mark.asyncio
async def test_save_library_info_does_not_backfill_on_update(
    admin_client_no_org, test_admin, test_db
):
    """If a LibrarySystem already exists, save_library_info is an update path.
    Users already attached to a different system must NOT be re-assigned.
    """
    from app.models.multi_branch import LibrarySystem

    # Create a pre-existing system and attach the admin to it
    sys_a = LibrarySystem(code="SYSA", name="System A")
    test_db.add(sys_a)
    await test_db.flush()
    test_admin.home_library_system_id = sys_a.id
    test_db.add(test_admin)
    await test_db.commit()
    await test_db.refresh(test_admin)

    original_id = test_admin.home_library_system_id
    assert original_id == sys_a.id

    # POST an update (system already exists -> update path, not create path)
    resp = await admin_client_no_org.post(
        "/api/v1/setup/library-info",
        json={"name": "Updated Name", "code": "SYSA"},
    )
    assert resp.status_code == 200, resp.text

    await test_db.refresh(test_admin)
    assert test_admin.home_library_system_id == original_id, (
        "save_library_info update path must not overwrite existing org assignments"
    )


# ---------------------------------------------------------------------------
# Part B -- create_user inherits org
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_with_org(test_db):
    """An ADMIN user pre-attached to a library system."""
    from app.models.multi_branch import LibrarySystem

    lib = LibrarySystem(code="ORG5", name="Org Five Library")
    test_db.add(lib)
    await test_db.flush()

    admin = User(
        email="admin-with-org@test.org",
        role=UserRole.ADMIN,
        home_library_system_id=lib.id,
        first_name="Admin",
        last_name="WithOrg",
        is_active=True,
        email_verified=True,
    )
    setattr(admin, "password_hash", "x")
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    admin._test_lib_id = lib.id
    return admin


@pytest.fixture
def admin_org_client(client, admin_with_org):
    app.dependency_overrides[get_current_user] = lambda: admin_with_org
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_create_user_inherits_admin_home_library_system_id(
    admin_org_client, admin_with_org, test_db
):
    """Users created via POST /api/v1/users must inherit the admin's
    home_library_system_id so they are org-scoped for the checklist counters.
    """
    expected_lsid = admin_with_org._test_lib_id

    resp = await admin_org_client.post(
        "/api/v1/users",
        json={
            "email": "new-staff@test.org",
            "password": "securepass123",
            "first_name": "New",
            "last_name": "Staff",
            "role": "staff",
        },
    )
    assert resp.status_code == 201, resp.text

    from sqlalchemy import select
    result = await test_db.execute(
        select(User).where(User.email == "new-staff@test.org")
    )
    new_user = result.scalar_one()
    assert new_user.home_library_system_id == expected_lsid, (
        f"create_user must inherit admin home_library_system_id "
        f"(expected {expected_lsid}, got {new_user.home_library_system_id})"
    )
