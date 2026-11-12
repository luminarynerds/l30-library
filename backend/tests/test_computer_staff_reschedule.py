# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff reschedule + staff-granted extension on computer reservations/sessions."""
import pytest
from datetime import datetime, timedelta, timezone

from app.models.computer import (
    Computer, ComputerReservation, ComputerReservationStatus,
    ComputerStatus, ComputerType,
)
from app.models.cipa_compliance import ComputerSession, ComputerSessionStatus
from app.services import computer_service

T0 = datetime(2026, 6, 10, 14, 0, tzinfo=timezone.utc)


async def _mk_computer(db, name="T-1", num="T-01"):
    c = Computer(
        name=name, computer_number=num, computer_type=ComputerType.adult,
        status=ComputerStatus.available, is_active=True, max_session_minutes=60,
    )
    db.add(c)
    await db.flush()
    return c


async def _mk_res(db, computer_id, start, end, status=ComputerReservationStatus.confirmed):
    r = ComputerReservation(
        computer_id=computer_id, reserved_start_time=start, reserved_end_time=end,
        status=status, session_duration_minutes=int((end - start).total_seconds() / 60),
    )
    db.add(r)
    await db.flush()
    return r


async def _mk_active_session(db, reservation_id, computer_id, start, end):
    s = ComputerSession(
        reservation_id=reservation_id, computer_id=computer_id, is_active=True,
        session_start_time=start, session_end_time=end,
        status=ComputerSessionStatus.ACTIVE, extension_count=0,
    )
    db.add(s)
    await db.flush()
    return s


@pytest.mark.asyncio
async def test_reschedule_confirmed_moves_both_ends(test_db):
    c = await _mk_computer(test_db)
    r = await _mk_res(test_db, c.id, T0, T0 + timedelta(hours=1))
    new_start, new_end = T0 + timedelta(hours=2), T0 + timedelta(hours=3)
    res, err = await computer_service.staff_update_reservation(test_db, r.id, new_start, new_end)
    assert err is None
    assert res.reserved_start_time == new_start
    assert res.reserved_end_time == new_end
    assert res.session_duration_minutes == 60


@pytest.mark.asyncio
async def test_reschedule_onto_another_reservation_conflicts(test_db):
    c = await _mk_computer(test_db)
    await _mk_res(test_db, c.id, T0, T0 + timedelta(hours=1))
    r2 = await _mk_res(test_db, c.id, T0 + timedelta(hours=2), T0 + timedelta(hours=3))
    res, err = await computer_service.staff_update_reservation(
        test_db, r2.id, T0, T0 + timedelta(hours=1)
    )
    assert res is None
    assert err == "conflict"


@pytest.mark.asyncio
async def test_reschedule_in_session_rejects_moving_start(test_db):
    c = await _mk_computer(test_db)
    r = await _mk_res(test_db, c.id, T0, T0 + timedelta(hours=1),
                      status=ComputerReservationStatus.in_session)
    res, err = await computer_service.staff_update_reservation(
        test_db, r.id, T0 + timedelta(hours=1), T0 + timedelta(hours=2)
    )
    assert res is None
    assert err == "bad_times"


@pytest.mark.asyncio
async def test_reschedule_in_session_moves_end_and_active_session(test_db):
    c = await _mk_computer(test_db)
    r = await _mk_res(test_db, c.id, T0, T0 + timedelta(hours=1),
                      status=ComputerReservationStatus.in_session)
    s = await _mk_active_session(test_db, r.id, c.id, T0, T0 + timedelta(hours=1))
    new_end = T0 + timedelta(hours=2)
    res, err = await computer_service.staff_update_reservation(test_db, r.id, None, new_end)
    assert err is None
    assert res.reserved_end_time == new_end
    await test_db.refresh(s)
    assert s.session_end_time == new_end
    assert s.auto_logout_at == new_end - timedelta(minutes=5)


@pytest.mark.asyncio
async def test_staff_extend_bumps_session_and_reservation(test_db):
    c = await _mk_computer(test_db)
    r = await _mk_res(test_db, c.id, T0, T0 + timedelta(hours=1),
                      status=ComputerReservationStatus.in_session)
    s = await _mk_active_session(test_db, r.id, c.id, T0, T0 + timedelta(hours=1))
    res, err = await computer_service.staff_extend_session(test_db, s.id, 30, staff_id=1)
    assert err is None
    assert res.reserved_end_time == T0 + timedelta(hours=1, minutes=30)
    assert res.extensions_used == 1
    await test_db.refresh(s)
    assert s.session_end_time == T0 + timedelta(hours=1, minutes=30)
    assert s.extension_count == 1
    assert s.was_extended is True
