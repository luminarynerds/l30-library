# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the patron-side discussion stubs that became persistent.

Covers:
  * list_discussions filters by meeting + non-archived
  * list_discussions returns [] for archived meetings
  * create_discussion blocks writes to archived meetings (returns id=0
    placeholder, no db.add)
  * get_club_detail hides archived meetings from upcoming_meetings
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.book_club import DiscussionStatus
from app.services.book_club_patron_service import BookClubPatronService


def _meeting_obj(meeting_id=42, club_id=1, is_archived=False):
    return SimpleNamespace(
        id=meeting_id,
        book_club_id=club_id,
        is_archived=is_archived,
        meeting_date=datetime.now(timezone.utc),
    )


def _stub_first(value):
    r = MagicMock()
    r.scalars.return_value.first.return_value = value
    return r


def _stub_all(values):
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
    return r


@pytest.mark.asyncio
async def test_list_discussions_returns_empty_when_meeting_archived():
    db = AsyncMock()
    # Sanity check returns None because is_archived filter excludes it
    db.execute = AsyncMock(side_effect=[_stub_first(None)])

    out = await BookClubPatronService.list_discussions(
        club_id=1,
        meeting_id=42,
        db=db,
    )

    assert out == []
    # Should NOT have made the follow-up SELECT for discussions.
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_list_discussions_returns_threads_for_active_meeting():
    meeting = _meeting_obj(meeting_id=42, is_archived=False)
    thread = SimpleNamespace(
        id=7,
        meeting_id=42,
        user_id=99,
        author_display_name="Sam C.",
        title="First impressions",
        body="I loved the prologue.",
        created_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        is_pinned=False,
    )
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _stub_first(meeting),
            _stub_all([thread]),
        ]
    )

    out = await BookClubPatronService.list_discussions(
        club_id=1,
        meeting_id=42,
        db=db,
    )

    assert len(out) == 1
    assert out[0].id == 7
    assert out[0].title == "First impressions"
    assert out[0].author_name == "Sam C."


@pytest.mark.asyncio
async def test_create_discussion_blocks_when_meeting_archived():
    """Returns a placeholder DiscussionThread without persisting."""
    archived = _meeting_obj(meeting_id=42, is_archived=True)
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_stub_first(archived))

    out = await BookClubPatronService.create_discussion(
        club_id=1,
        meeting_id=42,
        user_id=99,
        title="hi",
        content="body",
        db=db,
    )

    # Placeholder returned; nothing was added/committed
    assert out.id == 0
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_discussion_persists_for_active_meeting():
    active = _meeting_obj(meeting_id=42, is_archived=False)
    user = SimpleNamespace(
        id=99,
        first_name="Sam",
        last_name="Calder",
        email="sam@example.org",
    )

    # After db.refresh, simulate the columns that the DB would populate
    # (server-default for is_pinned, server_default + onupdate for
    # created_at, and the SERIAL primary key).
    def _refresh_side_effect(obj):
        obj.id = 123
        obj.created_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
        obj.is_pinned = False
        return None

    db = AsyncMock()
    # db.add() is sync in SQLAlchemy; AsyncMock would make it a coroutine.
    db.add = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _stub_first(active),  # meeting lookup
            _stub_first(user),  # user lookup for display name
        ]
    )
    db.refresh = AsyncMock(side_effect=_refresh_side_effect)

    out = await BookClubPatronService.create_discussion(
        club_id=1,
        meeting_id=42,
        user_id=99,
        title="hi",
        content="body",
        db=db,
    )

    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    assert out.id == 123
    assert out.author_name == "Sam Calder"


@pytest.mark.asyncio
async def test_get_club_detail_hides_archived_meetings():
    """Archived meetings must never appear in patron upcoming_meetings."""
    future = datetime.now(timezone.utc) + timedelta(days=7)
    active = SimpleNamespace(
        id=1,
        title="Active meeting",
        meeting_date=future,
        location=None,
        status=DiscussionStatus.planned,
        is_archived=False,
    )
    archived = SimpleNamespace(
        id=2,
        title="Archived meeting",
        meeting_date=future,
        location=None,
        status=DiscussionStatus.planned,
        is_archived=True,
    )
    member = SimpleNamespace(
        id=10,
        user_id=99,
        joined_at=datetime.now(timezone.utc),
        role=SimpleNamespace(value="member"),
        user=SimpleNamespace(first_name="Sam", last_name="C", email="s@x"),
    )
    club = SimpleNamespace(
        id=1,
        name="Club",
        description="",
        meeting_frequency="monthly",
        max_members=None,
        created_at=datetime.now(timezone.utc),
        members=[member],
        meetings=[active, archived],
    )

    result = MagicMock()
    result.unique.return_value.scalars.return_value.first.return_value = club
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)

    detail = await BookClubPatronService.get_club_detail(
        club_id=1,
        user_id=99,
        db=db,
    )

    assert detail is not None
    titles = [m.title for m in detail.upcoming_meetings]
    assert "Active meeting" in titles
    assert "Archived meeting" not in titles
