# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the staff-side check-in / no-show / roster audit fields.

Mirrors the service-layer style used in
``test_childcare_pickup_authorization.py`` -- we exercise the endpoint
*handlers* directly (not via the httpx client) to dodge the L30
pytest-asyncio + SessionMaker fixture-ordering issue that turns
TestClient tests into a flaky mess.

Five behaviors locked down:

  1. PATCH ``status=checked_in`` stamps ``checked_in_at`` AND
     ``checked_in_by_staff_id`` from ``current_user``.
  2. PATCH ``status=checked_in`` is idempotent -- a second call with the
     same status does NOT rewrite the original audit row.
  3. PATCH ``status=no_show`` stamps the no-show audit triad
     (``no_show_flagged_by_staff_id``, ``no_show_flagged_at``,
     ``no_show_reason``) when the reason field is supplied.
  4. PATCH ``status=checked_in`` from a patron user is rejected with 403
     (the spec's staff-only-transition tightening).
  5. PATCH with no_show_reason and status=cancelled silently drops the
     reason (only meaningful when transitioning to no_show).
  6. GET /sessions/{id}/roster (staff): counts reflect every status,
     and a non-staff caller gets 403.
"""
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.parent_onboarding.childcare import (
    get_childcare_roster,
    update_childcare_registration,
)
from app.models.parent_onboarding import (
    ChildcareRegistration,
    ChildcareRegistrationStatus,
    ChildcareSession,
    ChildcareSessionStatus,
)
from app.schemas.parent_onboarding import ChildcareRegistrationUpdate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _mk_user(test_db, *, role, email_suffix: str):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    u = User(
        email=f"checkin-{email_suffix}@example.test",
        password_hash=hash_password("Password123!"),
        first_name="F",
        last_name="L",
        role=role if isinstance(role, UserRole) else UserRole(role),
        is_active=True,
        email_verified=True,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u


async def _mk_registration(test_db, *, patron_id: int) -> ChildcareRegistration:
    session = ChildcareSession(
        branch_id=1,
        date=date(2026, 6, 1),
        start_time="09:00",
        end_time="12:00",
        max_children=10,
        status=ChildcareSessionStatus.available,
        staff_id=None,
    )
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)

    reg = ChildcareRegistration(
        session_id=session.id,
        patron_id=patron_id,
        child_name="Audit Child",
        child_age_months=24,
        emergency_contact_name="EC Person",
        emergency_contact_phone="5551110000",
        status=ChildcareRegistrationStatus.registered,
        authorized_pickup=[],
    )
    test_db.add(reg)
    await test_db.commit()
    await test_db.refresh(reg)
    return reg


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_checked_in_stamps_staff_audit(test_db):
    """checked_in transition stamps both timestamp AND who-checked-in."""
    from app.models.user import UserRole

    patron = await _mk_user(test_db, role=UserRole.PATRON, email_suffix="parent-1")
    staff = await _mk_user(test_db, role=UserRole.STAFF, email_suffix="staff-1")
    reg = await _mk_registration(test_db, patron_id=patron.id)

    body = ChildcareRegistrationUpdate(status=ChildcareRegistrationStatus.checked_in)
    response = await update_childcare_registration(
        registration_id=reg.id,
        data=body,
        current_user=staff,
        db=test_db,
    )

    assert response.status == ChildcareRegistrationStatus.checked_in
    assert response.checked_in_at is not None
    assert response.checked_in_by_staff_id == staff.id


@pytest.mark.asyncio
async def test_patch_checked_in_is_idempotent(test_db):
    """Second PATCH checked_in must NOT overwrite the original audit row."""
    from app.models.user import UserRole

    patron = await _mk_user(test_db, role=UserRole.PATRON, email_suffix="parent-2")
    staff_a = await _mk_user(test_db, role=UserRole.STAFF, email_suffix="staff-2a")
    staff_b = await _mk_user(test_db, role=UserRole.STAFF, email_suffix="staff-2b")
    reg = await _mk_registration(test_db, patron_id=patron.id)

    body = ChildcareRegistrationUpdate(status=ChildcareRegistrationStatus.checked_in)
    first = await update_childcare_registration(
        registration_id=reg.id, data=body, current_user=staff_a, db=test_db,
    )
    second = await update_childcare_registration(
        registration_id=reg.id, data=body, current_user=staff_b, db=test_db,
    )

    # The first staff member is preserved through the second redundant call.
    assert first.checked_in_at == second.checked_in_at
    assert second.checked_in_by_staff_id == staff_a.id
    assert second.checked_in_by_staff_id != staff_b.id


@pytest.mark.asyncio
async def test_patch_no_show_stamps_triad_and_reason(test_db):
    """no_show stamps flagged_by + flagged_at + reason."""
    from app.models.user import UserRole

    patron = await _mk_user(test_db, role=UserRole.PATRON, email_suffix="parent-3")
    staff = await _mk_user(test_db, role=UserRole.STAFF, email_suffix="staff-3")
    reg = await _mk_registration(test_db, patron_id=patron.id)

    body = ChildcareRegistrationUpdate(
        status=ChildcareRegistrationStatus.no_show,
        no_show_reason="Family didn't show up by start time + 30 min",
    )
    response = await update_childcare_registration(
        registration_id=reg.id, data=body, current_user=staff, db=test_db,
    )

    assert response.status == ChildcareRegistrationStatus.no_show
    assert response.no_show_flagged_at is not None
    assert response.no_show_flagged_by_staff_id == staff.id
    assert response.no_show_reason == "Family didn't show up by start time + 30 min"


@pytest.mark.asyncio
async def test_patch_checked_in_rejects_patron(test_db):
    """A patron cannot stamp themselves as checked in (forge audit row)."""
    from app.models.user import UserRole

    patron = await _mk_user(test_db, role=UserRole.PATRON, email_suffix="parent-4")
    reg = await _mk_registration(test_db, patron_id=patron.id)

    body = ChildcareRegistrationUpdate(status=ChildcareRegistrationStatus.checked_in)
    with pytest.raises(HTTPException) as exc:
        await update_childcare_registration(
            registration_id=reg.id, data=body, current_user=patron, db=test_db,
        )
    assert exc.value.status_code == 403
    # Reg unchanged.
    await test_db.refresh(reg)
    assert reg.checked_in_at is None
    assert reg.checked_in_by_staff_id is None


@pytest.mark.asyncio
async def test_patch_no_show_reason_dropped_when_status_is_cancelled(test_db):
    """no_show_reason is only meaningful for the no_show transition.

    Sent alongside any other status, the field is silently dropped so a
    confused client can't accidentally annotate an unrelated row.
    """
    from app.models.user import UserRole

    patron = await _mk_user(test_db, role=UserRole.PATRON, email_suffix="parent-5")
    # cancelled is a self-service transition -- the patron themselves may do it.
    reg = await _mk_registration(test_db, patron_id=patron.id)

    body = ChildcareRegistrationUpdate(
        status=ChildcareRegistrationStatus.cancelled,
        no_show_reason="this should be dropped",
    )
    response = await update_childcare_registration(
        registration_id=reg.id, data=body, current_user=patron, db=test_db,
    )

    assert response.status == ChildcareRegistrationStatus.cancelled
    assert response.no_show_reason is None
    assert response.no_show_flagged_at is None
    assert response.no_show_flagged_by_staff_id is None


@pytest.mark.asyncio
async def test_roster_counts_reflect_status_distribution(test_db):
    """GET roster: counts dict tallies every status in the session."""
    from app.models.user import UserRole

    staff = await _mk_user(test_db, role=UserRole.STAFF, email_suffix="roster-staff")
    patron_a = await _mk_user(test_db, role=UserRole.PATRON, email_suffix="roster-p-a")
    patron_b = await _mk_user(test_db, role=UserRole.PATRON, email_suffix="roster-p-b")
    patron_c = await _mk_user(test_db, role=UserRole.PATRON, email_suffix="roster-p-c")

    # Build one session manually so all three registrations share it.
    session = ChildcareSession(
        branch_id=1, date=date(2026, 6, 2), start_time="09:00", end_time="12:00",
        max_children=10, status=ChildcareSessionStatus.available, staff_id=None,
    )
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)

    def _mk(child_name: str, patron_id: int, status):
        return ChildcareRegistration(
            session_id=session.id, patron_id=patron_id,
            child_name=child_name, child_age_months=24,
            emergency_contact_name="EC", emergency_contact_phone="5550000000",
            status=status, authorized_pickup=[],
        )

    test_db.add_all([
        _mk("A", patron_a.id, ChildcareRegistrationStatus.registered),
        _mk("B", patron_b.id, ChildcareRegistrationStatus.checked_in),
        _mk("C", patron_c.id, ChildcareRegistrationStatus.no_show),
    ])
    await test_db.commit()

    # Fake Request that satisfies request.url.path + .client access.
    fake_request = SimpleNamespace(
        url=SimpleNamespace(path="/api/v1/parent-onboarding/childcare/sessions/1/roster"),
        client=SimpleNamespace(host="127.0.0.1"),
    )

    response = await get_childcare_roster(
        request=fake_request,
        session_id=session.id,
        current_user=staff,
        db=test_db,
    )

    assert response.counts.registered == 1
    assert response.counts.checked_in == 1
    assert response.counts.no_show == 1
    assert response.counts.checked_out == 0
    assert response.counts.cancelled == 0
    assert len(response.entries) == 3


@pytest.mark.asyncio
async def test_roster_rejects_non_staff(test_db):
    """A patron user gets 403 from the staff roster, even on their own session."""
    from app.models.user import UserRole

    patron = await _mk_user(test_db, role=UserRole.PATRON, email_suffix="roster-patron")
    reg = await _mk_registration(test_db, patron_id=patron.id)

    fake_request = SimpleNamespace(
        url=SimpleNamespace(path="/api/v1/parent-onboarding/childcare/sessions/X/roster"),
        client=SimpleNamespace(host="127.0.0.1"),
    )

    with pytest.raises(HTTPException) as exc:
        await get_childcare_roster(
            request=fake_request,
            session_id=reg.session_id,
            current_user=patron,
            db=test_db,
        )
    assert exc.value.status_code == 403
