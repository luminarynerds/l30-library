# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for the staff PII Access Log viewer endpoint.

Covers:
- Role gating (super_admin/director/legal allowed; staff/admin/patron 403).
- Date-range, user_id, patron_id filters.
- Pagination boundary (limit/offset).
- table-missing 503 path (mocked SQLAlchemy raise).
- Audit-log row is written for the viewer.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError

from app.api.v1.auth.helpers import get_current_user
from app.core.database import get_db
from app.core.pii_audit import PIIAccessLog
from app.core.security import hash_password
from app.main import app
from app.models.audit_log import AuditAction, AuditLog
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_user(
    db, *, email: str, role: UserRole, first: str = "First", last: str = "Last"
) -> User:
    u = User(
        email=email,
        password_hash=hash_password("TestPassword123!"),
        first_name=first,
        last_name=last,
        role=role,
        is_active=True,
        email_verified=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


async def _seed_log(
    db,
    *,
    user_id: int,
    user_role: str = "staff",
    endpoint: str = "/api/v1/staff/patrons/1",
    patron_ids: list[int] | None = None,
    timestamp: datetime | None = None,
    fields_accessed: list[str] | None = None,
) -> PIIAccessLog:
    row = PIIAccessLog(
        user_id=user_id,
        user_role=user_role,
        endpoint=endpoint,
        fields_accessed=fields_accessed or ["email", "first_name"],
        fields_redacted=[],
        patron_ids_accessed=patron_ids or [],
        ip_address="127.0.0.1",
        additional_context=None,
    )
    if timestamp is not None:
        row.timestamp = timestamp
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


def _client_as(db, current_user: User) -> AsyncClient:
    async def override_get_db():
        yield db

    async def override_get_current_user():
        return current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Role gating
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    "role,expected",
    [
        (UserRole.STAFF, 403),
        (UserRole.ADMIN, 403),
        (UserRole.PATRON, 403),
        (UserRole.SUPER_ADMIN, 200),
        (UserRole.DIRECTOR, 200),
        (UserRole.LEGAL, 200),
    ],
)
async def test_pii_access_log_role_gating(db, role, expected):
    user = await _seed_user(db, email=f"pii.gate.{role.value}@test.com", role=role)
    async with _client_as(db, user) as ac:
        try:
            resp = await ac.get("/api/v1/staff/pii-access-log")
            assert resp.status_code == expected, resp.text
        finally:
            _clear_overrides()


# ---------------------------------------------------------------------------
# Happy-path filters
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_pii_access_log_happy_path_lists_entries(db):
    admin = await _seed_user(
        db, email="pii.happy.admin@test.com", role=UserRole.SUPER_ADMIN, first="Sue", last="Admin"
    )
    actor = await _seed_user(
        db, email="pii.happy.actor@test.com", role=UserRole.STAFF, first="Alex", last="Staff"
    )
    await _seed_log(db, user_id=actor.id, user_role="staff", patron_ids=[42])
    await _seed_log(db, user_id=actor.id, user_role="staff", patron_ids=[42, 99])

    async with _client_as(db, admin) as ac:
        try:
            resp = await ac.get("/api/v1/staff/pii-access-log")
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["total"] >= 2
            assert len(body["entries"]) >= 2
            first = body["entries"][0]
            assert first["user_id"] == actor.id
            assert first["user_name"] == "Alex Staff"
            assert "fields_accessed" in first
            assert "timestamp" in first
        finally:
            _clear_overrides()


@pytest.mark.integration
async def test_pii_access_log_patron_id_filter(db):
    admin = await _seed_user(db, email="pii.patron.admin@test.com", role=UserRole.SUPER_ADMIN)
    actor = await _seed_user(db, email="pii.patron.actor@test.com", role=UserRole.STAFF)
    target = await _seed_log(db, user_id=actor.id, patron_ids=[7])
    other = await _seed_log(db, user_id=actor.id, patron_ids=[8])

    async with _client_as(db, admin) as ac:
        try:
            resp = await ac.get("/api/v1/staff/pii-access-log", params={"patron_id": 7})
            assert resp.status_code == 200, resp.text
            ids = {e["id"] for e in resp.json()["entries"]}
            assert target.id in ids
            assert other.id not in ids
        finally:
            _clear_overrides()


@pytest.mark.integration
async def test_pii_access_log_user_id_filter(db):
    admin = await _seed_user(db, email="pii.actor.admin@test.com", role=UserRole.SUPER_ADMIN)
    actor_a = await _seed_user(db, email="pii.actor.a@test.com", role=UserRole.STAFF)
    actor_b = await _seed_user(db, email="pii.actor.b@test.com", role=UserRole.STAFF)
    keep = await _seed_log(db, user_id=actor_a.id)
    drop = await _seed_log(db, user_id=actor_b.id)

    async with _client_as(db, admin) as ac:
        try:
            resp = await ac.get("/api/v1/staff/pii-access-log", params={"user_id": actor_a.id})
            assert resp.status_code == 200, resp.text
            ids = {e["id"] for e in resp.json()["entries"]}
            assert keep.id in ids
            assert drop.id not in ids
        finally:
            _clear_overrides()


