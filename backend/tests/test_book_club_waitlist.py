# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Backend tests for the book-club waitlist + capacity-signals feature.

These exercise the SERVICE layer against the real Postgres test DB
(``l30_test``) — the waitlist logic depends on Postgres-specific
behaviour (``FOR UPDATE SKIP LOCKED`` in promote, the
``uq_waitlist_club_user`` unique constraint, scalar COUNT capacity
checks) that a mocked session would not validate.

Run via per-test process isolation (the conftest singleton-engine /
function-loop trap mass-fails a plain suite run after test 1 — that is
a harness artifact, not a regression). See
``feedback_l30_conftest_singleton_engine_loop_trap``.
"""
import uuid

import pytest

from app.models.book_club import (
    BookClub,
    BookClubMember,
    BookClubRole,
    BookClubStatus,
    BookClubWaitlistEntry,
)
from app.models.user import User, UserRole
from app.services import book_club_service
from app.services.book_club_patron_service import BookClubPatronService


async def _make_user(db, *, role=UserRole.PATRON):
    """Create a persisted user with a unique email."""
    u = User(
        email=f"wl-{uuid.uuid4().hex[:12]}@example.com",
        password_hash="x",
        first_name="Way",
        last_name="Lister",
        role=role,
        is_active=True,
        email_verified=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


async def _make_club(db, *, max_members):
    club = BookClub(
        name=f"Club {uuid.uuid4().hex[:8]}",
        description="t",
        max_members=max_members,
        is_public=True,
        status=BookClubStatus.active,
    )
    db.add(club)
    await db.commit()
    await db.refresh(club)
    return club


async def _add_member(db, club_id, user_id):
    db.add(
        BookClubMember(
            book_club_id=club_id,
            user_id=user_id,
            role=BookClubRole.member,
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_join_full_club_routes_to_waitlist(db):
    club = await _make_club(db, max_members=1)
    seat_holder = await _make_user(db)
    await _add_member(db, club.id, seat_holder.id)

    latecomer = await _make_user(db)
    result = await BookClubPatronService.join_club(
        club_id=club.id, user_id=latecomer.id, db=db
    )

    assert result["status"] == "waitlisted"
    assert result["position"] == 1
    # No membership row was created for the latecomer.
    member_count = await book_club_service.get_member_count(club.id, db)
    assert member_count == 1
    assert await book_club_service.get_waitlist_count(club.id, db) == 1


@pytest.mark.asyncio
async def test_join_waitlist_twice_returns_409(db):
    club = await _make_club(db, max_members=1)
    holder = await _make_user(db)
    await _add_member(db, club.id, holder.id)
    patron = await _make_user(db)

    first = await BookClubPatronService.join_club(
        club_id=club.id, user_id=patron.id, db=db
    )
    assert first["status"] == "waitlisted"

    second = await BookClubPatronService.join_club(
        club_id=club.id, user_id=patron.id, db=db
    )
    # App-layer guard returns already_waitlisted (the 409 path in the
    # endpoint) BEFORE the uq_waitlist_club_user constraint would fire.
    assert second["status"] == "already_waitlisted"
    assert second["position"] == 1
    assert await book_club_service.get_waitlist_count(club.id, db) == 1


@pytest.mark.asyncio
async def test_leave_member_promotes_next_waitlist_patron(db):
    club = await _make_club(db, max_members=1)
    holder = await _make_user(db)
    await _add_member(db, club.id, holder.id)
    waiter = await _make_user(db)
    await BookClubPatronService.add_to_waitlist(
        club_id=club.id, user_id=waiter.id, db=db
    )
    assert await book_club_service.get_waitlist_count(club.id, db) == 1

    left = await BookClubPatronService.leave_club(
        club_id=club.id, user_id=holder.id, db=db
    )
    assert left is True

    # Waiter was auto-promoted into the freed seat.
    assert await book_club_service.get_member_count(club.id, db) == 1
    assert await book_club_service.get_waitlist_count(club.id, db) == 0
    promoted = await db.scalar(
        BookClubMember.__table__.select().where(
            BookClubMember.book_club_id == club.id,
            BookClubMember.user_id == waiter.id,
        )
    )
    assert promoted is not None


@pytest.mark.asyncio
async def test_promote_sends_email(db, monkeypatch):
    sent = {}

    async def _fake_send(user, club):
        sent["email"] = user.email
        sent["club"] = club.id
        return True

    monkeypatch.setattr(
        "app.core.email.send_waitlist_promotion_email", _fake_send
    )

    club = await _make_club(db, max_members=1)
    holder = await _make_user(db)
    await _add_member(db, club.id, holder.id)
    waiter = await _make_user(db)
    await BookClubPatronService.add_to_waitlist(
        club_id=club.id, user_id=waiter.id, db=db
    )

    await BookClubPatronService.leave_club(
        club_id=club.id, user_id=holder.id, db=db
    )

    assert sent.get("email") == waiter.email
    assert sent.get("club") == club.id


@pytest.mark.asyncio
async def test_archive_club_clears_waitlist(db, monkeypatch):
    notices = []

    async def _fake_notice(user, club):
        notices.append(user.email)
        return True

    monkeypatch.setattr(
        "app.core.email.send_waitlist_archived_notice_email", _fake_notice
    )

    club = await _make_club(db, max_members=1)
    holder = await _make_user(db)
    await _add_member(db, club.id, holder.id)
    w1 = await _make_user(db)
    w2 = await _make_user(db)
    await BookClubPatronService.add_to_waitlist(
        club_id=club.id, user_id=w1.id, db=db
    )
    await BookClubPatronService.add_to_waitlist(
        club_id=club.id, user_id=w2.id, db=db
    )
    assert await book_club_service.get_waitlist_count(club.id, db) == 2

    notified = await book_club_service.archive_book_club_with_waitlist(
        club.id, db
    )
    await db.commit()

    assert notified == 2
    assert sorted(notices) == sorted([w1.email, w2.email])
    assert await book_club_service.get_waitlist_count(club.id, db) == 0
    refreshed = await db.get(BookClub, club.id)
    assert refreshed.status == BookClubStatus.archived


@pytest.mark.asyncio
async def test_capacity_increase_auto_promotes(db):
    club = await _make_club(db, max_members=1)
    holder = await _make_user(db)
    await _add_member(db, club.id, holder.id)
    w1 = await _make_user(db)
    w2 = await _make_user(db)
    w3 = await _make_user(db)
    for w in (w1, w2, w3):
        await BookClubPatronService.add_to_waitlist(
            club_id=club.id, user_id=w.id, db=db
        )
    assert await book_club_service.get_waitlist_count(club.id, db) == 3

    # Mirror the real endpoint flow: update_book_club() persists the new
    # max_members (commit) BEFORE invoking the auto-promote hook, so the
    # club row already reflects the new cap when promote re-checks it.
    club.max_members = 3
    await db.commit()

    # Raise cap 1 -> 3: exactly 2 freed seats, 2 promotions (FIFO).
    promoted = await book_club_service.auto_promote_on_capacity_increase(
        club.id, old_max=1, new_max=3, db=db
    )
    await db.commit()

    assert promoted == 2
    assert await book_club_service.get_member_count(club.id, db) == 3
    assert await book_club_service.get_waitlist_count(club.id, db) == 1
    # w3 (last in) is the one still waiting.
    still = await db.scalar(
        BookClubWaitlistEntry.__table__.select().where(
            BookClubWaitlistEntry.book_club_id == club.id,
            BookClubWaitlistEntry.user_id == w3.id,
        )
    )
    assert still is not None


@pytest.mark.asyncio
async def test_uncapped_club_no_waitlist(db):
    club = await _make_club(db, max_members=None)
    # Many members, no cap -> joining always adds a member, never waitlists.
    for _ in range(5):
        u = await _make_user(db)
        result = await BookClubPatronService.join_club(
            club_id=club.id, user_id=u.id, db=db
        )
        assert result["status"] == "joined"

    assert await book_club_service.get_member_count(club.id, db) == 5
    assert await book_club_service.get_waitlist_count(club.id, db) == 0

    # Explicit waitlist join on an uncapped club is rejected.
    u = await _make_user(db)
    wl = await BookClubPatronService.add_to_waitlist(
        club_id=club.id, user_id=u.id, db=db
    )
    assert wl["status"] == "uncapped"
    assert await book_club_service.get_waitlist_count(club.id, db) == 0
