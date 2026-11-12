# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron date_of_birth encryption at rest + cleared under_18 boolean.

Commit 3 of the patron-PII-at-rest series. These tests are the deliverable:
do not weaken or skip them to go green.
"""

from datetime import date

import pytest
from sqlalchemy import select, text

from app.core.security import hash_password
from app.models.user import User, UserRole

# These assertions are only meaningful with encryption actually on; the deploy
# gate runs the suite with PII_ENCRYPTION_ENABLED=false.
from tests.pii_encryption_fixture import pii_encryption_on  # noqa: F401

pytestmark = pytest.mark.usefixtures("pii_encryption_on")


async def _make_patron(db, dob):
    user = User(
        email=f"dob{dob}@example.org",
        password_hash=hash_password("PatronPassword123!"),
        first_name="Dob",
        last_name="Tester",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        date_of_birth=dob,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _years_ago(n):
    today = date.today()
    try:
        return today.replace(year=today.year - n)
    except ValueError:  # Feb 29
        return today.replace(year=today.year - n, day=28)


@pytest.mark.asyncio
async def test_dob_is_ciphertext_at_rest(db_session):
    user = await _make_patron(db_session, _years_ago(25))

    raw = (
        await db_session.execute(
            text("SELECT date_of_birth FROM users WHERE id = :id"), {"id": user.id}
        )
    ).scalar_one()
    # Stored as a Fernet token string, not a DATE / ISO date literal.
    assert isinstance(raw, str)
    assert raw.startswith("gAAAAA")


@pytest.mark.asyncio
async def test_dob_roundtrip_decrypts(db_session):
    dob = _years_ago(40)
    user = await _make_patron(db_session, dob)
    db_session.expunge(user)
    reloaded = (await db_session.execute(select(User).where(User.id == user.id))).scalar_one()
    assert reloaded.date_of_birth == dob


@pytest.mark.asyncio
async def test_under_18_boolean_set_for_minor(db_session):
    user = await _make_patron(db_session, _years_ago(10))
    assert user.under_18 is True

    raw = (
        await db_session.execute(text("SELECT under_18 FROM users WHERE id = :id"), {"id": user.id})
    ).scalar_one()
    assert raw is True


@pytest.mark.asyncio
async def test_under_18_boolean_clear_for_adult(db_session):
    user = await _make_patron(db_session, _years_ago(30))
    assert user.under_18 is False


@pytest.mark.asyncio
async def test_under_18_can_be_filtered_in_sql(db_session):
    await _make_patron(db_session, _years_ago(8))
    await _make_patron(db_session, _years_ago(45))

    minors = (await db_session.execute(select(User).where(User.under_18.is_(True)))).scalars().all()
    assert len(minors) == 1
    assert minors[0].date_of_birth == _years_ago(8)
