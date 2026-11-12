# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Challenger PII encryption at rest on book_challenges.

A patron who objects to a book fills in the reconsideration form on the public
/banned-books page. It posts to an unauthenticated endpoint and stores their
name, contact, and a free-text objection: what a named person thinks about a
book. For a library that sits close to circulation data in sensitivity, and it
was the least protected data on the page.

These tests are the deliverable: do not weaken or skip them to go green.
"""

import pytest
from sqlalchemy import select, text

from app.models.book_challenge import BookChallenge, ChallengeReason

# Only meaningful with encryption actually on; the deploy gate runs the suite
# with PII_ENCRYPTION_ENABLED=false.
from tests.pii_encryption_fixture import pii_encryption_on  # noqa: F401

pytestmark = pytest.mark.usefixtures("pii_encryption_on")


async def _make_challenge(db, name="Dana Reyes", contact="dana@example.org"):
    challenge = BookChallenge(
        title="Gender Queer: A Memoir",
        author="Maia Kobabe",
        primary_reason=ChallengeReason.SEXUAL_CONTENT,
        challenger_name=name,
        challenger_contact=contact,
        challenger_complaint="I object to the illustrations.",
    )
    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)
    return challenge


@pytest.mark.asyncio
async def test_challenger_name_is_ciphertext_at_rest(db_session):
    challenge = await _make_challenge(db_session)

    raw = (
        await db_session.execute(
            text("SELECT challenger_name FROM book_challenges WHERE id = :i"),
            {"i": challenge.id},
        )
    ).scalar_one()

    assert raw != "Dana Reyes"
    assert raw.startswith("gAAAAA")


@pytest.mark.asyncio
async def test_challenger_contact_is_ciphertext_at_rest(db_session):
    challenge = await _make_challenge(db_session)

    raw = (
        await db_session.execute(
            text("SELECT challenger_contact FROM book_challenges WHERE id = :i"),
            {"i": challenge.id},
        )
    ).scalar_one()

    assert raw != "dana@example.org"
    assert raw.startswith("gAAAAA")


@pytest.mark.asyncio
async def test_challenger_complaint_is_ciphertext_at_rest(db_session):
    challenge = await _make_challenge(db_session)

    raw = (
        await db_session.execute(
            text("SELECT challenger_complaint FROM book_challenges WHERE id = :i"),
            {"i": challenge.id},
        )
    ).scalar_one()

    assert raw != "I object to the illustrations."
    assert raw.startswith("gAAAAA")


@pytest.mark.asyncio
async def test_values_read_back_as_plaintext_through_the_orm(db_session):
    challenge = await _make_challenge(db_session)
    db_session.expunge_all()

    fetched = (
        await db_session.execute(select(BookChallenge).where(BookChallenge.id == challenge.id))
    ).scalar_one()

    assert fetched.challenger_name == "Dana Reyes"
    assert fetched.challenger_contact == "dana@example.org"
    assert fetched.challenger_complaint == "I object to the illustrations."


@pytest.mark.asyncio
async def test_a_legacy_plaintext_row_still_reads(db_session):
    """The tolerant decrypt path. No backfill runs, so prod keeps plaintext rows."""
    challenge = await _make_challenge(db_session)
    await db_session.execute(
        text("UPDATE book_challenges SET challenger_name = :p WHERE id = :i"),
        {"p": "Legacy Plaintext", "i": challenge.id},
    )
    await db_session.commit()
    db_session.expunge_all()

    fetched = (
        await db_session.execute(select(BookChallenge).where(BookChallenge.id == challenge.id))
    ).scalar_one()

    assert fetched.challenger_name == "Legacy Plaintext"


@pytest.mark.asyncio
async def test_round_trips_unicode_and_apostrophes(db_session):
    challenge = await _make_challenge(
        db_session, name="Siobhán O'Malley-Núñez", contact="siobhán@example.org"
    )
    db_session.expunge_all()

    fetched = (
        await db_session.execute(select(BookChallenge).where(BookChallenge.id == challenge.id))
    ).scalar_one()

    assert fetched.challenger_name == "Siobhán O'Malley-Núñez"
    assert fetched.challenger_contact == "siobhán@example.org"


@pytest.mark.asyncio
async def test_a_null_challenger_stays_null(db_session):
    """The form's identity fields are optional; None must not become ciphertext."""
    challenge = await _make_challenge(db_session, name=None, contact=None)
    db_session.expunge_all()

    fetched = (
        await db_session.execute(select(BookChallenge).where(BookChallenge.id == challenge.id))
    ).scalar_one()

    assert fetched.challenger_name is None
    assert fetched.challenger_contact is None
