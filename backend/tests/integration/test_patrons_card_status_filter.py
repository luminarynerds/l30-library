# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the cardStatus filter on /staff/patrons and /staff/search/unified.

Two layers:

1. Pure-function unit tests for _card_status_clause and _card_status_today_bounds
   (no DB, no app) - anchor the math even if integration infrastructure is wedged.

2. Integration tests using the `admin_client` fixture from conftest.py (which
   overrides get_current_user, bypassing the JWT/Redis path that the local
   integration env can't reach). Covers the 5 CardStatusFilter values, day
   boundaries, NULL handling, the statistics expiring_cards_counts aggregation,
   and parity between list endpoint and unified-search code path.

All comparisons are UTC; card_expires_at is a tz-aware DateTime column.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.api.v1.staff.patron_operations import (
    _card_status_clause,
    _card_status_today_bounds,
)
from app.api.v1.staff.patrons_schemas import CardStatusFilter
from app.core.security import hash_password
from app.models.user import User, UserRole


# ============================================================================
# Pure-function tests - run independently of DB / app fixtures
# ============================================================================

async def test_card_status_today_bounds_uses_utc_date():
    fixed = datetime(2026, 5, 17, 14, 30, 0, tzinfo=timezone.utc)
    today_start, plus_30d_end, plus_90d_end = _card_status_today_bounds(fixed)
    assert today_start == datetime(2026, 5, 17, 0, 0, 0, tzinfo=timezone.utc)
    assert plus_30d_end == datetime(2026, 6, 16, 23, 59, 59, 999999, tzinfo=timezone.utc)
    assert plus_90d_end == datetime(2026, 8, 15, 23, 59, 59, 999999, tzinfo=timezone.utc)


async def test_card_status_clause_any_returns_none():
    assert _card_status_clause(CardStatusFilter.any) is None


async def test_card_status_clause_other_values_return_clause():
    for value in (
        CardStatusFilter.active,
        CardStatusFilter.expiring_30d,
        CardStatusFilter.expiring_90d,
        CardStatusFilter.expired,
    ):
        clause = _card_status_clause(value)
        assert clause is not None, f"{value} should produce a clause"


# ============================================================================
# Integration tests
# ============================================================================


def _utc_today_start() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc)


async def _seed_patron(db, *, email: str, first: str, last: str, expires_at) -> User:
    patron = User(
        email=email,
        password_hash=hash_password("PatronPassword123!"),
        first_name=first,
        last_name=last,
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        card_expires_at=expires_at,
    )
    db.add(patron)
    await db.commit()
    await db.refresh(patron)
    return patron


@pytest.fixture
async def admin_client(db):
    """Async HTTP client authenticated as an ADMIN user.

    Required because /staff/patrons list applies a PII filter that masks `email`
    for STAFF role, which then fails response_model validation (a pre-existing
    coupling). Using ADMIN gives the full PII view.
    """
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user
    from app.core.security import hash_password
    from app.main import app

    admin = User(
        email="cardstatus.admin@test.com",
        password_hash=hash_password("AdminPassword123!"),
        first_name="Card",
        last_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)

    async def override_get_db():
        yield db

    async def override_get_current_user():
        return admin

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
async def patrons_with_card_states(db):
    """Seed one patron per card-state band plus boundary cases."""
    today_start = _utc_today_start()
    return {
        # Boundary: expires today at 00:00:01 -> in expiring_30d window
        "expires_today": await _seed_patron(
            db,
            email="exp.today@test.com",
            first="Today",
            last="Exp",
            expires_at=today_start + timedelta(seconds=1),
        ),
        # Standard 15d future -> in 30d and 90d windows
        "expires_in_15d": await _seed_patron(
            db,
            email="exp.15d@test.com",
            first="Fifteen",
            last="Exp",
            expires_at=today_start + timedelta(days=15),
        ),
        # 60d future -> in 90d only
        "expires_in_60d": await _seed_patron(
            db,
            email="exp.60d@test.com",
            first="Sixty",
            last="Exp",
            expires_at=today_start + timedelta(days=60),
        ),
        # Far future -> active only
        "expires_in_200d": await _seed_patron(
            db,
            email="exp.200d@test.com",
            first="FarFuture",
            last="Exp",
            expires_at=today_start + timedelta(days=200),
        ),
        # Yesterday at 23:59:59 -> expired
        "expired_yesterday": await _seed_patron(
            db,
            email="exp.yest@test.com",
            first="Yesterday",
            last="Exp",
            expires_at=today_start - timedelta(seconds=1),
        ),
        # No expiry -> active (NULL treated as no expiry per spec)
        "null_expiry": await _seed_patron(
            db,
            email="exp.null@test.com",
            first="Null",
            last="Exp",
            expires_at=None,
        ),
    }


async def _list_patron_ids(admin_client, *, card_status: str) -> set[int]:
    resp = await admin_client.get(
        "/api/v1/staff/patrons",
        params={"cardStatus": card_status, "limit": 200},
    )
    assert resp.status_code == 200, resp.text
    return {p["id"] for p in resp.json()["patrons"]}


