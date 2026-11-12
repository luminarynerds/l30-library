# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Confidentiality gate for GET /api/v1/parent-onboarding/connection-groups/{id}/members.

Before this fix, the `/members` route required only `require_staff`, which
meant any staff role (interns, front-desk) could read the full roster
(patron PII) of a confidential group. The serializer privacy work
(`_serialize_group`) covered the list/detail endpoints but not the members
drawer route, so confidential rosters leaked to general staff.

Gate logic is now the same as the approval helper `_caller_can_approve`:
admin/director/super_admin OR the group facilitator. Any staff still sees
non-confidential rosters.
"""

import uuid

import pytest

from app.models.parent_onboarding import (
    ConnectionGroupType,
    MeetingFrequency,
    ParentConnectionGroup,
)
from app.models.user import User, UserRole


async def _make_user(test_db, role: UserRole) -> User:
    unique = uuid.uuid4().hex[:8]
    u = User(
        email=f"{role.value}-{unique}@cg-members-test.local",
        password_hash="x",
        first_name=role.value.title(),
        last_name="Tester",
        role=role,
        is_active=True,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u


async def _make_group(test_db, *, confidential: bool, facilitator_id: int | None) -> ParentConnectionGroup:
    g = ParentConnectionGroup(
        name=f"Test Group {uuid.uuid4().hex[:6]}",
        description="pytest",
        branch_id=1,
        group_type=ConnectionGroupType.general,
        max_members=12,
        meeting_frequency=MeetingFrequency.weekly,
        languages=["en"],
        is_active=True,
        confidential=confidential,
        facilitator_id=facilitator_id,
    )
    test_db.add(g)
    await test_db.commit()
    await test_db.refresh(g)
    return g


@pytest.mark.integration
async def test_non_facilitator_staff_403_on_confidential(client, test_db):
    """General staff (not facilitator, not admin) must NOT see a confidential roster."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    facilitator = await _make_user(test_db, UserRole.STAFF)
    other_staff = await _make_user(test_db, UserRole.STAFF)
    group = await _make_group(test_db, confidential=True, facilitator_id=facilitator.id)

    app.dependency_overrides[get_current_user] = lambda: other_staff
    try:
        resp = await client.get(
            f"/api/v1/parent-onboarding/connection-groups/{group.id}/members"
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 403, (
        f"non-facilitator staff should be blocked from confidential roster; "
        f"got {resp.status_code} {resp.text}"
    )
    # App wraps HTTPException.detail in {"error": {"message": ...}}; check the
    # specific message so we don't pass on an unrelated 403 (e.g. require_staff).
    body = resp.json()
    message = body.get("error", {}).get("message", "") or body.get("detail", "")
    assert "confidential" in message.lower(), body


@pytest.mark.integration
async def test_facilitator_200_on_confidential(client, test_db):
    """The group's facilitator must see the confidential roster."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    facilitator = await _make_user(test_db, UserRole.STAFF)
    group = await _make_group(test_db, confidential=True, facilitator_id=facilitator.id)

    app.dependency_overrides[get_current_user] = lambda: facilitator
    try:
        resp = await client.get(
            f"/api/v1/parent-onboarding/connection-groups/{group.id}/members"
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200, (
        f"facilitator should see confidential roster; got {resp.status_code} {resp.text}"
    )


@pytest.mark.integration
async def test_admin_200_on_confidential(client, test_db):
    """Admin must see the confidential roster even when not the facilitator."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    facilitator = await _make_user(test_db, UserRole.STAFF)
    admin = await _make_user(test_db, UserRole.ADMIN)
    group = await _make_group(test_db, confidential=True, facilitator_id=facilitator.id)

    app.dependency_overrides[get_current_user] = lambda: admin
    try:
        resp = await client.get(
            f"/api/v1/parent-onboarding/connection-groups/{group.id}/members"
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200, (
        f"admin should see confidential roster; got {resp.status_code} {resp.text}"
    )


@pytest.mark.integration
async def test_any_staff_200_on_non_confidential(client, test_db):
    """Any staff role still sees the roster on a non-confidential group."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    facilitator = await _make_user(test_db, UserRole.STAFF)
    other_staff = await _make_user(test_db, UserRole.STAFF)
    group = await _make_group(test_db, confidential=False, facilitator_id=facilitator.id)

    app.dependency_overrides[get_current_user] = lambda: other_staff
    try:
        resp = await client.get(
            f"/api/v1/parent-onboarding/connection-groups/{group.id}/members"
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200, (
        f"non-facilitator staff should see non-confidential roster; "
        f"got {resp.status_code} {resp.text}"
    )
