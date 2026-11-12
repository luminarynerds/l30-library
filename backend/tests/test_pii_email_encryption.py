# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron email encryption at rest + email_hash blind index.

Commit 2 of the patron-PII-at-rest series. These tests are the deliverable:
do not weaken or skip them to go green.
"""

import pytest
from sqlalchemy import select, text

from app.core.security import hash_password
from app.models.user import User, UserRole, email_blind_hash

# These assertions are only meaningful with encryption actually on; the deploy
# gate runs the suite with PII_ENCRYPTION_ENABLED=false.
from tests.pii_encryption_fixture import pii_encryption_on  # noqa: F401

pytestmark = pytest.mark.usefixtures("pii_encryption_on")


async def _make_patron(db, email, first="Test", last="Patron"):
    user = User(
        email=email,
        password_hash=hash_password("PatronPassword123!"),
        first_name=first,
        last_name=last,
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_email_is_ciphertext_at_rest(db_session):
    user = await _make_patron(db_session, "ada@example.org")

    raw = (
        await db_session.execute(text("SELECT email FROM users WHERE id = :id"), {"id": user.id})
    ).scalar_one()
    assert raw != "ada@example.org"
    assert raw.startswith("gAAAAA")


@pytest.mark.asyncio
async def test_email_roundtrip_decrypts(db_session):
    user = await _make_patron(db_session, "grace@example.org")
    db_session.expunge(user)
    reloaded = (await db_session.execute(select(User).where(User.id == user.id))).scalar_one()
    assert reloaded.email == "grace@example.org"


@pytest.mark.asyncio
async def test_email_hash_populated_and_normalized(db_session):
    user = await _make_patron(db_session, "MixedCase@Example.ORG")
    # Hash is over the normalized (lowercased/stripped) email.
    assert user.email_hash == email_blind_hash("mixedcase@example.org")


@pytest.mark.asyncio
async def test_email_lookup_via_hash(db_session):
    await _make_patron(db_session, "ada@example.org")
    await _make_patron(db_session, "grace@example.org")

    target = email_blind_hash("ada@example.org")
    rows = (await db_session.execute(select(User).where(User.email_hash == target))).scalars().all()
    assert len(rows) == 1
    assert rows[0].email == "ada@example.org"


@pytest.mark.asyncio
async def test_email_uniqueness_enforced_via_hash(db_session):
    from sqlalchemy.exc import IntegrityError

    await _make_patron(db_session, "dup@example.org")
    with pytest.raises(IntegrityError):
        # Same email, different casing -> same hash -> unique violation.
        await _make_patron(db_session, "DUP@example.org")
