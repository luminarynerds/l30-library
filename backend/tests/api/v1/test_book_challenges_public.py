# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for public (unauthenticated) book-challenges endpoints.

POST /api/v1/book-challenges/public/request — reconsideration form intake.

Covers:
- Turnstile gating: 400 when token invalid, no DB writes.
- Happy path: 201 + challenge + intake-note persisted.
- Transactional commit: if intake-note insert raises, no orphan challenge row.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book_challenge import BookChallenge, BookChallengeNote


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def _reset_test_engine_pool():
    """Workaround for asyncpg cross-event-loop pool errors.

    Same pattern as test_public_records_public.py — the shared L30 test engine
    pool keeps PG connections alive across event loops; each pytest-asyncio
    test gets a fresh loop, so we must dispose the pool between tests.
    """
    yield
    import tests.conftest as tc
    if tc._engine is not None:
        try:
            await tc._engine.dispose()
        except Exception:
            pass
        tc._engine = None
        tc._session_factory = None


SUBMIT_URL = "/api/v1/book-challenges/public/request"

VALID_PAYLOAD = {
    "title": "Test Book",
    "author": "Test Author",
    "primary_reason": "other",
    "challenger_complaint": "This is a complaint of sufficient length to satisfy the validator.",
    "challenger_name": "Jane Patron",
    "challenger_contact": "jane@example.com",
    "has_read_material": True,
    "turnstile_token": "valid-mock-token",
}


@pytest.fixture
def _feature_enabled():
    """Treat the banned-books feature as enabled for these tests."""
    with patch(
        "app.api.v1.feature_guards.OrganizationFeaturesService.is_feature_enabled",
        new=AsyncMock(return_value=True),
    ) as m:
        yield m


async def test_submit_happy_path_persists_challenge_and_note(
    client: AsyncClient, test_db: AsyncSession, _feature_enabled
):
    """Happy path: valid Turnstile token + complete payload → 201 + both rows persisted."""
    with patch(
        "app.api.v1.book_challenges.verify_turnstile",
        new=AsyncMock(return_value=True),
    ):
        resp = await client.post(SUBMIT_URL, json=VALID_PAYLOAD)

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "reference_id" in data
    assert data["expected_response_days"] == 30

    challenge_id = data["reference_id"]
    challenge = (
        await test_db.execute(select(BookChallenge).where(BookChallenge.id == challenge_id))
    ).scalar_one()
    assert challenge.title == "Test Book"
    assert challenge.challenger_name == "Jane Patron"

    notes = (
        await test_db.execute(
            select(BookChallengeNote).where(BookChallengeNote.challenge_id == challenge_id)
        )
    ).scalars().all()
    assert len(notes) == 1
    assert "online reconsideration form" in notes[0].note


async def test_submit_rejects_invalid_turnstile_with_no_db_writes(
    client: AsyncClient, test_db: AsyncSession, _feature_enabled
):
    """Invalid Turnstile token → 400, zero rows written."""
    before = (await test_db.execute(select(BookChallenge))).scalars().all()
    before_count = len(before)

    with patch(
        "app.api.v1.book_challenges.verify_turnstile",
        new=AsyncMock(return_value=False),
    ):
        resp = await client.post(SUBMIT_URL, json=VALID_PAYLOAD)

    assert resp.status_code == 400
    assert "Captcha" in resp.json()["error"]["message"]

    after = (await test_db.execute(select(BookChallenge))).scalars().all()
    assert len(after) == before_count


async def test_submit_rolls_back_when_intake_note_fails(
    client: AsyncClient, test_db: AsyncSession, _feature_enabled
):
    """If the intake-note insert raises, the challenge row must NOT persist."""
    from app.models import book_challenge as bc_model

    original_note_init = bc_model.BookChallengeNote.__init__

    def boom(self, *args, **kwargs):
        raise RuntimeError("simulated intake-note failure")

    before_count = len(
        (await test_db.execute(select(BookChallenge))).scalars().all()
    )

    with patch(
        "app.api.v1.book_challenges.verify_turnstile",
        new=AsyncMock(return_value=True),
    ):
        with patch.object(bc_model.BookChallengeNote, "__init__", boom):
            # The test client (ASGITransport) re-raises unhandled app exceptions
            # rather than surfacing the 500 a real server would return, so assert
            # the failure propagates, then verify the challenge row rolled back.
            with pytest.raises(RuntimeError, match="simulated intake-note failure"):
                await client.post(SUBMIT_URL, json=VALID_PAYLOAD)

    after_count = len(
        (await test_db.execute(select(BookChallenge))).scalars().all()
    )
    assert after_count == before_count, (
        "Challenge row leaked despite intake-note failure — transaction wrapper did not roll back"
    )
    bc_model.BookChallengeNote.__init__ = original_note_init  # belt-and-suspenders
