"""
Integration tests for book club mutation role gates.

Before the fix, POST /book-clubs/ only required an authenticated user, so any
PATRON could create a book club via direct API call. This pins the staff-only
gate in place and verifies the higher-privilege roles (super_admin, director)
are not accidentally excluded — a known L30 gotcha
(feedback_l30_staff_catalog_uncataloged_superadmin_blind_spot).
"""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


async def _make_user(test_db: AsyncSession, role: UserRole) -> User:
    """Create a user with the given role, unique email per role+test."""
    unique = uuid.uuid4().hex[:8]
    u = User(
        email=f"{role.value}-{unique}@bookclub-test.local",
        password_hash="x",
        first_name=role.value.title(),
        last_name="Tester",
        role=role,
        is_active=True,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u


@pytest.fixture
async def bc_payload():
    return {
        "name": f"Test Club {uuid.uuid4().hex[:6]}",
        "description": "Pytest-created",
        "max_members": 10,
        "is_public": True,
        "meeting_frequency": "monthly",
    }


@pytest.mark.integration
async def test_patron_cannot_create_book_club(client, test_db, bc_payload):
    from app.api.v1.auth import get_current_user
    from app.main import app

    patron = await _make_user(test_db, UserRole.PATRON)
    app.dependency_overrides[get_current_user] = lambda: patron
    try:
        resp = await client.post("/api/v1/book-clubs/", json=bc_payload)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 403, (
        f"PATRON should not be able to create a book club; got {resp.status_code} {resp.text}"
    )


@pytest.mark.integration
async def test_staff_can_create_book_club(client, test_db, bc_payload):
    from app.api.v1.auth import get_current_user
    from app.main import app

    staff = await _make_user(test_db, UserRole.STAFF)
    app.dependency_overrides[get_current_user] = lambda: staff
    try:
        resp = await client.post("/api/v1/book-clubs/", json=bc_payload)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 201, (
        f"STAFF should be able to create a book club; got {resp.status_code} {resp.text}"
    )


@pytest.mark.integration
async def test_super_admin_can_create_book_club(client, test_db, bc_payload):
    """Regression: higher-privilege roles must not be locked out (see
    feedback_l30_staff_catalog_uncataloged_superadmin_blind_spot)."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    sa = await _make_user(test_db, UserRole.SUPER_ADMIN)
    app.dependency_overrides[get_current_user] = lambda: sa
    try:
        resp = await client.post("/api/v1/book-clubs/", json=bc_payload)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 201, (
        f"SUPER_ADMIN should be able to create a book club; got {resp.status_code} {resp.text}"
    )


@pytest.mark.integration
async def test_director_can_create_book_club(client, test_db, bc_payload):
    """DIRECTOR is included in require_staff; verify no blind spot."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    director = await _make_user(test_db, UserRole.DIRECTOR)
    app.dependency_overrides[get_current_user] = lambda: director
    try:
        resp = await client.post("/api/v1/book-clubs/", json=bc_payload)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 201, (
        f"DIRECTOR should be able to create a book club; got {resp.status_code} {resp.text}"
    )
