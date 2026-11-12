# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API tests for /api/v1/admin/reports/collection-velocity.

The endpoint reads a Postgres materialized view that does not exist
in the SQLite test database. To keep the suite Postgres-free we
override ``get_db`` with a fake session whose ``execute`` returns a
canned mapping result -- mirroring the shape the real MV produces.
The test validates request->SQL bucket selection and response shape,
not MV correctness (that's manual post-deploy).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.api.v1.dependencies import require_staff
from app.core.database import get_db
from app.main import app
from app.models.user import User, UserRole


def _fake_user() -> User:
    u = User()
    u.id = 1
    u.email = "staff@l.example"
    u.role = UserRole.STAFF
    return u


def _row(**kwargs) -> dict:
    base = {
        "catalog_item_id": 1,
        "title": "Test Title",
        "author": "Test Author",
        "isbn": "9780000000001",
        "checkouts_30d": 0,
        "checkouts_90d": 0,
        "checkouts_365d": 0,
        "days_since_last_checkout": 400.0,
        "holds_active": 0,
        "holds_per_copy": None,
        "total_copies": 3,
        "last_refreshed_at": datetime(2026, 5, 20, 3, 30, tzinfo=timezone.utc),
    }
    base.update(kwargs)
    return base


class _FakeResult:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return list(self._rows)


class _FakeSession:
    """Minimal async-session stand-in capturing executed SQL."""

    def __init__(self, rows_by_call: list[list[dict]]):
        self._rows = list(rows_by_call)
        self.last_sql: str = ""
        self.last_params: dict = {}

    async def execute(self, stmt, params=None):
        self.last_sql = str(stmt)
        self.last_params = params or {}
        rows = self._rows.pop(0) if self._rows else []
        return _FakeResult(rows)


@pytest.fixture
def override_deps():
    """Override get_db + require_staff for the endpoint test."""
    sessions: list[_FakeSession] = []

    def make_override(rows: list[dict]):
        session = _FakeSession([rows])
        sessions.append(session)

        async def _get_db():
            yield session

        app.dependency_overrides[get_db] = _get_db
        app.dependency_overrides[require_staff] = _fake_user
        return session

    yield make_override

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_staff, None)


@pytest.mark.asyncio
async def test_weed_bucket_returns_rows(client, override_deps):
    session = override_deps(
        [_row(catalog_item_id=10, title="Old Book", days_since_last_checkout=900.0)]
    )

    resp = await client.get(
        "/api/v1/admin/reports/collection-velocity",
        params={"bucket": "weed", "limit": 5},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["bucket"] == "weed"
    assert body["count"] == 1
    assert body["items"][0]["catalog_item_id"] == 10
    assert body["items"][0]["title"] == "Old Book"
    assert body["items"][0]["days_since_last_checkout"] == 900.0
    # SQL must include the weed-specific WHERE
    assert "checkouts_365d = 0" in session.last_sql
    assert "total_copies >= 2" in session.last_sql
    assert session.last_params == {"limit": 5}


@pytest.mark.asyncio
async def test_buy_more_bucket_returns_rows(client, override_deps):
    session = override_deps(
        [
            _row(
                catalog_item_id=20,
                title="Hot Title",
                holds_active=14,
                holds_per_copy=4.7,
                total_copies=3,
            )
        ]
    )

    resp = await client.get(
        "/api/v1/admin/reports/collection-velocity",
        params={"bucket": "buy_more"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["bucket"] == "buy_more"
    assert body["items"][0]["holds_active"] == 14
    assert body["items"][0]["holds_per_copy"] == 4.7
    assert "holds_per_copy >= 2" in session.last_sql
    assert "holds_active > 0" in session.last_sql


@pytest.mark.asyncio
async def test_cold_spend_bucket_returns_rows(client, override_deps):
    session = override_deps(
        [_row(catalog_item_id=30, title="Bad Buy", checkouts_365d=0)]
    )

    resp = await client.get(
        "/api/v1/admin/reports/collection-velocity",
        params={"bucket": "cold_spend"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["bucket"] == "cold_spend"
    assert body["items"][0]["catalog_item_id"] == 30
    assert "ci.created_at" in session.last_sql
    assert "checkouts_365d = 0" in session.last_sql


@pytest.mark.asyncio
async def test_unknown_bucket_422(client, override_deps):
    override_deps([])
    resp = await client.get(
        "/api/v1/admin/reports/collection-velocity",
        params={"bucket": "nonsense"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_empty_result_is_well_formed(client, override_deps):
    override_deps([])
    resp = await client.get(
        "/api/v1/admin/reports/collection-velocity",
        params={"bucket": "weed"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"bucket": "weed", "limit": 50, "count": 0, "items": []}