async def _unified_search_patron_ids(admin_client, *, query: str, card_status: str) -> set[str]:
    resp = await admin_client.get(
        "/api/v1/staff/search/unified",
        params={"q": query, "cardStatus": card_status, "per_page": 100},
    )
    assert resp.status_code == 200, resp.text
    return {
        r["id"]  # e.g. "patron:42"
        for r in resp.json()["results"]
        if r["entity_type"] == "patron"
    }


@pytest.mark.asyncio
async def test_card_status_filter_each_band(admin_client, patrons_with_card_states):
    # Match by id since the admin_client fixture uses a STAFF user and the PII
    # filter masks the email field for that role.
    p = patrons_with_card_states

    any_ids = await _list_patron_ids(admin_client, card_status="any")
    for patron in p.values():
        assert patron.id in any_ids

    e30 = await _list_patron_ids(admin_client, card_status="expiring_30d")
    assert p["expires_today"].id in e30
    assert p["expires_in_15d"].id in e30
    assert p["expires_in_60d"].id not in e30
    assert p["expires_in_200d"].id not in e30
    assert p["expired_yesterday"].id not in e30
    assert p["null_expiry"].id not in e30

    e90 = await _list_patron_ids(admin_client, card_status="expiring_90d")
    assert p["expires_today"].id in e90
    assert p["expires_in_15d"].id in e90
    assert p["expires_in_60d"].id in e90
    assert p["expires_in_200d"].id not in e90
    assert p["expired_yesterday"].id not in e90
    assert p["null_expiry"].id not in e90

    expired = await _list_patron_ids(admin_client, card_status="expired")
    assert p["expired_yesterday"].id in expired
    assert p["expires_today"].id not in expired
    assert p["expires_in_15d"].id not in expired
    assert p["null_expiry"].id not in expired

    active = await _list_patron_ids(admin_client, card_status="active")
    assert p["expires_today"].id in active
    assert p["expires_in_15d"].id in active
    assert p["expires_in_60d"].id in active
    assert p["expires_in_200d"].id in active
    assert p["null_expiry"].id in active
    assert p["expired_yesterday"].id not in active


@pytest.mark.asyncio
async def test_card_status_unknown_value_rejected(admin_client):
    resp = await admin_client.get(
        "/api/v1/staff/patrons",
        params={"cardStatus": "not_a_valid_value"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_card_status_default_is_any(admin_client, patrons_with_card_states):
    """Omitting cardStatus must behave like cardStatus=any."""
    resp_default = await admin_client.get(
        "/api/v1/staff/patrons",
        params={"limit": 200},
    )
    assert resp_default.status_code == 200
    default_ids = {p["id"] for p in resp_default.json()["patrons"]}

    any_ids = await _list_patron_ids(admin_client, card_status="any")
    assert default_ids == any_ids


@pytest.mark.asyncio
async def test_card_status_list_and_unified_return_same_patrons(admin_client, patrons_with_card_states):
    """Unified-search and list endpoint must serve the same filter for the same patron set."""
    seeded = patrons_with_card_states
    seeded_int_ids = {p.id for p in seeded.values()}
    seeded_unified_ids = {f"patron:{p.id}" for p in seeded.values()}

    for status in ("expiring_30d", "expiring_90d", "expired", "active"):
        list_ids = await _list_patron_ids(admin_client, card_status=status)
        list_seeded_ids = list_ids & seeded_int_ids
        list_seeded_unified_ids = {f"patron:{i}" for i in list_seeded_ids}

        unified_ids = await _unified_search_patron_ids(
            admin_client, query="Exp", card_status=status
        )
        unified_seeded_ids = unified_ids & seeded_unified_ids

        assert unified_seeded_ids == list_seeded_unified_ids, (
            f"card_status={status}: list={list_seeded_unified_ids} vs unified={unified_seeded_ids}"
        )


@pytest.mark.asyncio
async def test_statistics_expiring_cards_counts(admin_client, patrons_with_card_states):
    resp = await admin_client.get("/api/v1/staff/patrons/statistics")
    assert resp.status_code == 200, resp.text
    payload = resp.json()

    assert "expiring_cards_counts" in payload, f"keys present: {sorted(payload.keys())}"
    counts = payload["expiring_cards_counts"]

    # Bands are nested: 30d count <= 90d count.
    assert counts["expiring_within_30d"] >= 2  # today + 15d
    assert counts["expiring_within_90d"] >= 3  # today + 15d + 60d
    assert counts["expiring_within_30d"] <= counts["expiring_within_90d"]
    assert counts["expired"] >= 1  # yesterday


@pytest.mark.asyncio
async def test_card_status_combines_with_search(admin_client, patrons_with_card_states):
    """cardStatus must compose with the existing text search, not replace it."""
    resp = await admin_client.get(
        "/api/v1/staff/patrons",
        params={"cardStatus": "expiring_30d", "search": "Fifteen", "limit": 50},
    )
    assert resp.status_code == 200, resp.text
    ids = {p["id"] for p in resp.json()["patrons"]}
    assert patrons_with_card_states["expires_in_15d"].id in ids
    # "Today" patron is in the 30d band but does not match "Fifteen" search.
    assert patrons_with_card_states["expires_today"].id not in ids
