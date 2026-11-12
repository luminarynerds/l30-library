# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for waitlist_service.

Tests cover:
- Joining a computer waitlist (success and duplicate handling)
- Getting a patron's waitlist position
- Advancing the waitlist when a computer becomes available
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.models.computer import ComputerWaitlist, ComputerWaitlistStatus
from app.services import waitlist_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_waitlist_entry(
    entry_id: int = 1,
    computer_id: int = 1,
    patron_id: int = 1,
    queue_position: int = 1,
    status: ComputerWaitlistStatus = ComputerWaitlistStatus.pending,
) -> MagicMock:
    now = datetime.now(timezone.utc)
    entry = MagicMock(spec=ComputerWaitlist)
    entry.id = entry_id
    entry.computer_id = computer_id
    entry.patron_id = patron_id
    entry.queue_position = queue_position
    entry.status = status
    entry.desired_start_time = now
    entry.desired_duration_minutes = 60
    entry.created_at = now
    entry.expires_at = now + timedelta(hours=24)
    entry.notified_at = None
    entry.notification_method = None
    return entry


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    return db


# ===========================================================================
# join_waitlist
# ===========================================================================


class TestJoinWaitlist:
    """Tests for waitlist_service.join_waitlist."""

    @pytest.mark.asyncio
    async def test_join_waitlist_success(self):
        """A patron can join the waitlist for a computer and gets position max+1."""
        db = _mock_db()

        # First execute: check for existing entry -> None
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        # Second execute: get max queue_position -> 3
        max_result = MagicMock()
        max_result.scalar.return_value = 3

        db.execute.side_effect = [existing_result, max_result]

        _ = await waitlist_service.join_waitlist(
            db, patron_id=1, computer_id=5, desired_duration_minutes=60
        )

        # A new entry should have been added
        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        assert isinstance(added, ComputerWaitlist)
        assert added.computer_id == 5
        assert added.patron_id == 1
        assert added.queue_position == 4  # max(3) + 1
        assert added.status == ComputerWaitlistStatus.pending
        assert added.desired_duration_minutes == 60

        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_join_waitlist_first_in_queue(self):
        """When the waitlist is empty, patron gets position 1."""
        db = _mock_db()

        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        max_result = MagicMock()
        max_result.scalar.return_value = None  # No entries -> returns None

        db.execute.side_effect = [existing_result, max_result]

        _ = await waitlist_service.join_waitlist(
            db, patron_id=1, computer_id=5
        )

        added = db.add.call_args[0][0]
        assert added.queue_position == 1  # None or 0 -> 0 + 1 = 1

    @pytest.mark.asyncio
    async def test_join_waitlist_already_on_waitlist(self):
        """Joining the same waitlist again raises 409 Conflict."""
        db = _mock_db()

        existing_entry = _make_waitlist_entry(patron_id=1, computer_id=5)
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = existing_entry

        db.execute.return_value = existing_result

        with pytest.raises(HTTPException) as exc_info:
            await waitlist_service.join_waitlist(
                db, patron_id=1, computer_id=5
            )

        assert exc_info.value.status_code == 409
        assert "already on waitlist" in exc_info.value.detail.lower()


# ===========================================================================
# get_position
# ===========================================================================


class TestGetPosition:
    """Tests for waitlist_service.get_position."""

    @pytest.mark.asyncio
    async def test_get_position_found(self):
        """Returns the waitlist entry when patron is on a waitlist."""
        db = _mock_db()
        entry = _make_waitlist_entry(patron_id=1, computer_id=5, queue_position=2)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = entry
        db.execute.return_value = result_mock

        result = await waitlist_service.get_position(
            db, patron_id=1, computer_id=5
        )

        assert result is entry
        assert result.queue_position == 2

    @pytest.mark.asyncio
    async def test_get_position_not_found(self):
        """Returns None when patron is not on any waitlist."""
        db = _mock_db()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        result = await waitlist_service.get_position(db, patron_id=1)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_position_without_computer_filter(self):
        """get_position works without specifying computer_id."""
        db = _mock_db()
        entry = _make_waitlist_entry(patron_id=1, computer_id=3)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = entry
        db.execute.return_value = result_mock

        result = await waitlist_service.get_position(db, patron_id=1)
        assert result is entry


# ===========================================================================
# advance_waitlist
# ===========================================================================


class TestAdvanceWaitlist:
    """Tests for waitlist_service.advance_waitlist."""

    @pytest.mark.asyncio
    async def test_advance_waitlist_notifies_next(self):
        """Advancing the waitlist notifies the next pending patron."""
        db = _mock_db()
        entry = _make_waitlist_entry(
            entry_id=10, patron_id=42, computer_id=5, queue_position=1
        )

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = entry
        db.execute.return_value = result_mock

        result = await waitlist_service.advance_waitlist(db, computer_id=5)

        assert result is entry
        assert entry.status == ComputerWaitlistStatus.notified
        assert entry.notified_at is not None
        assert entry.notification_method == "in_person"

        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_advance_waitlist_empty(self):
        """Advancing an empty waitlist returns None and does not commit."""
        db = _mock_db()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        result = await waitlist_service.advance_waitlist(db, computer_id=5)

        assert result is None
        db.commit.assert_not_awaited()
