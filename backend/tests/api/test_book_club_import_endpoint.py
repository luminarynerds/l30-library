# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for POST /book-clubs/{club_id}/members/import.

The ``require_book_clubs_enabled`` feature guard reads the singleton
``organization_features`` row. The shared ``l30_test`` database is known to
drift behind the model on unrelated feature-flag columns, which would make
*every* feature-gated endpoint test fail with an unrelated
``UndefinedColumnError`` (the same drift breaks the pre-existing
``test_book_club_role_gates.py`` on ``origin/main``). Since this suite is
about the *import* behaviour, not the org-features table, we override the
guard dependency with a no-op pass — the standard FastAPI
``dependency_overrides`` technique already used here for ``get_current_user``.
The 404-when-flag-off path is a thin shared helper covered elsewhere; the
role-gate (403) path is exercised directly below.
"""

import uuid

import pytest
from sqlalchemy import select

from app.models.book_club import BookClub, BookClubMember, BookClubMemberImport
from app.models.user import User, UserRole


async def _make_user(test_db, role=UserRole.PATRON, *, active: bool = True) -> User:
    u = User(
        email=f"{role.value}-{uuid.uuid4().hex[:8]}@import-endpoint.local",
        password_hash="x",
        first_name=role.value.title(),
        last_name="Test",
        role=role,
        is_active=active,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u


async def _make_club(test_db, creator: User) -> BookClub:
    c = BookClub(
        name=f"EndpointClub {uuid.uuid4().hex[:6]}",
        description="pytest",
        created_by_id=creator.id,
        is_public=True,
    )
    test_db.add(c)
    await test_db.commit()
    await test_db.refresh(c)
    return c


def _csv_bytes(rows: list[str], header: str = "email,patron_id,role") -> bytes:
    return ("\n".join([header] + rows) + "\n").encode("utf-8")


def _override_flag_on(app):
    """Override the book_clubs feature guard to a no-op (flag = on).

    Isolates the import endpoint tests from shared-test-DB org_features
    schema drift. Returns the guard callable so the caller can pop it.
    """
    from app.api.v1.feature_guards import require_book_clubs_enabled

    async def _noop() -> None:  # pragma: no cover - trivial
        return None

    app.dependency_overrides[require_book_clubs_enabled] = _noop
    return require_book_clubs_enabled


@pytest.mark.integration
async def test_import_staff_can_import_members(client, test_db):
    from app.api.v1.auth import get_current_user
    from app.main import app

    staff = await _make_user(test_db, role=UserRole.STAFF)
    alice = await _make_user(test_db)
    bob = await _make_user(test_db)
    club = await _make_club(test_db, staff)

    guard = _override_flag_on(app)
    app.dependency_overrides[get_current_user] = lambda: staff
    try:
        csv = _csv_bytes([
            f"{alice.email},,member",
            f"{bob.email},,facilitator",
        ])
        resp = await client.post(
            f"/api/v1/book-clubs/{club.id}/members/import",
            files={"file": ("import.csv", csv, "text/csv")},
            data={"default_role": "member", "dry_run": "false"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(guard, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_rows"] == 2
    assert body["success_count"] == 2
    assert body["import_id"] is not None
    assert body["dry_run"] is False

    res = await test_db.execute(
        select(BookClubMember).where(BookClubMember.book_club_id == club.id)
    )
    members = res.scalars().all()
    assert {m.user_id for m in members} == {alice.id, bob.id}


@pytest.mark.integration
async def test_import_dry_run_no_audit_row(client, test_db):
    from app.api.v1.auth import get_current_user
    from app.main import app

    staff = await _make_user(test_db, role=UserRole.STAFF)
    alice = await _make_user(test_db)
    club = await _make_club(test_db, staff)

    guard = _override_flag_on(app)
    app.dependency_overrides[get_current_user] = lambda: staff
    try:
        csv = _csv_bytes([f"{alice.email},,member"])
        resp = await client.post(
            f"/api/v1/book-clubs/{club.id}/members/import",
            files={"file": ("import.csv", csv, "text/csv")},
            data={"default_role": "member", "dry_run": "true"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(guard, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dry_run"] is True
    assert body["import_id"] is None
    assert body["success_count"] == 1

    res = await test_db.execute(
        select(BookClubMember).where(BookClubMember.book_club_id == club.id)
    )
    assert res.scalars().first() is None

    res = await test_db.execute(
        select(BookClubMemberImport).where(BookClubMemberImport.book_club_id == club.id)
    )
    assert res.scalars().first() is None


@pytest.mark.integration
async def test_import_unknown_club_returns_404(client, test_db):
    from app.api.v1.auth import get_current_user
    from app.main import app

    staff = await _make_user(test_db, role=UserRole.STAFF)
    guard = _override_flag_on(app)
    app.dependency_overrides[get_current_user] = lambda: staff
    try:
        csv = _csv_bytes(["x@x.x,,member"])
        resp = await client.post(
            "/api/v1/book-clubs/9999999/members/import",
            files={"file": ("x.csv", csv, "text/csv")},
            data={"default_role": "member"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(guard, None)

    assert resp.status_code == 404, resp.text


@pytest.mark.integration
async def test_import_patron_returns_403(client, test_db):
    from app.api.v1.auth import get_current_user
    from app.main import app

    staff = await _make_user(test_db, role=UserRole.STAFF)
    patron = await _make_user(test_db, role=UserRole.PATRON)
    club = await _make_club(test_db, staff)

    guard = _override_flag_on(app)
    app.dependency_overrides[get_current_user] = lambda: patron
    try:
        csv = _csv_bytes(["x@x.x,,member"])
        resp = await client.post(
            f"/api/v1/book-clubs/{club.id}/members/import",
            files={"file": ("x.csv", csv, "text/csv")},
            data={"default_role": "member"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(guard, None)

    assert resp.status_code == 403, resp.text


@pytest.mark.integration
async def test_import_exceeds_row_cap_returns_422(client, test_db):
    from app.api.v1.auth import get_current_user
    from app.main import app

    staff = await _make_user(test_db, role=UserRole.STAFF)
    club = await _make_club(test_db, staff)

    guard = _override_flag_on(app)
    app.dependency_overrides[get_current_user] = lambda: staff
    try:
        rows = [f"x{i}@x.x,,member" for i in range(501)]
        csv = _csv_bytes(rows)
        resp = await client.post(
            f"/api/v1/book-clubs/{club.id}/members/import",
            files={"file": ("x.csv", csv, "text/csv")},
            data={"default_role": "member"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(guard, None)

    assert resp.status_code == 422, resp.text
    # L30 wraps HTTPException as {error: {message}} (custom handler).
    assert "500" in resp.json()["error"]["message"]


@pytest.mark.integration
async def test_import_missing_columns_returns_422(client, test_db):
    from app.api.v1.auth import get_current_user
    from app.main import app

    staff = await _make_user(test_db, role=UserRole.STAFF)
    club = await _make_club(test_db, staff)

    guard = _override_flag_on(app)
    app.dependency_overrides[get_current_user] = lambda: staff
    try:
        csv = b"name,phone\nAlice,123\n"  # no email/patron_id
        resp = await client.post(
            f"/api/v1/book-clubs/{club.id}/members/import",
            files={"file": ("x.csv", csv, "text/csv")},
            data={"default_role": "member"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(guard, None)

    assert resp.status_code == 422, resp.text


@pytest.mark.integration
async def test_import_bom_tolerant(client, test_db):
    """CSV starting with a UTF-8 BOM must still parse."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    staff = await _make_user(test_db, role=UserRole.STAFF)
    alice = await _make_user(test_db)
    club = await _make_club(test_db, staff)

    guard = _override_flag_on(app)
    app.dependency_overrides[get_current_user] = lambda: staff
    try:
        csv = b"\xef\xbb\xbf" + _csv_bytes([f"{alice.email},,member"])
        resp = await client.post(
            f"/api/v1/book-clubs/{club.id}/members/import",
            files={"file": ("import.csv", csv, "text/csv")},
            data={"default_role": "member", "dry_run": "false"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(guard, None)

    assert resp.status_code == 200, resp.text
    assert resp.json()["success_count"] == 1


@pytest.mark.integration
async def test_import_header_only_returns_422(client, test_db):
    from app.api.v1.auth import get_current_user
    from app.main import app

    staff = await _make_user(test_db, role=UserRole.STAFF)
    club = await _make_club(test_db, staff)

    guard = _override_flag_on(app)
    app.dependency_overrides[get_current_user] = lambda: staff
    try:
        csv = b"email,patron_id,role\n"
        resp = await client.post(
            f"/api/v1/book-clubs/{club.id}/members/import",
            files={"file": ("x.csv", csv, "text/csv")},
            data={"default_role": "member"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(guard, None)

    assert resp.status_code == 422
