# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Retention purge for challenger identity on book_challenges.

Encrypting the fields protects them at rest but keeps them forever. The
challenge record stays permanently for transparency; the identity of the person
who filed it does not need to. Name and contact are nulled 12 months after
resolution.

challenger_complaint is deliberately kept: it is the substance of the objection
and part of the institutional record, not an identifier.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.book_challenge import (
    BookChallenge,
    ChallengeOutcome,
    ChallengeReason,
    ChallengeStatus,
)
from app.services.data_retention_service import purge_resolved_challenger_pii

from tests.pii_encryption_fixture import pii_encryption_on  # noqa: F401

pytestmark = pytest.mark.usefixtures("pii_encryption_on")


async def _challenge(db, *, resolved_months_ago=None):
    resolved = None
    if resolved_months_ago is not None:
        resolved = datetime.now(timezone.utc) - timedelta(days=30 * resolved_months_ago)
    row = BookChallenge(
        title="Gender Queer: A Memoir",
        author="Maia Kobabe",
        primary_reason=ChallengeReason.SEXUAL_CONTENT,
        status=ChallengeStatus.RESOLVED_RETAINED,
        outcome=ChallengeOutcome.RETAINED,
        challenger_name="Dana Reyes",
        challenger_contact="dana@example.org",
        challenger_complaint="I object to the illustrations.",
        public_title="A challenge to Gender Queer",
        public_summary="Retained after committee review.",
        date_resolved=resolved,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def _reload(db, row_id):
    db.expunge_all()
    return (await db.execute(select(BookChallenge).where(BookChallenge.id == row_id))).scalar_one()


@pytest.mark.asyncio
async def test_purges_identity_from_a_long_resolved_challenge(db_session):
    row = await _challenge(db_session, resolved_months_ago=18)

    purged = await purge_resolved_challenger_pii(db_session)
    await db_session.commit()

    assert purged >= 1
    after = await _reload(db_session, row.id)
    assert after.challenger_name is None
    assert after.challenger_contact is None


@pytest.mark.asyncio
async def test_keeps_the_complaint_and_the_public_record(db_session):
    """The objection survives; only the identity goes."""
    row = await _challenge(db_session, resolved_months_ago=18)

    await purge_resolved_challenger_pii(db_session)
    await db_session.commit()

    after = await _reload(db_session, row.id)
    assert after.challenger_complaint == "I object to the illustrations."
    assert after.public_title == "A challenge to Gender Queer"
    assert after.public_summary == "Retained after committee review."
    assert after.outcome == ChallengeOutcome.RETAINED
    assert after.date_resolved is not None


@pytest.mark.asyncio
async def test_leaves_a_recently_resolved_challenge_alone(db_session):
    row = await _challenge(db_session, resolved_months_ago=1)

    await purge_resolved_challenger_pii(db_session)
    await db_session.commit()

    after = await _reload(db_session, row.id)
    assert after.challenger_name == "Dana Reyes"
    assert after.challenger_contact == "dana@example.org"


@pytest.mark.asyncio
async def test_leaves_an_unresolved_challenge_alone(db_session):
    """date_resolved is NULL: the clock has not started."""
    row = await _challenge(db_session, resolved_months_ago=None)

    await purge_resolved_challenger_pii(db_session)
    await db_session.commit()

    after = await _reload(db_session, row.id)
    assert after.challenger_name == "Dana Reyes"
    assert after.challenger_contact == "dana@example.org"


@pytest.mark.asyncio
async def test_is_idempotent(db_session):
    await _challenge(db_session, resolved_months_ago=18)

    first = await purge_resolved_challenger_pii(db_session)
    await db_session.commit()
    second = await purge_resolved_challenger_pii(db_session)
    await db_session.commit()

    assert first >= 1
    assert second == 0


@pytest.mark.asyncio
async def test_a_row_just_past_the_boundary_is_purged(db_session):
    row = await _challenge(db_session, resolved_months_ago=13)

    await purge_resolved_challenger_pii(db_session)
    await db_session.commit()

    after = await _reload(db_session, row.id)
    assert after.challenger_name is None


@pytest.mark.asyncio
async def test_a_row_just_inside_the_boundary_is_kept(db_session):
    row = await _challenge(db_session, resolved_months_ago=11)

    await purge_resolved_challenger_pii(db_session)
    await db_session.commit()

    after = await _reload(db_session, row.id)
    assert after.challenger_name == "Dana Reyes"
