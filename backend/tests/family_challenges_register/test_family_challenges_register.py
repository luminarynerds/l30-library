# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the family-challenge register endpoint.

These tests live in their own directory (``tests/family_challenges_register``)
so they don't pick up ``tests/api/v1/conftest.py``'s autouse router-registration
fixture (which is fine for endpoint tests but slows down and over-couples a
pure-handler unit test).

The endpoint is exercised by calling the handler function directly with
mocked dependencies, following the MagicMock pattern established by
``tests/test_patron_preferences_api.py``.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.api.v1.school_reading.family_engagement import register_family_in_challenge
from app.models.reading import (
    FamilyChallengeRegistration,
    FamilyReadingChallenge,
    ReadingProgram,
)
from app.models.user import User, UserRole
from app.schemas.reading import FamilyChallengeRegistrationCreate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: int = 42, role: UserRole = UserRole.TEACHER) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = f"u{user_id}@example.com"
    user.role = role
    return user


def _make_challenge(challenge_id: int = 7, partner_id: int | None = 5) -> MagicMock:
    program = MagicMock(spec=ReadingProgram)
    program.id = 99
    program.partner_id = partner_id

    challenge = MagicMock(spec=FamilyReadingChallenge)
    challenge.id = challenge_id
    challenge.program_id = program.id
    challenge.program = program
    return challenge


def _mock_result(value):
    """sqlalchemy Result whose ``scalar_one_or_none()`` returns ``value``."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _request_stub() -> MagicMock:
    """Stand-in for the ``Request`` first arg slowapi-decorated handlers take."""
    return MagicMock(name="Request")


# ---------------------------------------------------------------------------
# Page shape (the bug we're fixing)
# ---------------------------------------------------------------------------


class TestPageShape:
    """Tests for the {schoolId, familyName, studentAge} shape."""

    @pytest.mark.asyncio
    async def test_creates_row_with_family_name_and_student_age(self):
        """Page-shape register stores familyName + studentAge, parent = current user."""
        user = _make_user(user_id=42)
        challenge = _make_challenge(challenge_id=7, partner_id=5)

        db = AsyncMock()
        db.execute.return_value = _mock_result(challenge)

        # capture what gets added
        added = {}

        def _add(obj):
            added["row"] = obj

        db.add = MagicMock(side_effect=_add)

        async def _refresh(obj):
            obj.id = 101
            obj.parent_progress = 0
            obj.child_progress = 0
            obj.combined_progress = 0
            obj.registered_at = MagicMock()

        db.refresh.side_effect = _refresh

        data = FamilyChallengeRegistrationCreate(
            schoolId=5,
            familyName="The Smiths",
            studentAge=8,
        )

        result = await register_family_in_challenge(
            request=_request_stub(),
            challenge_id=7,
            registration_data=data,
            current_user=user,
            db=db,
        )

        row = added["row"]
        assert isinstance(row, FamilyChallengeRegistration)
        assert row.challenge_id == 7
        assert row.family_name == "The Smiths"
        assert row.student_age == 8
        assert row.parent_user_id == 42
        assert row.child_user_id is None
        db.commit.assert_awaited_once()
        assert result is row

    @pytest.mark.asyncio
    async def test_wrong_school_returns_403(self):
        """schoolId mismatched with the challenge's program.partner_id is rejected."""
        user = _make_user()
        # challenge belongs to school 5, but page sends schoolId=999
        challenge = _make_challenge(partner_id=5)

        db = AsyncMock()
        db.execute.return_value = _mock_result(challenge)
        db.add = MagicMock()

        data = FamilyChallengeRegistrationCreate(
            schoolId=999, familyName="Wrong School", studentAge=10
        )

        with pytest.raises(HTTPException) as exc:
            await register_family_in_challenge(
                request=_request_stub(),
                challenge_id=7,
                registration_data=data,
                current_user=user,
                db=db,
            )

        assert exc.value.status_code == 403
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_challenge_returns_404(self):
        """Register against a non-existent challenge returns 404."""
        user = _make_user()
        db = AsyncMock()
        db.execute.return_value = _mock_result(None)
        db.add = MagicMock()

        data = FamilyChallengeRegistrationCreate(
            schoolId=5, familyName="Anyone", studentAge=8
        )

        with pytest.raises(HTTPException) as exc:
            await register_family_in_challenge(
                request=_request_stub(),
                challenge_id=12345,
                registration_data=data,
                current_user=user,
                db=db,
            )

        assert exc.value.status_code == 404
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_page_shape_family_name_only_works(self):
        """familyName alone (no schoolId) still routes through the page path."""
        user = _make_user(user_id=42)
        challenge = _make_challenge(partner_id=5)

        db = AsyncMock()
        db.execute.return_value = _mock_result(challenge)
        added = {}
        db.add = MagicMock(side_effect=lambda o: added.setdefault("row", o))

        async def _refresh(obj):
            obj.id = 1
            obj.parent_progress = 0
            obj.child_progress = 0
            obj.combined_progress = 0
            obj.registered_at = MagicMock()

        db.refresh.side_effect = _refresh

        data = FamilyChallengeRegistrationCreate(familyName="Solo", studentAge=11)

        await register_family_in_challenge(
            request=_request_stub(),
            challenge_id=7,
            registration_data=data,
            current_user=user,
            db=db,
        )

        row = added["row"]
        assert row.family_name == "Solo"
        assert row.student_age == 11
        assert row.parent_user_id == 42


# ---------------------------------------------------------------------------
# Linked-account shape (back-compat)
# ---------------------------------------------------------------------------


class TestLinkedAccountShape:
    """Tests for the legacy {parent_user_id, child_user_id, ...} shape."""

    @pytest.mark.asyncio
    async def test_creates_row_with_user_ids(self):
        """Legacy shape still creates a row with parent + child user FKs."""
        user = _make_user(user_id=42)  # staff invoker
        challenge = _make_challenge(partner_id=5)

        db = AsyncMock()
        db.execute.return_value = _mock_result(challenge)
        added = {}
        db.add = MagicMock(side_effect=lambda o: added.setdefault("row", o))

        async def _refresh(obj):
            obj.id = 1
            obj.parent_progress = 0
            obj.child_progress = 0
            obj.combined_progress = 0
            obj.registered_at = MagicMock()

        db.refresh.side_effect = _refresh

        data = FamilyChallengeRegistrationCreate(
            parent_user_id=100,
            child_user_id=200,
            parent_goal=300,
            child_goal=120,
        )

        await register_family_in_challenge(
            request=_request_stub(),
            challenge_id=7,
            registration_data=data,
            current_user=user,
            db=db,
        )

        row = added["row"]
        assert row.parent_user_id == 100
        assert row.child_user_id == 200
        assert row.parent_goal == 300
        assert row.child_goal == 120
        assert row.family_name is None or not hasattr(row, "family_name") or row.family_name is None
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_linked_shape_missing_child_id_returns_422(self):
        """parent_user_id without child_user_id is rejected."""
        user = _make_user()
        challenge = _make_challenge()
        db = AsyncMock()
        db.execute.return_value = _mock_result(challenge)
        db.add = MagicMock()

        data = FamilyChallengeRegistrationCreate(parent_user_id=100)

        with pytest.raises(HTTPException) as exc:
            await register_family_in_challenge(
                request=_request_stub(),
                challenge_id=7,
                registration_data=data,
                current_user=user,
                db=db,
            )

        assert exc.value.status_code == 422
        db.add.assert_not_called()
