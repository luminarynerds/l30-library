# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the two new FamilyReadingChallenges endpoints under
school-partnerships/family-challenges/{school_id}:

- GET /family-challenges/{school_id}                -> list_family_challenges_for_school
- GET /family-challenges/{school_id}/registrations  -> list_family_challenge_registrations_for_school

Calls handlers directly with mocked SQLAlchemy sessions, mirroring
backend/tests/unit/api/test_teacher_pd_endpoints.py to dodge the broken
tests/api/v1/conftest.py fixture chain.
"""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from app.models.user import UserRole


def _make_request():
    """Build a minimal real starlette Request to satisfy slowapi's decorator check."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
        "client": ("127.0.0.1", 0),
        "server": ("testserver", 80),
        "scheme": "http",
        "root_path": "",
        "raw_path": b"/",
        "app": MagicMock(state=MagicMock(limiter=MagicMock(enabled=False))),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


def _make_user(user_id=42):
    user = MagicMock()
    user.id = user_id
    return user


def _exec_returning_scalars(values):
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


def _exec_returning_rows(rows):
    """For aggregate queries returning tuples (e.g. group-by counts)."""
    result = MagicMock()
    result.all.return_value = rows
    return result


def _mock_result(value):
    """sqlalchemy Result whose ``scalar_one_or_none()`` returns ``value``.

    Must be a plain MagicMock, not AsyncMock: on a real Result object
    scalar_one_or_none() is synchronous. db is an AsyncMock, so leaving
    db.execute unconfigured makes its return value (and everything called
    on it) an auto-AsyncMock too -- result.scalar_one_or_none() would then
    return an unawaited coroutine instead of the value.
    """
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_challenge(
    challenge_id=1,
    name="Parents & Kids Read Together",
    goal_type="minutes",
    goal_value=600,
    is_active=True,
    challenge_type="parent-child",
    parent_reward="Free coffee",
):
    c = MagicMock()
    c.id = challenge_id
    c.name = name
    c.description = "Read with your kid"
    c.challenge_type = challenge_type
    c.goal_type = goal_type
    c.goal_value = goal_value
    # NOTE: kept as fixed calendar dates (not relative to today) because
    # test_list_family_challenges_returns_wrapped_list_with_frontend_shape
    # asserts the exact serialized "2026-05-01"/"2026-06-30" strings.
    # Tests that care about the computed active-vs-abandoned status (which
    # compares end_date to real "today") override end_date locally instead
    # of changing this shared default -- see
    # test_list_registrations_returns_wrapped_list_for_current_user.
    c.start_date = date(2026, 5, 1)
    c.end_date = date(2026, 6, 30)
    c.parent_reward_description = parent_reward
    c.child_reward_description = None
    c.is_active = is_active
    return c


