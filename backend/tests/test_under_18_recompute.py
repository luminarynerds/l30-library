# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Daily under_18 age-gate recompute job.

date_of_birth is encrypted at rest, so under_18 is a maintained boolean. It is
written at insert/update time, but a patron who is not written on their 18th
birthday would keep a stale under_18=True. COPPA data-retention filters on this
flag, so recompute_under_18_flags must flip stale flags daily.

These tests are the deliverable for the recompute half of commit 3; do not
weaken or skip them to go green.
"""
import uuid
from datetime import date

import pytest
from sqlalchemy import select, text

from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
def _bind_job_to_test_engine(monkeypatch):
    # recompute_under_18_flags opens its own AsyncSessionLocal, which by default
    # is the app engine with a real pool -- pooled connections bind to the event
    # loop that opened them, and pytest-asyncio uses a fresh loop per test, so
    # the second test hits "Event loop is closed". Point the job at the shared
    # NullPool test session factory (conftest) so every call gets a fresh
    # connection on the current loop, mirroring the rest of the suite.
    from tests.conftest import get_session_factory
    import app.services.schedulers.patron_lifecycle_jobs as job_mod

    monkeypatch.setattr(job_mod, "AsyncSessionLocal", get_session_factory())


async def _make_patron(db, dob, *, email, under_18_override=None):
    # Unique-ify the email so the unique email_hash index never collides with a
    # leftover row from another test in the shared test DB.
    local, _, domain = email.partition("@")
    email = f"{local}+{uuid.uuid4().hex[:8]}@{domain}"
    user = User(
        email=email,
        password_hash="hashed",
        first_name="Recompute",
        last_name="Tester",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        date_of_birth=dob,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    # Force a stale/wrong flag directly in SQL, bypassing the before_update
    # event listener (which would auto-correct it on any ORM write).
    if under_18_override is not None:
        await db.execute(
            text("UPDATE users SET under_18 = :u WHERE id = :id"),
            {"u": under_18_override, "id": user.id},
        )
        await db.commit()
    return user.id


def _birthday(years_ago, *, month=None, day=None):
    today = date.today()
    m = month if month is not None else today.month
    d = day if day is not None else today.day
    try:
        return date(today.year - years_ago, m, d)
    except ValueError:  # Feb 29 source date
        return date(today.year - years_ago, m, 28)


async def _flag(db, user_id):
    return (
        await db.execute(
            text("SELECT under_18 FROM users WHERE id = :id"), {"id": user_id}
        )
    ).scalar_one()


@pytest.mark.asyncio
async def test_stale_true_flips_to_false_after_18th_birthday(test_db):
    from app.services.schedulers import recompute_under_18_flags

    # Over 18 but flag still says minor (no write since they aged out).
    dob = _birthday(19)  # unambiguously over 18 regardless of today
    uid = await _make_patron(test_db, dob, email="stale_true@test.com", under_18_override=True)
    assert await _flag(test_db, uid) is True

    await recompute_under_18_flags()

    test_db.expire_all()
    assert await _flag(test_db, uid) is False


@pytest.mark.asyncio
async def test_stale_null_set_true_for_minor(test_db):
    from app.services.schedulers import recompute_under_18_flags

    dob = _birthday(10)
    uid = await _make_patron(test_db, dob, email="stale_null@test.com", under_18_override=None)
    # Null out the flag that the insert listener set, to simulate legacy rows.
    await test_db.execute(text("UPDATE users SET under_18 = NULL WHERE id = :id"), {"id": uid})
    await test_db.commit()
    assert await _flag(test_db, uid) is None

    await recompute_under_18_flags()

    test_db.expire_all()
    assert await _flag(test_db, uid) is True


@pytest.mark.asyncio
async def test_exact_18th_birthday_is_not_under_18(test_db):
    from app.services.schedulers import recompute_under_18_flags

    # Born exactly 18 years ago today -> age 18 -> NOT under_18.
    dob = _birthday(18)
    uid = await _make_patron(test_db, dob, email="exactly18@test.com", under_18_override=True)

    await recompute_under_18_flags()

    test_db.expire_all()
    assert await _flag(test_db, uid) is False


@pytest.mark.asyncio
async def test_day_before_18th_birthday_is_under_18(test_db):
    from app.services.schedulers import recompute_under_18_flags

    today = date.today()
    # Born 18 years ago but birthday is tomorrow -> still 17 -> under_18.
    # Use 17 years and ~364 days: born 18y ago + 1 day in the past year window.
    try:
        dob = date(today.year - 18, today.month, today.day)
        # shift birthday to tomorrow so it has NOT occurred yet this cycle
        from datetime import timedelta
        dob = (today + timedelta(days=1)).replace(year=today.year - 18)
    except ValueError:
        dob = date(today.year - 18, today.month, 28)
    uid = await _make_patron(test_db, dob, email="almost18@test.com", under_18_override=False)

    await recompute_under_18_flags()

    test_db.expire_all()
    assert await _flag(test_db, uid) is True


@pytest.mark.asyncio
async def test_correct_flag_left_unchanged_and_idempotent(test_db):
    from app.services.schedulers import recompute_under_18_flags

    adult = await _make_patron(test_db, _birthday(40), email="adult_ok@test.com")
    minor = await _make_patron(test_db, _birthday(8), email="minor_ok@test.com")
    assert await _flag(test_db, adult) is False
    assert await _flag(test_db, minor) is True

    # Two runs in a row -> stable, no flip-flop.
    await recompute_under_18_flags()
    await recompute_under_18_flags()

    test_db.expire_all()
    assert await _flag(test_db, adult) is False
    assert await _flag(test_db, minor) is True


@pytest.mark.asyncio
async def test_dob_less_patron_flag_untouched(test_db):
    from app.services.schedulers import recompute_under_18_flags

    uid = await _make_patron(test_db, None, email="no_dob@test.com")
    # No DOB -> under_18 stays NULL (unknown), job must not invent a value.
    await test_db.execute(text("UPDATE users SET under_18 = NULL WHERE id = :id"), {"id": uid})
    await test_db.commit()

    await recompute_under_18_flags()

    test_db.expire_all()
    assert await _flag(test_db, uid) is None
