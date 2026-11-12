# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Service-layer tests for L30 childcare session management.

Covers the additions made by feat/childcare-session-mgmt:

  * ``ChildcareService.list_sessions`` accepts ``to_date`` (inclusive) and
    combines correctly with ``from_date`` + ``status``.
  * ``ChildcareService.update_session`` exists and:
      - raises ``ValueError("Childcare session not found")`` for missing ids
        (router translates to 404)
      - raises ``ValueError("max_children below active count ...")`` when
        the cap would drop under the active-registration count (router
        translates to 422)
      - permits ``status=cancelled`` even when active registrations exist
        (the librarian's call to make)
      - persists the requested field changes (status, room_id, start_time,
        end_time, max_children, staff_id)

We deliberately drive the service directly rather than the FastAPI test
client; the project's pytest-asyncio + SessionMaker fixture ordering trips
on the dependency-override path (see
``test_childcare_pickup_authorization.py`` for the same rationale and the
``test_parent_connection_groups_enrollment_service.py`` docstring it cites).

The auth gating itself is verified by static introspection of the route's
declared dependencies -- that's enough to catch regressions where someone
swaps ``require_library_admin`` back to ``require_authenticated`` without
running the whole HTTP stack.
"""
from datetime import date

import pytest

from app.models.parent_onboarding import (
    ChildcareRegistration,
    ChildcareRegistrationStatus,
    ChildcareSession,
    ChildcareSessionStatus,
)
from app.services.parent_onboarding import ChildcareService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _mk_session(
    test_db,
    *,
    day: date,
    branch_id: int = 1,
    status: ChildcareSessionStatus = ChildcareSessionStatus.available,
    max_children: int = 6,
    start_time: str = "09:00",
    end_time: str = "12:00",
) -> ChildcareSession:
    s = ChildcareSession(
        branch_id=branch_id,
        date=day,
        start_time=start_time,
        end_time=end_time,
        max_children=max_children,
        status=status,
        staff_id=None,
    )
    test_db.add(s)
    await test_db.commit()
    await test_db.refresh(s)
    return s


async def _mk_patron(test_db, *, suffix: str) -> int:
    """Mint a fresh patron so registration FKs don't trip on uniqueness."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    u = User(
        email=f"sm-parent-{suffix}@example.test",
        password_hash=hash_password("Password123!"),
        first_name="P",
        last_name=suffix,
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u.id


async def _add_active_registration(
    test_db,
    *,
    session: ChildcareSession,
    patron_id: int,
    child_name: str,
    status: ChildcareRegistrationStatus = ChildcareRegistrationStatus.registered,
) -> ChildcareRegistration:
    reg = ChildcareRegistration(
        session_id=session.id,
        patron_id=patron_id,
        child_name=child_name,
        child_age_months=24,
        emergency_contact_name="EC Person",
        emergency_contact_phone="5551110000",
        status=status,
        authorized_pickup=[],
    )
    test_db.add(reg)
    await test_db.commit()
    await test_db.refresh(reg)
    return reg


# ---------------------------------------------------------------------------
# list_sessions: to_date + combined filters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_sessions_to_date_is_inclusive(test_db):
    """``to_date`` is inclusive on both edges of the window."""
    await _mk_session(test_db, day=date(2026, 6, 10))
    await _mk_session(test_db, day=date(2026, 6, 20))
    await _mk_session(test_db, day=date(2026, 6, 30))  # the upper edge
    await _mk_session(test_db, day=date(2026, 7, 5))   # outside

    sessions, total = await ChildcareService.list_sessions(
        test_db, to_date=date(2026, 6, 30)
    )
    dates = sorted(s.date for s in sessions)

    assert total == 3
    assert dates == [date(2026, 6, 10), date(2026, 6, 20), date(2026, 6, 30)]


@pytest.mark.asyncio
async def test_list_sessions_from_to_status_combine(test_db):
    """``from_date`` + ``to_date`` + ``status`` AND together correctly."""
    # Inside window, available -> SHOULD appear
    await _mk_session(test_db, day=date(2026, 6, 15))
    # Inside window, cancelled -> filtered by status
    await _mk_session(
        test_db, day=date(2026, 6, 18), status=ChildcareSessionStatus.cancelled
    )
    # Before window, available -> filtered by from_date
    await _mk_session(test_db, day=date(2026, 6, 1))
    # After window, available -> filtered by to_date
    await _mk_session(test_db, day=date(2026, 7, 1))

    sessions, total = await ChildcareService.list_sessions(
        test_db,
        from_date=date(2026, 6, 10),
        to_date=date(2026, 6, 30),
        status=ChildcareSessionStatus.available,
    )

    assert total == 1
    assert sessions[0].date == date(2026, 6, 15)


# ---------------------------------------------------------------------------
# update_session: 404 / capacity floor / cancel-with-registrations / persistence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_session_missing_id_raises_not_found(test_db):
    """Missing id -> ``ValueError`` with ``not found`` text (router: 404)."""
    with pytest.raises(ValueError) as excinfo:
        await ChildcareService.update_session(
            test_db, 999_999, {"max_children": 5}
        )
    assert "not found" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_update_session_max_children_below_active_count_raises(test_db):
    """Capacity floor: cannot under-cut already-registered families."""
    session = await _mk_session(test_db, day=date(2026, 8, 1), max_children=6)

    # Two distinct patrons -- the registration model is keyed on
    # (session_id, patron_id) and we want both to count toward "active".
    p1 = await _mk_patron(test_db, suffix="capfloor-a")
    p2 = await _mk_patron(test_db, suffix="capfloor-b")
    await _add_active_registration(
        test_db, session=session, patron_id=p1, child_name="A"
    )
    await _add_active_registration(
        test_db,
        session=session,
        patron_id=p2,
        child_name="B",
        status=ChildcareRegistrationStatus.checked_in,
    )

    with pytest.raises(ValueError) as excinfo:
        await ChildcareService.update_session(
            test_db, session.id, {"max_children": 1}
        )
    msg = str(excinfo.value).lower()
    assert "max_children" in msg
    assert "active" in msg


@pytest.mark.asyncio
async def test_update_session_cancel_allowed_with_active_registrations(test_db):
    """``status=cancelled`` is allowed even with active registrations.

    Notifying registered families is out of scope -- this is the librarian's
    call to make.
    """
    session = await _mk_session(test_db, day=date(2026, 8, 2))
    p = await _mk_patron(test_db, suffix="cancelwactive")
    await _add_active_registration(
        test_db, session=session, patron_id=p, child_name="ToCancel"
    )

    updated = await ChildcareService.update_session(
        test_db, session.id, {"status": ChildcareSessionStatus.cancelled}
    )
    assert updated.status == ChildcareSessionStatus.cancelled


@pytest.mark.asyncio
async def test_update_session_persists_field_changes(test_db):
    """Smoke check: every mutable field actually round-trips through update."""
    from app.models.room import Room

    session = await _mk_session(
        test_db,
        day=date(2026, 8, 3),
        start_time="09:00",
        end_time="12:00",
        max_children=6,
    )

    # room_id has a real FK to rooms.id -- a made-up id would fail the
    # constraint, so create a real room to point at.
    room = Room(name="Storytime Room")
    test_db.add(room)
    await test_db.commit()
    await test_db.refresh(room)

    updates = {
        "start_time": "10:30",
        "end_time": "13:15",
        "max_children": 8,
        "room_id": room.id,
        "staff_id": None,  # explicit clear
        "status": ChildcareSessionStatus.in_progress,
    }
    updated = await ChildcareService.update_session(test_db, session.id, updates)

    assert updated.start_time == "10:30"
    assert updated.end_time == "13:15"
    assert updated.max_children == 8
    assert updated.room_id == room.id
    assert updated.staff_id is None
    assert updated.status == ChildcareSessionStatus.in_progress


# ---------------------------------------------------------------------------
# Auth-gating introspection
# ---------------------------------------------------------------------------


def test_patch_route_is_library_admin_gated():
    """The PATCH route must be gated with ``require_library_admin``.

    We introspect the FastAPI app rather than hitting the HTTP client (the
    test-client pattern hits a known fixture-ordering issue in this repo,
    see this module's docstring).
    """
    from app.api.v1.dependencies import require_library_admin
    from app.api.v1.parent_onboarding.childcare import update_childcare_session

    # FastAPI stashes the resolved dependency on the function via
    # ``Depends(...)`` default; check that ``require_library_admin`` is the
    # callable on the ``current_user`` parameter default.
    import inspect

    sig = inspect.signature(update_childcare_session)
    current_user_param = sig.parameters["current_user"]
    # ``current_user_param.default`` is a ``fastapi.params.Depends`` instance.
    assert current_user_param.default.dependency is require_library_admin
