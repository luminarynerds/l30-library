# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression test: NULL columns must not 500 four list endpoints.

Four response schemas declared a field required (non-Optional) while the backing
DB column is nullable; rows that hold NULL made from_attributes hand pydantic an
explicit None and the GET endpoint 500'd with ResponseValidationError.

- ParentOnboardingSessionResponse.needs_identified / services_referred
  (nullable jsonb) -> coerced None -> [].
- ParentHomeVisitResponse.items_brought / services_discussed
  (nullable jsonb) -> coerced None -> [].
- MendingQueueEntryResponse.damaged_item_record_id (nullable FK) -> Optional[int].
- ClaimsReturnedDisputeResponse.lost_item_record_id (nullable FK) -> Optional[int].

Each test inserts a row via raw SQL with the target column(s) NULL and asserts the
GET endpoint returns 200 (and, for the Optional-FK cases, that the field is null
in the JSON). Raw SQL keeps the columns NULL instead of letting the ORM apply any
Python-side default.

parent-onboarding routes use Depends(require_authenticated) and the router carries
a Depends(require_parent_onboarding_enabled) feature guard at include time; both
are overridden. lost-damaged routes use Depends(require_staff).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.api.v1.dependencies import require_authenticated, require_staff
from app.api.v1.feature_guards import require_parent_onboarding_enabled
from app.core.database import get_db
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture
async def staff(db):
    user = User(
        email="nullfields-staff@example.com",
        first_name="Null",
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
async def patron(db):
    user = User(
        email="nullfields-patron@example.com",
        first_name="Null",
        last_name="Patron",
        password_hash="x",
        role=UserRole.PATRON,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _override_db(db):
    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    app.state.setup_complete = True


def _override_staff(staff_user, db):
    _override_db(db)

    async def _staff():
        return staff_user

    app.dependency_overrides[require_staff] = _staff


def _override_onboarding(user, db):
    _override_db(db)

    async def _authed():
        return user

    async def _flag():
        return None

    app.dependency_overrides[require_authenticated] = _authed
    app.dependency_overrides[require_parent_onboarding_enabled] = _flag


def _clear_overrides():
    for dep in (
        get_db,
        require_staff,
        require_authenticated,
        require_parent_onboarding_enabled,
    ):
        app.dependency_overrides.pop(dep, None)


# ============================================================================
# parent-onboarding sessions: needs_identified / services_referred NULL
# ============================================================================

@pytest.fixture
async def null_session(db, patron):
    sid = (await db.execute(
        text(
            "INSERT INTO parent_onboarding_sessions "
            "(patron_id, branch_id, status, scheduled_at, "
            " needs_identified, services_referred) "
            "VALUES (:p, 1, 'scheduled', now(), NULL, NULL) "
            "RETURNING id"
        ),
        {"p": patron.id},
    )).scalar_one()
    await db.commit()
    return sid


@pytest.mark.asyncio
async def test_list_sessions_serializes_null_jsonb(db, patron, null_session):
    from httpx import AsyncClient, ASGITransport

    _override_onboarding(patron, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            resp = await ac.get("/api/v1/parent-onboarding/sessions")
        assert resp.status_code == 200, resp.text
        row = next(r for r in resp.json()["sessions"] if r["id"] == null_session)
        assert row["needs_identified"] == []
        assert row["services_referred"] == []
    finally:
        _clear_overrides()


# ============================================================================
# parent-onboarding home-visits: items_brought / services_discussed NULL
# ============================================================================

@pytest.fixture
async def null_home_visit(db, patron):
    vid = (await db.execute(
        text(
            "INSERT INTO parent_home_visits "
            "(patron_id, purpose, status, scheduled_date, follow_up_needed, "
            " items_brought, services_discussed) "
            "VALUES (:p, 'intake', 'scheduled', '2026-01-15', false, NULL, NULL) "
            "RETURNING id"
        ),
        {"p": patron.id},
    )).scalar_one()
    await db.commit()
    return vid


@pytest.mark.asyncio
async def test_list_home_visits_serializes_null_jsonb(db, patron, null_home_visit):
    from httpx import AsyncClient, ASGITransport

    _override_onboarding(patron, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            resp = await ac.get("/api/v1/parent-onboarding/home-visits")
        assert resp.status_code == 200, resp.text
        row = next(r for r in resp.json()["visits"] if r["id"] == null_home_visit)
        assert row["items_brought"] == []
        assert row["services_discussed"] == []
    finally:
        _clear_overrides()


# ============================================================================
# lost-damaged mending-queue: damaged_item_record_id (nullable FK) NULL
# ============================================================================

@pytest.fixture
async def null_mending_entry(db):
    """is_completed=False so list_mending_queue (include_completed=False) keeps it."""
    mid = (await db.execute(
        text(
            "INSERT INTO mending_queue "
            "(damaged_item_record_id, priority, is_in_progress, is_completed) "
            "VALUES (NULL, 3, false, false) "
            "RETURNING id"
        )
    )).scalar_one()
    await db.commit()
    return mid


@pytest.mark.asyncio
async def test_list_mending_queue_tolerates_null_fk(db, staff, null_mending_entry):
    from httpx import AsyncClient, ASGITransport

    _override_staff(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            resp = await ac.get("/api/v1/staff/lost-damaged/mending-queue")
        assert resp.status_code == 200, resp.text
        row = next(r for r in resp.json()["items"] if r["id"] == null_mending_entry)
        assert row["damaged_item_record_id"] is None
    finally:
        _clear_overrides()


# ============================================================================
# lost-damaged claims-returned: lost_item_record_id (nullable FK) NULL
# ============================================================================

@pytest.fixture
async def null_claim(db):
    """patron_previous_claims_count is set non-null: that column is also nullable
    in the DB but the response declares it a required int (out of scope here), so
    leaving it NULL would 500 for an unrelated reason."""
    cid = (await db.execute(
        text(
            "INSERT INTO claims_returned_disputes "
            "(lost_item_record_id, status, patron_statement, "
            " patron_previous_claims_count) "
            "VALUES (NULL, 'pending', 'I returned this item last week.', 0) "
            "RETURNING id"
        )
    )).scalar_one()
    await db.commit()
    return cid


@pytest.mark.asyncio
async def test_list_claims_returned_tolerates_null_fk(db, staff, null_claim):
    from httpx import AsyncClient, ASGITransport

    _override_staff(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            resp = await ac.get("/api/v1/staff/lost-damaged/claims-returned")
        assert resp.status_code == 200, resp.text
        row = next(r for r in resp.json()["items"] if r["id"] == null_claim)
        assert row["lost_item_record_id"] is None
    finally:
        _clear_overrides()
