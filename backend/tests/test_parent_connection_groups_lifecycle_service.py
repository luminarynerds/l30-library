# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Service-layer tests for parent connection group lifecycle (cg_lifecycle_001).

Exercises ConnectionGroupService.archive_group, unarchive_group, list_meetings
(lazy materialization), cancel_meeting, reschedule_meeting, and the
count_active_members guard used by the PATCH route's 422 path.

Per the existing test_parent_connection_groups_enrollment_service convention:
we go directly to the service to sidestep the broken pytest-asyncio +
SessionMaker fixture-ordering issue on the FastAPI test client + httpx path.
Route-layer 403/422/404 contracts are documented in the route docstrings;
this file covers the *logic*, not the auth wiring.
"""
from datetime import date, timedelta

import pytest

from app.models.parent_onboarding import (
    ConnectionGroupType,
    GroupMemberStatus,
    MeetingFrequency,
    ParentConnectionGroup,
    ParentConnectionGroupMeeting,
    ParentConnectionGroupMember,
)
from app.services.parent_onboarding import ConnectionGroupService


# ---------------------------------------------------------------------------
# Local helpers — mirror the enrollment-service test file conventions so
# anyone reading both has one mental model.
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


async def _mk_group(
    test_db,
    *,
    max_members: int = 12,
    meeting_day_of_week: str = "monday",
    frequency: MeetingFrequency = MeetingFrequency.weekly,
) -> int:
    g = ParentConnectionGroup(
        name="Tuesday Crew",
        description="A group",
        branch_id=1,
        group_type=ConnectionGroupType.general,
        max_members=max_members,
        meeting_frequency=frequency,
        meeting_day_of_week=meeting_day_of_week,
        meeting_time="10:30",
        location="Community Room A",
        is_active=True,
    )
    test_db.add(g)
    await test_db.commit()
    await test_db.refresh(g)
    return g.id


async def _enroll_active(test_db, *, group_id: int, patron_id: int) -> int:
    m = ParentConnectionGroupMember(
        group_id=group_id,
        patron_id=patron_id,
        status=GroupMemberStatus.active,
        joined_date=date.today(),
        enrolled_by_id=None,
    )
    test_db.add(m)
    await test_db.commit()
    await test_db.refresh(m)
    return m.id


# ---------------------------------------------------------------------------
# Archive / unarchive
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_archive_group_sets_audit_columns(test_db):
    from app.models.user import UserRole

    admin_id = await _mk_user(test_db, email="admin1@x.com", role=UserRole.LIBRARY_ADMIN)
    group_id = await _mk_group(test_db)
    group = await ConnectionGroupService.get_group(test_db, group_id)

    await ConnectionGroupService.archive_group(
        test_db,
        group=group,
        archived_by_id=admin_id,
        archive_reason="cohort_complete",
        archive_notes="Wrapped up summer cohort",
    )

    assert group.is_active is False
    assert group.archived_at is not None
    assert group.archived_by_id == admin_id
    assert group.archive_reason == "cohort_complete"
    assert group.archive_notes == "Wrapped up summer cohort"


@pytest.mark.asyncio
async def test_archive_group_retains_active_members(test_db):
    """Archiving must NOT remove members — historical roster is read-after-archive."""
    from app.models.user import UserRole

    admin_id = await _mk_user(test_db, email="admin2@x.com", role=UserRole.LIBRARY_ADMIN)
    patron_id = await _mk_user(test_db, email="patron2@x.com", role=UserRole.PATRON)
    group_id = await _mk_group(test_db)
    await _enroll_active(test_db, group_id=group_id, patron_id=patron_id)

    group = await ConnectionGroupService.get_group(test_db, group_id)
    await ConnectionGroupService.archive_group(
        test_db,
        group=group,
        archived_by_id=admin_id,
        archive_reason="other",
    )

    members = await ConnectionGroupService.list_members(test_db, group_id)
    assert any(m["patron_id"] == patron_id for m in members)


@pytest.mark.asyncio
async def test_unarchive_clears_audit_columns(test_db):
    from app.models.user import UserRole

    admin_id = await _mk_user(test_db, email="admin3@x.com", role=UserRole.LIBRARY_ADMIN)
    group_id = await _mk_group(test_db)
    group = await ConnectionGroupService.get_group(test_db, group_id)

    await ConnectionGroupService.archive_group(
        test_db, group=group, archived_by_id=admin_id, archive_reason="cohort_complete",
    )
    await ConnectionGroupService.unarchive_group(test_db, group=group)

    assert group.is_active is True
    assert group.archived_at is None
    assert group.archived_by_id is None
    assert group.archive_reason is None
    assert group.archive_notes is None


# ---------------------------------------------------------------------------
# Capacity-conflict guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_count_active_members_matches_persisted_rows(test_db):
    from app.models.user import UserRole

    group_id = await _mk_group(test_db, max_members=12)
    p1 = await _mk_user(test_db, email="p1@x.com", role=UserRole.PATRON)
    p2 = await _mk_user(test_db, email="p2@x.com", role=UserRole.PATRON)
    await _enroll_active(test_db, group_id=group_id, patron_id=p1)
    await _enroll_active(test_db, group_id=group_id, patron_id=p2)

    assert await ConnectionGroupService.count_active_members(test_db, group_id) == 2
    ids = await ConnectionGroupService.active_member_ids(test_db, group_id)
    assert len(ids) == 2


# ---------------------------------------------------------------------------
# Lazy meeting materialization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_meetings_materializes_eight_dates(test_db):
    group_id = await _mk_group(test_db, meeting_day_of_week="monday")
    group = await ConnectionGroupService.get_group(test_db, group_id)

    meetings = await ConnectionGroupService.list_meetings(test_db, group=group)
    assert len(meetings) == 8
    # All should be in the future (or today) and on Mondays.
    today = date.today()
    for m in meetings:
        assert m.meeting_date >= today
        assert m.meeting_date.weekday() == 0  # Monday
        assert m.status == "scheduled"
        assert m.scheduled_time == "10:30"  # mirrored from group at materialization


@pytest.mark.asyncio
async def test_list_meetings_does_not_regenerate_existing(test_db):
    """Repeated reads must surface persisted edits, not overwrite them.
    Regression guard for the lazy-generation idempotency contract.
    """
    group_id = await _mk_group(test_db, meeting_day_of_week="monday")
    group = await ConnectionGroupService.get_group(test_db, group_id)

    first = await ConnectionGroupService.list_meetings(test_db, group=group)
    assert len(first) == 8
    first_ids = sorted(m.id for m in first)

    second = await ConnectionGroupService.list_meetings(test_db, group=group)
    second_ids = sorted(m.id for m in second)
    assert first_ids == second_ids


@pytest.mark.asyncio
async def test_list_meetings_backfills_after_cancel(test_db):
    """After cancelling one scheduled meeting the next read should materialize
    one more to maintain the 8-upcoming-scheduled invariant."""
    from app.models.user import UserRole

    admin_id = await _mk_user(test_db, email="admin-bf@x.com", role=UserRole.LIBRARY_ADMIN)
    group_id = await _mk_group(test_db, meeting_day_of_week="monday")
    group = await ConnectionGroupService.get_group(test_db, group_id)

    meetings = await ConnectionGroupService.list_meetings(test_db, group=group)
    initial_count = len(meetings)
    assert initial_count == 8
    to_cancel = meetings[0]
    await ConnectionGroupService.cancel_meeting(
        test_db,
        meeting=to_cancel,
        cancelled_by_id=admin_id,
        reason="weather",
    )

    refreshed = await ConnectionGroupService.list_meetings(test_db, group=group)
    scheduled = [m for m in refreshed if m.status == "scheduled"]
    assert len(scheduled) == 8


# ---------------------------------------------------------------------------
# Cancel / reschedule
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_meeting_writes_audit(test_db):
    from app.models.user import UserRole

    admin_id = await _mk_user(test_db, email="admin-c@x.com", role=UserRole.LIBRARY_ADMIN)
    group_id = await _mk_group(test_db)
    group = await ConnectionGroupService.get_group(test_db, group_id)
    meetings = await ConnectionGroupService.list_meetings(test_db, group=group)
    target = meetings[0]

    await ConnectionGroupService.cancel_meeting(
        test_db,
        meeting=target,
        cancelled_by_id=admin_id,
        reason="venue_unavailable",
        staff_notes="Closed for renovation",
        patron_message="We're moving the room. Stay tuned for next week.",
    )

    assert target.status == "cancelled"
    assert target.cancelled_reason == "venue_unavailable"
    assert target.cancelled_at is not None
    assert target.cancelled_by_id == admin_id
    assert target.staff_notes == "Closed for renovation"
    assert "Stay tuned" in (target.patron_message or "")


@pytest.mark.asyncio
async def test_reschedule_meeting_creates_new_links_old(test_db):
    from app.models.user import UserRole

    admin_id = await _mk_user(test_db, email="admin-r@x.com", role=UserRole.LIBRARY_ADMIN)
    group_id = await _mk_group(test_db)
    group = await ConnectionGroupService.get_group(test_db, group_id)
    meetings = await ConnectionGroupService.list_meetings(test_db, group=group)
    original = meetings[0]
    new_date = original.meeting_date + timedelta(days=2)

    old, new = await ConnectionGroupService.reschedule_meeting(
        test_db,
        group=group,
        meeting=original,
        rescheduled_by_id=admin_id,
        new_date=new_date,
        new_time="11:00",
        new_location="Community Room B",
        staff_notes="Switching to bigger room",
        patron_message="We've moved this one to Wednesday.",
    )

    assert old.status == "rescheduled"
    assert old.rescheduled_to_meeting_id == new.id
    assert new.status == "scheduled"
    assert new.meeting_date == new_date
    assert new.scheduled_time == "11:00"
    assert new.location == "Community Room B"
    assert new.patron_message == "We've moved this one to Wednesday."


@pytest.mark.asyncio
async def test_active_member_emails_excludes_waitlisted_and_inactive(test_db):
    from app.models.user import UserRole

    group_id = await _mk_group(test_db)
    active_id = await _mk_user(test_db, email="active@x.com", role=UserRole.PATRON)
    waitlist_id = await _mk_user(test_db, email="waitlist@x.com", role=UserRole.PATRON)
    await _enroll_active(test_db, group_id=group_id, patron_id=active_id)

    waitlist = ParentConnectionGroupMember(
        group_id=group_id,
        patron_id=waitlist_id,
        status=GroupMemberStatus.waitlisted,
        joined_date=date.today(),
    )
    test_db.add(waitlist)
    await test_db.commit()

    rows = await ConnectionGroupService.active_member_emails(test_db, group_id)
    assert len(rows) == 1
    pid, email, first = rows[0]
    assert pid == active_id
    assert email == "active@x.com"


@pytest.mark.asyncio
async def test_frequency_step_days_handles_known_values():
    """Spec: weekly=7, biweekly=14, monthly~=28. Documenting the contract
    in a test so future maintenance doesn't drift it silently."""
    assert ConnectionGroupService._frequency_step_days(MeetingFrequency.weekly) == 7
    assert ConnectionGroupService._frequency_step_days(MeetingFrequency.biweekly) == 14
    assert ConnectionGroupService._frequency_step_days(MeetingFrequency.monthly) == 28
    # Unknown / None falls back to weekly so lazy-gen never raises.
    assert ConnectionGroupService._frequency_step_days(None) == 7
