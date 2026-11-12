# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Service-layer tests for connection-group confidentiality + approval queue.

Mirrors test_parent_connection_groups_enrollment_service.py style: raw model
construction in tests to dodge the project-wide shared-session fixture
collision, async sqlite for speed, no FastAPI test client.
"""
from datetime import date

import pytest

from app.models.parent_onboarding import (
    ConnectionGroupType,
    GroupMemberStatus,
    MeetingFrequency,
    ParentConnectionGroup,
    ParentConnectionGroupMember,
)
from app.services.parent_onboarding import ConnectionGroupService


async def _mk_user(test_db, *, email: str, role):
    from app.core.security import hash_password
    from app.models.user import User

    u = User(
        email=email,
        password_hash=hash_password("Password123!"),
        first_name="First",
        last_name="Last",
        role=role,
        is_active=True,
        email_verified=True,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u.id


async def _mk_group(
    test_db,
    *,
    confidential: bool = True,
    max_members: int = 4,
    facilitator_id: int | None = None,
):
    g = ParentConnectionGroup(
        name="Confidential Crew",
        description="Sensitive group",
        branch_id=1,
        group_type=ConnectionGroupType.teen_parents,
        max_members=max_members,
        meeting_frequency=MeetingFrequency.weekly,
        is_active=True,
        confidential=confidential,
        confidential_card_description="Welcome and safe",
        confidential_approval_message="Staff will reply soon",
        estimated_response_window_hours=48,
        facilitator_id=facilitator_id,
    )
    test_db.add(g)
    await test_db.commit()
    await test_db.refresh(g)
    return g.id


@pytest.mark.asyncio
async def test_request_join_creates_pending_approval(test_db):
    from app.models.user import UserRole

    patron_id = await _mk_user(test_db, email="p1@test.com", role=UserRole.PATRON)
    group_id = await _mk_group(test_db)
    payload = await ConnectionGroupService.request_join(
        test_db,
        group_id=group_id,
        patron_id=patron_id,
        requested_by_id=patron_id,
        request_message="please",
        consent_to_share_contact=False,
    )
    assert payload["status"] == GroupMemberStatus.pending_approval
    assert payload["estimated_response_window_hours"] == 48


@pytest.mark.asyncio
async def test_request_join_on_non_confidential_raises(test_db):
    from app.models.user import UserRole

    patron_id = await _mk_user(test_db, email="p2@test.com", role=UserRole.PATRON)
    group_id = await _mk_group(test_db, confidential=False)
    with pytest.raises(ValueError, match="enroll endpoint"):
        await ConnectionGroupService.request_join(
            test_db,
            group_id=group_id,
            patron_id=patron_id,
            requested_by_id=patron_id,
        )


@pytest.mark.asyncio
async def test_decide_approve_promotes_to_active(test_db):
    from app.models.user import UserRole

    patron_id = await _mk_user(test_db, email="p3@test.com", role=UserRole.PATRON)
    admin_id = await _mk_user(test_db, email="a3@test.com", role=UserRole.ADMIN)
    group_id = await _mk_group(test_db)
    req = await ConnectionGroupService.request_join(
        test_db, group_id=group_id, patron_id=patron_id, requested_by_id=patron_id,
    )
    result = await ConnectionGroupService.decide_request(
        test_db,
        group_id=group_id,
        member_id=req["id"],
        decision="approve",
        decided_by_id=admin_id,
    )
    assert result["status"] == GroupMemberStatus.active
    assert result["decided_by_id"] == admin_id
    assert result["decided_at"] is not None


@pytest.mark.asyncio
async def test_decide_deny_sets_denied(test_db):
    from app.models.user import UserRole

    patron_id = await _mk_user(test_db, email="p4@test.com", role=UserRole.PATRON)
    admin_id = await _mk_user(test_db, email="a4@test.com", role=UserRole.ADMIN)
    group_id = await _mk_group(test_db)
    req = await ConnectionGroupService.request_join(
        test_db, group_id=group_id, patron_id=patron_id, requested_by_id=patron_id,
    )
    result = await ConnectionGroupService.decide_request(
        test_db,
        group_id=group_id,
        member_id=req["id"],
        decision="deny",
        decided_by_id=admin_id,
        patron_message="Not a fit right now",
    )
    assert result["status"] == GroupMemberStatus.denied


@pytest.mark.asyncio
async def test_decide_already_decided_is_idempotent(test_db):
    from app.models.user import UserRole

    patron_id = await _mk_user(test_db, email="p5@test.com", role=UserRole.PATRON)
    admin_id = await _mk_user(test_db, email="a5@test.com", role=UserRole.ADMIN)
    group_id = await _mk_group(test_db)
    req = await ConnectionGroupService.request_join(
        test_db, group_id=group_id, patron_id=patron_id, requested_by_id=patron_id,
    )
    first = await ConnectionGroupService.decide_request(
        test_db, group_id=group_id, member_id=req["id"], decision="approve", decided_by_id=admin_id,
    )
    second = await ConnectionGroupService.decide_request(
        test_db, group_id=group_id, member_id=req["id"], decision="deny", decided_by_id=admin_id,
    )
    assert first["status"] == GroupMemberStatus.active
    assert second.get("already_decided") is True
    assert second["status"] == GroupMemberStatus.active


@pytest.mark.asyncio
async def test_approval_queue_hides_contact_when_consent_false(test_db):
    from app.models.user import UserRole

    patron_id = await _mk_user(test_db, email="p6@test.com", role=UserRole.PATRON)
    group_id = await _mk_group(test_db)
    await ConnectionGroupService.request_join(
        test_db, group_id=group_id, patron_id=patron_id, requested_by_id=patron_id,
        consent_to_share_contact=False,
    )
    queue = await ConnectionGroupService.list_approval_queue(test_db, group_id)
    assert len(queue["pending"]) == 1
    row = queue["pending"][0]
    assert row["patron_contact_visible"] is False
    assert row["patron_email"] is None
    assert row["patron_phone"] is None


@pytest.mark.asyncio
async def test_approval_queue_shows_contact_when_consent_true(test_db):
    from app.models.user import UserRole

    patron_id = await _mk_user(test_db, email="p7@test.com", role=UserRole.PATRON)
    group_id = await _mk_group(test_db)
    await ConnectionGroupService.request_join(
        test_db, group_id=group_id, patron_id=patron_id, requested_by_id=patron_id,
        consent_to_share_contact=True,
    )
    queue = await ConnectionGroupService.list_approval_queue(test_db, group_id)
    row = queue["pending"][0]
    assert row["patron_contact_visible"] is True
    assert row["patron_email"] == "p7@test.com"


@pytest.mark.asyncio
async def test_staff_enroll_confidential_admin_direct_enroll(test_db):
    from app.models.user import UserRole

    patron_id = await _mk_user(test_db, email="p8@test.com", role=UserRole.PATRON)
    admin_id = await _mk_user(test_db, email="a8@test.com", role=UserRole.ADMIN)
    group_id = await _mk_group(test_db)
    payload = await ConnectionGroupService.staff_enroll(
        test_db,
        group_id=group_id,
        patron_id=patron_id,
        enrolled_by_id=admin_id,
        caller_is_facilitator_or_admin=True,
    )
    assert payload["status"] == GroupMemberStatus.active


@pytest.mark.asyncio
async def test_staff_enroll_confidential_general_staff_pending(test_db):
    from app.models.user import UserRole

    patron_id = await _mk_user(test_db, email="p9@test.com", role=UserRole.PATRON)
    staff_id = await _mk_user(test_db, email="s9@test.com", role=UserRole.STAFF)
    group_id = await _mk_group(test_db)
    payload = await ConnectionGroupService.staff_enroll(
        test_db,
        group_id=group_id,
        patron_id=patron_id,
        enrolled_by_id=staff_id,
        caller_is_facilitator_or_admin=False,
    )
    assert payload["status"] == GroupMemberStatus.pending_approval


@pytest.mark.asyncio
async def test_capacity_override_blocked_on_confidential(test_db):
    from app.models.user import UserRole

    patron_id = await _mk_user(test_db, email="p10@test.com", role=UserRole.PATRON)
    admin_id = await _mk_user(test_db, email="a10@test.com", role=UserRole.ADMIN)
    group_id = await _mk_group(test_db, max_members=2)
    with pytest.raises(ValueError, match="not allowed"):
        await ConnectionGroupService.staff_enroll(
            test_db,
            group_id=group_id,
            patron_id=patron_id,
            enrolled_by_id=admin_id,
            capacity_override=True,
            override_justification="x" * 20,
            caller_is_facilitator_or_admin=True,
        )


@pytest.mark.asyncio
async def test_request_join_idempotent_on_pending(test_db):
    from app.models.user import UserRole

    patron_id = await _mk_user(test_db, email="p11@test.com", role=UserRole.PATRON)
    group_id = await _mk_group(test_db)
    first = await ConnectionGroupService.request_join(
        test_db, group_id=group_id, patron_id=patron_id, requested_by_id=patron_id,
    )
    second = await ConnectionGroupService.request_join(
        test_db, group_id=group_id, patron_id=patron_id, requested_by_id=patron_id,
    )
    assert first["id"] == second["id"]
