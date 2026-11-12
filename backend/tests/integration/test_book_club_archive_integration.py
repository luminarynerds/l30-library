# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for book club discussion archive + Postgres FTS search.

Requires a live Postgres backend (skips on SQLite fallback) because the
search path uses ``tsvector``, ``plainto_tsquery``, ``ts_headline``,
``ts_rank`` and the BEFORE INSERT/UPDATE trigger created in
``20260519_bc_archive_001_book_club_discussion_archive.py``.

The archive endpoints + non-FTS service paths are covered by the
service-level unit tests in
``backend/tests/services/test_book_club_archive_service.py``.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.book_club import (
    BookClub,
    BookClubDiscussion,
    BookClubMeeting,
    BookClubMember,
    BookClubRole,
    BookClubStatus,
    DiscussionStatus,
)
from app.models.user import User, UserRole
from app.models.organization_features import OrganizationFeatures
from app.services import book_club_service


_IS_SQLITE = "sqlite" in os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    _IS_SQLITE,
    reason="Discussion archive search uses Postgres FTS (tsvector/ts_headline); "
    "SQLite fallback can't exercise it.",
)


async def _enable_history_flag(test_db):
    """Ensure the singleton OrganizationFeatures row has the flag on."""
    result = await test_db.execute(select(OrganizationFeatures).limit(1))
    feat = result.scalars().first()
    if feat is None:
        feat = OrganizationFeatures(book_club_history_enabled=True)
        test_db.add(feat)
    else:
        feat.book_club_history_enabled = True
    await test_db.commit()


async def _make_user(test_db, role: UserRole = UserRole.STAFF, *, first="Sam") -> User:
    unique = uuid.uuid4().hex[:8]
    u = User(
        email=f"{role.value}-{unique}@archive-test.local",
        password_hash="x",
        first_name=first,
        last_name="Tester",
        role=role,
        is_active=True,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u


async def _make_club_with_meetings(test_db, creator: User):
    club = BookClub(
        name=f"Test Club {uuid.uuid4().hex[:6]}",
        description="archive test",
        created_by_id=creator.id,
        status=BookClubStatus.active,
        is_public=True,
    )
    test_db.add(club)
    await test_db.flush()

    active = BookClubMeeting(
        book_club_id=club.id,
        title="Active May Meeting",
        meeting_date=datetime.now(timezone.utc) + timedelta(days=7),
        status=DiscussionStatus.planned,
        is_archived=False,
    )
    archived = BookClubMeeting(
        book_club_id=club.id,
        title="Archived January Meeting",
        meeting_date=datetime.now(timezone.utc) - timedelta(days=120),
        status=DiscussionStatus.completed,
        is_archived=True,
    )
    test_db.add_all([active, archived])
    await test_db.commit()
    await test_db.refresh(active)
    await test_db.refresh(archived)
    return club, active, archived


@pytest.mark.integration
async def test_archive_unarchive_flips_flag(test_db):
    creator = await _make_user(test_db)
    _, active, _ = await _make_club_with_meetings(test_db, creator)
    assert active.is_archived is False

    await book_club_service.archive_meeting(active.id, test_db)
    refreshed = await test_db.get(BookClubMeeting, active.id)
    assert refreshed.is_archived is True

    await book_club_service.unarchive_meeting(active.id, test_db)
    refreshed = await test_db.get(BookClubMeeting, active.id)
    assert refreshed.is_archived is False


@pytest.mark.integration
async def test_search_finds_discussion_in_active_meeting(test_db):
    creator = await _make_user(test_db)
    club, active, _ = await _make_club_with_meetings(test_db, creator)

    discussion = BookClubDiscussion(
        meeting_id=active.id,
        user_id=creator.id,
        author_display_name="Sam Calder",
        title="Beloved discussion",
        body="Toni Morrison's Beloved is a haunting novel about memory.",
    )
    test_db.add(discussion)
    await test_db.commit()

    hits = await book_club_service.search_discussions(
        club_id=club.id,
        q="beloved",
        db=test_db,
    )

    assert len(hits) >= 1
    found = next((h for h in hits if h["id"] == discussion.id), None)
    assert found is not None
    assert "Beloved" in found["snippet"] or "beloved" in found["snippet"].lower()
    assert found["rank"] > 0
    assert found["meeting_is_archived"] is False


@pytest.mark.integration
async def test_search_excludes_archived_by_default_includes_when_opted_in(test_db):
    creator = await _make_user(test_db)
    club, active, archived = await _make_club_with_meetings(test_db, creator)

    test_db.add_all(
        [
            BookClubDiscussion(
                meeting_id=active.id,
                user_id=creator.id,
                author_display_name="A. Author",
                title="Pickles",
                body="We talked about pickles in May.",
            ),
            BookClubDiscussion(
                meeting_id=archived.id,
                user_id=creator.id,
                author_display_name="A. Author",
                title="Pickles",
                body="The January meeting also covered pickles.",
            ),
        ]
    )
    await test_db.commit()

    active_only = await book_club_service.search_discussions(
        club_id=club.id,
        q="pickles",
        db=test_db,
        include_archived=False,
    )
    assert active_only and all(not h["meeting_is_archived"] for h in active_only)

    everything = await book_club_service.search_discussions(
        club_id=club.id,
        q="pickles",
        db=test_db,
        include_archived=True,
    )
    archived_titles = [h["meeting_title"] for h in everything if h["meeting_is_archived"]]
    assert "Archived January Meeting" in archived_titles


@pytest.mark.integration
async def test_search_respects_date_filters(test_db):
    creator = await _make_user(test_db)
    club, active, archived = await _make_club_with_meetings(test_db, creator)

    test_db.add_all(
        [
            BookClubDiscussion(
                meeting_id=active.id,
                user_id=creator.id,
                author_display_name="A",
                title="Bananas",
                body="banana banana",
            ),
            BookClubDiscussion(
                meeting_id=archived.id,
                user_id=creator.id,
                author_display_name="B",
                title="Bananas",
                body="banana banana",
            ),
        ]
    )
    await test_db.commit()

    # Date window covering only the future active meeting
    df = datetime.now(timezone.utc) + timedelta(days=1)
    dt = datetime.now(timezone.utc) + timedelta(days=30)

    hits = await book_club_service.search_discussions(
        club_id=club.id,
        q="bananas",
        db=test_db,
        include_archived=True,
        date_from=df,
        date_to=dt,
    )

    assert hits
    # All hits must be from the active (future) meeting, not the archived past one
    assert all(h["meeting_id"] == active.id for h in hits)


@pytest.mark.integration
async def test_search_limit_caps_at_50(test_db):
    creator = await _make_user(test_db)
    club, active, _ = await _make_club_with_meetings(test_db, creator)

    test_db.add_all(
        [
            BookClubDiscussion(
                meeting_id=active.id,
                user_id=creator.id,
                author_display_name=f"User{i}",
                title=f"Title {i}",
                body=f"watermelon {i} watermelon",
            )
            for i in range(60)
        ]
    )
    await test_db.commit()

    hits = await book_club_service.search_discussions(
        club_id=club.id,
        q="watermelon",
        db=test_db,
    )
    assert len(hits) <= 50
