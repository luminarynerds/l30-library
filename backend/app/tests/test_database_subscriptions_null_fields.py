# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression test: database-subscription detail/list must serialize NULL rows.

Several DatabaseSubscription columns are nullable in the DB but declared with a
non-null default in DatabaseSubscriptionResponse (subjects, keywords, proxy_type,
requires_proxy, renewal_reminder_days, payment_frequency, patron_types_allowed,
branch_restrictions, category, auto_renew, is_featured, display_order). Older/seeded
rows hold NULL there; from_attributes handed pydantic an explicit None, which the
declared default does NOT cover, so GET /databases/subscriptions{,/{id}} 500'd with
ResponseValidationError on every such row. The response schema now coerces None to
each field's default. (No updated_at column on this model, so no greenlet path.)
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture
async def staff(db):
    user = User(
        email="dbsub-staff@example.com",
        first_name="DBSub",
        last_name="Staff",
        password_hash="x",
        role=UserRole.STAFF,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def null_subscription(db):
    """Insert a subscription with every coercible column NULL, end date in the
    past (so update_subscription_status flips status and commits). Raw SQL keeps
    the columns NULL instead of letting the ORM apply its Python-side defaults."""
    row = (await db.execute(
        text(
            "INSERT INTO database_subscriptions "
            "(name, access_url, subscription_start, subscription_end, is_active, status, "
            " category, subjects, keywords, proxy_type, requires_proxy, auto_renew, "
            " renewal_reminder_days, payment_frequency, patron_types_allowed, "
            " branch_restrictions, is_featured, display_order) "
            "VALUES (:n, :u, '2020-01-01', '2020-12-31', true, 'active', "
            " NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL) "
            "RETURNING id"
        ),
        {"n": "Legacy DB (all-null fields)", "u": "https://example.com/legacy-db"},
    )).scalar_one()
    await db.commit()
    return row


def _override_auth(staff_user, db):
    async def _db():
        yield db

    async def _staff():
        return staff_user

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _staff
    app.state.setup_complete = True


def _clear_overrides():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_subscriptions_serializes_null_fields(db, staff, null_subscription):
    """GET list returns 200 and coerces NULL columns to their schema defaults."""
    from httpx import AsyncClient, ASGITransport

    _override_auth(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            resp = await ac.get("/api/v1/databases/subscriptions?include_inactive=true")
        assert resp.status_code == 200, resp.text
        row = next(r for r in resp.json() if r["id"] == null_subscription)
        assert row["subjects"] == []
        assert row["keywords"] == []
        assert row["patron_types_allowed"] == []
        assert row["branch_restrictions"] == []
        assert row["proxy_type"] == "ezproxy"
        assert row["requires_proxy"] is True
        assert row["auto_renew"] is False
        assert row["renewal_reminder_days"] == 60
        assert row["payment_frequency"] == "annual"
        assert row["category"] == "general_reference"
        assert row["is_featured"] is False
        assert row["display_order"] == 0
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_get_subscription_serializes_null_fields(db, staff, null_subscription):
    """GET by id returns 200 for a row with NULL coercible columns."""
    from httpx import AsyncClient, ASGITransport

    _override_auth(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            resp = await ac.get(f"/api/v1/databases/subscriptions/{null_subscription}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == null_subscription
        assert body["subjects"] == []
        assert body["proxy_type"] == "ezproxy"
        assert body["renewal_reminder_days"] == 60
    finally:
        _clear_overrides()