@pytest.mark.integration
async def test_pii_access_log_date_range_filter(db):
    admin = await _seed_user(db, email="pii.date.admin@test.com", role=UserRole.SUPER_ADMIN)
    actor = await _seed_user(db, email="pii.date.actor@test.com", role=UserRole.STAFF)
    now = datetime.now(timezone.utc)
    inside = await _seed_log(db, user_id=actor.id, timestamp=now - timedelta(days=5))
    outside = await _seed_log(db, user_id=actor.id, timestamp=now - timedelta(days=200))

    async with _client_as(db, admin) as ac:
        try:
            # Default since=now-90d hides the 200d-old row.
            resp = await ac.get("/api/v1/staff/pii-access-log")
            assert resp.status_code == 200, resp.text
            ids = {e["id"] for e in resp.json()["entries"]}
            assert inside.id in ids
            assert outside.id not in ids

            # Explicit `since` reaches back further.
            resp = await ac.get(
                "/api/v1/staff/pii-access-log",
                params={"since": (now - timedelta(days=365)).isoformat()},
            )
            assert resp.status_code == 200, resp.text
            ids = {e["id"] for e in resp.json()["entries"]}
            assert outside.id in ids
        finally:
            _clear_overrides()


@pytest.mark.integration
async def test_pii_access_log_pagination_boundary(db):
    admin = await _seed_user(db, email="pii.page.admin@test.com", role=UserRole.SUPER_ADMIN)
    actor = await _seed_user(db, email="pii.page.actor@test.com", role=UserRole.STAFF)
    rows = []
    for i in range(3):
        rows.append(await _seed_log(db, user_id=actor.id, endpoint=f"/api/v1/staff/patrons/{i}"))

    async with _client_as(db, admin) as ac:
        try:
            resp = await ac.get("/api/v1/staff/pii-access-log", params={"limit": 2, "offset": 0})
            assert resp.status_code == 200, resp.text
            page1 = resp.json()
            assert len(page1["entries"]) == 2
            assert page1["limit"] == 2 and page1["offset"] == 0

            resp = await ac.get(
                "/api/v1/staff/pii-access-log",
                params={"limit": 2, "offset": 2, "user_id": actor.id},
            )
            assert resp.status_code == 200, resp.text
            page2 = resp.json()
            assert len(page2["entries"]) == 1
        finally:
            _clear_overrides()


# ---------------------------------------------------------------------------
# Audit-the-auditor
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_pii_access_log_writes_audit_row(db):
    admin = await _seed_user(db, email="pii.audit.admin@test.com", role=UserRole.SUPER_ADMIN)
    actor = await _seed_user(db, email="pii.audit.actor@test.com", role=UserRole.STAFF)
    await _seed_log(db, user_id=actor.id)

    async with _client_as(db, admin) as ac:
        try:
            resp = await ac.get("/api/v1/staff/pii-access-log", params={"limit": 5})
            assert resp.status_code == 200, resp.text
        finally:
            _clear_overrides()

    audit_rows = (
        (
            await db.execute(
                select(AuditLog).where(
                    AuditLog.admin_id == admin.id,
                    AuditLog.action == AuditAction.VIEWED,
                )
            )
        )
        .scalars()
        .all()
    )
    assert any((r.details or {}).get("resource") == "pii_access_log" for r in audit_rows)


# ---------------------------------------------------------------------------
# Table-missing 503 path
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_pii_access_log_table_missing_returns_503(db):
    admin = await _seed_user(db, email="pii.missing.admin@test.com", role=UserRole.SUPER_ADMIN)

    original_execute = db.execute

    async def raising_execute(stmt, *args, **kwargs):
        # Crude: any SELECT that references pii_access_log raises UndefinedTable.
        sql_text = str(getattr(stmt, "compile", lambda: stmt)())
        if "pii_access_log" in sql_text:
            raise ProgrammingError(
                "select 1", {}, Exception('relation "pii_access_log" does not exist')
            )
        return await original_execute(stmt, *args, **kwargs)

    with patch.object(db, "execute", side_effect=raising_execute):
        async with _client_as(db, admin) as ac:
            try:
                resp = await ac.get("/api/v1/staff/pii-access-log")
                assert resp.status_code == 503, resp.text
                # HTTPException responses are wrapped as {"error": {"message": ...}}
                # by app.core.exception_handlers.http_exception_handler, not the
                # FastAPI default {"detail": ...}.
                assert "alembic upgrade head" in resp.json()["error"]["message"]
            finally:
                _clear_overrides()
