# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for session_manager service.

Tests cover:
- Starting a walk-in computer session
- Retrieving the current active session
- Extending a session (success and limit exceeded)
- Ending a session
- Background task: expiring overdue sessions
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.models.computer import (
    Computer,
    ComputerReservation,
    ComputerStatus,
    ComputerReservationStatus,
)
from app.services import session_manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_computer(
    computer_id: int = 1,
    status: ComputerStatus = ComputerStatus.available,
    max_session_minutes: int = 60,
    is_extendable: bool = True,
    max_extensions_per_day: int = 2,
    max_extension_minutes: int = 60,
) -> MagicMock:
    comp = MagicMock(spec=Computer)
    comp.id = computer_id
    comp.status = status
    comp.max_session_minutes = max_session_minutes
    comp.is_extendable = is_extendable
    comp.max_extensions_per_day = max_extensions_per_day
    comp.max_extension_minutes = max_extension_minutes
    return comp


def _make_reservation(
    reservation_id: int = 1,
    computer_id: int = 1,
    patron_id: int = 1,
    status: ComputerReservationStatus = ComputerReservationStatus.in_session,
    extensions_used: int = 0,
    start_offset_minutes: int = -30,
    end_offset_minutes: int = 30,
) -> MagicMock:
    now = datetime.now(timezone.utc)
    res = MagicMock(spec=ComputerReservation)
    res.id = reservation_id
    res.computer_id = computer_id
    res.patron_id = patron_id
    res.status = status
    res.reserved_start_time = now + timedelta(minutes=start_offset_minutes)
    res.reserved_end_time = now + timedelta(minutes=end_offset_minutes)
    res.extensions_used = extensions_used
    res.extended_until = None
    res.extension_requested = False
    res.actual_end_time = None
    return res


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    return db


# ===========================================================================
# start_session
# ===========================================================================


class TestStartSession:
    """Tests for session_manager.start_session."""

    @pytest.mark.asyncio
    async def test_start_session_success(self):
        """Starting a session on an available computer creates a reservation."""
        db = _mock_db()
        computer = _make_computer(computer_id=5, status=ComputerStatus.available)
        db.get.return_value = computer

        _ = await session_manager.start_session(
            db, patron_id=1, computer_id=5, duration_minutes=60
        )

        # Computer status should be switched to in_use
        assert computer.status == ComputerStatus.in_use

        # A reservation was added to the session
        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        assert isinstance(added, ComputerReservation)
        assert added.computer_id == 5
        assert added.patron_id == 1
        assert added.status == ComputerReservationStatus.in_session
        assert added.session_duration_minutes == 60

        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_session_computer_not_found(self):
        """Starting a session on a non-existent computer raises 404."""
        db = _mock_db()
        db.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await session_manager.start_session(db, patron_id=1, computer_id=999)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_start_session_computer_not_available(self):
        """Starting a session on an in-use computer raises 409 Conflict."""
        db = _mock_db()
        computer = _make_computer(computer_id=5, status=ComputerStatus.in_use)
        db.get.return_value = computer

        with pytest.raises(HTTPException) as exc_info:
            await session_manager.start_session(db, patron_id=1, computer_id=5)

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_start_session_duration_capped(self):
        """Duration is capped at computer.max_session_minutes."""
        db = _mock_db()
        computer = _make_computer(
            computer_id=5,
            status=ComputerStatus.available,
            max_session_minutes=30,
        )
        db.get.return_value = computer

        _ = await session_manager.start_session(
            db, patron_id=1, computer_id=5, duration_minutes=120
        )

        # The end time should be at most 30 minutes from start
        added = db.add.call_args[0][0]
        duration = (added.reserved_end_time - added.reserved_start_time).total_seconds() / 60
        assert duration <= 30


# ===========================================================================
# get_current_session
# ===========================================================================


class TestGetCurrentSession:
    """Tests for session_manager.get_current_session."""

    @pytest.mark.asyncio
    async def test_get_current_session_found(self):
        """Returns the active in_session reservation for the patron."""
        db = _mock_db()
        reservation = _make_reservation(patron_id=1)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = reservation
        db.execute.return_value = result_mock

        result = await session_manager.get_current_session(db, patron_id=1)
        assert result is reservation

    @pytest.mark.asyncio
    async def test_get_current_session_none(self):
        """Returns None when the patron has no active session."""
        db = _mock_db()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        result = await session_manager.get_current_session(db, patron_id=1)
        assert result is None


# ===========================================================================
# extend_session
# ===========================================================================


