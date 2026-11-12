# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the book club bulk member import service.

Exercises the per-row outcome logic directly, without hitting the FastAPI
layer. Endpoint-level tests live in tests/api/test_book_club_import_endpoint.py.
"""

import uuid

import pytest
from sqlalchemy import select

from app.models.book_club import (
    BookClub,
    BookClubMember,
    BookClubMemberImport,
    BookClubRole,
)
from app.models.user import User, UserRole
from app.services import book_club_service


async def _make_user(test_db, email_local: str, *, active: bool = True, role=UserRole.PATRON) -> User:
    u = User(
        email=f"{email_local}-{uuid.uuid4().hex[:6]}@import-test.local",
        password_hash="x",
        first_name=email_local.title(),
        last_name="Test",
        role=role,
        is_active=active,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u


async def _make_club(test_db, staff: User) -> BookClub:
    c = BookClub(
        name=f"ImportTest {uuid.uuid4().hex[:6]}",
        description="pytest",
        created_by_id=staff.id,
        is_public=True,
    )
    test_db.add(c)
    await test_db.commit()
    await test_db.refresh(c)
    return c


@pytest.mark.asyncio
async def test_import_happy_path_adds_members(test_db):
    staff = await _make_user(test_db, "staff", role=UserRole.STAFF)
    club = await _make_club(test_db, staff)
    alice = await _make_user(test_db, "alice")
    bob = await _make_user(test_db, "bob")

    rows = [
        {"email": alice.email, "patron_id": None, "role": "member"},
        {"email": bob.email, "patron_id": None, "role": "facilitator"},
    ]
    out = await book_club_service.import_members(
        club_id=club.id,
        rows=rows,
        default_role="member",
        dry_run=False,
        imported_by_id=staff.id,
        db=test_db,
    )
    await test_db.commit()

    assert out["success_count"] == 2
    assert out["skipped_count"] == 0
    assert out["error_count"] == 0
    assert out["import_id"] is not None

    # Membership rows exist.
    res = await test_db.execute(
        select(BookClubMember).where(BookClubMember.book_club_id == club.id)
    )
    members = res.scalars().all()
    assert {m.user_id for m in members} == {alice.id, bob.id}
    roles_by_id = {m.user_id: m.role for m in members}
    assert roles_by_id[alice.id] == BookClubRole.member
    assert roles_by_id[bob.id] == BookClubRole.facilitator

    # Audit row created.
    res = await test_db.execute(
        select(BookClubMemberImport).where(BookClubMemberImport.book_club_id == club.id)
    )
    audits = res.scalars().all()
    assert len(audits) == 1
    assert audits[0].row_count == 2
    assert audits[0].success_count == 2


@pytest.mark.asyncio
async def test_import_in_file_duplicate_marked_duplicate(test_db):
    staff = await _make_user(test_db, "staff", role=UserRole.STAFF)
    club = await _make_club(test_db, staff)
    alice = await _make_user(test_db, "alice")

    rows = [
        {"email": alice.email, "patron_id": None, "role": "member"},
        {"email": alice.email, "patron_id": None, "role": "facilitator"},
    ]
    out = await book_club_service.import_members(
        club_id=club.id,
        rows=rows,
        default_role="member",
        dry_run=False,
        imported_by_id=staff.id,
        db=test_db,
    )
    await test_db.commit()

    assert out["success_count"] == 1
    assert out["skipped_count"] == 1
    assert out["rows"][1]["status"] == "duplicate"


@pytest.mark.asyncio
async def test_import_already_member_skipped(test_db):
    staff = await _make_user(test_db, "staff", role=UserRole.STAFF)
    club = await _make_club(test_db, staff)
    alice = await _make_user(test_db, "alice")

    # Pre-add alice as member.
    test_db.add(
        BookClubMember(book_club_id=club.id, user_id=alice.id, role=BookClubRole.member)
    )
    await test_db.commit()

    out = await book_club_service.import_members(
        club_id=club.id,
        rows=[{"email": alice.email, "patron_id": None, "role": "member"}],
        default_role="member",
        dry_run=False,
        imported_by_id=staff.id,
        db=test_db,
    )
    await test_db.commit()

    assert out["success_count"] == 0
    assert out["skipped_count"] == 1
    assert out["rows"][0]["status"] == "duplicate"


@pytest.mark.asyncio
async def test_import_not_found_for_unknown_email(test_db):
    staff = await _make_user(test_db, "staff", role=UserRole.STAFF)
    club = await _make_club(test_db, staff)

    out = await book_club_service.import_members(
        club_id=club.id,
        rows=[{"email": "ghost-nobody@import-test.local", "patron_id": None, "role": "member"}],
        default_role="member",
        dry_run=False,
        imported_by_id=staff.id,
        db=test_db,
    )
    await test_db.commit()

    assert out["success_count"] == 0
    assert out["skipped_count"] == 1
    assert out["rows"][0]["status"] == "not_found"


@pytest.mark.asyncio
async def test_import_invalid_email_format(test_db):
    staff = await _make_user(test_db, "staff", role=UserRole.STAFF)
    club = await _make_club(test_db, staff)

    out = await book_club_service.import_members(
        club_id=club.id,
        rows=[{"email": "not-an-email", "patron_id": None, "role": "member"}],
        default_role="member",
        dry_run=False,
        imported_by_id=staff.id,
        db=test_db,
    )
    await test_db.commit()

    assert out["error_count"] == 1
    assert out["rows"][0]["status"] == "invalid_email"


@pytest.mark.asyncio
async def test_import_deactivated_user_skipped(test_db):
    staff = await _make_user(test_db, "staff", role=UserRole.STAFF)
    club = await _make_club(test_db, staff)
    dead = await _make_user(test_db, "deactivated", active=False)

    out = await book_club_service.import_members(
        club_id=club.id,
        rows=[{"email": dead.email, "patron_id": None, "role": "member"}],
        default_role="member",
        dry_run=False,
        imported_by_id=staff.id,
        db=test_db,
    )
    await test_db.commit()

    assert out["skipped_count"] == 1
    assert out["rows"][0]["status"] == "deactivated"
    assert out["rows"][0]["user_id"] == dead.id


@pytest.mark.asyncio
async def test_import_dry_run_no_writes(test_db):
    staff = await _make_user(test_db, "staff", role=UserRole.STAFF)
    club = await _make_club(test_db, staff)
    alice = await _make_user(test_db, "alice")

    out = await book_club_service.import_members(
        club_id=club.id,
        rows=[{"email": alice.email, "patron_id": None, "role": "member"}],
        default_role="member",
        dry_run=True,
        imported_by_id=staff.id,
        db=test_db,
    )
    # dry_run: no commit needed (no writes), but commit anyway for symmetry.
    await test_db.commit()

    assert out["success_count"] == 1
    assert out["import_id"] is None

    res = await test_db.execute(
        select(BookClubMember).where(BookClubMember.book_club_id == club.id)
    )
    assert res.scalars().first() is None

    res = await test_db.execute(
        select(BookClubMemberImport).where(BookClubMemberImport.book_club_id == club.id)
    )
    assert res.scalars().first() is None


@pytest.mark.asyncio
async def test_import_row_cap_raises(test_db):
    staff = await _make_user(test_db, "staff", role=UserRole.STAFF)
    club = await _make_club(test_db, staff)

    rows = [{"email": f"x{i}@x.x", "patron_id": None, "role": "member"} for i in range(501)]
    with pytest.raises(book_club_service.ImportRowCapExceeded):
        await book_club_service.import_members(
            club_id=club.id,
            rows=rows,
            default_role="member",
            dry_run=False,
            imported_by_id=staff.id,
            db=test_db,
        )


@pytest.mark.asyncio
async def test_import_patron_id_wins_over_email(test_db):
    """If both resolve to different users, patron_id wins."""
    staff = await _make_user(test_db, "staff", role=UserRole.STAFF)
    club = await _make_club(test_db, staff)
    alice = await _make_user(test_db, "alice")
    bob = await _make_user(test_db, "bob")

    # email points to alice but patron_id points to bob: bob wins.
    out = await book_club_service.import_members(
        club_id=club.id,
        rows=[{"email": alice.email, "patron_id": str(bob.id), "role": "member"}],
        default_role="member",
        dry_run=False,
        imported_by_id=staff.id,
        db=test_db,
    )
    await test_db.commit()

    assert out["success_count"] == 1
    assert out["rows"][0]["status"] == "success"
    assert out["rows"][0]["user_id"] == bob.id


@pytest.mark.asyncio
async def test_import_invalid_role_marked_error(test_db):
    staff = await _make_user(test_db, "staff", role=UserRole.STAFF)
    club = await _make_club(test_db, staff)
    alice = await _make_user(test_db, "alice")

    out = await book_club_service.import_members(
        club_id=club.id,
        rows=[{"email": alice.email, "patron_id": None, "role": "wizard"}],
        default_role="member",
        dry_run=False,
        imported_by_id=staff.id,
        db=test_db,
    )
    await test_db.commit()

    assert out["error_count"] == 1
    assert out["rows"][0]["status"] == "invalid_role"
