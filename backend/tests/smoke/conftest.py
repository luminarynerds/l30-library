# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixtures for the smoke suite.

Mirrors the project-wide `staff_client`/`public_client` (tests/conftest.py)
but adds patron- and admin-authenticated clients, which the smoke flows need.
"""
import pytest


@pytest.fixture
async def system_settings(test_db):
    """Minimal LibrarySystem + SystemSettings row.

    The circulation-policy resolver (loan period, fines) requires at least one
    system_settings row; the empty test DB has none, so any real checkout fails
    with "no system_settings row found". All policy columns default, so seeding
    the FK is enough.
    """
    from app.models.multi_branch import LibrarySystem, SystemSettings

    system = LibrarySystem(code="TEST", name="Test Library System")
    test_db.add(system)
    await test_db.commit()
    await test_db.refresh(system)

    settings = SystemSettings(library_system_id=system.id)
    test_db.add(settings)
    await test_db.commit()
    await test_db.refresh(settings)
    return settings


@pytest.fixture
async def patron_client(test_db, test_patron):
    """Async HTTP client authenticated as a patron."""
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return test_patron

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def admin_client(test_db, test_admin):
    """Async HTTP client authenticated as an admin."""
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return test_admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
