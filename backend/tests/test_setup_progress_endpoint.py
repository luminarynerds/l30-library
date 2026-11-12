# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.multi_branch import LibrarySystem
from app.models.user import UserRole

EXPECTED_STEP_IDS = {
    'add_team',
    'set_policies',
    'build_catalog',
    'add_holdings',
    'add_patrons',
    'first_checkout',
}


@pytest.fixture
async def library_system(test_db):
    sys = LibrarySystem(code='PROG', name='Progress Test Library')
    test_db.add(sys)
    await test_db.flush()
    await test_db.commit()
    await test_db.refresh(sys)
    return sys


@pytest.fixture
def admin_client(client, test_admin):
    app.dependency_overrides[get_current_user] = lambda: test_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def patron_client(client, test_patron):
    app.dependency_overrides[get_current_user] = lambda: test_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_patron_is_forbidden(patron_client):
    resp = await patron_client.get('/api/v1/setup/progress')
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_with_library_system_gets_progress(
    admin_client, test_admin, library_system, test_db
):
    from app.models.user import User, UserRole

    test_admin.home_library_system_id = library_system.id
    test_db.add(test_admin)
    await test_db.flush()

    # Add a second staff user so add_team flips to complete (count > 1).
    # The admin above is the 1st staff user; this makes count == 2.
    extra = User(
        email="extra-staff@x.org",
        role=UserRole.STAFF,
        home_library_system_id=library_system.id,
        first_name="Ex",
        last_name="Tra",
    )
    setattr(extra, "password_hash", "x")
    test_db.add(extra)
    await test_db.commit()

    resp = await admin_client.get('/api/v1/setup/progress')
    assert resp.status_code == 200

    body = resp.json()
    assert body['total'] == 6
    assert len(body['steps']) == 6
    assert {s['id'] for s in body['steps']} == EXPECTED_STEP_IDS

    # Ground-truth assertion: only add_team should be complete (2 staff users,
    # no CirculationPolicy, no CatalogItem, no ItemCopy, no Checkout, no Patron).
    assert body['completed_count'] == 1

    steps = {s['id']: s for s in body['steps']}
    assert steps['add_team']['completed'] is True
    assert steps['add_team']['count'] == 2
    assert steps['set_policies']['completed'] is False


@pytest.mark.asyncio
async def test_admin_without_library_system_gets_409(admin_client, test_admin, test_db):
    # test_admin is function-scoped, so this mutation is local to this test.
    test_admin.home_library_system_id = None
    test_db.add(test_admin)
    await test_db.commit()

    resp = await admin_client.get('/api/v1/setup/progress')
    assert resp.status_code == 409
