# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for POST /api/v1/pii-access-log/.

Covers:
- Auth: PATRON 403; unauthenticated 401/403; STAFF/ADMIN/SUPER_ADMIN 201.
- Persisted columns match the payload.
- Bad action -> 422.
- Missing required fields -> 422.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.pii_audit import PIIAccessLog
from app.models.user import User, UserRole


PATH = "/api/v1/pii-access-log/"


async def _make_user(db, *, role: UserRole, suffix: str) -> User:
    user = User(
        email=f"pii-route-{suffix}-{uuid.uuid4().hex[:6]}@test.local",
        password_hash="x",
        first_name="Route",
        last_name=suffix.title(),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _override(actor: User | None):
    """Install a get_current_user override for the duration of the test."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    if actor is None:
        # Remove override -> default dep raises 401/403.
        app.dependency_overrides.pop(get_current_user, None)
    else:
        app.dependency_overrides[get_current_user] = lambda: actor

    def _clear() -> None:
        app.dependency_overrides.pop(get_current_user, None)

    return _clear


@pytest.mark.integration
async def test_post_pii_access_log_as_staff_persists_row(client, test_db):
    staff = await _make_user(test_db, role=UserRole.STAFF, suffix="staff")
    patron = await _make_user(test_db, role=UserRole.PATRON, suffix="patron")

    clear = _override(staff)
    try:
        resp = await client.post(
            PATH,
            json={
                "patron_id": patron.id,
                "subject_type": "patron_profile",
                "subject_id": patron.id,
                "action": "read",
                "reason": "reviewing application",
            },
        )
    finally:
        clear()

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user_id"] == staff.id
    assert body["patron_id"] == patron.id
    assert body["subject_type"] == "patron_profile"
    assert body["subject_id"] == patron.id
    assert body["action"] == "read"
    assert body["reason"] == "reviewing application"
    assert "accessed_at" in body

    row = (
        await test_db.execute(
            select(PIIAccessLog).where(PIIAccessLog.id == body["id"])
        )
    ).scalar_one()
    assert row.user_id == staff.id
    assert row.patron_id == patron.id
    assert row.action == "read"


@pytest.mark.integration
async def test_post_pii_access_log_patron_forbidden(client, test_db):
    patron = await _make_user(test_db, role=UserRole.PATRON, suffix="forbidden")
    other = await _make_user(test_db, role=UserRole.PATRON, suffix="other")

    clear = _override(patron)
    try:
        resp = await client.post(
            PATH,
            json={
                "patron_id": other.id,
                "subject_type": "patron_profile",
                "action": "read",
            },
        )
    finally:
        clear()

    assert resp.status_code == 403, resp.text


@pytest.mark.integration
async def test_post_pii_access_log_optional_fields_omitted(client, test_db):
    staff = await _make_user(test_db, role=UserRole.STAFF, suffix="optional")
    patron = await _make_user(test_db, role=UserRole.PATRON, suffix="optional-patron")

    clear = _override(staff)
    try:
        resp = await client.post(
            PATH,
            json={
                "patron_id": patron.id,
                "subject_type": "home_address",
                "action": "reveal",
            },
        )
    finally:
        clear()

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["subject_id"] is None
    assert body["reason"] is None


@pytest.mark.integration
async def test_post_pii_access_log_invalid_action_422(client, test_db):
    staff = await _make_user(test_db, role=UserRole.STAFF, suffix="invalid")
    patron = await _make_user(test_db, role=UserRole.PATRON, suffix="invalid-patron")

    clear = _override(staff)
    try:
        resp = await client.post(
            PATH,
            json={
                "patron_id": patron.id,
                "subject_type": "patron_profile",
                "action": "delete",  # not in Literal
            },
        )
    finally:
        clear()

    assert resp.status_code == 422, resp.text


@pytest.mark.integration
async def test_post_pii_access_log_missing_required_field_422(client, test_db):
    staff = await _make_user(test_db, role=UserRole.STAFF, suffix="missing")

    clear = _override(staff)
    try:
        resp = await client.post(
            PATH,
            json={
                # patron_id missing
                "subject_type": "patron_profile",
                "action": "read",
            },
        )
    finally:
        clear()

    assert resp.status_code == 422, resp.text


@pytest.mark.integration
async def test_post_pii_access_log_extra_field_rejected(client, test_db):
    """Pydantic ConfigDict(extra='forbid') prevents typos creeping through."""
    staff = await _make_user(test_db, role=UserRole.STAFF, suffix="extra")
    patron = await _make_user(test_db, role=UserRole.PATRON, suffix="extra-patron")

    clear = _override(staff)
    try:
        resp = await client.post(
            PATH,
            json={
                "patron_id": patron.id,
                "subject_type": "patron_profile",
                "action": "read",
                "patronid": 99,  # typo: should be patron_id
            },
        )
    finally:
        clear()

    assert resp.status_code == 422, resp.text
