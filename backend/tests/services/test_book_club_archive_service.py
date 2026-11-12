# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for book-club discussion archive + search service layer.

Mocks ``db.execute()`` to avoid a live Postgres dependency for the
pure-Python branches (archive/unarchive, filter selection, patron
guard). A separate integration test (test_book_club_archive_integration.py)
exercises the actual Postgres tsvector search.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ResourceNotFoundError
from app.services import book_club_service


def _meeting(meeting_id=42, book_club_id=1, is_archived=False):
    return SimpleNamespace(
        id=meeting_id,
        book_club_id=book_club_id,
        title=f"Meeting {meeting_id}",
        is_archived=is_archived,
        meeting_date=datetime.now(timezone.utc),
    )


def _stub_single(obj):
    """Stub a db.execute() that returns a single .scalars().first() value."""
    result = MagicMock()
    result.scalars.return_value.first.return_value = obj
    return result


@pytest.mark.asyncio
async def test_archive_meeting_sets_is_archived_true():
    meeting = _meeting(is_archived=False)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_stub_single(meeting))

    out = await book_club_service.archive_meeting(meeting.id, db)

    assert out is meeting
    assert meeting.is_archived is True
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(meeting)


@pytest.mark.asyncio
async def test_archive_meeting_raises_when_missing():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_stub_single(None))

    with pytest.raises(ResourceNotFoundError):
        await book_club_service.archive_meeting(meeting_id=999, db=db)


@pytest.mark.asyncio
async def test_unarchive_meeting_flips_flag():
    meeting = _meeting(is_archived=True)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_stub_single(meeting))

    await book_club_service.unarchive_meeting(meeting.id, db)

    assert meeting.is_archived is False


@pytest.mark.asyncio
async def test_unarchive_meeting_raises_when_missing():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_stub_single(None))

    with pytest.raises(ResourceNotFoundError):
        await book_club_service.unarchive_meeting(meeting_id=999, db=db)


@pytest.mark.asyncio
async def test_search_discussions_short_circuits_on_empty_query():
    db = AsyncMock()
    out = await book_club_service.search_discussions(
        club_id=1, q="", db=db,
    )
    assert out == []
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_search_discussions_short_circuits_on_whitespace_query():
    db = AsyncMock()
    out = await book_club_service.search_discussions(
        club_id=1, q="   ", db=db,
    )
    assert out == []
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_search_discussions_excludes_archived_by_default():
    """When include_archived=False the SQL must filter on is_archived=false."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(mappings=MagicMock(return_value=[])))

    await book_club_service.search_discussions(
        club_id=1, q="beloved", db=db, include_archived=False,
    )

    db.execute.assert_awaited_once()
    sent_sql = str(db.execute.await_args[0][0])
    assert "m.is_archived = false" in sent_sql


@pytest.mark.asyncio
async def test_search_discussions_includes_archived_when_opted_in():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(mappings=MagicMock(return_value=[])))

    await book_club_service.search_discussions(
        club_id=1, q="beloved", db=db, include_archived=True,
    )

    sent_sql = str(db.execute.await_args[0][0])
    assert "m.is_archived = false" not in sent_sql


@pytest.mark.asyncio
async def test_search_discussions_applies_date_range():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(mappings=MagicMock(return_value=[])))
    df = datetime(2025, 1, 1, tzinfo=timezone.utc)
    dt = datetime(2025, 12, 31, tzinfo=timezone.utc)

    await book_club_service.search_discussions(
        club_id=1, q="beloved", db=db,
        date_from=df, date_to=dt,
    )

    sent_sql = str(db.execute.await_args[0][0])
    sent_params = db.execute.await_args[0][1]
    assert "m.meeting_date >= :date_from" in sent_sql
    assert "m.meeting_date <= :date_to" in sent_sql
    assert sent_params["date_from"] is df
    assert sent_params["date_to"] is dt


@pytest.mark.asyncio
async def test_search_discussions_maps_rows_to_dicts():
    """Verifies the row -> dict mapping (None rank -> 0.0, blank fields)."""
    row = {
        "id": 7,
        "meeting_id": 42,
        "meeting_title": "May Meeting",
        "meeting_scheduled_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
        "meeting_is_archived": True,
        "author_display_name": None,
        "created_at": datetime(2026, 5, 2, tzinfo=timezone.utc),
        "snippet": "<b>beloved</b> by Morrison",
        "rank": 0.987,
    }
    db = AsyncMock()
    result = MagicMock()
    result.mappings.return_value = [row]
    db.execute = AsyncMock(return_value=result)

    out = await book_club_service.search_discussions(
        club_id=1, q="beloved", db=db, include_archived=True,
    )

    assert len(out) == 1
    hit = out[0]
    assert hit["id"] == 7
    assert hit["meeting_id"] == 42
    assert hit["author_display_name"] == ""  # None coerced to ""
    assert hit["snippet"] == "<b>beloved</b> by Morrison"
    assert hit["rank"] == pytest.approx(0.987)
    assert hit["meeting_is_archived"] is True


@pytest.mark.asyncio
async def test_search_discussions_default_limit_capped_at_50():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(mappings=MagicMock(return_value=[])))

    await book_club_service.search_discussions(club_id=1, q="x", db=db)

    sent_params = db.execute.await_args[0][1]
    assert sent_params["limit"] == 50
