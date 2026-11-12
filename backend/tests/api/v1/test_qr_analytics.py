# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for /api/v1/admin/qr-analytics.

Mocks `umami_get` in the router module so no live Umami HTTP traffic happens.
Verifies:
  - auth gate (anon -> 401, patron -> 403, staff -> 200)
  - the router pulls qr=<slug> out of Umami `type=query` rows and ignores
    rows without a qr key
  - slugs are grouped and ordered by pageviews desc
  - 503 when umami_website_id is not configured
  - /by-month runs N parallel windows and stitches a slug -> [counts] series
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.services.umami_client import UmamiUnavailable


@pytest.fixture
async def staff_user(test_db: AsyncSession) -> User:
    user = User(
        email="staff@qranalytics.test",
        password_hash=hash_password("StaffPassword123!"),
        first_name="QR",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def patron_user(test_db: AsyncSession) -> User:
    user = User(
        email="patron@qranalytics.test",
        password_hash=hash_password("PatronPassword123!"),
        first_name="QR",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def staff_client(test_db: AsyncSession, staff_user: User) -> AsyncClient:
    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return staff_user

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
async def patron_client(test_db: AsyncSession, patron_user: User) -> AsyncClient:
    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return patron_user

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
async def anon_client(test_db: AsyncSession) -> AsyncClient:
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)


# Representative Umami `type=query` payload mixing qr=<slug> rows with
# unrelated query strings the router must skip.
_FAKE_QUERY_ROWS = [
    {"x": "qr=tech-p-printer", "y": 42},
    {"x": "p=printer&qr=tech-p-printer", "y": 8},  # same slug, merge
    {"x": "qr=guide-password-reset", "y": 15},
    {"x": "qr=tech-launchpad", "y": 5},
    {"x": "q=Victorian+detective+fiction", "y": 11},  # unrelated -> ignore
    {"x": "", "y": 17},  # empty query string -> ignore
    {"x": "sort=title&sort_dir=asc", "y": 3},  # unrelated -> ignore
    {"x": "qr=", "y": 4},  # qr present but empty -> ignore
]


def _patch_umami(monkeypatch, *, rows=None, configured=True, raises=None):
    """Patch the router-bound umami_get and umami_website_id setting."""
    import app.api.v1.qr_analytics as mod

    async def fake_umami_get(path, params=None):
        if raises is not None:
            raise raises
        return list(rows or _FAKE_QUERY_ROWS)

    monkeypatch.setattr(mod, "umami_get", fake_umami_get)

    # Force a known website id (or clear it) on the cached settings object.
    settings = mod.get_settings()
    if configured:
        monkeypatch.setattr(settings, "umami_website_id", "test-website-id", raising=False)
    else:
        monkeypatch.setattr(settings, "umami_website_id", "", raising=False)


# ---------------------------------------------------------------------------
# Auth gate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_qr_analytics_requires_auth(anon_client: AsyncClient, monkeypatch):
    _patch_umami(monkeypatch)
    resp = await anon_client.get("/api/v1/admin/qr-analytics")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_qr_analytics_rejects_patron(patron_client: AsyncClient, monkeypatch):
    _patch_umami(monkeypatch)
    resp = await patron_client.get("/api/v1/admin/qr-analytics")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_by_month_requires_auth(anon_client: AsyncClient, monkeypatch):
    _patch_umami(monkeypatch)
    resp = await anon_client.get("/api/v1/admin/qr-analytics/by-month")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_by_month_rejects_patron(patron_client: AsyncClient, monkeypatch):
    _patch_umami(monkeypatch)
    resp = await patron_client.get("/api/v1/admin/qr-analytics/by-month")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extracts_and_sums_qr_slugs(staff_client: AsyncClient, monkeypatch):
    _patch_umami(monkeypatch)
    resp = await staff_client.get("/api/v1/admin/qr-analytics?days=30")
    assert resp.status_code == 200
    data = resp.json()

    # Only the 3 distinct qr slugs (printer rows merged).
    slugs = {row["slug"] for row in data}
    assert slugs == {"tech-p-printer", "guide-password-reset", "tech-launchpad"}

    by_slug = {row["slug"]: row["pageviews"] for row in data}
    assert by_slug["tech-p-printer"] == 50  # 42 + 8 merge
    assert by_slug["guide-password-reset"] == 15
    assert by_slug["tech-launchpad"] == 5


@pytest.mark.asyncio
async def test_orders_by_pageviews_desc(staff_client: AsyncClient, monkeypatch):
    _patch_umami(monkeypatch)
    resp = await staff_client.get("/api/v1/admin/qr-analytics")
    assert resp.status_code == 200
    counts = [row["pageviews"] for row in resp.json()]
    assert counts == sorted(counts, reverse=True)


@pytest.mark.asyncio
async def test_ignores_non_qr_rows(staff_client: AsyncClient, monkeypatch):
    """Catalog search queries and empty rows must not produce phantom slugs."""
    _patch_umami(monkeypatch)
    resp = await staff_client.get("/api/v1/admin/qr-analytics")
    assert resp.status_code == 200
    slugs = {row["slug"] for row in resp.json()}
    # No catalog-search noise, no '' slug from empty rows.
    assert "" not in slugs
    assert "q=Victorian+detective+fiction" not in slugs


@pytest.mark.asyncio
async def test_returns_503_when_umami_not_configured(
    staff_client: AsyncClient, monkeypatch
):
    _patch_umami(monkeypatch, configured=False)
    resp = await staff_client.get("/api/v1/admin/qr-analytics")
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_returns_503_when_umami_credentials_missing(
    staff_client: AsyncClient, monkeypatch
):
    _patch_umami(monkeypatch, raises=UmamiUnavailable("Umami credentials not configured"))
    resp = await staff_client.get("/api/v1/admin/qr-analytics")
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_returns_502_when_umami_unreachable(
    staff_client: AsyncClient, monkeypatch
):
    _patch_umami(monkeypatch, raises=UmamiUnavailable("Umami login transport error: boom"))
    resp = await staff_client.get("/api/v1/admin/qr-analytics")
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_returns_empty_list_when_no_qr_landings(
    staff_client: AsyncClient, monkeypatch
):
    _patch_umami(
        monkeypatch,
        rows=[
            {"x": "q=foo", "y": 3},
            {"x": "", "y": 9},
        ],
    )
    resp = await staff_client.get("/api/v1/admin/qr-analytics")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# By-month
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_by_month_runs_one_window_per_month(
    staff_client: AsyncClient, monkeypatch
):
    """Each month gets its own umami_get call; slugs roll up across months."""
    import app.api.v1.qr_analytics as mod

    call_windows: list[tuple[int, int]] = []

    async def fake_umami_get(path, params=None):
        call_windows.append((int(params["startAt"]), int(params["endAt"])))
        return [{"x": "qr=tech-launchpad", "y": 1}]

    monkeypatch.setattr(mod, "umami_get", fake_umami_get)
    settings = mod.get_settings()
    monkeypatch.setattr(settings, "umami_website_id", "test-website-id", raising=False)

    resp = await staff_client.get("/api/v1/admin/qr-analytics/by-month?months=4")
    assert resp.status_code == 200
    body = resp.json()

    assert len(call_windows) == 4
    assert len(body["months"]) == 4
    # Months are returned oldest -> newest.
    assert body["months"] == sorted(body["months"])
    # Single slug across all four windows.
    assert len(body["series"]) == 1
    assert body["series"][0]["slug"] == "tech-launchpad"
    assert body["series"][0]["counts"] == [1, 1, 1, 1]


@pytest.mark.asyncio
async def test_by_month_stitches_sparse_series(staff_client: AsyncClient, monkeypatch):
    """A slug present in only some windows must show 0 for the others."""
    import app.api.v1.qr_analytics as mod

    payloads = [
        [{"x": "qr=tech-launchpad", "y": 2}],  # oldest window
        [],
        [{"x": "qr=guide-password-reset", "y": 5}, {"x": "qr=tech-launchpad", "y": 3}],
    ]
    calls = {"i": 0}

    async def fake_umami_get(path, params=None):
        rows = payloads[calls["i"]]
        calls["i"] += 1
        return list(rows)

    monkeypatch.setattr(mod, "umami_get", fake_umami_get)
    settings = mod.get_settings()
    monkeypatch.setattr(settings, "umami_website_id", "test-website-id", raising=False)

    resp = await staff_client.get("/api/v1/admin/qr-analytics/by-month?months=3")
    assert resp.status_code == 200
    body = resp.json()

    by_slug = {s["slug"]: s["counts"] for s in body["series"]}
    assert by_slug["tech-launchpad"] == [2, 0, 3]
    assert by_slug["guide-password-reset"] == [0, 0, 5]
    # Ordering: tech-launchpad has grand total 5, guide has 5 -- tie broken
    # alphabetically (guide- < tech-).
    assert [s["slug"] for s in body["series"]] == ["guide-password-reset", "tech-launchpad"]


@pytest.mark.asyncio
async def test_by_month_returns_503_when_umami_not_configured(
    staff_client: AsyncClient, monkeypatch
):
    _patch_umami(monkeypatch, configured=False)
    resp = await staff_client.get("/api/v1/admin/qr-analytics/by-month")
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Unit-level coverage for the slug parser
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "query_string,expected",
    [
        ("qr=tech-p-printer", "tech-p-printer"),
        ("p=printer&qr=tech-p-printer", "tech-p-printer"),
        ("qr=guide-password-reset&utm_source=poster", "guide-password-reset"),
        ("q=foo", None),
        ("", None),
        ("qr=", None),
        ("qr=%20", None),
    ],
)
def test_extract_qr_slug(query_string, expected):
    from app.api.v1.qr_analytics import _extract_qr_slug

    assert _extract_qr_slug(query_string) == expected
