# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for BookClubPatronService.list_clubs current_book + next_meeting wiring.

Mocks db.execute() to avoid a live Postgres dependency; we are exercising the
in-memory aggregation (current_book/next_meeting derivation) over a stub club
with stub meetings + catalog_items.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.book_club import BookClubStatus, DiscussionStatus
from app.services.book_club_patron_service import BookClubPatronService


def _make_meeting(meeting_date, status=DiscussionStatus.planned, catalog_item=None):
    return SimpleNamespace(
        meeting_date=meeting_date,
        status=status,
        catalog_item=catalog_item,
    )


def _make_club(meetings, name="Test Club"):
    return SimpleNamespace(
        id=1,
        name=name,
        description="A club",
        genre="fiction",
        meeting_frequency="monthly",
        max_members=20,
        members=[],
        meetings=meetings,
    )


def _stub_db_for(clubs, total=None):
    """Build an AsyncMock db whose .execute() returns count then clubs in order."""
    db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar.return_value = total if total is not None else len(clubs)
    clubs_result = MagicMock()
    # .unique().scalars().all() chain
    clubs_result.unique.return_value.scalars.return_value.all.return_value = clubs
    db.execute = AsyncMock(side_effect=[count_result, clubs_result])
    return db


@pytest.mark.asyncio
async def test_list_clubs_populates_current_book_from_upcoming_meeting():
    now = datetime.now(timezone.utc)
    catalog = SimpleNamespace(title="Beloved", author="Toni Morrison")
    upcoming = _make_meeting(now + timedelta(days=7), catalog_item=catalog)
    club = _make_club([upcoming])
    db = _stub_db_for([club])

    resp = await BookClubPatronService.list_clubs(db=db)

    assert len(resp.clubs) == 1
    item = resp.clubs[0]
    assert item.current_book_title == "Beloved"
    assert item.current_book_author == "Toni Morrison"
    assert item.next_meeting_date is not None
    assert item.next_meeting_date > now


@pytest.mark.asyncio
async def test_list_clubs_falls_back_to_most_recent_past_meeting_for_current_book():
    now = datetime.now(timezone.utc)
    old_catalog = SimpleNamespace(title="Old Book", author="Old Author")
    recent_catalog = SimpleNamespace(title="Recent Book", author="Recent Author")
    older = _make_meeting(
        now - timedelta(days=30),
        status=DiscussionStatus.completed,
        catalog_item=old_catalog,
    )
    more_recent = _make_meeting(
        now - timedelta(days=2),
        status=DiscussionStatus.completed,
        catalog_item=recent_catalog,
    )
    club = _make_club([older, more_recent])
    db = _stub_db_for([club])

    resp = await BookClubPatronService.list_clubs(db=db)

    item = resp.clubs[0]
    # No upcoming meetings, so falls back to most-recent past with a catalog_item
    assert item.current_book_title == "Recent Book"
    assert item.current_book_author == "Recent Author"
    # No upcoming meeting => no next_meeting_date
    assert item.next_meeting_date is None


@pytest.mark.asyncio
async def test_list_clubs_omits_current_book_when_no_meeting_has_catalog_item():
    now = datetime.now(timezone.utc)
    upcoming_no_book = _make_meeting(now + timedelta(days=3), catalog_item=None)
    club = _make_club([upcoming_no_book])
    db = _stub_db_for([club])

    resp = await BookClubPatronService.list_clubs(db=db)

    item = resp.clubs[0]
    assert item.current_book_title is None
    assert item.current_book_author is None
    # Next meeting itself is still surfaced even without a book
    assert item.next_meeting_date is not None


@pytest.mark.asyncio
async def test_list_clubs_prefers_upcoming_with_book_over_past_with_book():
    now = datetime.now(timezone.utc)
    past_catalog = SimpleNamespace(title="Past Pick", author="Past Author")
    future_catalog = SimpleNamespace(title="Next Pick", author="Future Author")
    past = _make_meeting(
        now - timedelta(days=10),
        status=DiscussionStatus.completed,
        catalog_item=past_catalog,
    )
    future = _make_meeting(now + timedelta(days=10), catalog_item=future_catalog)
    club = _make_club([past, future])
    db = _stub_db_for([club])

    resp = await BookClubPatronService.list_clubs(db=db)

    item = resp.clubs[0]
    assert item.current_book_title == "Next Pick"
    assert item.current_book_author == "Future Author"
