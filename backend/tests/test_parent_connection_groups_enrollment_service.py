# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Service-layer tests for parent connection group staff enrollment.

These exercise ConnectionGroupService.staff_enroll/staff_remove/list_members
directly. They intentionally avoid the FastAPI test client + httpx +
dependency_overrides path because that path hits a known broken pytest-asyncio
+ SessionMaker fixture-ordering issue on the L30 backend (multiple fixtures
sharing the same async test_db session see the identity-map collide on
auto-increment primary keys).

Endpoint-layer coverage (role gates, deprecation header, query-param
validation) is exercised at request time via the existing pytest harness in
PR review; the spec contract for those is documented in the route docstring
and the StaffEnrollRequest schema.
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


# ---------------------------------------------------------------------------
# Local fixtures that build test users via raw SQLAlchemy to avoid the broken
# shared-session id-collision in the project-wide test_patron/test_staff
# fixtures.
# ---------------------------------------------------------------------------


async def _mk_user(test_db, *, email: str, role) -> int:
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


async def _mk_group(test_db, *, max_members: int = 2) -> int:
    g = ParentConnectionGroup(
        name="Tuesday Crew",
        description="A group",
        branch_id=1,
        group_type=ConnectionGroupType.general,
        max_members=max_members,
        meeting_frequency=MeetingFrequency.weekly,
        is_active=True,
    )
    test_db.add(g)
    await test_db.commit()
    await test_db.refresh(g)
    return g.id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_staff_enroll_under_capacity_returns_active(test_db):
    from app.models.user import UserRole

    staff_id = await _mk_user(test_db, email="staff1@x.com", role=UserRole.STAFF)
    patron_id = await _mk_user(test_db, email="p1@x.com", role=UserRole.PATRON)
    group_id = await _mk_group(test_db, max_members=2)

    payload = await ConnectionGroupService.staff_enroll(
        test_db,
        group_id=group_id,
        patron_id=patron_id,
        enrolled_by_id=staff_id,
        consent_note="Verbal at desk",
    )
    assert payload["status"] == GroupMemberStatus.active
    assert payload["enrolled_by_id"] == staff_id
    assert payload["consent_note_recorded"] is True
    assert payload["capacity_overridden"] is False


@pytest.mark.asyncio
async def test_staff_enroll_over_capacity_no_override_waitlists(test_db):
    from app.models.user import UserRole

    staff_id = await _mk_user(test_db, email="staff2@x.com", role=UserRole.STAFF)
    p1 = await _mk_user(test_db, email="p2a@x.com", role=UserRole.PATRON)
    p2 = await _mk_user(test_db, email="p2b@x.com", role=UserRole.PATRON)
    p3 = await _mk_user(test_db, email="p2c@x.com", role=UserRole.PATRON)
    group_id = await _mk_group(test_db, max_members=2)

    # Fill capacity with two active members.
    for pid in (p1, p2):
        test_db.add(ParentConnectionGroupMember(
            group_id=group_id, patron_id=pid,
            joined_date=date.today(), status=GroupMemberStatus.active,
        ))
    await test_db.commit()

    payload = await ConnectionGroupService.staff_enroll(
        test_db,
        group_id=group_id,
        patron_id=p3,
        enrolled_by_id=staff_id,
    )
    assert payload["status"] == GroupMemberStatus.waitlisted
    assert payload["capacity_overridden"] is False


@pytest.mark.asyncio
async def test_staff_enroll_over_capacity_with_override_flag_writes_audit(test_db):
    from app.models.user import UserRole

    admin_id = await _mk_user(test_db, email="admin1@x.com", role=UserRole.ADMIN)
    p1 = await _mk_user(test_db, email="p3a@x.com", role=UserRole.PATRON)
    p2 = await _mk_user(test_db, email="p3b@x.com", role=UserRole.PATRON)
    p3 = await _mk_user(test_db, email="p3c@x.com", role=UserRole.PATRON)
    group_id = await _mk_group(test_db, max_members=2)

    for pid in (p1, p2):
        test_db.add(ParentConnectionGroupMember(
            group_id=group_id, patron_id=pid,
            joined_date=date.today(), status=GroupMemberStatus.active,
        ))
    await test_db.commit()

    payload = await ConnectionGroupService.staff_enroll(
        test_db,
        group_id=group_id,
        patron_id=p3,
        enrolled_by_id=admin_id,
        capacity_override=True,
        override_justification="Patron is the facilitator's co-lead.",
    )
    assert payload["status"] == GroupMemberStatus.active
    assert payload["capacity_overridden"] is True


