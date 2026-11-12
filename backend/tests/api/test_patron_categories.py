# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for /api/v1/admin/patron-categories CRUD."""

import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.patron_category import PatronCategory

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def admin_client(client, test_admin):
    """Async test client with get_current_user resolved to an admin."""
    app.dependency_overrides[get_current_user] = lambda: test_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


async def _seed_category(test_db, *, code: str, label: str, is_active: bool = True):
    cat = PatronCategory(code=code, label=label, is_active=is_active)
    test_db.add(cat)
    await test_db.commit()
    await test_db.refresh(cat)
    return cat


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


async def test_list_returns_active_categories(admin_client, test_db):
    """Seeded active categories appear in list; inactive ones are hidden."""
    await _seed_category(test_db, code="ADULT", label="Adult")
    await _seed_category(test_db, code="JUVENILE", label="Juvenile")
    await _seed_category(test_db, code="ARCHIVED", label="Archived", is_active=False)

    r = await admin_client.get("/api/v1/admin/patron-categories")
    assert r.status_code == 200
    codes = {c["code"] for c in r.json()}
    assert "ADULT" in codes
    assert "JUVENILE" in codes
    assert "ARCHIVED" not in codes


async def test_list_include_inactive(admin_client, test_db):
    """include_inactive=true returns all categories including inactive."""
    await _seed_category(test_db, code="ACTIVE1", label="Active One")
    await _seed_category(test_db, code="INACTIVE1", label="Inactive One", is_active=False)

    r = await admin_client.get("/api/v1/admin/patron-categories?include_inactive=true")
    assert r.status_code == 200
    codes = {c["code"] for c in r.json()}
    assert "ACTIVE1" in codes
    assert "INACTIVE1" in codes


async def test_create_uppercases_code(admin_client, test_db):
    """POST with lowercase code stores and returns uppercased code."""
    r = await admin_client.post(
        "/api/v1/admin/patron-categories",
        json={"code": "homeschool", "label": "Homeschool Family"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["code"] == "HOMESCHOOL"
    assert r.json()["label"] == "Homeschool Family"
    assert r.json()["is_active"] is True


async def test_create_duplicate_code_returns_409(admin_client, test_db):
    """Duplicate code returns 409 Conflict."""
    await _seed_category(test_db, code="ADULT", label="Adult")

    r = await admin_client.post(
        "/api/v1/admin/patron-categories",
        json={"code": "adult", "label": "Adult Duplicate"},
    )
    assert r.status_code == 409


async def test_get_by_id(admin_client, test_db):
    """GET /{id} returns the correct category."""
    cat = await _seed_category(test_db, code="SENIOR", label="Senior")

    r = await admin_client.get(f"/api/v1/admin/patron-categories/{cat.id}")
    assert r.status_code == 200
    assert r.json()["code"] == "SENIOR"


async def test_get_nonexistent_returns_404(admin_client, test_db):
    r = await admin_client.get("/api/v1/admin/patron-categories/99999")
    assert r.status_code == 404


async def test_update_label(admin_client, test_db):
    """PUT updates label and returns updated record."""
    cat = await _seed_category(test_db, code="STUDENT", label="Student")

    r = await admin_client.put(
        f"/api/v1/admin/patron-categories/{cat.id}",
        json={"label": "Student (K-12)"},
    )
    assert r.status_code == 200
    assert r.json()["label"] == "Student (K-12)"
    assert r.json()["code"] == "STUDENT"


async def test_delete_soft_deletes_via_is_active(admin_client, test_db):
    """DELETE sets is_active=False, does not remove the row."""
    cat = await _seed_category(test_db, code="TEMP", label="Temporary")

    d = await admin_client.delete(f"/api/v1/admin/patron-categories/{cat.id}")
    assert d.status_code == 204

    await test_db.refresh(cat)
    assert cat.is_active is False


async def test_unauthenticated_request_rejected():
    """Requests without auth are rejected with 401 or 403."""
    from httpx import AsyncClient, ASGITransport

    app.state.setup_complete = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/admin/patron-categories")
    assert r.status_code in (401, 403)
