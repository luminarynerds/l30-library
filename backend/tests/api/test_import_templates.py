# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for GET /api/v1/import-templates/{type} endpoint."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.models.user import User, UserRole

pytestmark = pytest.mark.asyncio


def _make_staff_user():
    return User(
        email="staff@test.local",
        password_hash="x",
        first_name="Staff",
        last_name="Test",
        role=UserRole.STAFF,
        is_active=True,
    )


def _make_patron_user():
    return User(
        email="patron@test.local",
        password_hash="x",
        first_name="Patron",
        last_name="Test",
        role=UserRole.PATRON,
        is_active=True,
    )


async def _get(app, path, user=None):
    from app.api.v1.auth.helpers import get_current_user

    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            return await ac.get(path)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def test_patron_template_downloads():
    from app.main import app

    r = await _get(app, "/api/v1/import-templates/patron", _make_staff_user())
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "patron_import_template.csv" in r.headers.get("content-disposition", "")
    first_header = r.text.split("\n")[0]
    assert "name" in first_header
    assert "email" in first_header


async def test_catalog_template_downloads():
    from app.main import app

    r = await _get(app, "/api/v1/import-templates/catalog", _make_staff_user())
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    first_header = r.text.split("\n")[0]
    assert "title" in first_header
    assert "isbn" in first_header


async def test_holdings_template_downloads():
    from app.main import app

    r = await _get(app, "/api/v1/import-templates/holdings", _make_staff_user())
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")


async def test_circulation_template_downloads():
    from app.main import app

    r = await _get(app, "/api/v1/import-templates/circulation", _make_staff_user())
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")


async def test_unknown_template_returns_422_or_404():
    from app.main import app

    r = await _get(app, "/api/v1/import-templates/fakeformat", _make_staff_user())
    assert r.status_code in (404, 422)


async def test_unauthenticated_request_is_rejected():
    from app.main import app

    r = await _get(app, "/api/v1/import-templates/patron", user=None)
    assert r.status_code in (401, 403)