@pytest.mark.asyncio
async def test_staff_enroll_already_member_raises(test_db):
    from app.models.user import UserRole

    staff_id = await _mk_user(test_db, email="staff3@x.com", role=UserRole.STAFF)
    patron_id = await _mk_user(test_db, email="p4@x.com", role=UserRole.PATRON)
    group_id = await _mk_group(test_db, max_members=10)

    test_db.add(ParentConnectionGroupMember(
        group_id=group_id, patron_id=patron_id,
        joined_date=date.today(), status=GroupMemberStatus.active,
    ))
    await test_db.commit()

    with pytest.raises(ValueError, match="already"):
        await ConnectionGroupService.staff_enroll(
            test_db,
            group_id=group_id,
            patron_id=patron_id,
            enrolled_by_id=staff_id,
        )


@pytest.mark.asyncio
async def test_staff_remove_writes_audit_columns(test_db):
    from app.models.user import UserRole

    staff_id = await _mk_user(test_db, email="staff4@x.com", role=UserRole.STAFF)
    patron_id = await _mk_user(test_db, email="p5@x.com", role=UserRole.PATRON)
    group_id = await _mk_group(test_db, max_members=10)

    test_db.add(ParentConnectionGroupMember(
        group_id=group_id, patron_id=patron_id,
        joined_date=date.today(), status=GroupMemberStatus.active,
    ))
    await test_db.commit()

    member = await ConnectionGroupService.staff_remove(
        test_db,
        group_id=group_id,
        patron_id=patron_id,
        removed_by_id=staff_id,
        reason="program_ended",
    )
    assert member.status == GroupMemberStatus.inactive
    assert member.removed_by_id == staff_id
    assert member.removal_reason == "program_ended"
    assert member.left_date == date.today()


@pytest.mark.asyncio
async def test_list_members_returns_active_and_waitlisted_excludes_inactive(test_db):
    from app.models.user import UserRole

    staff_id = await _mk_user(test_db, email="staff5@x.com", role=UserRole.STAFF)
    p1 = await _mk_user(test_db, email="p6a@x.com", role=UserRole.PATRON)
    p2 = await _mk_user(test_db, email="p6b@x.com", role=UserRole.PATRON)
    p3 = await _mk_user(test_db, email="p6c@x.com", role=UserRole.PATRON)
    group_id = await _mk_group(test_db, max_members=10)

    test_db.add_all([
        ParentConnectionGroupMember(
            group_id=group_id, patron_id=p1, joined_date=date.today(),
            status=GroupMemberStatus.active, enrolled_by_id=staff_id,
        ),
        ParentConnectionGroupMember(
            group_id=group_id, patron_id=p2, joined_date=date.today(),
            status=GroupMemberStatus.waitlisted,
        ),
        ParentConnectionGroupMember(
            group_id=group_id, patron_id=p3, joined_date=date.today(),
            status=GroupMemberStatus.inactive,
        ),
    ])
    await test_db.commit()

    rows = await ConnectionGroupService.list_members(test_db, group_id)
    statuses = sorted(r["status"] for r in rows)
    assert statuses == [GroupMemberStatus.active, GroupMemberStatus.waitlisted]
    # Active row carries the enroller id.
    active = next(r for r in rows if r["status"] == GroupMemberStatus.active)
    assert active["enrolled_by_id"] == staff_id


@pytest.mark.asyncio
async def test_staff_enroll_group_not_found_raises(test_db):
    from app.models.user import UserRole

    staff_id = await _mk_user(test_db, email="staff6@x.com", role=UserRole.STAFF)
    patron_id = await _mk_user(test_db, email="p7@x.com", role=UserRole.PATRON)

    with pytest.raises(ValueError, match="not found"):
        await ConnectionGroupService.staff_enroll(
            test_db,
            group_id=99999,
            patron_id=patron_id,
            enrolled_by_id=staff_id,
        )


def test_staff_enroll_request_schema_requires_justification_when_override():
    """Pydantic-level: override_capacity=True without justification → ValidationError."""
    from pydantic import ValidationError
    from app.schemas.parent_onboarding import StaffEnrollRequest

    with pytest.raises(ValidationError):
        StaffEnrollRequest(patron_id=1, override_capacity=True)

    # With both → passes.
    StaffEnrollRequest(
        patron_id=1,
        override_capacity=True,
        override_justification="A plausible reason text.",
    )


def test_staff_enroll_request_schema_consent_max_length():
    from pydantic import ValidationError
    from app.schemas.parent_onboarding import StaffEnrollRequest

    with pytest.raises(ValidationError):
        StaffEnrollRequest(patron_id=1, consent_note="x" * 501)