class TestExtendSession:
    """Tests for session_manager.extend_session."""

    @pytest.mark.asyncio
    async def test_extend_session_success(self):
        """Extending a session updates the end time and increments extensions_used."""
        # session_manager.extend_session queries the reservation itself
        # (with_for_update, to lock against concurrent extension) rather
        # than delegating to get_current_session, so the mock must configure
        # db.execute directly -- patching get_current_session has no effect
        # here (see TestGetCurrentSession above for where that patch target
        # would actually apply).
        db = _mock_db()
        reservation = _make_reservation(patron_id=1, extensions_used=0)
        computer = _make_computer(
            computer_id=1,
            is_extendable=True,
            max_extensions_per_day=2,
            max_extension_minutes=60,
        )

        original_end = reservation.reserved_end_time

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = reservation
        db.execute.return_value = result_mock
        db.get.return_value = computer

        _ = await session_manager.extend_session(
            db, patron_id=1, extra_minutes=30
        )

        expected_end = original_end + timedelta(minutes=30)
        assert reservation.reserved_end_time == expected_end
        assert reservation.extended_until == expected_end
        assert reservation.extensions_used == 1
        assert reservation.extension_requested is True

        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_extend_session_no_active_session(self):
        """Extending when there is no active session raises 404."""
        db = _mock_db()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc_info:
            await session_manager.extend_session(db, patron_id=1)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_extend_session_limit_exceeded(self):
        """Extending beyond max_extensions_per_day raises 400."""
        db = _mock_db()
        reservation = _make_reservation(patron_id=1, extensions_used=2)
        computer = _make_computer(
            computer_id=1,
            is_extendable=True,
            max_extensions_per_day=2,
        )

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = reservation
        db.execute.return_value = result_mock
        db.get.return_value = computer

        with pytest.raises(HTTPException) as exc_info:
            await session_manager.extend_session(db, patron_id=1)

        assert exc_info.value.status_code == 400
        assert "maximum" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_extend_session_not_extendable(self):
        """Extending on a non-extendable computer raises 400."""
        db = _mock_db()
        reservation = _make_reservation(patron_id=1, extensions_used=0)
        computer = _make_computer(computer_id=1, is_extendable=False)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = reservation
        db.execute.return_value = result_mock
        db.get.return_value = computer

        with pytest.raises(HTTPException) as exc_info:
            await session_manager.extend_session(db, patron_id=1)

        assert exc_info.value.status_code == 400


# ===========================================================================
# end_session
# ===========================================================================


class TestEndSession:
    """Tests for session_manager.end_session."""

    @pytest.mark.asyncio
    async def test_end_session_success(self):
        """Ending a session sets status to completed and frees the computer."""
        # session_manager.end_session queries both the reservation and the
        # computer itself (each with_for_update, to lock rows before
        # mutating them) rather than delegating to get_current_session /
        # db.get, so db.execute needs two distinct results in sequence.
        db = _mock_db()
        reservation = _make_reservation(patron_id=1, computer_id=3)
        computer = _make_computer(computer_id=3, status=ComputerStatus.in_use)

        reservation_result = MagicMock()
        reservation_result.scalar_one_or_none.return_value = reservation
        computer_result = MagicMock()
        computer_result.scalar_one_or_none.return_value = computer
        db.execute.side_effect = [reservation_result, computer_result]

        _ = await session_manager.end_session(db, patron_id=1)

        assert reservation.status == ComputerReservationStatus.completed
        assert reservation.actual_end_time is not None
        assert computer.status == ComputerStatus.available

        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_end_session_no_active_session(self):
        """Ending when there is no active session raises 404."""
        db = _mock_db()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc_info:
            await session_manager.end_session(db, patron_id=1)

        assert exc_info.value.status_code == 404


# ===========================================================================
# expire_sessions
# ===========================================================================


class TestExpireSessions:
    """Tests for session_manager.expire_sessions."""

    @pytest.mark.asyncio
    async def test_expire_sessions_marks_overdue(self):
        """Expired sessions are marked completed and computers freed."""
        db = _mock_db()

        _ = datetime.now(timezone.utc)
        r1 = _make_reservation(
            reservation_id=1,
            computer_id=1,
            status=ComputerReservationStatus.in_session,
            end_offset_minutes=-10,  # ended 10 min ago
        )
        r2 = _make_reservation(
            reservation_id=2,
            computer_id=2,
            status=ComputerReservationStatus.in_session,
            end_offset_minutes=-5,  # ended 5 min ago
        )

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [r1, r2]
        result_mock.scalars.return_value = scalars_mock

        comp1 = _make_computer(computer_id=1, status=ComputerStatus.in_use)
        comp2 = _make_computer(computer_id=2, status=ComputerStatus.in_use)
        comp1_result = MagicMock()
        comp1_result.scalar_one_or_none.return_value = comp1
        comp2_result = MagicMock()
        comp2_result.scalar_one_or_none.return_value = comp2

        # expire_sessions issues one execute() for the expired-reservations
        # query, then one more execute() per reservation to lock/fetch its
        # computer (it does not use db.get for this).
        db.execute.side_effect = [result_mock, comp1_result, comp2_result]

        count = await session_manager.expire_sessions(db)

        assert count == 2
        assert r1.status == ComputerReservationStatus.completed
        assert r2.status == ComputerReservationStatus.completed
        assert comp1.status == ComputerStatus.available
        assert comp2.status == ComputerStatus.available

        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_expire_sessions_none_expired(self):
        """When no sessions are expired, count is 0 and no commit occurs."""
        db = _mock_db()

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        count = await session_manager.expire_sessions(db)

        assert count == 0
        db.commit.assert_not_awaited()