def _make_registration(reg_id=1, challenge=None, parent_user_id=42, child_user_id=43, combined=120):
    r = MagicMock()
    r.id = reg_id
    r.challenge_id = challenge.id if challenge else 1
    r.challenge = challenge
    r.parent_user_id = parent_user_id
    r.child_user_id = child_user_id
    r.parent_progress = combined // 2
    r.child_progress = combined - (combined // 2)
    r.combined_progress = combined
    r.registered_at = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
    return r


# ============================================================================
# GET /family-challenges/{school_id} -- list challenges for a school
# ============================================================================


@pytest.mark.asyncio
async def test_list_family_challenges_returns_wrapped_list_with_frontend_shape():
    from app.api.v1.school_reading.family_engagement import list_family_challenges_for_school

    school = MagicMock(id=10, name="Elementary")
    challenge = _make_challenge(challenge_id=1, name="Read Together", goal_type="minutes", goal_value=600)

    db = AsyncMock()
    db.get.return_value = school  # school lookup
    db.execute.side_effect = [
        _exec_returning_scalars([challenge]),                  # list challenges
        _exec_returning_rows([(1, 3)]),                        # participant counts
    ]

    body = await list_family_challenges_for_school(
        request=_make_request(), school_id=10, db=db
    )

    assert "challenges" in body
    assert isinstance(body["challenges"], list)
    assert len(body["challenges"]) == 1

    row = body["challenges"][0]
    # Frontend ReadingChallenge interface fields:
    assert row["id"] == "1"
    assert row["title"] == "Read Together"
    assert row["description"] == "Read with your kid"
    assert row["startDate"] == "2026-05-01"
    assert row["endDate"] == "2026-06-30"
    assert row["goalMinutes"] == 600          # goal_type == minutes
    assert row["goalBooks"] == 0
    assert row["targetAgeGroup"] == "parent-child"
    assert row["theme"] == "parent-child"
    assert row["prizes"] == "Free coffee"
    assert row["participantCount"] == 3
    assert row["schoolId"] == "10"


@pytest.mark.asyncio
async def test_list_family_challenges_returns_empty_wrapped_when_no_challenges():
    from app.api.v1.school_reading.family_engagement import list_family_challenges_for_school

    db = AsyncMock()
    db.get.return_value = MagicMock(id=10)
    db.execute.side_effect = [
        _exec_returning_scalars([]),  # no challenges -- early return
    ]

    body = await list_family_challenges_for_school(
        request=_make_request(), school_id=10, db=db
    )

    assert body == {"challenges": []}


@pytest.mark.asyncio
async def test_list_family_challenges_books_goal_maps_to_goalBooks_not_goalMinutes():
    from app.api.v1.school_reading.family_engagement import list_family_challenges_for_school

    challenge = _make_challenge(challenge_id=2, name="Book Sprint", goal_type="books", goal_value=12)

    db = AsyncMock()
    db.get.return_value = MagicMock(id=10)
    db.execute.side_effect = [
        _exec_returning_scalars([challenge]),
        _exec_returning_rows([]),
    ]

    body = await list_family_challenges_for_school(
        request=_make_request(), school_id=10, db=db
    )
    row = body["challenges"][0]
    assert row["goalBooks"] == 12
    assert row["goalMinutes"] == 0
    assert row["participantCount"] == 0  # no count row


@pytest.mark.asyncio
async def test_list_family_challenges_404_when_school_missing():
    from fastapi import HTTPException
    from app.api.v1.school_reading.family_engagement import list_family_challenges_for_school

    db = AsyncMock()
    db.get.return_value = None  # school missing

    with pytest.raises(HTTPException) as exc:
        await list_family_challenges_for_school(
            request=_make_request(), school_id=999, db=db
        )
    assert exc.value.status_code == 404


# ============================================================================
# GET /family-challenges/{school_id}/registrations -- current user's regs
# ============================================================================


@pytest.mark.asyncio
async def test_list_registrations_returns_wrapped_list_for_current_user():
    from app.api.v1.school_reading.family_engagement import (
        list_family_challenge_registrations_for_school,
    )

    user = _make_user(user_id=42)
    school = MagicMock(id=10)
    challenge = _make_challenge(challenge_id=1, name="Read Together", goal_type="minutes", goal_value=600)
    # This test asserts status == "active", which the endpoint computes as
    # end_date > today -- override to a future date so the assertion doesn't
    # depend on when the suite happens to run (the shared _make_challenge
    # default is a fixed calendar date pinned for a different test's exact
    # date-string assertions).
    challenge.end_date = date.today() + timedelta(days=30)
    reg = _make_registration(reg_id=99, challenge=challenge, parent_user_id=42, combined=300)

    db = AsyncMock()
    db.get.return_value = school
    db.execute.return_value = _exec_returning_scalars([reg])

    body = await list_family_challenge_registrations_for_school(
        request=_make_request(), school_id=10, current_user=user, db=db
    )

    assert "registrations" in body
    assert isinstance(body["registrations"], list)
    assert len(body["registrations"]) == 1

    row = body["registrations"][0]
    # Frontend ChallengeRegistration interface fields:
    assert row["id"] == "99"
    assert row["challengeId"] == "1"
    assert row["challengeTitle"] == "Read Together"
    assert row["minutesRead"] == 300        # goal_type == minutes
    assert row["booksRead"] == 0
    assert row["goalMinutes"] == 600
    assert row["goalBooks"] == 0
    assert row["progressPercentage"] == 50.0
    assert row["status"] == "active"
    assert row["registrationDate"].startswith("2026-05-10")


@pytest.mark.asyncio
async def test_list_registrations_returns_empty_wrapped_when_none():
    from app.api.v1.school_reading.family_engagement import (
        list_family_challenge_registrations_for_school,
    )

    user = _make_user(user_id=42)
    db = AsyncMock()
    db.get.return_value = MagicMock(id=10)
    db.execute.return_value = _exec_returning_scalars([])

    body = await list_family_challenge_registrations_for_school(
        request=_make_request(), school_id=10, current_user=user, db=db
    )

    assert body == {"registrations": []}


@pytest.mark.asyncio
async def test_list_registrations_marks_completed_when_progress_at_or_above_goal():
    from app.api.v1.school_reading.family_engagement import (
        list_family_challenge_registrations_for_school,
    )

    user = _make_user(user_id=42)
    challenge = _make_challenge(challenge_id=1, goal_type="books", goal_value=10)
    reg = _make_registration(reg_id=1, challenge=challenge, parent_user_id=42, combined=10)

    db = AsyncMock()
    db.get.return_value = MagicMock(id=10)
    db.execute.return_value = _exec_returning_scalars([reg])

    body = await list_family_challenge_registrations_for_school(
        request=_make_request(), school_id=10, current_user=user, db=db
    )
    row = body["registrations"][0]
    assert row["booksRead"] == 10
    assert row["goalBooks"] == 10
    assert row["progressPercentage"] == 100.0
    assert row["status"] == "completed"


@pytest.mark.asyncio
async def test_list_registrations_404_when_school_missing():
    from fastapi import HTTPException
    from app.api.v1.school_reading.family_engagement import (
        list_family_challenge_registrations_for_school,
    )

    user = _make_user()
    db = AsyncMock()
    db.get.return_value = None

    with pytest.raises(HTTPException) as exc:
        await list_family_challenge_registrations_for_school(
            request=_make_request(), school_id=999, current_user=user, db=db
        )
    assert exc.value.status_code == 404


# ============================================================================
# Renamed: GET /family-challenges/by-id/{challenge_id}
# ============================================================================


@pytest.mark.asyncio
async def test_get_family_challenge_by_id_returns_challenge():
    from app.api.v1.school_reading.family_engagement import get_family_challenge

    challenge = _make_challenge(challenge_id=7, name="Old Path")
    challenge.program = MagicMock(partner_id=10)

    user = _make_user(user_id=42)
    user.role = UserRole.STAFF

    db = AsyncMock()
    # get_family_challenge fetches via db.execute(select(...).options(
    # selectinload(...))) now, not db.get() -- mocking db.get was stale.
    db.execute.return_value = _mock_result(challenge)

    result = await get_family_challenge(
        request=_make_request(), challenge_id=7, current_user=user, db=db
    )
    assert result is challenge
