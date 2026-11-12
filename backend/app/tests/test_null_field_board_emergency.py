# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression test: board + emergency response schemas must serialize NULL rows.

Several response-schema fields are declared with a non-null default (or a plain
required type) while the backing DB column is nullable and holds NULL on seeded/
legacy rows. from_attributes hands pydantic the explicit None, which the declared
default does NOT cover, so the GET endpoints 500 with ResponseValidationError.
The response schemas now coerce None -> the field default at the boundary:

  - BoardVoteResponse.final_tally_{yes,no,abstain,recusal}  None -> 0
  - ActionItemResponse.board_update_provided                None -> False
  - SIP2DeviceResponse.sort_bin_mapping                     None -> {}
  - SystemSecurityCheckResponse.{door,camera}_status,
    alarm_status_details                                    None -> {}

These endpoints all require staff; get_current_user is overridden with a STAFF
user, which cascades through require_staff. Raw SQL keeps the target columns NULL
instead of letting the ORM apply its Python-side defaults.
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
        email="board-emerg-staff@example.com",
        first_name="BoardEmerg",
        last_name="Staff",
        password_hash="x",
        role=UserRole.STAFF,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


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


# ============ Board votes ============


@pytest.fixture
async def null_vote(db):
    """A board vote with every tally column NULL (legacy/seeded shape)."""
    vid = (await db.execute(
        text(
            "INSERT INTO board_votes "
            "(title, description, vote_type, opens_at, closes_at, status, quorum_required, "
            " final_tally_yes, final_tally_no, final_tally_abstain, final_tally_recusal) "
            "VALUES (:t, :d, 'simple_majority', '2020-01-01', '2020-02-01', 'closed', 4, "
            " NULL, NULL, NULL, NULL) "
            "RETURNING id"
        ),
        {"t": "Legacy vote (null tallies)", "d": "Seeded row with NULL tallies"},
    )).scalar_one()
    await db.commit()
    return vid


@pytest.mark.asyncio
async def test_list_votes_serializes_null_tallies(db, staff, null_vote):
    """GET /board/votes returns 200 and coerces NULL tally columns to 0."""
    from httpx import AsyncClient, ASGITransport

    _override_auth(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            resp = await ac.get("/api/v1/board/votes")
        assert resp.status_code == 200, resp.text
        row = next(r for r in resp.json() if r["id"] == null_vote)
        assert row["final_tally_yes"] == 0
        assert row["final_tally_no"] == 0
        assert row["final_tally_abstain"] == 0
        assert row["final_tally_recusal"] == 0
        # created_by_id is a nullable audit FK now typed Optional, NULL is fine.
        assert row["created_by_id"] is None
    finally:
        _clear_overrides()


# ============ Board action items ============


@pytest.fixture
async def null_action_item(db):
    """An action item with board_update_provided NULL. Needs a parent meeting
    (meeting_id is NOT NULL FK)."""
    mid = (await db.execute(
        text(
            "INSERT INTO board_meetings (meeting_type, title, scheduled_date) "
            "VALUES ('regular', 'Test Meeting', '2020-01-01') RETURNING id"
        )
    )).scalar_one()
    aid = (await db.execute(
        text(
            "INSERT INTO meeting_action_items "
            "(meeting_id, title, status, priority, progress_percentage, "
            " requires_board_update, board_update_provided) "
            "VALUES (:m, 'Legacy action item', 'not_started', 'medium', 0, false, NULL) "
            "RETURNING id"
        ),
        {"m": mid},
    )).scalar_one()
    await db.commit()
    return aid


@pytest.mark.asyncio
async def test_list_action_items_serializes_null_bool(db, staff, null_action_item):
    """GET /board/action-items returns 200 and coerces NULL board_update_provided
    to False."""
    from httpx import AsyncClient, ASGITransport

    _override_auth(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            resp = await ac.get("/api/v1/board/action-items")
        assert resp.status_code == 200, resp.text
        row = next(r for r in resp.json() if r["id"] == null_action_item)
        assert row["board_update_provided"] is False
    finally:
        _clear_overrides()


# ============ SIP2 devices ============


@pytest.fixture
async def null_sip2_device(db):
    """A SIP2 device with sort_bin_mapping NULL. Required NOT-NULL columns are
    supplied as real values; only sort_bin_mapping is NULL."""
    did = (await db.execute(
        text(
            "INSERT INTO sip2_devices "
            "(name, device_id, host, port, institution_id, status, "
            " timeout_seconds, retry_attempts, supports_checkin, supports_checkout, "
            " supports_sorting, sort_bin_mapping) "
            "VALUES ('Legacy SIP2', 'dev-legacy-1', '127.0.0.1', 6001, 'inst-1', "
            " 'online', 30, 3, true, true, false, NULL) "
            "RETURNING id"
        )
    )).scalar_one()
    await db.commit()
    return did


@pytest.mark.asyncio
async def test_list_sip2_devices_serializes_null_sort_bin(db, staff, null_sip2_device):
    """GET /book-drop/sip2-devices returns 200 and coerces NULL sort_bin_mapping
    to {}."""
    from httpx import AsyncClient, ASGITransport

    _override_auth(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            resp = await ac.get("/api/v1/book-drop/sip2-devices")
        assert resp.status_code == 200, resp.text
        row = next(r for r in resp.json() if r["id"] == null_sip2_device)
        assert row["sort_bin_mapping"] == {}
    finally:
        _clear_overrides()


# ============ Security check ============


@pytest.fixture
async def null_security_check(db):
    """A security check with the three JSON status columns NULL. The bool columns
    are also nullable-but-required in the schema (a separate latent bug, out of
    scope), so supply them as real values here."""
    cid = (await db.execute(
        text(
            "INSERT INTO system_security_checks "
            "(all_doors_locked, cameras_operational, alarm_armed, alarm_triggered, "
            " remote_access_available, door_status, camera_status, alarm_status_details) "
            "VALUES (true, true, true, false, false, NULL, NULL, NULL) "
            "RETURNING id"
        )
    )).scalar_one()
    await db.commit()
    return cid


@pytest.mark.asyncio
async def test_latest_security_check_serializes_null_dicts(db, staff, null_security_check):
    """GET /emergency/security-check/latest returns 200 and coerces the NULL JSON
    status columns to {}."""
    from httpx import AsyncClient, ASGITransport

    _override_auth(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            resp = await ac.get("/api/v1/emergency/security-check/latest")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Optional response_model returns null on no-match; guard before indexing.
        assert body is not None, "expected the inserted security check to be returned"
        assert body["id"] == null_security_check
        assert body["door_status"] == {}
        assert body["camera_status"] == {}
        assert body["alarm_status_details"] == {}
    finally:
        _clear_overrides()


# ============ Building status (Optional fix, no row needed) ============


@pytest.mark.asyncio
async def test_building_status_serializes_no_log(db, staff):
    """GET /emergency/building-status returns 200 with status_changed_at=None when
    no status log exists (the handler passes None; the field is now Optional)."""
    from httpx import AsyncClient, ASGITransport

    # Ensure no building_status_logs rows so the handler hits its None branch.
    await db.execute(text("DELETE FROM building_status_logs"))
    await db.commit()

    _override_auth(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            resp = await ac.get("/api/v1/emergency/building-status")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status_changed_at"] is None
    finally:
        _clear_overrides()
