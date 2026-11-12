# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression coverage for the parent-onboarding session FE/BE reconciliation.

Prior to this fix, the frontend's edit and complete-session forms sent field
names (``notes``, ``location``, ``outcomes``, ``resources_provided``,
``referrals_made``, ``follow_up_date``) that don't exist on
``ParentOnboardingSession`` -- the real columns are ``family_situation_notes``,
``needs_identified``, ``services_referred``, ``welcome_packet_id``.

- PATCH used ``ParentOnboardingSessionUpdate`` (StrictInputSchema, extra=forbid)
  so the legacy field names 422'd outright.
- POST .../complete used a plain ``BaseModel`` (extra ignored silently), so
  the legacy field names were dropped without error -- and because the
  service applied ``model_dump()`` unconditionally (not exclude_unset), any
  *omitted* recognized field was reset to its schema default, wiping
  needs_identified/services_referred/family_situation_notes set by an
  earlier PATCH.

These tests drive the real endpoints end-to-end (create -> patch -> complete
-> get) and assert the round trip preserves data, plus lock in the two
regressions above so they can't silently return.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies import require_authenticated, require_staff
from app.api.v1.feature_guards import require_parent_onboarding_enabled
from app.core.database import get_db
from app.main import app
from app.models.user import User, UserRole

BASE = "/api/v1/parent-onboarding"


@pytest.fixture
async def staff(db):
    user = User(
        email="onboarding-roundtrip-staff@example.com",
        first_name="Round",
        last_name="Trip",
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
        email="onboarding-roundtrip-patron@example.com",
        first_name="Patron",
        last_name="RoundTrip",
        password_hash="x",
        role=UserRole.PATRON,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _override_staff(staff_user, db):
    async def _db():
        yield db

    async def _staff():
        return staff_user

    async def _flag():
        return None

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[require_staff] = _staff
    app.dependency_overrides[require_authenticated] = _staff
    app.dependency_overrides[require_parent_onboarding_enabled] = _flag
    app.state.setup_complete = True


def _clear_overrides():
    for dep in (
        get_db, require_staff, require_authenticated,
        require_parent_onboarding_enabled,
    ):
        app.dependency_overrides.pop(dep, None)


@pytest.mark.asyncio
async def test_session_edit_complete_get_roundtrip(db, staff, patron):
    """create -> PATCH (edit) -> POST /complete -> GET all reflect the same
    field names the frontend now sends, with nothing silently dropped."""
    _override_staff(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            create_resp = await ac.post(
                f"{BASE}/sessions",
                json={
                    "patron_id": patron.id,
                    "staff_id": staff.id,
                    "branch_id": 1,
                    "scheduled_at": "2026-08-01T10:00:00Z",
                },
            )
            assert create_resp.status_code == 201, create_resp.text
            session_id = create_resp.json()["id"]

            # Edit flow: this used to 422 because the FE sent notes/location.
            patch_resp = await ac.patch(
                f"{BASE}/sessions/{session_id}",
                json={
                    "family_situation_notes": "Family is settling in well.",
                    "status": "in_progress",
                },
            )
            assert patch_resp.status_code == 200, patch_resp.text
            assert patch_resp.json()["family_situation_notes"] == (
                "Family is settling in well."
            )
            assert patch_resp.json()["status"] == "in_progress"

            # Complete flow: this used to silently drop everything the FE
            # collected because the field names didn't match the schema.
            complete_resp = await ac.post(
                f"{BASE}/sessions/{session_id}/complete",
                json={
                    "family_situation_notes": "Session complete: WIC referral made.",
                    "needs_identified": [{"need": "childcare"}],
                    "services_referred": [{"service": "WIC"}],
                },
            )
            assert complete_resp.status_code == 200, complete_resp.text
            body = complete_resp.json()
            assert body["status"] == "completed"
            assert body["family_situation_notes"] == (
                "Session complete: WIC referral made."
            )
            assert body["needs_identified"] == [{"need": "childcare"}]
            assert body["services_referred"] == [{"service": "WIC"}]

            # GET reflects exactly what was persisted -- no silent drop.
            get_resp = await ac.get(f"{BASE}/sessions/{session_id}")
            assert get_resp.status_code == 200, get_resp.text
            get_body = get_resp.json()
            assert get_body["family_situation_notes"] == (
                "Session complete: WIC referral made."
            )
            assert get_body["needs_identified"] == [{"need": "childcare"}]
            assert get_body["services_referred"] == [{"service": "WIC"}]
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_complete_omitting_a_field_does_not_wipe_it(db, staff, patron):
    """A complete-session call that omits needs_identified must not reset it
    to [] -- exclude_unset must be honored end-to-end."""
    _override_staff(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            create_resp = await ac.post(
                f"{BASE}/sessions",
                json={
                    "patron_id": patron.id,
                    "branch_id": 1,
                    "scheduled_at": "2026-08-01T10:00:00Z",
                },
            )
            session_id = create_resp.json()["id"]

            patch_resp = await ac.patch(
                f"{BASE}/sessions/{session_id}",
                json={"needs_identified": [{"need": "housing"}]},
            )
            assert patch_resp.status_code == 200, patch_resp.text

            # Complete without mentioning needs_identified at all.
            complete_resp = await ac.post(
                f"{BASE}/sessions/{session_id}/complete",
                json={"family_situation_notes": "Wrapped up."},
            )
            assert complete_resp.status_code == 200, complete_resp.text
            assert complete_resp.json()["needs_identified"] == [
                {"need": "housing"},
            ]
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_legacy_frontend_field_names_are_rejected_not_dropped(db, staff, patron):
    """Regression guard for the original bug class: sending the old FE
    field names must 422 loudly (StrictInputSchema), never silently no-op."""
    _override_staff(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            create_resp = await ac.post(
                f"{BASE}/sessions",
                json={
                    "patron_id": patron.id,
                    "branch_id": 1,
                    "scheduled_at": "2026-08-01T10:00:00Z",
                },
            )
            session_id = create_resp.json()["id"]

            patch_resp = await ac.patch(
                f"{BASE}/sessions/{session_id}",
                json={"notes": "x", "location": "Branch Room A"},
            )
            assert patch_resp.status_code == 422

            complete_resp = await ac.post(
                f"{BASE}/sessions/{session_id}/complete",
                json={
                    "outcomes": "x",
                    "resources_provided": ["a"],
                    "referrals_made": ["b"],
                    "follow_up_date": "2026-08-08",
                },
            )
            assert complete_resp.status_code == 422
    finally:
        _clear_overrides()
